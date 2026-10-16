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
from app.db.models import CharacterContent, CharacterLevelFraming, ContentPack, ContentPackRevision
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

    def test_windows_reserved_pack_and_voice_namespace_ids(self):
        reserved = ["con", "prn", "aux", "nul"] + [
            f"{prefix}{number}"
            for prefix in ("com", "lpt")
            for number in range(1, 10)
        ]
        for name in reserved:
            for kind in ("character", "sfx", "bgm", "voice"):
                value = character() if kind == "character" else audio(kind)
                value["id"] = name
                if kind == "character":
                    value["character_id"] = name
                with self.subTest(name=name, kind=kind), self.assertRaises(ValidationError):
                    PackManifest.model_validate(value)
            with self.subTest(namespace=name), self.assertRaises(ValidationError):
                PackManifest.model_validate(audio("voice", namespace=name))
        for name in ("console", "aux-pack", "com10", "lpt10"):
            self.assertEqual(PackManifest.model_validate(audio(name=name)).id, name)

    def test_character_editor_reads_without_writes_and_tracks_fields_independently(self):
        cpu_list = self.client.get("/api/admin/cpus", headers=self.headers)
        self.assertEqual(cpu_list.status_code, 200, cpu_list.text)
        self.assertTrue(any(cpu["id"] == 1 for cpu in cpu_list.json()))
        before = self.client.get("/api/local/characters/1/content", headers=self.headers)
        self.assertEqual(before.status_code, 200, before.text)
        original = before.json()
        self.assertEqual(original["revision"], 0)
        self.assertEqual(original["prompts"]["appearance"], {
            "positive": "", "negative": "", "overrides": {"positive": False, "negative": False}
        })
        self.assertEqual(len(original["levels"]), 4)
        self.assertEqual(set(original["levels"]["0"]), {"profile", "full_body", "cg"})
        with self.runtime.session_factory() as session:
            self.assertEqual(session.query(CharacterContent).count(), 0)
            self.assertEqual(session.query(CharacterLevelFraming).count(), 0)
        response = self.client.patch(
            "/api/local/characters/1/content", headers=self.headers,
            json={"expected_revision": 0, "prompts": {"appearance": {"positive": ""}}},
        )
        self.assertEqual(response.status_code, 200, response.text)
        saved = response.json()
        self.assertEqual(saved["revision"], 1)
        self.assertTrue(saved["prompts"]["appearance"]["overrides"]["positive"])
        self.assertFalse(saved["prompts"]["appearance"]["overrides"]["negative"])
        response = self.client.patch(
            "/api/local/characters/1/content", headers=self.headers,
            json={"expected_revision": 1, "prompts": {"appearance": {"negative": "avoid test"}},
                  "framing": [{"level": 2, "kind": "cg", "positive": "frame test"}]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        saved = response.json()
        self.assertEqual(saved["prompts"]["appearance"]["positive"], "")
        self.assertEqual(saved["prompts"]["appearance"]["negative"], "avoid test")
        self.assertTrue(saved["prompts"]["appearance"]["overrides"]["positive"])
        self.assertTrue(saved["prompts"]["appearance"]["overrides"]["negative"])
        self.assertEqual(saved["levels"]["2"]["cg"]["positive"], "frame test")
        self.assertTrue(saved["levels"]["2"]["cg"]["overrides"]["positive"])
        self.assertFalse(saved["levels"]["2"]["cg"]["overrides"]["negative"])

    def test_character_editor_conflict_validation_auth_and_restart(self):
        path = "/api/local/characters/1/content"
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.patch(path, json={"expected_revision": 0, "prompts": {"appearance": {"positive": "x"}}}).status_code, 401)
        saved = self.client.patch(path, headers=self.headers, json={
            "expected_revision": 0, "prompts": {"upper_underwear": {"positive": ""}},
        })
        self.assertEqual(saved.status_code, 200, saved.text)
        conflict = self.client.patch(path, headers=self.headers, json={
            "expected_revision": 0, "prompts": {"appearance": {"positive": "stale"}},
        })
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["detail"]["code"], "revision_conflict")
        self.assertEqual(self.client.patch(path, headers=self.headers, json={
            "expected_revision": 1, "prompts": {"appearance": {"positive": None}},
        }).status_code, 422)
        self.assertEqual(self.client.patch(path, headers=self.headers, json={
            "expected_revision": 1, "framing": [
                {"level": 0, "kind": "profile", "positive": "a"},
                {"level": 0, "kind": "profile", "negative": "b"},
            ],
        }).status_code, 422)
        play = self.client.get("/api/local/play", headers=self.headers).json()
        reset = self.client.post("/api/local/play/reset", headers=self.headers, json={
            "generation": play["generation"], "confirm": True,
        })
        self.assertEqual(reset.status_code, 200, reset.text)
        self.restart()
        after = self.client.get(path, headers=self.headers).json()
        self.assertEqual(after["prompts"]["upper_underwear"]["positive"], "")
        self.assertTrue(after["prompts"]["upper_underwear"]["overrides"]["positive"])
        self.assertEqual(after["revision"], 1)

    def test_character_editor_commit_failure_keeps_saved_snapshot(self):
        path = "/api/local/characters/1/content"
        first = self.client.patch(path, headers=self.headers, json={
            "expected_revision": 0, "prompts": {"appearance": {"positive": "saved"}},
        })
        self.assertEqual(first.status_code, 200, first.text)
        with TestClient(self.runtime.app, raise_server_exceptions=False) as failing_client:
            with patch.object(Session, "commit", side_effect=SQLAlchemyError("injected commit failure")):
                failed = failing_client.patch(path, headers=self.headers, json={
                    "expected_revision": 1, "prompts": {"appearance": {"negative": "not committed"}},
                })
        self.assertEqual(failed.status_code, 500)
        current = self.client.get(path, headers=self.headers).json()
        self.assertEqual(current["revision"], 1)
        self.assertEqual(current["prompts"]["appearance"]["positive"], "saved")
        self.assertEqual(current["prompts"]["appearance"]["negative"], "")

    def test_pack_rescan_does_not_replace_local_prompt_edits(self):
        path = "/api/local/characters/1/content"
        self.install(character())
        self.assertEqual(self.scan()["accepted"], [["character", "", "test-character"]])
        saved = self.client.patch(path, headers=self.headers, json={
            "expected_revision": 0, "prompts": {"appearance": {"negative": "local test edit"}},
        })
        self.assertEqual(saved.status_code, 200, saved.text)
        self.scan()
        after = self.client.get(path, headers=self.headers).json()
        self.assertEqual(after["prompts"]["appearance"]["negative"], "local test edit")

    def application(self, pack, expected=0, cpu=1):
        return self.client.post(f"/api/local/characters/{cpu}/pack-application", headers=self.headers, json={
            "expected_revision": expected, "pack_id": pack["id"],
            "registered_revision_id": pack["registered_revision"]["id"],
        })

    def content(self, cpu=1):
        return self.client.get(f"/api/local/characters/{cpu}/content", headers=self.headers).json()

    def filled_character(self, label):
        value = character()
        for group, pair in value["prompts"].items():
            pair.update(positive=f"test-{label}-{group}-P", negative=f"test-{label}-{group}-N")
        for level, data in value["levels"].items():
            for kind, pair in data["framing"].items():
                pair.update(positive=f"test-{label}-{level}-{kind}-P", negative=f"test-{label}-{level}-{kind}-N")
        return value

    def test_character_pack_link_update_field_history_and_immutable_media(self):
        with self.runtime.session_factory() as session:
            before = [tuple(row) for row in session.execute(text("SELECT * FROM cpu_characters ORDER BY id"))]
            progress = [tuple(row) for row in session.execute(text("SELECT * FROM user_cpu_progress ORDER BY user_id, cpu_character_id"))]
        value = self.filled_character('a')
        value['levels']['2']['images']['cg'] = 'image.png'
        image_a = b'\x89PNG\r\n\x1a\nfirst-test'
        folder = self.install(value, {'image.png': image_a})
        first = self.scan()['registry']['packs'][0]
        self.assertIsNone(self.content()['pack'])  # registration never connects a CPU
        edit = dict(expected_revision=0, prompts={'appearance': {'positive': ''}, 'upper_underwear': {'negative': value['prompts']['upper_underwear']['negative']}},
                    framing=[{'level': 2, 'kind': 'cg', 'positive': ''}, {'level': 0, 'kind': 'profile', 'negative': value['levels']['0']['framing']['profile']['negative']}])
        self.assertEqual(self.client.patch('/api/local/characters/1/content', headers=self.headers, json=edit).status_code, 200)
        response = self.application(first, expected=1)
        self.assertEqual(response.status_code, 200, response.text)
        applied = response.json()
        self.assertEqual(applied['pack_revision_id'], first['registered_revision']['id'])
        self.assertEqual(applied['prompts']['appearance']['positive'], '')
        original = self.client.get(f"/api/local/characters/1/pack-revisions/{applied['pack_revision_id']}", headers=self.headers).json()
        old_url = original['media']['2']['cg']['url']
        self.assertEqual(self.client.get(old_url, headers=self.headers).content, image_a)
        value_b = self.filled_character('b')
        value_b['levels']['2']['images']['cg'] = 'image.png'
        self.install(value_b, {'image.png': b'\x89PNG\r\n\x1a\nsecond-test'})
        second = self.scan()['registry']['packs'][0]
        self.assertEqual(self.content()['pack_revision_id'], applied['pack_revision_id'])
        self.assertTrue(self.content()['pack']['update_available'])
        self.assertEqual(self.application(first, expected=2).status_code, 409)  # stale registry pointer
        updated = self.application(second, expected=2)
        self.assertEqual(updated.status_code, 200, updated.text)
        updated = updated.json()
        for group, pair in updated['prompts'].items():
            for field in ('positive', 'negative'):
                override = f'{group}.{field}' in ('appearance.positive', 'upper_underwear.negative')
                expected = applied['prompts'][group][field] if override else value_b['prompts'][group][field]
                self.assertEqual(pair[field], expected)
                self.assertEqual(pair['overrides'][field], override)
        for level, kinds in updated['levels'].items():
            for kind, pair in kinds.items():
                for field in ('positive', 'negative'):
                    override = (level, kind, field) in [('2', 'cg', 'positive'), ('0', 'profile', 'negative')]
                    expected = applied['levels'][level][kind][field] if override else value_b['levels'][level]['framing'][kind][field]
                    self.assertEqual(pair[field], expected)
                    self.assertEqual(pair['overrides'][field], override)
        self.assertNotEqual(updated['levels']['2']['cg']['media']['media_id'], original['media']['2']['cg']['media_id'])
        self.assertEqual(self.client.get(f"/api/local/characters/1/pack-revisions/{applied['pack_revision_id']}", headers=self.headers).json(), original)
        self.assertEqual(self.client.get(old_url, headers=self.headers).content, image_a)
        self.assertEqual(json.loads((folder/'manifest.json').read_text()), value_b)
        self.assertIsNone(self.content(2)['pack'])
        # Same registry pack may be explicitly linked independently to a second CPU.
        self.assertEqual(self.application(first, cpu=2).status_code, 409)
        self.assertEqual(self.application(second, cpu=2).status_code, 200)
        with self.runtime.session_factory() as session:
            self.assertEqual(before, [tuple(row) for row in session.execute(text("SELECT * FROM cpu_characters ORDER BY id"))])
            self.assertEqual(progress, [tuple(row) for row in session.execute(text("SELECT * FROM user_cpu_progress ORDER BY user_id, cpu_character_id"))])
            self.assertTrue(all(p.current_revision_id is None for p in session.scalars(select(ContentPack))))
        # A retained response is a display snapshot; reset/startup never rewrites it or current content.
        play = self.client.get('/api/local/play', headers=self.headers).json()
        self.assertEqual(self.client.post('/api/local/play/reset', headers=self.headers, json={'generation': play['generation'], 'confirm': True}).status_code, 200)
        self.restart()
        self.assertEqual(self.content(), updated)
        self.assertEqual(self.client.get(old_url, headers=self.headers).content, image_a)
        self.assertEqual(self.application(second, expected=updated['revision']).json(), updated)  # idempotent

    def test_character_pack_application_failures_preserve_content(self):
        value = self.filled_character('a')
        self.install(value)
        first = self.scan()['registry']['packs'][0]
        self.assertEqual(self.application(first).status_code, 200)
        original = self.content()
        # Different pack IDs / non-character packs cannot replace a link.
        other = character(); other['id'] = other['character_id'] = 'other'
        self.install(other); self.install(audio())
        packs = self.scan()['registry']['packs']
        for pack in packs:
            if pack['id'] != first['id']:
                self.assertIn(self.application(pack, expected=1).status_code, (409, 422))
        self.assertEqual(self.client.get(f"/api/local/characters/1/pack-revisions/{next(p for p in packs if p['pack_id']=='other')['registered_revision']['id']}", headers=self.headers).status_code, 404)
        value['prompts']['appearance']['negative'] = 'test-new'
        folder = self.install(value)
        second = next(p for p in self.scan()['registry']['packs'] if p['id'] == first['id'])
        self.assertEqual(self.application(second, expected=0).status_code, 409)
        with TestClient(self.runtime.app, raise_server_exceptions=False) as failing:
            with patch.object(Session, 'commit', side_effect=SQLAlchemyError('injected')):
                result = failing.post('/api/local/characters/1/pack-application', headers=self.headers, json={'expected_revision': 1, 'pack_id': second['id'], 'registered_revision_id': second['registered_revision']['id']})
        self.assertEqual(result.status_code, 500)
        current = self.content(); original['pack'] = current['pack']
        self.assertEqual(current, original)
        # Incomplete and conflicting live sources block new application and preserve old values.
        (folder/'manifest.json').write_text('{"kind":"character","id":"test-character",')
        self.scan()
        self.assertEqual(self.application(second, expected=1).status_code, 409)
        self.install(value)
        self.install(value, source='characters/duplicate')
        self.scan()
        self.assertEqual(self.application(second, expected=1).status_code, 409)
        self.assertEqual(self.content(), current)
        shutil.rmtree(self.root/'packs'/'characters'/'duplicate')
        shutil.rmtree(folder)  # preserved registration can be applied without its source folder
        self.scan()
        self.assertEqual(self.application(second, expected=1).status_code, 200)

    def test_character_pack_missing_immutable_media_and_dependency_auth(self):
        from app.db.models import ContentPackFile, LocalMediaAsset
        value = character(); value['levels']['0']['images']['profile'] = 'image.png'
        self.install(value, {'image.png': b'\x89PNG\r\n\x1a\ntest'})
        first = self.scan()['registry']['packs'][0]
        path = '/api/local/characters/1/pack-application'
        body = {'expected_revision': 0, 'pack_id': first['id'], 'registered_revision_id': first['registered_revision']['id']}
        self.assertEqual(self.client.post(path, json=body).status_code, 401)
        self.assertEqual(self.client.post(path, headers=self.headers, json={**body, 'expected_revision': None}).status_code, 422)
        self.assertEqual(self.client.post('/api/local/characters/999/pack-application', headers=self.headers, json=body).status_code, 404)
        with self.runtime.session_factory() as session:
            ref = session.scalar(select(ContentPackFile))
            asset = session.get(LocalMediaAsset, ref.media_asset_id)
            stored = self.runtime.paths.media / asset.storage_key
        saved = stored.read_bytes(); stored.write_bytes(b'corrupted-test')
        self.assertEqual(self.application(first).status_code, 409)
        self.assertIsNone(self.content()['pack'])
        stored.write_bytes(saved)
        self.assertEqual(self.application(first).status_code, 200)
        value['shared_dependencies'] = [{'namespace': 'test', 'id': 'test', 'revision_digest': 'a'*64}]
        self.install(value, {'image.png': saved})
        second = self.scan()['registry']['packs'][0]
        self.assertEqual(self.application(second, expected=1).status_code, 409)
        self.assertEqual(self.content()['pack_revision_id'], first['registered_revision']['id'])

    def test_character_pack_edit_apply_and_two_applications_race(self):
        value = self.filled_character('a'); self.install(value)
        first = self.scan()['registry']['packs'][0]
        self.assertEqual(self.application(first).status_code, 200)
        value = self.filled_character('b'); self.install(value)
        second = self.scan()['registry']['packs'][0]
        from threading import Barrier
        barrier = Barrier(2)
        def request(apply):
            with TestClient(self.runtime.app) as client:
                barrier.wait(timeout=10)
                if apply:
                    return client.post('/api/local/characters/1/pack-application', headers=self.headers, json={'expected_revision': 1, 'pack_id': second['id'], 'registered_revision_id': second['registered_revision']['id']})
                return client.patch('/api/local/characters/1/content', headers=self.headers, json={'expected_revision': 1, 'prompts': {'appearance': {'negative': ''}}})
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(request, (True, False)))
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])
        current = self.content()
        if results[1].status_code == 200:
            self.assertTrue(current['prompts']['appearance']['overrides']['negative'])
            self.assertEqual(self.application(second, expected=2).status_code, 200)
            self.assertEqual(self.content()['prompts']['appearance']['negative'], '')
        else:
            self.assertFalse(current['prompts']['appearance']['overrides']['negative'])
        # Two first-link requests cannot overwrite each other.
        barrier = Barrier(2)
        def link(_):
            with TestClient(self.runtime.app) as client:
                barrier.wait(timeout=10)
                return client.post('/api/local/characters/2/pack-application', headers=self.headers, json={'expected_revision': 0, 'pack_id': second['id'], 'registered_revision_id': second['registered_revision']['id']})
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(link, range(2)))
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])

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
                "20261016_0008",
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
