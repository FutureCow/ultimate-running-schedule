"""
Garmin Connect integration service.
Handles credential encryption, activity fetch, and workout push.
"""
import json
import asyncio
import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from garminconnect import Garmin
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.models.garmin import GarminCredential
from app.models.plan import WorkoutSession, WorkoutType


def _fernet() -> Fernet:
    key = settings.GARMIN_ENCRYPTION_KEY.encode()
    return Fernet(key)


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


async def save_credentials(db: AsyncSession, user_id: int, email: str, password: str) -> GarminCredential:
    result = await db.execute(select(GarminCredential).where(GarminCredential.user_id == user_id))
    cred = result.scalar_one_or_none()

    enc_email = encrypt(email)
    enc_pass = encrypt(password)

    if cred:
        cred.encrypted_email = enc_email
        cred.encrypted_password = enc_pass
        cred.encrypted_tokens = None
    else:
        cred = GarminCredential(
            user_id=user_id,
            encrypted_email=enc_email,
            encrypted_password=enc_pass,
        )
        db.add(cred)

    await db.commit()
    await db.refresh(cred)
    return cred


async def get_credentials(db: AsyncSession, user_id: int) -> Optional[GarminCredential]:
    result = await db.execute(select(GarminCredential).where(GarminCredential.user_id == user_id))
    return result.scalar_one_or_none()


def _build_client(cred: GarminCredential) -> Garmin:
    email = decrypt(cred.encrypted_email)
    password = decrypt(cred.encrypted_password)
    client = Garmin(email=email, password=password)
    return client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _login_sync(client: Garmin) -> None:
    client.login()


def _fetch_activities_sync(client: Garmin, start: date, end: date) -> list[dict]:
    activities = []
    limit = 100
    offset = 0
    while True:
        batch = client.get_activities(offset, limit)
        if not batch:
            break
        for act in batch:
            try:
                act_date = datetime.fromisoformat(
                    act.get("startTimeLocal", "1970-01-01T00:00:00")
                ).date()
                if act_date < start:
                    return activities
                if act_date <= end:
                    activities.append(act)
            except Exception:
                continue
        offset += limit
        if len(batch) < limit:
            break
    return activities


def _parse_activity(act: dict) -> dict:
    """Normalize a Garmin activity dict to our schema."""
    dist_m = act.get("distance", 0) or 0
    dist_km = round(dist_m / 1000, 2)
    duration_sec = int(act.get("duration", 0) or 0)
    avg_speed = act.get("averageSpeed", 0) or 0  # m/s

    pace_str = None
    if avg_speed and avg_speed > 0:
        pace_sec = 1000 / avg_speed  # seconds per km
        mins = int(pace_sec // 60)
        secs = int(pace_sec % 60)
        pace_str = f"{mins}:{secs:02d}"

    return {
        "activity_id": str(act.get("activityId", "")),
        "activity_name": act.get("activityName", ""),
        "start_time": act.get("startTimeLocal", ""),
        "distance_km": dist_km,
        "duration_seconds": duration_sec,
        "average_pace_per_km": pace_str,
        "average_heart_rate": act.get("averageHR"),
        "max_heart_rate": act.get("maxHR"),
        "average_cadence": act.get("averageRunningCadenceInStepsPerMinute"),
        "elevation_gain_m": act.get("elevationGain"),
        "activity_type": act.get("activityType", {}).get("typeKey", "running"),
    }


async def fetch_activities(db: AsyncSession, user_id: int, months: int = 3) -> dict:
    cred = await get_credentials(db, user_id)
    if not cred:
        raise ValueError("No Garmin credentials found. Please add them first.")

    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    def _run():
        client = _build_client(cred)
        _login_sync(client)
        raw = _fetch_activities_sync(client, start_date, end_date)
        return [_parse_activity(a) for a in raw if a.get("activityType", {}).get("typeKey", "").lower() in ("running", "trail_running", "treadmill_running")]

    loop = asyncio.get_event_loop()
    activities = await loop.run_in_executor(None, _run)

    # Update last_sync_at
    cred.last_sync_at = datetime.now(timezone.utc)
    await db.commit()

    # Summarize for AI context
    total_km = sum(a["distance_km"] for a in activities)
    avg_paces = [a["average_pace_per_km"] for a in activities if a["average_pace_per_km"]]
    weekly_km = total_km / (months * 4.3) if activities else 0

    return {
        "activities": activities,
        "summary": {
            "total_runs": len(activities),
            "total_km": round(total_km, 1),
            "avg_weekly_km": round(weekly_km, 1),
            "avg_pace_per_km": avg_paces[0] if avg_paces else None,
            "date_range": {"from": start_date.isoformat(), "to": end_date.isoformat()},
        },
    }


# ── Workout push to Garmin Connect ────────────────────────────────────────────

def _pace_to_speed(pace_str: str) -> float:
    """Convert 'M:SS' pace string to m/s."""
    parts = pace_str.split(":")
    total_sec = int(parts[0]) * 60 + int(parts[1])
    return round(1000 / total_sec, 4)  # m/s


def _build_garmin_workout(session: WorkoutSession) -> dict:
    """Build a Garmin Connect workout payload from a WorkoutSession."""
    steps = []
    step_order = 1

    def _make_step(step_type: str, description: str, end_condition: str,
                   end_value, target_type: str = "no.target",
                   target_low=None, target_high=None) -> dict:
        step = {
            "type": "ExecutableStepDTO",
            "stepId": None,
            "stepOrder": step_order,
            "stepType": {"stepTypeId": 1 if step_type == "warmup" else (2 if step_type == "cooldown" else 3),
                         "stepTypeKey": step_type},
            "description": description,
            "endCondition": {"conditionTypeKey": end_condition, "conditionTypeId": 3 if end_condition == "distance" else 2},
            "endConditionValue": end_value,
            "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": target_type},
        }
        if target_low and target_high:
            step["targetValueOne"] = target_low
            step["targetValueTwo"] = target_high
        return step

    paces = session.target_paces or {}
    wtype = session.workout_type

    if wtype == WorkoutType.INTERVAL and session.intervals:
        # Warmup
        if paces.get("warmup"):
            steps.append(_make_step("warmup", "Easy warmup jog", "distance", 2000))
            step_order += 1

        # Repeat block
        for iv in session.intervals:
            reps = iv.get("reps", 1)
            pace = iv.get("pace", "")
            dist = iv.get("distance_m", 400)
            rest_sec = iv.get("rest_seconds", 90)

            for _ in range(reps):
                steps.append({
                    "type": "ExecutableStepDTO",
                    "stepOrder": step_order,
                    "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
                    "description": f"Fast interval @ {pace}/km",
                    "endCondition": {"conditionTypeKey": "distance", "conditionTypeId": 3},
                    "endConditionValue": dist,
                    "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
                })
                step_order += 1
                steps.append({
                    "type": "ExecutableStepDTO",
                    "stepOrder": step_order,
                    "stepType": {"stepTypeId": 5, "stepTypeKey": "recovery"},
                    "description": "Recovery",
                    "endCondition": {"conditionTypeKey": "time", "conditionTypeId": 2},
                    "endConditionValue": rest_sec,
                    "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
                })
                step_order += 1

        # Cooldown
        if paces.get("cooldown"):
            steps.append(_make_step("cooldown", "Easy cooldown jog", "distance", 1000))
    else:
        dist_m = int((session.distance_km or 5) * 1000)
        main_pace = paces.get("main", "6:00")

        if paces.get("warmup"):
            steps.append(_make_step("warmup", "Easy warmup", "distance", 1000))
            step_order += 1

        steps.append({
            "type": "ExecutableStepDTO",
            "stepOrder": step_order,
            "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
            "description": f"Run @ {main_pace}/km",
            "endCondition": {"conditionTypeKey": "distance", "conditionTypeId": 3},
            "endConditionValue": dist_m,
            "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
        })
        step_order += 1

        if paces.get("cooldown"):
            steps.append(_make_step("cooldown", "Easy cooldown", "distance", 1000))

    sport_type_map = {
        WorkoutType.INTERVAL: {"sportTypeId": 1, "sportTypeKey": "running"},
        WorkoutType.LONG_RUN: {"sportTypeId": 1, "sportTypeKey": "running"},
        WorkoutType.TEMPO: {"sportTypeId": 1, "sportTypeKey": "running"},
        WorkoutType.EASY_RUN: {"sportTypeId": 1, "sportTypeKey": "running"},
        WorkoutType.RECOVERY: {"sportTypeId": 1, "sportTypeKey": "running"},
    }

    return {
        "sportType": sport_type_map.get(session.workout_type, {"sportTypeId": 1, "sportTypeKey": "running"}),
        "workoutName": session.title,
        "description": session.description or "",
        "workoutSegments": [{"segmentOrder": 1, "sportType": {"sportTypeId": 1, "sportTypeKey": "running"}, "workoutSteps": steps}],
    }


def _schedule_workout(client: Garmin, workout_id: str, schedule_date: "date") -> dict:
    """Schedule a workout on the Garmin Connect calendar for a specific date.

    The garminconnect library does not yet expose this endpoint directly,
    so we call it via the underlying garth session.
    """
    path = f"/workout-service/schedule/{workout_id}"
    body = {"date": schedule_date.isoformat()}
    # garminconnect uses garth under the hood; garth.connectapi does POST/PUT/etc.
    return client.garth.connectapi(path, method="POST", json=body)


async def push_sessions_to_garmin(db: AsyncSession, user_id: int, sessions: list[WorkoutSession]) -> list[dict]:
    """Push workout sessions to Garmin Connect and schedule them on the calendar."""
    cred = await get_credentials(db, user_id)
    if not cred:
        raise ValueError("No Garmin credentials found.")

    def _run():
        client = _build_client(cred)
        try:
            _login_sync(client)
        except Exception as login_err:
            logger.error("Garmin login failed: %s", login_err, exc_info=True)
            raise RuntimeError(f"Garmin login mislukt: {login_err}") from login_err
        pushed = []
        for session in sessions:
            if session.workout_type == WorkoutType.REST:
                pushed.append({"session_id": session.id, "skipped": True, "reason": "rest day"})
                continue
            try:
                # 1. Create workout in the Garmin library
                payload = _build_garmin_workout(session)
                logger.info("Pushing session %s (%s) to Garmin", session.id, session.title)
                resp = client.add_workout(payload)
                workout_id = str(resp.get("workoutId", ""))
                logger.info("Garmin workout created: %s", workout_id)

                # 2. Schedule it on the calendar if we have a date
                schedule_id = None
                if session.scheduled_date and workout_id:
                    try:
                        sched_resp = _schedule_workout(client, workout_id, session.scheduled_date)
                        schedule_id = str(sched_resp.get("workoutScheduleId", ""))
                        logger.info("Scheduled on %s (schedule_id=%s)", session.scheduled_date, schedule_id)
                    except Exception as sched_err:
                        # Scheduling failed but workout was created — not fatal
                        logger.warning("Schedule failed for workout %s: %s", workout_id, sched_err)

                pushed.append({
                    "session_id": session.id,
                    "garmin_workout_id": workout_id,
                    "garmin_schedule_id": schedule_id,
                    "success": True,
                })
            except Exception as e:
                logger.error("Push failed for session %s: %s", session.id, e, exc_info=True)
                pushed.append({"session_id": session.id, "success": False, "error": str(e)})
        return pushed

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, _run)

    # Persist Garmin IDs
    now = datetime.now(timezone.utc)
    for r in results:
        if r.get("success"):
            for s in sessions:
                if s.id == r["session_id"]:
                    s.garmin_workout_id = r["garmin_workout_id"]
                    s.garmin_pushed_at = now
    await db.commit()
    return results
