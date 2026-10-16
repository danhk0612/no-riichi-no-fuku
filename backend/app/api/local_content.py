from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_current_superadmin, get_session
from app.schemas.local_content import PackKind

router = APIRouter(
    prefix="/api/local/packs",
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
