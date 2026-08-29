from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_superadmin, get_session
from app.db.models import CpuCharacter, CpuDialogue, User
from app.schemas.admin import (
    CpuCharacterCreateRequest,
    CpuCharacterResponse,
    CpuCharacterUpdateRequest,
    CpuDialogueCreateRequest,
    CpuDialogueResponse,
    CpuDialogueUpdateRequest,
    MemberActiveUpdateRequest,
    MemberResponse,
)
from app.services.admin import (
    AdminEntityNotFoundError,
    CpuSlugAlreadyExistsError,
    create_cpu_character,
    create_cpu_dialogue,
    delete_cpu_dialogue,
    list_cpu_characters,
    list_cpu_dialogues,
    list_members,
    update_cpu_character,
    update_cpu_dialogue,
    update_member_active,
)


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_superadmin)],
)


def not_found(error: AdminEntityNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


@router.get("/users", response_model=list[MemberResponse])
def get_members(session: Session = Depends(get_session)) -> list[User]:
    return list_members(session)


@router.patch("/users/{user_id}", response_model=MemberResponse)
def set_member_active(
    user_id: int,
    request: MemberActiveUpdateRequest,
    session: Session = Depends(get_session),
) -> User:
    try:
        return update_member_active(session, user_id, request.is_active)
    except AdminEntityNotFoundError as error:
        raise not_found(error) from None


@router.get("/cpus", response_model=list[CpuCharacterResponse])
def get_cpu_characters(
    session: Session = Depends(get_session),
) -> list[CpuCharacter]:
    return list_cpu_characters(session)


@router.post(
    "/cpus",
    response_model=CpuCharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_cpu_character(
    request: CpuCharacterCreateRequest,
    session: Session = Depends(get_session),
) -> CpuCharacter:
    try:
        return create_cpu_character(session, request.model_dump())
    except CpuSlugAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CPU slug already exists",
        ) from None


@router.patch("/cpus/{cpu_id}", response_model=CpuCharacterResponse)
def edit_cpu_character(
    cpu_id: int,
    request: CpuCharacterUpdateRequest,
    session: Session = Depends(get_session),
) -> CpuCharacter:
    try:
        return update_cpu_character(
            session,
            cpu_id,
            request.model_dump(exclude_unset=True),
        )
    except AdminEntityNotFoundError as error:
        raise not_found(error) from None


@router.get(
    "/cpus/{cpu_id}/dialogues",
    response_model=list[CpuDialogueResponse],
)
def get_cpu_dialogues(
    cpu_id: int,
    session: Session = Depends(get_session),
) -> list[CpuDialogue]:
    try:
        return list_cpu_dialogues(session, cpu_id)
    except AdminEntityNotFoundError as error:
        raise not_found(error) from None


@router.post(
    "/cpus/{cpu_id}/dialogues",
    response_model=CpuDialogueResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_cpu_dialogue(
    cpu_id: int,
    request: CpuDialogueCreateRequest,
    session: Session = Depends(get_session),
) -> CpuDialogue:
    try:
        return create_cpu_dialogue(session, cpu_id, request.model_dump())
    except AdminEntityNotFoundError as error:
        raise not_found(error) from None


@router.patch("/dialogues/{dialogue_id}", response_model=CpuDialogueResponse)
def edit_cpu_dialogue(
    dialogue_id: int,
    request: CpuDialogueUpdateRequest,
    session: Session = Depends(get_session),
) -> CpuDialogue:
    try:
        return update_cpu_dialogue(
            session,
            dialogue_id,
            request.model_dump(exclude_unset=True),
        )
    except AdminEntityNotFoundError as error:
        raise not_found(error) from None


@router.delete("/dialogues/{dialogue_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cpu_dialogue(
    dialogue_id: int,
    session: Session = Depends(get_session),
) -> Response:
    try:
        delete_cpu_dialogue(session, dialogue_id)
    except AdminEntityNotFoundError as error:
        raise not_found(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
