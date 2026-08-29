from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .user_cpu_progress import UserCpuProgress


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("current_hp IS NULL OR current_hp >= 0", name="ck_users_current_hp"),
        CheckConstraint("max_hp IS NULL OR max_hp > 0", name="ck_users_max_hp"),
        CheckConstraint(
            "current_hp IS NULL OR max_hp IS NULL OR current_hp <= max_hp",
            name="ck_users_hp_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    player_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    profile_image_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    current_hp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="member", index=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    cpu_progress: Mapped[list[UserCpuProgress]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
