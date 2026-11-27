from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from riichienv import Action

from app.mahjong.agent import MahjongAgent
from app.mahjong.riichienv_adapter import (
    AdapterStateError,
    MatchResult,
    RiichiEnvAdapter,
)
from app.mahjong.hand_results import HandResultCollector, HandResultFact


HUMAN_SEAT = 0
CPU_SEATS = (1, 2, 3)


class GameSessionStateError(RuntimeError):
    pass


@dataclass(frozen=True)
class HumanTurn:
    observation: dict[str, object]
    legal_actions: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class PendingGameEvents:
    """마지막 step에서 발생한 게임 이벤트 (대사 생성용)"""

    events: tuple[dict[str, object] | str, ...]


class AuthoritativeGameSession:
    def __init__(
        self,
        *,
        user_id: int,
        cpu_character_ids: tuple[int, int, int],
        cpu_agents: Mapping[int, MahjongAgent],
        seed: int | None = None,
        max_steps: int = 5_000,
        capture_hand_results: bool = False,
    ) -> None:
        if len(set(cpu_character_ids)) != 3:
            raise ValueError("three distinct CPU characters are required")
        if set(cpu_agents) != set(CPU_SEATS):
            raise ValueError("CPU agents are required for seats 1, 2 and 3")
        self.user_id = user_id
        self.cpu_character_by_seat = MappingProxyType(
            dict(zip(CPU_SEATS, cpu_character_ids))
        )
        self._cpu_agents = dict(cpu_agents)
        self._adapter = RiichiEnvAdapter(seed=seed)
        self._max_steps = max_steps
        self._steps = 0
        self._result_settled = False
        self._event_offset = 0
        self._pending_events: list[dict[str, object] | str] = []
        self._hand_result_collector = HandResultCollector() if capture_hand_results else None

    @property
    def started(self) -> bool:
        return self._adapter.started

    @property
    def done(self) -> bool:
        return self._adapter.done

    @property
    def steps(self) -> int:
        return self._steps

    @property
    def result_settled(self) -> bool:
        return self._result_settled

    def pending_events(self) -> PendingGameEvents:
        """
        마지막 step 이후 누적된 게임 이벤트를 반환한다.
        이 메서드를 호출하면 누적된 이벤트가 소비된다.
        """
        events = tuple(self._pending_events)
        self._pending_events.clear()
        return PendingGameEvents(events=events)

    def pending_hand_results(self) -> tuple[HandResultFact, ...]:
        """Consume only closed hand facts; independent of dialogue/audio events."""
        if self._hand_result_collector is None:
            return ()
        return self._hand_result_collector.drain()

    def start(self) -> None:
        self._adapter.start()
        log = self._collect_new_events()
        if self._hand_result_collector is not None:
            self._hand_result_collector.consume(
                log, (), self._adapter.scores(), self.done
            )
        self._advance_until_human_turn()

    def human_turn(self) -> HumanTurn | None:
        if not self.started:
            raise GameSessionStateError("session has not started")
        if self.done:
            return None
        observation = self._adapter.pending_observations.get(HUMAN_SEAT)
        if observation is None:
            raise GameSessionStateError("session is not waiting for the human seat")
        serialized_observation = observation.to_dict()
        serialized_observation["kyoku_index"] = observation.kyoku_index
        serialized_observation["melds"] = [
            [
                {
                    "meld_type": int(meld.meld_type),
                    "tiles": list(meld.tiles),
                    "called_tile": meld.called_tile,
                    "from_who": meld.from_who,
                    "opened": meld.opened,
                }
                for meld in player_melds
            ]
            for player_melds in serialized_observation["melds"]
        ]
        return HumanTurn(
            observation=serialized_observation,
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

    def mark_result_settled(self) -> None:
        if not self.done:
            raise GameSessionStateError("match is not complete")
        if self._result_settled:
            raise GameSessionStateError("match result is already settled")
        self._result_settled = True

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
        log = self._collect_new_events()
        if self._hand_result_collector is not None:
            self._hand_result_collector.consume(
                log,
                self._adapter.last_hand_wins,
                self._adapter.scores(),
                self.done,
            )
        self._steps += 1
        if self._steps > self._max_steps:
            raise GameSessionStateError("match exceeded the step limit")

    def _collect_new_events(self) -> list[dict[str, object]]:
        # Every seat can observe the same action. The engine log records it once.
        log = self._adapter.mjai_log
        self._pending_events.extend(log[self._event_offset:])
        self._event_offset = len(log)
        return log
