from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from types import MappingProxyType
from typing import Mapping

from riichienv import Action, ActionType, GameRule, Observation, RiichiEnv

from app.mahjong.hand_scores import HandScoreCaptureError, HandWin, capture_hand_scores


EXPECTED_RIICHIENV_VERSION = "0.4.8"
GAME_MODE = "4p-red-east"


class AdapterStateError(RuntimeError):
    pass


class IllegalActionError(RuntimeError):
    pass


@dataclass(frozen=True)
class MatchResult:
    scores: tuple[int, int, int, int]
    ranks: tuple[int, int, int, int]


class RiichiEnvAdapter:
    def __init__(self, *, seed: int | None = None) -> None:
        installed_version = version("riichienv")
        if installed_version != EXPECTED_RIICHIENV_VERSION:
            raise RuntimeError(
                "expected RiichiEnv "
                f"{EXPECTED_RIICHIENV_VERSION}, got {installed_version}"
            )
        self._env = RiichiEnv(
            game_mode=GAME_MODE,
            rule=GameRule.default_tenhou(),
            seed=seed,
        )
        self._observations: dict[int, Observation] = {}
        self._started = False
        self._last_hand_wins: tuple[HandWin, ...] = ()

    @property
    def last_hand_wins(self) -> tuple[HandWin, ...]:
        """Verified wins from the last step only; not a persistent display queue."""
        return self._last_hand_wins

    @property
    def started(self) -> bool:
        return self._started

    @property
    def done(self) -> bool:
        return self._started and self._env.done()

    @property
    def pending_observations(self) -> Mapping[int, Observation]:
        return MappingProxyType(self._observations)

    @property
    def mjai_log(self) -> list[dict[str, object]]:
        """Read-only-by-convention source log used by internal persistence capture."""
        return self._env.mjai_log

    def scores(self) -> tuple[int, int, int, int]:
        values = tuple(self._env.scores())
        if len(values) != 4 or any(type(value) is not int for value in values):
            raise AdapterStateError("engine scores are invalid")
        return values

    def start(self) -> Mapping[int, Observation]:
        if self._started:
            raise AdapterStateError("match already started")
        self._observations = self._env.reset()
        self._started = True
        return self.pending_observations

    def legal_actions(self, seat: int) -> list[Action]:
        observation = self._observations.get(seat)
        if observation is None:
            raise AdapterStateError(f"seat {seat} is not waiting for an action")
        return observation.legal_actions()

    def step(self, actions: Mapping[int, Action]) -> Mapping[int, Observation]:
        if not self._started:
            raise AdapterStateError("match has not started")
        if self.done:
            raise AdapterStateError("match is already complete")

        expected_seats = set(self._observations)
        if set(actions) != expected_seats:
            raise IllegalActionError(
                f"expected actions for seats {sorted(expected_seats)}"
            )
        for seat, action in actions.items():
            legal_action_values = [
                candidate.to_dict() for candidate in self.legal_actions(seat)
            ]
            if action.to_dict() not in legal_action_values:
                raise IllegalActionError(f"illegal action for seat {seat}")

        self._last_hand_wins = ()
        winning = any(
            action.action_type in (ActionType.RON, ActionType.TSUMO)
            for action in actions.values()
        )
        try:
            captured = capture_hand_scores(self._env, actions) if winning else None
            self._observations = self._env.step(dict(actions))
            if captured is not None:
                self._last_hand_wins = captured.verify(self._env)
        except HandScoreCaptureError:
            raise
        except Exception as error:
            if not winning:
                raise
            raise HandScoreCaptureError("winning step score capture failed") from error
        return self.pending_observations

    def result(self) -> MatchResult:
        if not self.done:
            raise AdapterStateError("match is not complete")
        return MatchResult(
            scores=tuple(self._env.scores()),
            ranks=tuple(self._env.ranks()),
        )
