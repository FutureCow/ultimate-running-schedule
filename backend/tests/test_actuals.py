"""Tests for keeping planned and actual figures apart.

The plan holds what was planned; garmin_activities holds what was actually run.
Sync used to copy the actual distance onto the session, destroying the plan.
"""
from types import SimpleNamespace

from app.services.garmin_service import attach_actuals


def session(activity_id=None, distance_km=8.0):
    return SimpleNamespace(
        garmin_activity_id=activity_id,
        distance_km=distance_km,
        duration_minutes=45,
    )


def activity(distance_km=8.2, duration_seconds=2820, pace="5:44", hr=142):
    return SimpleNamespace(
        distance_km=distance_km,
        duration_seconds=duration_seconds,
        avg_pace_per_km=pace,
        avg_heart_rate=hr,
    )


def test_attaches_the_actual_distance_from_the_matched_activity():
    s = session("act-1")

    attach_actuals([s], {"act-1": activity()})

    assert s.actual_distance_km == 8.2


def test_leaves_the_planned_distance_untouched():
    """The whole point: the plan survives the sync."""
    s = session("act-1", distance_km=8.0)

    attach_actuals([s], {"act-1": activity(distance_km=8.2)})

    assert s.distance_km == 8.0


def test_converts_the_actual_duration_to_minutes():
    s = session("act-1")

    attach_actuals([s], {"act-1": activity(duration_seconds=2820)})

    assert s.actual_duration_minutes == 47


def test_carries_the_actual_pace_and_heart_rate():
    s = session("act-1")

    attach_actuals([s], {"act-1": activity(pace="5:44", hr=142)})

    assert s.actual_pace_per_km == "5:44"
    assert s.actual_avg_heart_rate == 142


def test_an_unmatched_session_gets_no_actuals():
    s = session(activity_id=None)

    attach_actuals([s], {"act-1": activity()})

    assert s.actual_distance_km is None
    assert s.actual_duration_minutes is None


def test_a_session_pointing_at_an_unknown_activity_gets_no_actuals():
    """The activity cache may not hold a run from outside the sync window."""
    s = session("act-missing")

    attach_actuals([s], {"act-1": activity()})

    assert s.actual_distance_km is None


def test_handles_an_activity_missing_its_duration():
    s = session("act-1")

    attach_actuals([s], {"act-1": activity(duration_seconds=None)})

    assert s.actual_duration_minutes is None
    assert s.actual_distance_km == 8.2
