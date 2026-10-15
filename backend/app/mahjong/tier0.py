from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

from riichienv import Action, ActionType, Observation, calculate_shanten


WIN_ACTIONS = (ActionType.TSUMO, ActionType.RON)
CALL_ACTIONS = (ActionType.CHI, ActionType.PON, ActionType.DAIMINKAN)


@dataclass(frozen=True)
class DiscardEvaluation:
    action: Action
    shanten: int
    ukeire: int
    safe_against_riichi: int


class Tier0Agent:
    """Basic hand-efficiency agent with a small, deterministic safety bias."""

    def __init__(
        self,
        *,
        seed: int | None = None,
        aggression: float = 1.0,
        defense: float = 1.0,
        call_preference: float = 1.0,
        riichi_preference: float = 1.0,
        hand_value_preference: float = 1.0,
        speed_preference: float = 1.0,
    ) -> None:
        self._rng = random.Random(seed)
        self._aggression = aggression
        self._defense = defense
        self._call_preference = call_preference
        self._riichi_preference = riichi_preference
        self._hand_value_preference = hand_value_preference
        self._speed_preference = speed_preference

    def choose_action(self, observation: Observation) -> Action:
        legal_actions = observation.legal_actions()
        if not legal_actions:
            raise ValueError("observation has no legal actions")

        for action_type in WIN_ACTIONS:
            action = self._first_action(legal_actions, action_type)
            if action is not None:
                return action

        riichi = self._first_action(legal_actions, ActionType.RIICHI)
        if riichi is not None and self._should_declare_riichi(observation):
            return riichi

        discards = [
            action
            for action in legal_actions
            if action.action_type == ActionType.DISCARD
        ]
        if discards:
            return self._choose_discard(observation, discards)

        pass_action = self._first_action(legal_actions, ActionType.PASS)
        calls = [
            action for action in legal_actions if action.action_type in CALL_ACTIONS
        ]
        improving_calls = self._improving_calls(observation, calls)
        if improving_calls:
            return self._rng.choice(improving_calls)
        if pass_action is not None:
            return pass_action

        return legal_actions[0]

    @staticmethod
    def _first_action(actions: Iterable[Action], action_type: ActionType) -> Action | None:
        return next(
            (action for action in actions if action.action_type == action_type),
            None,
        )

    def _should_declare_riichi(self, observation: Observation) -> bool:
        """Determine whether to declare riichi based on personality."""
        if self._riichi_preference >= 1.0:
            return True
        
        shanten = calculate_shanten(list(observation.hand))
        if shanten != 0:
            return True
        
        data = observation.to_dict()
        opponent_riichi_count = sum(
            1
            for seat, declared in enumerate(data["riichi_declared"])
            if declared and seat != observation.player_id
        )
        
        if opponent_riichi_count >= 2 and self._defense > self._riichi_preference:
            return False
        
        threshold = 0.85 * self._riichi_preference
        return self._rng.random() < threshold or self._riichi_preference >= 1.15

    def _choose_discard(
        self,
        observation: Observation,
        discards: list[Action],
    ) -> Action:
        evaluations = [
            self._evaluate_discard(observation, action) for action in discards
        ]
        best_shanten = min(candidate.shanten for candidate in evaluations)
        efficient = [
            candidate
            for candidate in evaluations
            if candidate.shanten == best_shanten
        ]
        best_ukeire = max(candidate.ukeire for candidate in efficient)
        rational = [
            candidate
            for candidate in efficient
            if candidate.ukeire >= best_ukeire - 4
        ]
        rational.sort(key=lambda candidate: candidate.action.tile)
        
        defense_weight = 2.0 * self._defense
        speed_weight = 1.0 * self._speed_preference
        min_ukeire = min(item.ukeire for item in rational)
        
        weights = [
            1
            + (candidate.ukeire - min_ukeire) * speed_weight
            + candidate.safe_against_riichi * defense_weight
            for candidate in rational
        ]
        return self._rng.choices(rational, weights=weights, k=1)[0].action

    def _evaluate_discard(
        self,
        observation: Observation,
        action: Action,
    ) -> DiscardEvaluation:
        hand_after = list(observation.hand)
        hand_after.remove(action.tile)
        shanten = calculate_shanten(hand_after)
        visible_tiles = self._visible_tiles(observation)
        ukeire = 0
        for tile_kind in range(34):
            visible_count = sum(tile // 4 == tile_kind for tile in visible_tiles)
            remaining = max(0, 4 - visible_count)
            if remaining == 0:
                continue
            candidate_tile = next(
                tile
                for tile in range(tile_kind * 4, tile_kind * 4 + 4)
                if tile not in hand_after
            )
            if calculate_shanten([*hand_after, candidate_tile]) < shanten:
                ukeire += remaining

        tile_kind = action.tile // 4
        safe_against_riichi = sum(
            tile_kind in safe_kinds
            for safe_kinds in self._riichi_safe_tile_kinds(observation)
        )
        return DiscardEvaluation(
            action=action,
            shanten=shanten,
            ukeire=ukeire,
            safe_against_riichi=safe_against_riichi,
        )

    @staticmethod
    def _visible_tiles(observation: Observation) -> list[int]:
        data = observation.to_dict()
        tiles = list(observation.hand)
        tiles.extend(
            tile
            for discards in data["discards"]
            for tile in discards
        )
        tiles.extend(data["dora_indicators"])
        for melds in data["melds"]:
            for meld in melds:
                tiles.extend(meld.tiles)
        return tiles

    @staticmethod
    def _riichi_safe_tile_kinds(observation: Observation) -> list[set[int]]:
        data = observation.to_dict()
        return [
            {tile // 4 for tile in data["discards"][seat]}
            for seat, declared in enumerate(data["riichi_declared"])
            if declared and seat != observation.player_id
        ]

    def _improving_calls(
        self,
        observation: Observation,
        calls: list[Action],
    ) -> list[Action]:
        if self._call_preference < 0.8:
            return []
        
        current_shanten = calculate_shanten(list(observation.hand))
        evaluated: list[tuple[int, Action]] = []
        for action in calls:
            hand_after = list(observation.hand)
            for tile in action.consume_tiles:
                hand_after.remove(tile)
            evaluated.append((calculate_shanten(hand_after), action))
        if not evaluated:
            return []
        best_shanten = min(shanten for shanten, _ in evaluated)
        if best_shanten >= current_shanten:
            return []
        
        improving = [
            action for shanten, action in evaluated if shanten == best_shanten
        ]
        
        if self._call_preference < 1.0 and self._rng.random() > self._call_preference:
            return []
        
        return improving
