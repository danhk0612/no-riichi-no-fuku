from __future__ import annotations

import json
from pathlib import Path

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CpuCharacter, User


CPU_SEED_PATH = Path(__file__).resolve().parents[1] / "seeds" / "cpu_characters.json"


class BootstrapConflictError(RuntimeError):
    pass


def bootstrap_superadmin(
    session: Session,
    login_id: str,
    initial_password: str,
    *,
    password_hasher: PasswordHasher | None = None,
) -> bool:
    existing_superadmin = session.scalar(
        select(User).where(User.role == "superadmin")
    )
    if existing_superadmin is not None:
        return False

    existing_login = session.scalar(select(User).where(User.login_id == login_id))
    if existing_login is not None:
        raise BootstrapConflictError(
            "SUPERADMIN_LOGIN_ID is already used by a non-superadmin account"
        )

    hasher = password_hasher or PasswordHasher()
    session.add(
        User(
            login_id=login_id,
            password_hash=hasher.hash(initial_password),
            role="superadmin",
            must_change_password=True,
            is_active=True,
        )
    )
    session.flush()
    return True


def seed_cpu_characters(
    session: Session,
    seed_path: Path = CPU_SEED_PATH,
) -> int:
    seed_entries = json.loads(seed_path.read_text(encoding="utf-8"))
    created = 0

    for entry in seed_entries:
        if entry.get("adult") is not True:
            raise ValueError(f"CPU seed must be adult: {entry.get('slug')}")
        existing = session.scalar(
            select(CpuCharacter).where(CpuCharacter.slug == entry["slug"])
        )
        if existing is not None:
            continue

        session.add(
            CpuCharacter(
                slug=entry["slug"],
                name=entry["name"],
                age_adult=True,
                style=entry["style"],
                short_description=entry["description"],
                profile_image_key=entry["profile_image"],
                active=True,
                aggression=entry["aggression"],
                defense=entry["defense"],
                call_preference=entry["call_preference"],
                riichi_preference=entry["riichi_preference"],
                hand_value_preference=entry["hand_value_preference"],
                speed_preference=entry["speed_preference"],
            )
        )
        created += 1

    session.flush()
    return created
