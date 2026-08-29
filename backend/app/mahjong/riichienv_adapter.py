from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from types import MappingProxyType
from typing import Mapping

from riichienv import Action, GameRule, Observation, RiichiEnv


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

    @property
    def started(self) -> bool:
        return self._started

    @property
    def done(self) -> bool:
        return self._started and self._env.done()

    @property
    def pending_observations(self) -> Mapping[int, Observation]:
        return MappingProxyType(self._observations)

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

        self._observations = self._env.step(dict(actions))
        return self.pending_observations

    def result(self) -> MatchResult:
        if not self.done:
            raise AdapterStateError("match is not complete")
        return MatchResult(
            scores=tuple(self._env.scores()),
            ranks=tuple(self._env.ranks()),
        )
