from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.db.models import (
    CharacterPromptCandidateEntry, CharacterPromptCandidates,
    SharedPromptDefault, SharedPromptItem,
)
from app.local_runtime import create_local_runtime


class SharedPromptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="nrnf-shared-prompts-")
        self.root = Path(self.temp.name) / "자료"
        self.runtime = create_local_runtime(self.root)
        self.client = TestClient(self.runtime.app)
        self.headers = {"X-Local-Capability": self.runtime.capability}

    def tearDown(self):
        self.client.close()
        self.runtime.close()
        self.temp.cleanup()

    def create(self, label="공유 임시 항목", level=0, kind="clothing_state", positive="  P\n<lora:test:0.8>  ", negative=""):
        response = self.client.post("/api/local/shared-prompts", headers=self.headers, json={
            "kind": kind, "level": level, "label": label,
            "positive": positive, "negative": negative,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_get_is_read_only_empty_defaults_and_strict_filters(self):
        path = "/api/local/shared-prompts?kind=pose&level=3"
        self.assertEqual(self.client.get(path).status_code, 401)
        with self.runtime.session_factory() as session:
            before = session.scalar(select(func.count()).select_from(SharedPromptDefault))
            self.assertEqual(before, 0)
        self.assertEqual(self.client.get(path, headers=self.headers).json(), {"items": []})
        self.assertEqual(self.client.get("/api/local/shared-prompts?kind=pose", headers=self.headers).status_code, 422)
        self.assertEqual(self.client.get("/api/local/shared-prompts?kind=bad&level=0", headers=self.headers).status_code, 422)
        default = self.client.get("/api/local/shared-prompt-defaults/3/pose", headers=self.headers).json()
        self.assertEqual((default["revision"], default["item_id"], default["valid"]), (0, None, False))
        no_change = self.client.put("/api/local/shared-prompt-defaults/3/pose", headers=self.headers, json={"expected_revision": 0, "item_id": None})
        self.assertEqual(no_change.json()["revision"], 0)
        candidates = self.client.get("/api/local/characters/1/prompt-candidates/3/pose", headers=self.headers).json()
        self.assertEqual((candidates["revision"], candidates["effective_items"], candidates["uses_default"], candidates["unregistered"]), (0, [], True, True))
        with self.runtime.session_factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(SharedPromptDefault)), 0)
            self.assertEqual(session.scalar(select(func.count()).select_from(CharacterPromptCandidates)), 0)

    def test_item_source_text_empty_values_and_revision_conflict(self):
        item = self.create()
        self.assertEqual(item["positive"], "  P\n<lora:test:0.8>  ")
        self.assertEqual(item["negative"], "")
        saved = self.client.patch(f"/api/local/shared-prompts/{item['id']}", headers=self.headers, json={
            "expected_revision": 1, "positive": "", "negative": "  N\nkeep  ",
        })
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual((saved.json()["positive"], saved.json()["negative"], saved.json()["revision"]), ("", "  N\nkeep  ", 2))
        unchanged = self.client.patch(f"/api/local/shared-prompts/{item['id']}", headers=self.headers, json={
            "expected_revision": 2, "positive": "",
        })
        self.assertEqual(unchanged.json()["revision"], 2)
        stale = self.client.patch(f"/api/local/shared-prompts/{item['id']}", headers=self.headers, json={
            "expected_revision": 1, "label": "stale",
        })
        self.assertEqual((stale.status_code, stale.json()["detail"]["code"]), (409, "revision_conflict"))
        invalid = self.client.post("/api/local/shared-prompts", headers=self.headers, json={
            "kind": "pose", "level": 4, "label": "bad", "positive": "", "negative": "",
        })
        self.assertEqual(invalid.status_code, 422)

    def test_all_eight_level_kind_scopes_are_independent(self):
        for level in range(4):
            for kind in ("clothing_state", "pose"):
                self.create(f"{kind}-{level}", level=level, kind=kind, positive=f"{kind}/{level}")
        for level in range(4):
            for kind in ("clothing_state", "pose"):
                listing = self.client.get(f"/api/local/shared-prompts?kind={kind}&level={level}", headers=self.headers)
                self.assertEqual(listing.status_code, 200, listing.text)
                self.assertEqual([(row["label"], row["positive"]) for row in listing.json()["items"]], [(f"{kind}-{level}", f"{kind}/{level}")])

    def test_candidate_first_then_default_and_scope_validation(self):
        first = self.create("first")
        second = self.create("second")
        default = self.client.put("/api/local/shared-prompt-defaults/0/clothing_state", headers=self.headers, json={
            "expected_revision": 0, "item_id": first["id"],
        })
        self.assertEqual(default.json()["revision"], 1)
        fallback = self.client.get("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers).json()
        self.assertTrue(fallback["uses_default"])
        self.assertEqual([x["id"] for x in fallback["effective_items"]], [first["id"]])
        empty = self.client.put("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers, json={
            "expected_revision": 0, "item_ids": [],
        })
        self.assertEqual(empty.json()["revision"], 0)
        fallback = self.client.get("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers).json()
        self.assertEqual(fallback["effective_items"][0]["id"], first["id"])
        explicit = self.client.put("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers, json={
            "expected_revision": 0, "item_ids": [second["id"]],
        })
        self.assertFalse(explicit.json()["uses_default"])
        self.assertEqual([x["id"] for x in explicit.json()["effective_items"]], [second["id"]])
        emptied = self.client.put("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers, json={
            "expected_revision": 1, "item_ids": [],
        })
        self.assertEqual((emptied.json()["revision"], emptied.json()["uses_default"], emptied.json()["effective_items"][0]["id"]), (2, True, first["id"]))
        bad = self.client.put("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers, json={
            "expected_revision": 2, "item_ids": [first["id"], first["id"]],
        })
        self.assertEqual((bad.status_code, bad.json()["detail"]["code"]), (422, "duplicate_candidate"))
        cross_scope = self.client.put("/api/local/characters/1/prompt-candidates/1/clothing_state", headers=self.headers, json={
            "expected_revision": 0, "item_ids": [first["id"]],
        })
        self.assertEqual(cross_scope.status_code, 422)
        unchanged_default = self.client.put("/api/local/shared-prompt-defaults/0/clothing_state", headers=self.headers, json={
            "expected_revision": 1, "item_id": first["id"],
        })
        self.assertEqual(unchanged_default.json()["revision"], 1)

    def test_same_level_move_is_rejected_without_detaching_references(self):
        item = self.create("same-level")
        self.client.put("/api/local/shared-prompt-defaults/0/clothing_state", headers=self.headers, json={
            "expected_revision": 0, "item_id": item["id"],
        })
        self.client.put("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers, json={
            "expected_revision": 0, "item_ids": [item["id"]],
        })
        preview = self.client.post(f"/api/local/shared-prompts/{item['id']}/change-preview", headers=self.headers, json={
            "expected_revision": 1, "action": "move", "target_level": 0,
        })
        self.assertEqual((preview.status_code, preview.json()["detail"]["code"]), (422, "same_level_move"))
        candidate = self.client.get("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers).json()
        default = self.client.get("/api/local/shared-prompt-defaults/0/clothing_state", headers=self.headers).json()
        self.assertEqual(candidate["stored_item_ids"], [item["id"]])
        self.assertEqual(default["item_id"], item["id"])

    def test_move_preview_confirmation_stale_guard_and_no_target_auto_attach(self):
        item = self.create("move me")
        saved = self.client.put("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers, json={
            "expected_revision": 0, "item_ids": [item["id"]],
        }).json()
        preview = self.client.post(f"/api/local/shared-prompts/{item['id']}/change-preview", headers=self.headers, json={
            "expected_revision": 1, "action": "move", "target_level": 1,
        })
        self.assertEqual(preview.status_code, 200, preview.text)
        result = preview.json()
        self.assertEqual(len(result["candidate_changes"]), 1)
        self.assertEqual(result["candidate_changes"][0]["candidate_revision"], saved["revision"])
        before = self.client.get("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers).json()
        self.assertEqual(before["stored_item_ids"], [item["id"]])
        confirm = self.client.post(f"/api/local/shared-prompts/{item['id']}/change-confirmation", headers=self.headers, json={
            "expected_revision": 1, "action": "move", "target_level": 1, "preview_digest": result["preview_digest"],
        })
        self.assertEqual(confirm.status_code, 200, confirm.text)
        self.assertEqual(confirm.json()["changed_candidate_sets"], 1)
        self.assertEqual(self.client.get("/api/local/shared-prompts?kind=clothing_state&level=1", headers=self.headers).json()["items"][0]["id"], item["id"])
        target = self.client.get("/api/local/characters/1/prompt-candidates/1/clothing_state", headers=self.headers).json()
        self.assertEqual((target["stored_item_ids"], target["effective_items"], target["unregistered"]), ([], [], True))
        old = self.client.get("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers).json()
        self.assertEqual(old["revision"], saved["revision"] + 1)

    def test_default_indirect_users_and_stale_preview_rejected(self):
        item = self.create("default", kind="pose")
        self.client.put("/api/local/shared-prompt-defaults/0/pose", headers=self.headers, json={"expected_revision": 0, "item_id": item["id"]})
        preview = self.client.post(f"/api/local/shared-prompts/{item['id']}/change-preview", headers=self.headers, json={
            "expected_revision": 1, "action": "delete",
        }).json()
        self.assertEqual(len(preview["affected_cpus"]), 6)
        self.assertTrue(all(row["reason"] == "default_reference" for row in preview["affected_cpus"]))
        self.client.put("/api/local/shared-prompt-defaults/0/pose", headers=self.headers, json={"expected_revision": 1, "item_id": None})
        stale = self.client.post(f"/api/local/shared-prompts/{item['id']}/change-confirmation", headers=self.headers, json={
            "expected_revision": 1, "action": "delete", "preview_digest": preview["preview_digest"],
        })
        self.assertEqual((stale.status_code, stale.json()["detail"]["code"]), (409, "preview_stale"))
        self.assertEqual(self.client.get("/api/local/shared-prompts?kind=pose&level=0", headers=self.headers).json()["items"][0]["active"], True)

    def test_delete_is_logical_clears_links_and_reset_restart_preserves_resources(self):
        item = self.create("remove")
        self.client.put("/api/local/shared-prompt-defaults/0/clothing_state", headers=self.headers, json={"expected_revision": 0, "item_id": item["id"]})
        self.client.put("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers, json={"expected_revision": 0, "item_ids": [item["id"]]})
        preview = self.client.post(f"/api/local/shared-prompts/{item['id']}/change-preview", headers=self.headers, json={"expected_revision": 1, "action": "delete"}).json()
        confirmed = self.client.post(f"/api/local/shared-prompts/{item['id']}/change-confirmation", headers=self.headers, json={
            "expected_revision": 1, "action": "delete", "preview_digest": preview["preview_digest"],
        })
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertFalse(confirmed.json()["item"]["active"])
        self.assertEqual(self.client.get("/api/local/shared-prompts?kind=clothing_state&level=0", headers=self.headers).json()["items"], [])
        self.assertEqual(self.client.get("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers).json()["stored_item_ids"], [])
        state = self.client.get("/api/local/play", headers=self.headers).json()
        reset = self.client.post("/api/local/play/reset", headers=self.headers, json={"generation": state["generation"], "confirm": True})
        self.assertEqual(reset.status_code, 200, reset.text)
        self.client.close(); self.runtime.close()
        self.runtime = create_local_runtime(self.root)
        self.client = TestClient(self.runtime.app)
        self.headers = {"X-Local-Capability": self.runtime.capability}
        with self.runtime.session_factory() as session:
            self.assertIsNotNone(session.get(SharedPromptItem, item["id"]))
            self.assertEqual(session.get(SharedPromptDefault, (0, "clothing_state")).item_id, None)
            candidate = session.scalar(select(CharacterPromptCandidates).where(CharacterPromptCandidates.cpu_id == 1))
            self.assertEqual(candidate.revision, 2)
            self.assertEqual(session.scalar(select(func.count()).select_from(CharacterPromptCandidateEntry).where(CharacterPromptCandidateEntry.candidate_set_id == candidate.id)), 0)

    def test_confirmation_write_failure_rolls_back_item_default_and_candidate_revisions(self):
        item = self.create("atomic")
        default = self.client.put("/api/local/shared-prompt-defaults/0/clothing_state", headers=self.headers, json={"expected_revision": 0, "item_id": item["id"]}).json()
        candidate = self.client.put("/api/local/characters/1/prompt-candidates/0/clothing_state", headers=self.headers, json={"expected_revision": 0, "item_ids": [item["id"]]}).json()
        preview = self.client.post(f"/api/local/shared-prompts/{item['id']}/change-preview", headers=self.headers, json={"expected_revision": 1, "action": "delete"}).json()
        with self.runtime.engine.begin() as connection:
            connection.execute(text("CREATE TRIGGER fail_shared_prompt_deactivate BEFORE UPDATE OF active ON shared_prompt_items WHEN NEW.active = 0 BEGIN SELECT RAISE(ABORT, 'injected commit failure'); END"))
        with self.assertRaises(Exception):
            self.client.post(f"/api/local/shared-prompts/{item['id']}/change-confirmation", headers=self.headers, json={
                "expected_revision": 1, "action": "delete", "preview_digest": preview["preview_digest"],
            })
        with self.runtime.session_factory() as session:
            saved_item = session.get(SharedPromptItem, item["id"])
            saved_default = session.get(SharedPromptDefault, (0, "clothing_state"))
            saved_candidates = session.get(CharacterPromptCandidates, candidate["candidate_set_id"]) if "candidate_set_id" in candidate else session.scalar(select(CharacterPromptCandidates).where(CharacterPromptCandidates.cpu_id == 1))
            entries = session.scalars(select(CharacterPromptCandidateEntry).where(CharacterPromptCandidateEntry.candidate_set_id == saved_candidates.id)).all()
            self.assertTrue(saved_item.active)
            self.assertEqual(saved_item.revision, 1)
            self.assertEqual((saved_default.item_id, saved_default.revision), (item["id"], default["revision"]))
            self.assertEqual((saved_candidates.revision, [entry.item_id for entry in entries]), (candidate["revision"], [item["id"]]))
