from __future__ import annotations

import tempfile
import unittest
import asyncio
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import BackgroundTrack, GameSessionRecord, LocalMediaAsset, SoundEffectSet, UserCpuProgress
from app.local_runtime import create_local_runtime
from app.services.game_registry import RegisteredGame
from app.services.local_media import LocalMediaError, media_path
from app.api.game import send_registered_game_state


class LocalSoundTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="nrnf-local-sound-")
        self.runtime = create_local_runtime(Path(self.temporary.name) / "data")
        self.client = TestClient(self.runtime.app)
        self.headers = {"X-Local-Capability": self.runtime.capability}

    def tearDown(self) -> None:
        self.client.close()
        self.runtime.close()
        self.temporary.cleanup()

    def upload(self, kind: str, name: str, data: bytes, mime: str):
        return self.client.post("/api/local/media", headers=self.headers, data={"kind": kind}, files={"file": (name, data, mime)})

    def test_upload_korean_filename_stream_range_and_path_guard(self):
        data = b"ID3" + b"\x00" * 32
        response = self.upload("audio", "배경 음악 test.mp3", data, "audio/mpeg")
        self.assertEqual(response.status_code, 201, response.text)
        asset = response.json()
        self.assertEqual(asset["kind"], "audio")
        self.assertEqual(asset["byte_size"], len(data))
        ranged = self.client.get(asset["url"], headers={**self.headers, "Range": "bytes=1-4"})
        self.assertEqual(ranged.status_code, 206)
        self.assertEqual(ranged.content, data[1:5])
        self.assertEqual(ranged.headers["content-range"], f"bytes 1-4/{len(data)}")
        with self.assertRaises(LocalMediaError):
            media_path(self.runtime.paths.media, "../game.db")

    def test_upload_rejects_extension_signature_mismatch_and_size_limit(self):
        mismatch = self.upload("audio", "wrong.wav", b"ID3" + b"x" * 12, "audio/wav")
        self.assertEqual(mismatch.status_code, 400)
        oversized = self.upload("image", "too-big.png", b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024), "image/png")
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(self.client.get("/api/local/media", headers=self.headers).json(), [])

    def test_selection_persists_inactive_refs_and_empty_is_silent(self):
        play = self.client.get("/api/local/play", headers=self.headers).json()
        confirmed = self.client.post("/api/local/play/roster", headers=self.headers, json={
            "generation": play["generation"], "cpu_character_ids": [1, 2, 3],
        })
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        clip = self.upload("audio", "clip.mp3", b"ID3" + b"x" * 16, "audio/mpeg").json()
        track_asset = self.upload("audio", "music.ogg", b"OggS" + b"x" * 16, "audio/ogg").json()
        created_set = self.client.post("/api/local/sound-effect-sets", headers=self.headers, json={
            "label": "기본 효과음", "active": True, "clips": {"ron": clip["id"]},
        })
        self.assertEqual(created_set.status_code, 201, created_set.text)
        track = self.client.post("/api/local/background-tracks", headers=self.headers, json={
            "label": "첫 곡", "active": True, "media_asset_id": track_asset["id"],
        })
        self.assertEqual(track.status_code, 201, track.text)
        saved = self.client.put("/api/local/sound-selection", headers=self.headers, json={
            "effect_set_id": created_set.json()["id"], "bgm_ids": [track.json()["id"]],
        })
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["bgm_ids"], [track.json()["id"]])
        self.assertEqual(self.client.get("/api/local/sound-selection", headers=self.headers).json()["effect_set_id"], created_set.json()["id"])
        self.client.patch(f"/api/local/sound-effect-sets/{created_set.json()['id']}", headers=self.headers, json={
            "label": "기본 효과음", "active": False, "clips": {"ron": clip["id"]},
        })
        unavailable = self.client.get("/api/local/sound-selection", headers=self.headers).json()
        self.assertEqual(unavailable["effect_set_id"], created_set.json()["id"])
        self.assertFalse(unavailable["effect_set_available"])
        self.assertEqual(self.client.put("/api/local/sound-selection", headers=self.headers, json={
            "effect_set_id": created_set.json()["id"], "bgm_ids": [],
        }).status_code, 400)
        silent = self.client.put("/api/local/sound-selection", headers=self.headers, json={
            "effect_set_id": None, "bgm_ids": [],
        })
        self.assertEqual(silent.status_code, 200)
        self.assertEqual(silent.json()["bgm_ids"], [])
        self.client.patch(f"/api/local/sound-effect-sets/{created_set.json()['id']}", headers=self.headers, json={
            "label": "기본 효과음", "active": True, "clips": {"ron": clip["id"]},
        })
        self.client.put("/api/local/sound-selection", headers=self.headers, json={
            "effect_set_id": created_set.json()["id"], "bgm_ids": [track.json()["id"]],
        })
        original_generation = self.client.get("/api/local/play", headers=self.headers).json()["generation"]
        self.assertEqual(original_generation, play["generation"])
        self.client.close()
        data_root = self.runtime.paths.root
        self.runtime.close()
        self.runtime = create_local_runtime(data_root)
        self.client = TestClient(self.runtime.app)
        self.headers = {"X-Local-Capability": self.runtime.capability}
        reopened = self.client.get("/api/local/sound-selection", headers=self.headers).json()
        self.assertEqual(reopened["effect_set_id"], created_set.json()["id"])
        self.assertEqual(reopened["bgm_ids"], [track.json()["id"]])
        reopened_play = self.client.get("/api/local/play", headers=self.headers).json()
        self.assertEqual(reopened_play["generation"], original_generation)
        self.assertEqual(reopened_play["phase"], "progress")
        self.assertEqual([row["cpu_character_id"] for row in reopened_play["roster"]], [1, 2, 3])

    def test_media_metadata_commit_failure_removes_only_new_upload(self):
        existing = self.upload("audio", "existing.mp3", b"ID3" + b"existing", "audio/mpeg")
        self.assertEqual(existing.status_code, 201, existing.text)
        existing_path = self.runtime.paths.media / "w06" / f"{existing.json()['id']}.mp3"
        previous_bytes = existing_path.read_bytes()
        original_commit = Session.commit

        def fail_media_commit(session):
            if any(isinstance(row, LocalMediaAsset) for row in (*session.new, *session.identity_map.values())):
                raise SQLAlchemyError("injected media metadata commit failure")
            return original_commit(session)

        with TestClient(self.runtime.app, raise_server_exceptions=False) as failure_client:
            with patch.object(Session, "commit", new=fail_media_commit):
                failed = failure_client.post("/api/local/media", headers=self.headers, data={"kind": "audio"}, files={
                    "file": ("failed upload.mp3", b"ID3" + b"failed", "audio/mpeg"),
                })
        self.assertEqual(failed.status_code, 500)
        self.assertEqual(existing_path.read_bytes(), previous_bytes)
        files = list((self.runtime.paths.media / "w06").glob("*"))
        self.assertEqual(files, [existing_path])
        self.assertEqual(len(self.client.get("/api/local/media", headers=self.headers).json()), 1)

    def test_commit_state_sender_emits_basic_effect_identity_in_omake_once(self):
        clip = self.upload("audio", "ron.mp3", b"ID3" + b"sfx fixture", "audio/mpeg").json()
        effect_set = self.client.post("/api/local/sound-effect-sets", headers=self.headers, json={
            "label": "검증 효과음", "active": True, "clips": {"riichi": clip["id"]},
        }).json()
        self.client.put("/api/local/sound-selection", headers=self.headers, json={
            "effect_set_id": effect_set["id"], "bgm_ids": [],
        })
        generation = self.client.get("/api/local/play", headers=self.headers).json()["generation"]
        record = GameSessionRecord(
            id="sound-event-session", user_id=self.runtime.member_id, match_seed=9,
            cpu_choices=[], players=[], human_action_indices=[], status="active",
            play_generation=generation, rules_snapshot={"version": 2, "mode": "omake"},
        )
        with self.runtime.session_factory.begin() as session:
            session.add(record)

        class PendingGame:
            cpu_character_by_seat = {}
            done = False
            def __init__(self): self.events = [{"type": "reach", "actor": 1}]
            def pending_events(self):
                events, self.events = self.events, []
                return SimpleNamespace(events=tuple(events))
            def human_turn(self): return SimpleNamespace(observation={"ok": True}, legal_actions=[])

        registered = RegisteredGame(
            session_id=record.id, user_id=self.runtime.member_id, players=(),
            action_version=7, game=PendingGame(), play_generation=generation,
            rules_mode="omake",
        )

        class Socket:
            def __init__(self): self.messages = []
            async def send_json(self, message): self.messages.append(message)
            async def close(self, code): self.closed_code = code

        socket = Socket()
        asyncio.run(send_registered_game_state(socket, registered, self.runtime.session_factory, self.runtime.registry, local_runtime=self.runtime))
        asyncio.run(send_registered_game_state(socket, registered, self.runtime.session_factory, self.runtime.registry, local_runtime=self.runtime))
        effects = [message for message in socket.messages if message.get("type") == "sound_effect"]
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0], {
            "type": "sound_effect", "generation": generation, "session_id": record.id,
            "action_version": 7, "event_index": 0, "event_key": "riichi",
            "asset_id": clip["id"], "url": f"/api/local/media/{clip['id']}/file",
        })
        self.assertGreaterEqual(len([message for message in socket.messages if message.get("type") == "human_turn"]), 1)

    def test_ending_snapshot_survives_resource_changes_reset_and_restart(self):
        image_data = b"\x89PNG\r\n\x1a\n" + b"image-fixture"
        image = self.upload("image", "엔딩 장면.png", image_data, "image/png").json()
        audio = self.upload("audio", "ending.mp3", b"ID3" + b"ending audio fixture", "audio/mpeg").json()
        track = self.client.post("/api/local/background-tracks", headers=self.headers, json={
            "label": "엔딩 음악", "active": True, "media_asset_id": audio["id"],
        }).json()
        configured = self.client.put("/api/local/ending-resources", headers=self.headers, json={
            "cg_asset_id": image["id"], "music_track_id": track["id"], "dialogue_text": "이 문장은 평문으로 고정됩니다.",
        })
        self.assertEqual(configured.status_code, 200, configured.text)
        play = self.client.get("/api/local/play", headers=self.headers).json()
        with self.runtime.session_factory.begin() as session:
            for cpu_id in (1, 2, 3):
                session.get(UserCpuProgress, (self.runtime.member_id, cpu_id)).defeat_stage = 3
        confirmed = self.client.post("/api/local/play/roster", headers=self.headers, json={
            "generation": play["generation"], "cpu_character_ids": [1, 2, 3],
        }).json()
        self.assertEqual(confirmed["phase"], "ending_pending")
        self.assertEqual(confirmed["ending_payload"], {
            "version": 1, "cg_asset_id": image["id"], "music_asset_id": audio["id"],
            "dialogue_text": "이 문장은 평문으로 고정됩니다.",
        })
        deactivated = self.client.patch(f"/api/local/background-tracks/{track['id']}", headers=self.headers, json={"active": False})
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        self.client.put("/api/local/ending-resources", headers=self.headers, json={
            "cg_asset_id": None, "music_track_id": None, "dialogue_text": None,
        })
        ending = self.client.get("/api/local/play/ending", headers=self.headers, params={
            "generation": confirmed["generation"], "event_id": confirmed["ending_event_id"],
        })
        self.assertEqual(ending.status_code, 200, ending.text)
        self.assertTrue(ending.json()["cg"]["available"])
        self.assertTrue(ending.json()["music"]["available"])
        self.assertEqual(ending.json()["dialogue_text"], "이 문장은 평문으로 고정됩니다.")
        ack = self.client.post("/api/local/play/ending/ack", headers=self.headers, json={
            "generation": confirmed["generation"], "ending_event_id": confirmed["ending_event_id"],
        })
        self.assertEqual(ack.json()["phase"], "omake")
        self.assertEqual(self.client.get("/api/local/play/ending", headers=self.headers, params={
            "generation": confirmed["generation"], "event_id": confirmed["ending_event_id"],
        }).json(), {"acknowledged": True})
        reset = self.client.post("/api/local/play/reset", headers=self.headers, json={
            "generation": confirmed["generation"], "confirm": True,
        }).json()
        self.assertEqual(reset["phase"], "roster_required")
        asset_path = self.runtime.paths.media / "w06" / f"{image['id']}.png"
        self.assertTrue(asset_path.is_file())
        self.assertEqual(asset_path.read_bytes(), image_data)
        reactivated = self.client.patch(f"/api/local/background-tracks/{track['id']}", headers=self.headers, json={"active": True})
        self.assertEqual(reactivated.status_code, 200, reactivated.text)
        self.client.put("/api/local/ending-resources", headers=self.headers, json={
            "cg_asset_id": None, "music_track_id": track["id"], "dialogue_text": None,
        })
        with self.runtime.session_factory.begin() as session:
            for cpu_id in (1, 2, 3):
                session.get(UserCpuProgress, (self.runtime.member_id, cpu_id)).defeat_stage = 3
        fresh_play = self.client.get("/api/local/play", headers=self.headers).json()
        deactivated = self.client.patch(f"/api/local/background-tracks/{track['id']}", headers=self.headers, json={"active": False})
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        new_ending = self.client.post("/api/local/play/roster", headers=self.headers, json={
            "generation": fresh_play["generation"], "cpu_character_ids": [1, 2, 3],
        }).json()
        self.assertEqual(new_ending["phase"], "ending_pending")
        self.assertIsNone(new_ending["ending_payload"]["music_asset_id"])
        unresolved = self.client.get("/api/local/play/ending", headers=self.headers, params={
            "generation": new_ending["generation"], "event_id": new_ending["ending_event_id"],
        }).json()
        self.assertFalse(unresolved["music"]["available"])
        self.client.close()
        self.runtime.close()
        data_root = self.runtime.paths.root
        self.runtime = create_local_runtime(data_root)
        self.client = TestClient(self.runtime.app)
        self.headers = {"X-Local-Capability": self.runtime.capability}
        self.assertEqual(self.client.get("/api/local/sound-selection", headers=self.headers).json()["effect_set_id"], None)
        self.assertEqual(self.client.get("/api/local/ending-resources", headers=self.headers).json(), {"cg_asset_id": None, "music_track_id": track["id"], "dialogue_text": None})
        with self.runtime.session_factory() as session:
            self.assertIsNotNone(session.get(LocalMediaAsset, image["id"]))
            self.assertIsNotNone(session.get(BackgroundTrack, track["id"]))


if __name__ == "__main__":
    unittest.main()
