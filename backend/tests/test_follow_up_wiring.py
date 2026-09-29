"""Tests for wiring the follow-up summary into plan creation."""
from datetime import date

from app.models.plan import Plan
from app.routers.plans import _apply_race_override, _plan_columns, _plan_to_create, _tier_decision
from app.schemas.plan import PlanCreate
from app.services.claude_service import _build_prompt

SUMMARY = {
    "name": "10K najaar", "goal": "10k", "goal_km": 10.0, "duration_weeks": 12,
    "finished": True, "stopped_in_week": None, "estimated_vdot": 36,
    "pace_zones": {"threshold": "6:05 – 6:20"}, "zones_recalibrated": True,
    "sessions_planned": 36, "sessions_done": 31, "skipped_by_type": {"interval": 3},
    "longest_run_km": 12.3, "build_weekly_km": 24.0,
    "race": {"distance_km": 10.05, "time_seconds": 3520},
}


# ── Tier ─────────────────────────────────────────────────────────────────────

def test_elite_may_always_add_a_plan_and_keeps_the_old_one():
    assert _tier_decision("elite", has_plan=True, is_follow_up=True) == (True, False)
    assert _tier_decision("elite", has_plan=True, is_follow_up=False) == (True, False)


def test_a_first_plan_is_always_allowed():
    assert _tier_decision("base", has_plan=False, is_follow_up=False) == (True, False)


def test_base_and_tempo_replace_their_plan_with_a_follow_up():
    assert _tier_decision("base", has_plan=True, is_follow_up=True) == (True, True)
    assert _tier_decision("tempo", has_plan=True, is_follow_up=True) == (True, True)


def test_base_and_tempo_still_cannot_add_an_unrelated_second_plan():
    assert _tier_decision("tempo", has_plan=True, is_follow_up=False) == (False, False)


# ── Race time override ───────────────────────────────────────────────────────

def test_an_entered_race_time_replaces_the_measured_one():
    """The activity may include warm-up; the athlete knows the real time."""
    summary = _apply_race_override(dict(SUMMARY), 3480)

    assert summary["race"]["time_seconds"] == 3480
    assert summary["race"]["distance_km"] == 10.05


def test_an_entered_race_time_without_a_matched_race_uses_the_goal_distance():
    summary = _apply_race_override({**SUMMARY, "race": None}, 3480)

    assert summary["race"] == {"distance_km": 10.0, "time_seconds": 3480}


def test_no_override_leaves_the_summary_alone():
    assert _apply_race_override(dict(SUMMARY), None)["race"]["time_seconds"] == 3520


# ── Columns ──────────────────────────────────────────────────────────────────

def payload(**overrides):
    fields = dict(name="Halve", goal="half_marathon", duration_weeks=12,
                  previous_plan_id="abc", previous_race_time_seconds=3480,
                  previous_summary=SUMMARY)
    fields.update(overrides)
    return PlanCreate(**fields)


def test_every_payload_field_maps_onto_a_plan_column():
    """create_plan splats these onto Plan(); a stray field is a 500 at runtime."""
    stored = Plan(user_id=1, **_plan_columns(payload()))

    assert stored.previous_summary["race"]["time_seconds"] == 3520


def test_request_only_fields_are_not_columns():
    columns = _plan_columns(payload())

    assert "previous_plan_id" not in columns
    assert "previous_race_time_seconds" not in columns
    assert "language" not in columns


# ── Prompt and regeneration ──────────────────────────────────────────────────

def test_the_prompt_carries_the_previous_plan():
    text = _build_prompt(payload(), None, "Dutch")

    assert "## Previous plan" in text
    assert "58:40" in text


def test_a_fresh_plan_has_no_previous_plan_block():
    text = _build_prompt(payload(previous_summary=None), None, "Dutch")

    assert "## Previous plan" not in text


def test_regenerating_a_follow_up_keeps_its_history():
    """Editing the follow-up must not forget what it was built on."""
    stored = Plan(
        name="Halve", goal="half_marathon", duration_weeks=12, goal_kind="race",
        start_date=date(2026, 10, 5), strength_enabled=False, previous_summary=SUMMARY,
    )

    assert _plan_to_create(stored).previous_summary == SUMMARY
