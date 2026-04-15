from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.plan import Plan, WorkoutSession
from app.routers.deps import get_current_user
from app.schemas.garmin import (
    GarminCredentialCreate, GarminCredentialResponse,
    GarminSyncResponse, GarminPushRequest, GarminPushWeekRequest,
)
from app.services import garmin_service

router = APIRouter(prefix="/garmin", tags=["garmin"])


@router.post("/credentials", response_model=GarminCredentialResponse)
async def save_credentials(
    payload: GarminCredentialCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await garmin_service.save_credentials(db, user.id, payload.email, payload.password)


@router.get("/credentials", response_model=GarminCredentialResponse)
async def get_credentials(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cred = await garmin_service.get_credentials(db, user.id)
    if not cred:
        raise HTTPException(status_code=404, detail="No Garmin credentials saved")
    return cred


@router.delete("/credentials", status_code=204)
async def delete_credentials(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cred = await garmin_service.get_credentials(db, user.id)
    if cred:
        await db.delete(cred)
        await db.commit()


@router.post("/sync", response_model=GarminSyncResponse)
async def sync_activities(
    months: int = 3,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        result = await garmin_service.fetch_activities(db, user.id, months)
        return GarminSyncResponse(
            synced=True,
            activity_count=len(result["activities"]),
            last_sync_at=datetime.now(timezone.utc),
            summary=result["summary"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Garmin sync failed: {str(e)}")


@router.post("/push/sessions")
async def push_sessions(
    payload: GarminPushRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WorkoutSession)
        .join(WorkoutSession.plan)
        .where(WorkoutSession.id.in_(payload.session_ids))
        .where(Plan.user_id == user.id)
    )
    sessions = result.scalars().all()
    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found")
    try:
        results = await garmin_service.push_sessions_to_garmin(db, user.id, list(sessions))
        return {"results": results}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Garmin push failed: {str(e)}")


@router.post("/push/week")
async def push_week(
    payload: GarminPushWeekRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan_result = await db.execute(
        select(Plan).where(Plan.id == payload.plan_id, Plan.user_id == user.id)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    sessions_result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.plan_id == payload.plan_id,
            WorkoutSession.week_number == payload.week_number,
        )
    )
    sessions = sessions_result.scalars().all()
    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found for this week")

    try:
        results = await garmin_service.push_sessions_to_garmin(db, user.id, list(sessions))
        return {"results": results, "week_number": payload.week_number}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Garmin push failed: {str(e)}")
