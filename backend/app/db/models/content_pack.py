from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from .mixins import TimestampMixin


class ContentPack(TimestampMixin, Base):
    __tablename__ = "content_packs"
    __table_args__ = (
        UniqueConstraint(
            "kind", "namespace", "pack_id", name="uq_content_pack_identity"
        ),
        CheckConstraint(
            "kind IN ('character','sfx','bgm','voice')", name="ck_content_pack_kind"
        ),
        CheckConstraint(
            "(kind = 'voice' AND namespace <> '') OR (kind <> 'voice' AND namespace = '')",
            name="ck_content_pack_namespace",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    namespace: Mapped[str] = mapped_column(String(80), nullable=False)
    pack_id: Mapped[str] = mapped_column(String(80), nullable=False)
    registered_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "content_pack_revisions.id",
            name="fk_pack_registered_revision",
            use_alter=True,
            ondelete="RESTRICT",
        )
    )
    current_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "content_pack_revisions.id",
            name="fk_pack_current_revision",
            use_alter=True,
            ondelete="RESTRICT",
        )
    )


class ContentPackRevision(TimestampMixin, Base):
    __tablename__ = "content_pack_revisions"
    __table_args__ = (
        UniqueConstraint("pack_id", "revision", name="uq_content_pack_revision"),
        UniqueConstraint("pack_id", "content_digest", name="uq_content_pack_digest"),
        CheckConstraint("revision > 0", name="ck_content_pack_revision"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pack_id: Mapped[str] = mapped_column(
        ForeignKey("content_packs.id", ondelete="RESTRICT"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    content_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False)


class ContentPackFile(Base):
    __tablename__ = "content_pack_files"
    revision_id: Mapped[str] = mapped_column(
        ForeignKey("content_pack_revisions.id", ondelete="RESTRICT"), primary_key=True
    )
    relative_path: Mapped[str] = mapped_column(String(1024), primary_key=True)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    media_asset_id: Mapped[str] = mapped_column(
        ForeignKey("local_media_assets.id", ondelete="RESTRICT"), nullable=False
    )


class ContentPackScanEntry(Base):
    __tablename__ = "content_pack_scan_entries"
    source: Mapped[str] = mapped_column(String(1024), primary_key=True)
    identity: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    issues: Mapped[list] = mapped_column(JSON, nullable=False)
