from sqlalchemy import CheckConstraint, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from .mixins import TimestampMixin


class CharacterFixedDialogue(TimestampMixin, Base):
    __tablename__ = 'character_fixed_dialogues'
    __table_args__ = (CheckConstraint('revision >= 1', name='ck_fixed_dialogue_revision'),)
    cpu_id: Mapped[int] = mapped_column(ForeignKey('cpu_characters.id', ondelete='CASCADE'), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    slots: Mapped[dict] = mapped_column(JSON, nullable=False)
