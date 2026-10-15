from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .cpu_character import CpuCharacter
    from .user import User


class UserCpuProgress(TimestampMixin, Base):
    __tablename__ = "user_cpu_progress"
    __table_args__ = (
        CheckConstraint(
            "defeat_stage >= 0 AND defeat_stage <= 3",
            name="ck_user_cpu_progress_defeat_stage",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    cpu_character_id: Mapped[int] = mapped_column(
        ForeignKey("cpu_characters.id", ondelete="CASCADE"), primary_key=True
    )
    defeat_stage: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship(back_populates="cpu_progress")
    cpu_character: Mapped[CpuCharacter] = relationship(back_populates="progress")
