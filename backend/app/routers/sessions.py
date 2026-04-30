import logging
from datetime import timedelta, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.plan import Plan, WorkoutSession
from app.routers.deps import get_current_user
from app.schemas.plan import WorkoutSessionResponse, SessionUpdate
from app.services import garmin_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionMove(BaseModel):
    day_number: int   # 1–7
    week_number: int | None = None  # if omitted, keeps current week


@router.patch("/{session_id}", response_model=WorkoutSessionResponse)
async def move_session(
    session_id: int,
    payload: SessionMove,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not 1 <= payload.day_number <= 7:
        raise HTTPException(status_code=422, detail="day_number must be between 1 and 7")

    result = await db.execute(
        select(WorkoutSession, Plan)
        .join(Plan, Plan.id == WorkoutSession.plan_id)
        .where(WorkoutSession.id == session_id, Plan.user_id == user.id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    session, plan = row

    if payload.week_number is not None:
        if not 1 <= payload.week_number <= plan.duration_weeks:
            raise HTTPException(status_code=422, detail="week_number out of plan range")
        session.week_number = payload.week_number

    session.day_number = payload.day_number

    # Recompute scheduled_date
    start = plan.start_date or date.today()
    start = start - timedelta(days=start.weekday())  # normalize to Monday
    week_start = start + timedelta(weeks=session.week_number - 1)
    session.scheduled_date = week_start + timedelta(days=payload.day_number - 1)

    await db.commit()
    await db.refresh(session)
    return session


@router.patch("/{session_id}/details", response_model=WorkoutSessionResponse)
async def update_session_details(
    session_id: int,
    payload: SessionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WorkoutSession, Plan)
        .join(Plan, Plan.id == WorkoutSession.plan_id)
        .where(WorkoutSession.id == session_id, Plan.user_id == user.id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    session, plan = row

    if payload.title is not None:
        session.title = payload.title
    if payload.description is not None:
        session.description = payload.description
    if payload.distance_km is not None:
        session.distance_km = payload.distance_km
    if payload.duration_minutes is not None:
        session.duration_minutes = payload.duration_minutes
    if payload.target_paces is not None:
        session.target_paces = dict(payload.target_paces)

    if payload.scheduled_date is not None:
        start = plan.start_date or date.today()
        week1_monday = start - timedelta(days=start.weekday())
        delta = payload.scheduled_date - week1_monday
        if delta.days < 0:
            raise HTTPException(status_code=422, detail="Datum valt voor de planstart")
        new_week = delta.days // 7 + 1
        new_day = delta.days % 7 + 1
        if new_week > plan.duration_weeks:
            raise HTTPException(status_code=422, detail="Datum valt na het einde van het plan")
        session.week_number = new_week
        session.day_number = new_day
        session.scheduled_date = payload.scheduled_date

    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WorkoutSession)
        .join(Plan, Plan.id == WorkoutSession.plan_id)
        .where(WorkoutSession.id == session_id, Plan.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # If the workout was pushed to Garmin, delete it there too (best-effort)
    if session.garmin_workout_id:
        try:
            await garmin_service.delete_workout_from_garmin(db, user.id, session.garmin_workout_id)
        except Exception as e:
            logger.warning("Garmin delete failed for workout %s: %s", session.garmin_workout_id, e)

    await db.delete(session)
    await db.commit()
