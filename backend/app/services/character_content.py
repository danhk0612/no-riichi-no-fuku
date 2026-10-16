from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CharacterContent, CharacterLevelFraming, CpuCharacter
from app.schemas.local_content import CharacterContentPatch

PROMPT_GROUPS = ("appearance", "upper_underwear", "lower_underwear")
IMAGE_KINDS = ("profile", "full_body", "cg")


def _empty_pair() -> dict:
    return {"positive": "", "negative": ""}


def get_character_content(session: Session, cpu_id: int) -> dict:
    if session.get(CpuCharacter, cpu_id) is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "캐릭터를 찾을 수 없습니다."})
    record = session.get(CharacterContent, cpu_id)
    prompts = record.prompts if record else {key: _empty_pair() for key in PROMPT_GROUPS}
    overrides = set(record.overrides or []) if record else set()
    level_records = session.scalars(
        select(CharacterLevelFraming).where(CharacterLevelFraming.cpu_id == cpu_id)
    ).all()
    by_identity = {(item.level, item.kind): item for item in level_records}
    levels = {}
    for level in range(4):
        levels[str(level)] = {}
        for kind in IMAGE_KINDS:
            item = by_identity.get((level, kind))
            levels[str(level)][kind] = {
                "positive": item.positive if item else "",
                "negative": item.negative if item else "",
                "revision": item.revision if item else 0,
                "overrides": {
                    "positive": bool(item and "positive" in (item.overrides or [])),
                    "negative": bool(item and "negative" in (item.overrides or [])),
                },
            }
    return {
        "schema_version": 1,
        "cpu_id": cpu_id,
        "revision": record.revision if record else 0,
        "pack_revision_id": record.pack_revision_id if record else None,
        "prompts": {
            key: {
                "positive": prompts.get(key, {}).get("positive", ""),
                "negative": prompts.get(key, {}).get("negative", ""),
                "overrides": {
                    field: f"{key}.{field}" in overrides
                    for field in ("positive", "negative")
                },
            }
            for key in PROMPT_GROUPS
        },
        "levels": levels,
    }


def patch_character_content(
    session: Session, cpu_id: int, change: CharacterContentPatch
) -> dict:
    if session.get(CpuCharacter, cpu_id) is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "캐릭터를 찾을 수 없습니다."})
    record = session.get(CharacterContent, cpu_id)
    revision = record.revision if record else 0
    if revision != change.expected_revision:
        raise HTTPException(
            status_code=409,
            detail={"code": "revision_conflict", "message": "다른 편집이 먼저 저장됐습니다.", "fields": {"expected_revision": revision}},
        )
    prompts = {key: _empty_pair() for key in PROMPT_GROUPS}
    overrides: set[str] = set()
    if record:
        prompts.update({key: dict(value) for key, value in (record.prompts or {}).items()})
        overrides.update(record.overrides or [])
    for group, edit in change.prompts.items():
        for field in edit.model_fields_set:
            prompts[group][field] = getattr(edit, field)
            overrides.add(f"{group}.{field}")
    if record is None:
        record = CharacterContent(
            cpu_id=cpu_id, pack_revision_id=None, revision=0,
            prompts=prompts, overrides=sorted(overrides),
        )
        session.add(record)
    record.prompts = prompts
    record.overrides = sorted(overrides)
    record.revision = revision + 1

    touched = set()
    for edit in change.framing:
        identity = (edit.level, edit.kind)
        if identity in touched:
            raise HTTPException(status_code=422, detail={"code": "duplicate_framing", "message": "같은 단계/구도는 한 번만 지정할 수 있습니다."})
        touched.add(identity)
        item = session.scalar(
            select(CharacterLevelFraming).where(
                CharacterLevelFraming.cpu_id == cpu_id,
                CharacterLevelFraming.level == edit.level,
                CharacterLevelFraming.kind == edit.kind,
            )
        )
        if item is None:
            item = CharacterLevelFraming(
                id=str(uuid4()), cpu_id=cpu_id, level=edit.level, kind=edit.kind,
                revision=0, positive="", negative="", overrides=[],
            )
            session.add(item)
        item_overrides = set(item.overrides or [])
        for field in edit.model_fields_set - {"level", "kind"}:
            setattr(item, field, getattr(edit, field))
            item_overrides.add(field)
        item.overrides = sorted(item_overrides)
        item.revision += 1
    session.flush()
    # Commit here so a successful response can never precede a failed write.
    session.commit()
    return get_character_content(session, cpu_id)
