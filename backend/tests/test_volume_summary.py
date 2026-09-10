"""Tests for weekly volume: a stable baseline plus what the athlete is doing now.

A three-month average lags badly — someone building from 15 to 30 km a week
still reads as 20 for months. The recent figure is what the profile shows and
the difference between the two is what tells a coach a build-up is happening.
"""
from datetime import date, timedelta

from app.services.garmin_service import _volume_summary

TODAY = date(2026, 9, 10)


def run(days_ago: int, km: float) -> dict:
    return {
        "start_time": (TODAY - timedelta(days=days_ago)).isoformat() + " 07:30:00",
        "distance_km": km,
    }


def summary(*activities: dict, months: int = 3) -> dict:
    return _volume_summary(list(activities), months=months, today=TODAY)


# ── Baseline over the whole window ───────────────────────────────────────────

def test_averages_the_whole_window_into_weekly_kilometres():
    """13 runs of 10 km spread over the 12.9-week window is 10.1 km a week."""
    result = summary(*[run(days_ago=d, km=10.0) for d in range(0, 90, 7)])

    assert result["avg_weekly_km"] == 10.1


def test_counts_runs_per_week_too():
    """weekly_runs was never derived from Garmin at all."""
    result = summary(*[run(days_ago=d, km=5.0) for d in range(0, 90, 7)])

    assert result["avg_weekly_runs"] == 1.0


# ── Recent form ──────────────────────────────────────────────────────────────

def test_recent_form_covers_the_last_four_weeks():
    """Four weeks of 30 km reads as 30, even with a quiet quarter behind it."""
    recent = [run(days_ago=d, km=10.0) for d in (1, 3, 5, 8, 10, 12, 15, 17, 19, 22, 24, 26)]

    assert summary(*recent)["recent_weekly_km"] == 30.0


def test_older_runs_do_not_count_as_recent_form():
    result = summary(run(days_ago=60, km=100.0))

    assert result["recent_weekly_km"] == 0.0
    assert result["avg_weekly_km"] > 0


def test_a_build_up_shows_as_a_gap_between_the_two():
    """The whole point: recent well above baseline means volume is rising."""
    quiet = [run(days_ago=d, km=5.0) for d in range(30, 90, 7)]
    ramping = [run(days_ago=d, km=10.0) for d in (2, 5, 9, 12, 16, 19, 23, 26)]

    result = summary(*quiet, *ramping)

    assert result["recent_weekly_km"] > result["avg_weekly_km"]


def test_counts_recent_runs_per_week():
    recent = [run(days_ago=d, km=8.0) for d in (2, 5, 9, 12, 16, 19, 23, 26)]

    assert summary(*recent)["recent_weekly_runs"] == 2.0


# ── Nothing to go on ─────────────────────────────────────────────────────────

def test_no_activities_yields_zeros():
    result = summary()

    assert result == {
        "avg_weekly_km": 0.0,
        "avg_weekly_runs": 0.0,
        "recent_weekly_km": 0.0,
        "recent_weekly_runs": 0.0,
    }


def test_an_unparseable_date_is_skipped_rather_than_crashing():
    result = summary({"start_time": "", "distance_km": 10.0}, run(days_ago=2, km=10.0))

    assert result["recent_weekly_km"] == 2.5


def test_a_missing_distance_counts_as_a_run_but_no_kilometres():
    result = summary({"start_time": (TODAY - timedelta(days=2)).isoformat(), "distance_km": None})

    assert result["recent_weekly_km"] == 0.0
    assert result["recent_weekly_runs"] == 0.25
