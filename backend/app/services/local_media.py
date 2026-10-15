from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.db.models import LocalMediaAsset
from app.services.result_assets import ResultAssetError, storage_path

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_AUDIO_BYTES = 32 * 1024 * 1024
CHUNK_BYTES = 64 * 1024


class LocalMediaError(RuntimeError):
    pass


class LocalMediaFormatError(LocalMediaError):
    pass


class LocalMediaTooLargeError(LocalMediaError):
    pass


def media_url(asset_id: str) -> str:
    return f"/api/local/media/{asset_id}/file"


def media_path(media_root: Path, storage_key: str) -> Path:
    try:
        return storage_path(media_root, storage_key)
    except ResultAssetError as error:
        raise LocalMediaError(str(error)) from None


def media_metadata(asset: LocalMediaAsset, media_root: Path | None = None) -> dict[str, object]:
    path_exists = None
    if media_root is not None:
        path_exists = media_path(media_root, asset.storage_key).is_file()
    return {
        "id": asset.id,
        "kind": asset.kind,
        "mime_type": asset.mime_type,
        "byte_size": asset.byte_size,
        "url": media_url(asset.id),
        "available": path_exists,
    }


def _identify(kind: str, filename: str, content_type: str | None, signature: bytes) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if kind == "image":
        formats = {
            ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
            ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
            ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
            ".webp": ("image/webp", b"RIFF"),
        }
        selected = formats.get(suffix)
        if selected is None:
            raise LocalMediaFormatError("image must be JPEG, PNG, or WebP")
        mime, marker = selected
        valid = signature.startswith(marker)
        if suffix == ".webp":
            valid = len(signature) >= 12 and signature[8:12] == b"WEBP"
        if not valid or content_type not in (None, "application/octet-stream", mime):
            raise LocalMediaFormatError("image extension, MIME type, and file signature must match")
        return mime, suffix.lstrip(".").replace("jpeg", "jpg")
    formats = {
        ".mp3": ("audio/mpeg", lambda data: data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0)),
        ".wav": ("audio/wav", lambda data: len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WAVE"),
        ".ogg": ("audio/ogg", lambda data: data.startswith(b"OggS")),
    }
    selected = formats.get(suffix)
    if kind != "audio" or selected is None:
        raise LocalMediaFormatError("audio must be MP3, WAV, or Ogg")
    mime, validator = selected
    allowed_mimes = {mime, "application/octet-stream"}
    if suffix == ".wav": allowed_mimes.add("audio/x-wav")
    if suffix == ".ogg": allowed_mimes.add("application/ogg")
    if not validator(signature) or content_type not in (None, *allowed_mimes):
        raise LocalMediaFormatError("audio extension, MIME type, and file signature must match")
    return mime, suffix.lstrip(".")


async def store_media_upload(upload: UploadFile, kind: str, media_root: Path) -> tuple[LocalMediaAsset, Path]:
    if kind not in {"image", "audio"}:
        await upload.close()
        raise LocalMediaFormatError("kind must be image or audio")
    temp_root = media_root / ".uploads"
    temp_root.mkdir(parents=True, exist_ok=True)
    temporary = temp_root / f"{uuid4()}.tmp"
    size = 0
    signature = bytearray()
    limit = MAX_IMAGE_BYTES if kind == "image" else MAX_AUDIO_BYTES
    try:
        with temporary.open("xb") as output:
            while chunk := await upload.read(CHUNK_BYTES):
                size += len(chunk)
                if size > limit:
                    raise LocalMediaTooLargeError(f"{kind} upload exceeds {limit // (1024 * 1024)} MiB")
                if len(signature) < 16:
                    signature.extend(chunk[:16 - len(signature)])
                output.write(chunk)
        mime_type, extension = _identify(kind, upload.filename or "", upload.content_type, bytes(signature))
        asset_id = str(uuid4())
        storage_key = f"w06/{asset_id}.{extension}"
        destination = media_path(media_root, storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary, destination)
        return LocalMediaAsset(
            id=asset_id, kind=kind, storage_key=storage_key,
            mime_type=mime_type, byte_size=size,
        ), destination
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def validate_effect_clips(session: Session, clips: dict[str, str]) -> None:
    allowed = {"chi", "pon", "kan", "riichi", "ron", "tsumo"}
    if any(key not in allowed for key in clips):
        raise LocalMediaError("effect clips may only use chi/pon/kan/riichi/ron/tsumo")
    if clips:
        assets = session.query(LocalMediaAsset).filter(LocalMediaAsset.id.in_(set(clips.values()))).all()
        valid = {asset.id for asset in assets if asset.kind == "audio"}
        if set(clips.values()) - valid:
            raise LocalMediaError("effect clip must reference an audio asset")


def validate_audio_asset(session: Session, asset_id: str) -> LocalMediaAsset:
    asset = session.get(LocalMediaAsset, asset_id)
    if asset is None or asset.kind != "audio":
        raise LocalMediaError("audio media asset not found")
    return asset
