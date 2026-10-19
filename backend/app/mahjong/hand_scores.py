"""Preserve 0.4.8 WinResult before next-round initialization clears it.

Only the clone receives artificial scores. The original remains the sole source
of match progression, payments and settlement. See spikes/w09-a2-hand-score.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping

from riichienv import Action, RiichiEnv, WinResult, calculate_score


class HandScoreCaptureError(RuntimeError):
    """The score copy cannot be matched to the authoritative winning step."""


@dataclass(frozen=True)
class HandScore:
    han: int
    fu: int
    yakuman: bool
    yaku: tuple[int, ...]
    ron_agari: int
    tsumo_agari_oya: int
    tsumo_agari_ko: int
    pao_payer: int | None
    band: int


@dataclass(frozen=True)
class HandWin:
    hand_start_offset: int
    hora_offset: int
    actor: int
    target: int
    deltas: tuple[int, ...]
    ura_markers: tuple[str, ...]
    score: HandScore


def _score(result: WinResult) -> HandScore:
    if not result.is_win:
        raise HandScoreCaptureError("winning result is missing")
    # Grade excludes honba/kyotaku and dealer multipliers, never inferred from deltas.
    base_ron = calculate_score(result.han, result.fu, False, False, 0).pay_ron
    if result.yakuman or base_ron >= 16000:
        band = 3
    elif base_ron >= 8000:
        band = 2
    else:
        band = 1
    return HandScore(
        han=result.han, fu=result.fu, yakuman=result.yakuman,
        yaku=tuple(result.yaku), ron_agari=result.ron_agari,
        tsumo_agari_oya=result.tsumo_agari_oya,
        tsumo_agari_ko=result.tsumo_agari_ko,
        pao_payer=result.pao_payer, band=band,
    )


def _hora_events(log: list[dict], offset: int) -> tuple[str, ...]:
    return tuple(json.dumps(e, sort_keys=True) for e in log[offset:] if e["type"] == "hora")


@dataclass(frozen=True)
class CapturedHandScores:
    source_offset: int
    expected_horas: tuple[str, ...]
    wins: tuple[HandWin, ...]

    def verify(self, original: RiichiEnv) -> tuple[HandWin, ...]:
        if _hora_events(original.mjai_log, self.source_offset) != self.expected_horas:
            raise HandScoreCaptureError("clone and original hora events differ")
        live = original.win_results
        if live and {seat: _score(value) for seat, value in live.items()} != {
            win.actor: win.score for win in self.wins
        }:
            raise HandScoreCaptureError("clone and final live scores differ")
        return self.wins


def capture_hand_scores(env: RiichiEnv, actions: Mapping[int, Action]) -> CapturedHandScores:
    """Called only after legal validation of an already chosen winning action map."""
    log = env.mjai_log
    offset = len(log)
    starts = [i for i, event in enumerate(log) if event["type"] == "start_kyoku"]
    if not starts:
        raise HandScoreCaptureError("winning hand has no start offset")
    clone = env.clone()
    clone.set_scores([-1_000_000] * 4)
    clone.step(dict(actions))
    clone_log = clone.mjai_log
    horas = [
        (i, event) for i, event in enumerate(clone_log[offset:], offset)
        if event["type"] == "hora"
    ]
    results = clone.win_results
    actors = [event["actor"] for _, event in horas]
    if len(set(actors)) != len(actors) or set(actors) != set(results):
        raise HandScoreCaptureError("clone winner/result identities differ")
    if horas and not clone.done():
        raise HandScoreCaptureError("clone cleared the winning hand")
    wins = tuple(HandWin(
        hand_start_offset=starts[-1], hora_offset=i,
        actor=event["actor"], target=event["target"],
        deltas=tuple(event["deltas"]), ura_markers=tuple(event.get("ura_markers", ())),
        score=_score(results[event["actor"]]),
    ) for i, event in horas)
    return CapturedHandScores(offset, _hora_events(clone_log, offset), wins)
