from __future__ import annotations

import random
from copy import deepcopy
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    GameHandResult,
    GameResultDelivery,
    GameResultDeliveryEntry,
    GameSessionRecord,
    LocalPlayState,
)
from app.services.hand_results import load_rows


class ResultDeliveryError(RuntimeError):
    pass


def create_delivery(db: Session, record: GameSessionRecord) -> GameResultDelivery:
    if record.result_delivery_version != 1 or record.hand_results_version != 1:
        raise ResultDeliveryError("C1 delivery requires version 1 local hand facts")
    if not isinstance(record.play_generation, str):
        raise ResultDeliveryError("C1 delivery generation is missing")
    delivery = GameResultDelivery(
        session_id=record.id, generation=record.play_generation, version=1,
        content_mode="unbound", acked_ordinal=0, revision=0, terminal_ordinal=None,
    )
    db.add(delivery)
    db.flush()
    return delivery


def append_hand_entries(
    db: Session, record: GameSessionRecord, facts: list[GameHandResult]
) -> None:
    delivery = _required_delivery(db, record)
    if delivery.terminal_ordinal is not None:
        raise ResultDeliveryError("hand result cannot be appended after terminal delivery")
    all_entries = _entries(db, record.id)
    if [entry.ordinal for entry in all_entries] != list(range(1, len(all_entries) + 1)):
        raise ResultDeliveryError("result delivery ordinals are not contiguous")
    existing_hands = {(entry.hand_start_log_offset, entry.display_index): entry for entry in all_entries if entry.kind == "hand"}
    added = False
    for fact in facts:
        if not isinstance(fact.payload, dict):
            raise ResultDeliveryError("hand fact payload is invalid")
        winners = fact.payload.get("winners")
        if not isinstance(winners, list) or any(not isinstance(winner, dict) or type(winner.get("hora_log_offset")) is not int for winner in winners):
            raise ResultDeliveryError("hand winner snapshot is invalid")
        offsets = [winner["hora_log_offset"] for winner in winners]
        if len(offsets) != len(set(offsets)):
            raise ResultDeliveryError("hand winner offsets are duplicated")
        persisted_for_hand = [entry for entry in existing_hands.values() if entry.hand_start_log_offset == fact.hand_start_log_offset]
        if persisted_for_hand:
            persisted_for_hand.sort(key=lambda entry: entry.display_index if entry.display_index is not None else -1)
            if [entry.display_index for entry in persisted_for_hand] != list(range(max(1, len(offsets)))):
                raise ResultDeliveryError("hand result delivery is only partially present")
            first_payload = persisted_for_hand[0].payload
            order = deepcopy(first_payload.get("winner_display_order")) if isinstance(first_payload, dict) else None
            if not isinstance(order, list):
                raise ResultDeliveryError("existing hand result display order is invalid")
        else:
            order = list(offsets)
            random.SystemRandom().shuffle(order)
        display_order: list[int | None] = order if order else [None]
        for display_index, displayed_hora in enumerate(display_order):
            identity = (fact.hand_start_log_offset, display_index)
            existing = existing_hands.get(identity)
            payload = {
                "version": 1,
                "kind": "hand",
                "fact_sequence": fact.sequence,
                "hand_start_log_offset": fact.hand_start_log_offset,
                "hand_end_log_offset": fact.hand_end_log_offset,
                "source_action_version": fact.source_action_version,
                "fact_snapshot": deepcopy(fact.payload),
                "winner_display_order": order,
                "display_index": display_index,
                "displayed_hora_log_offset": displayed_hora,
                "content_mode": "unbound",
            }
            if existing is not None:
                if existing.payload != payload:
                    raise ResultDeliveryError("existing result delivery entry conflicts with hand fact")
                continue
            if persisted_for_hand:
                raise ResultDeliveryError("hand result delivery is only partially present")
            ordinal = len(all_entries) + 1
            entry = GameResultDeliveryEntry(
                session_id=record.id, ordinal=ordinal, event_id=str(uuid4()), kind="hand",
                hand_start_log_offset=fact.hand_start_log_offset,
                display_index=display_index, payload=payload,
            )
            db.add(entry)
            all_entries.append(entry)
            existing_hands[identity] = entry
            added = True
    if added:
        delivery.revision += 1
        db.flush()


def append_settlement_entry(db: Session, record: GameSessionRecord) -> None:
    delivery = _required_delivery(db, record)
    if record.status != "completed" or record.scores is None or record.ranks is None or record.settlement is None:
        raise ResultDeliveryError("settlement snapshot is incomplete")
    entries = _entries(db, record.id)
    if delivery.terminal_ordinal is not None or any(entry.kind == "settlement" for entry in entries):
        raise ResultDeliveryError("settlement result delivery already exists")
    ordinal = len(entries) + 1
    db.add(GameResultDeliveryEntry(
        session_id=record.id, ordinal=ordinal, event_id=str(uuid4()), kind="settlement",
        hand_start_log_offset=None, display_index=None,
        payload={
            "version": 1, "kind": "settlement", "scores": deepcopy(record.scores),
            "ranks": deepcopy(record.ranks), "settlement": deepcopy(record.settlement),
            "presentation": deepcopy(record.presentation), "participants": deepcopy(record.players),
            "content_mode": "unbound",
        },
    ))
    delivery.terminal_ordinal = ordinal
    delivery.revision += 1
    db.flush()


def result_envelope(db: Session, record: GameSessionRecord) -> dict[str, object]:
    delivery = _validated(db, record)
    entries = _entries(db, record.id)
    head_entry = entries[delivery.acked_ordinal] if delivery.acked_ordinal < len(entries) else None
    state = db.get(LocalPlayState, record.user_id)
    if head_entry is not None:
        route = "result"
    elif record.status == "active" and delivery.terminal_ordinal is None:
        route = "settlement_wait" if record.status == "active" and _terminal_hand_pending(db, record) else "human_turn"
    elif record.status == "completed":
        if delivery.terminal_ordinal is None:
            route = "settlement_wait"
        elif state is not None and state.generation == delivery.generation and state.phase == "ending_pending":
            route = "ending"
        else:
            route = "selection"
    else:
        raise ResultDeliveryError("result delivery parent status is invalid")
    action_version = len(record.human_action_indices) if route == "human_turn" else None
    return {
        "version": 1,
        "generation": delivery.generation,
        "session_id": record.id,
        "delivery_revision": delivery.revision,
        "acked_ordinal": delivery.acked_ordinal,
        "head": None if head_entry is None else {
            "ordinal": head_entry.ordinal, "event_id": head_entry.event_id,
            "kind": head_entry.kind, "payload": deepcopy(head_entry.payload),
        },
        "terminal_ordinal": delivery.terminal_ordinal,
        "route": route,
        "action_version": action_version,
    }


def acknowledge_result(
    db: Session,
    record: GameSessionRecord,
    *,
    generation: str,
    event_id: str,
    ordinal: int,
    expected_revision: int,
) -> dict[str, object]:
    delivery = _validated(db, record)
    if generation != delivery.generation or generation != record.play_generation:
        raise ResultDeliveryError("play_generation_stale")
    entries = _entries(db, record.id)
    if ordinal <= delivery.acked_ordinal:
        if ordinal >= 1 and ordinal <= len(entries):
            previous = entries[ordinal - 1]
            if previous.ordinal == ordinal and previous.event_id == event_id:
                return result_envelope(db, record)
        raise ResultDeliveryError("result_ack_conflict")
    if ordinal != delivery.acked_ordinal + 1 or ordinal > len(entries):
        raise ResultDeliveryError("result_ack_conflict")
    current = entries[ordinal - 1]
    if current.event_id != event_id or expected_revision != delivery.revision:
        raise ResultDeliveryError("result_ack_conflict")
    delivery.acked_ordinal += 1
    delivery.revision += 1
    db.flush()
    return result_envelope(db, record)


def unresolved_generation_sessions(db: Session, user_id: int, generation: str) -> list[GameSessionRecord]:
    records = list(db.scalars(select(GameSessionRecord).where(
        GameSessionRecord.user_id == user_id,
        GameSessionRecord.play_generation == generation,
        GameSessionRecord.result_delivery_version == 1,
        GameSessionRecord.status != "cancelled",
    ).order_by(GameSessionRecord.created_at, GameSessionRecord.id)))
    unresolved = []
    for record in records:
        delivery = db.get(GameResultDelivery, record.id)
        if delivery is None:
            raise ResultDeliveryError("result delivery state is missing")
        _validated(db, record)
        entries = _entries(db, record.id)
        if delivery.acked_ordinal < len(entries) or delivery.terminal_ordinal is None:
            unresolved.append(record)
    return unresolved


def assert_action_delivery_clear(db: Session, record: GameSessionRecord) -> None:
    if record.result_delivery_version != 1:
        return
    delivery = _validated(db, record)
    if delivery.acked_ordinal < len(_entries(db, record.id)) or _terminal_hand_pending(db, record):
        raise ResultDeliveryError("result_pending")


def assert_generation_delivery_clear(db: Session, user_id: int, generation: str) -> None:
    if unresolved_generation_sessions(db, user_id, generation):
        raise ResultDeliveryError("result_pending")


def _required_delivery(db: Session, record: GameSessionRecord) -> GameResultDelivery:
    if record.result_delivery_version != 1 or record.hand_results_version != 1 or record.play_generation is None:
        raise ResultDeliveryError("session is not opted into result delivery")
    delivery = db.get(GameResultDelivery, record.id)
    if delivery is None:
        raise ResultDeliveryError("result delivery state is missing")
    if delivery.generation != record.play_generation or delivery.version != 1 or delivery.content_mode != "unbound":
        raise ResultDeliveryError("result delivery state does not match its session")
    return delivery


def _entries(db: Session, session_id: str) -> list[GameResultDeliveryEntry]:
    return list(db.scalars(select(GameResultDeliveryEntry).where(
        GameResultDeliveryEntry.session_id == session_id
    ).order_by(GameResultDeliveryEntry.ordinal)))


def _validated(db: Session, record: GameSessionRecord) -> GameResultDelivery:
    delivery = _required_delivery(db, record)
    entries = _entries(db, record.id)
    facts = load_rows(db, record)
    if [entry.ordinal for entry in entries] != list(range(1, len(entries) + 1)):
        raise ResultDeliveryError("result delivery entries are missing or non-contiguous")
    if type(delivery.acked_ordinal) is not int or not 0 <= delivery.acked_ordinal <= len(entries):
        raise ResultDeliveryError("result delivery cursor is invalid")
    if type(delivery.revision) is not int or delivery.revision < 0:
        raise ResultDeliveryError("result delivery revision is invalid")
    if ([fact.sequence for fact in facts] != list(range(1, len(facts) + 1))
            or [fact.hand_start_log_offset for fact in facts] != sorted({fact.hand_start_log_offset for fact in facts})
            or any(fact.hand_end_log_offset <= fact.hand_start_log_offset or fact.source_action_version < 0 for fact in facts)):
        raise ResultDeliveryError("source hand fact ordering or identity is invalid")
    expected_index = 0
    for fact in facts:
        fact_keys = {"version", "generation", "start", "participants", "outcome", "winners", "draws", "engine_scores_after_step", "terminal"}
        if not isinstance(fact.payload, dict) or set(fact.payload) != fact_keys or fact.payload.get("version") != 1:
            raise ResultDeliveryError("hand result fact version is unknown")
        winners = fact.payload.get("winners")
        if not isinstance(winners, list) or any(not isinstance(w, dict) or type(w.get("hora_log_offset")) is not int for w in winners):
            raise ResultDeliveryError("hand result winners are invalid")
        winner_offsets = [w["hora_log_offset"] for w in winners]
        expected_count = max(1, len(winner_offsets))
        hand_entries = entries[expected_index:expected_index + expected_count]
        if len(hand_entries) != expected_count:
            raise ResultDeliveryError("hand result delivery is incomplete")
        order: object = None
        for display_index, entry in enumerate(hand_entries):
            payload = entry.payload
            payload_keys = {
                "version", "kind", "fact_sequence", "hand_start_log_offset", "hand_end_log_offset",
                "source_action_version", "fact_snapshot", "winner_display_order", "display_index",
                "displayed_hora_log_offset", "content_mode",
            }
            if (entry.kind != "hand" or entry.hand_start_log_offset != fact.hand_start_log_offset
                    or entry.display_index != display_index or not isinstance(payload, dict) or set(payload) != payload_keys
                    or payload.get("version") != 1 or payload.get("kind") != "hand"
                    or payload.get("fact_sequence") != fact.sequence
                    or payload.get("hand_start_log_offset") != fact.hand_start_log_offset
                    or payload.get("hand_end_log_offset") != fact.hand_end_log_offset
                    or payload.get("source_action_version") != fact.source_action_version
                    or payload.get("fact_snapshot") != fact.payload
                    or payload.get("display_index") != display_index
                    or payload.get("content_mode") != "unbound"):
                raise ResultDeliveryError("hand result delivery differs from its source fact")
            if order is None:
                order = payload.get("winner_display_order")
            elif order != payload.get("winner_display_order"):
                raise ResultDeliveryError("winner display order differs within a hand")
        expected_order = order
        if (not isinstance(expected_order, list) or any(type(offset) is not int for offset in expected_order)
                or len(expected_order) != len(winner_offsets)
                or sorted(expected_order) != sorted(winner_offsets)
                or len(set(expected_order)) != len(expected_order)):
            raise ResultDeliveryError("winner display order is not a complete permutation")
        for display_index, entry in enumerate(hand_entries):
            shown = expected_order[display_index] if winner_offsets else None
            if entry.payload.get("displayed_hora_log_offset") != shown:
                raise ResultDeliveryError("displayed winner does not match the stored order")
        expected_index += expected_count
    if record.status == "completed":
        if (not facts or facts[-1].payload.get("terminal") is not True
                or any(f.payload.get("terminal") is not False for f in facts[:-1])):
            raise ResultDeliveryError("terminal hand facts are invalid")
    elif record.status == "active":
        if any(f.payload.get("terminal") is not False for f in facts[:-1]):
            raise ResultDeliveryError("terminal hand facts are invalid")
        if facts and facts[-1].payload.get("terminal") not in (True, False):
            raise ResultDeliveryError("terminal hand facts are invalid")
    if not facts and record.status == "completed":
        raise ResultDeliveryError("completed delivery has no terminal hand facts")
    for entry in entries:
        try:
            UUID(entry.event_id)
        except (ValueError, TypeError, AttributeError):
            raise ResultDeliveryError("result delivery event identity is invalid") from None
    trailing = entries[expected_index:]
    if record.status == "active":
        if trailing or delivery.terminal_ordinal is not None:
            raise ResultDeliveryError("active result delivery contains a settlement")
    elif record.status == "completed":
        if (len(trailing) != 1 or trailing[0].kind != "settlement"
                or delivery.terminal_ordinal != len(entries)
                or trailing[0].ordinal != delivery.terminal_ordinal):
            raise ResultDeliveryError("completed result delivery settlement is missing")
        expected_settlement = {
            "version": 1, "kind": "settlement", "scores": record.scores,
            "ranks": record.ranks, "settlement": record.settlement,
            "presentation": record.presentation, "participants": record.players,
            "content_mode": "unbound",
        }
        if trailing[0].payload != expected_settlement:
            raise ResultDeliveryError("settlement entry differs from completed session snapshot")
    else:
        raise ResultDeliveryError("result delivery status is invalid")
    if delivery.acked_ordinal > 0 and entries[delivery.acked_ordinal - 1].ordinal != delivery.acked_ordinal:
        raise ResultDeliveryError("acknowledged result prefix is invalid")
    return delivery


def _terminal_hand_pending(db: Session, record: GameSessionRecord) -> bool:
    facts = load_rows(db, record)
    return bool(facts and facts[-1].payload.get("terminal") is True)
