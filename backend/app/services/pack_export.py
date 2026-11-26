"""Write a portable pack tree from immutable saved media and character settings."""
import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.db.models import ContentPack, ContentPackFile, ContentPackRevision, CpuCharacter, LocalMediaAsset
from app.schemas.local_content import PackManifest
from app.services.audio_packs import audio_pack_selection_response, character_voice_selection
from app.services.character_content import get_character_content
from app.services.content_packs import safe_path, ScanIssue
from app.services.generation_settings import match_inputs
from app.services.local_media import media_path


def write_manifest(folder, manifest):
    PackManifest.model_validate(manifest)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def copy_asset(session, media, asset_id, target, expected_digest=None):
    asset = session.get(LocalMediaAsset, asset_id)
    if not asset:
        raise HTTPException(409, "등록된 미디어를 찾을 수 없습니다.")
    source = safe_path(media, media_path(media, asset.storage_key))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    if expected_digest:
        with target.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected_digest:
                raise HTTPException(409, "미디어 파일이 등록된 내용과 다릅니다.")


def copy_audio_pack(session, media, tree, pack_uuid):
    pack = session.get(ContentPack, pack_uuid)
    revision = session.get(ContentPackRevision, pack.registered_revision_id)
    manifest = revision.manifest
    parsed = PackManifest.model_validate(manifest)
    folder = tree / {"voice": "voices", "bgm": "bgm", "sfx": "sfx"}[pack.kind]
    if pack.kind == "voice":
        folder /= parsed.character_id
    folder /= parsed.id
    for ref in session.scalars(select(ContentPackFile).where(ContentPackFile.revision_id == revision.id)):
        copy_asset(session, media, ref.media_asset_id, folder / ref.relative_path, ref.digest)
    write_manifest(folder, manifest)
    return {"id": parsed.id, "character_id": parsed.character_id}


def export_character(session, registry, cpu_id, pack_id, include_audio):
    content = get_character_content(session, cpu_id)
    cpu = session.get(CpuCharacter, cpu_id)
    root = registry.game_root or registry.root
    exports = root / "exports"
    media = registry.media_root
    try:
        exports.mkdir(exist_ok=True)
        safe_path(root, exports)
        with TemporaryDirectory(dir=exports) as temp:
            bundle = Path(temp) / "bundle"
            tree = bundle / "packs"
            folder = tree / "characters" / pack_id
            def pair(item):
                return {key: item[key] for key in ("positive", "negative")}
            levels = {}
            for level, slots in content["levels"].items():
                images = {}
                for kind, slot in slots.items():
                    image = slot["media"]
                    images[kind] = None
                    if image:
                        asset = session.get(LocalMediaAsset, image["media_id"])
                        if not asset:
                            raise HTTPException(409, "등록된 이미지를 찾을 수 없습니다.")
                        name = f"images/level-{level}/{kind}{Path(asset.storage_key).suffix}"
                        copy_asset(session, media, asset.id, folder / name, image["digest"])
                        images[kind] = name
                levels[level] = {"images": images, "framing": {k: pair(v) for k, v in slots.items()}}
            ending = pair(content["ending"])
            ending_media = content["ending"]["media"]
            if ending_media:
                asset = session.get(LocalMediaAsset, ending_media["media_id"])
                ending["image"] = "images/ending" + Path(asset.storage_key).suffix
                copy_asset(session, media, asset.id, folder / ending["image"], ending_media["digest"])
            voice = character_voice_selection(session, cpu_id)
            voice_id = voice["selected_pack_id"] or voice["default_pack_id"]
            voice_ref = None
            if voice_id and voice["selection_mode"] != "off":
                voice_ref = copy_audio_pack(session, media, tree, voice_id)
            if include_audio:
                selection = audio_pack_selection_response(session)
                for kind in ("bgm", "sfx"):
                    if selection[kind + "_mode"] == "pack":
                        for pack_uuid in {selection[kind + "_pack_id"], selection["defaults"][kind]} - {None}:
                            copy_audio_pack(session, media, tree, pack_uuid)
            metadata = dict((content["pack_source"] or {}).get("metadata") or {})
            metadata.update(name=cpu.name, adult=True, measurements_cm=content["measurements_cm"])
            generation = match_inputs(session)
            character_settings = generation.characters.get(cpu_id) if generation else None
            write_manifest(folder, {**({"generation": character_settings.model_dump()} if character_settings else {}),
                "schema_version": 1, "kind": "character", "id": pack_id,
                "character_id": pack_id, "label": cpu.name, "version": "1", "metadata": metadata,
                "levels": levels, "ending": ending, "prompts": {k: pair(v) for k, v in content["prompts"].items()},
                "default_voice_pack": voice_ref, "shared_dependencies": []})
            destination = exports / (pack_id + "-" + uuid4().hex[:12])
            bundle.rename(destination)
            return {"folder": str(destination)}
    except (OSError, ScanIssue) as error:
        raise HTTPException(409, "팩을 내보내지 못했습니다. 원본 파일과 게임 폴더 쓰기 권한을 확인해 주세요.") from error
