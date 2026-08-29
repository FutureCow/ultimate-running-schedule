"""Tests for custom goal distances — a free km value instead of 5k/10k/HM/marathon."""
import pytest
from pydantic import ValidationError

from app.schemas.plan import PlanCreate
from app.services.claude_service import _build_prompt


def plan(**overrides) -> PlanCreate:
    base = dict(name="Test", goal="custom", custom_distance_km=18.5, duration_weeks=12)
    base.update(overrides)
    return PlanCreate(**base)


def prompt_for(**overrides) -> str:
    return _build_prompt(plan(**overrides), None, "English")


# ── Prompt: distance ─────────────────────────────────────────────────────────

def test_states_the_custom_distance_as_the_goal():
    assert "18.5 km" in prompt_for()


def test_drops_a_pointless_decimal_from_a_round_distance():
    assert "25 km" in prompt_for(custom_distance_km=25.0)
    assert "25.0 km" not in prompt_for(custom_distance_km=25.0)


# ── Prompt: race vs fitness framing ──────────────────────────────────────────

def test_a_custom_race_tapers_like_any_other_race():
    text = prompt_for(goal_kind="race")

    assert "Taper weeks" in text
    assert "race on day" in text


def test_a_fitness_goal_has_no_taper_and_no_race_day():
    text = prompt_for(goal_kind="fitness")

    assert "Taper weeks" not in text
    assert "race on day" not in text


def test_a_fitness_goal_names_the_target_week():
    """Week 12 of a 12-week plan is when the athlete must cover the distance."""
    text = prompt_for(goal_kind="fitness", duration_weeks=12)

    assert "week 12" in text.lower()
    assert "18.5 km" in text


def test_race_is_the_default_kind():
    assert "Taper weeks" in prompt_for()


# ── Prompt: ultra guidance ───────────────────────────────────────────────────

def test_beyond_the_marathon_the_prompt_switches_to_ultra_guidance():
    text = prompt_for(custom_distance_km=50)

    assert "back-to-back" in text.lower()


def test_marathon_distance_gets_no_ultra_guidance():
    assert "back-to-back" not in prompt_for(custom_distance_km=42.2).lower()


# ── Prompt: presets keep working ─────────────────────────────────────────────

def test_a_preset_goal_still_renders_its_own_label_and_taper():
    text = _build_prompt(
        PlanCreate(name="Test", goal="10k", duration_weeks=12), None, "English"
    )

    assert "10 km" in text
    assert "Taper weeks" in text


# ── Validation ───────────────────────────────────────────────────────────────

def test_a_custom_goal_requires_a_distance():
    with pytest.raises(ValidationError):
        PlanCreate(name="Test", goal="custom")


@pytest.mark.parametrize("distance", [0, 0.9, 100.1, 250])
def test_rejects_distances_outside_one_to_a_hundred_km(distance):
    with pytest.raises(ValidationError):
        PlanCreate(name="Test", goal="custom", custom_distance_km=distance)


@pytest.mark.parametrize("distance", [1, 18.5, 42.2, 100])
def test_accepts_distances_from_one_to_a_hundred_km(distance):
    assert PlanCreate(
        name="Test", goal="custom", custom_distance_km=distance
    ).custom_distance_km == distance


def test_a_preset_goal_discards_a_stray_custom_distance():
    """Switching back to a preset must not leave the old km value behind."""
    assert PlanCreate(
        name="Test", goal="10k", custom_distance_km=18.5
    ).custom_distance_km is None


def test_rejects_an_unknown_goal_kind():
    with pytest.raises(ValidationError):
        plan(goal_kind="something_else")


# ── PlanCreate → Plan column mapping ─────────────────────────────────────────

def test_every_plan_create_field_maps_onto_a_plan_column():
    """create_plan splats the payload straight onto Plan(); a name mismatch
    would only surface as a 500 at runtime."""
    from app.models.plan import Plan

    payload = plan(goal_kind="fitness")

    # Mirror what create_plan does with the payload
    plan_data = payload.model_dump()
    plan_data.pop("language", None)
    strength = plan_data.pop("strength", None) or {}
    plan_data["strength_enabled"] = strength.get("enabled", False)
    plan_data["strength_location"] = strength.get("location")
    plan_data["strength_type"] = strength.get("type")
    plan_data["strength_days"] = strength.get("days")
    plan_data["strength_equipment"] = strength.get("equipment")

    stored = Plan(user_id=1, **plan_data)

    assert stored.goal == "custom"
    assert stored.custom_distance_km == 18.5
    assert stored.goal_kind == "fitness"


# ── Target line ──────────────────────────────────────────────────────────────

def test_a_fitness_goal_has_no_time_target_to_chase():
    """"Personal best" contradicts "no time goal to peak for"."""
    text = prompt_for(goal_kind="fitness")

    assert "Personal best" not in text
    assert "Complete the distance" in text


def test_a_fitness_goal_still_honours_an_explicit_target_pace():
    assert "6:00/km" in prompt_for(goal_kind="fitness", target_pace_per_km="6:00")


def test_a_race_goal_without_a_time_still_aims_for_a_personal_best():
    assert "Personal best" in prompt_for(goal_kind="race")
