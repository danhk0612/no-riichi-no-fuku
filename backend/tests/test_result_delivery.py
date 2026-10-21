from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import GameHandResult, GameSessionRecord, LocalPlayState, UserCpuProgress
from app.local_runtime import create_local_runtime
from app.services.result_delivery import (
    append_hand_entries,
    append_settlement_entry,
    create_delivery,
    result_envelope,
)


class ResultDeliveryTests(unittest.TestCase):
    def _build_completed(self, runtime):
        with runtime.session_factory.begin() as db:
            state = db.get(LocalPlayState, runtime.member_id)
            generation = state.generation
            record = GameSessionRecord(
                id="c1-test-session", user_id=runtime.member_id, match_seed=1,
                cpu_choices=[
                    {"id": 1, "defeat_stage": 0}, {"id": 2, "defeat_stage": 1}, {"id": 3, "defeat_stage": 2},
                ],
                players=[
                    {"seat": 0, "name": "플레이어", "is_human": True},
                    {"seat": 1, "name": "CPU A", "is_human": False},
                    {"seat": 2, "name": "CPU B", "is_human": False},
                    {"seat": 3, "name": "CPU C", "is_human": False},
                ],
                human_action_indices=[], status="completed", scores=[40000, 30000, 20000, 10000],
                ranks=[1, 2, 3, 4], settlement={"progression_version": 2, "mode": "progress"},
                presentation={"version": 2, "result_asset": None, "result_dialogues": [], "settlement": {"stage_changed": True}},
                play_generation=generation, rules_snapshot={"version": 2, "mode": "progress"},
                hand_results_version=1, result_delivery_version=1,
            )
            db.add(record)
            db.flush()
            fact_payload = {
                "version": 1,
                "generation": generation,
                "start": {"bakaze": "E", "kyoku": 0, "honba": 0, "kyotaku": 0, "oya": 0, "scores": [25000] * 4},
                "participants": [
                    {"seat": 0, "is_human": True, "name": "플레이어", "cpu_id": None, "stage_at_hand": None},
                    {"seat": 1, "is_human": False, "name": "CPU A", "cpu_id": 1, "stage_at_hand": 0},
                    {"seat": 2, "is_human": False, "name": "CPU B", "cpu_id": 2, "stage_at_hand": 1},
                    {"seat": 3, "is_human": False, "name": "CPU C", "cpu_id": 3, "stage_at_hand": 2},
                ],
                "outcome": "win",
                "winners": [{
                    "hora_log_offset": 5, "actor": 1, "target": 0, "win_kind": "ron", "deltas": [-1000, 1000, 0, 0],
                    "ura_markers": [], "score": {"han": 1, "fu": 30, "yakuman": 0, "yaku": ["tanyao"],
                        "ron_agari": 1000, "tsumo_agari_oya": None, "tsumo_agari_ko": None, "pao_payer": None, "band": "만관 미만"},
                }],
                "draws": [], "engine_scores_after_step": [24000, 26000, 25000, 25000], "terminal": True,
            }
            fact = GameHandResult(
                session_id=record.id, hand_start_log_offset=1, sequence=1,
                hand_end_log_offset=8, source_action_version=1, payload=fact_payload,
            )
            db.add(fact)
            db.flush()
            create_delivery(db, record)
            append_hand_entries(db, record, [fact])
            append_settlement_entry(db, record)
            return generation

    def test_result_resume_ack_and_selection_are_server_owned(self):
        with tempfile.TemporaryDirectory(prefix="nrnf-c1-") as directory:
            runtime = create_local_runtime(Path(directory) / "data")
            client = TestClient(runtime.app)
            headers = {"X-Local-Capability": runtime.capability}
            try:
                generation = self._build_completed(runtime)
                play = client.get("/api/local/play", headers=headers)
                self.assertEqual(play.status_code, 200, play.text)
                self.assertEqual(play.json()["result_resume"]["route"], "result")
                session_id = play.json()["result_resume"]["session_id"]
                current = client.get(
                    f"/api/local/play/sessions/{session_id}/results",
                    params={"generation": generation}, headers=headers,
                )
                self.assertEqual(current.status_code, 200, current.text)
                envelope = current.json()
                self.assertEqual(envelope["head"]["kind"], "hand")
                self.assertEqual(envelope["head"]["payload"]["content_mode"], "unbound")
                self.assertEqual(envelope["head"]["payload"]["winner_display_order"], [5])
                first_ack = client.post(
                    f"/api/local/play/sessions/{session_id}/results/ack", headers=headers,
                    json={"generation": generation, "event_id": envelope["head"]["event_id"],
                        "ordinal": envelope["head"]["ordinal"], "expected_delivery_revision": envelope["delivery_revision"]},
                )
                self.assertEqual(first_ack.status_code, 200, first_ack.text)
                self.assertEqual(first_ack.json()["head"]["kind"], "settlement")
                self.assertEqual(first_ack.json()["acked_ordinal"], 1)
                self.assertEqual(first_ack.json()["head"]["payload"]["participants"], [
                    {"seat": 0, "name": "플레이어", "is_human": True},
                    {"seat": 1, "name": "CPU A", "is_human": False},
                    {"seat": 2, "name": "CPU B", "is_human": False},
                    {"seat": 3, "name": "CPU C", "is_human": False},
                ])
                repeated = client.post(
                    f"/api/local/play/sessions/{session_id}/results/ack", headers=headers,
                    json={"generation": generation, "event_id": envelope["head"]["event_id"],
                        "ordinal": envelope["head"]["ordinal"], "expected_delivery_revision": envelope["delivery_revision"]},
                )
                self.assertEqual(repeated.status_code, 200, repeated.text)
                self.assertEqual(repeated.json()["acked_ordinal"], 1)
                final = first_ack.json()
                settled = client.post(
                    f"/api/local/play/sessions/{session_id}/results/ack", headers=headers,
                    json={"generation": generation, "event_id": final["head"]["event_id"],
                        "ordinal": final["head"]["ordinal"], "expected_delivery_revision": final["delivery_revision"]},
                )
                self.assertEqual(settled.status_code, 200, settled.text)
                self.assertEqual(settled.json()["route"], "selection")
                self.assertIsNone(client.get("/api/local/play", headers=headers).json()["result_resume"])
                self.assertIsNone(client.get("/api/game/sessions/recent", headers=headers).json())
                with runtime.session_factory() as db:
                    record = db.get(GameSessionRecord, session_id)
                    self.assertEqual(record.status, "completed")
                    self.assertEqual(len(db.scalars(select(GameHandResult).where(GameHandResult.session_id == session_id)).all()), 1)
                    self.assertEqual(result_envelope(db, record)["acked_ordinal"], 2)
            finally:
                client.close()
                runtime.close()

    def test_bad_event_and_future_ordinal_do_not_advance_cursor(self):
        with tempfile.TemporaryDirectory(prefix="nrnf-c1-conflict-") as directory:
            runtime = create_local_runtime(Path(directory) / "data")
            client = TestClient(runtime.app)
            headers = {"X-Local-Capability": runtime.capability}
            try:
                generation = self._build_completed(runtime)
                state = client.get("/api/local/play", headers=headers).json()
                session_id = state["result_resume"]["session_id"]
                response = client.post(
                    f"/api/local/play/sessions/{session_id}/results/ack", headers=headers,
                    json={"generation": generation, "event_id": "wrong-event", "ordinal": 2, "expected_delivery_revision": 2},
                )
                self.assertEqual(response.status_code, 409, response.text)
                current = client.get(f"/api/local/play/sessions/{session_id}/results?generation={generation}", headers=headers)
                self.assertEqual(current.json()["acked_ordinal"], 0)
                self.assertEqual(current.json()["head"]["ordinal"], 1)
            finally:
                client.close()
                runtime.close()

    def test_pending_results_gate_new_session_and_ending_ack(self):
        with tempfile.TemporaryDirectory(prefix="nrnf-c1-gates-") as directory:
            runtime = create_local_runtime(Path(directory) / "data")
            client = TestClient(runtime.app)
            headers = {"X-Local-Capability": runtime.capability}
            try:
                generation = self._build_completed(runtime)
                state = client.get("/api/local/play", headers=headers).json()
                candidates = client.get("/api/local/play/roster-candidates", headers=headers).json()
                cpu_ids = [item["id"] for item in candidates[:3]]
                roster = client.post("/api/local/play/roster", headers=headers, json={
                    "generation": generation, "cpu_character_ids": cpu_ids,
                })
                self.assertEqual(roster.status_code, 200, roster.text)
                created = client.post("/api/game/sessions", headers=headers, json={
                    "generation": generation, "cpu_character_ids": cpu_ids,
                })
                self.assertEqual(created.status_code, 409, created.text)
                self.assertEqual(created.json()["detail"]["code"], "result_pending")
                with runtime.session_factory.begin() as db:
                    local_state = db.get(LocalPlayState, runtime.member_id)
                    local_state.phase = "ending_pending"
                    local_state.ending_event_id = "pending-ending-event"
                    local_state.ending_payload = {"version": 1, "cg_asset_id": None, "music_asset_id": None, "dialogue_text": ""}
                    for progress in db.scalars(select(UserCpuProgress).where(
                        UserCpuProgress.user_id == runtime.member_id
                    )).all():
                        progress.defeat_stage = 3
                ending = client.post("/api/local/play/ending/ack", headers=headers, json={
                    "generation": generation, "ending_event_id": "pending-ending-event",
                })
                self.assertEqual(ending.status_code, 409, ending.text)
                self.assertEqual(ending.json()["detail"]["code"], "result_pending")
                self.assertEqual(client.get("/api/local/play", headers=headers).json()["result_resume"]["session_id"],
                                 state["result_resume"]["session_id"])
            finally:
                client.close()
                runtime.close()


if __name__ == "__main__":
    unittest.main()
