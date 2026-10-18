from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CharacterPromptCandidateEntry, CharacterPromptCandidates, CpuCharacter,
    SharedPromptDefault, SharedPromptItem,
)


def _error(status: int, code: str, message: str, fields: dict | None = None):
    detail = {"code": code, "message": message}
    if fields is not None:
        detail["fields"] = fields
    raise HTTPException(status_code=status, detail=detail)


def _item_dict(item: SharedPromptItem) -> dict:
    return {"id": item.id, "kind": item.kind, "level": item.level,
            "label": item.label, "positive": item.positive, "negative": item.negative,
            "revision": item.revision, "active": item.active}


def list_items(session: Session, kind: str, level: int) -> list[dict]:
    return [_item_dict(item) for item in session.scalars(select(SharedPromptItem).where(
        SharedPromptItem.kind == kind, SharedPromptItem.level == level,
        SharedPromptItem.active.is_(True),
    ).order_by(SharedPromptItem.label, SharedPromptItem.id)).all()]


def create_item(session: Session, data) -> dict:
    item = SharedPromptItem(id=str(uuid4()), kind=data.kind, level=data.level,
        label=data.label, positive=data.positive, negative=data.negative, revision=1, active=True)
    session.add(item)
    session.flush()
    session.commit()
    return _item_dict(item)


def patch_item(session: Session, item_id: str, data) -> dict:
    item = session.get(SharedPromptItem, item_id)
    if item is None or not item.active:
        _error(404, "not_found", "공유 프롬프트를 찾을 수 없습니다.")
    if item.revision != data.expected_revision:
        _error(409, "revision_conflict", "공유 프롬프트가 변경됐습니다. 다시 불러와 주세요.", {"expected_revision": item.revision})
    changed = False
    for field in ("label", "positive", "negative"):
        if field in data.model_fields_set and getattr(item, field) != getattr(data, field):
            setattr(item, field, getattr(data, field))
            changed = True
    if changed:
        item.revision += 1
        session.flush()
        session.commit()
    return _item_dict(item)


def get_default(session: Session, level: int, kind: str) -> dict:
    row = session.get(SharedPromptDefault, (level, kind))
    item = session.get(SharedPromptItem, row.item_id) if row and row.item_id else None
    valid = bool(item and item.active and item.level == level and item.kind == kind)
    return {"level": level, "kind": kind, "revision": row.revision if row else 0,
            "item_id": row.item_id if row else None, "valid": valid,
            "item": _item_dict(item) if valid else None}


def put_default(session: Session, level: int, kind: str, data) -> dict:
    row = session.get(SharedPromptDefault, (level, kind))
    revision = row.revision if row else 0
    if data.expected_revision != revision:
        _error(409, "revision_conflict", "기본값이 변경됐습니다. 다시 불러와 주세요.", {"expected_revision": revision})
    if data.item_id is not None:
        item = session.get(SharedPromptItem, data.item_id)
        if item is None or not item.active or item.level != level or item.kind != kind:
            _error(422, "invalid_default_item", "기본값은 같은 Level·종류의 활성 항목이어야 합니다.")
    if row is None and data.item_id is None:
        return get_default(session, level, kind)
    if row and row.item_id == data.item_id:
        return get_default(session, level, kind)
    if row is None:
        row = SharedPromptDefault(level=level, kind=kind, item_id=data.item_id, revision=1)
        session.add(row)
    else:
        row.item_id = data.item_id
        row.revision += 1
    session.flush()
    session.commit()
    return get_default(session, level, kind)


def get_candidates(session: Session, cpu_id: int, level: int, kind: str) -> dict:
    if session.get(CpuCharacter, cpu_id) is None:
        _error(404, "not_found", "캐릭터를 찾을 수 없습니다.")
    row = session.scalar(select(CharacterPromptCandidates).where(
        CharacterPromptCandidates.cpu_id == cpu_id,
        CharacterPromptCandidates.level == level,
        CharacterPromptCandidates.kind == kind,
    ))
    entries = session.scalars(select(CharacterPromptCandidateEntry).where(
        CharacterPromptCandidateEntry.candidate_set_id == row.id
    ).order_by(CharacterPromptCandidateEntry.id)).all() if row else []
    stored_ids = [entry.item_id for entry in entries]
    stored = [session.get(SharedPromptItem, item_id) for item_id in stored_ids]
    effective = [item for item in stored if item and item.active and item.level == level and item.kind == kind]
    uses_default = not effective
    default = get_default(session, level, kind) if uses_default else None
    if uses_default and default and default["valid"]:
        effective = [session.get(SharedPromptItem, default["item_id"])]
    return {
        "cpu_id": cpu_id, "level": level, "kind": kind,
        "revision": row.revision if row else 0,
        "stored_item_ids": stored_ids,
        "effective_items": [_item_dict(item) for item in effective],
        "uses_default": uses_default,
        "default_revision": default["revision"] if default else get_default(session, level, kind)["revision"],
        "unregistered": not effective,
    }


def put_candidates(session: Session, cpu_id: int, level: int, kind: str, data) -> dict:
    if session.get(CpuCharacter, cpu_id) is None:
        _error(404, "not_found", "캐릭터를 찾을 수 없습니다.")
    if len(set(data.item_ids)) != len(data.item_ids):
        _error(422, "duplicate_candidate", "후보 ID는 중복할 수 없습니다.")
    items = [session.get(SharedPromptItem, item_id) for item_id in data.item_ids]
    if any(item is None or not item.active or item.level != level or item.kind != kind for item in items):
        _error(422, "invalid_candidate", "후보는 같은 Level·종류의 활성 공유 항목이어야 합니다.")
    row = session.scalar(select(CharacterPromptCandidates).where(
        CharacterPromptCandidates.cpu_id == cpu_id,
        CharacterPromptCandidates.level == level,
        CharacterPromptCandidates.kind == kind,
    ))
    revision = row.revision if row else 0
    if data.expected_revision != revision:
        _error(409, "revision_conflict", "캐릭터 후보가 변경됐습니다. 다시 불러와 주세요.", {"expected_revision": revision})
    current = [entry.item_id for entry in session.scalars(select(CharacterPromptCandidateEntry).where(
        CharacterPromptCandidateEntry.candidate_set_id == row.id
    ).order_by(CharacterPromptCandidateEntry.id)).all()] if row else []
    if row is None and not data.item_ids:
        return get_candidates(session, cpu_id, level, kind)
    if row is not None and current == data.item_ids:
        return get_candidates(session, cpu_id, level, kind)
    if row is None:
        row = CharacterPromptCandidates(id=str(uuid4()), cpu_id=cpu_id, level=level, kind=kind, revision=1)
        session.add(row)
        session.flush()
    else:
        row.revision += 1
        session.query(CharacterPromptCandidateEntry).filter_by(candidate_set_id=row.id).delete(synchronize_session=False)
    session.add_all(CharacterPromptCandidateEntry(candidate_set_id=row.id, item_id=item_id) for item_id in data.item_ids)
    session.flush()
    session.commit()
    return get_candidates(session, cpu_id, level, kind)


def _impact(session: Session, item: SharedPromptItem, action: str, target_level: int | None) -> dict:
    source_default = session.get(SharedPromptDefault, (item.level, item.kind))
    next_default_id = source_default.item_id if source_default else None
    if next_default_id == item.id:
        next_default_id = None
    next_default = session.get(SharedPromptItem, next_default_id) if next_default_id else None
    if not next_default or not next_default.active or next_default.level != item.level or next_default.kind != item.kind:
        next_default = None
    sets = session.scalars(select(CharacterPromptCandidates).where(
        CharacterPromptCandidates.level == item.level,
        CharacterPromptCandidates.kind == item.kind,
    ).order_by(CharacterPromptCandidates.cpu_id)).all()
    scope_snapshot = []
    for row in sets:
        entries = session.scalars(select(CharacterPromptCandidateEntry).where(
            CharacterPromptCandidateEntry.candidate_set_id == row.id
        ).order_by(CharacterPromptCandidateEntry.id)).all()
        scope_snapshot.append({"candidate_set_id": row.id, "cpu_id": row.cpu_id,
            "revision": row.revision, "item_ids": [entry.item_id for entry in entries]})
    cpu_ids = [cpu.id for cpu in session.scalars(select(CpuCharacter).order_by(CpuCharacter.id)).all()]
    affected = []
    direct_rows = []
    for row in sets:
        entries = session.scalars(select(CharacterPromptCandidateEntry).where(
            CharacterPromptCandidateEntry.candidate_set_id == row.id
        ).order_by(CharacterPromptCandidateEntry.id)).all()
        ids = [entry.item_id for entry in entries]
        cpu = session.get(CpuCharacter, row.cpu_id)
        direct = item.id in ids
        old_valid = [session.get(SharedPromptItem, x) for x in ids]
        old_valid = [x for x in old_valid if x and x.active and x.level == item.level and x.kind == item.kind]
        after_valid = [x for x in old_valid if x.id != item.id] if direct else old_valid
        old_uses_default = not old_valid
        after_uses_default = not after_valid
        default_affected = source_default is not None and source_default.item_id == item.id and old_uses_default
        if direct:
            direct_rows.append({"cpu_id": row.cpu_id, "cpu_name": cpu.name if cpu else "",
                "cpu_slug": cpu.slug if cpu else "", "level": row.level, "kind": row.kind,
                "candidate_set_id": row.id, "candidate_revision": row.revision,
                "stored_item_ids": ids, "after_item_ids": [x for x in ids if x != item.id],
                "after_effective_item_ids": [x.id for x in after_valid],
                "uses_default_after": after_uses_default,
                "fallback_item_id": next_default.id if after_uses_default and next_default else None,
                "unregistered_after": after_uses_default and next_default is None})
        if default_affected:
            affected.append({"cpu_id": row.cpu_id, "cpu_name": cpu.name if cpu else "",
                "cpu_slug": cpu.slug if cpu else "", "level": row.level, "kind": row.kind,
                "candidate_set_id": row.id, "candidate_revision": row.revision,
                "reason": "default_reference", "fallback_item_id": None,
                "unregistered_after": True})
    # CPU rows with no candidate set also inherit the default at read time.
    set_cpu_ids = {row.cpu_id for row in sets}
    implicit_default_users = []
    if source_default and source_default.item_id == item.id:
        for cpu_id in cpu_ids:
            if cpu_id in set_cpu_ids:
                continue
            cpu = session.get(CpuCharacter, cpu_id)
            implicit_default_users.append({"cpu_id": cpu_id, "cpu_name": cpu.name,
                "cpu_slug": cpu.slug, "level": item.level, "kind": item.kind,
                "candidate_set_id": None, "candidate_revision": 0,
                "reason": "default_reference", "fallback_item_id": None,
                "unregistered_after": True})
    return {
        "item": {"id": item.id, "kind": item.kind, "level": item.level,
                 "label": item.label, "revision": item.revision},
        "action": action, "target_level": target_level,
        "candidate_changes": direct_rows,
        "candidate_scope_snapshot": scope_snapshot,
        "affected_cpus": sorted(affected + implicit_default_users, key=lambda x: (x["cpu_id"], x["kind"])),
        "source_default": {"item_id": source_default.item_id if source_default else None,
            "revision": source_default.revision if source_default else 0,
            "after_item_id": next_default.id if next_default else None,
            "after_item_revision": next_default.revision if next_default else None,
            "will_clear": bool(source_default and source_default.item_id == item.id)},
        "new_level": {"level": target_level, "candidate_auto_inclusion": False,
            "default_auto_assignment": False} if action == "move" else None,
    }


def preview_change(session: Session, item_id: str, data) -> dict:
    item = session.get(SharedPromptItem, item_id)
    if item is None or not item.active:
        _error(404, "not_found", "공유 프롬프트를 찾을 수 없습니다.")
    if item.revision != data.expected_revision:
        _error(409, "revision_conflict", "공유 프롬프트가 변경됐습니다. 다시 불러와 주세요.", {"expected_revision": item.revision})
    impact = _impact(session, item, data.action, data.target_level)
    canonical = json.dumps(impact, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    impact["preview_digest"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return impact


def confirm_change(session: Session, item_id: str, data) -> dict:
    current = preview_change(session, item_id, data)
    if current["preview_digest"] != data.preview_digest:
        _error(409, "preview_stale", "연결 대상이나 기본값이 바뀌었습니다. 영향을 다시 확인해 주세요.")
    item = session.get(SharedPromptItem, item_id)
    for candidate in current["candidate_changes"]:
        row = session.get(CharacterPromptCandidates, candidate["candidate_set_id"])
        if row is None or row.revision != candidate["candidate_revision"]:
            _error(409, "preview_stale", "캐릭터 후보가 바뀌었습니다. 영향을 다시 확인해 주세요.")
        session.query(CharacterPromptCandidateEntry).filter_by(
            candidate_set_id=row.id, item_id=item.id
        ).delete(synchronize_session=False)
        row.revision += 1
    source_default = session.get(SharedPromptDefault, (item.level, item.kind))
    if source_default and source_default.item_id == item.id:
        source_default.item_id = None
        source_default.revision += 1
    if data.action == "move":
        item.level = data.target_level
    else:
        item.active = False
    item.revision += 1
    session.flush()
    session.commit()
    return {"item": _item_dict(item), "action": data.action, "confirmed": True,
            "changed_candidate_sets": len(current["candidate_changes"]),
            "cleared_default": bool(current["source_default"]["will_clear"])}
