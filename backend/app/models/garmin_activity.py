from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class GarminActivity(Base):
    __tablename__ = "garmin_activities"
    __table_args__ = (UniqueConstraint("user_id", "activity_id", name="uq_user_activity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    activity_name: Mapped[str | None] = mapped_column(String(255))
    activity_type: Mapped[str | None] = mapped_column(String(50))
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_km: Mapped[float | None] = mapped_column(Float)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    avg_pace_per_km: Mapped[str | None] = mapped_column(String(20))
    avg_heart_rate: Mapped[int | None] = mapped_column(Integer)
    max_heart_rate: Mapped[int | None] = mapped_column(Integer)
    avg_cadence: Mapped[int | None] = mapped_column(Integer)
    elevation_gain_m: Mapped[float | None] = mapped_column(Float)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
