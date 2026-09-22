"""Tests for the context and interpretation rules sent with a run analysis.

Numbers alone mislead: cadence read without the pace it was run at invites the
"aim for 180 spm" trope, which is wrong for an easy run.
"""
from app.services.claude_service import (
    _context_lines,
    _feedback_instructions,
    _feedback_prompt,
)


# ── Athlete context ──────────────────────────────────────────────────────────

def test_sends_the_athlete_height():
    """Taller runners cadence lower; without height that reads as a fault."""
    lines = "\n".join(_context_lines({"height_cm": 192}, None))

    assert "192" in lines


def test_sends_weekly_volume_as_load_context():
    lines = "\n".join(_context_lines({"weekly_km": 45, "weekly_runs": 4}, None))

    assert "45" in lines and "4" in lines


def test_omits_missing_athlete_fields_entirely():
    """A blank profile must not produce 'height: None' lines."""
    lines = "\n".join(_context_lines({"height_cm": None, "weight_kg": None}, None))

    assert "None" not in lines
    assert lines.strip() == ""


def test_no_athlete_and_no_session_yields_nothing():
    assert _context_lines(None, None) == []


# ── Planned session ──────────────────────────────────────────────────────────

def test_sends_the_planned_workout_type():
    """An easy run and an interval session must not be judged the same way."""
    lines = "\n".join(_context_lines(None, {"workout_type": "easy_run"}))

    assert "easy_run" in lines


def test_sends_the_prescribed_pace():
    lines = "\n".join(_context_lines(None, {"target_paces": {"main": "6:45 – 7:30"}}))

    assert "6:45" in lines


def test_sends_the_planned_distance():
    lines = "\n".join(_context_lines(None, {"distance_km": 8.0}))

    assert "8" in lines


def test_ignores_a_placeholder_pace():
    """Strength sessions carry main = 'N/A'."""
    lines = "\n".join(_context_lines(None, {"target_paces": {"main": "N/A"}}))

    assert "N/A" not in lines


# ── Interpretation guidance ──────────────────────────────────────────────────

def prompt(tone: str = "scientific") -> str:
    _, task, _ = _feedback_instructions(tone, "Dutch (Nederlands)")
    return _feedback_prompt(task, ["- Distance: 8 km"])


def flat(tone: str = "scientific") -> str:
    """Lowercased with whitespace collapsed, so assertions survive re-wrapping."""
    return " ".join(prompt(tone).split()).lower()


def test_the_prompt_ties_cadence_to_the_pace_that_was_run():
    text = prompt().lower()

    assert "cadence" in text
    assert "pace" in text
    assert "180" in text  # names the myth so it can be rejected


def test_the_prompt_warns_against_a_fixed_cadence_target():
    assert "never a fixed target" in prompt().lower()


def test_the_prompt_says_easy_zones_are_the_goal_on_an_easy_run():
    assert "easy run" in prompt().lower()


def test_both_tones_get_the_same_guidance():
    assert "180" in prompt("encouraging")


def test_the_prompt_still_carries_the_workout_data():
    assert "- Distance: 8 km" in prompt()


# ── Pace is the verdict, heart rate is evidence ──────────────────────────────

def test_the_prescribed_pace_is_the_verdict_on_execution():
    assert "prescribed pace is the verdict" in flat()


def test_a_session_run_on_pace_is_never_called_too_hard():
    """Three of four real analyses scolded the athlete for a correctly paced run."""
    assert "never tell an athlete who hit the prescribed pace" in flat()


def test_an_estimated_max_hr_may_not_be_stated_as_fact():
    text = flat()

    assert "estimate, not a measurement" in text
    assert "athlete-set" in text


def test_a_high_heart_rate_at_easy_pace_is_called_a_trait():
    """Some runners simply run high; that is not a fault to correct every week."""
    assert "trait, not a fault" in flat()


def test_the_old_flag_high_hr_on_easy_runs_rule_is_gone():
    assert "high hr on an easy run" not in prompt().lower()
