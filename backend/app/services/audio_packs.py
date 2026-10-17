from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CharacterContent, CharacterVoiceLink, ContentPack, ContentPackFile,
    ContentPackRevision, CpuCharacter, GameSetting, LocalMediaAsset,
)
from app.schemas.audio_packs import AudioPackSelectionWrite, CharacterVoiceSelectionWrite
from app.services.local_media import LocalMediaError
from app.services.result_assets import storage_path

AUDIO_PACK_SELECTION_KEY = "local_audio_pack_selection"
DEFAULT_AUDIO_PACK_SELECTION = {
    "revision": 0, "sfx_mode": "legacy", "sfx_pack_id": None,
    "bgm_mode": "legacy", "bgm_pack_id": None,
}


def _audio_selection(session: Session) -> dict:
    row = session.get(GameSetting, AUDIO_PACK_SELECTION_KEY)
    value = row.value if row is not None and isinstance(row.value, dict) else DEFAULT_AUDIO_PACK_SELECTION
    return {**DEFAULT_AUDIO_PACK_SELECTION, **value}


def _pack(session: Session, pack_id: str | None, kind: str) -> ContentPack | None:
    pack = session.get(ContentPack, pack_id) if isinstance(pack_id, str) else None
    if pack is None or pack.kind != kind or not pack.registered_revision_id:
        return None
    revision = session.get(ContentPackRevision, pack.registered_revision_id)
    return pack if revision is not None and revision.pack_id == pack.id else None


def _default_audio_pack(session: Session, kind: str) -> ContentPack | None:
    return session.scalar(select(ContentPack).where(
        ContentPack.kind == kind, ContentPack.pack_id == "default",
        ContentPack.namespace == "",
    ))


def _clip_from_pack(session: Session, pack: ContentPack | None, slot: str, media_root: Path) -> dict | None:
    if pack is None or not pack.registered_revision_id:
        return None
    revision = session.get(ContentPackRevision, pack.registered_revision_id)
    if revision is None:
        return None
    path = (revision.manifest.get("slots") or {}).get(slot)
    if not isinstance(path, str):
        return None
    file_ref = session.get(ContentPackFile, (revision.id, path))
    asset = session.get(LocalMediaAsset, file_ref.media_asset_id) if file_ref else None
    if asset is None or asset.kind != "audio":
        return None
    try:
        available = storage_path(media_root, asset.storage_key).is_file()
    except (LocalMediaError, OSError):
        available = False
    if not available:
        return None
    return {"asset_id": asset.id, "url": f"/api/local/media/{asset.id}/file", "pack_id": pack.id, "slot": slot}


def resolve_audio_pack_slot(session: Session, *, kind: str, slot: str, media_root: Path) -> dict | None:
    setting = _audio_selection(session)
    domain = "sfx" if kind == "sfx" else "bgm"
    if setting[f"{domain}_mode"] != "pack":
        return None
    selected = _pack(session, setting.get(f"{domain}_pack_id"), kind)
    default = _pack(session, getattr(_default_audio_pack(session, kind), "id", None), kind)
    result = _clip_from_pack(session, selected, slot, media_root)
    if result is not None:
        return result
    return _clip_from_pack(session, default, slot, media_root)


def _voice_default_pack(session: Session, cpu_id: int) -> str | None:
    content = session.get(CharacterContent, cpu_id)
    if content is None or not content.pack_revision_id:
        return None
    revision = session.get(ContentPackRevision, content.pack_revision_id)
    if revision is None:
        return None
    reference = revision.manifest.get("default_voice_pack")
    if not isinstance(reference, dict):
        return None
    return session.scalar(select(ContentPack.id).where(
        ContentPack.kind == "voice",
        ContentPack.namespace == reference.get("character_id"),
        ContentPack.pack_id == reference.get("id"),
    ))


def sync_default_voice_pack(session: Session, cpu_id: int) -> None:
    default_id = _voice_default_pack(session, cpu_id)
    row = session.get(CharacterVoiceLink, cpu_id)
    if row is None:
        session.add(CharacterVoiceLink(cpu_id=cpu_id, default_pack_id=default_id,
                                       selected_pack_id=None, selection_mode="default", revision=1))
    elif row.default_pack_id != default_id:
        row.default_pack_id = default_id
        row.revision += 1


def audio_pack_selection_response(session: Session, media_root: Path | None = None) -> dict:
    value = _audio_selection(session)
    defaults = {}
    packs = []
    for kind in ("sfx", "bgm"):
        default = _default_audio_pack(session, kind)
        defaults[kind] = default.id if default else None
        packs.extend({"id": row.id, "kind": row.kind, "pack_id": row.pack_id,
                      "revision": row.registered_revision_id} for row in session.scalars(
            select(ContentPack).where(ContentPack.kind == kind, ContentPack.registered_revision_id.is_not(None))
            .order_by(ContentPack.pack_id)
        ))
    bgm_slots = {slot: resolve_audio_pack_slot(session, kind="bgm", slot=slot, media_root=media_root)
                 for slot in ("title", "selection", "game", "result")} if media_root else {}
    return {"schema_version": 1, **value, "defaults": defaults, "packs": packs, "bgm_slots": bgm_slots}


def update_audio_pack_selection(session: Session, change: AudioPackSelectionWrite, media_root: Path | None = None) -> dict:
    current = _audio_selection(session)
    if current["revision"] != change.expected_revision:
        raise HTTPException(409, detail={"code": "revision_conflict", "message": "사운드 설정이 변경됐습니다. 다시 불러와 주세요."})
    for kind, mode, pack_id in (("sfx", change.sfx_mode, change.sfx_pack_id), ("bgm", change.bgm_mode, change.bgm_pack_id)):
        if mode == "legacy":
            continue
        if pack_id is not None and _pack(session, pack_id, kind) is None:
            raise HTTPException(422, detail={"code": "invalid_pack", "message": "선택한 음향팩을 찾을 수 없습니다."})
    value = {"revision": current["revision"] + 1,
             "sfx_mode": change.sfx_mode, "sfx_pack_id": change.sfx_pack_id,
             "bgm_mode": change.bgm_mode, "bgm_pack_id": change.bgm_pack_id}
    row = session.get(GameSetting, AUDIO_PACK_SELECTION_KEY)
    if row is None:
        session.add(GameSetting(key=AUDIO_PACK_SELECTION_KEY, value=value))
    else:
        row.value = value
    session.flush()
    session.commit()
    return audio_pack_selection_response(session, media_root)


def character_voice_selection(session: Session, cpu_id: int) -> dict:
    if session.get(CpuCharacter, cpu_id) is None:
        raise HTTPException(404, detail={"code": "not_found", "message": "캐릭터를 찾을 수 없습니다."})
    row = session.get(CharacterVoiceLink, cpu_id)
    default_id = row.default_pack_id if row is not None and row.default_pack_id else _voice_default_pack(session, cpu_id)
    packs = [{"id": pack.id, "namespace": pack.namespace, "pack_id": pack.pack_id,
              "revision": pack.registered_revision_id}
             for pack in session.scalars(select(ContentPack).where(
                 ContentPack.kind == "voice",
                 ContentPack.registered_revision_id.is_not(None)
             ).order_by(ContentPack.namespace, ContentPack.pack_id))]
    return {"schema_version": 1, "cpu_id": cpu_id, "revision": row.revision if row else 0,
            "default_pack_id": default_id, "selected_pack_id": row.selected_pack_id if row else None,
            "selection_mode": row.selection_mode if row else "default", "packs": packs}


def update_character_voice_selection(session: Session, cpu_id: int, change: CharacterVoiceSelectionWrite) -> dict:
    if session.get(CpuCharacter, cpu_id) is None:
        raise HTTPException(404, detail={"code": "not_found", "message": "캐릭터를 찾을 수 없습니다."})
    row = session.get(CharacterVoiceLink, cpu_id)
    revision = row.revision if row else 0
    if revision != change.expected_revision:
        raise HTTPException(409, detail={"code": "revision_conflict", "message": "음성팩 연결이 변경됐습니다. 다시 불러와 주세요."})
    if change.selection_mode == "selected":
        selected = _pack(session, change.selected_pack_id, "voice")
        if selected is None:
            raise HTTPException(422, detail={"code": "invalid_pack", "message": "선택한 음성팩을 찾을 수 없습니다."})
    if row is None:
        row = CharacterVoiceLink(cpu_id=cpu_id, default_pack_id=_voice_default_pack(session, cpu_id),
                                 selected_pack_id=None, selection_mode="default", revision=0)
        session.add(row)
    row.selection_mode = change.selection_mode
    row.selected_pack_id = change.selected_pack_id if change.selection_mode == "selected" else None
    row.revision += 1
    session.flush()
    session.commit()
    return character_voice_selection(session, cpu_id)


def resolve_voice_slot(session: Session, cpu_id: int, slot: str, media_root: Path) -> dict | None:
    row = session.get(CharacterVoiceLink, cpu_id)
    if row is None:
        default_id = _voice_default_pack(session, cpu_id)
        selected_id = None
        mode = "default"
    else:
        default_id, selected_id, mode = row.default_pack_id, row.selected_pack_id, row.selection_mode
        if default_id is None:
            default_id = _voice_default_pack(session, cpu_id)
    if mode == "off":
        return None
    if mode == "selected":
        selected = _pack(session, selected_id, "voice")
        if selected is not None:
            return _clip_from_pack(session, selected, slot, media_root)
    return _clip_from_pack(session, _pack(session, default_id, "voice"), slot, media_root)
