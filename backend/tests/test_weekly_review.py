"""Tests for the weekly review of a plan that is under way."""
from datetime import date
from types import SimpleNamespace

from app.services.weekly_review import review_prompt, review_week, weekly_stats

# Week 1 starts Monday 7 September 2026; a Wednesday in week 4 is 30 September
START = date(2026, 9, 7)
IN_WEEK_4 = date(2026, 9, 30)


def session(week, day, kind, km, done=True, act=None, feedback=None, title="Run"):
    when = date.fromordinal(START.toordinal() + (week - 1) * 7 + day - 1)
    return SimpleNamespace(
        week_number=week, day_number=day, workout_type=kind, distance_km=km,
        scheduled_date=when, garmin_activity_id=act, completed_at="x" if done else None,
        ai_feedback=feedback, title=title,
    )


def activity(km, seconds=None, hr=None):
    return SimpleNamespace(distance_km=km, duration_seconds=seconds, avg_heart_rate=hr)


def plan():
    s = [
        session(1, 2, "easy_run", 5, act="a1"), session(1, 4, "tempo", 6, act="a2"),
        session(1, 7, "long_run", 8, act="a3"),
        session(2, 2, "easy_run", 5, done=False), session(2, 4, "interval", 6, act="a4"),
        session(2, 7, "long_run", 10, act="a5", feedback="Mooie duurloop, rustig begonnen.",
                title="Lange duurloop"),
        session(3, 2, "easy_run", 5, act="a6"), session(3, 3, "rest", None, done=False),
        session(3, 4, "tempo", 7, act="a7", feedback="Blokken netjes op tempo.", title="Drempelloop"),
        session(3, 7, "long_run", 11, act="a8"),
        session(4, 2, "easy_run", 6, done=False), session(4, 4, "interval", 7, done=False),
        session(4, 7, "long_run", 13, done=False),
        session(5, 7, "long_run", 15, done=False),
        session(6, 7, "race", 10, done=False),
    ]
    acts = {"a1": activity(5.1), "a2": activity(6.2), "a3": activity(8.3), "a4": activity(6.0),
            "a5": activity(10.4), "a6": activity(5.0), "a7": activity(7.1), "a8": activity(11.2)}
    return SimpleNamespace(
        name="10K", goal="10k", custom_distance_km=None, duration_weeks=6,
        start_date=START, race_date=date(2026, 10, 18), target_time_seconds=3420,
        sessions=s,
    ), acts


# ── Which week ───────────────────────────────────────────────────────────────

def test_reviews_the_last_full_week():
    """On a Wednesday in week 4, week 3 is the one that has finished."""
    p, _ = plan()

    assert review_week(p, IN_WEEK_4) == 3


def test_on_monday_the_week_just_ended_is_reviewed():
    p, _ = plan()

    assert review_week(p, date(2026, 9, 28)) == 3


def test_nothing_to_review_before_the_first_week_is_over():
    p, _ = plan()

    assert review_week(p, date(2026, 9, 10)) is None


def test_nothing_to_review_after_the_plan_has_ended():
    """By then the follow-up plan takes over."""
    p, _ = plan()

    assert review_week(p, date(2026, 11, 30)) is None


# ── The numbers ──────────────────────────────────────────────────────────────

def stats():
    p, acts = plan()
    return weekly_stats(p, acts, IN_WEEK_4)


def test_series_compares_planned_with_run_per_week():
    week_3 = next(w for w in stats()["weeks"] if w["week"] == 3)

    assert week_3["planned_km"] == 23
    assert week_3["run_km"] == 23.3
    assert week_3["sessions_done"] == 3
    assert week_3["sessions_planned"] == 3  # rest day left out


def test_a_skipped_session_shows_in_its_week():
    week_2 = next(w for w in stats()["weeks"] if w["week"] == 2)

    assert week_2["sessions_done"] == 2
    assert week_2["sessions_planned"] == 3


def test_the_series_covers_at_most_four_weeks_up_to_the_reviewed_one():
    assert [w["week"] for w in stats()["weeks"]] == [1, 2, 3]


def test_longest_run_so_far_and_longest_still_to_come():
    s = stats()

    assert s["longest_run_km"] == 11.2
    assert s["longest_ahead_km"] == 15


def test_counts_the_weeks_to_go():
    assert stats()["weeks_to_go"] == 3


def test_lists_next_week():
    ahead = stats()["next_week"]

    assert [(x["type"], x["km"]) for x in ahead] == [("easy_run", 6), ("interval", 7), ("long_run", 13)]


# ── The prompt ───────────────────────────────────────────────────────────────

def recent():
    p, _ = plan()
    return [(s.scheduled_date, s.title, s.ai_feedback) for s in p.sessions if s.ai_feedback]


def test_the_prompt_carries_the_numbers_and_the_recent_analyses():
    _, task, _ = review_prompt(stats(), recent(), "encouraging", "Dutch")

    assert "23.3" in task
    assert "Blokken netjes op tempo." in task


def test_the_prompt_asks_for_a_thread_not_a_repeat():
    _, task, _ = review_prompt(stats(), recent(), "scientific", "Dutch")

    assert "do not repeat" in " ".join(task.split()).lower()


def test_the_prompt_forbids_inventing_a_race_time():
    _, task, _ = review_prompt(stats(), recent(), "encouraging", "Dutch")

    assert "never predict a race time" in " ".join(task.split()).lower()


def test_the_prompt_ends_with_a_pep_talk():
    _, task, _ = review_prompt(stats(), recent(), "encouraging", "Dutch")

    assert "pep talk" in task.lower()


def test_the_tone_changes_the_voice():
    encouraging, _, _ = review_prompt(stats(), recent(), "encouraging", "Dutch")
    scientific, _, _ = review_prompt(stats(), recent(), "scientific", "Dutch")

    assert encouraging != scientific
