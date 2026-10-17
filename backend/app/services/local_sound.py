from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BackgroundTrack, GameSetting, LocalMediaAsset, SoundEffectSet
from app.services.local_media import LocalMediaError, media_metadata, validate_audio_asset
from app.services.result_assets import storage_path

SOUND_SELECTION_KEY = "local_sound_selection"
ENDING_RESOURCES_KEY = "local_ending_resources"
DEFAULT_SOUND_SELECTION: dict[str, object] = {"effect_set_id": None, "bgm_ids": []}
DEFAULT_ENDING_RESOURCES: dict[str, object] = {
    "cg_asset_id": None, "music_track_id": None, "dialogue_text": None,
}


def get_setting(session: Session, key: str, default: dict[str, object]) -> dict[str, object]:
    row = session.get(GameSetting, key)
    return dict(row.value) if row is not None and isinstance(row.value, dict) else dict(default)


def set_setting(session: Session, key: str, value: dict[str, object]) -> dict[str, object]:
    row = session.get(GameSetting, key)
    if row is None:
        row = GameSetting(key=key, value=value)
        session.add(row)
    else:
        row.value = value
    session.flush()
    return value


def sound_selection_response(session: Session, media_root: Path) -> dict[str, object]:
    value = get_setting(session, SOUND_SELECTION_KEY, DEFAULT_SOUND_SELECTION)
    effect_sets = {row.id: row for row in session.scalars(select(SoundEffectSet)).all()}
    tracks = {row.id: row for row in session.scalars(select(BackgroundTrack)).all()}
    from app.services.audio_packs import audio_pack_selection_response
    return {
        **value,
        "audio_packs": audio_pack_selection_response(session, media_root),
        "effect_sets": [effect_set_payload(row) for row in sorted(effect_sets.values(), key=lambda item: item.label.casefold())],
        "tracks": [track_payload(session, row, media_root) for row in sorted(tracks.values(), key=lambda item: item.label.casefold())],
        "effect_set_available": _active(effect_sets.get(value.get("effect_set_id"))),
        "bgm_available": [
            _track_available(session, tracks.get(track_id), media_root)
            for track_id in value.get("bgm_ids", []) if isinstance(track_id, str)
        ],
    }


def validate_sound_selection(session: Session, effect_set_id: str | None, bgm_ids: list[str]) -> None:
    if len(bgm_ids) != len(set(bgm_ids)):
        raise LocalMediaError("duplicate background track IDs are not allowed")
    if effect_set_id is not None:
        row = session.get(SoundEffectSet, effect_set_id)
        if row is None:
            raise LocalMediaError("selected effect set not found")
        if not row.active:
            raise LocalMediaError("selected effect set is inactive")
    for track_id in bgm_ids:
        row = session.get(BackgroundTrack, track_id)
        if row is None:
            raise LocalMediaError("selected background track not found")
        if not row.active:
            raise LocalMediaError("selected background track is inactive")


def validate_ending_resources(session: Session, cg_asset_id: str | None, music_track_id: str | None) -> None:
    if cg_asset_id is not None:
        asset = session.get(LocalMediaAsset, cg_asset_id)
        if asset is None or asset.kind != "image":
            raise LocalMediaError("ending image asset not found")
    if music_track_id is not None:
        track = session.get(BackgroundTrack, music_track_id)
        if track is None:
            raise LocalMediaError("ending music track not found")
        if not track.active:
            raise LocalMediaError("ending music track is inactive")
        validate_audio_asset(session, track.media_asset_id)


def effect_set_payload(row: SoundEffectSet) -> dict[str, object]:
    return {"id": row.id, "label": row.label, "active": row.active, "clips": row.clips}


def track_payload(session: Session, row: BackgroundTrack, media_root: Path) -> dict[str, object]:
    asset = session.get(LocalMediaAsset, row.media_asset_id)
    return {
        "id": row.id, "label": row.label, "active": row.active,
        "media_asset_id": row.media_asset_id,
        "available": bool(asset and asset.kind == "audio" and storage_path(media_root, asset.storage_key).is_file()),
        "url": f"/api/local/media/{asset.id}/file" if asset else None,
    }


def resolve_ending(session: Session, payload: dict[str, object], media_root: Path) -> dict[str, object]:
    if payload.get("acknowledged") is True:
        return {"acknowledged": True}
    cg_id = payload.get("cg_asset_id")
    music_id = payload.get("music_asset_id")
    cg = session.get(LocalMediaAsset, cg_id) if isinstance(cg_id, str) else None
    music = session.get(LocalMediaAsset, music_id) if isinstance(music_id, str) else None
    cg_available = bool(cg and cg.kind == "image" and storage_path(media_root, cg.storage_key).is_file())
    music_available = bool(music and music.kind == "audio" and storage_path(media_root, music.storage_key).is_file())
    return {
        "acknowledged": False,
        "cg": {"asset_id": cg_id, "url": f"/api/local/media/{cg.id}/file" if cg_available and cg else None, "available": cg_available},
        "music": {"asset_id": music_id, "url": f"/api/local/media/{music.id}/file" if music_available and music else None, "available": music_available},
        "dialogue_text": payload.get("dialogue_text"),
    }


def selected_effect_clip(session: Session, event_key: str, media_root: Path) -> dict[str, object] | None:
    from app.services.audio_packs import _audio_selection
    if _audio_selection(session).get("sfx_mode") == "pack":
        return None
    selection = get_setting(session, SOUND_SELECTION_KEY, DEFAULT_SOUND_SELECTION)
    set_id = selection.get("effect_set_id")
    effect_set = session.get(SoundEffectSet, set_id) if isinstance(set_id, str) else None
    if effect_set is None or not effect_set.active:
        return None
    asset_id = effect_set.clips.get(event_key) if isinstance(effect_set.clips, dict) else None
    asset = session.get(LocalMediaAsset, asset_id) if isinstance(asset_id, str) else None
    if asset is None or asset.kind != "audio":
        return None
    if not storage_path(media_root, asset.storage_key).is_file():
        return None
    return {"asset_id": asset.id, "url": f"/api/local/media/{asset.id}/file"}


def _active(row: SoundEffectSet | None) -> bool:
    return bool(row and row.active)


def _track_available(session: Session, row: BackgroundTrack | None, media_root: Path) -> bool:
    if row is None or not row.active:
        return False
    asset = session.get(LocalMediaAsset, row.media_asset_id)
    return bool(asset and asset.kind == "audio" and storage_path(media_root, asset.storage_key).is_file())
