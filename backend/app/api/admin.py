from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path as ApiPath,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_superadmin, get_session, get_settings
from app.core.config import Settings
from app.db.models import CpuCharacter, CpuDialogue, CpuResultAsset, User
from app.schemas.admin import (
    CpuCharacterCreateRequest,
    CpuCharacterResponse,
    CpuCharacterUpdateRequest,
    CpuDialogueCreateRequest,
    CpuDialogueResponse,
    CpuDialogueUpdateRequest,
    CpuResultAssetResponse,
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
from app.services.result_assets import (
    ResultAssetError,
    ResultAssetFormatError,
    ResultAssetTooLargeError,
    list_result_assets,
    result_asset_url,
    storage_path,
    store_result_asset_upload,
)


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_superadmin)],
)


def not_found(error: AdminEntityNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


def admin_result_asset_response(asset: CpuResultAsset) -> dict[str, object]:
    return {
        "id": asset.id,
        "cpu_character_id": asset.cpu_character_id,
        "defeat_stage": asset.defeat_stage,
        "storage_key": asset.storage_key,
        "mime_type": asset.mime_type,
        "active": asset.active,
        "url": result_asset_url(asset.id) if asset.storage_key else None,
    }


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


@router.get(
    "/cpus/{cpu_id}/result-assets",
    response_model=list[CpuResultAssetResponse],
)
def get_cpu_result_assets(
    cpu_id: int,
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    try:
        assets = list_result_assets(session, cpu_id)
    except ResultAssetError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return [admin_result_asset_response(asset) for asset in assets]


@router.put(
    "/cpus/{cpu_id}/result-assets/{defeat_stage}",
    response_model=CpuResultAssetResponse,
)
async def put_cpu_result_asset(
    cpu_id: int,
    defeat_stage: Annotated[int, ApiPath(ge=1, le=3)],
    file: Annotated[UploadFile, File()],
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    if session.get(CpuCharacter, cpu_id) is None:
        raise HTTPException(status_code=404, detail="CPU character not found")
    try:
        storage_key, mime_type = await store_result_asset_upload(
            file,
            settings.media_root,
            cpu_id,
            defeat_stage,
        )
    except ResultAssetTooLargeError as error:
        raise HTTPException(status_code=413, detail=str(error)) from None
    except ResultAssetFormatError as error:
        raise HTTPException(status_code=415, detail=str(error)) from None

    previous = session.scalar(
        select(CpuResultAsset).where(
            CpuResultAsset.cpu_character_id == cpu_id,
            CpuResultAsset.defeat_stage == defeat_stage,
        )
    )
    previous_path: Path | None = None
    if previous is None:
        asset = CpuResultAsset(
            cpu_character_id=cpu_id,
            defeat_stage=defeat_stage,
            storage_key=storage_key,
            mime_type=mime_type,
            active=True,
        )
        session.add(asset)
    else:
        asset = previous
        if previous.storage_key is not None:
            previous_path = storage_path(settings.media_root, previous.storage_key)
        asset.storage_key = storage_key
        asset.mime_type = mime_type
        asset.active = True

    new_path = storage_path(settings.media_root, storage_key)
    try:
        session.commit()
        session.refresh(asset)
    except Exception:
        session.rollback()
        new_path.unlink(missing_ok=True)
        raise
    if previous_path is not None and previous_path != new_path:
        previous_path.unlink(missing_ok=True)
    return admin_result_asset_response(asset)


@router.delete(
    "/cpus/{cpu_id}/result-assets/{defeat_stage}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_cpu_result_asset(
    cpu_id: int,
    defeat_stage: Annotated[int, ApiPath(ge=1, le=3)],
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    asset = session.scalar(
        select(CpuResultAsset).where(
            CpuResultAsset.cpu_character_id == cpu_id,
            CpuResultAsset.defeat_stage == defeat_stage,
        )
    )
    if asset is None or asset.storage_key is None:
        raise HTTPException(status_code=404, detail="result CG not found")
    asset_path = storage_path(settings.media_root, asset.storage_key)
    asset.storage_key = None
    asset.mime_type = None
    asset.active = False
    session.commit()
    asset_path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
