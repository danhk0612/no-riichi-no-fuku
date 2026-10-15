from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from .mixins import TimestampMixin


class LocalMediaAsset(TimestampMixin, Base):
    __tablename__ = "local_media_assets"
    __table_args__ = (
        CheckConstraint("kind IN ('image', 'audio')", name="ck_local_media_assets_kind"),
        CheckConstraint("byte_size > 0", name="ck_local_media_assets_byte_size"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)


class SoundEffectSet(TimestampMixin, Base):
    __tablename__ = "sound_effect_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    clips: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)


class BackgroundTrack(TimestampMixin, Base):
    __tablename__ = "background_tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    media_asset_id: Mapped[str] = mapped_column(
        ForeignKey("local_media_assets.id", ondelete="RESTRICT"), nullable=False
    )
