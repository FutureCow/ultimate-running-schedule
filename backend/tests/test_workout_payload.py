"""Tests for the Garmin workout payload.

A pushed workout has to mirror the plan: separate steps for warm-up, each work
block, the jog between them and the cool-down — not one flattened block.
"""
from app.models.plan import WorkoutSession
from app.services.garmin_service import _build_workout_payload

PACES = {"warmup": "7:10 - 7:50", "main": "6:05 - 6:20", "cooldown": "7:20 - 8:00"}


def session(**overrides) -> WorkoutSession:
    fields = dict(
        plan_id=1, week_number=3, day_number=2,
        workout_type="tempo", title="Drempelloop", description="Blokken op drempeltempo.",
        distance_km=5.0, duration_minutes=40, target_paces=PACES, intervals=None,
    )
    fields.update(overrides)
    return WorkoutSession(**fields)


def steps_of(s: WorkoutSession) -> list[dict]:
    return _build_workout_payload(s)["workoutSegments"][0]["workoutSteps"]


def kinds(s: WorkoutSession) -> list[str]:
    return [st["stepType"]["stepTypeKey"] for st in steps_of(s)]


def distance_total_m(s: WorkoutSession) -> float:
    return sum(
        st["endConditionValue"] for st in steps_of(s)
        if st["endCondition"]["conditionTypeKey"] == "distance"
    )


TWO_BLOCKS = [{"reps": 2, "distance_m": 1000, "pace": "6:05 - 6:20", "rest_seconds": 90}]


# ── Interval structure is honoured whatever the workout is called ────────────

def test_a_tempo_session_with_blocks_gets_separate_steps():
    """The reported bug: a threshold session was flattened into one long block."""
    assert kinds(session(workout_type="tempo", intervals=TWO_BLOCKS)) == [
        "warmup", "interval", "recovery", "interval", "cooldown",
    ]


def test_an_interval_session_still_gets_separate_steps():
    assert kinds(session(workout_type="interval", intervals=TWO_BLOCKS)) == [
        "warmup", "interval", "recovery", "interval", "cooldown",
    ]


def test_no_jog_after_the_last_block():
    """A recovery jog between the blocks, not one trailing into the cool-down."""
    assert kinds(session(intervals=TWO_BLOCKS)).count("recovery") == 1


def test_every_work_block_carries_its_pace():
    work = [st for st in steps_of(session(intervals=TWO_BLOCKS))
            if st["stepType"]["stepTypeKey"] == "interval"]

    assert len(work) == 2
    assert all(st.get("targetValueOne") for st in work)


# ── Time-based blocks ────────────────────────────────────────────────────────

def test_a_block_given_in_minutes_becomes_a_timed_step():
    """"Two blocks of 6 minutes" must not silently become 1000 m."""
    timed = [{"reps": 2, "duration_seconds": 360, "pace": "6:05 - 6:20", "rest_seconds": 90}]

    work = [st for st in steps_of(session(intervals=timed))
            if st["stepType"]["stepTypeKey"] == "interval"]

    assert all(st["endCondition"]["conditionTypeKey"] == "time" for st in work)
    assert all(st["endConditionValue"] == 360 for st in work)


def test_distance_wins_when_both_are_given():
    both = [{"reps": 1, "distance_m": 1000, "duration_seconds": 360, "pace": "6:05 - 6:20"}]

    work = [st for st in steps_of(session(intervals=both))
            if st["stepType"]["stepTypeKey"] == "interval"]

    assert work[0]["endCondition"]["conditionTypeKey"] == "distance"
    assert work[0]["endConditionValue"] == 1000


# ── Warm-up and cool-down lengths ────────────────────────────────────────────

def test_uses_the_planned_warmup_and_cooldown():
    s = session(intervals=TWO_BLOCKS, warmup_km=1.5, cooldown_km=1.5)
    by_kind = {st["stepType"]["stepTypeKey"]: st for st in steps_of(s)}

    assert by_kind["warmup"]["endConditionValue"] == 1500
    assert by_kind["cooldown"]["endConditionValue"] == 1500


def test_falls_back_when_the_plan_does_not_say():
    """Plans generated before the fields existed keep the old defaults."""
    by_kind = {st["stepType"]["stepTypeKey"]: st for st in steps_of(session(intervals=TWO_BLOCKS))}

    assert by_kind["warmup"]["endConditionValue"] == 1000
    assert by_kind["cooldown"]["endConditionValue"] == 500


# ── A steady run must not overshoot its planned distance ─────────────────────

def test_a_steady_run_totals_its_planned_distance():
    """Warm-up and cool-down come out of the total, they are not added on top."""
    assert distance_total_m(session(distance_km=8.0)) == 8000


def test_the_planned_warmup_still_comes_out_of_the_total():
    s = session(distance_km=8.0, warmup_km=1.5, cooldown_km=1.5)
    by_kind = {st["stepType"]["stepTypeKey"]: st for st in steps_of(s)}

    assert by_kind["warmup"]["endConditionValue"] == 1500
    assert by_kind["interval"]["endConditionValue"] == 5000
    assert distance_total_m(s) == 8000


def test_a_run_too_short_to_split_stays_one_block():
    kinds_short = kinds(session(distance_km=1.0))

    assert kinds_short == ["interval"]
    assert distance_total_m(session(distance_km=1.0)) == 1000


def test_a_run_without_warmup_or_cooldown_paces_is_one_block():
    s = session(distance_km=6.0, target_paces={"main": "6:30 - 6:50"})

    assert kinds(s) == ["interval"]
    assert distance_total_m(s) == 6000
