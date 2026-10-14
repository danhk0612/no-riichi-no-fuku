from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.db.models import CpuCharacter, GameSessionRecord, User, UserCpuProgress
from app.local_runtime import create_local_runtime, resolve_data_paths


class LocalRuntimeTests(unittest.TestCase):
    @staticmethod
    def _receive_human_turn(websocket):
        while True:
            message = websocket.receive_json()
            if message["type"] == "human_turn":
                return message
            if message["type"] == "error":
                raise AssertionError(message)

    def test_explicit_data_root_layout_migration_and_idempotent_profile_restore(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nrnf-local-") as directory:
            root = Path(directory) / "only-this-test-root"
            runtime = create_local_runtime(root)
            try:
                self.assertEqual(runtime.paths.root, root.resolve())
                self.assertEqual(runtime.paths.database.name, "game.db")
                self.assertTrue(runtime.paths.media.is_dir())
                self.assertTrue(runtime.paths.config.is_dir())
                with runtime.engine.connect() as connection:
                    self.assertEqual(
                        connection.execute(text("PRAGMA foreign_keys")).scalar_one(), 1
                    )
                    self.assertEqual(
                        connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
                        "20260912_0004",
                    )
                with runtime.session_factory.begin() as session:
                    member = session.get(User, runtime.member_id)
                    member.player_name = "저장 이름"
                    member.current_hp = 2
                    progress = session.get(UserCpuProgress, (member.id, 1))
                    progress.defeat_stage = 2
                    session.add(
                        GameSessionRecord(
                            id="preserved-active-test-session",
                            user_id=member.id,
                            match_seed=7,
                            cpu_choices=[],
                            players=[],
                            human_action_indices=[1, 3],
                            status="active",
                        )
                    )
            finally:
                runtime.close()

            restarted = create_local_runtime(root)
            try:
                with restarted.session_factory() as session:
                    member = session.get(User, restarted.member_id)
                    self.assertEqual(member.player_name, "저장 이름")
                    self.assertEqual(member.current_hp, 2)
                    self.assertEqual(
                        session.get(UserCpuProgress, (member.id, 1)).defeat_stage, 2
                    )
                    active = session.get(GameSessionRecord, "preserved-active-test-session")
                    self.assertEqual(active.human_action_indices, [1, 3])
                    self.assertEqual(
                        session.scalar(select(func.count()).select_from(User).where(User.role == "member")),
                        1,
                    )
                    self.assertEqual(
                        session.scalar(select(func.count()).select_from(CpuCharacter)), 6
                    )
            finally:
                restarted.close()

    def test_engine_lock_foreign_keys_and_active_game_unique_constraint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nrnf-lock-") as directory:
            root = Path(directory) / "db"
            first = create_local_runtime(root)
            try:
                with self.assertRaisesRegex(RuntimeError, "another engine owns"):
                    create_local_runtime(root)
                with first.session_factory.begin() as session:
                    member = session.get(User, first.member_id)
                    session.add(
                        GameSessionRecord(
                            id="first-active",
                            user_id=member.id,
                            match_seed=1,
                            cpu_choices=[],
                            players=[],
                            human_action_indices=[],
                            status="active",
                        )
                    )
                with first.session_factory.begin() as session:
                    session.add(
                        GameSessionRecord(
                            id="second-active",
                            user_id=first.member_id,
                            match_seed=2,
                            cpu_choices=[],
                            players=[],
                            human_action_indices=[],
                            status="active",
                        )
                    )
                    with self.assertRaises(IntegrityError):
                        session.flush()
                with first.session_factory.begin() as session:
                    with self.assertRaises(IntegrityError):
                        session.execute(text("INSERT INTO user_cpu_progress (user_id,cpu_character_id,defeat_stage,created_at,updated_at) VALUES (999999,999999,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
            finally:
                first.close()

            again = create_local_runtime(root)
            again.close()

    def test_concurrent_active_session_writers_are_serialized_by_sqlite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nrnf-writers-") as directory:
            runtime = create_local_runtime(Path(directory) / "db")
            barrier = threading.Barrier(2)

            def write_active(session_id: str) -> str:
                try:
                    with runtime.session_factory.begin() as session:
                        session.add(
                            GameSessionRecord(
                                id=session_id,
                                user_id=runtime.member_id,
                                match_seed=1,
                                cpu_choices=[],
                                players=[],
                                human_action_indices=[],
                                status="active",
                            )
                        )
                        barrier.wait(timeout=5)
                        session.flush()
                    return "committed"
                except IntegrityError:
                    return "rejected"

            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    outcomes = list(pool.map(write_active, ("race-a", "race-b")))
                self.assertCountEqual(outcomes, ["committed", "rejected"])
                with runtime.session_factory() as session:
                    count = session.scalar(
                        select(func.count()).select_from(GameSessionRecord).where(
                            GameSessionRecord.status == "active"
                        )
                    )
                    self.assertEqual(count, 1)
            finally:
                runtime.close()

    def test_file_database_restores_exact_turn_after_process_runtime_restart(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nrnf-recovery-") as directory:
            root = Path(directory) / "db"
            first = create_local_runtime(root)
            try:
                first_client = TestClient(first.app)
                headers = {"X-Local-Capability": first.capability}
                cpu_ids = [cpu["id"] for cpu in first_client.get("/api/game/cpus", headers=headers).json()][:3]
                started = first_client.post(
                    "/api/game/sessions",
                    json={"cpu_character_ids": cpu_ids},
                    headers=headers,
                )
                self.assertEqual(started.status_code, 201)
                session_id = started.json()["session_id"]
                with first_client.websocket_connect(
                    f"/api/game/sessions/{session_id}/ws"
                ) as websocket:
                    websocket.send_json(
                        {"type": "authenticate", "capability": first.capability}
                    )
                    before = self._receive_human_turn(websocket)
                    websocket.send_json(
                        {
                            "type": "action",
                            "legal_action_index": 0,
                            "action_version": before["action_version"],
                        }
                    )
                    committed_turn = self._receive_human_turn(websocket)
                self.assertEqual(committed_turn["action_version"], 1)
            finally:
                first.close()

            restarted = create_local_runtime(root)
            try:
                client = TestClient(restarted.app)
                headers = {"X-Local-Capability": restarted.capability}
                active = client.get("/api/game/sessions/active", headers=headers)
                self.assertEqual(active.status_code, 200)
                self.assertEqual(active.json()["session_id"], session_id)
                with client.websocket_connect(
                    f"/api/game/sessions/{session_id}/ws"
                ) as websocket:
                    websocket.send_json(
                        {"type": "authenticate", "capability": restarted.capability}
                    )
                    restored_turn = self._receive_human_turn(websocket)
                self.assertEqual(restored_turn, committed_turn)
            finally:
                restarted.close()

    def test_capability_protects_local_rest_ws_and_web_auth_remains_separate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nrnf-auth-") as directory:
            runtime = create_local_runtime(Path(directory) / "db")
            try:
                client = TestClient(runtime.app)
                self.assertEqual(client.get("/api/profile/me").status_code, 401)
                self.assertEqual(
                    client.get(
                        "/api/profile/me",
                        headers={"X-Local-Capability": "incorrect"},
                    ).status_code,
                    401,
                )
                profile = client.get(
                    "/api/profile/me",
                    headers={"X-Local-Capability": runtime.capability},
                )
                self.assertEqual(profile.status_code, 200)
                self.assertEqual(profile.json()["player_name"], "플레이어")
                edited = client.patch(
                    "/api/profile/me",
                    json={"player_name": "로컬 이름"},
                    headers={"X-Local-Capability": runtime.capability},
                )
                self.assertEqual(edited.status_code, 200)
                self.assertEqual(edited.json()["player_name"], "로컬 이름")
                self.assertEqual(client.post("/api/auth/login", json={}).status_code, 404)
                self.assertEqual(
                    client.get("/api/admin/cpus").status_code, 401
                )
                self.assertEqual(
                    client.get(
                        "/api/admin/cpus",
                        headers={"X-Local-Capability": runtime.capability},
                    ).status_code,
                    200,
                )
                self.assertEqual(
                    client.get(
                        "/api/admin/users",
                        headers={"X-Local-Capability": runtime.capability},
                    ).status_code,
                    404,
                )
                cpu_ids = [
                    cpu["id"]
                    for cpu in client.get(
                        "/api/game/cpus",
                        headers={"X-Local-Capability": runtime.capability},
                    ).json()
                ][:3]
                created = client.post(
                    "/api/game/sessions",
                    json={"cpu_character_ids": cpu_ids},
                    headers={"X-Local-Capability": runtime.capability},
                )
                self.assertEqual(created.status_code, 201)
                session_id = created.json()["session_id"]
                with client.websocket_connect(
                    f"/api/game/sessions/{session_id}/ws"
                ) as websocket:
                    websocket.send_json(
                        {"type": "authenticate", "capability": "old-run-capability"}
                    )
                    self.assertEqual(
                        websocket.receive_json()["code"], "invalid_authentication"
                    )
                with client.websocket_connect(
                    f"/api/game/sessions/{session_id}/ws"
                ) as websocket:
                    websocket.send_json(
                        {"type": "authenticate", "capability": runtime.capability}
                    )
                    self.assertEqual(websocket.receive_json()["type"], "human_turn")
                self.assertIsNone(runtime.websocket_member("old-run-capability"))
                self.assertIsNotNone(runtime.websocket_member(runtime.capability))
            finally:
                runtime.close()

            restarted = create_local_runtime(Path(directory) / "db")
            try:
                self.assertNotEqual(runtime.capability, restarted.capability)
                self.assertIsNone(restarted.websocket_member(runtime.capability))
            finally:
                restarted.close()

    def test_default_path_is_only_localappdata_and_requires_explicit_test_override(self) -> None:
        paths = resolve_data_paths(Path("relative-test-root"))
        self.assertEqual(paths.database, paths.root / "game.db")
        self.assertEqual(paths.media, paths.root / "media")
        self.assertEqual(paths.config, paths.root / "config")


if __name__ == "__main__":
    unittest.main()
