import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.local_runtime import create_local_runtime
from app.services.audio_packs import resolve_audio_pack_slot, resolve_voice_slot


def audio(kind, pack_id, slots, namespace=None):
    value = {"schema_version": 1, "kind": kind, "id": pack_id, "version": "1", "label": pack_id, "slots": slots}
    if kind == "voice": value["character_id"] = namespace
    return value


def character(default_voice=None):
    pair = {"positive": "", "negative": ""}
    value = {
        "schema_version": 1, "kind": "character", "id": "actor-one", "character_id": "actor-one",
        "version": "1", "label": "actor", "metadata": {"name": "actor", "adult": True},
        "prompts": {key: dict(pair) for key in ("appearance", "upper_underwear", "lower_underwear")},
        "levels": {str(level): {"images": {"profile": None, "full_body": None, "cg": None},
                               "framing": {kind: dict(pair) for kind in ("profile", "full_body", "cg")}}
                   for level in range(4)},
        "shared_dependencies": [], "default_voice_pack": default_voice,
    }
    return value


class AudioPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nrnf-audio-packs-")
        self.root = Path(self.tmp.name) / "data"
        self.runtime = create_local_runtime(self.root)
        self.client = TestClient(self.runtime.app)
        self.headers = {"X-Local-Capability": self.runtime.capability}

    def tearDown(self):
        self.client.close(); self.runtime.close(); self.tmp.cleanup()

    def install(self, manifest, files=None):
        kind = manifest["kind"]
        source = f"voices/{manifest['character_id']}/{manifest['id']}" if kind == "voice" else f"{'characters' if kind == 'character' else kind}/{manifest['id']}"
        folder = self.root / "packs" / source
        folder.mkdir(parents=True, exist_ok=True)
        for name, data in (files or {}).items():
            (folder / name).write_bytes(data)
        (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return folder

    def scan(self):
        result = self.client.post("/api/local/packs/rescan", headers=self.headers)
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()["registry"]["packs"]

    def restart(self):
        self.client.close(); self.runtime.close()
        self.runtime = create_local_runtime(self.root)
        self.client = TestClient(self.runtime.app)
        self.headers = {"X-Local-Capability": self.runtime.capability}

    def by_id(self, packs, pack_id):
        return next(pack for pack in packs if pack["pack_id"] == pack_id)

    def test_audio_fallback_and_q_audio_switch_preserve_legacy(self):
        self.install(audio("sfx", "default", {"tile_discard": "base.mp3"}), {"base.mp3": b"ID3base audio"})
        self.install(audio("sfx", "selected", {"tile_shuffle": "shuffle.mp3"}), {"shuffle.mp3": b"ID3selected audio"})
        packs = self.scan()
        default, selected = self.by_id(packs, "default"), self.by_id(packs, "selected")
        old = self.client.get("/api/local/sound-selection", headers=self.headers).json()
        self.assertEqual(old["audio_packs"]["sfx_mode"], "legacy")
        changed = self.client.put("/api/local/audio-pack-selection", headers=self.headers, json={
            "expected_revision": 0, "sfx_mode": "pack", "sfx_pack_id": selected["id"],
            "bgm_mode": "legacy", "bgm_pack_id": None,
        })
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["sfx_mode"], "pack")
        with self.runtime.session_factory() as session:
            fallback = resolve_audio_pack_slot(session, kind="sfx", slot="tile_discard", media_root=self.runtime.paths.media)
            direct = resolve_audio_pack_slot(session, kind="sfx", slot="tile_shuffle", media_root=self.runtime.paths.media)
        self.assertEqual(fallback["pack_id"], default["id"])
        self.assertEqual(direct["pack_id"], selected["id"])
        after = self.client.get("/api/local/sound-selection", headers=self.headers).json()
        self.assertEqual(after["effect_set_id"], old["effect_set_id"])
        play = self.client.get("/api/local/play", headers=self.headers).json()
        reset = self.client.post("/api/local/play/reset", headers=self.headers, json={"generation": play["generation"], "confirm": True})
        self.assertEqual(reset.status_code, 200, reset.text)
        self.restart()
        self.assertEqual(self.client.get("/api/local/audio-pack-selection", headers=self.headers).json()["sfx_mode"], "pack")
        self.assertEqual(self.client.put("/api/local/audio-pack-selection", headers=self.headers, json={
            "expected_revision": 0, "sfx_mode": "legacy", "sfx_pack_id": None,
            "bgm_mode": "legacy", "bgm_pack_id": None,
        }).status_code, 409)

    def test_voice_default_pack_revision_and_explicit_selected_off_are_preserved(self):
        self.install(audio("voice", "voice-a", {"chi": "chi.mp3", "win": "win.mp3", "defeat_stage_3": "loss.mp3"}, "actor-one"),
                     {"chi.mp3": b"ID3chi", "win.mp3": b"ID3win", "loss.mp3": b"ID3loss"})
        self.install(audio("voice", "voice-b", {"chi": "other.mp3"}, "actor-one"), {"other.mp3": b"ID3other"})
        self.install(audio("voice", "wrong-actor", {"chi": "wrong.mp3"}, "actor-two"), {"wrong.mp3": b"ID3wrong"})
        value = character({"character_id": "actor-one", "id": "voice-a"})
        folder = self.install(value)
        packs = self.scan()
        image_pack = self.by_id(packs, "actor-one")
        voice_a = self.by_id(packs, "voice-a")
        voice_b = self.by_id(packs, "voice-b")
        wrong_actor = self.by_id(packs, "wrong-actor")
        applied = self.client.post("/api/local/characters/1/pack-application", headers=self.headers, json={
            "expected_revision": 0, "pack_id": image_pack["id"], "registered_revision_id": image_pack["registered_revision"]["id"],
        })
        self.assertEqual(applied.status_code, 200, applied.text)
        initial = self.client.get("/api/local/characters/1/voice-selection", headers=self.headers).json()
        self.assertEqual(initial["default_pack_id"], voice_a["id"])
        self.assertEqual({pack["id"] for pack in initial["packs"]}, {voice_a["id"], voice_b["id"], wrong_actor["id"]})
        wrong = self.client.put("/api/local/characters/1/voice-selection", headers=self.headers, json={
            "expected_revision": initial["revision"], "selection_mode": "selected", "selected_pack_id": image_pack["id"],
        })
        self.assertEqual(wrong.status_code, 422)
        with self.runtime.session_factory() as session:
            self.assertEqual(resolve_voice_slot(session, 1, "win", self.runtime.paths.media)["pack_id"], voice_a["id"])

        selected = self.client.put("/api/local/characters/1/voice-selection", headers=self.headers, json={
            "expected_revision": initial["revision"], "selection_mode": "selected", "selected_pack_id": voice_b["id"],
        })
        self.assertEqual(selected.status_code, 200, selected.text)
        fixed_path = '/api/local/characters/1/fixed-dialogues'
        content_before = self.client.get('/api/local/characters/1/content', headers=self.headers).json()
        play_before = self.client.get('/api/local/play', headers=self.headers).json()
        difficulty_before = self.client.get('/api/local/difficulty', headers=self.headers).json()
        fixed = self.client.patch(fixed_path, headers=self.headers, json={
            'expected_revision': 0, 'edits': {'win': {'text': 'test'}}})
        self.assertEqual(fixed.status_code, 200, fixed.text)
        self.assertEqual(self.client.get('/api/local/characters/1/voice-selection', headers=self.headers).json(), selected.json())
        self.assertEqual(self.client.get('/api/local/characters/1/content', headers=self.headers).json(), content_before)
        self.assertEqual(self.client.get('/api/local/play', headers=self.headers).json(), play_before)
        self.assertEqual(self.client.get('/api/local/difficulty', headers=self.headers).json(), difficulty_before)
        with self.runtime.session_factory() as session:
            self.assertIsNone(resolve_voice_slot(session, 1, "win", self.runtime.paths.media))
            self.assertEqual(resolve_voice_slot(session, 1, "chi", self.runtime.paths.media)["pack_id"], voice_b["id"])

        value["default_voice_pack"] = {"character_id": "actor-one", "id": "voice-b"}
        folder.joinpath("manifest.json").write_text(json.dumps(value), encoding="utf-8")
        packs = self.scan(); image_pack = self.by_id(packs, "actor-one")
        updated = self.client.post("/api/local/characters/1/pack-application", headers=self.headers, json={
            "expected_revision": 1, "pack_id": image_pack["id"], "registered_revision_id": image_pack["registered_revision"]["id"],
        })
        self.assertEqual(updated.status_code, 200, updated.text)
        refreshed = self.client.get("/api/local/characters/1/voice-selection", headers=self.headers).json()
        self.assertEqual(refreshed["default_pack_id"], voice_b["id"])
        self.assertEqual(refreshed["selection_mode"], "selected")
        self.assertEqual(refreshed["selected_pack_id"], voice_b["id"])

        off = self.client.put("/api/local/characters/1/voice-selection", headers=self.headers, json={
            "expected_revision": refreshed["revision"], "selection_mode": "off", "selected_pack_id": None,
        })
        self.assertEqual(off.status_code, 200, off.text)
        edited = self.client.patch(fixed_path, headers=self.headers, json={
            'expected_revision': 1, 'edits': {'defeat_stage_1': {'text': ''}}})
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(self.client.get('/api/local/characters/1/voice-selection', headers=self.headers).json(), off.json())
        with self.runtime.session_factory() as session:
            self.assertIsNone(resolve_voice_slot(session, 1, "chi", self.runtime.paths.media))
        play = self.client.get("/api/local/play", headers=self.headers).json()
        reset = self.client.post("/api/local/play/reset", headers=self.headers, json={"generation": play["generation"], "confirm": True})
        self.assertEqual(reset.status_code, 200, reset.text)
        self.restart()
        persisted = self.client.get("/api/local/characters/1/voice-selection", headers=self.headers).json()
        self.assertEqual(persisted["selection_mode"], "off")
        self.assertEqual(persisted["default_pack_id"], voice_b["id"])
        self.assertEqual(self.client.get(fixed_path, headers=self.headers).json(), edited.json())

    def test_audio_selection_competing_writers_use_revision_gate(self):
        base = self.client.get("/api/local/audio-pack-selection", headers=self.headers).json()
        barrier = Barrier(2)
        def save(mode):
            with TestClient(self.runtime.app) as client:
                barrier.wait(timeout=10)
                return client.put("/api/local/audio-pack-selection", headers=self.headers, json={
                    "expected_revision": base["revision"], "sfx_mode": mode, "sfx_pack_id": None,
                    "bgm_mode": "legacy", "bgm_pack_id": None,
                }).status_code
        with ThreadPoolExecutor(2) as pool:
            statuses = list(pool.map(save, ("legacy", "pack")))
        self.assertEqual(sorted(statuses), [200, 409])

        from app.db.models import CpuCharacter
        with self.runtime.session_factory() as session:
            namespace = session.get(CpuCharacter, 1).slug
        self.install(audio("voice", "cpu-default", {"chi": "chi.mp3"}, namespace), {"chi.mp3": b"ID3voice"})
        self.scan()
        voice = self.client.get("/api/local/characters/1/voice-selection", headers=self.headers).json()
        pack_id = voice["packs"][0]["id"]
        voice_barrier = Barrier(2)
        def save_voice(mode):
            with TestClient(self.runtime.app) as client:
                voice_barrier.wait(timeout=10)
                return client.put("/api/local/characters/1/voice-selection", headers=self.headers, json={
                    "expected_revision": voice["revision"], "selection_mode": mode,
                    "selected_pack_id": pack_id if mode == "selected" else None,
                }).status_code
        with ThreadPoolExecutor(2) as pool:
            voice_statuses = list(pool.map(save_voice, ("selected", "off")))
        self.assertEqual(sorted(voice_statuses), [200, 409])

    def test_voice_namespace_is_distribution_identity_not_cpu_restriction(self):
        for namespace in ('actor-one', 'voice-library'):
            self.install(audio('voice', 'shared', {'chi': 'chi.mp3'}, namespace),
                         {'chi.mp3': b'ID3' + namespace.encode()})
        self.install(character({'character_id': 'voice-library', 'id': 'shared'}))
        packs = self.scan()
        image = self.by_id(packs, 'actor-one')
        voices = {p['namespace']: p for p in packs if p['kind'] == 'voice'}
        applied = self.client.post('/api/local/characters/1/pack-application', headers=self.headers, json={
            'expected_revision': 0, 'pack_id': image['id'],
            'registered_revision_id': image['registered_revision']['id'],
        })
        self.assertEqual(applied.status_code, 200, applied.text)
        state = self.client.get('/api/local/characters/1/voice-selection', headers=self.headers).json()
        self.assertEqual(state['default_pack_id'], voices['voice-library']['id'])
        self.assertEqual({p['id'] for p in state['packs']}, {p['id'] for p in voices.values()})
        with self.runtime.session_factory() as session:
            self.assertEqual(resolve_voice_slot(session, 1, 'chi', self.runtime.paths.media)['pack_id'],
                             voices['voice-library']['id'])
        # A CPU without an image-pack link may explicitly choose any registered voice namespace.
        selected = self.client.put('/api/local/characters/2/voice-selection', headers=self.headers, json={
            'expected_revision': 0, 'selection_mode': 'selected',
            'selected_pack_id': voices['voice-library']['id'],
        })
        self.assertEqual(selected.status_code, 200, selected.text)
        with self.runtime.session_factory() as session:
            self.assertEqual(resolve_voice_slot(session, 2, 'chi', self.runtime.paths.media)['pack_id'],
                             voices['voice-library']['id'])

    def test_audio_and_voice_commit_failure_preserve_saved_selection(self):
        cases = [
            ('/api/local/audio-pack-selection', {'expected_revision': 0, 'sfx_mode': 'pack',
              'sfx_pack_id': None, 'bgm_mode': 'pack', 'bgm_pack_id': None}),
            ('/api/local/characters/1/voice-selection', {'expected_revision': 0,
              'selection_mode': 'off', 'selected_pack_id': None}),
        ]
        for path, body in cases:
            with self.subTest(path=path):
                before = self.client.get(path, headers=self.headers).json()
                with TestClient(self.runtime.app, raise_server_exceptions=False) as failing:
                    with patch.object(Session, 'commit', side_effect=SQLAlchemyError('injected')):
                        response = failing.put(path, headers=self.headers, json=body)
                self.assertEqual(response.status_code, 500)
                self.assertEqual(self.client.get(path, headers=self.headers).json(), before)
        self.restart()
        self.assertEqual(self.client.get(cases[0][0], headers=self.headers).json()['revision'], 0)
        self.assertEqual(self.client.get(cases[1][0], headers=self.headers).json()['revision'], 0)
