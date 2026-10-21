"""Add opt-in local result delivery and acknowledgement state."""

from alembic import op
import sqlalchemy as sa


revision = "20261021_0013"
down_revision = "20261019_0012"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("game_sessions") as batch_op:
        batch_op.add_column(sa.Column("result_delivery_version", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_game_sessions_result_delivery_version",
            "result_delivery_version IS NULL OR result_delivery_version = 1",
        )
    op.create_table(
        "game_result_deliveries",
        sa.Column("session_id", sa.String(36), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("generation", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_mode", sa.String(16), nullable=False),
        sa.Column("acked_ordinal", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("terminal_ordinal", sa.Integer(), nullable=True),
        sa.CheckConstraint("version = 1", name="ck_game_result_deliveries_version"),
        sa.CheckConstraint("content_mode = 'unbound'", name="ck_game_result_deliveries_content_mode"),
        sa.CheckConstraint("acked_ordinal >= 0", name="ck_game_result_deliveries_acked"),
        sa.CheckConstraint("revision >= 0", name="ck_game_result_deliveries_revision"),
        sa.CheckConstraint("terminal_ordinal IS NULL OR terminal_ordinal >= 1", name="ck_game_result_deliveries_terminal"),
    )
    op.create_index("ix_game_result_deliveries_generation", "game_result_deliveries", ["generation"])
    op.create_table(
        "game_result_delivery_entries",
        sa.Column("session_id", sa.String(36), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("hand_start_log_offset", sa.Integer(), nullable=True),
        sa.Column("display_index", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("ordinal >= 1", name="ck_game_result_delivery_entries_ordinal"),
        sa.CheckConstraint("kind IN ('hand', 'settlement')", name="ck_game_result_delivery_entries_kind"),
        sa.CheckConstraint(
            "(kind = 'hand' AND hand_start_log_offset IS NOT NULL AND display_index IS NOT NULL) OR "
            "(kind = 'settlement' AND hand_start_log_offset IS NULL AND display_index IS NULL)",
            name="ck_game_result_delivery_entries_identity",
        ),
        sa.UniqueConstraint("event_id", name="uq_game_result_delivery_entries_event_id"),
        sa.UniqueConstraint("session_id", "hand_start_log_offset", "display_index", name="uq_game_result_delivery_entries_hand_display"),
    )
    op.create_index(
        "uq_game_result_delivery_entries_settlement", "game_result_delivery_entries", ["session_id"], unique=True,
        sqlite_where=sa.text("kind = 'settlement'"), postgresql_where=sa.text("kind = 'settlement'"),
    )


def downgrade():
    op.drop_index("uq_game_result_delivery_entries_settlement", table_name="game_result_delivery_entries")
    op.drop_table("game_result_delivery_entries")
    op.drop_index("ix_game_result_deliveries_generation", table_name="game_result_deliveries")
    op.drop_table("game_result_deliveries")
    with op.batch_alter_table("game_sessions") as batch_op:
        batch_op.drop_constraint("ck_game_sessions_result_delivery_version", type_="check")
        batch_op.drop_column("result_delivery_version")
