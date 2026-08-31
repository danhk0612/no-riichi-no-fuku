"""Persist authoritative game session action logs.

Revision ID: 20260830_0003
Revises: 20260829_0002
Create Date: 2026-08-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260830_0003"
down_revision: str | None = "20260829_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("match_seed", sa.BigInteger(), nullable=False),
        sa.Column("cpu_choices", sa.JSON(), nullable=False),
        sa.Column("players", sa.JSON(), nullable=False),
        sa.Column("human_action_indices", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("scores", sa.JSON(), nullable=True),
        sa.Column("ranks", sa.JSON(), nullable=True),
        sa.Column("settlement", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed')",
            name="ck_game_sessions_status",
        ),
    )
    op.create_index("ix_game_sessions_user_id", "game_sessions", ["user_id"])
    op.create_index("ix_game_sessions_status", "game_sessions", ["status"])
    op.create_index(
        "uq_game_sessions_active_user",
        "game_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_game_sessions_active_user", table_name="game_sessions")
    op.drop_index("ix_game_sessions_status", table_name="game_sessions")
    op.drop_index("ix_game_sessions_user_id", table_name="game_sessions")
    op.drop_table("game_sessions")
