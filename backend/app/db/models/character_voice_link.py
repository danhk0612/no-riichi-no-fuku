from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from .mixins import TimestampMixin


class CharacterVoiceLink(TimestampMixin, Base):
    __tablename__ = "character_voice_links"
    __table_args__ = (
        CheckConstraint("selection_mode IN ('default','selected','off')", name="ck_character_voice_selection_mode"),
        CheckConstraint("revision >= 1", name="ck_character_voice_revision"),
    )
    cpu_id: Mapped[int] = mapped_column(
        ForeignKey("cpu_characters.id", ondelete="CASCADE"), primary_key=True
    )
    default_pack_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_packs.id", ondelete="RESTRICT"), nullable=True
    )
    selected_pack_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_packs.id", ondelete="RESTRICT"), nullable=True
    )
    selection_mode: Mapped[str] = mapped_column(String(12), nullable=False, default="default")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
