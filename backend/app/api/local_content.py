from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.db.models import GameSetting
from app.services.image_prompts import PRESETS, KEY as SITUATION_KEY, situations

from app.api.dependencies import get_current_superadmin, get_session
from app.db.session import mark_write_intent
from app.schemas.local_content import PackKind
from app.schemas.local_content import CharacterContentPatch, CharacterPackApplication
from app.services.character_content import (get_character_content, patch_character_content,
    apply_character_pack, get_character_pack_revision)

router = APIRouter(
    prefix="/api/local/packs",
    tags=["local-content"],
    dependencies=[Depends(get_current_superadmin)],
)
character_router = APIRouter(
    prefix="/api/local/characters",
    tags=["local-content"],
    dependencies=[Depends(get_current_superadmin)],
)


@router.get("")
def list_packs(request: Request, kind: PackKind | None = None):
    return request.app.state.local_runtime.content_packs.listing(kind)


@router.post("/rescan")
def rescan_packs(request: Request, session=Depends(get_session)):
    # Authentication read must not hold a transaction while source files are read/copied.
    session.rollback()
    registry = request.app.state.local_runtime.content_packs
    return {**registry.scan(), "registry": registry.listing()}


class SituationEdit(BaseModel):
    text: str = Field(max_length=8000)
    previous: str


@character_router.get("/situation-prompts")
def read_situations(session=Depends(get_session)):
    return situations(session)


@character_router.put("/situation-prompts/{event}")
def edit_situation(event: str, change: SituationEdit, session=Depends(get_session)):
    if event not in PRESETS:
        raise HTTPException(422, "알 수 없는 상황입니다.")
    session.rollback()
    mark_write_intent(session)
    if situations(session)[event] != change.previous:
        raise HTTPException(409, "다른 편집이 먼저 저장됐습니다. 다시 열어 주세요.")
    row = session.get(GameSetting, SITUATION_KEY)
    values = dict(row.value) if row else {}
    values[event] = change.text.strip()
    if row:
        row.value = values
    else:
        session.add(GameSetting(key=SITUATION_KEY, value=values))
    session.commit()
    return situations(session)


@character_router.get("/{cpu_id}/content")
def read_character_content(cpu_id: int, request: Request, session=Depends(get_session)):
    return get_character_content(session, cpu_id)


@character_router.patch("/{cpu_id}/content")
def edit_character_content(
    cpu_id: int,
    change: CharacterContentPatch,
    request: Request,
    session=Depends(get_session),
):
    session.rollback()
    mark_write_intent(session)
    return patch_character_content(session, cpu_id, change)


@character_router.post("/{cpu_id}/pack-application")
def apply_pack(cpu_id: int, change: CharacterPackApplication, request: Request, session=Depends(get_session)):
    session.rollback()
    mark_write_intent(session)
    paths = request.app.state.local_runtime.paths
    return apply_character_pack(session, cpu_id, change, paths.root, paths.media)


@character_router.get("/{cpu_id}/pack-revisions/{revision_id}")
def read_pack_revision(cpu_id: int, revision_id: str, session=Depends(get_session)):
    return get_character_pack_revision(session, cpu_id, revision_id)


from app.schemas.fixed_dialogue import FixedDialoguePatch
from app.services.fixed_dialogue import read_fixed, candidates, patch_fixed


@character_router.get('/{cpu_id}/fixed-dialogues')
def get_fixed_dialogues(cpu_id: int, session=Depends(get_session)):
    return read_fixed(session, cpu_id)


@character_router.get('/{cpu_id}/fixed-dialogue-candidates')
def get_fixed_dialogue_candidates(cpu_id: int, session=Depends(get_session)):
    return candidates(session, cpu_id)


@character_router.patch('/{cpu_id}/fixed-dialogues')
def edit_fixed_dialogues(cpu_id: int, change: FixedDialoguePatch, session=Depends(get_session)):
    session.rollback()
    mark_write_intent(session)
    return patch_fixed(session, cpu_id, change)
