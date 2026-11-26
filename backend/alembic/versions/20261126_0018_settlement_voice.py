"""Remember whether the match settlement voice was offered."""
from alembic import op
import sqlalchemy as sa

revision = "20261126_0018"
down_revision = "20261126_0017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("game_result_deliveries", sa.Column("defeat_voice_claimed", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("game_result_deliveries", "defeat_voice_claimed")
