"""Retain per-slot image requests and local overrides without modifying pack files."""
from alembic import op
import sqlalchemy as sa

revision = "20261126_0017"
down_revision = "20261126_0016"
branch_labels = depends_on = None


def upgrade():
    op.create_table("stage_images",
        sa.Column("cpu_id", sa.Integer, sa.ForeignKey("cpu_characters.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("level", sa.Integer, primary_key=True), sa.Column("kind", sa.String(12), primary_key=True),
        sa.Column("ticket", sa.String(36), nullable=False), sa.Column("inputs", sa.JSON, nullable=False),
        sa.Column("endpoint", sa.String, nullable=False), sa.Column("content_revision", sa.Integer, nullable=False),
        sa.Column("media_id", sa.String(36), sa.ForeignKey("local_media_assets.id", ondelete="RESTRICT")),
        sa.Column("digest", sa.String(64)))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM stage_images LIMIT 1")).first():
        raise RuntimeError("Downgrade would remove saved stage images")
    op.drop_table("stage_images")
