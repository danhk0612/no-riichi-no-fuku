from fastapi import APIRouter, Depends, Request
from app.core.config import Settings
from app.api.dependencies import get_settings

from app.api.dependencies import get_current_superadmin, get_session
from app.db.session import mark_write_intent
from app.schemas.audio_packs import AudioPackSelectionWrite, CharacterVoiceSelectionWrite
from app.services.audio_packs import (
    audio_pack_selection_response, character_voice_selection,
    update_audio_pack_selection, update_character_voice_selection,
)

router = APIRouter(prefix="/api/local", tags=["local-audio-packs"], dependencies=[Depends(get_current_superadmin)])


@router.get("/audio-pack-selection")
def get_audio_pack_selection(session=Depends(get_session), settings: Settings = Depends(get_settings)):
    return audio_pack_selection_response(session, settings.media_root)


@router.put("/audio-pack-selection")
def put_audio_pack_selection(change: AudioPackSelectionWrite, session=Depends(get_session), settings: Settings = Depends(get_settings)):
    session.rollback()
    mark_write_intent(session)
    return update_audio_pack_selection(session, change, settings.media_root)


@router.get("/characters/{cpu_id}/voice-selection")
def get_voice_selection(cpu_id: int, session=Depends(get_session)):
    return character_voice_selection(session, cpu_id)


@router.put("/characters/{cpu_id}/voice-selection")
def put_voice_selection(cpu_id: int, change: CharacterVoiceSelectionWrite, session=Depends(get_session)):
    session.rollback()
    mark_write_intent(session)
    return update_character_voice_selection(session, cpu_id, change)
