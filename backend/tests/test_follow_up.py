"""Tests for summarising a finished (or abandoned) plan to build the next one on.

A new plan used to start from zero: only the profile and a Garmin summary went
in. What the previous plan learned — the race result, the recalibrated zones,
how far the long run got, what was skipped — was thrown away.
"""
from datetime import date
from types import SimpleNamespace

from app.services.follow_up import previous_plan_lines, summarise_plan

TODAY = date(2026, 9, 30)


def session(week, day, kind, planned_km, when, activity=None, completed=True):
    return SimpleNamespace(
        week_number=week, day_number=day, workout_type=kind, distance_km=planned_km,
        scheduled_date=when, garmin_activity_id=activity,
        completed_at="2026-01-01" if completed else None,
    )


def activity(km, seconds=None):
    return SimpleNamespace(distance_km=km, duration_seconds=seconds)


def plan(sessions, **overrides):
    fields = dict(
        name="10K najaar", goal="10k", custom_distance_km=None, duration_weeks=4,
        plan_json={"plan_overview": {
            "estimated_vdot": 36,
            "pace_zones": {"easy": "7:05 – 7:40", "threshold": "6:05 – 6:20"},
        }},
        sessions=sessions,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def finished_plan():
    """Four weeks, a race on the last Sunday, one interval and one easy run skipped."""
    s = [
        session(1, 2, "easy_run", 5, date(2026, 9, 1), "a1"),
        session(1, 4, "interval", 6, date(2026, 9, 3), completed=False),
        session(1, 7, "long_run", 8, date(2026, 9, 6), "a2"),
        session(2, 2, "easy_run", 5, date(2026, 9, 8), completed=False),
        session(2, 4, "tempo", 6, date(2026, 9, 10), "a3"),
        session(2, 7, "long_run", 10, date(2026, 9, 13), "a4"),
        session(3, 3, "rest", None, date(2026, 9, 16), completed=False),
        session(3, 7, "long_run", 12, date(2026, 9, 20), "a5"),
        session(4, 7, "race", 10, date(2026, 9, 27), "race"),
    ]
    acts = {
        "a1": activity(5.2), "a2": activity(8.1), "a3": activity(6.3),
        "a4": activity(10.4), "a5": activity(12.3), "race": activity(10.05, 3520),
    }
    return plan(s), acts


# ── The summary ──────────────────────────────────────────────────────────────

def test_a_plan_past_its_last_session_is_finished():
    p, acts = finished_plan()

    assert summarise_plan(p, acts, today=TODAY)["finished"] is True


def test_counts_sessions_done_and_skipped_leaving_rest_out():
    summary = summarise_plan(*finished_plan(), today=TODAY)

    assert summary["sessions_done"] == 6
    assert summary["sessions_planned"] == 8


def test_lists_what_was_skipped_by_type():
    summary = summarise_plan(*finished_plan(), today=TODAY)

    assert summary["skipped_by_type"] == {"interval": 1, "easy_run": 1}


def test_the_longest_run_is_the_distance_actually_run():
    """12.3 km measured, not the 12 km planned — and not the race."""
    assert summarise_plan(*finished_plan(), today=TODAY)["longest_run_km"] == 12.3


def test_takes_the_race_result_from_the_matched_activity():
    race = summarise_plan(*finished_plan(), today=TODAY)["race"]

    assert race["time_seconds"] == 3520
    assert race["distance_km"] == 10.05


def test_carries_the_level_the_plan_ended_on():
    summary = summarise_plan(*finished_plan(), today=TODAY)

    assert summary["estimated_vdot"] == 36
    assert summary["pace_zones"]["threshold"] == "6:05 – 6:20"
    assert summary["zones_recalibrated"] is False


def test_notices_zones_that_were_recalibrated():
    p, acts = finished_plan()
    p.plan_json["plan_overview"]["original_pace_zones"] = {"easy": "7:20 – 7:55"}

    assert summarise_plan(p, acts, today=TODAY)["zones_recalibrated"] is True


def test_weekly_volume_leaves_the_taper_out():
    """Weeks 1-2 are the build (13.3 and 16.7 km measured); 3-4 are the taper."""
    summary = summarise_plan(*finished_plan(), today=TODAY)

    assert summary["build_weekly_km"] == 15.0


def test_a_manually_completed_session_counts_its_planned_distance():
    p = plan([session(1, 7, "long_run", 9, date(2026, 9, 6), activity=None)])

    assert summarise_plan(p, {}, today=TODAY)["longest_run_km"] == 9


# ── A plan left halfway ──────────────────────────────────────────────────────

def test_a_plan_with_sessions_still_ahead_is_not_finished():
    p, acts = finished_plan()

    summary = summarise_plan(p, acts, today=date(2026, 9, 14))

    assert summary["finished"] is False
    assert summary["stopped_in_week"] == 2


def test_future_sessions_do_not_count_as_skipped():
    p, acts = finished_plan()

    summary = summarise_plan(p, acts, today=date(2026, 9, 14))

    assert summary["sessions_planned"] == 6  # 1 Sep – 13 Sep, rest day left out
    assert summary["race"] is None


# ── In the prompt ────────────────────────────────────────────────────────────

def text(summary) -> str:
    return " ".join(previous_plan_lines(summary).split()).lower()


def test_the_prompt_says_to_build_on_it_not_restart():
    assert "do not restart" in text(summarise_plan(*finished_plan(), today=TODAY))


def test_the_prompt_gives_the_race_time_and_pace():
    lines = previous_plan_lines(summarise_plan(*finished_plan(), today=TODAY))

    assert "58:40" in lines
    assert "5:50 /km" in lines


def test_the_prompt_names_what_was_skipped():
    assert "1× interval" in text(summarise_plan(*finished_plan(), today=TODAY))


def test_the_prompt_sets_the_starting_volume_from_the_build_weeks():
    t = text(summarise_plan(*finished_plan(), today=TODAY))

    assert "15.0 km" in t
    assert "80–90%" in t


def test_the_prompt_says_when_a_plan_was_not_finished():
    p, acts = finished_plan()

    assert "stopped in week 2" in text(summarise_plan(p, acts, today=date(2026, 9, 14)))


# ── Aerobic efficiency: faster at the same heart rate ────────────────────────

def easy(week, day, when, act_id):
    return session(week, day, "easy_run", 6, when, act_id)


def run_at(km, pace_s, hr):
    """An activity of km at pace_s per km with an average heart rate."""
    act = activity(km, round(km * pace_s))
    act.avg_heart_rate = hr
    return act


def efficiency_plan(late_pace_s=425, late_hr=150, early_pace_s=450, early_hr=150, n=3):
    """n easy runs early in the plan and n late, before the taper."""
    sessions, acts = [], {}
    for i in range(n):
        sessions.append(easy(1, 2 + i, date(2026, 6, 1 + i), f"e{i}"))
        acts[f"e{i}"] = run_at(6, early_pace_s, early_hr)
        sessions.append(easy(8, 2 + i, date(2026, 7, 20 + i), f"l{i}"))
        acts[f"l{i}"] = run_at(6, late_pace_s, late_hr)
    return plan(sessions, duration_weeks=12), acts


def test_measures_running_faster_at_the_same_heart_rate():
    """7:30 -> 7:05 at 150 bpm is about 6% more distance per heartbeat."""
    p, acts = efficiency_plan()

    eff = summarise_plan(p, acts, today=TODAY)["aerobic_efficiency"]

    assert 5.5 <= eff["change_pct"] <= 6.5


def test_a_high_heart_rate_runner_is_judged_against_themselves():
    """Same 6% gain, just at 165 bpm throughout: the level does not matter."""
    p, acts = efficiency_plan(early_hr=165, late_hr=165)

    assert 5.5 <= summarise_plan(p, acts, today=TODAY)["aerobic_efficiency"]["change_pct"] <= 6.5


def test_the_same_pace_at_a_lower_heart_rate_is_also_a_gain():
    p, acts = efficiency_plan(early_pace_s=450, late_pace_s=450, early_hr=155, late_hr=145)

    assert summarise_plan(p, acts, today=TODAY)["aerobic_efficiency"]["change_pct"] > 5


def test_too_few_easy_runs_with_heart_rate_gives_no_trend():
    """Noise sold as a trend is worse than saying nothing."""
    p, acts = efficiency_plan(n=2)

    assert summarise_plan(p, acts, today=TODAY)["aerobic_efficiency"] is None


def test_runs_without_heart_rate_are_left_out():
    p, acts = efficiency_plan()
    for act in acts.values():
        act.avg_heart_rate = None

    assert summarise_plan(p, acts, today=TODAY)["aerobic_efficiency"] is None


def test_the_prompt_reports_the_gain_with_the_heat_caveat():
    p, acts = efficiency_plan()

    t = text(summarise_plan(p, acts, today=TODAY))

    assert "same heart rate" in t
    assert "heat" in t


def test_the_trend_never_invents_a_target_time():
    """Without a race it says how much fitter, not how fast over a distance."""
    from app.services.follow_up import suggest_goals

    p, acts = efficiency_plan()
    summary = summarise_plan(p, acts, today=TODAY)

    assert all(s["target_time_seconds"] is None for s in suggest_goals(summary))
