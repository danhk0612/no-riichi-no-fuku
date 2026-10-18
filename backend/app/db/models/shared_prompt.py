from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from .mixins import TimestampMixin


class SharedPromptItem(TimestampMixin, Base):
    __tablename__ = "shared_prompt_items"
    __table_args__ = (
        CheckConstraint("level BETWEEN 0 AND 3", name="ck_shared_prompt_level"),
        CheckConstraint("kind IN ('clothing_state','pose')", name="ck_shared_prompt_kind"),
        CheckConstraint("revision >= 1", name="ck_shared_prompt_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    positive: Mapped[str] = mapped_column(Text, nullable=False)
    negative: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CharacterPromptCandidates(TimestampMixin, Base):
    __tablename__ = "character_prompt_candidates"
    __table_args__ = (
        UniqueConstraint("cpu_id", "level", "kind", name="uq_prompt_candidates_scope"),
        CheckConstraint("level BETWEEN 0 AND 3", name="ck_prompt_candidates_level"),
        CheckConstraint("kind IN ('clothing_state','pose')", name="ck_prompt_candidates_kind"),
        CheckConstraint("revision >= 1", name="ck_prompt_candidates_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cpu_id: Mapped[int] = mapped_column(ForeignKey("cpu_characters.id", ondelete="CASCADE"), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class CharacterPromptCandidateEntry(Base):
    __tablename__ = "character_prompt_candidate_entries"
    __table_args__ = (UniqueConstraint("candidate_set_id", "item_id", name="uq_prompt_candidate_entry"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_set_id: Mapped[str] = mapped_column(ForeignKey("character_prompt_candidates.id", ondelete="CASCADE"), nullable=False)
    item_id: Mapped[str] = mapped_column(ForeignKey("shared_prompt_items.id", ondelete="RESTRICT"), nullable=False)


class SharedPromptDefault(TimestampMixin, Base):
    __tablename__ = "shared_prompt_defaults"
    __table_args__ = (
        CheckConstraint("level BETWEEN 0 AND 3", name="ck_shared_prompt_default_level"),
        CheckConstraint("kind IN ('clothing_state','pose')", name="ck_shared_prompt_default_kind"),
        CheckConstraint("revision >= 1", name="ck_shared_prompt_default_revision"),
    )

    level: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    item_id: Mapped[str | None] = mapped_column(ForeignKey("shared_prompt_items.id", ondelete="RESTRICT"), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
