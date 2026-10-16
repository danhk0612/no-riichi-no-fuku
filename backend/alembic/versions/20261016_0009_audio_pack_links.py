"""Add per-character voice pack selection links."""

from alembic import op
import sqlalchemy as sa

revision = "20261016_0009"
down_revision = "20261016_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "character_voice_links",
        sa.Column("cpu_id", sa.Integer(), sa.ForeignKey("cpu_characters.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("default_pack_id", sa.String(36), sa.ForeignKey("content_packs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("selected_pack_id", sa.String(36), sa.ForeignKey("content_packs.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("selection_mode", sa.String(12), nullable=False, server_default="default"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("selection_mode IN ('default','selected','off')", name="ck_character_voice_selection_mode"),
        sa.CheckConstraint("revision >= 1", name="ck_character_voice_revision"),
    )


def downgrade():
    op.drop_table("character_voice_links")
