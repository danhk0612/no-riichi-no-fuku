from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import get_current_superadmin, get_session
from app.db.session import mark_write_intent
from app.schemas.shared_prompts import (
    CandidateWrite, ChangeConfirmation, ChangePreviewRequest, DefaultWrite,
    SharedPromptCreate, SharedPromptPatch,
)
from app.services import shared_prompts as service

router = APIRouter(prefix="/api/local", tags=["local-shared-prompts"],
                   dependencies=[Depends(get_current_superadmin)])
Kind = Literal["clothing_state", "pose"]


@router.get("/shared-prompts")
def list_items(kind: Kind = Query(...), level: int = Query(..., ge=0, le=3), session=Depends(get_session)):
    return {"items": service.list_items(session, kind, level)}


@router.post("/shared-prompts")
def create_item(data: SharedPromptCreate, session=Depends(get_session)):
    session.rollback()
    mark_write_intent(session)
    return service.create_item(session, data)


@router.patch("/shared-prompts/{item_id}")
def patch_item(item_id: str, data: SharedPromptPatch, session=Depends(get_session)):
    session.rollback()
    mark_write_intent(session)
    return service.patch_item(session, item_id, data)


@router.get("/shared-prompt-defaults/{level}/{kind}")
def get_default(level: Annotated[int, Path(ge=0, le=3)], kind: Kind, session=Depends(get_session)):
    return service.get_default(session, level, kind)


@router.put("/shared-prompt-defaults/{level}/{kind}")
def put_default(level: Annotated[int, Path(ge=0, le=3)], kind: Kind, data: DefaultWrite, session=Depends(get_session)):
    session.rollback()
    mark_write_intent(session)
    return service.put_default(session, level, kind, data)


@router.get("/characters/{cpu_id}/prompt-candidates/{level}/{kind}")
def get_candidates(cpu_id: int, level: Annotated[int, Path(ge=0, le=3)], kind: Kind, session=Depends(get_session)):
    return service.get_candidates(session, cpu_id, level, kind)


@router.put("/characters/{cpu_id}/prompt-candidates/{level}/{kind}")
def put_candidates(cpu_id: int, level: Annotated[int, Path(ge=0, le=3)], kind: Kind, data: CandidateWrite, session=Depends(get_session)):
    session.rollback()
    mark_write_intent(session)
    return service.put_candidates(session, cpu_id, level, kind, data)


@router.post("/shared-prompts/{item_id}/change-preview")
def preview_change(item_id: str, data: ChangePreviewRequest, session=Depends(get_session)):
    return service.preview_change(session, item_id, data)


@router.post("/shared-prompts/{item_id}/change-confirmation")
def confirm_change(item_id: str, data: ChangeConfirmation, session=Depends(get_session)):
    session.rollback()
    mark_write_intent(session)
    return service.confirm_change(session, item_id, data)
