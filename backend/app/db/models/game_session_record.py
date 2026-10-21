from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    JSON,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

from .mixins import TimestampMixin


class GameSessionRecord(TimestampMixin, Base):
    __tablename__ = "game_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="ck_game_sessions_status",
        ),
        CheckConstraint(
            "hand_results_version IS NULL OR hand_results_version = 1",
            name="ck_game_sessions_hand_results_version",
        ),
        CheckConstraint(
            "result_delivery_version IS NULL OR result_delivery_version = 1",
            name="ck_game_sessions_result_delivery_version",
        ),
        Index(
            "uq_game_sessions_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    match_seed: Mapped[int] = mapped_column(BigInteger)
    cpu_choices: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    players: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    human_action_indices: Mapped[list[int]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), index=True)
    scores: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    ranks: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    settlement: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    play_generation: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    rules_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    presentation: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    hand_results_version: Mapped[int | None] = mapped_column(nullable=True)
    result_delivery_version: Mapped[int | None] = mapped_column(nullable=True)
