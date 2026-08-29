"""Tests for _create_sessions_from_json — the plan_json → WorkoutSession mapping."""
from datetime import date, timedelta

import pytest

from app.models.plan import Plan
from app.routers.plans import _create_sessions_from_json

# Week 1 starts Monday 5 January 2026; a 12-week plan therefore races in week 12
# and winds down in week 13.
START = date(2026, 1, 5)
RACE_SATURDAY = date(2026, 3, 28)  # week 12, day 6


def make_plan(**overrides) -> Plan:
    plan = Plan(
        name="Test",
        goal="10k",
        duration_weeks=12,
        start_date=START,
        race_date=RACE_SATURDAY,
        strength_enabled=False,
    )
    plan.id = 1
    for key, value in overrides.items():
        setattr(plan, key, value)
    return plan


def workout(day_number: int, workout_type: str, title: str = "Run") -> dict:
    return {
        "day_number": day_number,
        "workout_type": workout_type,
        "title": title,
        "distance_km": 8.0,
    }


def make_plan_json(*weeks: dict) -> dict:
    return {"weeks": list(weeks)}


def week(number: int, *workouts: dict) -> dict:
    return {"week_number": number, "theme": f"Week {number}", "workouts": list(workouts)}


def find(sessions, week_number: int, day_number: int):
    for s in sessions:
        if s.week_number == week_number and s.day_number == day_number:
            return s
    return None


def test_keeps_post_race_recovery_week():
    """Week 13 is the post-race recovery week and must survive the race-date cutoff."""
    plan_json = make_plan_json(
        week(12, workout(6, "race", "Wedstrijd")),
        week(13, workout(2, "easy_run"), workout(4, "easy_run")),
    )

    sessions = _create_sessions_from_json(make_plan(), plan_json)

    recovery_week = [s for s in sessions if s.week_number == 13]
    assert len(recovery_week) == 2


def test_degrades_hard_workouts_after_the_race_to_recovery():
    """Nothing after the race is a hard session, in the race week or the week after."""
    plan_json = make_plan_json(
        week(12, workout(6, "race", "Wedstrijd"), workout(7, "tempo")),
        week(13, workout(2, "tempo"), workout(4, "easy_run")),
    )

    sessions = _create_sessions_from_json(make_plan(), plan_json)

    assert find(sessions, 12, 7).workout_type == "recovery"
    assert find(sessions, 13, 2).workout_type == "recovery"


def test_leaves_easy_workouts_after_the_race_untouched():
    """easy_run/recovery/rest are already wind-down types and keep their identity."""
    plan_json = make_plan_json(
        week(12, workout(6, "race", "Wedstrijd")),
        week(13, workout(2, "easy_run"), workout(5, "rest")),
    )

    sessions = _create_sessions_from_json(make_plan(), plan_json)

    assert find(sessions, 13, 2).workout_type == "easy_run"
    assert find(sessions, 13, 5).workout_type == "rest"


def test_pins_the_race_to_the_race_date_and_keeps_its_type():
    plan_json = make_plan_json(week(12, workout(3, "race", "Wedstrijd")))

    sessions = _create_sessions_from_json(make_plan(), plan_json)

    race = find(sessions, 12, 3)
    assert race.workout_type == "race"
    assert race.scheduled_date == RACE_SATURDAY


def test_schedules_recovery_week_on_the_calendar_week_after_the_race():
    plan_json = make_plan_json(
        week(12, workout(6, "race", "Wedstrijd")),
        week(13, workout(1, "easy_run")),
    )

    sessions = _create_sessions_from_json(make_plan(), plan_json)

    assert find(sessions, 13, 1).scheduled_date == date(2026, 3, 30)


def test_drops_sessions_scheduled_before_the_plan_start():
    """A plan starting mid-week skips the days before start_date."""
    wednesday_start = START + timedelta(days=2)
    plan_json = make_plan_json(week(1, workout(1, "easy_run"), workout(5, "easy_run")))

    sessions = _create_sessions_from_json(
        make_plan(start_date=wednesday_start), plan_json
    )

    assert find(sessions, 1, 1) is None
    assert find(sessions, 1, 5) is not None


def test_drops_strength_workouts_when_strength_is_disabled():
    plan_json = make_plan_json(week(1, workout(2, "strength"), workout(4, "easy_run")))

    sessions = _create_sessions_from_json(make_plan(strength_enabled=False), plan_json)

    assert find(sessions, 1, 2) is None
    assert find(sessions, 1, 4) is not None


def test_keeps_strength_workouts_when_strength_is_enabled():
    plan_json = make_plan_json(week(1, workout(2, "strength")))

    sessions = _create_sessions_from_json(make_plan(strength_enabled=True), plan_json)

    assert find(sessions, 1, 2).workout_type == "strength"


def test_without_a_race_date_every_week_is_kept_as_planned():
    plan_json = make_plan_json(
        week(12, workout(6, "tempo")),
        week(13, workout(2, "tempo")),
    )

    sessions = _create_sessions_from_json(make_plan(race_date=None), plan_json)

    assert find(sessions, 12, 6).workout_type == "tempo"
    assert find(sessions, 13, 2).workout_type == "tempo"
