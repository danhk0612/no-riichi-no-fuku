from sqlalchemy import CheckConstraint, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from .mixins import TimestampMixin


class CharacterContent(TimestampMixin, Base):
    __tablename__ = "character_content"
    cpu_id: Mapped[int] = mapped_column(
        ForeignKey("cpu_characters.id", ondelete="CASCADE"), primary_key=True
    )
    pack_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_pack_revisions.id", ondelete="RESTRICT"), nullable=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prompts: Mapped[dict] = mapped_column(JSON, nullable=False)
    overrides: Mapped[list] = mapped_column(JSON, nullable=False)
    measurements_cm: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class CharacterLevelFraming(TimestampMixin, Base):
    __tablename__ = "character_level_framing"
    __table_args__ = (
        UniqueConstraint("cpu_id", "level", "kind", name="uq_character_framing"),
        CheckConstraint("level BETWEEN 0 AND 3", name="ck_character_framing_level"),
        CheckConstraint("kind IN ('profile','full_body','cg')", name="ck_character_framing_kind"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cpu_id: Mapped[int] = mapped_column(
        ForeignKey("cpu_characters.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    positive: Mapped[str] = mapped_column(Text, nullable=False)
    negative: Mapped[str] = mapped_column(Text, nullable=False)
    overrides: Mapped[list] = mapped_column(JSON, nullable=False)


class StageImage(Base):
    __tablename__ = "stage_images"
    cpu_id: Mapped[int] = mapped_column(ForeignKey("cpu_characters.id", ondelete="CASCADE"), primary_key=True)
    level: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(12), primary_key=True)
    ticket: Mapped[str] = mapped_column(String(36))
    inputs: Mapped[dict] = mapped_column(JSON)
    endpoint: Mapped[str] = mapped_column(String)
    content_revision: Mapped[int] = mapped_column(Integer)
    media_id: Mapped[str | None] = mapped_column(ForeignKey("local_media_assets.id", ondelete="RESTRICT"))
    digest: Mapped[str | None] = mapped_column(String(64))
