"""The race date decides which plan week is the race week."""
from datetime import date

from app.schemas.plan import PlanCreate, plan_week


def make(**fields) -> PlanCreate:
    return PlanCreate(name="Test", goal="10k", **fields)


def test_plan_week_counts_from_the_start_monday():
    sunday_start = date(2026, 8, 30)
    assert plan_week(sunday_start, sunday_start) == 1
    assert plan_week(sunday_start, date(2026, 8, 31)) == 2
    assert plan_week(sunday_start, date(2026, 11, 22)) == 13


def test_race_twelve_weeks_after_a_sunday_start_makes_a_13_week_plan():
    # Start + 12 × 7 days is the Sunday of week 13, not week 12
    plan = make(start_date=date(2026, 8, 30), race_date=date(2026, 11, 22), duration_weeks=12)
    assert plan.duration_weeks == 13


def test_race_on_sunday_of_week_12_keeps_12_weeks():
    plan = make(start_date=date(2026, 8, 24), race_date=date(2026, 11, 15), duration_weeks=12)
    assert plan.duration_weeks == 12


def test_midweek_start_and_saturday_race():
    # Wednesday 7 January 2026 → week 1 starts Monday 5 January; Saturday 28 March is week 12
    plan = make(start_date=date(2026, 1, 7), race_date=date(2026, 3, 28), duration_weeks=11)
    assert plan.duration_weeks == 12


def test_without_race_date_duration_is_left_alone():
    plan = make(start_date=date(2026, 8, 30), duration_weeks=10)
    assert plan.duration_weeks == 10


def test_race_before_start_does_not_change_duration():
    plan = make(start_date=date(2026, 8, 30), race_date=date(2026, 8, 1), duration_weeks=8)
    assert plan.duration_weeks == 8
