from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class GarminCredentialCreate(BaseModel):
    email: str
    password: str


class GarminCredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_sync_at: Optional[datetime] = None
    created_at: datetime
    # Never expose email/password


class GarminSyncResponse(BaseModel):
    synced: bool
    activity_count: int
    last_sync_at: datetime
    summary: dict


class GarminActivity(BaseModel):
    activity_id: str
    activity_name: str
    start_time: datetime
    distance_km: float
    duration_seconds: int
    average_pace_per_km: Optional[str] = None
    average_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    average_cadence: Optional[int] = None
    elevation_gain_m: Optional[float] = None
    activity_type: str


class GarminPushRequest(BaseModel):
    session_ids: list[int]


class GarminPushWeekRequest(BaseModel):
    plan_id: str  # public_id (UUID)
    week_number: int
