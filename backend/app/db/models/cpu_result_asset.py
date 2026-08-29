from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .cpu_character import CpuCharacter


class CpuResultAsset(TimestampMixin, Base):
    __tablename__ = "cpu_result_assets"
    __table_args__ = (
        CheckConstraint(
            "defeat_stage >= 1 AND defeat_stage <= 3",
            name="ck_cpu_result_assets_defeat_stage",
        ),
        UniqueConstraint(
            "cpu_character_id",
            "defeat_stage",
            name="uq_cpu_result_assets_character_stage",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cpu_character_id: Mapped[int] = mapped_column(
        ForeignKey("cpu_characters.id", ondelete="CASCADE"), index=True
    )
    defeat_stage: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    cpu_character: Mapped[CpuCharacter] = relationship(back_populates="result_assets")
