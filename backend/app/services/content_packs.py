"""Local, read-only source scanning and immutable pack revision registration."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    ContentPack,
    ContentPackFile,
    ContentPackRevision,
    ContentPackScanEntry,
    LocalMediaAsset,
)
from app.db.session import mark_write_intent
from app.schemas.local_content import PackManifest, PackValidationError, relative_file
from app.services.local_media import (
    MAX_AUDIO_BYTES,
    MAX_IMAGE_BYTES,
    LocalMediaError,
    _identify,
    media_path,
    media_url,
)

ID_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
MAX_MANIFEST_BYTES = 1024 * 1024


class ScanIssue(Exception):
    def __init__(self, code: str):
        self.code = code


def canonical(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ScanIssue("duplicate_json_key")
        result[key] = value
    return result


def safe_path(root: Path, path: Path) -> Path:
    """Reject every link/reparse component, including a linked packs/category root."""
    try:
        parts = path.relative_to(root).parts
        cursor = root
        for part in parts:
            cursor = cursor / part
            info = cursor.lstat()
            if (
                stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise ScanIssue("unsafe_path")
        if not path.resolve().is_relative_to(root.resolve()):
            raise ScanIssue("unsafe_path")
        return path
    except ValueError:
        raise ScanIssue("unsafe_path") from None


def read_file(root: Path, path: Path, limit: int) -> tuple[bytes, tuple]:
    safe_path(root, path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ScanIssue("not_regular_file")
    if before.st_size > limit:
        raise ScanIssue("file_too_large")
    with path.open("rb") as source:
        data = source.read(limit + 1)
    safe_path(root, path)
    after = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if len(data) > limit:
        raise ScanIssue("file_too_large")
    if identity(before) != identity(after) or len(data) != before.st_size:
        raise ScanIssue("incomplete_copy")
    return data, identity(after)


@dataclass
class Candidate:
    source: str
    identity: tuple[str, str, str] | None = None
    status: str = "unresolved"
    issues: list[str] | None = None
    manifest: dict | None = None
    parsed: PackManifest | None = None
    manifest_digest: str | None = None
    content_digest: str | None = None
    files: dict | None = None
    raw_manifest: bytes | None = None
    manifest_stamp: tuple | None = None

    def entry(self):
        return {
            "source": self.source,
            "identity": list(self.identity) if self.identity else None,
            "status": self.status,
            "issues": self.issues or [],
        }


class ContentPackRegistry:
    def __init__(self, data_root: Path, media_root: Path, sessions: sessionmaker):
        self.root = data_root
        self.pack_root = data_root / "packs"
        self.media_root = media_root
        self.sessions = sessions
        self.lock = RLock()

    def _discover(self) -> list[Candidate]:
        candidates = []
        for category in ("characters", "sfx", "bgm", "voices"):
            category_root = self.pack_root / category
            if not category_root.exists() and not category_root.is_symlink():
                continue
            try:
                safe_path(self.root, category_root)
                for folder in sorted(category_root.iterdir()):
                    # Files alongside pack folders are not pack candidates.
                    if not folder.is_dir() and not folder.is_symlink():
                        continue
                    try:
                        safe_path(self.root, folder)
                        roots = (
                            sorted(folder.iterdir())
                            if category == "voices"
                            else [folder]
                        )
                        for pack in roots:
                            if pack.is_dir() or pack.is_symlink():
                                candidates.append(
                                    Candidate(
                                        pack.relative_to(self.pack_root).as_posix()
                                    )
                                )
                    except (OSError, ScanIssue):
                        candidates.append(
                            Candidate(
                                folder.relative_to(self.pack_root).as_posix(),
                                issues=["unsafe_or_unreadable_source"],
                            )
                        )
            except (OSError, ScanIssue):
                candidates.append(
                    Candidate(category, issues=["unsafe_or_unreadable_source"])
                )
        return candidates

    def _inspect(self, candidate: Candidate) -> None:
        if candidate.issues:
            return
        folder = self.pack_root / candidate.source
        try:
            raw, manifest_stamp = read_file(
                self.root, folder / "manifest.json", MAX_MANIFEST_BYTES
            )
            value = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_no_duplicate_keys,
                parse_constant=lambda _: (_ for _ in ()).throw(
                    ScanIssue("invalid_json")
                ),
            )
            if not isinstance(value, dict):
                raise ScanIssue("invalid_manifest")
            # Keep claims even if validation fails, so a broken duplicate cannot replace a good registration.
            kind, namespace, pack_id = (
                value.get("kind"),
                value.get("character_id") if value.get("kind") == "voice" else "",
                value.get("id"),
            )
            if (
                isinstance(kind, str)
                and kind in {"character", "sfx", "bgm", "voice"}
                and all(
                    isinstance(v, str) and len(v) <= 80 and ID_PATTERN.fullmatch(v)
                    for v in (pack_id, *([namespace] if kind == "voice" else []))
                )
            ):
                candidate.identity = kind, namespace, pack_id
            if (
                type(value.get("schema_version")) is int
                and value["schema_version"] != 1
            ):
                raise ScanIssue("unsupported_schema_version")
            parsed = PackManifest.model_validate(value)
            candidate.identity = parsed.identity()
            expected = {
                "character": f"characters/{parsed.id}",
                "sfx": f"sfx/{parsed.id}",
                "bgm": f"bgm/{parsed.id}",
                "voice": f"voices/{parsed.character_id}/{parsed.id}",
            }[parsed.kind]
            if candidate.source != expected:
                raise ScanIssue("directory_identity_mismatch")
            files = {}
            case_paths = set()
            for name, media_kind in sorted(parsed.references().items()):
                relative_file(name)
                folded = name.casefold()
                if folded in case_paths:
                    raise ScanIssue("file_path_conflict")
                case_paths.add(folded)
                limit = MAX_IMAGE_BYTES if media_kind == "image" else MAX_AUDIO_BYTES
                data, stamp = read_file(self.root, folder / name, limit)
                mime, extension = _identify(media_kind, name, None, data[:16])
                files[name] = (data, digest(data), stamp, media_kind, mime, extension)
            # A second complete read detects interrupted/cross-file copies before metadata is written.
            self._verify_source(folder, raw, manifest_stamp, files)
            candidate.raw_manifest, candidate.manifest_stamp = raw, manifest_stamp
            candidate.manifest = value
            candidate.parsed = parsed
            candidate.manifest_digest = digest(canonical(value))
            candidate.content_digest = digest(
                canonical(
                    {
                        "manifest": value,
                        "files": [
                            [name, item[1]] for name, item in sorted(files.items())
                        ],
                    }
                )
            )
            candidate.files = files
            candidate.status, candidate.issues = "normal", []
        except ScanIssue as error:
            candidate.issues = [error.code]
        except (
            OSError,
            UnicodeError,
            ValueError,
            TypeError,
            RecursionError,
            ValidationError,
            LocalMediaError,
        ):
            candidate.issues = ["invalid_manifest_or_file"]

    def _verify_source(self, folder, raw, manifest_stamp, files):
        again, stamp = read_file(
            self.root, folder / "manifest.json", MAX_MANIFEST_BYTES
        )
        if again != raw or stamp != manifest_stamp:
            raise ScanIssue("incomplete_copy")
        for name, item in files.items():
            data, expected_digest, expected_stamp, kind, _, _ = item
            again, stamp = read_file(
                self.root,
                folder / name,
                MAX_IMAGE_BYTES if kind == "image" else MAX_AUDIO_BYTES,
            )
            if stamp != expected_stamp or digest(again) != expected_digest:
                raise ScanIssue("incomplete_copy")

    def _register(self, candidate: Candidate) -> str:
        # Repeated scans do not write/discard duplicate media files.
        with self.sessions() as session:
            kind, namespace, pack_id = candidate.identity
            pack = session.scalar(
                select(ContentPack).where(
                    ContentPack.kind == kind,
                    ContentPack.namespace == namespace,
                    ContentPack.pack_id == pack_id,
                )
            )
            known = (
                session.scalar(
                    select(ContentPackRevision).where(
                        ContentPackRevision.pack_id == pack.id,
                        ContentPackRevision.content_digest == candidate.content_digest,
                    )
                )
                if pack
                else None
            )
            if known is not None and pack.registered_revision_id == known.id:
                return "unchanged"
            known_id, pack_uuid = (known.id, pack.id) if known else (None, None)
        if known_id:
            # A -> B -> A recognizes the existing A without applying it or copying files.
            with self.sessions() as session:
                mark_write_intent(session)
                pack = session.get(ContentPack, pack_uuid)
                pack.registered_revision_id = known_id
                session.commit()
            return "unchanged"
        owned = []
        try:
            # Prepare immutable copies before taking any DB writer reservation.
            assets = []
            for name, (
                data,
                file_digest,
                _,
                kind,
                mime,
                extension,
            ) in candidate.files.items():
                asset_id = str(uuid4())
                storage_key = f"packs/{asset_id}.{extension}"
                destination = media_path(self.media_root, storage_key)
                # Reuse media storage; reject a replaced media/packs directory too.
                destination.parent.mkdir(parents=True, exist_ok=True)
                safe_path(self.root, destination.parent)
                with destination.open("xb") as output:
                    owned.append(destination)
                    output.write(data)
                assets.append(
                    (
                        name,
                        file_digest,
                        LocalMediaAsset(
                            id=asset_id,
                            kind=kind,
                            storage_key=storage_key,
                            mime_type=mime,
                            byte_size=len(data),
                        ),
                    )
                )
            self._verify_source(
                self.pack_root / candidate.source,
                candidate.raw_manifest,
                candidate.manifest_stamp,
                candidate.files,
            )
            with self.sessions() as session:
                mark_write_intent(session)
                kind, namespace, pack_id = candidate.identity
                pack = session.scalar(
                    select(ContentPack).where(
                        ContentPack.kind == kind,
                        ContentPack.namespace == namespace,
                        ContentPack.pack_id == pack_id,
                    )
                )
                if pack is None:
                    pack = ContentPack(
                        id=str(uuid4()), kind=kind, namespace=namespace, pack_id=pack_id
                    )
                    session.add(pack)
                    session.flush()
                revisions = session.scalars(
                    select(ContentPackRevision).where(
                        ContentPackRevision.pack_id == pack.id
                    )
                ).all()
                existing = next(
                    (
                        r
                        for r in revisions
                        if r.content_digest == candidate.content_digest
                    ),
                    None,
                )
                if existing:
                    pack.registered_revision_id = existing.id
                    session.commit()
                    return "unchanged"
                revision = ContentPackRevision(
                    id=str(uuid4()),
                    pack_id=pack.id,
                    revision=max((r.revision for r in revisions), default=0) + 1,
                    manifest_digest=candidate.manifest_digest,
                    content_digest=candidate.content_digest,
                    manifest=candidate.manifest,
                )
                session.add(revision)
                session.add_all(asset for _, _, asset in assets)
                session.flush()
                pack.registered_revision_id = revision.id
                session.add_all(
                    ContentPackFile(
                        revision_id=revision.id,
                        relative_path=name,
                        digest=file_digest,
                        media_asset_id=asset.id,
                    )
                    for name, file_digest, asset in assets
                )
                session.commit()
                # No application pointer/CPU/selection is changed, including first registration.
                owned.clear()
            return "accepted"
        finally:
            for path in owned:
                path.unlink(missing_ok=True)

    def scan(self) -> dict:
        with self.lock:
            candidates = self._discover()
            for candidate in candidates:
                self._inspect(candidate)
            claims = defaultdict(list)
            for candidate in candidates:
                if candidate.identity:
                    claims[candidate.identity].append(candidate)
            result = {"accepted": [], "unchanged": [], "conflicts": [], "issues": []}
            for group in claims.values():
                if len(group) > 1:
                    for candidate in group:
                        candidate.status, candidate.issues = (
                            "conflict",
                            ["duplicate_identity"],
                        )
            for candidate in candidates:
                if candidate.status == "conflict":
                    result["conflicts"].append(candidate.entry())
                elif not candidate.issues:
                    try:
                        outcome = self._register(candidate)
                        result[outcome].append(list(candidate.identity))
                    except ScanIssue as error:
                        candidate.status, candidate.issues = "unresolved", [error.code]
                    except Exception:
                        # Filesystem/metadata failure must never prevent engine/game startup.
                        candidate.status, candidate.issues = (
                            "unresolved",
                            ["registration_failed"],
                        )
                if candidate.issues and candidate.status != "conflict":
                    result["issues"].append(candidate.entry())
            try:
                with self.sessions() as session:
                    mark_write_intent(session)
                    session.execute(delete(ContentPackScanEntry))
                    session.add_all(
                        ContentPackScanEntry(**c.entry()) for c in candidates
                    )
                    session.commit()
            except Exception:
                result["issues"].append(
                    {"status": "unresolved", "issues": ["scan_diagnostics_failed"]}
                )
            return {"schema_version": 1, **result}

    def listing(self, kind: str | None = None) -> dict:
        with self.sessions() as session:
            packs = session.scalars(
                select(ContentPack).order_by(
                    ContentPack.kind, ContentPack.namespace, ContentPack.pack_id
                )
            ).all()
            entries = session.scalars(
                select(ContentPackScanEntry).order_by(ContentPackScanEntry.source)
            ).all()
            known_voices = {
                (p.namespace, p.pack_id) for p in packs if p.kind == "voice"
            }
            payload = []
            for pack in packs:
                if kind and pack.kind != kind:
                    continue
                identity = [pack.kind, pack.namespace, pack.pack_id]
                revisions = session.scalars(
                    select(ContentPackRevision)
                    .where(ContentPackRevision.pack_id == pack.id)
                    .order_by(ContentPackRevision.revision)
                ).all()
                issues = []
                status = "normal"
                matching = [e for e in entries if e.identity == identity]
                if not matching:
                    issues.append("source_missing")
                if any(e.status == "conflict" for e in matching):
                    status = "conflict"
                for entry in matching:
                    issues.extend(entry.issues)
                latest = next(
                    (r for r in revisions if r.id == pack.registered_revision_id), None
                )
                if latest:
                    if latest.manifest.get("shared_dependencies"):
                        issues.append("shared_dependencies_unresolved")
                    voice = latest.manifest.get("default_voice_pack")
                    if (
                        voice
                        and (voice["character_id"], voice["id"]) not in known_voices
                    ):
                        issues.append("default_voice_pack_unresolved")
                revision_payloads = []
                for revision in revisions:
                    files = []
                    for ref in session.scalars(
                        select(ContentPackFile)
                        .where(ContentPackFile.revision_id == revision.id)
                        .order_by(ContentPackFile.relative_path)
                    ):
                        asset = session.get(LocalMediaAsset, ref.media_asset_id)
                        files.append(
                            {
                                "relative_path": ref.relative_path,
                                "digest": ref.digest,
                                "media_id": ref.media_asset_id,
                                "url": media_url(ref.media_asset_id),
                            }
                        )
                        if asset is None:
                            issues.append("stored_media_metadata_missing")
                    revision_payloads.append(
                        {
                            "id": revision.id,
                            "revision": revision.revision,
                            "manifest_digest": revision.manifest_digest,
                            "content_digest": revision.content_digest,
                            "manifest": revision.manifest,
                            "files": files,
                        }
                    )
                # A missing source alone does not invalidate preserved registration/copies.
                if status != "conflict" and any(
                    issue != "source_missing" for issue in issues
                ):
                    status = "unresolved"
                payload.append(
                    {
                        "id": pack.id,
                        "identity": identity,
                        "kind": pack.kind,
                        "namespace": pack.namespace,
                        "pack_id": pack.pack_id,
                        "status": status,
                        "issues": sorted(set(issues)),
                        "registered_revision": next(
                            (
                                r
                                for r in revision_payloads
                                if r["id"] == pack.registered_revision_id
                            ),
                            None,
                        ),
                        "applied_revision_id": pack.current_revision_id,
                        "revisions": revision_payloads,
                    }
                )
            return {
                "schema_version": 1,
                "packs": payload,
                "scan_entries": [
                    {
                        "source": e.source,
                        "identity": e.identity,
                        "status": e.status,
                        "issues": e.issues,
                    }
                    for e in entries
                    if not kind
                    or (e.identity and e.identity[0] == kind)
                    or e.source.split("/")[0]
                    == {"character": "characters", "voice": "voices"}.get(kind, kind)
                ],
            }
