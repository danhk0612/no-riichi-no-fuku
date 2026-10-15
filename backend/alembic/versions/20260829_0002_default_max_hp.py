"""Set the initial player maximum HP.

Revision ID: 20260829_0002
Revises: 20260829_0001
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260829_0002"
down_revision: str | None = "20260829_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO game_settings (key, value) "
            "VALUES ('player_max_hp', '3')"
        )
    )


def downgrade() -> None:
    game_settings = sa.table(
        "game_settings",
        sa.column("key", sa.String()),
    )
    op.execute(game_settings.delete().where(game_settings.c.key == "player_max_hp"))
