from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session
from app.db.models import User
from app.schemas.profile import ProfileResponse, UpdateProfileRequest


router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/me", response_model=ProfileResponse)
def get_profile(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=ProfileResponse)
def update_profile(
    request: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    user.player_name = request.player_name
    session.flush()
    return user
