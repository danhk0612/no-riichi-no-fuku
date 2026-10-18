"""Add optional character measurements without changing existing content."""

from alembic import op
import sqlalchemy as sa


revision = "20261018_0010"
down_revision = "20261016_0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "character_content",
        sa.Column("measurements_cm", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column("character_content", "measurements_cm")
