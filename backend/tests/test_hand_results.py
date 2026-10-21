from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from riichienv import ActionType
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import CpuCharacter, GameHandResult, GameResultDelivery, GameResultDeliveryEntry, GameSessionRecord, LocalPlayState, User, UserCpuProgress
from app.db.session import LocalRuntimeSession
from app.local_runtime import create_local_runtime
from app.mahjong.hand_results import HandResultCaptureError, HandResultCollector, HandResultFact
from app.mahjong.hand_scores import HandScore, HandWin
from app.services.game_registry import GameRegistry
from app.services.hand_results import append_facts, fact_payload, verify_replay_batch
from app.services.result_delivery import acknowledge_result


def _ack_all_results(db, session_id: str, *, include_settlement: bool = True) -> None:
    record = db.get(GameSessionRecord, session_id)
    delivery = db.get(GameResultDelivery, session_id)
    if delivery is None:
        return
    entries = db.scalars(select(GameResultDeliveryEntry).where(
        GameResultDeliveryEntry.session_id == session_id
    ).order_by(GameResultDeliveryEntry.ordinal)).all()
    while delivery.acked_ordinal < len(entries):
        entry = entries[delivery.acked_ordinal]
        if not include_settlement and entry.kind == "settlement":
            break
        acknowledge_result(
            db, record, generation=delivery.generation, event_id=entry.event_id,
            ordinal=entry.ordinal, expected_revision=delivery.revision,
        )


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

    def test_preserves_multiple_hora_mixed_draw_triple_ron_and_repeated_round_number_offsets(self):
        collector = HandResultCollector()
        def start(kyoku, honba):
            return {"type": "start_kyoku", "bakaze": "E", "kyoku": kyoku, "honba": honba,
                    "oya": 0, "kyotaku": 0, "scores": [25000] * 4}
        initial = [{"type": "start_game"}, start(1, 0)]
        collector.consume(initial, (), (25000,) * 4, False)
        log = [
            *initial,
            {"type": "hora", "actor": 0, "target": 0, "deltas": [1000, -300, -300, -400]},
            {"type": "hora", "actor": 1, "target": 1, "deltas": [1000, -300, -300, -400]},
            {"type": "ryukyoku", "reason": "fixture-mixed", "deltas": [0, 0, 0, 0]},
            {"type": "end_kyoku"},
            start(1, 1), {"type": "ryukyoku", "reason": "triple_ron", "deltas": [0, 0, 0, 0]},
            {"type": "end_kyoku"}, {"type": "end_game"},
        ]
        collector.consume(log, (_win(1, 2, 0), _win(1, 3, 1)), (25000,) * 4, True)
        facts = collector.drain()
        self.assertEqual([(fact.start_log_offset, fact.end_log_offset) for fact in facts], [(1, 5), (6, 8)])
        self.assertEqual(facts[0].payload["outcome"], "mixed")
        self.assertEqual([winner["hora_log_offset"] for winner in facts[0].payload["winners"]], [2, 3])
        self.assertEqual(facts[0].payload["draws"][0]["reason"], "fixture-mixed")
        self.assertEqual(facts[1].payload["outcome"], "draw")
        self.assertEqual(facts[1].payload["draws"][0]["reason"], "triple_ron")
        self.assertTrue(facts[1].payload["terminal"])

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

    def test_rejects_in_place_prefix_mutation_without_aliasing_input(self):
        for mutate in (
            lambda start: start.__setitem__("honba", 99),
            lambda start: start["scores"].__setitem__(0, 99999),
        ):
            start = {"type": "start_kyoku", "bakaze": "E", "kyoku": 1, "honba": 0,
                     "oya": 0, "kyotaku": 0, "scores": [25000] * 4}
            log = [{"type": "start_game"}, start]
            collector = HandResultCollector()
            collector.consume(log, (), (25000,) * 4, False)
            mutate(start)
            with self.assertRaisesRegex(HandResultCaptureError, "prefix"):
                collector.consume(log, (), (25000,) * 4, False)

    def test_allows_append_but_rejects_replaced_and_shortened_prefix(self):
        start = {"type": "start_kyoku", "bakaze": "E", "kyoku": 1, "honba": 0,
                 "oya": 0, "kyotaku": 0, "scores": [25000] * 4}
        base = [{"type": "start_game"}, start]
        collector = HandResultCollector()
        collector.consume(base, (), (25000,) * 4, False)
        appended = [*base, {"type": "tsumo", "actor": 0}]
        collector.consume(appended, (), (25000,) * 4, False)

        replacement = [dict(event) for event in appended]
        replacement[1] = {**replacement[1], "scores": [24000] * 4}
        with self.assertRaisesRegex(HandResultCaptureError, "prefix"):
            collector.consume(replacement, (), (25000,) * 4, False)
        with self.assertRaisesRegex(HandResultCaptureError, "prefix"):
            collector.consume(base, (), (25000,) * 4, False)

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
    def test_create_start_facts_are_version_zero_and_result_failure_leaves_no_parent_or_cache(self):
        with tempfile.TemporaryDirectory(prefix="nrnf-w09-b2-start-") as directory:
            runtime = create_local_runtime(Path(directory) / "data")
            client = TestClient(runtime.app)
            headers = {"X-Local-Capability": runtime.capability}
            try:
                state = client.get("/api/local/play", headers=headers).json()
                candidates = client.get("/api/local/play/roster-candidates", headers=headers).json()
                cpu_ids = tuple(item["id"] for item in candidates[:3])
                self.assertEqual(client.post("/api/local/play/roster", headers=headers, json={
                    "generation": state["generation"], "cpu_character_ids": list(cpu_ids),
                }).status_code, 200)
                with runtime.session_factory.begin() as db:
                    db.get(LocalPlayState, runtime.member_id).phase = "omake"
                    for cpu_id in cpu_ids:
                        db.get(UserCpuProgress, (runtime.member_id, cpu_id)).defeat_stage = 3
                raw_fact = HandResultFact(1, 3, {
                    "version": 1,
                    "start": {"bakaze": "E", "kyoku": 1, "honba": 0, "oya": 0,
                              "kyotaku": 0, "scores": [25000] * 4},
                    "outcome": "draw", "winners": [], "draws": [],
                    "engine_scores_after_step": [25000] * 4, "terminal": False,
                })

                class StartFactGame:
                    done = False

                    def pending_hand_results(self):
                        return (raw_fact,)

                    def pending_events(self):
                        return SimpleNamespace(events=())

                from app.services import game_registry as registry_module
                with runtime.session_factory() as db:
                    user = db.get(User, runtime.member_id)
                    with patch.object(registry_module, "create_game_session_from_choices", return_value=StartFactGame()), \
                         patch.object(registry_module, "append_facts", side_effect=RuntimeError("injected start result write")):
                        with self.assertRaisesRegex(RuntimeError, "start result write"):
                            runtime.registry.create(db, user, cpu_ids, generation=state["generation"])
                    db.rollback()
                    self.assertIsNone(db.scalar(select(GameSessionRecord.id).where(
                        GameSessionRecord.user_id == runtime.member_id,
                        GameSessionRecord.status == "active",
                    )))
                    self.assertEqual(runtime.registry._games, {})

                # A result-row flush failure after the parent flush must roll back the
                # whole create and must not be reported as an active-game conflict.
                original_flush = LocalRuntimeSession.flush

                def fail_result_flush(db_session, *args, **kwargs):
                    if any(isinstance(item, GameHandResult) for item in db_session.new):
                        raise SQLAlchemyError("injected start result flush failure")
                    return original_flush(db_session, *args, **kwargs)

                failure_client = TestClient(runtime.app, raise_server_exceptions=False)
                with patch.object(registry_module, "create_game_session_from_choices", return_value=StartFactGame()), \
                     patch.object(LocalRuntimeSession, "flush", new=fail_result_flush):
                    failed_flush = failure_client.post("/api/game/sessions", headers=headers, json={
                        "generation": state["generation"], "cpu_character_ids": list(cpu_ids),
                    })
                self.assertEqual(failed_flush.status_code, 500, failed_flush.text)
                with runtime.session_factory() as db:
                    self.assertIsNone(db.scalar(select(GameSessionRecord.id).where(
                        GameSessionRecord.user_id == runtime.member_id,
                        GameSessionRecord.status == "active",
                    )))
                    self.assertEqual(db.scalars(select(GameHandResult)).all(), [])
                    self.assertEqual(runtime.registry._games, {})

                # The route owns commit, so exercise its post-registry failure guard too.
                with patch.object(registry_module, "create_game_session_from_choices", return_value=StartFactGame()), \
                     patch.object(LocalRuntimeSession, "commit", side_effect=SQLAlchemyError("injected start result commit failure")):
                    failed_commit = failure_client.post("/api/game/sessions", headers=headers, json={
                        "generation": state["generation"], "cpu_character_ids": list(cpu_ids),
                    })
                self.assertEqual(failed_commit.status_code, 500, failed_commit.text)
                with runtime.session_factory() as db:
                    self.assertIsNone(db.scalar(select(GameSessionRecord.id).where(
                        GameSessionRecord.user_id == runtime.member_id,
                        GameSessionRecord.status == "active",
                    )))
                    self.assertEqual(db.scalars(select(GameHandResult)).all(), [])
                    self.assertEqual(runtime.registry._games, {})

                with runtime.session_factory() as db:
                    user = db.get(User, runtime.member_id)
                    with patch.object(registry_module, "create_game_session_from_choices", return_value=StartFactGame()):
                        created = runtime.registry.create(db, user, cpu_ids, generation=state["generation"])
                        db.commit()
                    record = db.get(GameSessionRecord, created.session_id)
                    row = db.scalars(select(GameHandResult).where(
                        GameHandResult.session_id == created.session_id
                    )).one()
                    self.assertEqual(record.hand_results_version, 1)
                    self.assertEqual(record.rules_snapshot["mode"], "omake")
                    self.assertTrue(all(choice["effective_tier"] == 2 for choice in record.cpu_choices))
                    self.assertEqual(row.source_action_version, 0)
                    self.assertEqual(row.sequence, 1)
                    runtime.registry.evict(created.session_id)
                    with patch.object(registry_module, "create_game_session_from_choices", return_value=StartFactGame()):
                        restored = GameRegistry().get_owned(db, created.session_id, runtime.member_id)
                    self.assertEqual(restored.action_version, 0)
                    self.assertIsNotNone(restored.game)
            finally:
                if "failure_client" in locals():
                    failure_client.close()
                client.close()
                runtime.close()

    def test_append_facts_rejects_rows_whose_sequence_disagrees_with_source_order(self):
        record = SimpleNamespace(
            id="test-session", hand_results_version=1, play_generation="test-generation",
            players=[{"seat": 0, "name": "p", "is_human": True},
                     *[{"seat": seat, "name": f"c{seat}", "is_human": False} for seat in (1, 2, 3)]],
            cpu_choices=[{"id": seat, "defeat_stage": 0} for seat in (1, 2, 3)],
        )
        payload = {
            "version": 1, "start": {"bakaze": "E", "kyoku": 1, "honba": 0,
                "oya": 0, "kyotaku": 0, "scores": [25000] * 4},
            "outcome": "draw", "winners": [], "draws": [],
            "engine_scores_after_step": [25000] * 4, "terminal": False,
        }
        facts = tuple(HandResultFact(offset, offset + 2, payload) for offset in (1, 4))
        rows = [
            SimpleNamespace(sequence=1, hand_start_log_offset=4, hand_end_log_offset=6,
                            source_action_version=2, payload=fact_payload(record, facts[1])),
            SimpleNamespace(sequence=2, hand_start_log_offset=1, hand_end_log_offset=3,
                            source_action_version=2, payload=fact_payload(record, facts[0])),
        ]
        with patch("app.services.hand_results.load_rows", return_value=rows):
            with self.assertRaisesRegex(HandResultCaptureError, "sequence"):
                append_facts(SimpleNamespace(add=lambda _row: None), record, facts, 2)

    def test_append_facts_accepts_identical_retry_and_new_suffix_but_rejects_conflicts(self):
        record = SimpleNamespace(
            id="test-session", hand_results_version=1, play_generation="test-generation",
            players=[{"seat": 0, "name": "p", "is_human": True},
                     *[{"seat": seat, "name": f"c{seat}", "is_human": False} for seat in (1, 2, 3)]],
            cpu_choices=[{"id": seat, "defeat_stage": 0} for seat in (1, 2, 3)],
        )
        payload = {
            "version": 1, "start": {"bakaze": "E", "kyoku": 1, "honba": 0,
                "oya": 0, "kyotaku": 0, "scores": [25000] * 4},
            "outcome": "draw", "winners": [], "draws": [],
            "engine_scores_after_step": [25000] * 4, "terminal": False,
        }
        first, suffix = (HandResultFact(offset, offset + 2, payload) for offset in (1, 4))
        first_row = SimpleNamespace(
            sequence=1, hand_start_log_offset=1, hand_end_log_offset=3,
            source_action_version=2, payload=fact_payload(record, first),
        )
        added = []
        db = SimpleNamespace(add=added.append)
        with patch("app.services.hand_results.load_rows", return_value=[first_row]):
            append_facts(db, record, (first,), 2)
            append_facts(db, record, (first, suffix), 2)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0].sequence, 2)
        self.assertEqual(added[0].hand_start_log_offset, 4)

        for field, value in (
            ("hand_end_log_offset", 99),
            ("source_action_version", 3),
            ("payload", {**first_row.payload, "outcome": "win"}),
        ):
            changed = SimpleNamespace(
                sequence=first_row.sequence,
                hand_start_log_offset=first_row.hand_start_log_offset,
                hand_end_log_offset=first_row.hand_end_log_offset,
                source_action_version=first_row.source_action_version,
                payload=deepcopy(first_row.payload),
            )
            setattr(changed, field, value)
            with patch("app.services.hand_results.load_rows", return_value=[changed]):
                with self.assertRaisesRegex(HandResultCaptureError, "conflicts"):
                    append_facts(db, record, (first,), 2)

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

                with runtime.session_factory() as db:
                    restored_game = runtime.registry.get_owned(db, session_id, runtime.member_id)
                    serialization_seen = {"facts": 0}
                    from app.services import hand_results as hand_results_module

                    def fail_serialize(record, fact):
                        serialization_seen["facts"] += 1
                        raise HandResultCaptureError("injected hand result serialization failure")

                    with patch.object(hand_results_module, "fact_payload", side_effect=fail_serialize):
                        with self.assertRaisesRegex(HandResultCaptureError, "serialization failure"):
                            runtime.registry.submit_action(
                                db, restored_game,
                                next((i for i, action in enumerate(failed_turn["legal_actions"])
                                     if action["type"] == int(ActionType.DISCARD)), 0),
                                failed_version,
                            )
                    self.assertGreater(serialization_seen["facts"], 0)
                    self.assertIsNone(restored_game.game)
                    db.rollback()
                with runtime.session_factory() as db:
                    recovered = runtime.registry.get_owned(db, session_id, runtime.member_id)
                    self.assertEqual(recovered.action_version, failed_version)
                    self.assertIsNotNone(recovered.game)
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
                            snapshot_participants = deepcopy(rows[0].payload["participants"])
                            for cpu_id in cpu_ids:
                                db.get(CpuCharacter, cpu_id).name = "현재 설정 변경"
                                db.get(UserCpuProgress, (runtime.member_id, cpu_id)).defeat_stage = 3
                            db.commit()
                            saved = rows[0]
                            row_values = {
                                "session_id": saved.session_id,
                                "hand_start_log_offset": saved.hand_start_log_offset,
                                "sequence": saved.sequence,
                                "hand_end_log_offset": saved.hand_end_log_offset,
                                "source_action_version": saved.source_action_version,
                                "payload": deepcopy(saved.payload),
                                "created_at": saved.created_at,
                            }
                            saved.payload = {**saved.payload, "outcome": "tampered"}
                            db.commit()
                            runtime.registry.evict(session_id)
                            with self.assertRaises(HandResultCaptureError):
                                GameRegistry().get_owned(db, session_id, runtime.member_id)
                            self.assertEqual(db.scalars(select(GameHandResult).where(
                                GameHandResult.session_id == session_id
                            )).one().payload["outcome"], "tampered", "cold GET must not repair or rewrite rows")
                            saved.payload = row_values["payload"]
                            db.commit()
                            db.delete(saved)
                            db.commit()
                            runtime.registry.evict(session_id)
                            with self.assertRaisesRegex(HandResultCaptureError, "unpersisted"):
                                GameRegistry().get_owned(db, session_id, runtime.member_id)
                            self.assertEqual(db.scalar(select(GameHandResult.sequence).where(
                                GameHandResult.session_id == session_id
                            )), None, "cold GET must not backfill missing rows")
                            db.add(GameHandResult(**row_values))
                            db.commit()
                            runtime.registry.evict(session_id)
                            restored = GameRegistry().get_owned(db, session_id, runtime.member_id)
                            self.assertEqual(restored.action_version, registered.action_version)
                            self.assertEqual(row_values["payload"]["participants"], snapshot_participants)
                            break
                else:
                    self.fail("seed 701 did not close a hand within 120 human actions")

                failed_turn = None
                result_flush_failed = False
                original_flush = LocalRuntimeSession.flush

                def fail_action_result_flush(db_session, *args, **kwargs):
                    if any(isinstance(item, GameHandResult) for item in db_session.new):
                        raise SQLAlchemyError("injected action result flush failure")
                    return original_flush(db_session, *args, **kwargs)

                # Advance to the next actual result batch so the injected failure is
                # specifically the row flush, after the engine has already advanced.
                for _ in range(180):
                    before_failed_write = restored.game.human_turn()
                    failed_index = next((i for i, action in enumerate(before_failed_write.legal_actions)
                                         if action["type"] == int(ActionType.DISCARD)), 0)
                    with runtime.session_factory() as db:
                        _ack_all_results(db, session_id)
                        with patch.object(LocalRuntimeSession, "flush", new=fail_action_result_flush):
                            try:
                                runtime.registry.submit_action(db, restored, failed_index, restored.action_version)
                                db.commit()
                            except SQLAlchemyError as error:
                                self.assertIn("action result flush", str(error))
                                db.rollback()
                                failed_turn = before_failed_write
                                result_flush_failed = True
                    if result_flush_failed:
                        break
                self.assertTrue(result_flush_failed, "seed 701 did not reach a result-row flush within 180 actions")
                self.assertIsNone(restored.game, "failed result flush must discard advanced engine")
                with runtime.session_factory() as db:
                    restored = runtime.registry.get_owned(db, session_id, runtime.member_id)
                    self.assertEqual(restored.game.human_turn(), failed_turn)
                    self.assertEqual(restored.action_version, len(db.get(GameSessionRecord, session_id).human_action_indices))
                    self.assertIsNotNone(restored.game, "cold recovery should rebuild the committed turn")
                    self.assertGreaterEqual(len(db.scalars(select(GameHandResult).where(
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
                        _ack_all_results(db, session_id)
                        runtime.registry.submit_action(db, registered, action_index, registered.action_version)
                        db.commit()
                self.assertTrue(registered.game.done, "fixed-seed match did not complete")
                with runtime.session_factory() as db:
                    runtime.registry.evict(session_id)
                    restored_before_settlement = GameRegistry().get_owned(db, session_id, runtime.member_id)
                    rows_before_settlement = db.scalars(select(GameHandResult).where(
                        GameHandResult.session_id == session_id
                    ).order_by(GameHandResult.sequence)).all()
                    frozen_rows = [(row.hand_start_log_offset, row.hand_end_log_offset,
                                    row.source_action_version, row.payload) for row in rows_before_settlement]
                    with patch.object(LocalRuntimeSession, "commit", side_effect=SQLAlchemyError(
                        "injected settlement commit failure"
                    )):
                        with self.assertRaisesRegex(SQLAlchemyError, "settlement commit"):
                            GameRegistry().settle(db, restored_before_settlement)
                            db.commit()
                    db.rollback()
                with runtime.session_factory() as db:
                    active_after_failed_settlement = db.get(GameSessionRecord, session_id)
                    self.assertEqual(active_after_failed_settlement.status, "active")
                    still_saved = db.scalars(select(GameHandResult).where(
                        GameHandResult.session_id == session_id
                    ).order_by(GameHandResult.sequence)).all()
                    self.assertEqual([(row.hand_start_log_offset, row.hand_end_log_offset,
                                       row.source_action_version, row.payload) for row in still_saved], frozen_rows)
                    # A fresh registry cold-restores the committed terminal action, then settles once.
                    restored_for_retry = GameRegistry().get_owned(db, session_id, runtime.member_id)
                    self.assertTrue(restored_for_retry.done)
                    retry_registry = GameRegistry()
                    restored_for_retry = retry_registry.get_owned(db, session_id, runtime.member_id)
                    retry_registry.settle(db, restored_for_retry)
                    db.commit()
                    progress_after_first_settlement = {
                        row.cpu_character_id: row.defeat_stage
                        for row in db.query(UserCpuProgress).filter_by(user_id=runtime.member_id)
                    }
                    retry_registry.settle(db, restored_for_retry)
                    db.commit()
                    progress_after_repeat_settlement = {
                        row.cpu_character_id: row.defeat_stage
                        for row in db.query(UserCpuProgress).filter_by(user_id=runtime.member_id)
                    }
                    self.assertEqual(progress_after_repeat_settlement, progress_after_first_settlement)
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
                with runtime.session_factory.begin() as db:
                    _ack_all_results(db, session_id, include_settlement=False)
                from scripts.verify_hand_result_evidence import main as verify_artifact_database
                evidence_path = Path(directory) / "hand-results.json"
                verify_artifact_database(runtime.paths.database, evidence_path)
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                self.assertEqual(evidence["database_open_mode"], "read-only")
                self.assertEqual(evidence["verified_completed_sessions"][0]["session_id"], session_id)

                with runtime.session_factory() as db:
                    record = db.get(GameSessionRecord, session_id)
                    record.hand_results_version = 9
                    with self.assertRaisesRegex(HandResultCaptureError, "version is unknown"):
                        GameRegistry()._restore(db, record)
                    record.hand_results_version = 1
                    row = db.scalars(select(GameHandResult).where(
                        GameHandResult.session_id == session_id
                    ).order_by(GameHandResult.sequence)).first()
                    original_payload = deepcopy(row.payload)
                    row.payload = {**row.payload, "version": 9}
                    db.commit()
                    with self.assertRaisesRegex(HandResultCaptureError, "payload version is unknown"):
                        GameRegistry().get_owned(db, session_id, runtime.member_id)
                    row.payload = original_payload
                    db.commit()
            finally:
                client.close()
                runtime.close()


if __name__ == "__main__":
    unittest.main()
