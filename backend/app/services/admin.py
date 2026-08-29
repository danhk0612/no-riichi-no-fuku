from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CpuCharacter, CpuDialogue, User, UserCpuProgress


class AdminEntityNotFoundError(RuntimeError):
    pass


class CpuSlugAlreadyExistsError(RuntimeError):
    pass


def list_members(session: Session) -> list[User]:
    return list(
        session.scalars(
            select(User).where(User.role == "member").order_by(User.id)
        ).all()
    )


def update_member_active(session: Session, user_id: int, is_active: bool) -> User:
    user = session.scalar(
        select(User).where(User.id == user_id, User.role == "member")
    )
    if user is None:
        raise AdminEntityNotFoundError("member not found")
    user.is_active = is_active
    session.flush()
    return user


def list_cpu_characters(session: Session) -> list[CpuCharacter]:
    return list(session.scalars(select(CpuCharacter).order_by(CpuCharacter.id)).all())


def create_cpu_character(
    session: Session,
    values: dict[str, object],
) -> CpuCharacter:
    existing = session.scalar(
        select(CpuCharacter).where(CpuCharacter.slug == values["slug"])
    )
    if existing is not None:
        raise CpuSlugAlreadyExistsError(str(values["slug"]))

    cpu = CpuCharacter(age_adult=True, profile_image_key=None, **values)
    session.add(cpu)
    session.flush()

    member_ids = session.scalars(select(User.id).where(User.role == "member")).all()
    session.add_all(
        [
            UserCpuProgress(
                user_id=member_id,
                cpu_character_id=cpu.id,
                defeat_stage=0,
            )
            for member_id in member_ids
        ]
    )
    session.flush()
    return cpu


def update_cpu_character(
    session: Session,
    cpu_id: int,
    values: dict[str, object],
) -> CpuCharacter:
    cpu = session.get(CpuCharacter, cpu_id)
    if cpu is None:
        raise AdminEntityNotFoundError("CPU character not found")
    for field, value in values.items():
        setattr(cpu, field, value)
    session.flush()
    return cpu


def list_cpu_dialogues(session: Session, cpu_id: int) -> list[CpuDialogue]:
    if session.get(CpuCharacter, cpu_id) is None:
        raise AdminEntityNotFoundError("CPU character not found")
    return list(
        session.scalars(
            select(CpuDialogue)
            .where(CpuDialogue.cpu_character_id == cpu_id)
            .order_by(CpuDialogue.id)
        ).all()
    )


def create_cpu_dialogue(
    session: Session,
    cpu_id: int,
    values: dict[str, object],
) -> CpuDialogue:
    if session.get(CpuCharacter, cpu_id) is None:
        raise AdminEntityNotFoundError("CPU character not found")
    dialogue = CpuDialogue(cpu_character_id=cpu_id, **values)
    session.add(dialogue)
    session.flush()
    return dialogue


def update_cpu_dialogue(
    session: Session,
    dialogue_id: int,
    values: dict[str, object],
) -> CpuDialogue:
    dialogue = session.get(CpuDialogue, dialogue_id)
    if dialogue is None:
        raise AdminEntityNotFoundError("CPU dialogue not found")
    for field, value in values.items():
        setattr(dialogue, field, value)
    session.flush()
    return dialogue


def delete_cpu_dialogue(session: Session, dialogue_id: int) -> None:
    dialogue = session.get(CpuDialogue, dialogue_id)
    if dialogue is None:
        raise AdminEntityNotFoundError("CPU dialogue not found")
    session.delete(dialogue)
    session.flush()
