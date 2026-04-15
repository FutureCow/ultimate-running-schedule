from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.plan import Plan, WorkoutSession
from app.routers.deps import get_current_user
from app.schemas.plan import PlanCreate, PlanResponse
from app.services import claude_service, garmin_service

router = APIRouter(prefix="/plans", tags=["plans"])


def _create_sessions_from_json(plan: Plan, plan_json: dict) -> list[WorkoutSession]:
    sessions = []
    start = plan.start_date or date.today()
    # Adjust to Monday of the start week
    start = start - timedelta(days=start.weekday())

    for week in plan_json.get("weeks", []):
        wnum = week["week_number"]
        week_start = start + timedelta(weeks=wnum - 1)
        for workout in week.get("workouts", []):
            day_num = workout.get("day_number", 1)
            scheduled = week_start + timedelta(days=day_num - 1)
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
        plan_json = await claude_service.generate_plan(payload, garmin_summary)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI plan generation failed: {str(e)}")

    # Persist plan
    plan = Plan(
        user_id=user.id,
        **payload.model_dump(),
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
