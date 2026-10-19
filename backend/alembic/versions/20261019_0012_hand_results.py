"""Persist source-verified hand result facts."""

from alembic import op
import sqlalchemy as sa


revision = "20261019_0012"
down_revision = "20261018_0011"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("game_sessions") as batch_op:
        batch_op.add_column(sa.Column("hand_results_version", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_game_sessions_hand_results_version",
            "hand_results_version IS NULL OR hand_results_version = 1",
        )
    op.create_table(
        "game_hand_results",
        sa.Column("session_id", sa.String(36), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("hand_start_log_offset", sa.Integer(), primary_key=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("hand_end_log_offset", sa.Integer(), nullable=False),
        sa.Column("source_action_version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("session_id", "sequence", name="uq_game_hand_results_sequence"),
        sa.CheckConstraint("sequence >= 1", name="ck_game_hand_results_sequence"),
        sa.CheckConstraint("hand_start_log_offset >= 0", name="ck_game_hand_results_start_offset"),
        sa.CheckConstraint("hand_end_log_offset > hand_start_log_offset", name="ck_game_hand_results_end_offset"),
        sa.CheckConstraint("source_action_version >= 0", name="ck_game_hand_results_action_version"),
    )


def downgrade():
    op.drop_table("game_hand_results")
    with op.batch_alter_table("game_sessions") as batch_op:
        batch_op.drop_constraint("ck_game_sessions_hand_results_version", type_="check")
        batch_op.drop_column("hand_results_version")
