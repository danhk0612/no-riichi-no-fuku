from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from riichienv import ActionType
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import GameHandResult, GameSessionRecord, User
from app.db.session import LocalRuntimeSession
from app.local_runtime import create_local_runtime
from app.mahjong.hand_results import HandResultCaptureError, HandResultCollector
from app.mahjong.hand_scores import HandScore, HandWin
from app.services.game_registry import GameRegistry
from app.services.hand_results import fact_payload, verify_replay_batch


def _win(start: int, hora: int, actor: int = 0) -> HandWin:
    score = HandScore(
        han=1, fu=30, yakuman=False, yaku=(1,), ron_agari=1000,
        tsumo_agari_oya=500, tsumo_agari_ko=300, pao_payer=None, band=1,
    )
    return HandWin(start, hora, actor, actor, (1000, -300, -300, -400), (), score)


class HandResultCollectorTests(unittest.TestCase):
    def test_offsets_multi_hands_draws_and_terminal_are_source_ordered_and_whitelisted(self):
        collector = HandResultCollector()
        start = {
            "type": "start_kyoku", "bakaze": "E", "kyoku": 1, "honba": 0,
            "oya": 0, "kyotaku": 0, "scores": [25000] * 4,
            "tehais": [["1m"] * 13] * 4,
        }
        collector.consume([{"type": "start_game"}, start], (), (25000,) * 4, False)
        log = [
            {"type": "start_game"}, start,
            {"type": "hora", "actor": 0, "target": 0, "deltas": [1000, -300, -300, -400]},
            {"type": "end_kyoku"},
            {"type": "start_kyoku", "bakaze": "E", "kyoku": 2, "honba": 1,
             "oya": 1, "kyotaku": 0, "scores": [26000, 24700, 24700, 24600], "tehais": []},
            {"type": "ryukyoku", "reason": "nagashimangan", "deltas": [0, 0, 0, 0]},
            {"type": "end_kyoku"}, {"type": "end_game"},
        ]
        collector.consume(log, (_win(1, 2),), (26000, 24700, 24700, 24600), True)
        facts = collector.drain()
        self.assertEqual([(f.start_log_offset, f.end_log_offset) for f in facts], [(1, 3), (4, 6)])
        self.assertEqual([f.payload["outcome"] for f in facts], ["win", "draw"])
        self.assertEqual(facts[0].payload["winners"][0]["win_kind"], "tsumo")
        self.assertEqual(facts[1].payload["draws"][0]["reason"], "nagashimangan")
        self.assertTrue(facts[-1].payload["terminal"])
        self.assertFalse(any("tehais" in fact.payload["start"] for fact in facts))

    def test_rejects_log_prefix_change_and_missing_or_mismatched_score(self):
        collector = HandResultCollector()
        base = [{"type": "start_game"}, {"type": "start_kyoku", "bakaze": "E", "kyoku": 1,
            "honba": 0, "oya": 0, "kyotaku": 0, "scores": [25000] * 4}]
        collector.consume(base, (), (25000,) * 4, False)
        with self.assertRaisesRegex(HandResultCaptureError, "prefix"):
            collector.consume([{"type": "start_game"}, {"type": "other"}], (), (25000,) * 4, False)

        collector = HandResultCollector()
        log = base + [{"type": "hora", "actor": 0, "target": 1, "deltas": [1000, -1000, 0, 0]},
                      {"type": "end_kyoku"}]
        with self.assertRaisesRegex(HandResultCaptureError, "B1 score"):
            collector.consume(log, (), (25000,) * 4, False)

    def test_replay_rejects_missing_or_mutated_persisted_facts(self):
        start = {"type": "start_kyoku", "bakaze": "E", "kyoku": 1, "honba": 0,
                 "oya": 0, "kyotaku": 0, "scores": [25000] * 4}
        log = [{"type": "start_game"}, start,
               {"type": "hora", "actor": 0, "target": 0, "deltas": [1000, -300, -300, -400]},
               {"type": "end_kyoku"}]
        collector = HandResultCollector()
        collector.consume(log, (_win(1, 2),), (26000, 24700, 24700, 24600), False)
        fact = collector.drain()[0]
        record = SimpleNamespace(
            id="test-session", play_generation="test-generation",
            players=[{"seat": 0, "name": "p", "is_human": True},
                     *[{"seat": seat, "name": f"c{seat}", "is_human": False} for seat in (1, 2, 3)]],
            cpu_choices=[{"id": seat, "defeat_stage": 0} for seat in (1, 2, 3)],
        )
        payload = fact_payload(record, fact)
        row = SimpleNamespace(
            sequence=1, hand_start_log_offset=fact.start_log_offset,
            hand_end_log_offset=fact.end_log_offset, source_action_version=2,
            payload=payload,
        )
        self.assertEqual(verify_replay_batch(record, [row], (fact,), 2, 0), 1)
        with self.assertRaisesRegex(HandResultCaptureError, "unpersisted"):
            verify_replay_batch(record, [], (fact,), 2, 0)
        row.payload = {**payload, "outcome": "draw"}
        with self.assertRaisesRegex(HandResultCaptureError, "differs"):
            verify_replay_batch(record, [row], (fact,), 2, 0)


class LocalHandResultPersistenceTests(unittest.TestCase):
    def test_result_commit_failure_rolls_back_facts_and_websocket_restores_saved_turn(self):
        with tempfile.TemporaryDirectory(prefix="nrnf-w09-b2-commit-") as directory:
            runtime = create_local_runtime(Path(directory) / "data")
            runtime.registry = GameRegistry(seed_factory=lambda: 701)
            client = TestClient(runtime.app)
            headers = {"X-Local-Capability": runtime.capability}
            try:
                state = client.get("/api/local/play", headers=headers).json()
                candidates = client.get("/api/local/play/roster-candidates", headers=headers).json()
                cpu_ids = [item["id"] for item in candidates[:3]]
                self.assertEqual(client.post("/api/local/play/roster", headers=headers, json={
                    "generation": state["generation"], "cpu_character_ids": cpu_ids,
                }).status_code, 200)
                created = client.post("/api/game/sessions", headers=headers, json={
                    "generation": state["generation"], "cpu_character_ids": cpu_ids,
                })
                self.assertEqual(created.status_code, 201, created.text)
                session_id = created.json()["session_id"]
                captured = {"count": 0}
                from app.services import game_registry as registry_module
                append_original = registry_module.append_facts
                commit_original = LocalRuntimeSession.commit

                def observe_batch(*args, **kwargs):
                    captured["count"] = len(args[2])
                    return append_original(*args, **kwargs)

                def fail_when_result_is_pending(db_session):
                    if captured["count"]:
                        raise SQLAlchemyError("injected hand result commit failure")
                    return commit_original(db_session)

                with client.websocket_connect(f"/api/game/sessions/{session_id}/ws") as websocket:
                    websocket.send_json({
                        "type": "authenticate", "capability": runtime.capability,
                        "generation": state["generation"],
                    })
                    message = websocket.receive_json()
                    while message.get("type") != "human_turn":
                        self.assertNotEqual(message.get("type"), "error", message)
                        message = websocket.receive_json()
                    self.assertEqual(message["type"], "human_turn")
                    failed_turn = None
                    failed_version = None
                    with patch.object(registry_module, "append_facts", side_effect=observe_batch), patch.object(
                        LocalRuntimeSession, "commit", new=fail_when_result_is_pending,
                    ):
                        for _ in range(160):
                            captured["count"] = 0
                            legal = message["turn"]["legal_actions"]
                            failed_turn = message["turn"]
                            failed_version = message["action_version"]
                            action_index = next((i for i, action in enumerate(legal)
                                                 if action["type"] == int(ActionType.DISCARD)), 0)
                            websocket.send_json({
                                "type": "action", "generation": state["generation"],
                                "action_version": message["action_version"],
                                "legal_action_index": action_index,
                            })
                            message = websocket.receive_json()
                            while message.get("type") not in ("human_turn", "error"):
                                message = websocket.receive_json()
                            if message.get("type") == "error":
                                break
                            self.assertEqual(message["type"], "human_turn")
                    self.assertEqual(message.get("code"), "persistence_failed", message)
                    self.assertGreater(captured["count"], 0, "failure was not injected on a hand-result action")

                with runtime.session_factory() as db:
                    record = db.get(GameSessionRecord, session_id)
                    self.assertEqual(len(db.scalars(select(GameHandResult).where(
                        GameHandResult.session_id == session_id
                    )).all()), 0)
                    committed_actions = len(record.human_action_indices)
                    self.assertGreater(committed_actions, 0)
                with client.websocket_connect(f"/api/game/sessions/{session_id}/ws") as websocket:
                    websocket.send_json({
                        "type": "authenticate", "capability": runtime.capability,
                        "generation": state["generation"],
                    })
                    restored = websocket.receive_json()
                    while restored.get("type") != "human_turn":
                        self.assertNotEqual(restored.get("type"), "error", restored)
                        restored = websocket.receive_json()
                    self.assertEqual(restored["type"], "human_turn")
                    self.assertEqual(restored["action_version"], failed_version)
                    self.assertEqual(restored["turn"], failed_turn)
            finally:
                client.close()
                runtime.close()

    def test_new_local_match_persists_and_replays_closed_hands_without_reset_deletion(self):
        with tempfile.TemporaryDirectory(prefix="nrnf-w09-b2-") as directory:
            runtime = create_local_runtime(Path(directory) / "data")
            runtime.registry = GameRegistry(seed_factory=lambda: 701)
            client = TestClient(runtime.app)
            headers = {"X-Local-Capability": runtime.capability}
            try:
                state = client.get("/api/local/play", headers=headers).json()
                candidates = client.get("/api/local/play/roster-candidates", headers=headers).json()
                cpu_ids = [item["id"] for item in candidates[:3]]
                confirmed = client.post("/api/local/play/roster", headers=headers, json={
                    "generation": state["generation"], "cpu_character_ids": cpu_ids,
                })
                self.assertEqual(confirmed.status_code, 200, confirmed.text)
                created = client.post("/api/game/sessions", headers=headers, json={
                    "generation": state["generation"], "cpu_character_ids": cpu_ids,
                })
                self.assertEqual(created.status_code, 201, created.text)
                session_id = created.json()["session_id"]
                with runtime.session_factory() as db:
                    record = db.get(GameSessionRecord, session_id)
                    self.assertEqual(record.hand_results_version, 1)
                    self.assertEqual(db.scalars(select(GameHandResult).where(
                        GameHandResult.session_id == session_id
                    )).all(), [])
                    registered = runtime.registry.get_owned(db, session_id, runtime.member_id)

                for _ in range(120):
                    turn = registered.game.human_turn()
                    action_index = next((i for i, action in enumerate(turn.legal_actions)
                                         if action["type"] == int(ActionType.DISCARD)), 0)
                    with runtime.session_factory() as db:
                        runtime.registry.submit_action(db, registered, action_index, registered.action_version)
                        db.commit()
                    with runtime.session_factory() as db:
                        rows = db.scalars(select(GameHandResult).where(
                            GameHandResult.session_id == session_id
                        ).order_by(GameHandResult.sequence)).all()
                        if rows:
                            self.assertEqual(rows[0].sequence, 1)
                            self.assertEqual(rows[0].source_action_version, registered.action_version)
                            self.assertEqual(rows[0].payload["generation"], state["generation"])
                            self.assertEqual(rows[0].payload["participants"][0]["name"], "플레이어")
                            self.assertNotIn("tehais", str(rows[0].payload))
                            runtime.registry.evict(session_id)
                            restored = GameRegistry().get_owned(db, session_id, runtime.member_id)
                            self.assertEqual(restored.action_version, registered.action_version)
                            break
                else:
                    self.fail("seed 701 did not close a hand within 120 human actions")

                before_failed_write = restored.game.human_turn()
                failed_index = next((i for i, action in enumerate(before_failed_write.legal_actions)
                                     if action["type"] == int(ActionType.DISCARD)), 0)
                with runtime.session_factory() as db:
                    with patch("app.services.game_registry.append_facts", side_effect=RuntimeError("injected result write failure")):
                        with self.assertRaisesRegex(RuntimeError, "injected result write failure"):
                            runtime.registry.submit_action(db, restored, failed_index, restored.action_version)
                    db.rollback()
                with runtime.session_factory() as db:
                    restored = GameRegistry().get_owned(db, session_id, runtime.member_id)
                    self.assertEqual(restored.game.human_turn(), before_failed_write)
                    self.assertEqual(restored.action_version, len(db.get(GameSessionRecord, session_id).human_action_indices))
                    self.assertEqual(len(db.scalars(select(GameHandResult).where(
                        GameHandResult.session_id == session_id
                    )).all()), 1)

                reset = client.post("/api/local/play/reset", headers=headers, json={
                    "generation": state["generation"], "confirm": True,
                })
                self.assertEqual(reset.status_code, 200, reset.text)
                with runtime.session_factory() as db:
                    record = db.get(GameSessionRecord, session_id)
                    self.assertEqual(record.status, "cancelled")
                    self.assertGreater(db.scalar(select(GameHandResult.sequence).where(
                        GameHandResult.session_id == session_id
                    )), 0)
            finally:
                client.close()
                runtime.close()

    def test_completed_v1_reconnect_reads_terminal_rows_without_engine_replay(self):
        with tempfile.TemporaryDirectory(prefix="nrnf-w09-b2-completed-") as directory:
            runtime = create_local_runtime(Path(directory) / "data")
            runtime.registry = GameRegistry(seed_factory=lambda: 701)
            client = TestClient(runtime.app)
            headers = {"X-Local-Capability": runtime.capability}
            try:
                state = client.get("/api/local/play", headers=headers).json()
                candidates = client.get("/api/local/play/roster-candidates", headers=headers).json()
                cpu_ids = [item["id"] for item in candidates[:3]]
                self.assertEqual(client.post("/api/local/play/roster", headers=headers, json={
                    "generation": state["generation"], "cpu_character_ids": cpu_ids,
                }).status_code, 200)
                created = client.post("/api/game/sessions", headers=headers, json={
                    "generation": state["generation"], "cpu_character_ids": cpu_ids,
                })
                self.assertEqual(created.status_code, 201, created.text)
                session_id = created.json()["session_id"]
                with runtime.session_factory() as db:
                    registered = runtime.registry.get_owned(db, session_id, runtime.member_id)

                for _ in range(800):
                    if registered.game.done:
                        break
                    turn = registered.game.human_turn()
                    action_index = next((i for i, action in enumerate(turn.legal_actions)
                                         if action["type"] in (int(ActionType.PASS), int(ActionType.DISCARD))), 0)
                    with runtime.session_factory() as db:
                        runtime.registry.submit_action(db, registered, action_index, registered.action_version)
                        db.commit()
                self.assertTrue(registered.game.done, "fixed-seed match did not complete")
                with runtime.session_factory() as db:
                    runtime.registry.settle(db, registered)
                    db.commit()
                with runtime.session_factory() as db:
                    record = db.get(GameSessionRecord, session_id)
                    rows = db.scalars(select(GameHandResult).where(
                        GameHandResult.session_id == session_id
                    ).order_by(GameHandResult.sequence)).all()
                    self.assertEqual(record.status, "completed")
                    self.assertTrue(rows)
                    self.assertEqual([row.sequence for row in rows], list(range(1, len(rows) + 1)))
                    self.assertFalse(any(row.payload["terminal"] for row in rows[:-1]))
                    self.assertTrue(rows[-1].payload["terminal"])
                    before = [(row.hand_start_log_offset, row.hand_end_log_offset,
                               row.source_action_version, row.payload) for row in rows]
                fresh_registry = GameRegistry()
                with runtime.session_factory() as db, patch(
                    "app.services.game_registry.create_game_session_from_choices",
                    side_effect=AssertionError("completed v1 must not replay"),
                ):
                    restored = fresh_registry.get_owned(db, session_id, runtime.member_id)
                    self.assertTrue(restored.done)
                    self.assertEqual(list(restored.result.scores), record.scores)
                    after_rows = db.scalars(select(GameHandResult).where(
                        GameHandResult.session_id == session_id
                    ).order_by(GameHandResult.sequence)).all()
                    after = [(row.hand_start_log_offset, row.hand_end_log_offset,
                              row.source_action_version, row.payload) for row in after_rows]
                    self.assertEqual(after, before)
                from scripts.verify_hand_result_evidence import main as verify_artifact_database
                evidence_path = Path(directory) / "hand-results.json"
                verify_artifact_database(runtime.paths.database, evidence_path)
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                self.assertEqual(evidence["database_open_mode"], "read-only")
                self.assertEqual(evidence["verified_completed_sessions"][0]["session_id"], session_id)
            finally:
                client.close()
                runtime.close()


if __name__ == "__main__":
    unittest.main()
