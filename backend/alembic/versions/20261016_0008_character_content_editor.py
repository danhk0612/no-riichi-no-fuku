"""Store explicit character prompt edits without applying pack revisions."""

from alembic import op
import sqlalchemy as sa

revision = "20261016_0008"
down_revision = "20261016_0007"
branch_labels = None
depends_on = None


def timestamps():
    return [
        sa.Column(key, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
        for key in ("created_at", "updated_at")
    ]


def upgrade():
    op.create_table(
        "character_content",
        sa.Column("cpu_id", sa.Integer(), sa.ForeignKey("cpu_characters.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("pack_revision_id", sa.String(36), sa.ForeignKey("content_pack_revisions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("prompts", sa.JSON(), nullable=False),
        sa.Column("overrides", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "character_level_framing",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cpu_id", sa.Integer(), sa.ForeignKey("cpu_characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("positive", sa.Text(), nullable=False),
        sa.Column("negative", sa.Text(), nullable=False),
        sa.Column("overrides", sa.JSON(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("cpu_id", "level", "kind", name="uq_character_framing"),
        sa.CheckConstraint("level BETWEEN 0 AND 3", name="ck_character_framing_level"),
        sa.CheckConstraint("kind IN ('profile','full_body','cg')", name="ck_character_framing_kind"),
    )


def downgrade():
    op.drop_table("character_level_framing")
    op.drop_table("character_content")
