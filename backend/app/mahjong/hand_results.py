"""Capture immutable, source-ordered facts for completed MJAI hands."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.mahjong.hand_scores import HandScoreCaptureError, HandWin


class HandResultCaptureError(HandScoreCaptureError):
    """The authoritative log cannot be converted into a complete hand fact."""


@dataclass(frozen=True)
class HandResultFact:
    start_log_offset: int
    end_log_offset: int
    payload: dict[str, object]


def _ints(values: object, label: str) -> list[int]:
    if not isinstance(values, (list, tuple)) or len(values) != 4 or any(type(v) is not int for v in values):
        raise HandResultCaptureError(f"{label} must contain four integer seats")
    return list(values)


def _copy_start(event: Mapping[str, Any]) -> dict[str, object]:
    keys = ("bakaze", "kyoku", "honba", "oya", "kyotaku")
    if any(key not in event for key in keys):
        raise HandResultCaptureError("start_kyoku is missing required fields")
    if not isinstance(event["bakaze"], str) or any(type(event[key]) is not int for key in keys[1:]):
        raise HandResultCaptureError("start_kyoku fields have invalid types")
    return {**{key: event[key] for key in keys}, "scores": _ints(event.get("scores"), "start scores")}


def _hora_facts(event: Mapping[str, Any], offset: int, win: HandWin) -> dict[str, object]:
    if win.hora_offset != offset or win.hand_start_offset < 0:
        raise HandResultCaptureError("hora offset does not match B1 score capture")
    try:
        actor, target = event["actor"], event["target"]
        deltas = _ints(event["deltas"], "hora deltas")
        ura = event.get("ura_markers", [])
    except (KeyError, TypeError) as error:
        raise HandResultCaptureError("hora event is incomplete") from error
    if type(actor) is not int or type(target) is not int or actor != win.actor or target != win.target:
        raise HandResultCaptureError("hora identity differs from B1 score capture")
    if tuple(deltas) != win.deltas or not isinstance(ura, (list, tuple)) or tuple(ura) != win.ura_markers:
        raise HandResultCaptureError("hora payment or ura differs from B1 score capture")
    score = win.score
    return {
        "hora_log_offset": offset,
        "actor": actor,
        "target": target,
        "win_kind": "tsumo" if target == actor else "ron",
        "deltas": deltas,
        "ura_markers": list(ura),
        "score": {
            "han": score.han, "fu": score.fu, "yakuman": score.yakuman,
            "yaku": list(score.yaku), "ron_agari": score.ron_agari,
            "tsumo_agari_oya": score.tsumo_agari_oya,
            "tsumo_agari_ko": score.tsumo_agari_ko,
            "pao_payer": score.pao_payer, "band": score.band,
        },
    }


class HandResultCollector:
    """Consumes the authoritative append-only MJAI log by absolute offset."""

    def __init__(self) -> None:
        self._cursor = 0
        self._prefix: list[object] = []
        self._current: dict[str, object] | None = None
        self._pending: list[HandResultFact] = []

    def consume(
        self,
        log: list[dict[str, object]],
        wins: tuple[HandWin, ...],
        engine_scores: tuple[int, int, int, int],
        terminal: bool,
    ) -> None:
        if len(log) < self._cursor or log[:self._cursor] != self._prefix:
            raise HandResultCaptureError("MJAI log prefix changed or became shorter")
        win_by_offset = {win.hora_offset: win for win in wins}
        if len(win_by_offset) != len(wins):
            raise HandResultCaptureError("B1 score capture contains duplicate hora offsets")
        suffix_horas: set[int] = set()
        closed_this_step: list[int] = []
        for offset in range(self._cursor, len(log)):
            event = log[offset]
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise HandResultCaptureError("MJAI log event is invalid")
            kind = event["type"]
            if kind == "start_kyoku":
                if self._current is not None:
                    raise HandResultCaptureError("new hand started before previous end_kyoku")
                self._current = {"start": _copy_start(event), "start_offset": offset, "winners": [], "draws": []}
            elif kind == "hora":
                if self._current is None or offset not in win_by_offset:
                    raise HandResultCaptureError("hora has no matching current hand or B1 score")
                win = win_by_offset[offset]
                if win.hand_start_offset != self._current["start_offset"]:
                    raise HandResultCaptureError("B1 hand identity differs from start_kyoku offset")
                self._current["winners"].append(_hora_facts(event, offset, win))
                suffix_horas.add(offset)
            elif kind == "ryukyoku":
                if self._current is None:
                    raise HandResultCaptureError("ryukyoku has no active hand")
                reason = event.get("reason")
                if reason is not None and not isinstance(reason, str):
                    raise HandResultCaptureError("ryukyoku reason is invalid")
                self._current["draws"].append({
                    "log_offset": offset,
                    "reason": reason,
                    "deltas": _ints(event.get("deltas"), "ryukyoku deltas"),
                })
            elif kind == "end_kyoku":
                if self._current is None:
                    raise HandResultCaptureError("end_kyoku has no active hand")
                winners = self._current["winners"]
                draws = self._current["draws"]
                outcome = "mixed" if winners and draws else ("win" if winners else "draw")
                self._pending.append(HandResultFact(
                    start_log_offset=int(self._current["start_offset"]),
                    end_log_offset=offset,
                    payload={
                        "version": 1,
                        "start": self._current["start"],
                        "outcome": outcome,
                        "winners": winners,
                        "draws": draws,
                        "engine_scores_after_step": _ints(engine_scores, "engine scores"),
                        "terminal": False,
                    },
                ))
                closed_this_step.append(len(self._pending) - 1)
                self._current = None
            elif kind == "end_game" and closed_this_step:
                index = closed_this_step[-1]
                fact = self._pending[index]
                payload = dict(fact.payload)
                payload["terminal"] = True
                self._pending[index] = HandResultFact(fact.start_log_offset, fact.end_log_offset, payload)
        if suffix_horas != set(win_by_offset):
            raise HandResultCaptureError("B1 score capture and MJAI hora offsets differ")
        self._cursor = len(log)
        self._prefix = list(log)
        if terminal and not (closed_this_step and self._pending[closed_this_step[-1]].payload["terminal"]):
            raise HandResultCaptureError("terminal match did not close its final hand")

    def drain(self) -> tuple[HandResultFact, ...]:
        result = tuple(self._pending)
        self._pending.clear()
        return result
