from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import create_database_engine, create_session_factory


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_engine(database_url: str) -> Engine:
    return create_database_engine(database_url)


@lru_cache
def get_session_factory(database_url: str) -> sessionmaker[Session]:
    return create_session_factory(get_engine(database_url))


def get_session(
    settings: Settings = Depends(get_settings),
) -> Generator[Session, None, None]:
    session_factory = get_session_factory(settings.require_database_url())
    with session_factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        user_id = decode_access_token(
            credentials.credentials,
            settings.require_jwt_secret(),
        )
    except (jwt.InvalidTokenError, RuntimeError):
        raise unauthorized from None

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


def get_current_superadmin(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="superadmin access required",
        )
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="initial password must be changed",
        )
    return user


def get_current_member(user: User = Depends(get_current_user)) -> User:
    if user.role != "member":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="member access required",
        )
    return user
