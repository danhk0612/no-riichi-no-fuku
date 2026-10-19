"""Read-only check of packaged W09-B2 rows left by the renderer smoke match."""
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
        if version != "20261019_0012":
            raise RuntimeError(f"unexpected packaged database revision: {version}")
        sessions = connection.execute(
            "SELECT id, status, hand_results_version FROM game_sessions "
            "WHERE status='completed' AND hand_results_version=1 ORDER BY updated_at DESC"
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
            verified.append({"session_id": session["id"], "rows": summaries})
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
