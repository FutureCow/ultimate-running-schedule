from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class GarminCredential(Base):
    __tablename__ = "garmin_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    # Garmin email & password stored encrypted (Fernet)
    encrypted_email: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    # Serialized MFA/OAuth tokens (Fernet-encrypted JSON)
    encrypted_tokens: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="garmin_credential")
