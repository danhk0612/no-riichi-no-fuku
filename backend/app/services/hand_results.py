from __future__ import annotations

from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import GameHandResult, GameSessionRecord
from app.mahjong.hand_results import HandResultCaptureError, HandResultFact


def _participants(record: GameSessionRecord) -> list[dict[str, object]]:
    choices = {seat: choice for seat, choice in enumerate(record.cpu_choices, start=1)}
    players = record.players
    if not isinstance(players, list) or len(players) != 4 or len(choices) != 3:
        raise HandResultCaptureError("saved match participants are invalid")
    result: list[dict[str, object]] = []
    for seat, player in enumerate(players):
        if not isinstance(player, dict) or player.get("seat") != seat or type(player.get("is_human")) is not bool:
            raise HandResultCaptureError("saved participant seat snapshot is invalid")
        is_human = player["is_human"]
        choice = None if is_human else choices.get(seat)
        if (seat == 0) != is_human or not isinstance(player.get("name"), str) or (not is_human and choice is None):
            raise HandResultCaptureError("saved participant snapshot is incomplete")
        cpu_id = None if choice is None else choice.get("id")
        stage = None if choice is None else choice.get("defeat_stage")
        if is_human:
            if cpu_id is not None or stage is not None:
                raise HandResultCaptureError("human participant cannot have a CPU stage snapshot")
        elif type(cpu_id) is not int or type(stage) is not int or not 0 <= stage <= 3:
            raise HandResultCaptureError("CPU participant stage snapshot is invalid")
        result.append({
            "seat": seat,
            "is_human": is_human,
            "name": player["name"],
            "cpu_id": cpu_id,
            "stage_at_hand": stage,
        })
    return result


def fact_payload(record: GameSessionRecord, fact: HandResultFact) -> dict[str, object]:
    if not isinstance(record.play_generation, str):
        raise HandResultCaptureError("version 1 match generation is missing")
    payload = deepcopy(fact.payload)
    payload["generation"] = record.play_generation
    payload["participants"] = _participants(record)
    expected = {
        "version", "generation", "start", "participants", "outcome", "winners",
        "draws", "engine_scores_after_step", "terminal",
    }
    if set(payload) != expected or payload.get("version") != 1:
        raise HandResultCaptureError("hand result payload does not match version 1 schema")
    return payload


def load_rows(db_session: Session, record: GameSessionRecord) -> list[GameHandResult]:
    return list(db_session.scalars(
        select(GameHandResult)
        .where(GameHandResult.session_id == record.id)
        .order_by(GameHandResult.sequence)
    ))


def append_facts(
    db_session: Session,
    record: GameSessionRecord,
    facts: tuple[HandResultFact, ...],
    source_action_version: int,
) -> None:
    if record.hand_results_version != 1:
        if facts:
            raise HandResultCaptureError("hand facts are disabled for this game session")
        return
    rows = load_rows(db_session, record)
    if [row.sequence for row in rows] != list(range(1, len(rows) + 1)):
        raise HandResultCaptureError("persisted hand result sequence is not contiguous")
    by_start = {row.hand_start_log_offset: row for row in rows}
    sequence_by_start = {row.hand_start_log_offset: row.sequence for row in rows}
    sequence = len(rows)
    for fact in facts:
        payload = fact_payload(record, fact)
        existing = by_start.get(fact.start_log_offset)
        if existing is not None:
            if (
                existing.sequence != sequence_by_start[fact.start_log_offset]
                or existing.hand_end_log_offset != fact.end_log_offset
                or existing.source_action_version != source_action_version
                or existing.payload != payload
            ):
                raise HandResultCaptureError("persisted hand result identity conflicts with replay")
            continue
        sequence += 1
        row = GameHandResult(
            session_id=record.id,
            hand_start_log_offset=fact.start_log_offset,
            sequence=sequence,
            hand_end_log_offset=fact.end_log_offset,
            source_action_version=source_action_version,
            payload=payload,
        )
        db_session.add(row)
        by_start[fact.start_log_offset] = row
        sequence_by_start[fact.start_log_offset] = sequence


def verify_replay_batch(
    record: GameSessionRecord,
    rows: list[GameHandResult],
    facts: tuple[HandResultFact, ...],
    source_action_version: int,
    matched: int,
) -> int:
    for fact in facts:
        if matched >= len(rows):
            raise HandResultCaptureError("replay produced an unpersisted hand result")
        row = rows[matched]
        if (
            row.sequence != matched + 1
            or row.hand_start_log_offset != fact.start_log_offset
            or row.hand_end_log_offset != fact.end_log_offset
            or row.source_action_version != source_action_version
            or row.payload != fact_payload(record, fact)
        ):
            raise HandResultCaptureError("replayed hand result differs from persisted facts")
        matched += 1
    return matched


def verify_completed_rows(rows: list[GameHandResult]) -> None:
    if not rows or [row.sequence for row in rows] != list(range(1, len(rows) + 1)):
        raise HandResultCaptureError("completed match hand result sequence is invalid")
    if any(
        not isinstance(row.payload, dict)
        or type(row.payload.get("version")) is not int
        or row.payload.get("version") != 1
        for row in rows
    ):
        raise HandResultCaptureError("completed match hand result payload version is unknown")
    if any(row.payload.get("terminal") is not False for row in rows[:-1]) or rows[-1].payload.get("terminal") is not True:
        raise HandResultCaptureError("completed match terminal hand marker is invalid")
