from __future__ import annotations

from uuid import uuid4
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CharacterContent, CharacterLevelFraming, CpuCharacter, ContentPack,
    ContentPackRevision, ContentPackFile, ContentPackScanEntry, LocalMediaAsset,
)
from app.schemas.local_content import CharacterContentPatch, CharacterPackApplication, PackManifest
from app.services.local_media import media_url, media_path, MAX_IMAGE_BYTES
from app.services.content_packs import read_file, digest, ScanIssue

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
    applied = session.get(ContentPackRevision, record.pack_revision_id) if record and record.pack_revision_id else None
    pack = session.get(ContentPack, applied.pack_id) if applied else None
    images = _revision_images(session, applied) if applied else {}
    for level, kinds in levels.items():
        for kind, pair in kinds.items():
            pair["media"] = images.get(level, {}).get(kind)
    return {
        "pack_source": {"prompts": applied.manifest["prompts"], "levels": applied.manifest["levels"]} if applied else None,
        "pack": {
            "id": pack.id, "pack_id": pack.pack_id,
            "applied_revision_id": applied.id, "applied_revision": applied.revision,
            "registered_revision_id": pack.registered_revision_id,
            "update_available": pack.registered_revision_id != applied.id,
        } if pack else None,
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


def _revision_images(session: Session, revision: ContentPackRevision) -> dict:
    files = {ref.relative_path: ref for ref in session.scalars(
        select(ContentPackFile).where(ContentPackFile.revision_id == revision.id)
    )}
    return {
        level: {
            kind: {
                "media_id": files[path].media_asset_id,
                "url": media_url(files[path].media_asset_id),
                "digest": files[path].digest,
            } if path in files else None
            for kind, path in data["images"].items()
        }
        for level, data in revision.manifest["levels"].items()
    }


def get_character_pack_revision(session: Session, cpu_id: int, revision_id: str) -> dict:
    # Only a revision belonging to the explicitly linked pack is addressable here.
    content = get_character_content(session, cpu_id)
    revision = session.get(ContentPackRevision, revision_id)
    if not content["pack"] or not revision or revision.pack_id != content["pack"]["id"]:
        raise HTTPException(404, detail={"code": "not_found", "message": "연결된 팩의 revision을 찾을 수 없습니다."})
    return {
        "schema_version": 1, "cpu_id": cpu_id, "pack_id": revision.pack_id,
        "revision_id": revision.id, "revision": revision.revision,
        "content_digest": revision.content_digest, "prompts": revision.manifest["prompts"],
        "levels": revision.manifest["levels"], "media": _revision_images(session, revision),
    }


def apply_character_pack(
    session: Session, cpu_id: int, change: CharacterPackApplication, root: Path, media_root: Path
) -> dict:
    current = get_character_content(session, cpu_id)
    if current["revision"] != change.expected_revision:
        raise HTTPException(409, detail={"code": "revision_conflict", "message": "캐릭터 자료가 변경됐습니다. 다시 열어 확인해 주세요."})
    pack = session.get(ContentPack, change.pack_id)
    if pack is None:
        raise HTTPException(404, detail={"code": "not_found", "message": "팩을 찾을 수 없습니다."})
    if pack.kind != "character":
        raise HTTPException(422, detail={"code": "invalid_pack_kind", "message": "캐릭터팩만 연결할 수 있습니다."})
    if current["pack"] and current["pack"]["id"] != pack.id:
        raise HTTPException(409, detail={"code": "pack_replacement_excluded", "message": "다른 팩으로 교체할 수 없습니다."})
    if not pack.registered_revision_id or pack.registered_revision_id != change.registered_revision_id:
        raise HTTPException(409, detail={"code": "pack_revision_conflict", "message": "등록 revision이 변경됐습니다. 팩 목록을 다시 확인해 주세요."})
    revision = session.get(ContentPackRevision, pack.registered_revision_id)
    entries = session.scalars(select(ContentPackScanEntry)).all()
    if any((e.identity == ["character", "", pack.pack_id] or e.source == f"characters/{pack.pack_id}") and (e.status != "normal" or e.issues) for e in entries):
        raise HTTPException(409, detail={"code": "pack_unresolved", "message": "팩 검색 진단을 해결한 뒤 다시 적용해 주세요."})
    if revision is None or revision.pack_id != pack.id:
        raise HTTPException(409, detail={"code": "pack_unresolved", "message": "팩 revision을 확인할 수 없습니다."})
    parsed = PackManifest.model_validate(revision.manifest)
    if parsed.shared_dependencies:
        raise HTTPException(409, detail={"code": "pack_unresolved", "message": "공유 의존성이 해결되지 않았습니다."})
    # Apply only fully preserved, digest-verified immutable media. Never read live sources.
    files = {ref.relative_path: ref for ref in session.scalars(
        select(ContentPackFile).where(ContentPackFile.revision_id == revision.id)
    )}
    try:
        for path in parsed.references():
            ref = files[path]
            asset = session.get(LocalMediaAsset, ref.media_asset_id)
            if asset is None or asset.kind != "image":
                raise ValueError("missing media")
            data, _ = read_file(root, media_path(media_root, asset.storage_key), MAX_IMAGE_BYTES)
            if digest(data) != ref.digest:
                raise ValueError("media digest mismatch")
    except (OSError, ValueError, KeyError, RuntimeError, ScanIssue):
        raise HTTPException(409, detail={"code": "pack_media_unavailable", "message": "보관된 팩 이미지 파일을 확인할 수 없습니다."}) from None
    if current["pack_revision_id"] == revision.id:
        return current
    record = session.get(CharacterContent, cpu_id)
    prompts = {}
    for group in PROMPT_GROUPS:
        pair = current["prompts"][group]
        prompts[group] = {
            field: pair[field] if pair["overrides"][field] else revision.manifest["prompts"][group][field]
            for field in ("positive", "negative")
        }
    if record is None:
        record = CharacterContent(cpu_id=cpu_id, overrides=[])
        session.add(record)
    record.prompts = prompts
    record.pack_revision_id = revision.id
    record.revision = current["revision"] + 1
    for level in range(4):
        for kind in IMAGE_KINDS:
            pair = current["levels"][str(level)][kind]
            item = session.scalar(select(CharacterLevelFraming).where(
                CharacterLevelFraming.cpu_id == cpu_id,
                CharacterLevelFraming.level == level, CharacterLevelFraming.kind == kind,
            ))
            if item is None:
                item = CharacterLevelFraming(id=str(uuid4()), cpu_id=cpu_id, level=level, kind=kind, overrides=[])
                session.add(item)
            for field in ("positive", "negative"):
                setattr(item, field, pair[field] if pair["overrides"][field] else revision.manifest["levels"][str(level)]["framing"][kind][field])
            item.revision = pair["revision"] + 1
    from app.services.audio_packs import sync_default_voice_pack
    sync_default_voice_pack(session, cpu_id)
    session.flush()
    session.commit()
    return get_character_content(session, cpu_id)
