from __future__ import annotations

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import GameHandResult, GameResultDeliveryEntry, GameSessionRecord, LocalPlayState, UserCpuProgress
from app.local_runtime import create_local_runtime
from app.services.result_delivery import (
    append_hand_entries,
    append_settlement_entry,
    create_delivery,
    result_envelope,
)


class ResultDeliveryTests(unittest.TestCase):
    def _build_completed(self, runtime, content=False, hand_defaults=False, mode="progress", last_seat=3):
        with runtime.session_factory.begin() as db:
            if hand_defaults:
                from app.db.models import SharedPromptDefault, SharedPromptItem
                for kind in ("clothing_state", "situation", "pose"):
                    db.add(SharedPromptItem(id=kind, kind=kind, level=0, label=kind, positive=kind,
                        negative="", allowed_events=["ron_band_2"] if kind=="situation" else None))
                    db.flush()
                    db.add(SharedPromptDefault(level=0,kind=kind,item_id=kind))
            state = db.get(LocalPlayState, runtime.member_id)
            generation = state.generation
            ranks = [1, 2, 3, 4]
            ranks[3], ranks[last_seat] = ranks[last_seat], ranks[3]
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
                ranks=ranks, settlement={"progression_version": 2, "mode": mode},
                presentation={"version": 2, "result_asset": None, "result_dialogues": [], "settlement": {"stage_changed": mode == "progress" and last_seat != 0, "mode": mode, "defeat_stage": 3 if mode == "progress" and last_seat else None}},
                play_generation=generation, rules_snapshot={"version": 2, "mode": mode},
                hand_results_version=1, result_delivery_version=1, result_content_version=1 if content else None,
            )
            db.add(record)
            db.flush()
            fact_payload = {
                "version": 1,
                "generation": generation,
                "start": {"bakaze": "E", "kyoku": 1, "honba": 0, "kyotaku": 0, "oya": 0, "scores": [25000] * 4},
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
                        "ron_agari": 1000, "tsumo_agari_oya": None, "tsumo_agari_ko": None, "pao_payer": None, "band": 2},
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

    def test_defeat_voice_claim_is_settlement_only_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            runtime = create_local_runtime(data)
            try:
                generation = self._build_completed(runtime)
                headers = {"X-Local-Capability": runtime.capability}
                path = "/api/local/play/sessions/c1-test-session/results"
                query = {"generation": generation}
                with TestClient(runtime.app) as client:
                    hand = client.get(path, headers=headers, params=query).json()
                    event = hand["head"]["event_id"]
                    self.assertEqual(client.post(f"{path}/{event}/defeat-voice", headers=headers, params=query).status_code, 409)
                    result = client.post(f"{path}/ack", headers=headers, json={
                        **query, "ordinal": 1, "event_id": event, "expected_delivery_revision": hand["delivery_revision"]})
                    url = f"{path}/{result.json()['head']['event_id']}/defeat-voice"
                    with patch("app.api.local_play.resolve_voice_slot", return_value={"url": "/clip"}) as resolver:
                        with ThreadPoolExecutor(max_workers=2) as pool:
                            clips = list(pool.map(lambda _: client.post(url, headers=headers, params=query).json()["url"], range(2)))
                        self.assertCountEqual(clips, [None, "/clip"])
                        self.assertEqual(resolver.call_args.args[1:3], (3, "defeat_stage_3"))
                        resolver.assert_called_once()
            finally:
                runtime.close()
            runtime = create_local_runtime(data)
            try:
                with TestClient(runtime.app) as client:
                    self.assertEqual(client.post(url, headers={"X-Local-Capability": runtime.capability}, params=query).json(), {"url": None})
            finally:
                runtime.close()

    def test_omake_uses_final_voice_and_human_last_place_is_silent(self):
        for seat in (0, 2):
            with self.subTest(seat=seat), tempfile.TemporaryDirectory() as tmp:
                runtime = create_local_runtime(Path(tmp) / "data")
                try:
                    gen = self._build_completed(runtime, mode="omake", last_seat=seat)
                    with TestClient(runtime.app) as client:
                        headers = {"X-Local-Capability": runtime.capability}
                        path = "/api/local/play/sessions/c1-test-session/results"
                        hand = client.get(path, headers=headers, params={"generation": gen}).json()
                        result = client.post(f"{path}/ack", headers=headers, json={
                            "generation": gen, "ordinal": 1, "event_id": hand["head"]["event_id"],
                            "expected_delivery_revision": hand["delivery_revision"]}).json()
                        with patch("app.api.local_play.resolve_voice_slot", return_value=None) as slot:
                            reply = client.post(f"{path}/{result['head']['event_id']}/defeat-voice",
                                                headers=headers, params={"generation": gen})
                            self.assertEqual(reply.json(), {"url": None})
                            if seat:
                                self.assertEqual(slot.call_args.args[1:3], (2, "defeat_stage_3"))
                            else:
                                slot.assert_not_called()
                finally:
                    runtime.close()

    def test_saved_content_survives_editor_change_and_cold_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            runtime = create_local_runtime(data)
            try:
                with TestClient(runtime.app) as client:
                    path = "/api/local/characters/1/fixed-dialogues"
                    headers = {"X-Local-Capability": runtime.capability}
                    def edit(revision, text):
                        response = client.patch(path, headers=headers, json={"expected_revision": revision, "edits": {"win": {"text": text}}})
                        self.assertEqual(response.status_code, 200, response.text)
                    gp = "/api/local/generation-settings"
                    first = {"expected_revision": 0, "common": {"model": "common", "loras": [{"name":"A","strength":1}]},
                             "characters": {"1":{"model": "CPU1", "loras": [{"name":"B","strength":0}]}}}
                    self.assertEqual(client.put(gp, headers=headers, json=first).status_code, 200)
                    edit(0, "original")
                    self._build_completed(runtime, content=True, hand_defaults=True)
                    self.assertEqual(client.put(gp, headers=headers, json={"expected_revision": 1, "common":{"model":"updated"}}).status_code, 200)
                    edit(1, "edited")
            finally:
                runtime.close()
            runtime = create_local_runtime(data)
            try:
                with runtime.session_factory() as db:
                    record = db.get(GameSessionRecord, "c1-test-session")
                    head = result_envelope(db, record)["head"]["payload"]
                    self.assertEqual(head["content_mode"], "snapshot")
                    self.assertEqual(head["content"]["dialogues"][0]["text"], "original")
                    self.assertEqual(head["content"]["scene"]["event"], "ron_band_2")
                    frozen = head["content"]["scene"]["generation_input"]
                    self.assertEqual((frozen["settings"]["model"], frozen["settings"]["loras"]), ("CPU1", [["A", 1], ["B", 0]]))
                    self.assertNotIn("endpoint", frozen["settings"])
                    settlement = db.scalar(select(GameResultDeliveryEntry).where(GameResultDeliveryEntry.kind == "settlement"))
                    self.assertEqual(settlement.result_content["scene"]["stage"], 3)
                    self.assertEqual(settlement.result_content["dialogues"][0]["slot"], "defeat_stage_3")
            finally:
                runtime.close()

    def test_hand_default_must_match_event_and_missing_candidate_never_submits(self):
        from copy import deepcopy
        from app.db.models import GameResultDelivery
        from app.services.result_content import resolve
        with tempfile.TemporaryDirectory() as tmp:
            rt = create_local_runtime(Path(tmp))
            try:
                with TestClient(rt.app,headers={"X-Local-Capability":rt.capability}) as client:
                    client.put("/api/local/generation-settings",json={"expected_revision":0,
                        "common":{"model":"m","encoder":"e","vae":"v"}}).raise_for_status()
                    generation = self._build_completed(rt,content=True)
                    base="/api/local/play/sessions/c1-test-session/results"
                    head=client.get(base,params={"generation":generation}).json()["head"]
                    scene=head["payload"]["content"]["scene"]
                    self.assertIn("declaring ron", scene["generation_input"]["positive"])
                    self.assertEqual(head["payload"]["content"]["dialogues"][0]["slot"],"win")
                    with rt.session_factory() as db:
                        anchor=deepcopy(db.get(GameResultDelivery,"c1-test-session").content_anchor)
                    level=anchor["seats"]["1"]["levels"]["0"]
                    # A saved pre-recipe anchor retains its original candidate requirements.
                    del level["composed_cg"]
                    for kind in ("clothing_state","situation","pose"):
                        level[kind] = {"explicit": []}
                        level[kind]["default"]={"positive":kind,"negative":"","allowed_events":["ron_band_2"]}
                    level["situation"]["explicit"]=[{"positive":"wrong","negative":"","allowed_events":["ron_band_1"]}]
                    def resolved(): return resolve(anchor,"hand",head["payload"],head["event_id"])["scene"]
                    self.assertIn("situation",resolved()["generation_input"]["positive"])
                    level["situation"]["default"]["allowed_events"]=["tsumo_band_2"]
                    self.assertEqual(resolved()["missing_candidates"],["situation"])
                    self.assertNotIn("generation_input",resolved())
            finally:
                rt.close()

    def test_invalid_optional_generation_settings_do_not_block_results(self):
        from app.db.models import GameSetting
        from app.services.generation_settings import KEY
        with tempfile.TemporaryDirectory() as tmp:
            runtime = create_local_runtime(Path(tmp))
            try:
                with runtime.session_factory.begin() as db:
                    db.add(GameSetting(key=KEY, value={"revision": 1, "common": {"steps": "broken"}}))
                self._build_completed(runtime, content=True)
                with runtime.session_factory() as db:
                    record = db.get(GameSessionRecord, "c1-test-session")
                    saved = result_envelope(db, record)["head"]["payload"]["content"]["scene"]
                    self.assertEqual(saved["event"], "ron_band_2")
                    self.assertNotIn("generation_input", saved)
            finally:
                runtime.close()

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

    def test_ack_commit_failure_keeps_cursor_and_revision_for_retry(self):
        with tempfile.TemporaryDirectory(prefix="nrnf-c1-ack-failure-") as directory:
            runtime = create_local_runtime(Path(directory) / "data")
            client = TestClient(runtime.app)
            headers = {"X-Local-Capability": runtime.capability}
            try:
                generation = self._build_completed(runtime)
                before = client.get("/api/local/play", headers=headers).json()["result_resume"]
                session_id = before["session_id"]
                envelope = client.get(f"/api/local/play/sessions/{session_id}/results?generation={generation}", headers=headers).json()
                with patch.object(Session, "commit", side_effect=RuntimeError("injected commit failure")):
                    failed = client.post(f"/api/local/play/sessions/{session_id}/results/ack", headers=headers, json={
                        "generation": generation, "event_id": envelope["head"]["event_id"],
                        "ordinal": envelope["head"]["ordinal"], "expected_delivery_revision": envelope["delivery_revision"],
                    })
                self.assertEqual(failed.status_code, 503, failed.text)
                current = client.get(f"/api/local/play/sessions/{session_id}/results?generation={generation}", headers=headers).json()
                self.assertEqual(current["acked_ordinal"], envelope["acked_ordinal"])
                self.assertEqual(current["delivery_revision"], envelope["delivery_revision"])
                retried = client.post(f"/api/local/play/sessions/{session_id}/results/ack", headers=headers, json={
                    "generation": generation, "event_id": envelope["head"]["event_id"],
                    "ordinal": envelope["head"]["ordinal"], "expected_delivery_revision": envelope["delivery_revision"],
                })
                self.assertEqual(retried.status_code, 200, retried.text)
                self.assertEqual(retried.json()["acked_ordinal"], 1)
            finally:
                client.close()
                runtime.close()

    def test_two_independent_writers_ack_same_head_only_once(self):
        with tempfile.TemporaryDirectory(prefix="nrnf-c1-ack-race-") as directory:
            runtime = create_local_runtime(Path(directory) / "data")
            headers = {"X-Local-Capability": runtime.capability}
            try:
                generation = self._build_completed(runtime)
                resume = TestClient(runtime.app).get("/api/local/play", headers=headers).json()["result_resume"]
                session_id = resume["session_id"]
                first = TestClient(runtime.app).get(f"/api/local/play/sessions/{session_id}/results?generation={generation}", headers=headers).json()
                body = {"generation": generation, "event_id": first["head"]["event_id"], "ordinal": 1,
                        "expected_delivery_revision": first["delivery_revision"]}

                def ack_once(_):
                    with TestClient(runtime.app) as client:
                        return client.post(f"/api/local/play/sessions/{session_id}/results/ack", headers=headers, json=body)

                with ThreadPoolExecutor(max_workers=2) as executor:
                    responses = list(executor.map(ack_once, range(2)))
                self.assertEqual([response.status_code for response in responses], [200, 200])
                current = TestClient(runtime.app).get(f"/api/local/play/sessions/{session_id}/results?generation={generation}", headers=headers).json()
                self.assertEqual(current["acked_ordinal"], 1)
                self.assertEqual(current["delivery_revision"], first["delivery_revision"] + 1)
            finally:
                runtime.close()

    def test_missing_last_delivery_entry_is_rejected_by_get_and_generation_gate(self):
        with tempfile.TemporaryDirectory(prefix="nrnf-c1-missing-entry-") as directory:
            runtime = create_local_runtime(Path(directory) / "data")
            client = TestClient(runtime.app)
            headers = {"X-Local-Capability": runtime.capability}
            try:
                generation = self._build_completed(runtime)
                resume = client.get("/api/local/play", headers=headers).json()["result_resume"]
                session_id = resume["session_id"]
                with runtime.session_factory.begin() as db:
                    db.execute(delete(GameResultDeliveryEntry).where(
                        GameResultDeliveryEntry.session_id == session_id,
                        GameResultDeliveryEntry.ordinal == 2,
                    ))
                response = client.get(f"/api/local/play/sessions/{session_id}/results?generation={generation}", headers=headers)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(response.json()["detail"]["code"], "result_delivery_invalid")
                candidates = client.get("/api/local/play/roster-candidates", headers=headers).json()
                blocked = client.post("/api/game/sessions", headers=headers, json={
                    "generation": generation, "cpu_character_ids": [item["id"] for item in candidates[:3]],
                })
                self.assertEqual(blocked.status_code, 503, blocked.text)
                self.assertEqual(blocked.json()["detail"]["code"], "result_delivery_invalid")
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
