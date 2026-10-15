from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LocalPlayState(Base):
    __tablename__ = "local_play_states"
    __table_args__ = (
        CheckConstraint(
            "phase IN ('roster_required', 'progress', 'ending_pending', 'omake')",
            name="ck_local_play_states_phase",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    generation: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    phase: Mapped[str] = mapped_column(String(24), nullable=False)
    ending_event_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    ending_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)


class LocalPlayRoster(Base):
    __tablename__ = "local_play_roster"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    cpu_character_id: Mapped[int] = mapped_column(
        ForeignKey("cpu_characters.id", ondelete="RESTRICT"), primary_key=True
    )
