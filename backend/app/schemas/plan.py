from pydantic import BaseModel, ConfigDict, model_validator
from datetime import datetime, date
from typing import Literal, Optional, Any

from app.schemas.common import FeedbackTone

# A goal is either one of the fixed race distances or "custom", in which case
# custom_distance_km carries the distance the athlete picked.
CUSTOM_GOAL = "custom"
MIN_CUSTOM_DISTANCE_KM = 1.0
MAX_CUSTOM_DISTANCE_KM = 100.0

GoalKind = Literal["race", "fitness"]


def _check_custom_distance(model):
    """A custom goal needs a distance; a preset goal must not carry one."""
    if model.goal == CUSTOM_GOAL:
        distance = model.custom_distance_km
        if distance is None:
            raise ValueError("custom_distance_km is required when goal is 'custom'")
        if not MIN_CUSTOM_DISTANCE_KM <= distance <= MAX_CUSTOM_DISTANCE_KM:
            raise ValueError(
                f"custom_distance_km must be between {MIN_CUSTOM_DISTANCE_KM:g} "
                f"and {MAX_CUSTOM_DISTANCE_KM:g} km"
            )
    elif model.goal is not None:
        # Switching back to a preset must not leave the old km value behind
        model.custom_distance_km = None
    return model


class StrengthPreferences(BaseModel):
    enabled: bool = False
    location: Optional[str] = None        # bodyweight / home_equipment / gym
    type: Optional[str] = None            # core_stability / max_strength / plyometrics / injury_prevention / full_body
    days: Optional[list[int]] = None      # [1, 3, 5] — day numbers (1=Mon)
    equipment: Optional[list[str]] = None # ["dumbbells", "resistance_bands", ...] — only for home_equipment
    notes: Optional[str] = None          # free-text athlete preferences for strength


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
    completed_at: Optional[datetime] = None
    garmin_activity_id: Optional[str] = None


class PlanCreate(BaseModel):
    name: str
    goal: str
    custom_distance_km: Optional[float] = None
    goal_kind: GoalKind = "race"
    # None means "follow the athlete's profile default"
    feedback_tone: Optional[FeedbackTone] = None
    target_time_seconds: Optional[int] = None
    target_pace_per_km: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    weekly_km: Optional[float] = None
    weekly_runs: Optional[int] = None
    injuries: Optional[str] = None
    extra_notes: Optional[str] = None
    training_days: Optional[list[str]] = None
    long_run_day: Optional[str] = None
    duration_weeks: int = 12
    surface: Optional[str] = None
    start_date: Optional[date] = None
    race_date: Optional[date] = None
    language: str = "nl"
    strength: Optional[StrengthPreferences] = None

    @model_validator(mode="after")
    def _validate_custom_distance(self):
        return _check_custom_distance(self)


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    target_paces: Optional[dict] = None
    scheduled_date: Optional[date] = None


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    custom_distance_km: Optional[float] = None
    goal_kind: Optional[GoalKind] = None
    feedback_tone: Optional[FeedbackTone] = None
    target_time_seconds: Optional[int] = None
    target_pace_per_km: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    weekly_km: Optional[float] = None
    weekly_runs: Optional[int] = None
    injuries: Optional[str] = None
    extra_notes: Optional[str] = None
    training_days: Optional[list[str]] = None
    long_run_day: Optional[str] = None
    duration_weeks: Optional[int] = None
    surface: Optional[str] = None
    start_date: Optional[date] = None
    race_date: Optional[date] = None
    language: Optional[str] = None

    @model_validator(mode="after")
    def _validate_custom_distance(self):
        return _check_custom_distance(self)


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    user_id: int
    name: str
    goal: str
    custom_distance_km: Optional[float] = None
    goal_kind: str = "race"
    feedback_tone: Optional[str] = None
    target_time_seconds: Optional[int] = None
    target_pace_per_km: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    weekly_km: Optional[float] = None
    weekly_runs: Optional[int] = None
    injuries: Optional[str] = None
    extra_notes: Optional[str] = None
    training_days: Optional[list] = None
    long_run_day: Optional[str] = None
    duration_weeks: int
    surface: Optional[str] = None
    start_date: Optional[date] = None
    race_date: Optional[date] = None
    plan_json: Optional[Any] = None
    garmin_synced: bool
    strength_enabled: bool = False
    strength_location: Optional[str] = None
    strength_type: Optional[str] = None
    strength_days: Optional[list] = None
    strength_equipment: Optional[list] = None
    created_at: datetime
    updated_at: datetime
    sessions: list[WorkoutSessionResponse] = []
