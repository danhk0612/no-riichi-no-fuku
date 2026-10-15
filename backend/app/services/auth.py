from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import CpuCharacter, GameSetting, User, UserCpuProgress


class LoginIdAlreadyExistsError(RuntimeError):
    pass


class InvalidCredentialsError(RuntimeError):
    pass


class PlayerMaxHpConfigurationError(RuntimeError):
    pass


def register_member(
    session: Session,
    login_id: str,
    password: str,
    player_name: str,
) -> User:
    existing = session.scalar(select(User).where(User.login_id == login_id))
    if existing is not None:
        raise LoginIdAlreadyExistsError(login_id)

    max_hp_setting = session.get(GameSetting, "player_max_hp")
    if (
        max_hp_setting is None
        or not isinstance(max_hp_setting.value, int)
        or isinstance(max_hp_setting.value, bool)
        or max_hp_setting.value <= 0
    ):
        raise PlayerMaxHpConfigurationError("player_max_hp must be a positive integer")

    user = User(
        login_id=login_id,
        password_hash=hash_password(password),
        player_name=player_name,
        current_hp=max_hp_setting.value,
        max_hp=max_hp_setting.value,
        role="member",
        must_change_password=False,
        is_active=True,
    )
    session.add(user)
    session.flush()

    cpu_ids = session.scalars(select(CpuCharacter.id)).all()
    session.add_all(
        [
            UserCpuProgress(
                user_id=user.id,
                cpu_character_id=cpu_id,
                defeat_stage=0,
            )
            for cpu_id in cpu_ids
        ]
    )
    session.flush()
    return user


def authenticate_user(session: Session, login_id: str, password: str) -> User:
    user = session.scalar(select(User).where(User.login_id == login_id))
    if user is None or not user.is_active:
        raise InvalidCredentialsError()
    if not verify_password(user.password_hash, password):
        raise InvalidCredentialsError()
    return user


def change_password(
    session: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(user.password_hash, current_password):
        raise InvalidCredentialsError()
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    session.flush()
