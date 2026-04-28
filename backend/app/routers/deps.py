from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import auth_service
from app.models.user import User

bearer_scheme = HTTPBearer()

_TIER_RANK = {"base": 0, "tempo": 1, "elite": 2}

TIER_NAMES = {
    "base":  "Base",
    "tempo": "Tempo",
    "elite": "Elite",
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = auth_service.decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await auth_service.get_user_by_id(db, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_tier(min_tier: str):
    """Dependency factory: raises 403 if user's tier is below min_tier."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if _TIER_RANK.get(user.tier, 0) < _TIER_RANK.get(min_tier, 0):
            needed = TIER_NAMES.get(min_tier, min_tier)
            raise HTTPException(
                status_code=403,
                detail=f"UPGRADE_REQUIRED:{min_tier}:Dit vereist een {needed}-abonnement",
            )
        return user
    return _check
