from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

from riichienv import Action, ActionType, Meld, MeldType, Observation, calculate_shanten


WIN_ACTIONS = (ActionType.TSUMO, ActionType.RON)
CALL_ACTIONS = (ActionType.CHI, ActionType.PON, ActionType.DAIMINKAN)


@dataclass(frozen=True)
class DiscardEvaluation:
    action: Action
    shanten: int
    ukeire: int
    dora_count: int
    potential_yaku_bonus: float
    danger_level: int
    safe_against_riichi: int


class Tier1Agent:
    """Improved agent with value awareness, better defense, and basic push/fold."""

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
        if riichi is not None and self._should_riichi(observation):
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

    def _should_riichi(self, observation: Observation) -> bool:
        data = observation.to_dict()
        shanten = calculate_shanten(list(observation.hand))
        if shanten != 0:
            return False

        riichi_sticks = data.get("riichi_sticks", 0)
        honba = data.get("honba", 0)
        scores = data.get("scores", [25000] * 4)
        my_score = scores[observation.player_id]

        opponent_riichi_count = sum(
            1
            for seat, declared in enumerate(data["riichi_declared"])
            if declared and seat != observation.player_id
        )

        defense_factor = self._defense / self._riichi_preference
        if opponent_riichi_count >= 2 and defense_factor > 1.1:
            return False

        dora_indicators = data.get("dora_indicators", [])
        dora_count = self._count_dora(observation.hand, dora_indicators)

        dora_threshold = max(0, int(2 - self._riichi_preference))
        if dora_count >= dora_threshold or my_score < 15000 * self._aggression:
            return True

        if opponent_riichi_count == 0 and my_score >= 15000 / self._riichi_preference:
            return True

        return my_score < 10000 * self._aggression

    def _choose_discard(
        self,
        observation: Observation,
        discards: list[Action],
    ) -> Action:
        evaluations = [
            self._evaluate_discard(observation, action) for action in discards
        ]

        data = observation.to_dict()
        opponent_riichi_count = sum(
            1
            for seat, declared in enumerate(data["riichi_declared"])
            if declared and seat != observation.player_id
        )

        should_fold = self._should_fold(observation, evaluations, opponent_riichi_count)

        if should_fold:
            safe_candidates = [
                e for e in evaluations
                if e.safe_against_riichi > 0 or e.danger_level == 0
            ]
            if safe_candidates:
                safe_candidates.sort(
                    key=lambda e: (
                        -e.safe_against_riichi,
                        e.danger_level,
                        -e.shanten,
                    )
                )
                return safe_candidates[0].action

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

        ukeire_weight = 2.0 * self._speed_preference
        dora_weight = 3.0 * self._hand_value_preference
        yaku_weight = 2.0 * self._hand_value_preference
        danger_weight = 1.5 * self._defense
        safety_weight = 3.0 * self._defense
        
        for candidate in rational:
            score = (
                candidate.ukeire * ukeire_weight
                + candidate.dora_count * dora_weight
                + candidate.potential_yaku_bonus * yaku_weight
                - candidate.danger_level * danger_weight
                + candidate.safe_against_riichi * safety_weight
            )
            candidate.__dict__["_score"] = score

        rational.sort(key=lambda e: (-e.__dict__["_score"], e.action.tile))
        weights = [
            max(1, int(10 + e.__dict__["_score"]))
            for e in rational
        ]

        return self._rng.choices(rational, weights=weights, k=1)[0].action

    def _should_fold(
        self,
        observation: Observation,
        evaluations: list[DiscardEvaluation],
        opponent_riichi_count: int,
    ) -> bool:
        if opponent_riichi_count == 0:
            return False

        data = observation.to_dict()
        scores = data.get("scores", [25000] * 4)
        my_score = scores[observation.player_id]
        shanten = calculate_shanten(list(observation.hand))

        aggression_factor = self._aggression / self._defense
        
        if shanten >= 2 and opponent_riichi_count >= 1 and aggression_factor < 1.0:
            return True

        if my_score < 5000 * aggression_factor and opponent_riichi_count >= 1:
            return True

        dora_indicators = data.get("dora_indicators", [])
        dora_count = self._count_dora(observation.hand, dora_indicators)

        if shanten == 1 and dora_count == 0 and opponent_riichi_count >= 2 and self._defense > 1.1:
            return True

        return False

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

        data = observation.to_dict()
        dora_indicators = data.get("dora_indicators", [])
        dora_count = self._count_dora(hand_after, dora_indicators)

        potential_yaku_bonus = self._estimate_yaku_bonus(hand_after, observation)

        tile_kind = action.tile // 4
        safe_against_riichi = sum(
            tile_kind in safe_kinds
            for safe_kinds in self._riichi_safe_tile_kinds(observation)
        )

        danger_level = self._estimate_danger_level(action.tile, observation)

        return DiscardEvaluation(
            action=action,
            shanten=shanten,
            ukeire=ukeire,
            dora_count=dora_count,
            potential_yaku_bonus=potential_yaku_bonus,
            danger_level=danger_level,
            safe_against_riichi=safe_against_riichi,
        )

    @staticmethod
    def _count_dora(hand: list[int], dora_indicators: list[int]) -> int:
        if not dora_indicators:
            return 0

        dora_tiles = []
        for indicator in dora_indicators:
            tile_kind = indicator // 4
            if tile_kind < 27:
                suit = tile_kind // 9
                rank = tile_kind % 9
                next_rank = (rank + 1) % 9
                dora_kind = suit * 9 + next_rank
            else:
                honor = tile_kind - 27
                next_honor = (honor + 1) % 7
                dora_kind = 27 + next_honor
            dora_tiles.append(dora_kind)

        return sum(tile // 4 in dora_tiles for tile in hand)

    @staticmethod
    def _estimate_yaku_bonus(hand: list[int], observation: Observation) -> float:
        bonus = 0.0

        tile_kinds = [tile // 4 for tile in hand]

        has_terminal_or_honor = any(
            kind % 9 == 0 or kind % 9 == 8 or kind >= 27
            for kind in tile_kinds
        )
        if not has_terminal_or_honor:
            bonus += 1.0

        terminals = [k for k in tile_kinds if k % 9 == 0 or k % 9 == 8]
        honors = [k for k in tile_kinds if k >= 27]
        if len(terminals) + len(honors) >= 10:
            bonus += 0.5

        data = observation.to_dict()
        melds = data.get("melds", [[]] * 4)[observation.player_id]
        if not melds:
            bonus += 0.3

        suits = {tile // 9 for tile in hand if tile // 4 < 27}
        if len(suits) == 1:
            bonus += 0.8

        return bonus

    @staticmethod
    def _estimate_danger_level(tile: int, observation: Observation) -> int:
        data = observation.to_dict()
        tile_kind = tile // 4

        opponent_riichi = [
            seat
            for seat, declared in enumerate(data["riichi_declared"])
            if declared and seat != observation.player_id
        ]

        if not opponent_riichi:
            return 0

        danger = 0

        for seat in opponent_riichi:
            discards = data.get("discards", [[]] * 4)[seat]
            if tile_kind in [t // 4 for t in discards]:
                continue

            if tile_kind >= 27:
                danger += 3
            elif tile_kind % 9 in (0, 8):
                danger += 1
            elif tile_kind % 9 in (1, 7):
                danger += 2
            else:
                danger += 3

        return danger

    @staticmethod
    def _visible_tiles(observation: Observation) -> list[int]:
        data = observation.to_dict()
        tiles = list(observation.hand)
        tiles.extend(
            tile
            for discards in data["discards"]
            for tile in discards
        )
        tiles.extend(data.get("dora_indicators", []))
        for melds in data["melds"]:
            for meld in melds:
                if isinstance(meld, Meld):
                    tiles.extend(meld.tiles)
                elif isinstance(meld, dict):
                    tiles.extend(meld.get("tiles", []))
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
        current_shanten = calculate_shanten(list(observation.hand))
        evaluated: list[tuple[int, int, Action]] = []

        data = observation.to_dict()
        dora_indicators = data.get("dora_indicators", [])

        for action in calls:
            hand_after = list(observation.hand)
            for tile in action.consume_tiles:
                hand_after.remove(tile)

            new_shanten = calculate_shanten(hand_after)

            dora_in_call = sum(
                1 for tile in action.consume_tiles
                if Tier1Agent._tile_is_dora(tile, dora_indicators)
            )

            evaluated.append((new_shanten, dora_in_call, action))

        if not evaluated:
            return []

        best_shanten = min(shanten for shanten, _, _ in evaluated)

        if best_shanten > current_shanten:
            return []

        if best_shanten < current_shanten:
            improving = [action for shanten, _, action in evaluated if shanten == best_shanten]
            if self._call_preference < 1.0:
                threshold = 0.6 + (self._call_preference * 0.4)
                if self._rng.random() > threshold:
                    return []
            return improving

        candidates = [action for shanten, dora, action in evaluated if shanten == best_shanten and dora > 0]
        if candidates and self._hand_value_preference > 0.9:
            return candidates

        if self._call_preference > 1.0:
            return [action for shanten, _, action in evaluated if shanten == best_shanten if action.action_type == ActionType.PON]

        if self._call_preference < 1.1:
            return []

        return []

    @staticmethod
    def _tile_is_dora(tile: int, dora_indicators: list[int]) -> bool:
        if not dora_indicators:
            return False

        tile_kind = tile // 4
        for indicator in dora_indicators:
            indicator_kind = indicator // 4
            if indicator_kind < 27:
                suit = indicator_kind // 9
                rank = indicator_kind % 9
                next_rank = (rank + 1) % 9
                dora_kind = suit * 9 + next_rank
            else:
                honor = indicator_kind - 27
                next_honor = (honor + 1) % 7
                dora_kind = 27 + next_honor

            if tile_kind == dora_kind:
                return True

        return False
