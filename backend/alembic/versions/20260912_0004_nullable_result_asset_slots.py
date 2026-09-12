"""Allow empty result CG metadata slots.

Revision ID: 20260912_0004
Revises: 20260830_0003
Create Date: 2026-09-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260912_0004"
down_revision: str | None = "20260830_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("cpu_result_assets") as batch_op:
        batch_op.alter_column(
            "storage_key",
            existing_type=sa.String(length=512),
            nullable=True,
        )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM cpu_result_assets WHERE storage_key IS NULL")
    )
    with op.batch_alter_table("cpu_result_assets") as batch_op:
        batch_op.alter_column(
            "storage_key",
            existing_type=sa.String(length=512),
            nullable=False,
        )
