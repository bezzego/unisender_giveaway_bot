from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, Integer, Boolean, UniqueConstraint, func, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("email", name="uq_participants_email"),
        UniqueConstraint("telegram_id", name="uq_participants_telegram_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # reward
    reward_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # cinema | guide | promo
    promo_code: Mapped[str | None] = mapped_column(String(128), nullable=True)


class PromoCode(Base):
    """
    Storage for limited cinema promo codes.
    """
    __tablename__ = "promo_codes"
    __table_args__ = (UniqueConstraint("code", name="uq_promo_codes_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="cinema")  # cinema
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    used_by_participant_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)