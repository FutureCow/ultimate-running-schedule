from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.plan import Plan, WorkoutSession
from app.routers.deps import get_current_user
from app.schemas.plan import PlanCreate, PlanUpdate, PlanResponse, StrengthPreferences
from app.services import claude_service, garmin_service

router = APIRouter(prefix="/plans", tags=["plans"])


def _create_sessions_from_json(plan: Plan, plan_json: dict) -> list[WorkoutSession]:
    sessions = []
    actual_start = plan.start_date or date.today()
    # Week 1 starts on the Monday of the week that contains actual_start.
    # Sessions scheduled before actual_start are skipped so no training
    # appears in the past or before the user's chosen start date.
    week1_monday = actual_start - timedelta(days=actual_start.weekday())

    for week in plan_json.get("weeks", []):
        wnum = week["week_number"]
        week_start = week1_monday + timedelta(weeks=wnum - 1)
        for workout in week.get("workouts", []):
            day_num = workout.get("day_number", 1)
            scheduled = week_start + timedelta(days=day_num - 1)
            # Skip sessions that fall before the actual start date
            if scheduled < actual_start:
                continue
            session = WorkoutSession(
                plan_id=plan.id,
                week_number=wnum,
                day_number=day_num,
                scheduled_date=scheduled,
                workout_type=workout.get("workout_type", "easy_run"),
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

    # Persist plan
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


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    payload: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id, Plan.user_id == user.id))
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
    await db.execute(sql_delete(WorkoutSession).where(WorkoutSession.plan_id == plan_id))

    await db.flush()

    # Create new sessions
    sessions = _create_sessions_from_json(plan, plan_json)
    db.add_all(sessions)
    await db.commit()

    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    return result.scalar_one()


class RecalculateDatesPayload(BaseModel):
    start_date: Optional[date] = None


@router.patch("/{plan_id}/recalculate-dates", response_model=PlanResponse)
async def recalculate_session_dates(
    plan_id: int,
    payload: RecalculateDatesPayload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Recompute scheduled_date for all sessions from plan_json. No AI call.
    Optionally pass start_date to correct the stored plan start date first."""
    result = await db.execute(select(Plan).where(Plan.id == plan_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not plan.plan_json:
        raise HTTPException(status_code=400, detail="Plan has no stored JSON to recalculate from")

    if payload.start_date is not None:
        plan.start_date = payload.start_date

    from sqlalchemy import delete as sql_delete
    await db.execute(sql_delete(WorkoutSession).where(WorkoutSession.plan_id == plan_id))
    await db.flush()

    sessions = _create_sessions_from_json(plan, plan.plan_json)
    db.add_all(sessions)
    await db.commit()

    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    return result.scalar_one()


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id, Plan.user_id == user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await db.delete(plan)
    await db.commit()
