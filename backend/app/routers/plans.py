from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.plan import Plan, WorkoutSession
from app.routers.deps import get_current_user, require_tier
from app.schemas.plan import PlanCreate, PlanUpdate, PlanResponse, StrengthPreferences
from app.services import claude_service, garmin_service

router = APIRouter(prefix="/plans", tags=["plans"])


_POST_RACE_TYPES = {"easy_run", "recovery", "rest"}


def _create_sessions_from_json(plan: Plan, plan_json: dict) -> list[WorkoutSession]:
    sessions = []
    actual_start = plan.start_date or date.today()
    week1_monday = actual_start - timedelta(days=actual_start.weekday())

    # Find the race week number and day so we can enforce post-race workout types
    race_week_num: int | None = None
    race_day_num: int | None = None
    if plan.race_date:
        for week in plan_json.get("weeks", []):
            for workout in week.get("workouts", []):
                if workout.get("workout_type") == "race":
                    race_week_num = week["week_number"]
                    race_day_num = workout.get("day_number")
                    break

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

            # Drop everything scheduled after the race date
            if plan.race_date and scheduled > plan.race_date:
                continue

            # Guard: any session after the race in the same week must be recovery/rest
            if (race_week_num is not None and race_day_num is not None
                    and wnum == race_week_num and day_num > race_day_num
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
                target_paces=workout.get("target_paces"),
                intervals=workout.get("intervals"),
            )
            sessions.append(session)
    return sessions


@router.post("", response_model=PlanResponse, status_code=201)
async def create_plan(
    payload: PlanCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Tier gate: base and tempo may only have 1 plan; elite is unlimited
    if user.tier in ("base", "tempo"):
        existing = await db.execute(select(Plan).where(Plan.user_id == user.id))
        if existing.scalars().first():
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
        sync_result = await garmin_service.fetch_activities(db, user.id, months=3)
        garmin_summary = sync_result
    except Exception:
        pass  # Proceed without Garmin data

    # Generate plan via Claude
    try:
        plan_json = await claude_service.generate_plan(payload, garmin_summary, language=payload.language)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI plan generation failed: {str(e)}")

    plan_data = payload.model_dump()
    plan_data.pop("language", None)  # language is not a DB column

    # Flatten nested strength preferences into individual DB columns
    strength = plan_data.pop("strength", None) or {}
    plan_data["strength_enabled"] = strength.get("enabled", False)
    plan_data["strength_location"] = strength.get("location")
    plan_data["strength_type"] = strength.get("type")
    plan_data["strength_days"] = strength.get("days")
    plan_data["strength_equipment"] = strength.get("equipment")

    # Persist plan
    try:
        plan = Plan(
            user_id=user.id,
            **plan_data,
            plan_json=plan_json,
        )
        db.add(plan)
        await db.flush()  # get plan.id

        sessions = _create_sessions_from_json(plan, plan_json)
        db.add_all(sessions)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Plan opslaan mislukt: {str(e)}")

    # Reload fully with selectin-loaded sessions
    result = await db.execute(select(Plan).where(Plan.id == plan.id))
    return result.scalar_one()


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Plan).where(Plan.user_id == user.id).order_by(Plan.created_at.desc()))
    return result.scalars().all()


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
    return plan


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
    merged = PlanCreate(
        name=plan.name,
        goal=plan.goal,
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
    )

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
    return result.scalar_one()


_ZONE_FOR_TYPE: dict[str, str] = {
    "easy_run": "easy",
    "long_run":  "marathon",
    "recovery":  "easy",
    "tempo":     "threshold",
    "interval":  "interval",
}


@router.post("/{public_id}/regenerate", response_model=PlanResponse)
async def regenerate_plan(
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
    for session in future_sessions:
        zone = _ZONE_FOR_TYPE[session.workout_type]
        new_main = new_zones.get(zone)
        if not new_main:
            continue
        paces = dict(session.target_paces or {})
        paces["main"] = new_main
        if "warmup" in paces and new_zones.get("easy"):
            paces["warmup"] = new_zones["easy"]
        if "cooldown" in paces and new_zones.get("easy"):
            paces["cooldown"] = new_zones["easy"]
        session.target_paces = paces

        # Update interval paces too
        if session.workout_type == "interval" and session.intervals and new_zones.get("interval"):
            session.intervals = [{**iv, "pace": new_zones["interval"]} for iv in session.intervals]

    # Update pace zones + notes in stored plan_json
    if plan.plan_json:
        import copy
        pj = copy.deepcopy(plan.plan_json)
        overview = pj.setdefault("plan_overview", {})
        overview["pace_zones"] = {**current_zones, **new_zones}
        if new_data.get("notes"):
            overview["coaching_notes"] = new_data["notes"]
        plan.plan_json = pj

    await db.commit()

    result = await db.execute(select(Plan).where(Plan.public_id == public_id))
    return result.scalar_one()


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
    return result.scalar_one()


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
    return result.scalar_one()


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
    await db.delete(plan)
    await db.commit()
