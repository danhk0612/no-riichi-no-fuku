"""Add shared clothing-state and pose prompt management."""

from alembic import op
import sqlalchemy as sa


revision = "20261018_0011"
down_revision = "20261018_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shared_prompt_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("positive", sa.Text(), nullable=False),
        sa.Column("negative", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("level BETWEEN 0 AND 3", name="ck_shared_prompt_level"),
        sa.CheckConstraint("kind IN ('clothing_state','pose')", name="ck_shared_prompt_kind"),
        sa.CheckConstraint("revision >= 1", name="ck_shared_prompt_revision"),
    )
    op.create_table(
        "character_prompt_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cpu_id", sa.Integer(), sa.ForeignKey("cpu_characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("cpu_id", "level", "kind", name="uq_prompt_candidates_scope"),
        sa.CheckConstraint("level BETWEEN 0 AND 3", name="ck_prompt_candidates_level"),
        sa.CheckConstraint("kind IN ('clothing_state','pose')", name="ck_prompt_candidates_kind"),
        sa.CheckConstraint("revision >= 1", name="ck_prompt_candidates_revision"),
    )
    op.create_table(
        "character_prompt_candidate_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("candidate_set_id", sa.String(36), sa.ForeignKey("character_prompt_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("shared_prompt_items.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("candidate_set_id", "item_id", name="uq_prompt_candidate_entry"),
    )
    op.create_table(
        "shared_prompt_defaults",
        sa.Column("level", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(20), primary_key=True),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("shared_prompt_items.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("level BETWEEN 0 AND 3", name="ck_shared_prompt_default_level"),
        sa.CheckConstraint("kind IN ('clothing_state','pose')", name="ck_shared_prompt_default_kind"),
        sa.CheckConstraint("revision >= 1", name="ck_shared_prompt_default_revision"),
    )


def downgrade():
    op.drop_table("shared_prompt_defaults")
    op.drop_table("character_prompt_candidate_entries")
    op.drop_table("character_prompt_candidates")
    op.drop_table("shared_prompt_items")
