"""Add pack registry without applying or migrating existing content."""

from alembic import op
import sqlalchemy as sa

revision = "20261016_0007"
down_revision = "20261016_0006"
branch_labels = None
depends_on = None


def timestamps():
    return [
        sa.Column(
            key,
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )
        for key in ("created_at", "updated_at")
    ]


def upgrade():
    op.create_table(
        "content_packs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("namespace", sa.String(80), nullable=False),
        sa.Column("pack_id", sa.String(80), nullable=False),
        *timestamps(),
        sa.UniqueConstraint(
            "kind", "namespace", "pack_id", name="uq_content_pack_identity"
        ),
        sa.CheckConstraint(
            "kind IN ('character','sfx','bgm','voice')", name="ck_content_pack_kind"
        ),
        sa.CheckConstraint(
            "(kind = 'voice' AND namespace <> '') OR (kind <> 'voice' AND namespace = '')",
            name="ck_content_pack_namespace",
        ),
    )
    op.create_table(
        "content_pack_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "pack_id",
            sa.String(36),
            sa.ForeignKey("content_packs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("manifest_digest", sa.String(64), nullable=False),
        sa.Column("content_digest", sa.String(64), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("pack_id", "revision", name="uq_content_pack_revision"),
        sa.UniqueConstraint("pack_id", "content_digest", name="uq_content_pack_digest"),
        sa.CheckConstraint("revision > 0", name="ck_content_pack_revision"),
    )
    with op.batch_alter_table("content_packs") as batch:
        batch.add_column(sa.Column("current_revision_id", sa.String(36), nullable=True))
        batch.create_foreign_key(
            "fk_pack_current_revision",
            "content_pack_revisions",
            ["current_revision_id"],
            ["id"],
            ondelete="RESTRICT",
        )
    op.create_table(
        "content_pack_files",
        sa.Column(
            "revision_id",
            sa.String(36),
            sa.ForeignKey("content_pack_revisions.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("relative_path", sa.String(1024), primary_key=True),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column(
            "media_asset_id",
            sa.String(36),
            sa.ForeignKey("local_media_assets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    op.create_table(
        "content_pack_scan_entries",
        sa.Column("source", sa.String(1024), primary_key=True),
        sa.Column("identity", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False),
    )


def downgrade():
    op.drop_table("content_pack_scan_entries")
    op.drop_table("content_pack_files")
    with op.batch_alter_table("content_packs") as batch:
        batch.drop_constraint("fk_pack_current_revision", type_="foreignkey")
        batch.drop_column("current_revision_id")
    op.drop_table("content_pack_revisions")
    op.drop_table("content_packs")
