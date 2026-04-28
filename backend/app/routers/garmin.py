from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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


class MfaSubmit(BaseModel):
    mfa_code: str


@router.post("/credentials")
async def save_credentials(
    payload: GarminCredentialCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        result = await garmin_service.save_credentials(db, user.id, payload.email, payload.password)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result["needs_mfa"]:
        return {"needs_mfa": True}
    return result["cred"]


@router.post("/submit-mfa", response_model=GarminCredentialResponse)
async def submit_mfa(
    payload: MfaSubmit,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        cred = await garmin_service.complete_mfa(db, user.id, payload.mfa_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return cred


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


@router.post("/auto-sync")
async def auto_sync_if_stale(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sync Garmin activities if last sync was more than 1 hour ago.
    Also updates the user's weekly_km profile field from Garmin data."""
    cred = await garmin_service.get_credentials(db, user.id)
    if not cred:
        return {"synced": False, "reason": "no_credentials"}

    now = datetime.now(timezone.utc)
    if cred.last_sync_at and (now - cred.last_sync_at) < timedelta(hours=1):
        return {"synced": False, "reason": "recent", "last_sync_at": cred.last_sync_at.isoformat()}

    try:
        result = await garmin_service.fetch_activities(db, user.id, months=3, user_tier=user.tier)
        avg_weekly_km = result["summary"].get("avg_weekly_km")
        if avg_weekly_km is not None:
            user.weekly_km = avg_weekly_km
            await db.commit()
        return {
            "synced": True,
            "activity_count": len(result["activities"]),
            "avg_weekly_km": avg_weekly_km,
            "last_sync_at": now.isoformat(),
        }
    except Exception as e:
        return {"synced": False, "reason": "error", "detail": str(e)}


@router.post("/sync", response_model=GarminSyncResponse)
async def sync_activities(
    months: int = 3,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        result = await garmin_service.fetch_activities(db, user.id, months, user_tier=user.tier)
        avg_weekly_km = result["summary"].get("avg_weekly_km")
        if avg_weekly_km is not None:
            user.weekly_km = avg_weekly_km
            await db.commit()
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


@router.get("/activity/{activity_id}")
async def get_activity_detail(
    activity_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Fetch detailed activity data (GPS track + metric streams) from Garmin."""
    from app.services import claude_service
    try:
        data = await garmin_service.fetch_activity_detail(db, user.id, activity_id)
        # Attach AI feedback from the matched WorkoutSession (if any)
        session_result = await db.execute(
            select(WorkoutSession)
            .join(WorkoutSession.plan)
            .where(WorkoutSession.garmin_activity_id == activity_id, Plan.user_id == user.id)
        )
        session = session_result.scalar_one_or_none()

        # Generate feedback lazily using full stream data if not yet stored or if
        # previously stored feedback is too short (likely generated without proper data)
        needs_feedback = session and user.tier == "elite" and (
            not session.ai_feedback or len(session.ai_feedback) < 200
        )
        if needs_feedback:
            try:
                session.ai_feedback = await claude_service.generate_run_feedback(
                    data, session.title, language="nl"
                )
                await db.commit()
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "AI feedback generation failed for activity %s: %s", activity_id, exc
                )

        data["ai_feedback"] = session.ai_feedback if session else None
        data["session_title"] = session.title if session else None
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Garmin activity detail failed: {str(e)}")


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


@router.delete("/sessions/{session_id}", status_code=204)
async def remove_session_from_garmin(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WorkoutSession)
        .join(WorkoutSession.plan)
        .where(WorkoutSession.id == session_id)
        .where(Plan.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.garmin_workout_id:
        raise HTTPException(status_code=400, detail="Session has no Garmin workout ID")

    await garmin_service.delete_workout_from_garmin(db, user.id, session.garmin_workout_id)
    session.garmin_workout_id = None
    session.garmin_pushed_at = None
    await db.commit()


@router.post("/push/week")
async def push_week(
    payload: GarminPushWeekRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan_result = await db.execute(
        select(Plan).where(Plan.public_id == payload.plan_id, Plan.user_id == user.id)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    sessions_result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.plan_id == plan.id,
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
