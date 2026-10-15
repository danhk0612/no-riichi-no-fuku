from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def create_access_token(
    user_id: int,
    secret: str,
    expires_minutes: int,
) -> tuple[str, int]:
    expires_delta = timedelta(minutes=expires_minutes)
    expires_at = datetime.now(UTC) + expires_delta
    token = jwt.encode(
        {"sub": str(user_id), "exp": expires_at, "type": "access"},
        secret,
        algorithm="HS256",
    )
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str, secret: str) -> int:
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("invalid token type")
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isdigit():
        raise jwt.InvalidTokenError("invalid token subject")
    return int(subject)
