from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .cpu_dialogue import CpuDialogue
    from .cpu_result_asset import CpuResultAsset
    from .user_cpu_progress import UserCpuProgress


class CpuCharacter(TimestampMixin, Base):
    __tablename__ = "cpu_characters"
    __table_args__ = (
        CheckConstraint("age_adult = true", name="ck_cpu_characters_adult"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    age_adult: Mapped[bool] = mapped_column(Boolean, default=True)
    style: Mapped[str] = mapped_column(String(40))
    short_description: Mapped[str] = mapped_column(String(255))
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_image_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    aggression: Mapped[float] = mapped_column(Float)
    defense: Mapped[float] = mapped_column(Float)
    call_preference: Mapped[float] = mapped_column(Float)
    riichi_preference: Mapped[float] = mapped_column(Float)
    hand_value_preference: Mapped[float] = mapped_column(Float)
    speed_preference: Mapped[float] = mapped_column(Float)

    progress: Mapped[list[UserCpuProgress]] = relationship(back_populates="cpu_character")
    dialogues: Mapped[list[CpuDialogue]] = relationship(
        back_populates="cpu_character", cascade="all, delete-orphan"
    )
    result_assets: Mapped[list[CpuResultAsset]] = relationship(
        back_populates="cpu_character", cascade="all, delete-orphan"
    )
