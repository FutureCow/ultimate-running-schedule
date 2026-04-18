"""
Garmin Connect integration service — compatible with python-garminconnect 0.3.2.

Authentication uses the mobile SSO flow (DI OAuth Bearer tokens).
Tokens are stored as garmin_tokens.json in a per-user temp directory,
then the file contents are encrypted and persisted in the database.
"""
import json
import asyncio
import logging
import tempfile
import os
from datetime import datetime, date, timedelta, timezone
from typing import Optional
from pathlib import Path
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

from app.config import settings
from app.models.garmin import GarminCredential
from app.models.plan import WorkoutSession, WorkoutType

logger = logging.getLogger(__name__)

TOKEN_FILENAME = "garmin_tokens.json"


# ── Encryption helpers ────────────────────────────────────────────────────────

def _fernet() -> Fernet:
    return Fernet(settings.GARMIN_ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


# ── Token file helpers ────────────────────────────────────────────────────────

def _write_token_dir(cred: GarminCredential) -> str:
    """Write decrypted token JSON to a temp dir; return the dir path."""
    tmp = tempfile.mkdtemp(prefix=f"garmin_{cred.user_id}_")
    if cred.encrypted_tokens:
        token_json = decrypt(cred.encrypted_tokens)
        Path(tmp, TOKEN_FILENAME).write_text(token_json)
        logger.debug("Restored Garmin tokens for user %s", cred.user_id)
    return tmp


def _read_token_dir(token_dir: str) -> Optional[str]:
    """Read token file from dir and return encrypted string (or None)."""
    token_path = Path(token_dir, TOKEN_FILENAME)
    if token_path.exists():
        return encrypt(token_path.read_text())
    return None


def _cleanup_token_dir(token_dir: str) -> None:
    import shutil
    try:
        shutil.rmtree(token_dir, ignore_errors=True)
    except Exception:
        pass


# ── Credential CRUD ───────────────────────────────────────────────────────────

async def save_credentials(db: AsyncSession, user_id: int, email: str, password: str) -> GarminCredential:
    result = await db.execute(select(GarminCredential).where(GarminCredential.user_id == user_id))
    cred = result.scalar_one_or_none()
    enc_email = encrypt(email)
    enc_pass = encrypt(password)
    if cred:
        cred.encrypted_email = enc_email
        cred.encrypted_password = enc_pass
        cred.encrypted_tokens = None  # force re-login with new credentials
    else:
        cred = GarminCredential(user_id=user_id, encrypted_email=enc_email, encrypted_password=enc_pass)
        db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return cred


async def get_credentials(db: AsyncSession, user_id: int) -> Optional[GarminCredential]:
    result = await db.execute(select(GarminCredential).where(GarminCredential.user_id == user_id))
    return result.scalar_one_or_none()


# ── Login helper ──────────────────────────────────────────────────────────────

def _login(cred: GarminCredential, token_dir: str) -> Garmin:
    """
    Login strategy:
    1. If tokens exist in token_dir → restore them (no SSO)
    2. If no tokens → full credential login and save to token_dir
    """
    email = decrypt(cred.encrypted_email)
    password = decrypt(cred.encrypted_password)

    if Path(token_dir, TOKEN_FILENAME).exists():
        # Restore from token file — no SSO needed
        logger.info("Garmin: restoring tokens from cache (user %s)", cred.user_id)
        client = Garmin()
        client.login(token_dir)
    else:
        # First-time or expired — full SSO login
        logger.info("Garmin: performing full SSO login for user %s", cred.user_id)
        client = Garmin(
            email=email,
            password=password,
            prompt_mfa=None,  # MFA not supported in headless mode
        )
        client.login(token_dir)
        logger.info("Garmin: login successful, tokens saved")

    return client


# ── Activity fetch ────────────────────────────────────────────────────────────

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
                act_date = datetime.fromisoformat(act.get("startTimeLocal", "1970-01-01T00:00:00")).date()
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
    dist_m = act.get("distance", 0) or 0
    dist_km = round(dist_m / 1000, 2)
    duration_sec = int(act.get("duration", 0) or 0)
    avg_speed = act.get("averageSpeed", 0) or 0
    pace_str = None
    if avg_speed > 0:
        pace_sec = 1000 / avg_speed
        mins, secs = int(pace_sec // 60), int(pace_sec % 60)
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
        raise ValueError("Geen Garmin credentials gevonden. Sla ze eerst op.")

    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)
    token_dir = _write_token_dir(cred)
    new_token_data: list[str] = []

    def _run():
        try:
            client = _login(cred, token_dir)
            raw = _fetch_activities_sync(client, start_date, end_date)
            enc = _read_token_dir(token_dir)
            if enc:
                new_token_data.append(enc)
            return [
                _parse_activity(a) for a in raw
                if a.get("activityType", {}).get("typeKey", "").lower()
                in ("running", "trail_running", "treadmill_running")
            ]
        finally:
            _cleanup_token_dir(token_dir)

    loop = asyncio.get_event_loop()
    try:
        activities = await loop.run_in_executor(None, _run)
    except GarminConnectTooManyRequestsError as e:
        raise RuntimeError("Garmin rate limit bereikt (429). Wacht 15 minuten.") from e
    except GarminConnectAuthenticationError as e:
        # Wipe tokens so next attempt does a fresh login
        cred.encrypted_tokens = None
        await db.commit()
        raise RuntimeError("Garmin authenticatie mislukt. Controleer je credentials.") from e

    if new_token_data:
        cred.encrypted_tokens = new_token_data[0]
    cred.last_sync_at = datetime.now(timezone.utc)
    await db.commit()

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


# ── Workout builder ───────────────────────────────────────────────────────────

_SPORT_RUNNING = {"sportTypeId": 1, "sportTypeKey": "running"}
_SPORT_STRENGTH = {"sportTypeId": 13, "sportTypeKey": "strength_training"}


def _pace_to_ms(pace_str: str) -> Optional[float]:
    """Convert a 'MM:SS' pace-per-km string to speed in m/s."""
    clean = pace_str.strip().replace("/km", "").strip()
    try:
        parts = clean.split(":")
        total_sec = int(parts[0]) * 60 + int(parts[1])
        return round(1000 / total_sec, 4) if total_sec > 0 else None
    except Exception:
        return None


_NO_TARGET = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"}
# pace.zone (typeId=6) uses the same m/s values as speed.zone (typeId=5),
# but Garmin displays them as min/km instead of km/h.
_PACE_ZONE = {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"}


def _pace_target(pace_range: Optional[str]) -> tuple[dict, Optional[float], Optional[float]]:
    """
    Parse a pace range string.
    Returns (targetType dict, targetValueOne, targetValueTwo) where:
      - targetType uses pace.zone (typeId=6) so Garmin displays min/km
      - targetValueOne = faster speed (higher m/s = lower MM:SS, e.g. 6:20)
      - targetValueTwo = slower speed (lower m/s = higher MM:SS, e.g. 6:40)
    Garmin displays them as one→two in pace: "6:20 – 6:40" ✓
    Both values go at the step level, NOT inside targetType.
    """
    if not pace_range:
        return _NO_TARGET, None, None

    pace_range = pace_range.replace("/km", "").strip()
    fast_ms = slow_ms = None

    for sep in (" – ", " - ", "–", "-"):
        if sep in pace_range:
            a, b = pace_range.split(sep, 1)
            fast_ms = _pace_to_ms(a)  # first token = faster pace (lower MM:SS = higher m/s)
            slow_ms = _pace_to_ms(b)  # second token = slower pace (higher MM:SS = lower m/s)
            break
    else:
        speed = _pace_to_ms(pace_range)
        if speed:
            margin = round(speed * 0.03, 4)
            slow_ms = round(speed - margin, 4)
            fast_ms = round(speed + margin, 4)

    if slow_ms and fast_ms and 0 < slow_ms < fast_ms:
        # one=fast, two=slow → Garmin renders as "6:20 – 6:40" (fast first in pace notation)
        return _PACE_ZONE, fast_ms, slow_ms

    return _NO_TARGET, None, None


def _step(order: int, step_type_id: int, step_type_key: str,
          end_condition: str, end_value, description: str = "",
          pace_range: Optional[str] = None) -> dict:
    """Build a single Garmin workout step dict with an optional pace target.
    targetValueOne/Two must be at the step level (not inside targetType)."""
    cond_id = 3 if end_condition == "distance" else 2  # 3=distance, 2=time
    target_type, val_one, val_two = _pace_target(pace_range)
    step: dict = {
        "type": "ExecutableStepDTO",
        "stepId": None,
        "stepOrder": order,
        "stepType": {"stepTypeId": step_type_id, "stepTypeKey": step_type_key},
        "description": description,
        "endCondition": {"conditionTypeKey": end_condition, "conditionTypeId": cond_id},
        "endConditionValue": end_value,
        "targetType": target_type,
    }
    if val_one is not None:
        step["targetValueOne"] = val_one
        step["targetValueTwo"] = val_two
    return step


def _build_workout_payload(session: WorkoutSession) -> dict:
    """Build a Garmin Connect workout dict with proper pace targets per step."""
    paces = session.target_paces or {}
    steps = []
    order = 1

    # Warmup (1 km at warmup pace)
    if paces.get("warmup"):
        steps.append(_step(order, 1, "warmup", "distance", 1000,
                           "Warming-up", pace_range=paces.get("warmup")))
        order += 1

    if session.workout_type == WorkoutType.INTERVAL and session.intervals:
        for iv in session.intervals:
            reps = iv.get("reps", 1)
            dist_m = iv.get("distance_m") or 400
            rest_sec = iv.get("rest_seconds", 90)
            iv_pace = iv.get("pace", "")
            for _ in range(reps):
                steps.append(_step(order, 3, "interval", "distance", dist_m,
                                   f"Interval {dist_m}m", pace_range=iv_pace))
                order += 1
                # Recovery: time-based, no pace target
                steps.append(_step(order, 4, "recovery", "time", rest_sec, "Rust"))
                order += 1
    else:
        dist_m = int((session.distance_km or 5) * 1000)
        steps.append(_step(order, 3, "interval", "distance", dist_m,
                           session.description or "", pace_range=paces.get("main")))
        order += 1

    # Strides (short fast accelerations stored in target_paces["strides"])
    strides = paces.get("strides")
    if strides and session.workout_type != WorkoutType.INTERVAL:
        reps = strides.get("reps", 4)
        dist_m = strides.get("distance_m", 100)
        rest_sec = strides.get("rest_seconds", 90)
        stride_pace = strides.get("pace", "")
        for i in range(reps):
            steps.append(_step(order, 3, "interval", "distance", dist_m,
                               f"Stride {i + 1}", pace_range=stride_pace))
            order += 1
            if i < reps - 1:
                steps.append(_step(order, 4, "recovery", "time", rest_sec, "Herstel"))
                order += 1

    # Cooldown (500 m at cooldown pace)
    if paces.get("cooldown"):
        steps.append(_step(order, 2, "cooldown", "distance", 500,
                           "Cooling-down", pace_range=paces.get("cooldown")))

    return {
        "sportType": _SPORT_RUNNING,
        "workoutName": session.title,
        "description": session.description or "",
        "estimatedDurationInSecs": (session.duration_minutes or 30) * 60,
        "workoutSegments": [{
            "segmentOrder": 1,
            "sportType": _SPORT_RUNNING,
            "workoutSteps": steps,
        }],
    }


# ── Workout delete ────────────────────────────────────────────────────────────

async def delete_workout_from_garmin(db: AsyncSession, user_id: int, garmin_workout_id: str) -> bool:
    """Delete a workout from Garmin Connect. Returns True on success, False on failure."""
    cred = await get_credentials(db, user_id)
    if not cred:
        logger.warning("No Garmin credentials for user %s — skipping Garmin delete", user_id)
        return False

    token_dir = _write_token_dir(cred)
    new_token_data: list[str] = []

    def _run() -> bool:
        try:
            client = _login(cred, token_dir)
            logger.info("Deleting Garmin workout %s for user %s", garmin_workout_id, user_id)
            client.delete_workout(garmin_workout_id)
            enc = _read_token_dir(token_dir)
            if enc:
                new_token_data.append(enc)
            return True
        except Exception as e:
            logger.warning("Failed to delete Garmin workout %s: %s", garmin_workout_id, e)
            return False
        finally:
            _cleanup_token_dir(token_dir)

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, _run)

    if new_token_data:
        cred.encrypted_tokens = new_token_data[0]
        await db.commit()

    return success


def _build_strength_workout_payload(session: WorkoutSession) -> dict:
    """Build a Garmin Connect strength_training workout with exercises in the description step."""
    duration_sec = (session.duration_minutes or 40) * 60
    step = {
        "type": "ExecutableStepDTO",
        "stepId": None,
        "stepOrder": 1,
        "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
        "description": session.description or "",
        "endCondition": {"conditionTypeKey": "time", "conditionTypeId": 2},
        "endConditionValue": duration_sec,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
    }
    return {
        "sportType": _SPORT_STRENGTH,
        "workoutName": session.title,
        "description": session.description or "",
        "estimatedDurationInSecs": duration_sec,
        "workoutSegments": [{
            "segmentOrder": 1,
            "sportType": _SPORT_STRENGTH,
            "workoutSteps": [step],
        }],
    }


# ── Workout push ──────────────────────────────────────────────────────────────

async def push_sessions_to_garmin(db: AsyncSession, user_id: int, sessions: list[WorkoutSession]) -> list[dict]:
    cred = await get_credentials(db, user_id)
    if not cred:
        raise ValueError("Geen Garmin credentials gevonden.")

    token_dir = _write_token_dir(cred)
    new_token_data: list[str] = []

    def _run():
        try:
            client = _login(cred, token_dir)
            pushed = []

            for session in sessions:
                if session.workout_type == WorkoutType.REST:
                    pushed.append({"session_id": session.id, "skipped": True, "reason": "rest day"})
                    continue
                try:
                    if session.workout_type == WorkoutType.STRENGTH:
                        payload = _build_strength_workout_payload(session)
                    else:
                        payload = _build_workout_payload(session)
                    logger.info("Uploading session %s: %s", session.id, session.title)
                    resp = client.upload_workout(payload)
                    workout_id = str(resp.get("workoutId", ""))
                    logger.info("Workout created: %s", workout_id)

                    schedule_id = None
                    if session.scheduled_date and workout_id:
                        try:
                            sched = client.schedule_workout(workout_id, session.scheduled_date.isoformat())
                            schedule_id = str(sched.get("workoutScheduleId", ""))
                            logger.info("Scheduled on %s (id=%s)", session.scheduled_date, schedule_id)
                        except Exception as e:
                            logger.warning("Schedule failed for %s: %s", workout_id, e)

                    pushed.append({
                        "session_id": session.id,
                        "garmin_workout_id": workout_id,
                        "garmin_schedule_id": schedule_id,
                        "success": True,
                    })
                except Exception as e:
                    logger.error("Push failed for session %s: %s", session.id, e, exc_info=True)
                    pushed.append({"session_id": session.id, "success": False, "error": str(e)})

            enc = _read_token_dir(token_dir)
            if enc:
                new_token_data.append(enc)
            return pushed
        finally:
            _cleanup_token_dir(token_dir)

    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(None, _run)
    except GarminConnectTooManyRequestsError as e:
        raise RuntimeError("Garmin rate limit (429). Wacht 15 minuten.") from e
    except GarminConnectAuthenticationError as e:
        cred.encrypted_tokens = None
        await db.commit()
        raise RuntimeError("Garmin authenticatie mislukt.") from e

    if new_token_data:
        cred.encrypted_tokens = new_token_data[0]
    now = datetime.now(timezone.utc)
    for r in results:
        if r.get("success"):
            for s in sessions:
                if s.id == r["session_id"]:
                    s.garmin_workout_id = r["garmin_workout_id"]
                    s.garmin_pushed_at = now
    await db.commit()
    return results
