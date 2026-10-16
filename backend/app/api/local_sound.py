from __future__ import annotations

import re
from uuid import uuid4
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_member, get_current_superadmin, get_session, get_settings
from app.core.config import Settings
from app.db.models import BackgroundTrack, LocalMediaAsset, LocalPlayState, SoundEffectSet, User
from app.db.session import mark_write_intent
from app.schemas.local_sound import BackgroundTrackCreate, BackgroundTrackUpdate, EndingResources, SoundEffectSetWrite, SoundSelection
from app.services.local_media import (
    LocalMediaError, LocalMediaFormatError, LocalMediaTooLargeError, media_metadata,
    media_path, store_media_upload, validate_audio_asset, validate_effect_clips,
)
from app.services.local_sound import (
    DEFAULT_ENDING_RESOURCES, DEFAULT_SOUND_SELECTION, ENDING_RESOURCES_KEY,
    SOUND_SELECTION_KEY, effect_set_payload, get_setting, resolve_ending,
    set_setting, sound_selection_response, track_payload, validate_ending_resources,
    validate_sound_selection,
)

router = APIRouter(prefix="/api/local", tags=["local-sound"])
SOUND_KEYS = {"chi", "pon", "kan", "riichi", "ron", "tsumo"}


def _http_media_error(error: LocalMediaError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(error))


def _label(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="label is required")
    return cleaned


@router.get("/media")
def list_media(
    user: User = Depends(get_current_superadmin), session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, object]]:
    return [media_metadata(asset, settings.media_root) for asset in session.scalars(select(LocalMediaAsset).order_by(LocalMediaAsset.created_at, LocalMediaAsset.id)).all()]


@router.post("/media", status_code=status.HTTP_201_CREATED)
async def upload_media(
    kind: Annotated[str, Form()], file: Annotated[UploadFile, File()],
    user: User = Depends(get_current_superadmin), session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    try:
        asset, path = await store_media_upload(file, kind, settings.media_root)
    except LocalMediaTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error)) from None
    except LocalMediaFormatError as error:
        raise _http_media_error(error) from None
    try:
        # Authentication dependencies may have opened a read transaction; release
        # it before reserving the serialized writer, after the file was safely stored.
        session.rollback()
        mark_write_intent(session)
        session.add(asset)
        session.flush()
        session.commit()
    except Exception:
        session.rollback()
        path.unlink(missing_ok=True)
        raise
    return media_metadata(asset, settings.media_root)


@router.get("/media/{asset_id}/file")
def get_media_file(
    asset_id: str, user: User = Depends(get_current_member),
    session: Session = Depends(get_session), settings: Settings = Depends(get_settings),
    range_header: str | None = Header(default=None, alias="Range"),
) -> Response:
    # The standard Range header is read from Request below through an explicit header alias.
    asset = session.get(LocalMediaAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="media file not found")
    try:
        path = media_path(settings.media_root, asset.storage_key)
    except LocalMediaError:
        raise HTTPException(status_code=404, detail="media file not found") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="media file not found")
    return _range_file_response(path, asset.mime_type, range_header)


def _range_file_response(path: Path, mime_type: str, range_header: str | None) -> Response:
    size = path.stat().st_size
    headers = {"Cache-Control": "private, no-store", "Accept-Ranges": "bytes"}
    if range_header is None:
        def stream_all():
            with path.open("rb") as source:
                while chunk := source.read(64 * 1024):
                    yield chunk
        headers["Content-Length"] = str(size)
        return StreamingResponse(stream_all(), media_type=mime_type, headers=headers)
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
    if match is None or size == 0:
        return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{size}"})
    start_text, end_text = match.groups()
    if not start_text:
        suffix_size = int(end_text or "0")
        if suffix_size <= 0:
            return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{size}"})
        start = max(0, size - suffix_size)
        end = size - 1
    else:
        start = int(start_text)
        end = min(int(end_text), size - 1) if end_text else size - 1
    if start >= size or end < start:
        return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{size}"})
    length = end - start + 1
    def stream_range():
        with path.open("rb") as source:
            source.seek(start)
            remaining = length
            while remaining:
                chunk = source.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
    headers.update({"Content-Length": str(length), "Content-Range": f"bytes {start}-{end}/{size}"})
    return StreamingResponse(stream_range(), status_code=206, media_type=mime_type, headers=headers)


@router.get("/sound-effect-sets")
def list_effect_sets(user: User = Depends(get_current_superadmin), session: Session = Depends(get_session)):
    return [effect_set_payload(row) for row in session.scalars(select(SoundEffectSet).order_by(SoundEffectSet.label, SoundEffectSet.id)).all()]


@router.post("/sound-effect-sets", status_code=201)
def create_effect_set(request: SoundEffectSetWrite, user: User = Depends(get_current_superadmin), session: Session = Depends(get_session)):
    try:
        validate_effect_clips(session, request.clips)
        row = SoundEffectSet(id=str(uuid4()), label=_label(request.label), active=request.active, clips=request.clips)
        session.add(row)
        session.flush()
        session.commit()
        return effect_set_payload(row)
    except LocalMediaError as error:
        session.rollback()
        raise _http_media_error(error) from None
    except Exception:
        session.rollback()
        raise


@router.patch("/sound-effect-sets/{set_id}")
def update_effect_set(set_id: str, request: SoundEffectSetWrite, user: User = Depends(get_current_superadmin), session: Session = Depends(get_session)):
    row = session.get(SoundEffectSet, set_id)
    if row is None:
        raise HTTPException(status_code=404, detail="effect set not found")
    try:
        validate_effect_clips(session, request.clips)
        row.label, row.active, row.clips = _label(request.label), request.active, request.clips
        session.flush()
        session.commit()
        return effect_set_payload(row)
    except LocalMediaError as error:
        session.rollback()
        raise _http_media_error(error) from None
    except Exception:
        session.rollback()
        raise


@router.get("/background-tracks")
def list_tracks(user: User = Depends(get_current_superadmin), session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    return [track_payload(session, row, settings.media_root) for row in session.scalars(select(BackgroundTrack).order_by(BackgroundTrack.label, BackgroundTrack.id)).all()]


@router.post("/background-tracks", status_code=201)
def create_track(request: BackgroundTrackCreate, user: User = Depends(get_current_superadmin), session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    try:
        validate_audio_asset(session, request.media_asset_id)
        row = BackgroundTrack(id=str(uuid4()), label=_label(request.label), active=request.active, media_asset_id=request.media_asset_id)
        session.add(row)
        session.flush()
        session.commit()
        return track_payload(session, row, settings.media_root)
    except LocalMediaError as error:
        session.rollback()
        raise _http_media_error(error) from None
    except Exception:
        session.rollback()
        raise


@router.patch("/background-tracks/{track_id}")
def update_track(track_id: str, request: BackgroundTrackUpdate, user: User = Depends(get_current_superadmin), session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    row = session.get(BackgroundTrack, track_id)
    if row is None:
        raise HTTPException(status_code=404, detail="background track not found")
    try:
        data = request.model_dump(exclude_unset=True)
        if data.get("label") is not None: row.label = _label(data["label"])
        if data.get("active") is not None: row.active = data["active"]
        if data.get("media_asset_id") is not None:
            validate_audio_asset(session, data["media_asset_id"])
            row.media_asset_id = data["media_asset_id"]
        session.flush()
        session.commit()
        return track_payload(session, row, settings.media_root)
    except LocalMediaError as error:
        session.rollback()
        raise _http_media_error(error) from None
    except Exception:
        session.rollback()
        raise


@router.get("/sound-selection")
def get_sound_selection(user: User = Depends(get_current_member), session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    return sound_selection_response(session, settings.media_root)


@router.put("/sound-selection")
def put_sound_selection(request: SoundSelection, user: User = Depends(get_current_member), session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    try:
        validate_sound_selection(session, request.effect_set_id, request.bgm_ids)
        set_setting(session, SOUND_SELECTION_KEY, request.model_dump())
        session.commit()
        return sound_selection_response(session, settings.media_root)
    except LocalMediaError as error:
        session.rollback()
        raise _http_media_error(error) from None
    except Exception:
        session.rollback()
        raise


@router.get("/ending-resources")
def get_ending_resources(user: User = Depends(get_current_member), session: Session = Depends(get_session)):
    return get_setting(session, ENDING_RESOURCES_KEY, DEFAULT_ENDING_RESOURCES)


@router.put("/ending-resources")
def put_ending_resources(request: EndingResources, user: User = Depends(get_current_member), session: Session = Depends(get_session)):
    try:
        validate_ending_resources(session, request.cg_asset_id, request.music_track_id)
        value = request.model_dump()
        set_setting(session, ENDING_RESOURCES_KEY, value)
        session.commit()
        return value
    except LocalMediaError as error:
        session.rollback()
        raise _http_media_error(error) from None
    except Exception:
        session.rollback()
        raise


@router.get("/play/ending")
def get_ending(generation: str, event_id: str, user: User = Depends(get_current_member), session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    state = session.get(LocalPlayState, user.id)
    if state is None or state.generation != generation or state.ending_event_id != event_id:
        raise HTTPException(status_code=409, detail={"code": "ending_event_stale", "message": "ending event is no longer current"})
    if state.phase == "omake":
        return {"acknowledged": True}
    if state.phase != "ending_pending" or not isinstance(state.ending_payload, dict):
        raise HTTPException(status_code=409, detail={"code": "ending_event_stale", "message": "ending event is no longer pending"})
    return resolve_ending(session, state.ending_payload, settings.media_root)
