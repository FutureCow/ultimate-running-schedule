from datetime import datetime, date
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Date,
    ForeignKey, Text, JSON, func, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from app.database import Base


class PlanGoal(str, enum.Enum):
    FIVE_K = "5k"
    TEN_K = "10k"
    HALF_MARATHON = "half_marathon"
    MARATHON = "marathon"


class WorkoutType(str, enum.Enum):
    EASY_RUN = "easy_run"
    LONG_RUN = "long_run"
    TEMPO = "tempo"
    INTERVAL = "interval"
    RECOVERY = "recovery"
    RACE = "race"
    REST = "rest"


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(String(50), nullable=False)
    target_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_pace_per_km: Mapped[str | None] = mapped_column(String(20), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    weekly_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    weekly_runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    injuries: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_days: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["monday","wednesday",...]
    long_run_day: Mapped[str | None] = mapped_column(String(20), nullable=True)
    duration_weeks: Mapped[int] = mapped_column(Integer, default=12)
    surface: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Full AI-generated plan stored as JSON
    plan_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    garmin_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="plans")
    sessions: Mapped[list["WorkoutSession"]] = relationship(
        "WorkoutSession", back_populates="plan", cascade="all, delete-orphan",
        lazy="selectin", order_by="WorkoutSession.week_number, WorkoutSession.day_number"
    )


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)   # 1-7
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    workout_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Pace ranges as JSON: {"warmup": "6:00-6:30", "main": "5:10-5:20", "cooldown": "6:00-6:30"}
    target_paces: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Interval structure: [{"reps": 6, "distance_m": 400, "pace": "4:30-4:40", "rest_seconds": 90}]
    intervals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    garmin_workout_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    garmin_pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plan: Mapped["Plan"] = relationship("Plan", back_populates="sessions")
