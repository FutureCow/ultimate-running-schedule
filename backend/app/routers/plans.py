from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.rate_limit import limiter
from app.models.user import User
from app.models.plan import Plan, WorkoutSession
from app.routers.deps import get_current_user, require_tier
from app.schemas.plan import PlanCreate, PlanUpdate, PlanResponse, StrengthPreferences
from app.services import claude_service, garmin_service
from app.services.follow_up import suggest_goals, summarise_plan

router = APIRouter(prefix="/plans", tags=["plans"])


_POST_RACE_TYPES = {"easy_run", "recovery", "rest"}


async def _with_actuals(db: AsyncSession, user_id: int, plans):
    """Attach what was actually run to every session of the given plan(s)."""
    from app.models.garmin_activity import GarminActivity

    many = isinstance(plans, (list, tuple))
    plan_list = list(plans) if many else [plans]

    activity_ids = {
        s.garmin_activity_id
        for plan in plan_list for s in plan.sessions if s.garmin_activity_id
    }
    activities_by_id = {}
    if activity_ids:
        rows = await db.execute(
            select(GarminActivity).where(
                GarminActivity.user_id == user_id,
                GarminActivity.activity_id.in_(activity_ids),
            )
        )
        activities_by_id = {a.activity_id: a for a in rows.scalars().all()}

    for plan in plan_list:
        garmin_service.attach_actuals(plan.sessions, activities_by_id)

    return plans


def _tier_decision(tier: str, has_plan: bool, is_follow_up: bool) -> tuple[bool, bool]:
    """(allowed, replace_previous) for creating a plan.

    Base and Tempo keep one plan. A follow-up takes the place of the plan it
    builds on, so they can progress too; an unrelated second plan still needs
    an upgrade. Elite keeps every plan.
    """
    if tier not in ("base", "tempo") or not has_plan:
        return True, False
    return (True, True) if is_follow_up else (False, False)


def _apply_race_override(
    summary: dict, race_time_seconds: int | None, race_distance_km: float | None = None
) -> dict:
    """A race time or distance entered by the athlete wins over the matched
    activity, which may include a warm-up — or over the plan's goal distance
    when the race actually run was a different one."""
    measured = summary.get("race") or {}
    time = race_time_seconds or measured.get("time_seconds")
    if not time:
        return summary  # a distance alone says nothing about level
    summary["race"] = {
        "distance_km": race_distance_km or measured.get("distance_km") or summary.get("goal_km"),
        "time_seconds": time,
    }
    return summary


# Fields a create request carries that are not columns on Plan
_REQUEST_ONLY = ("language", "previous_plan_id", "previous_race_time_seconds", "previous_race_distance_km")


def _plan_columns(payload: PlanCreate) -> dict:
    """The create payload as Plan column values."""
    data = payload.model_dump()
    for field in _REQUEST_ONLY:
        data.pop(field, None)
    strength = data.pop("strength", None) or {}
    data["strength_enabled"] = strength.get("enabled", False)
    data["strength_location"] = strength.get("location")
    data["strength_type"] = strength.get("type")
    data["strength_days"] = strength.get("days")
    data["strength_equipment"] = strength.get("equipment")
    return data


async def _activities_for(db: AsyncSession, user_id: int, plan: Plan) -> dict:
    from app.models.garmin_activity import GarminActivity

    ids = {s.garmin_activity_id for s in plan.sessions if s.garmin_activity_id}
    if not ids:
        return {}
    rows = await db.execute(
        select(GarminActivity).where(
            GarminActivity.user_id == user_id, GarminActivity.activity_id.in_(ids)
        )
    )
    return {a.activity_id: a for a in rows.scalars().all()}


async def _delete_plan_and_garmin_workouts(db: AsyncSession, user_id: int, plan: Plan) -> None:
    """Remove a plan, taking its pushed workouts off Garmin first.

    Once the sessions are gone the workout ids are lost and the workouts sit on
    the watch with no way to clean them up. Garmin failures are logged, not
    fatal — the plan still goes.
    """
    import logging

    for s in plan.sessions:
        if s.garmin_workout_id:
            try:
                await garmin_service.delete_workout_from_garmin(db, user_id, s.garmin_workout_id)
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "Garmin cleanup failed for workout %s: %s", s.garmin_workout_id, exc
                )
    await db.delete(plan)


def _plan_to_create(plan: Plan) -> PlanCreate:
    """Rebuild the AI input from a stored plan, for regeneration on edit.

    Every field that shapes the prompt has to be listed here — a missing one
    silently drops out of the regenerated plan.
    """
    return PlanCreate(
        name=plan.name,
        goal=plan.goal,
        custom_distance_km=plan.custom_distance_km,
        goal_kind=plan.goal_kind or "race",
        target_time_seconds=plan.target_time_seconds,
        target_pace_per_km=plan.target_pace_per_km,
        age=plan.age,
        height_cm=plan.height_cm,
        weight_kg=plan.weight_kg,
        weekly_km=plan.weekly_km,
        weekly_runs=plan.weekly_runs,
        injuries=plan.injuries,
        extra_notes=plan.extra_notes,
        training_days=plan.training_days,
        long_run_day=plan.long_run_day,
        duration_weeks=plan.duration_weeks,
        surface=plan.surface,
        start_date=plan.start_date,
        race_date=plan.race_date,
        strength=StrengthPreferences(
            enabled=plan.strength_enabled,
            location=plan.strength_location,
            type=plan.strength_type,
            days=plan.strength_days,
            equipment=plan.strength_equipment,
        ) if plan.strength_enabled else None,
        previous_summary=plan.previous_summary,
    )


def _create_sessions_from_json(plan: Plan, plan_json: dict) -> list[WorkoutSession]:
    sessions = []
    actual_start = plan.start_date or date.today()
    week1_monday = actual_start - timedelta(days=actual_start.weekday())

    for week in plan_json.get("weeks", []):
        wnum = week["week_number"]
        week_start = week1_monday + timedelta(weeks=wnum - 1)
        for workout in week.get("workouts", []):
            day_num = workout.get("day_number", 1)
            scheduled = week_start + timedelta(days=day_num - 1)
            if scheduled < actual_start:
                continue

            workout_type = workout.get("workout_type", "easy_run")

            # Drop strength workouts when strength training is not enabled
            if workout_type == "strength" and not plan.strength_enabled:
                continue

            # Force the race session onto the exact race_date
            if workout_type == "race" and plan.race_date:
                scheduled = plan.race_date

            # After the race the plan winds down — it never trains hard again.
            # Covers both the tail of the race week and the post-race recovery
            # week, which is kept so the athlete can see it.
            if (plan.race_date and scheduled > plan.race_date
                    and workout_type not in _POST_RACE_TYPES):
                workout_type = "recovery"

            session = WorkoutSession(
                plan_id=plan.id,
                week_number=wnum,
                day_number=day_num,
                scheduled_date=scheduled,
                workout_type=workout_type,
                title=workout.get("title", "Run"),
                description=workout.get("description"),
                distance_km=workout.get("distance_km"),
                duration_minutes=workout.get("duration_minutes"),
                warmup_km=workout.get("warmup_km"),
                cooldown_km=workout.get("cooldown_km"),
                target_paces=workout.get("target_paces"),
                intervals=workout.get("intervals"),
            )
            sessions.append(session)
    return sessions


@router.post("", response_model=PlanResponse, status_code=201)
@limiter.limit("5/hour")
async def create_plan(
    request: Request,
    payload: PlanCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # A follow-up builds on one of the athlete's own plans
    previous = None
    if payload.previous_plan_id:
        found = await db.execute(select(Plan).where(
            Plan.public_id == payload.previous_plan_id, Plan.user_id == user.id))
        previous = found.scalar_one_or_none()
        if not previous:
            raise HTTPException(status_code=404, detail="Vorig plan niet gevonden")
        summary = summarise_plan(previous, await _activities_for(db, user.id, previous))
        payload.previous_summary = _apply_race_override(
            summary, payload.previous_race_time_seconds, payload.previous_race_distance_km)
    else:
        payload.previous_summary = None  # never trust one sent by the client

    # Tier gate: base and tempo keep one plan; a follow-up takes its place
    existing = await db.execute(select(Plan.id).where(Plan.user_id == user.id))
    allowed, replace_previous = _tier_decision(
        user.tier, existing.first() is not None, previous is not None)
    if not allowed:
        needed = "elite" if user.tier == "tempo" else "tempo"
        raise HTTPException(
            status_code=403,
            detail=f"UPGRADE_REQUIRED:{needed}:Je kunt met je huidige abonnement maar 1 plan aanmaken",
        )

    # Tier gate: strength training is Elite only
    has_strength = payload.strength and payload.strength.enabled
    if has_strength and user.tier != "elite":
        raise HTTPException(
            status_code=403,
            detail="UPGRADE_REQUIRED:elite:Krachttraining vereist een Elite-abonnement",
        )

    # Optionally fetch Garmin summary for AI context
    garmin_summary = None
    try:
        garmin_summary = await garmin_service.fetch_activities(db, user.id, months=3)
    except Exception:
        pass  # Proceed without Garmin data

    # Generate first: if this fails, the previous plan is still untouched
    try:
        plan_json = await claude_service.generate_plan(payload, garmin_summary, language=payload.language)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI plan generation failed: {str(e)}")

    try:
        plan = Plan(user_id=user.id, **_plan_columns(payload), plan_json=plan_json)
        db.add(plan)
        await db.flush()  # get plan.id

        db.add_all(_create_sessions_from_json(plan, plan_json))
        if replace_previous:
            await _delete_plan_and_garmin_workouts(db, user.id, previous)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Plan opslaan mislukt: {str(e)}")

    # Reload fully with selectin-loaded sessions
    result = await db.execute(select(Plan).where(Plan.id == plan.id))
    return await _with_actuals(db, user.id, result.scalar_one())


@router.get("/{public_id}/follow-up-summary")
async def follow_up_summary(
    public_id: str,
    race_time_seconds: Optional[int] = None,
    race_distance_km: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """What a follow-up plan would build on, and goals it could aim for.

    The wizard passes a corrected race time or distance back in, so the
    suggested goals follow the result the athlete says is right.
    """
    result = await db.execute(select(Plan).where(Plan.public_id == public_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    summary = summarise_plan(plan, await _activities_for(db, user.id, plan))
    summary = _apply_race_override(summary, race_time_seconds, race_distance_km)
    return {**summary, "suggestions": suggest_goals(summary)}


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Plan).where(Plan.user_id == user.id).order_by(Plan.created_at.desc()))
    return await _with_actuals(db, user.id, list(result.scalars().all()))


@router.get("/{public_id}", response_model=PlanResponse)
async def get_plan(
    public_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Plan).where(Plan.public_id == public_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return await _with_actuals(db, user.id, plan)


@router.put("/{public_id}", response_model=PlanResponse)
async def update_plan(
    public_id: str,
    payload: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_tier("tempo")),
):
    result = await db.execute(select(Plan).where(Plan.public_id == public_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Extract language before applying to DB model (not a DB column)
    update_language = payload.language or "nl"

    # Apply updated fields (skip language – not a DB column)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field != "language":
            setattr(plan, field, value)

    # Build a PlanCreate-like object for AI generation using merged values
    merged = _plan_to_create(plan)

    # Fetch optional Garmin context
    garmin_summary = None
    try:
        garmin_summary = await garmin_service.fetch_activities(db, user.id, months=3)
    except Exception:
        pass

    # Regenerate plan via AI
    try:
        plan_json = await claude_service.generate_plan(merged, garmin_summary, language=update_language)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI plan generation failed: {str(e)}")

    plan.plan_json = plan_json

    # Delete old sessions
    from sqlalchemy import delete as sql_delete
    await db.execute(sql_delete(WorkoutSession).where(WorkoutSession.plan_id == plan.id))

    await db.flush()

    # Create new sessions
    sessions = _create_sessions_from_json(plan, plan_json)
    db.add_all(sessions)
    await db.commit()

    result = await db.execute(select(Plan).where(Plan.public_id == public_id))
    return await _with_actuals(db, user.id, result.scalar_one())


def _pace_secs(pace_str: str) -> int | None:
    import re as _re
    m = _re.search(r'(\d+):(\d{2})', pace_str or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None

def _zone_delta(old_zone: str, new_zone: str) -> int:
    import re as _re
    def midpoint(z: str) -> int | None:
        vals = [_pace_secs(p) for p in _re.findall(r'\d+:\d{2}', z or "")]
        vals = [v for v in vals if v is not None]
        return sum(vals) // len(vals) if vals else None
    old, new = midpoint(old_zone), midpoint(new_zone)
    return (new - old) if (old is not None and new is not None) else 0

def _shift_pace(pace_str: str, delta_secs: int) -> str:
    import re as _re
    if not pace_str or not delta_secs:
        return pace_str
    def shift(m):
        secs = int(m.group(1)) * 60 + int(m.group(2)) + delta_secs
        mins, s = divmod(max(0, secs), 60)
        return f"{mins}:{s:02d}"
    return _re.sub(r'(\d+):(\d{2})', shift, pace_str)


_ZONE_FOR_TYPE: dict[str, str] = {
    "easy_run": "easy",
    "long_run":  "marathon",
    "recovery":  "easy",
    "tempo":     "threshold",
    "interval":  "interval",
}


@router.post("/{public_id}/regenerate/preview")
@limiter.limit("10/hour")
async def preview_regenerate_plan(
    request: Request,
    public_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_tier("tempo")),
):
    """Calculate new pace zones without saving — returns preview for user confirmation."""
    result = await db.execute(select(Plan).where(Plan.public_id == public_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    activity_by_id: dict[str, dict] = {}
    try:
        sync_result = await garmin_service.fetch_activities(db, user.id, months=3, user_tier=user.tier)
        for act in sync_result.get("activities", []):
            activity_by_id[act["activity_id"]] = act
    except Exception:
        pass

    completed = sorted(
        [s for s in plan.sessions if s.completed_at and s.workout_type not in ("rest", "strength")],
        key=lambda s: s.completed_at,
        reverse=True,
    )[:6]

    recent_runs = []
    for s in completed:
        act = activity_by_id.get(s.garmin_activity_id or "", {})
        recent_runs.append({
            "workout_type": s.workout_type,
            "planned_paces": s.target_paces or {},
            "actual_pace": act.get("average_pace_per_km"),
            "actual_hr":   act.get("average_heart_rate"),
            "distance_km": act.get("distance_km") or s.distance_km,
        })

    if not recent_runs:
        raise HTTPException(
            status_code=400,
            detail="Geen voltooide sessies gevonden — voltooi eerst een paar runs via Garmin sync.",
        )

    current_zones: dict = {}
    if plan.plan_json:
        current_zones = (plan.plan_json.get("plan_overview") or {}).get("pace_zones") or {}

    try:
        new_data = await claude_service.recalibrate_paces(recent_runs, current_zones)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Pace recalibratie mislukt: {str(e)}")

    new_zones = {k: v for k, v in new_data.items() if k != "notes"}
    if not new_zones:
        raise HTTPException(status_code=502, detail="Claude kon geen nieuwe pacezones berekenen.")

    future_count = len([
        s for s in plan.sessions
        if not s.completed_at and s.workout_type in _ZONE_FOR_TYPE
    ])

    return {
        "current_zones": current_zones,
        "new_zones": new_zones,
        "notes": new_data.get("notes"),
        "sessions_to_update": future_count,
        "based_on_runs": len(recent_runs),
    }


@router.post("/{public_id}/regenerate", response_model=PlanResponse)
@limiter.limit("5/hour")
async def regenerate_plan(
    request: Request,
    public_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_tier("tempo")),
):
    """Recalibrate pace zones from the last 6 Garmin activities.
    Does NOT create a new plan — only updates target_paces on future sessions."""
    result = await db.execute(select(Plan).where(Plan.public_id == public_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Fetch fresh Garmin activities to get actual paces
    activity_by_id: dict[str, dict] = {}
    try:
        sync_result = await garmin_service.fetch_activities(db, user.id, months=3, user_tier=user.tier)
        for act in sync_result.get("activities", []):
            activity_by_id[act["activity_id"]] = act
    except Exception:
        pass  # proceed with whatever data we have

    # Find the 6 most recent completed non-rest sessions from this plan
    completed = sorted(
        [s for s in plan.sessions if s.completed_at and s.workout_type not in ("rest", "strength")],
        key=lambda s: s.completed_at,
        reverse=True,
    )[:6]

    recent_runs = []
    for s in completed:
        act = activity_by_id.get(s.garmin_activity_id or "", {})
        recent_runs.append({
            "workout_type": s.workout_type,
            "planned_paces": s.target_paces or {},
            "actual_pace": act.get("average_pace_per_km"),
            "actual_hr":   act.get("average_heart_rate"),
            "distance_km": act.get("distance_km") or s.distance_km,
        })

    if not recent_runs:
        raise HTTPException(
            status_code=400,
            detail="Geen voltooide sessies gevonden — voltooi eerst een paar runs via Garmin sync.",
        )

    # Get current pace zones from plan
    current_zones = {}
    if plan.plan_json:
        current_zones = (plan.plan_json.get("plan_overview") or {}).get("pace_zones") or {}

    # Ask Claude to recalibrate
    try:
        new_data = await claude_service.recalibrate_paces(recent_runs, current_zones)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Pace recalibratie mislukt: {str(e)}")

    new_zones = {k: v for k, v in new_data.items() if k != "notes"}
    if not new_zones:
        raise HTTPException(status_code=502, detail="Claude kon geen nieuwe pacezones berekenen.")

    # Apply updated zones to all future (uncompleted) running sessions
    future_sessions = [
        s for s in plan.sessions
        if not s.completed_at and s.workout_type in _ZONE_FOR_TYPE
    ]
    easy_delta = _zone_delta(current_zones.get("easy", ""), new_zones.get("easy", ""))
    for session in future_sessions:
        zone = _ZONE_FOR_TYPE[session.workout_type]
        new_zone = new_zones.get(zone)
        if not new_zone:
            continue
        delta = _zone_delta(current_zones.get(zone, ""), new_zone)
        paces = dict(session.target_paces or {})

        # Shift existing main pace by delta; fall back to zone value if none set
        existing_main = paces.get("main", "")
        if existing_main and existing_main.upper() != "N/A":
            paces["main"] = _shift_pace(existing_main, delta) if delta else existing_main
        else:
            paces["main"] = new_zone

        # Only update warmup/cooldown if they already had a real (non-empty) value
        if paces.get("warmup") and paces["warmup"].upper() != "N/A":
            paces["warmup"] = _shift_pace(paces["warmup"], easy_delta) if easy_delta else paces["warmup"]
        if paces.get("cooldown") and paces["cooldown"].upper() != "N/A":
            paces["cooldown"] = _shift_pace(paces["cooldown"], easy_delta) if easy_delta else paces["cooldown"]

        session.target_paces = paces

        # Update interval paces by delta too
        if session.workout_type == "interval" and session.intervals and new_zones.get("interval"):
            int_delta = _zone_delta(current_zones.get("interval", ""), new_zones["interval"])
            session.intervals = [
                {**iv, "pace": _shift_pace(iv["pace"], int_delta) if iv.get("pace") and int_delta else iv.get("pace", new_zones["interval"])}
                for iv in session.intervals
            ]

    # Update pace zones + notes in stored plan_json
    if plan.plan_json:
        import copy
        pj = copy.deepcopy(plan.plan_json)
        overview = pj.setdefault("plan_overview", {})
        # Preserve original AI zones on first recalibration so reset can restore them
        if "original_pace_zones" not in overview and current_zones:
            overview["original_pace_zones"] = dict(current_zones)
        overview["pace_zones"] = {**current_zones, **new_zones}
        if new_data.get("notes"):
            overview["coaching_notes"] = new_data["notes"]
        plan.plan_json = pj

    await db.commit()

    result = await db.execute(select(Plan).where(Plan.public_id == public_id))
    return await _with_actuals(db, user.id, result.scalar_one())


@router.post("/{public_id}/reset", response_model=PlanResponse)
async def reset_plan(
    public_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Restore all future uncompleted sessions to their original AI-generated values."""
    result = await db.execute(select(Plan).where(Plan.public_id == public_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan niet gevonden")
    if not plan.plan_json:
        raise HTTPException(status_code=400, detail="Plan heeft geen opgeslagen originele data.")

    # Build lookup: (week_number, day_number) -> original workout dict
    originals: dict[tuple[int, int], dict] = {}
    for week in plan.plan_json.get("weeks", []):
        for w in week.get("workouts", []):
            originals[(week["week_number"], w["day_number"])] = w

    import copy
    from sqlalchemy.orm.attributes import flag_modified

    future_sessions = [s for s in plan.sessions if not s.completed_at]
    for session in future_sessions:
        original = originals.get((session.week_number, session.day_number))
        if not original:
            continue
        session.target_paces     = copy.deepcopy(original.get("target_paces"))
        session.intervals        = copy.deepcopy(original.get("intervals"))
        session.distance_km      = original.get("distance_km")
        session.duration_minutes = original.get("duration_minutes")
        session.warmup_km        = original.get("warmup_km")
        session.cooldown_km      = original.get("cooldown_km")
        session.title            = original.get("title", session.title)
        session.description      = original.get("description", session.description)
        flag_modified(session, "target_paces")
        flag_modified(session, "intervals")

    # Restore pace zones to original AI-generated values
    overview = (plan.plan_json or {}).get("plan_overview", {})
    original_zones = overview.get("original_pace_zones")
    if original_zones:
        pj = copy.deepcopy(plan.plan_json)
        pj["plan_overview"]["pace_zones"] = dict(original_zones)
        plan.plan_json = pj
        flag_modified(plan, "plan_json")

    await db.commit()
    result = await db.execute(select(Plan).where(Plan.public_id == public_id))
    return await _with_actuals(db, user.id, result.scalar_one())


class RecalculateDatesPayload(BaseModel):
    start_date: Optional[date] = None


@router.patch("/{public_id}/recalculate-dates", response_model=PlanResponse)
async def recalculate_session_dates(
    public_id: str,
    payload: RecalculateDatesPayload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Recompute scheduled_date for all sessions from plan_json. No AI call.
    Optionally pass start_date to correct the stored plan start date first."""
    result = await db.execute(select(Plan).where(Plan.public_id == public_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not plan.plan_json:
        raise HTTPException(status_code=400, detail="Plan has no stored JSON to recalculate from")

    if payload.start_date is not None:
        plan.start_date = payload.start_date

    from sqlalchemy import delete as sql_delete
    await db.execute(sql_delete(WorkoutSession).where(WorkoutSession.plan_id == plan.id))
    await db.flush()

    sessions = _create_sessions_from_json(plan, plan.plan_json)
    db.add_all(sessions)
    await db.commit()

    result = await db.execute(select(Plan).where(Plan.public_id == public_id))
    return await _with_actuals(db, user.id, result.scalar_one())


@router.post("/{public_id}/add-strength", response_model=PlanResponse)
async def add_strength_to_plan(
    public_id: str,
    payload: StrengthPreferences,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_tier("elite")),
):
    """Generate and insert strength sessions into an existing plan without touching running sessions."""
    result = await db.execute(select(Plan).where(Plan.public_id == public_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not plan.plan_json:
        raise HTTPException(status_code=400, detail="Plan has no stored JSON")

    try:
        strength_sessions = await claude_service.generate_strength_sessions(
            plan.plan_json, payload, plan.duration_weeks
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI strength generation failed: {str(e)}")

    # Remove existing strength sessions
    from sqlalchemy import delete as sql_delete
    await db.execute(
        sql_delete(WorkoutSession).where(
            WorkoutSession.plan_id == plan.id,
            WorkoutSession.workout_type == "strength",
        )
    )
    await db.flush()

    # Calculate scheduled_date for each new session
    actual_start = plan.start_date or date.today()
    week1_monday = actual_start - timedelta(days=actual_start.weekday())

    new_sessions = []
    for s in strength_sessions:
        wnum = s.get("week_number", 1)
        day_num = s.get("day_number", 1)
        scheduled = week1_monday + timedelta(weeks=wnum - 1, days=day_num - 1)
        new_sessions.append(WorkoutSession(
            plan_id=plan.id,
            week_number=wnum,
            day_number=day_num,
            scheduled_date=scheduled,
            workout_type="strength",
            title=s.get("title", "Strength"),
            description=s.get("description"),
            distance_km=None,
            duration_minutes=s.get("duration_minutes"),
            target_paces={"main": "N/A"},
        ))

    # Persist strength preferences on plan
    plan.strength_enabled = True
    plan.strength_location = payload.location
    plan.strength_type = payload.type
    plan.strength_days = payload.days
    plan.strength_equipment = payload.equipment

    db.add_all(new_sessions)
    await db.commit()

    result = await db.execute(select(Plan).where(Plan.public_id == public_id))
    return await _with_actuals(db, user.id, result.scalar_one())


class BulkFilter(BaseModel):
    day_number: int | None = None
    workout_type: str | None = None
    only_future: bool = True


class BulkUpdate(BaseModel):
    day_number: int | None = None
    target_pace_key: str | None = None
    target_pace_value: str | None = None          # absolute value, e.g. "6:30-6:50"
    target_pace_delta_seconds: int | None = None  # relative shift, e.g. -10 or +15


class BulkEditPayload(BaseModel):
    filter: BulkFilter
    update: BulkUpdate


@router.patch("/{public_id}/sessions/bulk")
async def bulk_edit_sessions(
    public_id: str,
    payload: BulkEditPayload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Bulk edit sessions: move a day or change a pace across matching sessions."""
    has_pace_update = payload.update.target_pace_key is not None and (
        payload.update.target_pace_value is not None or payload.update.target_pace_delta_seconds is not None
    )
    if payload.update.day_number is None and not has_pace_update:
        raise HTTPException(status_code=422, detail="Specify day_number or target_pace_key+value/delta to update")

    result = await db.execute(select(Plan).where(Plan.public_id == public_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    q = select(WorkoutSession).where(WorkoutSession.plan_id == plan.id)
    if payload.filter.day_number is not None:
        q = q.where(WorkoutSession.day_number == payload.filter.day_number)
    if payload.filter.workout_type is not None:
        q = q.where(WorkoutSession.workout_type == payload.filter.workout_type)
    if payload.filter.only_future:
        q = q.where(WorkoutSession.completed_at.is_(None))

    sessions = (await db.execute(q)).scalars().all()

    start = plan.start_date or date.today()
    week1_monday = start - timedelta(days=start.weekday())

    updated = 0
    for session in sessions:
        if payload.update.day_number is not None:
            new_day = payload.update.day_number
            session.day_number = new_day
            session.scheduled_date = (
                week1_monday + timedelta(weeks=session.week_number - 1, days=new_day - 1)
            )
        if payload.update.target_pace_key:
            key = payload.update.target_pace_key
            current = dict(session.target_paces or {})
            if key in current:
                if payload.update.target_pace_value is not None:
                    current[key] = payload.update.target_pace_value
                elif payload.update.target_pace_delta_seconds is not None:
                    current[key] = _shift_pace(current[key], payload.update.target_pace_delta_seconds)
                session.target_paces = current
        updated += 1

    if updated:
        await db.commit()

    return {"updated": updated}


@router.delete("/{public_id}", status_code=204)
async def delete_plan(
    public_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Plan).where(Plan.public_id == public_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await _delete_plan_and_garmin_workouts(db, user.id, plan)
    await db.commit()
