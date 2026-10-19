from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GameHandResult(Base):
    __tablename__ = "game_hand_results"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_game_hand_results_sequence"),
        CheckConstraint("sequence >= 1", name="ck_game_hand_results_sequence"),
        CheckConstraint("hand_start_log_offset >= 0", name="ck_game_hand_results_start_offset"),
        CheckConstraint("hand_end_log_offset > hand_start_log_offset", name="ck_game_hand_results_end_offset"),
        CheckConstraint("source_action_version >= 0", name="ck_game_hand_results_action_version"),
    )

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    hand_start_log_offset: Mapped[int] = mapped_column(Integer, primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    hand_end_log_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    source_action_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
