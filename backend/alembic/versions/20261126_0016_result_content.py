"""Add nullable content snapshots without changing old delivery records."""
from alembic import op
import sqlalchemy as sa

revision = "20261126_0016"
down_revision = "20261126_0015"
branch_labels = depends_on = None

columns = [("game_sessions", "result_content_version", sa.Integer()),
           ("game_result_deliveries", "content_anchor", sa.JSON()),
           ("game_result_delivery_entries", "result_content", sa.JSON())]


def upgrade():
    for table, name, typ in columns:
        op.add_column(table, sa.Column(name, typ, nullable=True))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM game_sessions WHERE result_content_version IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Downgrade would remove saved result content")
    for table, name, _ in reversed(columns):
        op.drop_column(table, name)
