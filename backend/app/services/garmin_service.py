"""
Garmin Connect integration service — compatible with python-garminconnect 0.3.2.

Authentication uses the mobile SSO flow (DI OAuth Bearer tokens).
Tokens are stored as garmin_tokens.json in a per-user temp directory,
then the file contents are encrypted and persisted in the database.

2FA/MFA flow:
  save_credentials() attempts login with return_on_mfa=True.
  If MFA is required, the Garmin client instance is held in _MFA_PENDING (in-memory, 5 min TTL).
  complete_mfa() retrieves the client, calls resume_login(), then saves tokens to DB.
"""
import json
import asyncio
import logging
import tempfile
import os
import time as _time
from datetime import datetime, date, timedelta, timezone
from typing import Optional
from pathlib import Path
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

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

# In-memory MFA state: user_id → (garmin_client, expiry_timestamp)
# Valid for 5 minutes after initial login attempt triggers MFA.
_MFA_PENDING: dict[int, tuple] = {}
_MFA_TTL = 300


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

async def save_credentials(db: AsyncSession, user_id: int, email: str, password: str) -> dict:
    """Save credentials and attempt an initial login to detect 2FA.

    Returns:
        {"needs_mfa": False, "cred": GarminCredential}  — login succeeded
        {"needs_mfa": True,  "cred": GarminCredential}  — MFA code required; call complete_mfa()
    """
    result = await db.execute(select(GarminCredential).where(GarminCredential.user_id == user_id))
    cred = result.scalar_one_or_none()
    enc_email = encrypt(email)
    enc_pass = encrypt(password)
    if cred:
        cred.encrypted_email = enc_email
        cred.encrypted_password = enc_pass
        cred.encrypted_tokens = None
    else:
        cred = GarminCredential(user_id=user_id, encrypted_email=enc_email, encrypted_password=enc_pass)
        db.add(cred)
    await db.commit()
    await db.refresh(cred)

    # Attempt login to detect 2FA and pre-cache tokens
    token_dir = tempfile.mkdtemp(prefix=f"garmin_{user_id}_")
    new_token_data: list[str] = []
    mfa_client_holder: list[Garmin] = []

    def _run():
        try:
            client = Garmin(email=email, password=password, return_on_mfa=True)
            status, _ = client.login(token_dir)
            if status == "needs_mfa":
                mfa_client_holder.append(client)
                return "needs_mfa"
            enc = _read_token_dir(token_dir)
            if enc:
                new_token_data.append(enc)
            return "ok"
        finally:
            if not mfa_client_holder:
                _cleanup_token_dir(token_dir)

    loop = asyncio.get_event_loop()
    try:
        outcome = await loop.run_in_executor(None, _run)
    except GarminConnectTooManyRequestsError as e:
        _cleanup_token_dir(token_dir)
        raise RuntimeError("Garmin rate limit bereikt (429). Wacht 15 minuten.") from e
    except GarminConnectAuthenticationError as e:
        _cleanup_token_dir(token_dir)
        raise RuntimeError("Garmin authenticatie mislukt. Controleer je e-mailadres en wachtwoord.") from e

    if outcome == "needs_mfa":
        _MFA_PENDING[user_id] = (mfa_client_holder[0], token_dir, _time.monotonic() + _MFA_TTL)
        logger.info("Garmin MFA required for user %s — pending code submission", user_id)
        return {"needs_mfa": True, "cred": cred}

    if new_token_data:
        cred.encrypted_tokens = new_token_data[0]
    cred.last_sync_at = datetime.now(timezone.utc)
    await db.commit()
    return {"needs_mfa": False, "cred": cred}


async def complete_mfa(db: AsyncSession, user_id: int, mfa_code: str) -> GarminCredential:
    """Complete a pending 2FA login by submitting the MFA code."""
    entry = _MFA_PENDING.pop(user_id, None)
    if entry is None:
        raise ValueError("Geen actieve MFA-sessie. Probeer opnieuw te koppelen.")

    garmin_client, token_dir, expiry = entry
    if _time.monotonic() > expiry:
        _cleanup_token_dir(token_dir)
        raise ValueError("MFA-sessie verlopen (5 minuten). Probeer opnieuw te koppelen.")

    new_token_data: list[str] = []

    def _run():
        try:
            garmin_client.resume_login(None, mfa_code)
            # Tokens are now in memory on garmin_client.client — serialize directly
            token_json = garmin_client.client.dumps()
            new_token_data.append(encrypt(token_json))
        except GarminConnectAuthenticationError as e:
            raise RuntimeError(f"MFA-code onjuist of verlopen: {e}") from e
        finally:
            _cleanup_token_dir(token_dir)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run)

    cred = await get_credentials(db, user_id)
    if not cred:
        raise ValueError("Garmin credentials niet gevonden.")

    if new_token_data:
        cred.encrypted_tokens = new_token_data[0]
    cred.last_sync_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(cred)
    logger.info("Garmin MFA completed successfully for user %s", user_id)
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


async def fetch_activities(db: AsyncSession, user_id: int, months: int = 3, user_tier: str = "elite") -> dict:
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

    # Match activities to planned WorkoutSessions by date
    matched = await _match_activities_to_sessions(db, user_id, activities, user_tier=user_tier)

    return {
        "activities": activities,
        "summary": {
            "total_runs": len(activities),
            "total_km": round(total_km, 1),
            "avg_weekly_km": round(weekly_km, 1),
            "avg_pace_per_km": avg_paces[0] if avg_paces else None,
            "date_range": {"from": start_date.isoformat(), "to": end_date.isoformat()},
            "matched_sessions": matched,
        },
    }


async def _match_activities_to_sessions(db: AsyncSession, user_id: int, activities: list[dict], user_tier: str = "elite") -> int:
    """Mark WorkoutSessions as completed when a Garmin activity falls on the same date."""
    from app.models.plan import Plan, WorkoutSession

    # Build date → activity map (keep the largest distance per date)
    date_to_activity: dict[date, dict] = {}
    for act in activities:
        start_str = act.get("start_time", "")
        if not start_str:
            continue
        try:
            act_date = date.fromisoformat(start_str[:10])
        except ValueError:
            continue
        existing = date_to_activity.get(act_date)
        if existing is None or act["distance_km"] > existing["distance_km"]:
            date_to_activity[act_date] = act

    if not date_to_activity:
        return 0

    # Fetch unmatched running sessions belonging to user's plans
    from sqlalchemy import Date as SADate
    result = await db.execute(
        select(WorkoutSession)
        .join(WorkoutSession.plan)
        .where(
            Plan.user_id == user_id,
            WorkoutSession.scheduled_date.isnot(None),
            WorkoutSession.workout_type.notin_(["rest"]),
            WorkoutSession.completed_at.is_(None),
        )
    )
    sessions = result.scalars().all()

    matched = 0
    now = datetime.now(timezone.utc)
    newly_matched: list[tuple] = []  # (session, activity_dict)
    for session in sessions:
        act = date_to_activity.get(session.scheduled_date)
        if act:
            session.completed_at = now
            session.garmin_activity_id = act["activity_id"]
            matched += 1
            newly_matched.append((session, act))

    if matched:
        await db.commit()

    # AI feedback is generated lazily in the activity detail endpoint
    # using full stream data (HR, cadence, pace, altitude) for better quality.

    return matched


# ── Activity detail ──────────────────────────────────────────────────────────

async def fetch_activity_detail(db: AsyncSession, user_id: int, activity_id: str) -> dict:
    """Fetch detailed activity data: GPS track, HR, cadence, pace, altitude streams."""
    cred = await get_credentials(db, user_id)
    if not cred:
        raise ValueError("Geen Garmin credentials gevonden.")

    token_dir = _write_token_dir(cred)
    new_token_data: list[str] = []
    result_holder: list[dict] = []

    def _run():
        try:
            client = _login(cred, token_dir)
            summary = client.get_activity(activity_id)
            details = client.get_activity_details(activity_id, maxchart=2000, maxpoly=4000)
            enc = _read_token_dir(token_dir)
            if enc:
                new_token_data.append(enc)
            result_holder.append({"summary": summary, "details": details})
        finally:
            _cleanup_token_dir(token_dir)

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _run)
    except GarminConnectTooManyRequestsError as e:
        raise RuntimeError("Garmin rate limit (429). Wacht 15 minuten.") from e
    except GarminConnectAuthenticationError as e:
        cred.encrypted_tokens = None
        await db.commit()
        raise RuntimeError("Garmin authenticatie mislukt.") from e

    if new_token_data:
        cred.encrypted_tokens = new_token_data[0]
        await db.commit()

    if not result_holder:
        raise RuntimeError("Geen data ontvangen van Garmin.")

    summary_raw = result_holder[0]["summary"]
    details = result_holder[0]["details"]

    # --- GPS track ---
    gps_track = []
    geo = details.get("geoPolylineDTO") or {}
    for pt in (geo.get("polyline") or []):
        lat, lon = pt.get("lat"), pt.get("lon")
        if lat is not None and lon is not None:
            gps_track.append({"lat": lat, "lon": lon, "altitude": pt.get("altitude")})

    # --- Metric streams ---
    descriptors = details.get("metricDescriptors") or []
    metrics_data = details.get("activityDetailMetrics") or []

    key_to_idx: dict[str, int] = {}
    for d in descriptors:
        k = d.get("key", "")
        if k in ("directTimestamp", "directSpeed", "directHeartRate",
                 "directCadence", "directRunCadence",
                 "directAltitude", "directElevation"):
            idx = d.get("metricsIndex")
            if idx is not None:
                key_to_idx[k] = int(idx)

    def _val(m: list, key: str):
        i = key_to_idx.get(key)
        if i is None or i >= len(m):
            return None
        v = m[i]
        if v is None:
            return None
        if isinstance(v, float) and v != v:  # NaN
            return None
        return v

    time_s: list = []
    pace_vals: list = []
    hr_vals: list = []
    cadence_vals: list = []
    altitude_vals: list = []

    start_ts_ms: Optional[float] = None
    if metrics_data and "directTimestamp" in key_to_idx:
        first_m = (metrics_data[0].get("metrics") or []) if isinstance(metrics_data[0], dict) else []
        t0 = _val(first_m, "directTimestamp")
        if t0 is not None:
            start_ts_ms = float(t0)

    for point in metrics_data:
        m = point.get("metrics", []) if isinstance(point, dict) else []

        ts = _val(m, "directTimestamp")
        if ts is not None and start_ts_ms is not None:
            time_s.append(round((float(ts) - start_ts_ms) / 1000))
        else:
            time_s.append(len(time_s))

        speed = _val(m, "directSpeed")
        if speed and float(speed) > 0.5:
            pace_vals.append(round(1000 / float(speed), 1))
        else:
            pace_vals.append(None)

        hr = _val(m, "directHeartRate")
        hr_vals.append(int(hr) if hr is not None else None)

        cad = _val(m, "directRunCadence") or _val(m, "directCadence")
        # Garmin stores cadence as strides/min (one foot); multiply by 2 for steps/min (both feet)
        cadence_vals.append(int(cad) * 2 if cad is not None else None)

        alt = _val(m, "directElevation") or _val(m, "directAltitude")
        altitude_vals.append(round(float(alt), 1) if alt is not None else None)

    if not any(t > 0 for t in time_s):
        dur = float(summary_raw.get("duration") or 0)
        n = len(metrics_data)
        time_s = [round(i * dur / n) for i in range(n)] if n > 0 else []

    # --- Summary ---
    # get_activity() can return fields at the top level OR nested in summaryDTO,
    # depending on the Garmin Connect API version. Try both locations.
    dto = summary_raw.get("summaryDTO") or {}

    def _pick(*keys):
        """Return the first non-None, non-zero value found across top-level and summaryDTO."""
        for k in keys:
            v = summary_raw.get(k)
            if v is not None and v != 0:
                return v
        for k in keys:
            v = dto.get(k)
            if v is not None and v != 0:
                return v
        return None

    dist_m  = float(_pick("distance", "totalDistance") or 0)
    dist_km = round(dist_m / 1000, 2)
    duration_sec = int(float(_pick("duration", "movingDuration", "elapsedDuration") or 0))
    avg_speed = float(_pick("averageSpeed", "avgSpeed") or 0)
    pace_str = None
    if avg_speed > 0:
        ps = 1000 / avg_speed
        pace_str = f"{int(ps // 60)}:{int(ps % 60):02d}"

    avg_hr  = _pick("averageHR", "averageHeartRate", "avgHr")
    max_hr  = _pick("maxHR", "maxHeartRate", "maxHr")
    cadence = _pick(
        "averageRunningCadenceInStepsPerMinute", "averageRunCadence",
        "averageCadence", "avgRunCadence", "avgCadence",
    )
    # Fallback: derive from stream data (already ×2 = steps/min) if summary field is missing
    if cadence is None:
        cad_stream_vals = [v for v in cadence_vals if v is not None]
        if cad_stream_vals:
            cadence = sum(cad_stream_vals) / len(cad_stream_vals)
            # stream values are already in steps/min — store as-is, skip the ×2 below
            cadence = int(round(cadence))
    elev    = _pick("elevationGain", "totalElevationGain", "totalAscent")

    def _nonempty(lst: list) -> list:
        return lst if any(v is not None for v in lst) else []

    return {
        "summary": {
            "name": summary_raw.get("activityName") or dto.get("activityName") or "",
            "start_time": summary_raw.get("startTimeLocal") or dto.get("startTimeLocal") or "",
            "distance_km": dist_km,
            "duration_seconds": duration_sec,
            "avg_pace_per_km": pace_str,
            "avg_heart_rate": int(avg_hr) if avg_hr is not None else None,
            "max_heart_rate": int(max_hr) if max_hr is not None else None,
            "avg_cadence": int(round(float(cadence))) if cadence is not None else None,
            "elevation_gain_m": round(float(elev), 1) if elev is not None else None,
        },
        "gps_track": gps_track,
        "streams": {
            "time": time_s,
            "pace": _nonempty(pace_vals),
            "heart_rate": _nonempty(hr_vals),
            "cadence": _nonempty(cadence_vals),
            "altitude": _nonempty(altitude_vals),
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
