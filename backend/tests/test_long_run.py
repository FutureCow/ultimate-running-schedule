"""Tests for the long-run rule: the long run is the longest run of its week."""
from datetime import date

from app.schemas.plan import PlanCreate
from app.services.claude_service import (
    _build_prompt,
    _merge_corrected_weeks,
    find_long_run_violations,
)


def run(day: int, workout_type: str, distance_km, title: str = "Run") -> dict:
    return {
        "day_number": day,
        "workout_type": workout_type,
        "title": title,
        "distance_km": distance_km,
    }


def week(number: int, *workouts: dict) -> dict:
    return {"week_number": number, "theme": f"Week {number}", "workouts": list(workouts)}


def plan_json(*weeks: dict) -> dict:
    return {"weeks": list(weeks)}


# ── Detection ────────────────────────────────────────────────────────────────

def test_flags_a_week_where_another_run_is_longer_than_the_long_run():
    """The reported bug: Sunday long run 5.5 km, Thursday easy run 6.5 km."""
    data = plan_json(week(
        2,
        run(2, "easy_run", 4.0),
        run(4, "easy_run", 6.5),
        run(7, "long_run", 5.5),
    ))

    violations = find_long_run_violations(data)

    assert len(violations) == 1
    assert "2" in violations[0]


def test_accepts_a_week_where_the_long_run_is_longest():
    data = plan_json(week(
        2,
        run(2, "easy_run", 4.0),
        run(4, "easy_run", 5.0),
        run(7, "long_run", 8.0),
    ))

    assert find_long_run_violations(data) == []


def test_an_equally_long_run_is_not_a_violation():
    data = plan_json(week(2, run(4, "easy_run", 6.0), run(7, "long_run", 6.0)))

    assert find_long_run_violations(data) == []


def test_ignores_weeks_without_a_long_run():
    """Recovery and consolidation weeks legitimately have no long run."""
    data = plan_json(week(13, run(2, "easy_run", 4.0), run(4, "easy_run", 5.0)))

    assert find_long_run_violations(data) == []


def test_ignores_workouts_without_a_distance():
    """Rest and strength sessions carry distance_km = null."""
    data = plan_json(week(
        2,
        run(3, "strength", None),
        run(5, "rest", None),
        run(7, "long_run", 6.0),
    ))

    assert find_long_run_violations(data) == []


def test_reports_every_offending_week():
    data = plan_json(
        week(2, run(4, "easy_run", 6.5), run(7, "long_run", 5.5)),
        week(3, run(4, "easy_run", 5.0), run(7, "long_run", 9.0)),
        week(4, run(4, "tempo", 8.0), run(7, "long_run", 7.0)),
    )

    violations = find_long_run_violations(data)

    assert len(violations) == 2


# ── Merging the correction back ──────────────────────────────────────────────

def test_a_corrected_week_replaces_the_original():
    original = plan_json(
        week(2, run(4, "easy_run", 6.5), run(7, "long_run", 5.5)),
        week(3, run(4, "easy_run", 5.0), run(7, "long_run", 9.0)),
    )
    corrected = [week(2, run(4, "easy_run", 5.0), run(7, "long_run", 7.0))]

    merged = _merge_corrected_weeks(original, corrected)

    assert find_long_run_violations(merged) == []
    assert merged["weeks"][0]["workouts"][1]["distance_km"] == 7.0


def test_untouched_weeks_survive_the_merge():
    original = plan_json(
        week(2, run(4, "easy_run", 6.5), run(7, "long_run", 5.5)),
        week(3, run(4, "easy_run", 5.0), run(7, "long_run", 9.0)),
    )
    corrected = [week(2, run(4, "easy_run", 5.0), run(7, "long_run", 7.0))]

    merged = _merge_corrected_weeks(original, corrected)

    assert len(merged["weeks"]) == 2
    assert merged["weeks"][1]["workouts"][1]["distance_km"] == 9.0


def test_a_correction_for_an_unknown_week_is_ignored():
    """A hallucinated week number must not grow the plan."""
    original = plan_json(week(2, run(7, "long_run", 5.5)))

    merged = _merge_corrected_weeks(original, [week(99, run(7, "long_run", 7.0))])

    assert len(merged["weeks"]) == 1
    assert merged["weeks"][0]["week_number"] == 2


def test_merging_leaves_the_original_untouched():
    original = plan_json(week(2, run(4, "easy_run", 6.5), run(7, "long_run", 5.5)))

    _merge_corrected_weeks(original, [week(2, run(7, "long_run", 9.0))])

    assert original["weeks"][0]["workouts"][1]["distance_km"] == 5.5


# ── Prompt ───────────────────────────────────────────────────────────────────

def test_the_prompt_states_that_the_long_run_is_the_longest():
    text = _build_prompt(
        PlanCreate(
            name="T", goal="10k", duration_weeks=12,
            training_days=["tuesday", "thursday", "sunday"], long_run_day="sunday",
        ),
        None,
        "English",
    )

    assert "longest run" in text.lower()
