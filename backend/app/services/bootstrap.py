from __future__ import annotations

import json
from pathlib import Path

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CpuCharacter, CpuDialogue, CpuResultAsset, User


CPU_SEED_PATH = Path(__file__).resolve().parents[1] / "seeds" / "cpu_characters.json"
CPU_DIALOGUE_SEED_PATH = (
    Path(__file__).resolve().parents[1] / "seeds" / "cpu_dialogues.json"
)


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


def seed_cpu_dialogues(
    session: Session,
    seed_path: Path = CPU_DIALOGUE_SEED_PATH,
) -> int:
    seed_entries = json.loads(seed_path.read_text(encoding="utf-8"))
    created = 0

    for slug, event_pools in seed_entries.items():
        cpu = session.scalar(
            select(CpuCharacter).where(CpuCharacter.slug == slug)
        )
        if cpu is None:
            raise ValueError(f"Dialogue seed CPU does not exist: {slug}")
        for event_key, lines in event_pools.items():
            existing = session.scalar(
                select(CpuDialogue.id).where(
                    CpuDialogue.cpu_character_id == cpu.id,
                    CpuDialogue.event_key == event_key,
                )
            )
            if existing is not None:
                continue
            for text in lines:
                session.add(
                    CpuDialogue(
                        cpu_character_id=cpu.id,
                        event_key=event_key,
                        text=text,
                        active=True,
                    )
                )
                created += 1

    session.flush()
    return created


def seed_result_asset_slots(session: Session) -> int:
    created = 0
    cpu_ids = session.scalars(select(CpuCharacter.id)).all()
    existing_slots = set(
        session.execute(
            select(
                CpuResultAsset.cpu_character_id,
                CpuResultAsset.defeat_stage,
            )
        ).all()
    )
    for cpu_id in cpu_ids:
        for defeat_stage in (1, 2, 3):
            if (cpu_id, defeat_stage) in existing_slots:
                continue
            session.add(
                CpuResultAsset(
                    cpu_character_id=cpu_id,
                    defeat_stage=defeat_stage,
                    storage_key=None,
                    mime_type=None,
                    active=False,
                )
            )
            created += 1

    session.flush()
    return created
