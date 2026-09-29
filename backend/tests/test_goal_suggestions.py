"""Tests for suggesting where a follow-up plan could aim.

Someone finishing a plan often does not know what to go for next. One race
result predicts the rest well enough (Riegel: t2 = t1 * (d2/d1)^1.06), as long
as the step up allows for endurance that is not there yet.
"""
from app.services.follow_up import riegel_seconds, suggest_goals

RACE_10K = {"distance_km": 10.05, "time_seconds": 3520}  # 58:40


def summary(**overrides):
    fields = dict(goal="10k", goal_km=10.0, sessions_planned=36, sessions_done=32,
                  longest_run_km=12.3, build_weekly_km=24.0, race=RACE_10K)
    fields.update(overrides)
    return fields


def by_kind(suggestions):
    return {s["kind"]: s for s in suggestions}


# ── The prediction itself ────────────────────────────────────────────────────

def test_riegel_keeps_the_same_time_over_the_same_distance():
    assert riegel_seconds(3520, 10.05, 10.05) == 3520


def test_riegel_predicts_a_half_marathon_from_a_10k():
    """Roughly 2:09 from 58:40 — slower per km, as it should be."""
    assert 7650 <= riegel_seconds(3520, 10.05, 21.0975) <= 7800


# ── Faster at the same distance ──────────────────────────────────────────────

def test_suggests_the_same_distance_a_little_faster():
    faster = by_kind(suggest_goals(summary()))["faster"]

    assert faster["goal"] == "10k"
    assert faster["goal_kind"] == "race"
    assert 3400 <= faster["target_time_seconds"] < 3520


def test_a_measured_distance_close_to_a_standard_one_uses_that_goal():
    """10.05 km on GPS is a 10K, not a custom 10.05 km goal."""
    assert by_kind(suggest_goals(summary()))["faster"]["goal"] == "10k"


def test_an_odd_distance_becomes_a_custom_goal():
    faster = by_kind(suggest_goals(summary(race={"distance_km": 8.0, "time_seconds": 2880})))["faster"]

    assert faster["goal"] == "custom"
    assert faster["custom_distance_km"] == 8.0


def test_a_poorly_completed_plan_asks_for_less_improvement():
    keen = by_kind(suggest_goals(summary()))["faster"]["target_time_seconds"]
    patchy = by_kind(suggest_goals(summary(sessions_done=24)))["faster"]["target_time_seconds"]

    assert patchy > keen


def test_a_plan_mostly_skipped_suggests_no_faster_time():
    """Aiming faster after doing half the sessions sets the athlete up to fail."""
    kinds = by_kind(suggest_goals(summary(sessions_done=15)))

    assert "faster" not in kinds
    assert kinds["repeat"]["target_time_seconds"] == 3520


# ── A step up ────────────────────────────────────────────────────────────────

def test_suggests_the_next_distance_up():
    step = by_kind(suggest_goals(summary()))["step_up"]

    assert step["goal"] == "half_marathon"


def test_the_step_up_time_is_more_cautious_than_riegel():
    step = by_kind(suggest_goals(summary()))["step_up"]

    assert step["target_time_seconds"] > riegel_seconds(3520, 10.05, 21.0975)


def test_without_the_endurance_the_step_up_is_about_finishing():
    """A 6 km longest run is not a base for racing a half marathon."""
    step = by_kind(suggest_goals(summary(longest_run_km=6.0)))["step_up"]

    assert step["goal_kind"] == "fitness"
    assert step["target_time_seconds"] is None


def test_there_is_no_step_up_from_a_marathon():
    marathon = summary(goal="marathon", goal_km=42.195,
                       race={"distance_km": 42.3, "time_seconds": 16200}, longest_run_km=32)

    assert "step_up" not in by_kind(suggest_goals(marathon))


# ── Without a race ───────────────────────────────────────────────────────────

def test_without_a_race_no_time_is_invented():
    suggestions = suggest_goals(summary(race=None))

    assert all(s["target_time_seconds"] is None for s in suggestions)


def test_without_a_race_it_still_offers_the_next_distance_to_finish():
    step = by_kind(suggest_goals(summary(race=None)))["step_up"]

    assert step["goal"] == "half_marathon"
    assert step["goal_kind"] == "fitness"


def test_without_a_race_or_a_known_goal_there_is_nothing_to_suggest():
    assert suggest_goals(summary(race=None, goal="custom", goal_km=None)) == []
