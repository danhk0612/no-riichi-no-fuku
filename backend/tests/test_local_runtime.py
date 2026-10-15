from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import sqlite3
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from app.db.models import CpuCharacter, GameSessionRecord, User, UserCpuProgress
from app.db.session import create_database_engine, mark_write_intent
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
                child = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "import sys; from pathlib import Path; from app.local_runtime import DataRootLock; "
                        "lock=DataRootLock(Path(sys.argv[1])); "
                        "\ntry: lock.acquire()\nexcept RuntimeError: sys.exit(0)\n"
                        "else: lock.release(); sys.exit(2)",
                        str(root / ".engine.lock"),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(child.returncode, 0, child.stderr)
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
                    with runtime.session_factory() as session:
                        barrier.wait(timeout=5)
                        mark_write_intent(session)
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
                        session.flush()
                        session.commit()
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

    def test_local_read_transactions_do_not_reserve_writer_slot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nrnf-read-write-") as directory:
            runtime = create_local_runtime(Path(directory) / "db")
            statements: list[str] = []
            event.listen(
                runtime.engine,
                "before_cursor_execute",
                lambda _conn, _cursor, statement, _params, _context, _many: statements.append(
                    statement.upper()
                ),
            )
            try:
                with runtime.session_factory() as session:
                    self.assertIsNotNone(
                        session.scalar(select(User.id).where(User.id == runtime.member_id))
                    )
                self.assertNotIn("BEGIN IMMEDIATE", statements)

                statements.clear()
                with runtime.session_factory() as session:
                    mark_write_intent(session)
                    self.assertIsNotNone(
                        session.scalar(select(User.id).where(User.id == runtime.member_id))
                    )
                self.assertLess(
                    statements.index("BEGIN IMMEDIATE"),
                    next(i for i, statement in enumerate(statements) if statement.startswith("SELECT")),
                )

                read_barrier = threading.Barrier(2)

                def hold_read_transaction(_index: int) -> int:
                    with runtime.session_factory() as session:
                        user_id = session.scalar(
                            select(User.id).where(User.id == runtime.member_id)
                        )
                        read_barrier.wait(timeout=5)
                        self.assertEqual(
                            session.scalar(
                                select(User.id).where(User.id == runtime.member_id)
                            ),
                            runtime.member_id,
                        )
                        return user_id

                with ThreadPoolExecutor(max_workers=2) as pool:
                    self.assertEqual(
                        list(pool.map(hold_read_transaction, (1, 2))),
                        [runtime.member_id, runtime.member_id],
                    )

                # A separate process holding SQLite's reserved writer slot must not block a local read.
                writer = sqlite3.connect(runtime.paths.database, timeout=1)
                try:
                    writer.execute("BEGIN IMMEDIATE")
                    with runtime.session_factory() as session:
                        self.assertEqual(
                            session.scalar(select(User.id).where(User.id == runtime.member_id)),
                            runtime.member_id,
                        )
                finally:
                    writer.rollback()
                    writer.close()
            finally:
                runtime.close()

    def test_default_sqlite_engine_keeps_existing_immediate_begin_behavior(self) -> None:
        engine = create_database_engine("sqlite+pysqlite:///:memory:")
        statements: list[str] = []
        event.listen(
            engine,
            "before_cursor_execute",
            lambda _conn, _cursor, statement, _params, _context, _many: statements.append(
                statement.upper()
            ),
        )
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1")).scalar_one()
            self.assertIn("BEGIN IMMEDIATE", statements)
        finally:
            engine.dispose()

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
                    websocket.send_json(
                        {
                            "type": "action",
                            "legal_action_index": 0,
                            "action_version": 0,
                        }
                    )
                    self.assertEqual(
                        websocket.receive_json()["code"], "stale_action"
                    )
                    self.assertEqual(
                        self._receive_human_turn(websocket), committed_turn
                    )
                self.assertEqual(restored_turn, committed_turn)
            finally:
                restarted.close()

    def test_capability_protects_local_rest_ws_and_web_auth_remains_separate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nrnf-auth-") as directory:
            runtime = create_local_runtime(Path(directory) / "db")
            try:
                client = TestClient(runtime.app)
                self.assertEqual(client.get("/api/profile/me").status_code, 401)
                for malformed in ("incorrect", ""):
                    rejected = client.get(
                        "/api/profile/me",
                        headers={"X-Local-Capability": malformed},
                    )
                    self.assertEqual(rejected.status_code, 401)
                    if malformed:
                        self.assertNotIn(malformed, rejected.text)
                non_ascii = client.get(
                    "/api/profile/me",
                    headers={
                        "X-Local-Capability": "잘못된 토큰".encode("utf-8")
                    },
                )
                self.assertEqual(non_ascii.status_code, 401)
                admin_rejected = client.get(
                    "/api/admin/cpus",
                    headers={"X-Local-Capability": "잘못된 토큰".encode("utf-8")},
                )
                self.assertEqual(admin_rejected.status_code, 401)
                self.assertNotIn("잘못된 토큰", admin_rejected.text)
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
                self.assertEqual(
                    client.get(
                        "/api/profile/me",
                        headers={"X-Local-Capability": runtime.capability},
                    ).json()["player_name"],
                    "로컬 이름",
                )
                with runtime.session_factory() as session:
                    self.assertEqual(
                        session.get(User, runtime.member_id).player_name,
                        "로컬 이름",
                    )
                self.assertEqual(client.post("/api/auth/login", json={}).status_code, 404)
                self.assertEqual(
                    client.get("/api/admin/cpus").status_code, 401
                )
                admin_cpus = client.get(
                    "/api/admin/cpus",
                    headers={"X-Local-Capability": runtime.capability},
                )
                self.assertEqual(admin_cpus.status_code, 200)
                first_cpu = admin_cpus.json()[0]
                admin_edit = client.patch(
                    f"/api/admin/cpus/{first_cpu['id']}",
                    json={"short_description": "local write fixture"},
                    headers={"X-Local-Capability": runtime.capability},
                )
                self.assertEqual(admin_edit.status_code, 200, admin_edit.text)
                with runtime.session_factory() as session:
                    self.assertEqual(
                        session.get(CpuCharacter, first_cpu["id"]).short_description,
                        "local write fixture",
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
                    websocket.send_json({"type": "authenticate"})
                    self.assertEqual(
                        websocket.receive_json()["code"], "invalid_authentication"
                    )
                    with self.assertRaises(WebSocketDisconnect) as rejected:
                        websocket.receive_json()
                    self.assertEqual(rejected.exception.code, 4401)
                with client.websocket_connect(
                    f"/api/game/sessions/{session_id}/ws"
                ) as websocket:
                    websocket.send_json(
                        {"type": "authenticate", "capability": "old-run-capability"}
                    )
                    self.assertEqual(
                        websocket.receive_json()["code"], "invalid_authentication"
                    )
                    with self.assertRaises(WebSocketDisconnect) as rejected:
                        websocket.receive_json()
                    self.assertEqual(getattr(rejected.exception, "code", None), 4401)
                with client.websocket_connect(
                    f"/api/game/sessions/{session_id}/ws"
                ) as websocket:
                    websocket.send_json(
                        {"type": "authenticate", "capability": "문자열-비ASCII"}
                    )
                    self.assertEqual(
                        websocket.receive_json()["code"], "invalid_authentication"
                    )
                    with self.assertRaises(WebSocketDisconnect) as rejected:
                        websocket.receive_json()
                    self.assertEqual(getattr(rejected.exception, "code", None), 4401)
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

            persisted = create_local_runtime(Path(directory) / "db")
            try:
                profile = TestClient(persisted.app).get(
                    "/api/profile/me",
                    headers={"X-Local-Capability": persisted.capability},
                )
                self.assertEqual(profile.status_code, 200)
                self.assertEqual(profile.json()["player_name"], "로컬 이름")
            finally:
                persisted.close()

    def test_file_db_settlement_commit_failure_rolls_back_and_retries_once(self) -> None:
        with tempfile.TemporaryDirectory(prefix="nrnf-settlement-commit-") as directory:
            root = Path(directory) / "db"
            runtime = create_local_runtime(root)
            client = TestClient(runtime.app)
            headers = {"X-Local-Capability": runtime.capability}
            cpu_ids = [
                cpu["id"]
                for cpu in client.get("/api/game/cpus", headers=headers).json()
            ][:3]
            created = client.post(
                "/api/game/sessions",
                json={"cpu_character_ids": cpu_ids},
                headers=headers,
            )
            self.assertEqual(created.status_code, 201, created.text)
            session_id = created.json()["session_id"]

            try:
                with runtime.session_factory() as session:
                    registered = runtime.registry.get_owned(
                        session, session_id, runtime.member_id
                    )
                for _ in range(1000):
                    if registered.done:
                        break
                    turn = registered.game.human_turn()
                    assert turn is not None
                    with runtime.session_factory() as session:
                        mark_write_intent(session)
                        runtime.registry.submit_action(
                            session,
                            registered,
                            0,
                            registered.action_version,
                        )
                        session.commit()
                self.assertTrue(registered.done, "fixed-seed match did not complete")
                final_action_count = registered.action_version
                final_result = registered.game.result()
                with runtime.session_factory() as session:
                    member = session.get(User, runtime.member_id)
                    hp_before = member.current_hp
                    stages_before = dict(
                        session.execute(
                            select(
                                UserCpuProgress.cpu_character_id,
                                UserCpuProgress.defeat_stage,
                            ).where(UserCpuProgress.user_id == runtime.member_id)
                        ).all()
                    )

                original_commit = Session.commit

                def fail_only_settlement_commit(session: Session) -> None:
                    if session.info.get("sqlite_write_intent"):
                        raise SQLAlchemyError("injected local settlement commit failure")
                    original_commit(session)

                with patch.object(Session, "commit", new=fail_only_settlement_commit):
                    with self.assertRaisesRegex(
                        SQLAlchemyError, "injected local settlement commit failure"
                    ):
                        with client.websocket_connect(
                            f"/api/game/sessions/{session_id}/ws"
                        ) as websocket:
                            websocket.send_json(
                                {"type": "authenticate", "capability": runtime.capability}
                            )
                            websocket.receive_json()

                self.assertNotIn(session_id, runtime.registry._games)
                with runtime.session_factory() as session:
                    persisted = session.get(GameSessionRecord, session_id)
                    self.assertEqual(persisted.status, "active")
                    self.assertEqual(len(persisted.human_action_indices), final_action_count)
                    self.assertIsNone(persisted.settlement)
                    member = session.get(User, runtime.member_id)
                    self.assertEqual(member.current_hp, hp_before)
                    stages_after = dict(
                        session.execute(
                            select(
                                UserCpuProgress.cpu_character_id,
                                UserCpuProgress.defeat_stage,
                            ).where(UserCpuProgress.user_id == runtime.member_id)
                        ).all()
                    )
                    self.assertEqual(stages_after, stages_before)
            finally:
                client.close()
                runtime.close()

            restarted = create_local_runtime(root)
            try:
                client = TestClient(restarted.app)
                headers = {"X-Local-Capability": restarted.capability}
                results = []
                for _ in range(2):
                    with client.websocket_connect(
                        f"/api/game/sessions/{session_id}/ws"
                    ) as websocket:
                        websocket.send_json(
                            {"type": "authenticate", "capability": restarted.capability}
                        )
                        messages = []
                        while True:
                            message = websocket.receive_json()
                            if message["type"] == "match_complete":
                                results.append(message)
                                break
                            messages.append(message)
                            self.assertNotEqual(message["type"], "error", message)
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0]["result"]["scores"], list(final_result.scores))
                self.assertEqual(results[0]["result"]["ranks"], list(final_result.ranks))
                with restarted.session_factory() as session:
                    record = session.get(GameSessionRecord, session_id)
                    self.assertEqual(record.status, "completed")
                    self.assertIsNotNone(record.settlement)
                    self.assertEqual(
                        len(record.human_action_indices), final_action_count
                    )
                    member = session.get(User, restarted.member_id)
                    self.assertEqual(
                        member.current_hp, results[0]["settlement"]["current_hp"]
                    )
                    self.assertEqual(
                        dict(
                            session.execute(
                                select(
                                    UserCpuProgress.cpu_character_id,
                                    UserCpuProgress.defeat_stage,
                                ).where(UserCpuProgress.user_id == restarted.member_id)
                            ).all()
                        ),
                        {
                            **stages_before,
                            **(
                                {
                                    results[0]["settlement"]["cpu_character_id"]:
                                    results[0]["settlement"]["defeat_stage"]
                                }
                                if results[0]["settlement"]["cpu_character_id"] is not None
                                else {}
                            ),
                        },
                    )
            finally:
                client.close()
                restarted.close()

    def test_default_path_is_only_localappdata_and_requires_explicit_test_override(self) -> None:
        paths = resolve_data_paths(Path("relative-test-root"))
        self.assertEqual(paths.database, paths.root / "game.db")
        self.assertEqual(paths.media, paths.root / "media")
        self.assertEqual(paths.config, paths.root / "config")


if __name__ == "__main__":
    unittest.main()
