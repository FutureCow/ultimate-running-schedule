"""Tests for finding work blocks in the pace trace of a structured session.

The reported analysis compared the whole-run average (7:08/km, including
warm-up, cool-down and a walking pause) with the prescribed block pace
(6:05-6:20) and told an athlete who ran both blocks on target to speed up.
"""
from app.services.claude_service import (
    _detect_work_blocks,
    _feedback_instructions,
    _feedback_prompt,
    _pace_range_s,
    _structure_lines,
    _trace_lines,
)


def seg(start_s: int, end_s: int, pace_s: float, hr: int | None = 140):
    """One sample per second from start to end at a steady pace."""
    return [(t, pace_s, hr) for t in range(start_s, end_s)]


def reported_run():
    """Shaped like the reported chart: 2 km in, 2 x 8 min, walk, 1.5 km out."""
    samples = (
        seg(0, 900, 450, 135)            # warm-up ~7:30 for 15 min
        + seg(900, 1380, 373, 158)       # block 1 at 6:13 for 8 min
        + seg(1380, 1470, 720, 150)      # walking pause ~12:00
        + seg(1470, 1950, 370, 162)      # block 2 at 6:10 for 8 min
        + seg(1950, 2620, 450, 145)      # cool-down ~7:30
    )
    time_s = [s[0] for s in samples]
    pace = [s[1] for s in samples]
    hr = [s[2] for s in samples]
    return time_s, pace, hr


PLANNED = {
    "workout_type": "tempo",
    "target_paces": {"warmup": "7:10 – 7:50", "main": "6:05 – 6:20", "cooldown": "7:20 – 8:00"},
    "intervals": [{"reps": 2, "distance_m": 1300, "pace": "6:05 – 6:20", "rest_seconds": 90}],
}


# ── Pace ranges ──────────────────────────────────────────────────────────────

def test_parses_a_pace_range_in_seconds():
    assert _pace_range_s("6:05 – 6:20") == (365, 380)
    assert _pace_range_s("6:05-6:20 /km") == (365, 380)


def test_a_single_pace_is_a_range_of_one():
    assert _pace_range_s("6:10") == (370, 370)


def test_an_unusable_pace_gives_nothing():
    assert _pace_range_s("N/A") is None
    assert _pace_range_s(None) is None


# ── Finding the blocks ───────────────────────────────────────────────────────

def test_finds_both_blocks_in_the_reported_run():
    time_s, pace, hr = reported_run()

    blocks = _detect_work_blocks(time_s, pace, hr, threshold_s=405)

    assert len(blocks) == 2


def test_measures_each_block_at_its_own_pace():
    """The whole point: 6:13 and 6:10, not the 7:08 run average."""
    time_s, pace, hr = reported_run()

    first, second = _detect_work_blocks(time_s, pace, hr, threshold_s=405)

    assert abs(first["pace_s"] - 373) < 2
    assert abs(second["pace_s"] - 370) < 2


def test_measures_each_block_duration():
    time_s, pace, hr = reported_run()

    first, second = _detect_work_blocks(time_s, pace, hr, threshold_s=405)

    assert abs(first["duration_s"] - 480) <= 15
    assert abs(second["duration_s"] - 480) <= 15


def test_reports_heart_rate_per_block():
    time_s, pace, hr = reported_run()

    first, second = _detect_work_blocks(time_s, pace, hr, threshold_s=405)

    assert first["hr"] == 158
    assert second["hr"] == 162


def test_a_gps_spike_is_not_a_block():
    """The reported chart starts with a spike to under 5:00 for a few seconds."""
    samples = seg(0, 5, 290) + seg(5, 900, 450)
    time_s, pace, hr = [s[0] for s in samples], [s[1] for s in samples], [s[2] for s in samples]

    assert _detect_work_blocks(time_s, pace, hr, threshold_s=405) == []


def test_a_short_dip_inside_a_block_does_not_split_it():
    """A corner or a traffic light is not the end of the block."""
    samples = seg(0, 300, 450) + seg(300, 540, 372) + seg(540, 552, 460) + seg(552, 780, 372) + seg(780, 1100, 450)
    time_s, pace, hr = [s[0] for s in samples], [s[1] for s in samples], [s[2] for s in samples]

    assert len(_detect_work_blocks(time_s, pace, hr, threshold_s=405)) == 1


def test_stopped_samples_are_not_work():
    samples = seg(0, 300, 450) + [(t, None, None) for t in range(300, 600)] + seg(600, 900, 450)
    time_s, pace, hr = [s[0] for s in samples], [s[1] for s in samples], [s[2] for s in samples]

    assert _detect_work_blocks(time_s, pace, hr, threshold_s=405) == []


# ── What the analysis is told ────────────────────────────────────────────────

def structure(planned=PLANNED):
    time_s, pace, hr = reported_run()
    return "\n".join(_structure_lines({"time": time_s, "pace": pace, "heart_rate": hr}, planned))


def test_states_the_planned_work():
    text = structure()

    assert "2 × 1300 m" in text
    assert "6:05" in text


def test_lists_the_measured_blocks():
    text = structure()

    assert "block 1" in text and "block 2" in text
    assert "6:13" in text and "6:10" in text


def test_labels_the_run_average_as_including_the_easy_parts():
    assert "warm-up, cool-down and pauses" in structure()


def test_says_so_when_no_block_was_found():
    """An honest 'none found' beats silence the model fills with the average."""
    samples = seg(0, 2000, 450)
    stream = {"time": [s[0] for s in samples], "pace": [s[1] for s in samples],
              "heart_rate": [s[2] for s in samples]}

    text = "\n".join(_structure_lines(stream, PLANNED))

    assert "no sustained block" in text.lower()


def test_a_steady_run_gets_no_block_analysis():
    steady = {"workout_type": "easy_run", "target_paces": {"main": "7:10 – 7:50"}}

    assert _structure_lines({"time": [0, 1], "pace": [450, 450], "heart_rate": [140, 140]}, steady) == []


# ── The coarse trace ─────────────────────────────────────────────────────────

def test_the_trace_is_every_30_seconds_for_a_normal_run():
    time_s, pace, hr = reported_run()

    lines = _trace_lines(time_s, pace, hr)

    assert 80 <= len(lines) <= 95  # 43:40 in 30 s steps, plus a header


def test_a_long_run_falls_back_to_one_row_per_minute():
    samples = seg(0, 7200, 450)
    lines = _trace_lines([s[0] for s in samples], [s[1] for s in samples], [s[2] for s in samples])

    assert 115 <= len(lines) <= 125


def test_the_trace_shows_the_pause():
    time_s, pace, hr = reported_run()

    assert any("12:00 /km" in line for line in _trace_lines(time_s, pace, hr))


# ── The rule ─────────────────────────────────────────────────────────────────

def test_the_prompt_forbids_comparing_the_run_average_with_the_block_pace():
    _, task, _ = _feedback_instructions("encouraging", "Dutch")
    flat = " ".join(_feedback_prompt(task, []).split()).lower()

    assert "never compare the whole-run average" in flat
