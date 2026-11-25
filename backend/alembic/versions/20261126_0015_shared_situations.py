"""Allow explicitly event-bound shared situations."""
from alembic import op
import sqlalchemy as sa

revision = "20261126_0015"
down_revision = "20261030_0014"
branch_labels = depends_on = None

TABLES = (("shared_prompt_items", "ck_shared_prompt_kind"),
          ("character_prompt_candidates", "ck_prompt_candidates_kind"),
          ("shared_prompt_defaults", "ck_shared_prompt_default_kind"))


def change(expand):
    db = op.get_bind()
    if not expand and any(db.execute(sa.text(f"SELECT 1 FROM {table} WHERE kind='situation' LIMIT 1")).first() for table, _ in TABLES):
        raise RuntimeError("Downgrade would remove situation data")
    # SQLite batch rebuild drops parent tables. Preserve inbound FK rows including IDs first.
    sqlite = db.dialect.name == "sqlite"
    children = ("character_prompt_candidate_entries", "shared_prompt_defaults")
    if sqlite:
        for table in children:
            op.execute(f"CREATE TEMP TABLE saved_{table} AS SELECT * FROM {table}")
            op.execute(f"DELETE FROM {table}")
    for table, name in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="check")
            batch.create_check_constraint(name, "kind IN ('clothing_state','pose','situation')" if expand else "kind IN ('clothing_state','pose')")
            if table == "shared_prompt_items":
                if expand:
                    batch.add_column(sa.Column("allowed_events", sa.JSON(), nullable=True))
                else:
                    batch.drop_column("allowed_events")
    if sqlite:
        for table in children:
            op.execute(f"INSERT INTO {table} SELECT * FROM saved_{table}")
            op.execute(f"DROP TABLE saved_{table}")


def upgrade():
    change(True)


def downgrade():
    change(False)
