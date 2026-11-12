"""Tests for the estimated race times on the analysis page.

Garmin and Strava show predicted 5K/10K/HM/M times. Metriq gives its own, by
Jack Daniels' VDOT — the method the plans use — from the best recent effort,
and always says which activity the estimate rests on.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.race_predictions import predict_race_times, seconds_for, vdot

NOW = datetime(2026, 11, 30, 12, 0, tzinfo=timezone.utc)


def act(km, seconds, days_ago=3, kind="running", name="Run", activity_id=None):
    return SimpleNamespace(
        activity_id=activity_id or f"{km}-{seconds}-{days_ago}",
        activity_name=name, activity_type=kind, distance_km=km,
        duration_seconds=seconds, start_time=NOW - timedelta(days=days_ago),
    )


def by_key(result):
    return {p["key"]: p["seconds"] for p in result["predictions"]}


# ── The VDOT formula against Daniels' published table ────────────────────────

def test_vdot_of_a_table_5k():
    # Daniels' table: VDOT 50 runs a 5K in 19:57
    assert abs(vdot(5.0, 19 * 60 + 57) - 50) < 0.3


def test_time_for_vdot_50_matches_the_table():
    assert abs(seconds_for(50, 10.0) - (41 * 60 + 21)) < 15
    assert abs(seconds_for(50, 21.0975) - (1 * 3600 + 31 * 60 + 35)) < 40
    assert abs(seconds_for(50, 42.195) - (3 * 3600 + 10 * 60 + 49)) < 90


def test_a_result_predicts_itself():
    v = vdot(8.0, 48 * 60)
    assert abs(seconds_for(v, 8.0) - 48 * 60) <= 1


# ── Choosing the basis ───────────────────────────────────────────────────────

def test_best_effort_is_the_basis():
    easy = act(10.0, 70 * 60, name="Easy")
    race = act(8.0, 48 * 60, name="8K wedstrijd", activity_id="race")
    result = predict_race_times([easy, race], now=NOW)
    assert result["basis"]["activity_id"] == "race"
    assert result["basis"]["name"] == "8K wedstrijd"
    assert result["basis"]["distance_km"] == 8.0
    assert result["basis"]["duration_seconds"] == 48 * 60
    # 8K in 48:00 is about a 29:10 5K and a 60:50 10K
    times = by_key(result)
    assert abs(times["5k"] - (29 * 60 + 10)) < 30
    assert abs(times["10k"] - (60 * 60 + 50)) < 60
    assert times["5k"] < times["10k"] < times["half_marathon"] < times["marathon"]


def test_older_than_twelve_weeks_does_not_count():
    old = act(5.0, 22 * 60, days_ago=12 * 7 + 1)
    assert predict_race_times([old], now=NOW) is None


def test_shorter_than_three_km_does_not_count():
    short = act(2.0, 8 * 60)
    recent = act(5.0, 30 * 60)
    result = predict_race_times([short, recent], now=NOW)
    assert result["basis"]["distance_km"] == 5.0


def test_only_running_activities_count():
    ride = act(30.0, 60 * 60, kind="cycling")
    treadmill = act(5.0, 18 * 60, kind="treadmill_running")
    trail = act(6.0, 40 * 60, kind="trail_running", activity_id="trail")
    result = predict_race_times([ride, treadmill, trail], now=NOW)
    assert result["basis"]["activity_id"] == "trail"


def test_implausible_pace_is_a_gps_error():
    # 10 km in 20 minutes is faster than the world record
    glitch = act(10.0, 20 * 60)
    real = act(5.0, 28 * 60, activity_id="real")
    assert predict_race_times([glitch, real], now=NOW)["basis"]["activity_id"] == "real"


def test_no_usable_activity_gives_nothing():
    assert predict_race_times([], now=NOW) is None
    missing = SimpleNamespace(activity_id="x", activity_name=None, activity_type="running",
                              distance_km=None, duration_seconds=None, start_time=NOW)
    assert predict_race_times([missing], now=NOW) is None


def test_result_carries_the_date_and_vdot():
    result = predict_race_times([act(5.0, 25 * 60, days_ago=10)], now=NOW)
    assert result["basis"]["date"] == (NOW - timedelta(days=10)).date().isoformat()
    assert 35 < result["vdot"] < 45
