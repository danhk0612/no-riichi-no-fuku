from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session, get_settings
from app.core.config import Settings
from app.core.security import create_access_token
from app.db.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.profile import ProfileResponse
from app.services.auth import (
    InvalidCredentialsError,
    LoginIdAlreadyExistsError,
    PlayerMaxHpConfigurationError,
    authenticate_user,
    change_password,
    register_member,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    session: Session = Depends(get_session),
) -> User:
    try:
        return register_member(
            session,
            request.login_id,
            request.password,
            request.player_name,
        )
    except LoginIdAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="login_id already exists",
        ) from None
    except PlayerMaxHpConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="player maximum HP is not configured",
        ) from None


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> TokenResponse:
    try:
        user = authenticate_user(session, request.login_id, request.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid authentication credentials",
        ) from None

    token, expires_in = create_access_token(
        user.id,
        settings.require_jwt_secret(),
        settings.access_token_expire_minutes,
    )
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        must_change_password=user.must_change_password,
    )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def update_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    try:
        change_password(
            session,
            user,
            request.current_password,
            request.new_password,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current password is incorrect",
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
