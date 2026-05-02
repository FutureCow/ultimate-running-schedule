from datetime import datetime
import enum
from sqlalchemy import String, Boolean, DateTime, Integer, Float, Text, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserTier(str, enum.Enum):
    BASE  = "base"
    TEMPO = "tempo"
    ELITE = "elite"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    tier: Mapped[str] = mapped_column(String(20), default="elite", server_default="elite", nullable=False)
    password_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Athlete profile — persisted so new plans are pre-filled
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    weekly_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    weekly_runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    injuries: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    garmin_credential: Mapped["GarminCredential"] = relationship(
        "GarminCredential", back_populates="user", uselist=False, lazy="selectin"
    )
    plans: Mapped[list["Plan"]] = relationship("Plan", back_populates="user", lazy="selectin")
