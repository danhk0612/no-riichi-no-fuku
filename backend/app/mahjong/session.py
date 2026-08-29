from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from riichienv import Action

from app.mahjong.agent import MahjongAgent
from app.mahjong.riichienv_adapter import (
    AdapterStateError,
    MatchResult,
    RiichiEnvAdapter,
)


HUMAN_SEAT = 0
CPU_SEATS = (1, 2, 3)


class GameSessionStateError(RuntimeError):
    pass


@dataclass(frozen=True)
class HumanTurn:
    observation: dict[str, object]
    legal_actions: tuple[dict[str, object], ...]


class AuthoritativeGameSession:
    def __init__(
        self,
        *,
        user_id: int,
        cpu_character_ids: tuple[int, int, int],
        cpu_agents: Mapping[int, MahjongAgent],
        seed: int | None = None,
        max_steps: int = 5_000,
    ) -> None:
        if len(set(cpu_character_ids)) != 3:
            raise ValueError("three distinct CPU characters are required")
        if set(cpu_agents) != set(CPU_SEATS):
            raise ValueError("CPU agents are required for seats 1, 2 and 3")
        self.user_id = user_id
        self.cpu_character_by_seat = dict(zip(CPU_SEATS, cpu_character_ids))
        self._cpu_agents = dict(cpu_agents)
        self._adapter = RiichiEnvAdapter(seed=seed)
        self._max_steps = max_steps
        self._steps = 0

    @property
    def started(self) -> bool:
        return self._adapter.started

    @property
    def done(self) -> bool:
        return self._adapter.done

    @property
    def steps(self) -> int:
        return self._steps

    def start(self) -> None:
        self._adapter.start()
        self._advance_until_human_turn()

    def human_turn(self) -> HumanTurn | None:
        if not self.started:
            raise GameSessionStateError("session has not started")
        if self.done:
            return None
        observation = self._adapter.pending_observations.get(HUMAN_SEAT)
        if observation is None:
            raise GameSessionStateError("session is not waiting for the human seat")
        return HumanTurn(
            observation=observation.to_dict(),
            legal_actions=tuple(
                action.to_dict()
                for action in self._adapter.legal_actions(HUMAN_SEAT)
            ),
        )

    def submit_human_action(self, legal_action_index: int) -> None:
        turn = self.human_turn()
        if turn is None:
            raise GameSessionStateError("match is already complete")
        legal_actions = self._adapter.legal_actions(HUMAN_SEAT)
        if legal_action_index < 0 or legal_action_index >= len(legal_actions):
            raise GameSessionStateError("legal action index is out of range")

        actions = self._cpu_actions_for_pending_observations()
        actions[HUMAN_SEAT] = legal_actions[legal_action_index]
        self._step(actions)
        self._advance_until_human_turn()

    def result(self) -> MatchResult:
        try:
            return self._adapter.result()
        except AdapterStateError as error:
            raise GameSessionStateError(str(error)) from None

    def _advance_until_human_turn(self) -> None:
        while not self.done and HUMAN_SEAT not in self._adapter.pending_observations:
            self._step(self._cpu_actions_for_pending_observations())

    def _cpu_actions_for_pending_observations(self) -> dict[int, Action]:
        return {
            seat: self._cpu_agents[seat].choose_action(observation)
            for seat, observation in self._adapter.pending_observations.items()
            if seat != HUMAN_SEAT
        }

    def _step(self, actions: Mapping[int, Action]) -> None:
        self._adapter.step(actions)
        self._steps += 1
        if self._steps > self._max_steps:
            raise GameSessionStateError("match exceeded the step limit")
