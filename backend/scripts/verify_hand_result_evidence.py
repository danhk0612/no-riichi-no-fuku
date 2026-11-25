"""Read-only check of packaged W09-B2 facts and W09-C1 delivery left by renderer smoke."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

def main(database: Path, output: Path) -> None:
    uri = f"{database.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        if version != "20261030_0014":
            raise RuntimeError(f"unexpected packaged database revision: {version}")
        sessions = connection.execute(
            "SELECT id, status, hand_results_version, result_delivery_version, players, scores, ranks, "
            "settlement, presentation FROM game_sessions "
            "WHERE status='completed' AND hand_results_version=1 AND result_delivery_version=1 ORDER BY updated_at DESC"
        ).fetchall()
        if not sessions:
            raise RuntimeError("packaged renderer smoke left no completed marker-1 match")
        verified = []
        for session in sessions:
            rows = connection.execute(
                "SELECT sequence, hand_start_log_offset, hand_end_log_offset, "
                "source_action_version, payload FROM game_hand_results "
                "WHERE session_id=? ORDER BY sequence", (session["id"],)
            ).fetchall()
            if not rows or [row["sequence"] for row in rows] != list(range(1, len(rows) + 1)):
                raise RuntimeError("completed match has missing or non-contiguous hand rows")
            summaries = []
            for index, row in enumerate(rows):
                payload = json.loads(row["payload"])
                if payload.get("version") != 1 or payload.get("terminal") is not (index == len(rows) - 1):
                    raise RuntimeError("hand payload version or terminal marker is invalid")
                participants = payload.get("participants")
                if not isinstance(participants, list) or len(participants) != 4:
                    raise RuntimeError("participant snapshot is incomplete")
                for seat, participant in enumerate(participants):
                    if participant.get("seat") != seat:
                        raise RuntimeError("participant seats are not in canonical order")
                    stage = participant.get("stage_at_hand")
                    if stage is not None and (type(stage) is not int or not 0 <= stage <= 3):
                        raise RuntimeError("participant stage snapshot is invalid")
                if "tehais" in json.dumps(payload, ensure_ascii=False):
                    raise RuntimeError("hidden hand contents leaked into persisted payload")
                summaries.append({
                    "sequence": row["sequence"],
                    "start_log_offset": row["hand_start_log_offset"],
                    "end_log_offset": row["hand_end_log_offset"],
                    "source_action_version": row["source_action_version"],
                    "outcome": payload.get("outcome"),
                    "participant_stages": [p.get("stage_at_hand") for p in participants],
                    "terminal": payload["terminal"],
                    "payload_sha256": hashlib.sha256(row["payload"].encode("utf-8")).hexdigest(),
                })
            delivery = connection.execute(
                "SELECT generation, version, content_mode, acked_ordinal, revision, terminal_ordinal "
                "FROM game_result_deliveries WHERE session_id=?", (session["id"],)
            ).fetchone()
            entries = connection.execute(
                "SELECT ordinal, event_id, kind, hand_start_log_offset, display_index, payload "
                "FROM game_result_delivery_entries WHERE session_id=? ORDER BY ordinal", (session["id"],)
            ).fetchall()
            if (delivery is None or delivery["version"] != 1 or delivery["content_mode"] != "unbound"
                    or delivery["terminal_ordinal"] != len(entries) or not entries
                    or [row["ordinal"] for row in entries] != list(range(1, len(entries) + 1))
                    or entries[-1]["kind"] != "settlement"
                    or delivery["acked_ordinal"] != delivery["terminal_ordinal"] - 1):
                raise RuntimeError("packaged renderer did not leave every hand acknowledged and settlement pending")
            settlement_payload = json.loads(entries[-1]["payload"])
            if (settlement_payload.get("participants") != json.loads(session["players"])
                    or settlement_payload.get("scores") != json.loads(session["scores"])
                    or settlement_payload.get("ranks") != json.loads(session["ranks"])
                    or settlement_payload.get("settlement") != json.loads(session["settlement"])
                    or settlement_payload.get("presentation") != json.loads(session["presentation"])):
                raise RuntimeError("packaged settlement entry differs from saved participant/result snapshots")
            hand_entries = [row for row in entries if row["kind"] == "hand"]
            expected_hands = 0
            for fact in rows:
                fact_payload = json.loads(fact["payload"])
                winner_offsets = [winner["hora_log_offset"] for winner in fact_payload["winners"]]
                expected_count = max(1, len(winner_offsets))
                selected = [row for row in hand_entries if row["hand_start_log_offset"] == fact["hand_start_log_offset"]]
                if len(selected) != expected_count or [row["display_index"] for row in selected] != list(range(expected_count)):
                    raise RuntimeError("packaged result entries do not fully correspond to source hand facts")
                display_order = [json.loads(row["payload"])["winner_display_order"] for row in selected]
                if any(order != display_order[0] for order in display_order) or sorted(display_order[0]) != sorted(winner_offsets):
                    raise RuntimeError("packaged winner display order is not a complete saved permutation")
                expected_hands += expected_count
            if len(hand_entries) != expected_hands:
                raise RuntimeError("packaged result delivery has extra hand entries")
            verified.append({
                "session_id": session["id"], "rows": summaries,
                "delivery": {
                    "generation": delivery["generation"], "version": delivery["version"],
                    "content_mode": delivery["content_mode"], "acked_ordinal": delivery["acked_ordinal"],
                    "revision": delivery["revision"], "terminal_ordinal": delivery["terminal_ordinal"],
                    "entries": [{
                        "ordinal": row["ordinal"], "event_id": row["event_id"], "kind": row["kind"],
                        "hand_start_log_offset": row["hand_start_log_offset"],
                        "display_index": row["display_index"],
                        "payload_sha256": hashlib.sha256(row["payload"].encode("utf-8")).hexdigest(),
                    } for row in entries],
                },
            })
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({
            "database_revision": version,
            "database_open_mode": "read-only",
            "verified_completed_sessions": verified,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    finally:
        connection.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_hand_result_evidence.py <game.db> <evidence.json>")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
