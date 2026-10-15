from __future__ import annotations

import tempfile
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from unittest.mock import patch
from pathlib import Path

from alembic import command
from alembic.config import Config

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    CpuCharacter,
    CpuDialogue,
    GameSessionRecord,
    GameSetting,
    LocalPlayRoster,
    LocalPlayState,
    User,
    UserCpuProgress,
)
from app.local_runtime import create_local_runtime
from app.db.session import create_database_engine
from app.mahjong.riichienv_adapter import MatchResult
from app.services.game_registry import GameRegistry, GamePlayer, RegisteredGame
from app.services.game_setup import list_selectable_cpus
from app.services.local_play import effective_choices, roster_candidates


class _FinishedGame:
    cpu_character_by_seat = {1: 1, 2: 2, 3: 3}

    def __init__(self, ranks: tuple[int, int, int, int]):
        self._result = MatchResult(scores=(30000, 25000, 23000, 22000), ranks=ranks)

    def result(self):
        return self._result

    def mark_result_settled(self):
        return None


class LocalPlayTests(unittest.TestCase):
    def _runtime(self, folder: str):
        temporary = tempfile.TemporaryDirectory(prefix=folder)
        runtime = create_local_runtime(Path(temporary.name) / "data")
        client = TestClient(runtime.app)
        headers = {"X-Local-Capability": runtime.capability}
        return temporary, runtime, client, headers

    def test_candidates_include_stage_three_and_roster_keeps_stage_without_copy(self):
        temporary, runtime, client, headers = self._runtime("nrnf-roster-")
        try:
            with runtime.session_factory.begin() as session:
                session.get(UserCpuProgress, (runtime.member_id, 1)).defeat_stage = 3
            play = client.get("/api/local/play", headers=headers).json()
            candidates = client.get("/api/local/play/roster-candidates", headers=headers).json()
            self.assertEqual(len(candidates), 6)
            self.assertEqual(next(cpu for cpu in candidates if cpu["id"] == 1)["defeat_stage"], 3)
            response = client.post("/api/local/play/roster", headers=headers, json={
                "generation": play["generation"], "cpu_character_ids": [1, 2, 3, 4],
            })
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["phase"], "progress")
            self.assertEqual(response.json()["roster"][0]["defeat_stage"], 3)
            admin_headers = {"X-Local-Capability": runtime.capability}
            disabled = client.patch(f"/api/admin/cpus/1", headers=admin_headers, json={"active": False})
            self.assertEqual(disabled.status_code, 409, disabled.text)
            added = client.post("/api/admin/cpus", headers=admin_headers, json={
                "slug": "w06-new-after-roster", "name": "신규 등록 CPU", "style": "검증",
                "short_description": "명단 확장 확인", "active": True,
                "aggression": 0.5, "defense": 0.5, "call_preference": 0.5,
                "riichi_preference": 0.5, "hand_value_preference": 0.5, "speed_preference": 0.5,
            })
            self.assertEqual(added.status_code, 201, added.text)
            self.assertEqual(len(client.get("/api/local/play", headers=headers).json()["roster"]), 4)
            with runtime.session_factory() as session:
                self.assertEqual(session.get(UserCpuProgress, (runtime.member_id, 1)).defeat_stage, 3)
                self.assertEqual(session.scalar(select(LocalPlayRoster.cpu_character_id).where(
                    LocalPlayRoster.user_id == runtime.member_id,
                    LocalPlayRoster.cpu_character_id == 1,
                )), 1)
        finally:
            client.close()
            runtime.close()
            temporary.cleanup()

    def test_completed_cpu_eligibility_and_tier_are_separate_from_stage(self):
        temporary, runtime, client, headers = self._runtime("nrnf-effective-tier-")
        try:
            play = client.get("/api/local/play", headers=headers).json()
            with runtime.session_factory.begin() as session:
                for cpu_id, stage in ((1, 3), (2, 0), (3, 0), (4, 0)):
                    session.get(UserCpuProgress, (runtime.member_id, cpu_id)).defeat_stage = stage
            response = client.post("/api/local/play/roster", headers=headers, json={
                "generation": play["generation"], "cpu_character_ids": [1, 2, 3, 4],
            })
            self.assertEqual(response.status_code, 200, response.text)
            with runtime.session_factory() as session:
                state = session.get(LocalPlayState, runtime.member_id)
                # Three incomplete participants: a completed CPU is not eligible.
                with self.assertRaises(Exception):
                    effective_choices(session, runtime.member_id, (1, 2, 3), state)
                session.get(UserCpuProgress, (runtime.member_id, 2)).defeat_stage = 3
                session.flush()
                # Two incomplete participants: completed CPU joins as Tier 0 while stage remains 3.
                choices = effective_choices(session, runtime.member_id, (1, 2, 3), state)
                self.assertEqual((choices[0].defeat_stage, choices[0].effective_tier), (3, 0))
                session.get(UserCpuProgress, (runtime.member_id, 3)).defeat_stage = 3
                session.get(UserCpuProgress, (runtime.member_id, 4)).defeat_stage = 3
                state.phase = "omake"
                choices = effective_choices(session, runtime.member_id, (1, 2, 3), state)
                self.assertEqual([(choice.defeat_stage, choice.effective_tier) for choice in choices], [(3, 2)] * 3)
        finally:
            client.close()
            runtime.close()
            temporary.cleanup()

    def test_last_unfinished_cpu_fourth_place_completes_and_ack_is_idempotent(self):
        temporary, runtime, client, headers = self._runtime("nrnf-ending-")
        try:
            play = client.get("/api/local/play", headers=headers).json()
            with runtime.session_factory.begin() as session:
                session.get(UserCpuProgress, (runtime.member_id, 1)).defeat_stage = 2
                session.get(UserCpuProgress, (runtime.member_id, 2)).defeat_stage = 3
                session.get(UserCpuProgress, (runtime.member_id, 3)).defeat_stage = 3
            confirmed = client.post("/api/local/play/roster", headers=headers, json={
                "generation": play["generation"], "cpu_character_ids": [1, 2, 3],
            }).json()
            record = GameSessionRecord(
                id="ending-test-session", user_id=runtime.member_id, match_seed=1,
                cpu_choices=[
                    {"id": 1, "defeat_stage": 2, "effective_tier": 2},
                    {"id": 2, "defeat_stage": 3, "effective_tier": 0},
                    {"id": 3, "defeat_stage": 3, "effective_tier": 0},
                ], players=[], human_action_indices=[], status="active",
                play_generation=confirmed["generation"],
                rules_snapshot={"version": 2, "mode": "progress"},
            )
            registered = RegisteredGame(
                session_id=record.id, user_id=runtime.member_id, players=(), action_version=0,
                game=_FinishedGame((1, 4, 2, 3)), play_generation=confirmed["generation"],
                rules_mode="progress",
            )
            registry = GameRegistry()
            with runtime.session_factory.begin() as session:
                session.add(record)
                session.flush()
                settlement = registry._settle_local(session, registered, record)
                self.assertTrue(settlement.cpu_completed)
                self.assertEqual(session.get(UserCpuProgress, (runtime.member_id, 1)).defeat_stage, 3)
                state = session.get(LocalPlayState, runtime.member_id)
                self.assertEqual(state.phase, "ending_pending")
                event_id = state.ending_event_id
                payload = state.ending_payload
                self.assertEqual(payload, {"version": 1, "cg_asset_id": None, "music_asset_id": None, "dialogue_text": None})
            acknowledged = client.post("/api/local/play/ending/ack", headers=headers, json={
                "generation": confirmed["generation"], "ending_event_id": event_id,
            })
            self.assertEqual(acknowledged.status_code, 200, acknowledged.text)
            self.assertEqual(acknowledged.json()["phase"], "omake")
            repeated = client.post("/api/local/play/ending/ack", headers=headers, json={
                "generation": confirmed["generation"], "ending_event_id": event_id,
            })
            self.assertEqual(repeated.status_code, 200, repeated.text)
            self.assertEqual(repeated.json()["ending_payload"], payload)
        finally:
            client.close()
            runtime.close()
            temporary.cleanup()

    def test_completed_cpu_last_dialogue_is_persisted_once(self):
        temporary, runtime, client, headers = self._runtime("nrnf-complete-cpu-dialogue-")
        try:
            play = client.get("/api/local/play", headers=headers).json()
            with runtime.session_factory.begin() as session:
                session.get(UserCpuProgress, (runtime.member_id, 1)).defeat_stage = 3
                session.add(CpuDialogue(cpu_character_id=1, event_key="match_last", text="완료 CPU 패배 대사"))
            confirmed = client.post("/api/local/play/roster", headers=headers, json={
                "generation": play["generation"], "cpu_character_ids": [1, 2, 3],
            })
            self.assertEqual(confirmed.status_code, 200, confirmed.text)
            record = GameSessionRecord(
                id="completed-cpu-dialogue-session", user_id=runtime.member_id, match_seed=1,
                cpu_choices=[
                    {"id": 1, "defeat_stage": 3, "effective_tier": 0},
                    {"id": 2, "defeat_stage": 0, "effective_tier": 2},
                    {"id": 3, "defeat_stage": 0, "effective_tier": 2},
                ], players=[], human_action_indices=[], status="active",
                play_generation=confirmed.json()["generation"],
                rules_snapshot={"version": 2, "mode": "progress"},
            )
            registered = RegisteredGame(
                session_id=record.id, user_id=runtime.member_id, players=(), action_version=0,
                game=_FinishedGame((2, 4, 3, 1)), play_generation=confirmed.json()["generation"],
                rules_mode="progress",
            )
            with runtime.session_factory.begin() as session:
                session.add(record)
                session.flush()
                GameRegistry()._settle_local(session, registered, record)
                dialogues = registered.presentation["result_dialogues"]
                self.assertEqual(len(dialogues), 1)
                self.assertEqual(dialogues[0]["cpu_character_id"], 1)
                self.assertEqual(dialogues[0]["event_key"], "match_last")
        finally:
            client.close()
            runtime.close()
            temporary.cleanup()

    def test_reset_preserves_registered_data_and_files_but_cancels_active_generation(self):
        temporary, runtime, client, headers = self._runtime("nrnf-reset-preserve-")
        try:
            play = client.get("/api/local/play", headers=headers).json()
            candidates = client.get("/api/local/play/roster-candidates", headers=headers).json()
            ids = [cpu["id"] for cpu in candidates[:3]]
            self.assertEqual(client.post("/api/local/play/roster", headers=headers, json={
                "generation": play["generation"], "cpu_character_ids": ids,
            }).status_code, 200)
            started = client.post("/api/game/sessions", headers=headers, json={
                "generation": play["generation"], "cpu_character_ids": ids,
            })
            self.assertEqual(started.status_code, 201, started.text)
            stored_file = runtime.paths.media / "w06" / "preserve.fixture"
            stored_file.parent.mkdir(parents=True)
            stored_file.write_bytes(b"registered runtime fixture")
            with runtime.session_factory.begin() as session:
                session.add(GameSetting(key="w06-preserve-fixture", value={"keep": True}))
                cpu = session.get(CpuCharacter, ids[0])
                cpu.short_description = "keep registered material"
                session.get(UserCpuProgress, (runtime.member_id, ids[0])).defeat_stage = 2
            reset = client.post("/api/local/play/reset", headers=headers, json={
                "generation": play["generation"], "confirm": True,
            })
            self.assertEqual(reset.status_code, 200, reset.text)
            self.assertNotEqual(reset.json()["generation"], play["generation"])
            self.assertEqual(reset.json()["phase"], "roster_required")
            with runtime.session_factory() as session:
                self.assertEqual(session.get(GameSessionRecord, started.json()["session_id"]).status, "cancelled")
                self.assertEqual(session.get(GameSessionRecord, started.json()["session_id"]).human_action_indices, [])
                self.assertEqual(session.get(UserCpuProgress, (runtime.member_id, ids[0])).defeat_stage, 0)
                self.assertEqual(session.get(CpuCharacter, ids[0]).short_description, "keep registered material")
                self.assertEqual(session.get(GameSetting, "w06-preserve-fixture").value, {"keep": True})
            self.assertEqual(stored_file.read_bytes(), b"registered runtime fixture")
        finally:
            client.close()
            runtime.close()
            temporary.cleanup()

    def test_simultaneous_resets_accept_only_one_generation_change(self):
        temporary, runtime, client, headers = self._runtime("nrnf-reset-race-")
        try:
            generation = client.get("/api/local/play", headers=headers).json()["generation"]
            barrier = threading.Barrier(2)

            def reset_once():
                with TestClient(runtime.app) as concurrent_client:
                    barrier.wait(timeout=5)
                    return concurrent_client.post("/api/local/play/reset", headers=headers, json={
                        "generation": generation, "confirm": True,
                    })

            with ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(executor.map(lambda _: reset_once(), range(2)))
            self.assertEqual(sorted(response.status_code for response in responses), [200, 409])
            current = client.get("/api/local/play", headers=headers).json()
            self.assertNotEqual(current["generation"], generation)
            self.assertEqual(current["phase"], "roster_required")
        finally:
            client.close()
            runtime.close()
            temporary.cleanup()

    def test_reset_closes_old_generation_socket_before_old_action_can_commit(self):
        temporary, runtime, client, headers = self._runtime("nrnf-reset-socket-")
        try:
            play = client.get("/api/local/play", headers=headers).json()
            candidates = client.get("/api/local/play/roster-candidates", headers=headers).json()
            ids = [cpu["id"] for cpu in candidates[:3]]
            self.assertEqual(client.post("/api/local/play/roster", headers=headers, json={
                "generation": play["generation"], "cpu_character_ids": ids,
            }).status_code, 200)
            started = client.post("/api/game/sessions", headers=headers, json={
                "generation": play["generation"], "cpu_character_ids": ids,
            })
            self.assertEqual(started.status_code, 201, started.text)
            with client.websocket_connect(f"/api/game/sessions/{started.json()['session_id']}/ws") as websocket:
                websocket.send_json({
                    "type": "authenticate", "capability": runtime.capability,
                    "generation": play["generation"],
                })
                turn = websocket.receive_json()
                self.assertEqual(turn["type"], "human_turn")
                reset = client.post("/api/local/play/reset", headers=headers, json={
                    "generation": play["generation"], "confirm": True,
                })
                self.assertEqual(reset.status_code, 200, reset.text)
                with self.assertRaises(WebSocketDisconnect) as disconnected:
                    websocket.receive_json()
                self.assertEqual(disconnected.exception.code, 4409)
            with runtime.session_factory() as session:
                record = session.get(GameSessionRecord, started.json()["session_id"])
                self.assertEqual(record.status, "cancelled")
                self.assertEqual(record.human_action_indices, [])
        finally:
            client.close()
            runtime.close()
            temporary.cleanup()

    def test_mutable_local_routes_do_not_report_success_when_commit_fails(self):
        temporary, runtime, initial_client, headers = self._runtime("nrnf-local-commit-gate-")
        client = TestClient(runtime.app, raise_server_exceptions=False)
        try:
            play = client.get("/api/local/play", headers=headers).json()
            candidates = client.get("/api/local/play/roster-candidates", headers=headers).json()
            ids = [cpu["id"] for cpu in candidates[:3]]
            original_commit = Session.commit

            def fail_write(session: Session):
                if session.info.get("sqlite_write_intent"):
                    raise SQLAlchemyError("injected local commit failure")
                return original_commit(session)

            with patch.object(Session, "commit", new=fail_write):
                failed_roster = client.post("/api/local/play/roster", headers=headers, json={
                    "generation": play["generation"], "cpu_character_ids": ids,
                })
            self.assertEqual(failed_roster.status_code, 500)
            self.assertEqual(client.get("/api/local/play", headers=headers).json()["phase"], "roster_required")

            confirmed = client.post("/api/local/play/roster", headers=headers, json={
                "generation": play["generation"], "cpu_character_ids": ids,
            }).json()
            with patch.object(Session, "commit", new=fail_write):
                failed_start = client.post("/api/game/sessions", headers=headers, json={
                    "generation": confirmed["generation"], "cpu_character_ids": ids,
                })
            self.assertEqual(failed_start.status_code, 500)
            self.assertFalse(runtime.registry._games)
            with runtime.session_factory() as session:
                self.assertIsNone(session.scalar(select(GameSessionRecord.id).where(GameSessionRecord.status == "active")))

            started = client.post("/api/game/sessions", headers=headers, json={
                "generation": confirmed["generation"], "cpu_character_ids": ids,
            })
            self.assertEqual(started.status_code, 201, started.text)
            with patch.object(Session, "commit", new=fail_write):
                failed_reset = client.post("/api/local/play/reset", headers=headers, json={
                    "generation": confirmed["generation"], "confirm": True,
                })
            self.assertEqual(failed_reset.status_code, 500)
            self.assertEqual(client.get("/api/local/play", headers=headers).json()["generation"], confirmed["generation"])
            with runtime.session_factory() as session:
                self.assertEqual(session.get(GameSessionRecord, started.json()["session_id"]).status, "active")

            reset = client.post("/api/local/play/reset", headers=headers, json={
                "generation": confirmed["generation"], "confirm": True,
            }).json()
            with runtime.session_factory.begin() as session:
                for cpu_id in range(1, 7):
                    session.get(UserCpuProgress, (runtime.member_id, cpu_id)).defeat_stage = 3
            pending = client.post("/api/local/play/roster", headers=headers, json={
                "generation": reset["generation"], "cpu_character_ids": ids,
            }).json()
            self.assertEqual(pending["phase"], "ending_pending")
            with patch.object(Session, "commit", new=fail_write):
                failed_ack = client.post("/api/local/play/ending/ack", headers=headers, json={
                    "generation": pending["generation"], "ending_event_id": pending["ending_event_id"],
                })
            self.assertEqual(failed_ack.status_code, 500)
            self.assertEqual(client.get("/api/local/play", headers=headers).json()["phase"], "ending_pending")
        finally:
            initial_client.close()
            client.close()
            runtime.close()
            temporary.cleanup()

    def test_upgrade_from_0004_preserves_legacy_profile_progress_and_active_record(self):
        temporary = tempfile.TemporaryDirectory(prefix="nrnf-local-upgrade-")
        root = Path(temporary.name) / "data"
        runtime = create_local_runtime(root)
        try:
            with runtime.session_factory.begin() as session:
                member = session.get(User, runtime.member_id)
                member.player_name = "기존 프로필"
                member.current_hp = 0
                session.get(UserCpuProgress, (runtime.member_id, 1)).defeat_stage = 2
                choices = list_selectable_cpus(session, runtime.member_id)[:3]
                snapshots = []
                for choice in choices:
                    snapshot = asdict(choice)
                    snapshot.pop("effective_tier", None)
                    snapshots.append(snapshot)
                session.add(GameSessionRecord(
                    id="legacy-active-before-0005", user_id=runtime.member_id,
                    match_seed=77, cpu_choices=snapshots,
                    players=[
                        {"seat": 0, "name": "기존 프로필", "is_human": True},
                        *[{"seat": seat, "name": choices[seat - 1].name, "is_human": False} for seat in (1, 2, 3)],
                    ],
                    human_action_indices=[4, 8], status="active",
                ))
        finally:
            runtime.close()

        engine = create_database_engine(f"sqlite:///{root / 'game.db'}")
        try:
            cfg = Config("alembic.ini")
            cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
            with engine.connect() as connection:
                cfg.attributes["connection"] = connection
                command.downgrade(cfg, "20260912_0004")
        finally:
            engine.dispose()

        upgraded = create_local_runtime(root)
        client = TestClient(upgraded.app)
        try:
            headers = {"X-Local-Capability": upgraded.capability}
            state = client.get("/api/local/play", headers=headers).json()
            self.assertEqual(state["phase"], "roster_required")
            self.assertEqual(state["active_session_id"], "legacy-active-before-0005")
            self.assertTrue(state["legacy_active"])
            with upgraded.session_factory() as session:
                member = session.get(User, upgraded.member_id)
                record = session.get(GameSessionRecord, "legacy-active-before-0005")
                self.assertEqual(member.player_name, "기존 프로필")
                self.assertEqual(member.current_hp, 0)
                self.assertEqual(session.get(UserCpuProgress, (upgraded.member_id, 1)).defeat_stage, 2)
                self.assertEqual(record.play_generation, state["generation"])
                self.assertIsNone(record.rules_snapshot)
                self.assertEqual(record.human_action_indices, [4, 8])
        finally:
            client.close()
            upgraded.close()
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
