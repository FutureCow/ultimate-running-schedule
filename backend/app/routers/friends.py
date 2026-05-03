import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.friendship import Friendship
from app.routers.deps import get_current_user
from app.services import garmin_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/friends", tags=["friends"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _user_summary(u: User) -> dict:
    return {"id": u.id, "name": u.name or u.email, "avatar_url": u.avatar_url}


async def _get_accepted_friendship(
    db: AsyncSession, user_id: int, friend_id: int
) -> Friendship | None:
    result = await db.execute(
        select(Friendship).where(
            Friendship.status == "accepted",
            or_(
                and_(Friendship.requester_id == user_id, Friendship.addressee_id == friend_id),
                and_(Friendship.requester_id == friend_id, Friendship.addressee_id == user_id),
            ),
        )
    )
    return result.scalar_one_or_none()


# ── Search ────────────────────────────────────────────────────────────────────

class SearchPayload(BaseModel):
    name: str


@router.post("/search")
async def search_users(
    payload: SearchPayload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Search for a user by exact full name. Returns the match (excluding yourself)."""
    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Naam moet minimaal 2 tekens bevatten")

    result = await db.execute(
        select(User).where(User.name == name, User.id != user.id, User.is_active == True)
    )
    users = result.scalars().all()
    if not users:
        return {"users": []}

    # Enrich with friendship status for the current user
    user_ids = [u.id for u in users]
    fs_result = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == user.id, Friendship.addressee_id.in_(user_ids)),
                and_(Friendship.requester_id.in_(user_ids), Friendship.addressee_id == user.id),
            )
        )
    )
    friendships = fs_result.scalars().all()
    fs_map: dict[int, str] = {}
    for f in friendships:
        other_id = f.addressee_id if f.requester_id == user.id else f.requester_id
        fs_map[other_id] = f.status if f.requester_id == user.id else f"incoming_{f.status}"

    return {
        "users": [
            {**_user_summary(u), "friendship_status": fs_map.get(u.id, "none")}
            for u in users
        ]
    }


# ── Requests ──────────────────────────────────────────────────────────────────

@router.post("/request/{addressee_id}")
async def send_request(
    addressee_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if addressee_id == user.id:
        raise HTTPException(status_code=422, detail="Je kunt jezelf geen verzoek sturen")

    addressee = await db.get(User, addressee_id)
    if not addressee or not addressee.is_active:
        raise HTTPException(status_code=404, detail="Gebruiker niet gevonden")

    # Check no existing friendship/request in either direction
    existing = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == user.id, Friendship.addressee_id == addressee_id),
                and_(Friendship.requester_id == addressee_id, Friendship.addressee_id == user.id),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Er bestaat al een verzoek of vriendschap")

    db.add(Friendship(requester_id=user.id, addressee_id=addressee_id, status="pending"))
    await db.commit()
    return {"ok": True}


@router.get("/requests")
async def list_requests(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Incoming pending friend requests."""
    result = await db.execute(
        select(Friendship).where(
            Friendship.addressee_id == user.id,
            Friendship.status == "pending",
        )
    )
    requests = result.scalars().all()
    out = []
    for f in requests:
        requester = await db.get(User, f.requester_id)
        if requester:
            out.append({"friendship_id": f.id, "user": _user_summary(requester), "created_at": f.created_at})
    return {"requests": out}


@router.get("/sent")
async def list_sent_requests(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Outgoing pending friend requests."""
    result = await db.execute(
        select(Friendship).where(
            Friendship.requester_id == user.id,
            Friendship.status == "pending",
        )
    )
    requests = result.scalars().all()
    out = []
    for f in requests:
        addressee = await db.get(User, f.addressee_id)
        if addressee:
            out.append({"friendship_id": f.id, "user": _user_summary(addressee), "created_at": f.created_at})
    return {"requests": out}


@router.post("/requests/{friendship_id}/accept")
async def accept_request(
    friendship_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    f = await db.get(Friendship, friendship_id)
    if not f or f.addressee_id != user.id or f.status != "pending":
        raise HTTPException(status_code=404, detail="Verzoek niet gevonden")
    f.status = "accepted"
    await db.commit()
    return {"ok": True}


@router.delete("/requests/{friendship_id}")
async def decline_or_cancel_request(
    friendship_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Decline an incoming request OR cancel an outgoing one."""
    f = await db.get(Friendship, friendship_id)
    if not f or (f.addressee_id != user.id and f.requester_id != user.id):
        raise HTTPException(status_code=404, detail="Verzoek niet gevonden")
    if f.status != "pending":
        raise HTTPException(status_code=409, detail="Verzoek is al verwerkt")
    await db.delete(f)
    await db.commit()
    return {"ok": True}


# ── Friends list ──────────────────────────────────────────────────────────────

@router.get("")
async def list_friends(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Friendship).where(
            Friendship.status == "accepted",
            or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
        )
    )
    friendships = result.scalars().all()
    out = []
    for f in friendships:
        friend_id = f.addressee_id if f.requester_id == user.id else f.requester_id
        friend = await db.get(User, friend_id)
        if friend:
            out.append({"friendship_id": f.id, "user": _user_summary(friend)})
    return {"friends": out}


@router.delete("/{friend_id}")
async def remove_friend(
    friend_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    f = await _get_accepted_friendship(db, user.id, friend_id)
    if not f:
        raise HTTPException(status_code=404, detail="Vriend niet gevonden")
    await db.delete(f)
    await db.commit()
    return {"ok": True}


# ── Friend activity data ──────────────────────────────────────────────────────

@router.get("/{friend_id}/activities")
async def get_friend_activities(
    friend_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await _get_accepted_friendship(db, user.id, friend_id):
        raise HTTPException(status_code=403, detail="Geen toegang tot activiteiten van deze gebruiker")
    from app.models.garmin_activity import GarminActivity
    from sqlalchemy import select
    result = await db.execute(
        select(GarminActivity)
        .where(GarminActivity.user_id == friend_id)
        .order_by(GarminActivity.start_time.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "activity_id": r.activity_id,
            "activity_name": r.activity_name or "",
            "activity_type": r.activity_type,
            "start_time": r.start_time.isoformat() if r.start_time else "",
            "distance_km": r.distance_km or 0,
            "duration_seconds": r.duration_seconds,
            "average_pace_per_km": r.avg_pace_per_km,
            "average_heart_rate": r.avg_heart_rate,
        }
        for r in rows
    ]


@router.get("/{friend_id}/activity/{activity_id}")
async def get_friend_activity_detail(
    friend_id: int,
    activity_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not await _get_accepted_friendship(db, user.id, friend_id):
        raise HTTPException(status_code=403, detail="Geen toegang tot activiteiten van deze gebruiker")
    try:
        data = await garmin_service.fetch_activity_detail(db, friend_id, activity_id)
        data["ai_feedback"] = None  # never expose friend's AI feedback
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Activiteit ophalen mislukt: {e}")
