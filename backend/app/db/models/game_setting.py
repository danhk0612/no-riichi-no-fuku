from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

from .mixins import TimestampMixin


class GameSetting(TimestampMixin, Base):
    __tablename__ = "game_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[object] = mapped_column(JSON)
