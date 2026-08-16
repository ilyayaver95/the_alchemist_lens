from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now())

    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )


class Favorite(Base):
    __tablename__ = "favorites"
    # One row per drink per user; re-saving the same drink is a no-op, not a dupe.
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key", name="uq_favorite_per_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(20))  # analyze | classic | invention
    slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    drink_name: Mapped[str] = mapped_column(String(200))
    dedupe_key: Mapped[str] = mapped_column(String(64))
    # The whole AnalyzeResponse as JSON text, so replaying a favorite needs no
    # recomputation and renders through exactly the same frontend code path.
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="favorites")
