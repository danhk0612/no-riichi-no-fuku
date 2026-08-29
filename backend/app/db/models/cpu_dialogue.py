from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .cpu_character import CpuCharacter


class CpuDialogue(TimestampMixin, Base):
    __tablename__ = "cpu_dialogues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cpu_character_id: Mapped[int] = mapped_column(
        ForeignKey("cpu_characters.id", ondelete="CASCADE"), index=True
    )
    event_key: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    cpu_character: Mapped[CpuCharacter] = relationship(back_populates="dialogues")
