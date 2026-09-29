"""Tests for reading warm-up and cool-down lengths out of a session description.

Plans generated before warmup_km/cooldown_km existed have those fields empty,
so Garmin got the 1 km / 0.5 km defaults — while the description said exactly
how far to run: "Na 2 km inlopen ... daarna 1,5 km uitlopen."
"""
import pytest

from app.models.plan import WorkoutSession
from app.services.garmin_service import _build_workout_payload, _km_from_description

REPORTED = (
    "Na 2 km inlopen twee blokken van 8 minuten op drempeltempo met 90 seconden "
    "dribbelpauze, daarna 1,5 km uitlopen."
)


# ── Reading the description ──────────────────────────────────────────────────

def test_reads_the_reported_warmup():
    assert _km_from_description(REPORTED, "warmup") == 2.0


def test_reads_the_reported_cooldown_with_a_decimal_comma():
    assert _km_from_description(REPORTED, "cooldown") == 1.5


@pytest.mark.parametrize("text, expected", [
    ("Begin met 1,5 km rustig inlopen.", 1.5),
    ("Warming-up van 2 km, dan 5x 400 m.", 2.0),
    ("2 km warming-up gevolgd door blokken.", 2.0),
    ("Start with a 1.5 km warm-up.", 1.5),
    ("Warm-up: 2 km easy.", 2.0),
])
def test_reads_common_warmup_phrasings(text, expected):
    assert _km_from_description(text, "warmup") == expected


@pytest.mark.parametrize("text, expected", [
    ("Afsluiten met 1 km uitlopen.", 1.0),
    ("Cooling-down van 1,5 km.", 1.5),
    ("Finish with a 1 km cool-down.", 1.0),
    ("Daarna 2 km rustig uitlopen.", 2.0),
])
def test_reads_common_cooldown_phrasings(text, expected):
    assert _km_from_description(text, "cooldown") == expected


def test_does_not_mistake_the_cooldown_for_the_warmup():
    assert _km_from_description("Blokken, daarna 1,5 km uitlopen.", "warmup") is None


def test_ignores_distances_that_belong_to_the_work():
    """"5 km op drempeltempo" is not a warm-up."""
    assert _km_from_description("Loop 5 km op drempeltempo.", "warmup") is None


def test_ignores_an_implausible_length():
    assert _km_from_description("Na 15 km inlopen.", "warmup") is None


def test_no_description_gives_nothing():
    assert _km_from_description(None, "warmup") is None
    assert _km_from_description("", "cooldown") is None


# ── In the pushed workout ────────────────────────────────────────────────────

def old_plan_session(**overrides) -> WorkoutSession:
    """A session from before the fields existed: warmup_km and cooldown_km empty."""
    fields = dict(
        plan_id=1, week_number=5, day_number=2, workout_type="tempo",
        title="Drempelloop", description=REPORTED, distance_km=6.1,
        duration_minutes=45, warmup_km=None, cooldown_km=None,
        target_paces={"warmup": "7:10 - 7:50", "main": "6:05 - 6:20", "cooldown": "7:20 - 8:00"},
        intervals=[{"reps": 2, "distance_m": 1300, "pace": "6:05 - 6:20", "rest_seconds": 90}],
    )
    fields.update(overrides)
    return WorkoutSession(**fields)


def by_kind(s: WorkoutSession) -> dict:
    steps = _build_workout_payload(s)["workoutSegments"][0]["workoutSteps"]
    return {st["stepType"]["stepTypeKey"]: st for st in steps}


def test_an_old_plan_gets_the_warmup_its_description_asks_for():
    steps = by_kind(old_plan_session())

    assert steps["warmup"]["endConditionValue"] == 2000
    assert steps["cooldown"]["endConditionValue"] == 1500


def test_the_plan_field_still_wins_over_the_description():
    steps = by_kind(old_plan_session(warmup_km=3.0, cooldown_km=1.0))

    assert steps["warmup"]["endConditionValue"] == 3000
    assert steps["cooldown"]["endConditionValue"] == 1000


def test_without_either_it_falls_back_to_the_defaults():
    steps = by_kind(old_plan_session(description="Twee blokken op drempeltempo."))

    assert steps["warmup"]["endConditionValue"] == 1000
    assert steps["cooldown"]["endConditionValue"] == 500
