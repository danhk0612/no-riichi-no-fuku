from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CpuCharacter, CpuResultAsset, UserCpuProgress


MAX_RESULT_ASSET_BYTES = 5 * 1024 * 1024
_READ_CHUNK_BYTES = 64 * 1024


class ResultAssetError(RuntimeError):
    pass


class ResultAssetFormatError(ResultAssetError):
    pass


class ResultAssetTooLargeError(ResultAssetError):
    pass


def result_asset_url(asset_id: int) -> str:
    return f"/api/game/result-assets/{asset_id}/file"


def result_asset_metadata(asset: CpuResultAsset) -> dict[str, object]:
    if asset.storage_key is None:
        raise ResultAssetError("result CG slot is empty")
    return {
        "id": asset.id,
        "cpu_character_id": asset.cpu_character_id,
        "defeat_stage": asset.defeat_stage,
        "mime_type": asset.mime_type,
        "url": result_asset_url(asset.id),
    }


def storage_path(media_root: Path, storage_key: str) -> Path:
    relative_key = storage_key.removeprefix("/")
    candidate = (media_root / relative_key).resolve()
    root = media_root.resolve()
    if not candidate.is_relative_to(root):
        raise ResultAssetError("invalid result asset storage key")
    return candidate


def detect_result_asset_format(signature: bytes) -> tuple[str, str]:
    if signature.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if signature.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if (
        len(signature) >= 12
        and signature.startswith(b"RIFF")
        and signature[8:12] == b"WEBP"
    ):
        return "image/webp", "webp"
    raise ResultAssetFormatError("result CG must be JPEG, PNG, or WebP")


async def store_result_asset_upload(
    upload: UploadFile,
    media_root: Path,
    cpu_id: int,
    defeat_stage: int,
) -> tuple[str, str]:
    upload_root = media_root / ".uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    temporary_path = upload_root / f"{uuid4()}.tmp"
    size = 0
    signature = bytearray()

    try:
        with temporary_path.open("xb") as destination:
            while chunk := await upload.read(_READ_CHUNK_BYTES):
                size += len(chunk)
                if size > MAX_RESULT_ASSET_BYTES:
                    raise ResultAssetTooLargeError(
                        "result CG must not exceed 5 MiB"
                    )
                if len(signature) < 12:
                    signature.extend(chunk[: 12 - len(signature)])
                destination.write(chunk)
        mime_type, extension = detect_result_asset_format(bytes(signature))
        storage_key = (
            f"/cpu/{cpu_id}/result/stage-{defeat_stage}/{uuid4()}.{extension}"
        )
        destination_path = storage_path(media_root, storage_key)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary_path, destination_path)
        return storage_key, mime_type
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def list_result_assets(session: Session, cpu_id: int) -> list[CpuResultAsset]:
    if session.get(CpuCharacter, cpu_id) is None:
        raise ResultAssetError("CPU character not found")
    return list(
        session.scalars(
            select(CpuResultAsset)
            .where(CpuResultAsset.cpu_character_id == cpu_id)
            .order_by(CpuResultAsset.defeat_stage)
        ).all()
    )


def get_unlocked_result_asset(
    session: Session,
    user_id: int,
    cpu_id: int,
    defeat_stage: int,
) -> CpuResultAsset | None:
    return session.scalar(
        select(CpuResultAsset)
        .join(
            UserCpuProgress,
            UserCpuProgress.cpu_character_id == CpuResultAsset.cpu_character_id,
        )
        .where(
            CpuResultAsset.cpu_character_id == cpu_id,
            CpuResultAsset.defeat_stage == defeat_stage,
            CpuResultAsset.storage_key.is_not(None),
            CpuResultAsset.active.is_(True),
            UserCpuProgress.user_id == user_id,
            UserCpuProgress.defeat_stage >= CpuResultAsset.defeat_stage,
        )
    )


def get_unlocked_result_asset_by_id(
    session: Session,
    user_id: int,
    asset_id: int,
) -> CpuResultAsset | None:
    return session.scalar(
        select(CpuResultAsset)
        .join(
            UserCpuProgress,
            UserCpuProgress.cpu_character_id == CpuResultAsset.cpu_character_id,
        )
        .where(
            CpuResultAsset.id == asset_id,
            CpuResultAsset.storage_key.is_not(None),
            CpuResultAsset.active.is_(True),
            UserCpuProgress.user_id == user_id,
            UserCpuProgress.defeat_stage >= CpuResultAsset.defeat_stage,
        )
    )
