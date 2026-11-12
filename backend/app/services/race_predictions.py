"""Estimated race times from the athlete's best recent effort.

Garmin and Strava show predicted 5K/10K/HM/M times; this is Metriq's own, by
Jack Daniels' VDOT, the method the plans are built on. Only whole activities
are stored, so the warm-up of an interval session drags it down: the estimate
leans on races, time trials and tempo runs, and says which one it used.
"""
import math
from datetime import datetime, timedelta, timezone

WINDOW = timedelta(weeks=12)
MIN_KM = 3.0
# Faster than this over 3 km or more is a GPS error, not a run
MAX_VDOT = 85.0

# Outdoor running: a treadmill's distance is only as good as its calibration
RUNNING_TYPES = {"running", "street_running", "track_running", "trail_running", "ultra_run"}

DISTANCES = [
    ("5k", 5.0),
    ("10k", 10.0),
    ("half_marathon", 21.0975),
    ("marathon", 42.195),
]


def vdot(distance_km: float, seconds: float) -> float:
    """Daniels & Gilbert: oxygen cost of the speed over the share of VO2max held that long."""
    minutes = seconds / 60
    speed = distance_km * 1000 / minutes  # metres per minute
    cost = -4.60 + 0.182258 * speed + 0.000104 * speed ** 2
    share = (0.8 + 0.1894393 * math.exp(-0.012778 * minutes)
             + 0.2989558 * math.exp(-0.1932605 * minutes))
    return cost / share


def seconds_for(target_vdot: float, distance_km: float) -> int:
    """The time over distance_km that a VDOT stands for. VDOT falls as time grows."""
    low, high = distance_km * 60.0, distance_km * 1200.0  # 1:00 to 20:00 per km
    for _ in range(60):
        mid = (low + high) / 2
        if vdot(distance_km, mid) > target_vdot:
            low = mid
        else:
            high = mid
    return round((low + high) / 2)


def _usable(act, since: datetime) -> bool:
    return bool(
        act.distance_km and act.distance_km >= MIN_KM
        and act.duration_seconds and act.duration_seconds > 0
        and (act.activity_type or "running") in RUNNING_TYPES
        and act.start_time and act.start_time >= since
    )


def predict_race_times(activities, now: datetime | None = None) -> dict | None:
    """Times over the standard distances from the best effort of the last 12 weeks.

    None when there is no usable run: no estimate is better than an invented one.
    """
    now = now or datetime.now(timezone.utc)
    since = now - WINDOW
    best, best_vdot = None, 0.0
    for act in activities:
        if not _usable(act, since):
            continue
        v = vdot(act.distance_km, act.duration_seconds)
        if best_vdot < v <= MAX_VDOT:
            best, best_vdot = act, v
    if best is None:
        return None

    return {
        "vdot": round(best_vdot, 1),
        "basis": {
            "activity_id": best.activity_id,
            "name": best.activity_name or "",
            "date": best.start_time.date().isoformat(),
            "distance_km": round(best.distance_km, 2),
            "duration_seconds": best.duration_seconds,
        },
        "predictions": [
            {"key": key, "distance_km": km, "seconds": seconds_for(best_vdot, km)}
            for key, km in DISTANCES
        ],
    }
