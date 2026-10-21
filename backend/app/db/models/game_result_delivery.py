from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GameResultDelivery(Base):
    __tablename__ = "game_result_deliveries"
    __table_args__ = (
        CheckConstraint("version = 1", name="ck_game_result_deliveries_version"),
        CheckConstraint("content_mode = 'unbound'", name="ck_game_result_deliveries_content_mode"),
        CheckConstraint("acked_ordinal >= 0", name="ck_game_result_deliveries_acked"),
        CheckConstraint("revision >= 0", name="ck_game_result_deliveries_revision"),
        CheckConstraint("terminal_ordinal IS NULL OR terminal_ordinal >= 1", name="ck_game_result_deliveries_terminal"),
    )

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    generation: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="unbound")
    acked_ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    terminal_ordinal: Mapped[int | None] = mapped_column(Integer, nullable=True)


class GameResultDeliveryEntry(Base):
    __tablename__ = "game_result_delivery_entries"
    __table_args__ = (
        CheckConstraint("ordinal >= 1", name="ck_game_result_delivery_entries_ordinal"),
        CheckConstraint("kind IN ('hand', 'settlement')", name="ck_game_result_delivery_entries_kind"),
        CheckConstraint(
            "(kind = 'hand' AND hand_start_log_offset IS NOT NULL AND display_index IS NOT NULL) OR "
            "(kind = 'settlement' AND hand_start_log_offset IS NULL AND display_index IS NULL)",
            name="ck_game_result_delivery_entries_identity",
        ),
        UniqueConstraint("event_id", name="uq_game_result_delivery_entries_event_id"),
        UniqueConstraint(
            "session_id", "hand_start_log_offset", "display_index",
            name="uq_game_result_delivery_entries_hand_display",
        ),
        Index(
            "uq_game_result_delivery_entries_settlement",
            "session_id", unique=True,
            sqlite_where=text("kind = 'settlement'"),
            postgresql_where=text("kind = 'settlement'"),
        ),
    )

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    hand_start_log_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    display_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
