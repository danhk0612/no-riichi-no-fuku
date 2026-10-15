"""Add the Windows local play generation and fixed roster."""

from collections.abc import Sequence
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "20261015_0005"
down_revision: str | None = "20260912_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("game_sessions") as batch:
        batch.add_column(sa.Column("play_generation", sa.String(36), nullable=True))
        batch.add_column(sa.Column("rules_snapshot", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("presentation", sa.JSON(), nullable=True))
        batch.drop_constraint("ck_game_sessions_status", type_="check")
        batch.create_check_constraint(
            "ck_game_sessions_status", "status IN ('active', 'completed', 'cancelled')"
        )
        batch.create_index("ix_game_sessions_play_generation", ["play_generation"])

    op.create_table(
        "local_play_states",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("generation", sa.String(36), nullable=False),
        sa.Column("phase", sa.String(24), nullable=False),
        sa.Column("ending_event_id", sa.String(36), nullable=True),
        sa.Column("ending_payload", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "phase IN ('roster_required', 'progress', 'ending_pending', 'omake')",
            name="ck_local_play_states_phase",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("generation"),
        sa.UniqueConstraint("ending_event_id"),
    )
    op.create_table(
        "local_play_roster",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("cpu_character_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["cpu_character_id"], ["cpu_characters.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("user_id", "cpu_character_id"),
    )


def downgrade() -> None:
    op.drop_table("local_play_roster")
    op.drop_table("local_play_states")
    with op.batch_alter_table("game_sessions") as batch:
        batch.drop_index("ix_game_sessions_play_generation")
        batch.drop_column("presentation")
        batch.drop_column("rules_snapshot")
        batch.drop_column("play_generation")
        batch.drop_constraint("ck_game_sessions_status", type_="check")
        batch.create_check_constraint(
            "ck_game_sessions_status", "status IN ('active', 'completed')"
        )
