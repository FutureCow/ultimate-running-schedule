from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from typing import Optional, Any


class TargetPaces(BaseModel):
    warmup: Optional[str] = None
    main: str
    cooldown: Optional[str] = None
    note: Optional[str] = None


class IntervalStep(BaseModel):
    reps: int
    distance_m: Optional[int] = None
    duration_seconds: Optional[int] = None
    pace: str
    rest_seconds: int = 90


class WorkoutSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    week_number: int
    day_number: int
    scheduled_date: Optional[date] = None
    workout_type: str
    title: str
    description: Optional[str] = None
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    target_paces: Optional[dict] = None
    intervals: Optional[list] = None
    garmin_workout_id: Optional[str] = None
    garmin_pushed_at: Optional[datetime] = None


class PlanCreate(BaseModel):
    name: str
    goal: str
    target_time_seconds: Optional[int] = None
    target_pace_per_km: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    weekly_km: Optional[float] = None
    weekly_runs: Optional[int] = None
    injuries: Optional[str] = None
    training_days: Optional[list[str]] = None
    long_run_day: Optional[str] = None
    duration_weeks: int = 12
    surface: Optional[str] = None
    start_date: Optional[date] = None


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    target_time_seconds: Optional[int] = None
    target_pace_per_km: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    weekly_km: Optional[float] = None
    weekly_runs: Optional[int] = None
    injuries: Optional[str] = None
    training_days: Optional[list[str]] = None
    long_run_day: Optional[str] = None
    duration_weeks: Optional[int] = None
    surface: Optional[str] = None
    start_date: Optional[date] = None


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    goal: str
    target_time_seconds: Optional[int] = None
    target_pace_per_km: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    weekly_km: Optional[float] = None
    weekly_runs: Optional[int] = None
    injuries: Optional[str] = None
    training_days: Optional[list] = None
    long_run_day: Optional[str] = None
    duration_weeks: int
    surface: Optional[str] = None
    start_date: Optional[date] = None
    plan_json: Optional[Any] = None
    garmin_synced: bool
    created_at: datetime
    updated_at: datetime
    sessions: list[WorkoutSessionResponse] = []
