from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session
from app.db.models import User
from app.schemas.profile import ProfileResponse, UpdateProfileRequest


router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/me", response_model=ProfileResponse)
def get_profile(request: Request, user: User = Depends(get_current_user)) -> User | dict[str, object]:
    if getattr(request.app.state, "local_runtime", None) is not None:
        return {"id": user.id, "login_id": user.login_id, "player_name": user.player_name,
                "profile_image_key": user.profile_image_key, "current_hp": None,
                "max_hp": None, "role": user.role, "must_change_password": user.must_change_password}
    return user


@router.patch("/me", response_model=ProfileResponse)
def update_profile(
    request: UpdateProfileRequest,
    raw_request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    user.player_name = request.player_name
    session.flush()
    if getattr(raw_request.app.state, "local_runtime", None) is not None:
        return {"id": user.id, "login_id": user.login_id, "player_name": user.player_name,
                "profile_image_key": user.profile_image_key, "current_hp": None,
                "max_hp": None, "role": user.role, "must_change_password": user.must_change_password}
    return user
