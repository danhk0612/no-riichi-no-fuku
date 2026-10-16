"""Signature fixtures verify the system, not actual media output."""

import copy
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.db.models import ContentPack, ContentPackRevision
from app.local_runtime import create_local_runtime
from app.schemas.local_content import PackManifest, relative_file
from app.services.content_packs import ContentPackRegistry, canonical, digest


def audio(kind="sfx", name="test-pack", namespace="test-character"):
    result = dict(
        schema_version=1, kind=kind, id=name, version="1", label="검증", slots={}
    )
    if kind == "voice":
        result["character_id"] = namespace
    return result


def character():
    pair = dict(positive="", negative="")
    return dict(
        schema_version=1,
        kind="character",
        id="test-character",
        character_id="test-character",
        version="1",
        label="검증",
        metadata=dict(name="검증", adult=True),
        prompts={
            k: dict(pair) for k in ("appearance", "upper_underwear", "lower_underwear")
        },
        levels={
            str(n): dict(
                images=dict(profile=None, full_body=None, cg=None),
                framing={k: dict(pair) for k in ("profile", "full_body", "cg")},
            )
            for n in range(4)
        },
        shared_dependencies=[],
        default_voice_pack=None,
    )


class PackRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nrnf-w08-")
        self.root = Path(self.tmp.name) / "한글 공백 자료"
        self.runtime = create_local_runtime(self.root)
        self.open_client()

    def open_client(self):
        self.client = TestClient(self.runtime.app)
        self.headers = {"X-Local-Capability": self.runtime.capability}

    def tearDown(self):
        self.client.close()
        self.runtime.close()
        self.tmp.cleanup()

    def install(self, value, files=None, source=None):
        kind, name = value["kind"], value["id"]
        source = source or (
            f"voices/{value['character_id']}/{name}"
            if kind == "voice"
            else f"{'characters' if kind == 'character' else kind}/{name}"
        )
        folder = self.root / "packs" / source
        folder.mkdir(parents=True, exist_ok=True)
        for name, data in (files or {}).items():
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (folder / "manifest.json").write_text(
            json.dumps(value, ensure_ascii=False), encoding="utf-8"
        )
        return folder

    def scan(self):
        response = self.client.post("/api/local/packs/rescan", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def listing(self):
        return self.client.get("/api/local/packs", headers=self.headers).json()

    def restart(self):
        self.client.close()
        self.runtime.close()
        self.runtime = create_local_runtime(self.root)
        self.open_client()

    def test_character_structure_and_original_snapshot(self):
        value = character()
        value["prompts"]["upper_underwear"]["negative"] = "test-only"
        value["levels"]["2"]["framing"]["cg"]["positive"] = "test-only"
        value["levels"]["0"]["images"]["profile"] = "자료/프로필 사진.png"
        data = b"\x89PNG\r\n\x1a\nsystem-fixture"
        self.install(value, {"자료/프로필 사진.png": data})
        result = self.scan()
        self.assertEqual(len(result["accepted"]), 1)
        pack = result["registry"]["packs"][0]
        self.assertIsNone(pack["applied_revision_id"])
        self.assertEqual(pack["registered_revision"]["manifest"], value)
        ref = pack["registered_revision"]["files"][0]
        self.assertEqual(
            self.client.get(ref["url"], headers=self.headers).content, data
        )
        for change in ("pair", "level", "image", "framing", "adult"):
            bad = copy.deepcopy(value)
            if change == "pair":
                del bad["prompts"]["lower_underwear"]
            if change == "level":
                del bad["levels"]["3"]
            if change == "image":
                del bad["levels"]["0"]["images"]["cg"]
            if change == "framing":
                del bad["levels"]["0"]["framing"]["cg"]["negative"]
            if change == "adult":
                bad["metadata"]["adult"] = False
            with self.subTest(change=change), self.assertRaises(ValidationError):
                PackManifest.model_validate(bad)

    def test_four_kinds_namespace_and_authentication(self):
        for kind in ("sfx", "bgm", "voice"):
            self.install(audio(kind, "same"))
        self.install(character())
        self.install(audio("voice", "same", "other-character"))
        self.assertEqual(len(self.scan()["accepted"]), 5)
        # GET lists registered metadata only; it never examines the source/media filesystem.
        with patch(
            "app.services.content_packs.media_path",
            side_effect=AssertionError("GET touched files"),
        ):
            self.assertEqual(len(self.listing()["packs"]), 5)
        self.assertEqual(
            len(
                self.client.get(
                    "/api/local/packs?kind=voice", headers=self.headers
                ).json()["packs"]
            ),
            2,
        )
        self.assertEqual(self.client.get("/api/local/packs").status_code, 401)
        self.assertEqual(self.client.post("/api/local/packs/rescan").status_code, 401)
        self.assertEqual(
            self.client.get(
                "/api/local/packs?kind=invalid", headers=self.headers
            ).status_code,
            422,
        )
        for name in ("UPPER", "../escape", "two_words", "a" * 81, "한글", "-bad"):
            with self.subTest(name=name), self.assertRaises(ValidationError):
                PackManifest.model_validate(audio(name=name))
        value = character()
        value["character_id"] = "other"
        with self.assertRaises(ValidationError):
            PackManifest.model_validate(value)
        for kind in ("sfx", "bgm", "voice"):
            value = audio(kind)
            value["slots"] = {"invented": "x.mp3"}
            with self.assertRaises(ValidationError):
                PackManifest.model_validate(value)

    def test_bytes_revision_canonical_noop_revert_and_history(self):
        value = audio()
        value["slots"] = {"tile_discard": "효과 음.mp3"}
        folder = self.install(value, {"효과 음.mp3": b"ID3first-fixture"})
        first = self.scan()["registry"]["packs"][0]["registered_revision"]
        self.assertEqual(first["manifest_digest"], digest(canonical(value)))
        (folder / "manifest.json").write_text(
            json.dumps(value, indent=4), encoding="utf-8"
        )
        self.assertEqual(len(self.scan()["unchanged"]), 1)
        (folder / "효과 음.mp3").write_bytes(b"ID3second-fixture")
        second = self.scan()["registry"]["packs"][0]["registered_revision"]
        self.assertEqual(second["revision"], 2)
        self.assertEqual(first["manifest_digest"], second["manifest_digest"])
        self.assertNotEqual(first["content_digest"], second["content_digest"])
        self.assertEqual(
            self.client.get(first["files"][0]["url"], headers=self.headers).content,
            b"ID3first-fixture",
        )
        (folder / "효과 음.mp3").write_bytes(b"ID3first-fixture")
        real_commit = Session.commit

        def fail_recognition(session):
            if any(
                isinstance(row, ContentPack) for row in session.identity_map.values()
            ):
                raise SQLAlchemyError("injected recognition pointer commit failure")
            return real_commit(session)

        with patch.object(Session, "commit", new=fail_recognition):
            self.assertTrue(self.scan()["issues"])
        self.assertEqual(
            self.listing()["packs"][0]["registered_revision"]["id"], second["id"]
        )
        self.assertEqual(len(self.scan()["unchanged"]), 1)
        self.assertEqual(len(self.listing()["packs"][0]["revisions"]), 2)
        self.assertEqual(
            self.listing()["packs"][0]["registered_revision"]["id"], first["id"]
        )
        self.assertIsNone(self.listing()["packs"][0]["applied_revision_id"])
        self.restart()
        self.assertEqual(
            self.listing()["packs"][0]["registered_revision"]["id"], first["id"]
        )
        self.assertEqual(len(list((self.runtime.paths.media / "packs").iterdir())), 2)

    def test_invalid_or_missing_source_preserves_existing_revision(self):
        value = audio()
        value["slots"] = {"tile_discard": "clip.wav"}
        folder = self.install(value, {"clip.wav": b"RIFFxxxxWAVEfixture"})
        before = self.scan()["registry"]["packs"][0]["registered_revision"]
        for mutation in ("missing", "signature", "version", "json", "identity"):
            self.install(value, {"clip.wav": b"RIFFxxxxWAVEfixture"})
            if mutation == "missing":
                (folder / "clip.wav").unlink()
            if mutation == "signature":
                (folder / "clip.wav").write_bytes(b"bad")
            if mutation == "version":
                self.install(dict(value, schema_version=2))
            if mutation == "json":
                (folder / "manifest.json").write_text("{")
            if mutation == "identity":
                self.install(dict(value, id="different"))
            result = self.scan()
            self.assertEqual(result["accepted"], [])
            self.assertTrue(result["issues"])
            self.assertEqual(
                result["registry"]["packs"][0]["registered_revision"], before
            )
        shutil.rmtree(folder)
        pack = self.scan()["registry"]["packs"][0]
        self.assertEqual(pack["status"], "normal")
        self.assertEqual(pack["issues"], ["source_missing"])
        self.assertEqual(
            self.client.get(
                before["files"][0]["url"], headers=self.headers
            ).status_code,
            200,
        )

    def test_duplicate_claims_block_both(self):
        value = audio()
        self.install(value)
        before = self.scan()["registry"]["packs"][0]["registered_revision"]
        self.install(dict(value, label="other"), source="sfx/duplicate")
        result = self.scan()
        self.assertEqual(len(result["conflicts"]), 2)
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["registry"]["packs"][0]["status"], "conflict")
        self.assertEqual(result["registry"]["packs"][0]["registered_revision"], before)
        shutil.rmtree(self.root / "packs/sfx/duplicate")
        self.assertEqual(self.scan()["registry"]["packs"][0]["status"], "normal")

    def test_path_validation_and_links(self):
        for name in (
            "../escape.mp3",
            "/tmp/x.mp3",
            "C:/x.mp3",
            "//server/share/x",
            "a\\b.mp3",
            "https://x/y",
            "x.mp3:stream",
            "CON.mp3",
            "x./y.mp3",
            "./x.mp3",
            "a//b.mp3",
            "a/../b.mp3",
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                relative_file(name)
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (outside / "clip.mp3").write_bytes(b"ID3outside")
        value = audio()
        value["slots"] = {"tile_discard": "linked/clip.mp3"}
        folder = self.install(value)

        def link(path):
            try:
                path.symlink_to(outside, target_is_directory=True)
            except OSError:
                if os.name != "nt":
                    raise
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(path), str(outside)],
                    check=True,
                    capture_output=True,
                )

        link(folder / "linked")
        result = self.scan()
        self.assertEqual(result["accepted"], [])
        self.assertIn("unsafe_path", result["issues"][0]["issues"])
        self.assertEqual((outside / "clip.mp3").read_bytes(), b"ID3outside")
        shutil.rmtree(self.root / "packs/sfx")
        link(self.root / "packs/sfx")
        self.assertTrue(self.scan()["issues"])

    def test_mutating_file_between_reads_is_incomplete_copy(self):
        value = audio()
        value["slots"] = {"tile_discard": "clip.mp3"}
        self.install(value, {"clip.mp3": b"ID3fixture"})
        original = ContentPackRegistry._verify_source

        def change(registry, folder, raw, stamp, files):
            (folder / "clip.mp3").write_bytes(b"ID3changed")
            return original(registry, folder, raw, stamp, files)

        with patch.object(ContentPackRegistry, "_verify_source", new=change):
            result = self.scan()
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["issues"][0]["issues"], ["incomplete_copy"])
        self.assertEqual(self.listing()["packs"], [])

    def test_commit_failure_removes_only_owned_files(self):
        value = audio()
        value["slots"] = {"tile_discard": "clip.mp3"}
        folder = self.install(value, {"clip.mp3": b"ID3original"})
        before = self.scan()["registry"]["packs"][0]["registered_revision"]
        originals = {
            p: p.read_bytes() for p in (self.runtime.paths.media / "packs").iterdir()
        }
        (folder / "clip.mp3").write_bytes(b"ID3changed")
        real_commit = Session.commit

        def fail(session):
            if any(
                isinstance(row, ContentPackRevision)
                for row in (*session.new, *session.identity_map.values())
            ):
                raise SQLAlchemyError("injected")
            return real_commit(session)

        with patch.object(Session, "commit", new=fail):
            result = self.scan()
        self.assertEqual(result["issues"][0]["issues"], ["registration_failed"])
        self.assertEqual(self.listing()["packs"][0]["registered_revision"], before)
        self.assertEqual(
            {p: p.read_bytes() for p in (self.runtime.paths.media / "packs").iterdir()},
            originals,
        )
        self.assertEqual(len(self.scan()["accepted"]), 1)

    def test_dependencies_stored_unresolved_and_not_applied(self):
        value = character()
        value["shared_dependencies"] = [
            dict(namespace="pose", id="missing", revision_digest="a" * 64)
        ]
        value["default_voice_pack"] = dict(
            character_id="other-character", id="voice-pack"
        )
        self.install(value)
        pack = self.scan()["registry"]["packs"][0]
        self.assertEqual(pack["status"], "unresolved")
        self.assertIn("default_voice_pack_unresolved", pack["issues"])
        self.install(audio("voice", "voice-pack", "other-character"))
        pack = next(
            p for p in self.scan()["registry"]["packs"] if p["kind"] == "character"
        )
        self.assertNotIn("default_voice_pack_unresolved", pack["issues"])
        self.assertIn("shared_dependencies_unresolved", pack["issues"])
        self.assertIsNone(pack["applied_revision_id"])

    def test_startup_repeat_migration_restart_reset_preserve_files_get_is_readonly(
        self,
    ):
        value = audio("bgm")
        value["slots"] = {"game": "곡.ogg"}
        folder = self.install(value, {"곡.ogg": b"OggSfixture"})
        self.assertEqual(self.listing()["packs"], [])
        self.restart()
        before = self.listing()["packs"]
        self.assertEqual(len(before), 1)
        self.restart()
        self.assertEqual(self.listing()["packs"], before)
        state = self.client.get("/api/local/play", headers=self.headers).json()
        reset = self.client.post(
            "/api/local/play/reset",
            headers=self.headers,
            json=dict(generation=state["generation"], confirm=True),
        )
        self.assertEqual(reset.status_code, 200, reset.text)
        self.assertEqual(self.listing()["packs"], before)
        shutil.rmtree(folder)
        self.restart()
        self.assertEqual(
            self.listing()["packs"][0]["revisions"], before[0]["revisions"]
        )
        with self.runtime.engine.connect() as conn:
            self.assertEqual(conn.execute(text("PRAGMA foreign_key_check")).all(), [])
            self.assertEqual(
                conn.execute(text("select version_num from alembic_version")).scalar(),
                "20261016_0007",
            )

    def test_concurrent_scan_no_duplicates_and_reads_outside_writer(self):
        value = audio()
        value["slots"] = {"tile_discard": "clip.mp3"}
        self.install(value, {"clip.mp3": b"ID3fixture"})
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(
                pool.map(lambda _: self.runtime.content_packs.scan(), range(3))
            )
        self.assertEqual(sum(len(r["accepted"]) for r in results), 1)
        self.assertEqual(sum(len(r["unchanged"]) for r in results), 2)
        with self.runtime.session_factory() as session:
            self.assertEqual(len(session.scalars(select(ContentPackRevision)).all()), 1)
        original = ContentPackRegistry._verify_source

        def inspect(registry, *args):
            with registry.sessions() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                session.rollback()
            return original(registry, *args)

        with patch.object(ContentPackRegistry, "_verify_source", new=inspect):
            self.assertEqual(len(self.scan()["unchanged"]), 1)

    def test_upgrade_from_w06_preserves_settings_data_and_file_bytes(self):
        from alembic import command
        from alembic.config import Config

        clip = self.client.post(
            "/api/local/media",
            headers=self.headers,
            data={"kind": "audio"},
            files={"file": ("old.mp3", b"ID3legacy-fixture", "audio/mpeg")},
        ).json()
        effect = self.client.post(
            "/api/local/sound-effect-sets",
            headers=self.headers,
            json=dict(label="기존", active=True, clips={"ron": clip["id"]}),
        ).json()
        saved = self.client.put(
            "/api/local/sound-selection",
            headers=self.headers,
            json=dict(effect_set_id=effect["id"], bgm_ids=[]),
        ).json()
        # Remove only empty W08 tables from this owned test DB to reproduce the W06 schema.
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.set_main_option(
            "script_location", str(Path(__file__).resolve().parents[1] / "alembic")
        )
        with self.runtime.engine.connect() as conn:
            config.attributes["connection"] = conn
            command.downgrade(config, "20261016_0006")
        snapshots = {}
        with self.runtime.engine.connect() as conn:
            for table in (
                "users",
                "cpu_characters",
                "cpu_dialogues",
                "cpu_result_assets",
                "user_cpu_progress",
                "game_settings",
                "local_media_assets",
                "sound_effect_sets",
                "local_play_states",
            ):
                snapshots[table] = conn.exec_driver_sql(f"SELECT * FROM {table}").all()
        self.restart()
        self.restart()
        with self.runtime.engine.connect() as conn:
            for table, rows in snapshots.items():
                self.assertEqual(
                    conn.exec_driver_sql(f"SELECT * FROM {table}").all(), rows, table
                )
        self.assertEqual(
            self.client.get("/api/local/sound-selection", headers=self.headers).json(),
            saved,
        )
        self.assertEqual(
            self.client.get(clip["url"], headers=self.headers).content,
            b"ID3legacy-fixture",
        )

    def test_malformed_json_types_missing_manifest_and_size_limits(self):
        folder = self.install(audio())
        for raw in (
            '{"kind":[],"schema_version":1}',
            '{"schema_version":1,"schema_version":2}',
            "[]",
            '{"x":NaN}',
        ):
            (folder / "manifest.json").write_text(raw)
            self.assertTrue(self.scan()["issues"])
        (folder / "manifest.json").unlink()
        self.assertTrue(self.scan()["issues"])
        value = audio()
        value["slots"] = {"tile_discard": "clip.mp3"}
        self.install(value, {"clip.mp3": b"ID3fixture"})
        with patch("app.services.content_packs.MAX_AUDIO_BYTES", 8):
            result = self.scan()
        self.assertEqual(result["accepted"], [])
        self.assertIn("file_too_large", result["issues"][0]["issues"])
        self.assertEqual(self.listing()["packs"], [])

    def test_file_copy_failure_preserves_previous_registration(self):
        value = audio()
        value["slots"] = {"tile_discard": "clip.mp3"}
        folder = self.install(value, {"clip.mp3": b"ID3original"})
        before = self.scan()["registry"]["packs"][0]["registered_revision"]
        (folder / "clip.mp3").write_bytes(b"ID3changed")
        original = Path.open

        def fail(path, *args, **kwargs):
            if args and args[0] == "xb":
                raise OSError("injected write failure")
            return original(path, *args, **kwargs)

        with patch.object(Path, "open", new=fail):
            result = self.scan()
        self.assertEqual(result["accepted"], [])
        self.assertEqual(self.listing()["packs"][0]["registered_revision"], before)
        self.assertEqual(
            self.client.get(before["files"][0]["url"], headers=self.headers).content,
            b"ID3original",
        )
