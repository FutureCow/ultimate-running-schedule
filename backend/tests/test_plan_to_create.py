"""Tests for _plan_to_create — rebuilding the AI input from a stored plan.

update_plan regenerates a plan by feeding a PlanCreate back to Claude. Every
field that shapes the prompt has to survive that round trip, or editing a plan
silently changes it.
"""
from datetime import date

from app.models.plan import Plan
from app.routers.plans import _plan_to_create


def stored_plan(**overrides) -> Plan:
    plan = Plan(
        name="Test",
        goal="10k",
        custom_distance_km=None,
        goal_kind="race",
        duration_weeks=12,
        start_date=date(2026, 1, 5),
        race_date=date(2026, 3, 28),
        strength_enabled=False,
    )
    for key, value in overrides.items():
        setattr(plan, key, value)
    return plan


def test_carries_a_custom_distance_across_the_round_trip():
    merged = _plan_to_create(
        stored_plan(goal="custom", custom_distance_km=18.5, goal_kind="fitness")
    )

    assert merged.goal == "custom"
    assert merged.custom_distance_km == 18.5
    assert merged.goal_kind == "fitness"


def test_keeps_a_preset_goal_a_race():
    merged = _plan_to_create(stored_plan(goal="marathon"))

    assert merged.goal == "marathon"
    assert merged.goal_kind == "race"
    assert merged.custom_distance_km is None


def test_carries_the_schedule_fields():
    merged = _plan_to_create(stored_plan())

    assert merged.duration_weeks == 12
    assert merged.start_date == date(2026, 1, 5)
    assert merged.race_date == date(2026, 3, 28)


def test_maps_flat_strength_columns_back_into_preferences():
    merged = _plan_to_create(
        stored_plan(
            strength_enabled=True,
            strength_location="gym",
            strength_type="max_strength",
            strength_days=[2, 5],
            strength_equipment=["dumbbells"],
        )
    )

    assert merged.strength is not None
    assert merged.strength.enabled is True
    assert merged.strength.location == "gym"
    assert merged.strength.days == [2, 5]


def test_leaves_strength_unset_when_disabled():
    assert _plan_to_create(stored_plan(strength_enabled=False)).strength is None
