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
    danger_score: float
    safe_against_riichi: int
    expected_value: float


@dataclass(frozen=True)
class GameState:
    remaining_tiles: int
    my_score: int
    my_rank: int
    scores: tuple[int, int, int, int]
    ranks: tuple[int, int, int, int]
    is_final_round: bool
    opponent_riichi_count: int


class Tier2Agent:
    """Advanced agent with placement awareness, suji/wall defense, and expected value."""

    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def choose_action(self, observation: Observation) -> Action:
        legal_actions = observation.legal_actions()
        if not legal_actions:
            raise ValueError("observation has no legal actions")

        for action_type in WIN_ACTIONS:
            action = self._first_action(legal_actions, action_type)
            if action is not None:
                return action

        game_state = self._analyze_game_state(observation)

        riichi = self._first_action(legal_actions, ActionType.RIICHI)
        if riichi is not None and self._should_riichi(observation, game_state):
            return riichi

        discards = [
            action
            for action in legal_actions
            if action.action_type == ActionType.DISCARD
        ]
        if discards:
            return self._choose_discard(observation, discards, game_state)

        pass_action = self._first_action(legal_actions, ActionType.PASS)
        calls = [
            action for action in legal_actions if action.action_type in CALL_ACTIONS
        ]
        improving_calls = self._improving_calls(observation, calls, game_state)
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

    def _analyze_game_state(self, observation: Observation) -> GameState:
        data = observation.to_dict()
        
        scores = tuple(data.get("scores", [25000] * 4))
        my_score = scores[observation.player_id]
        
        ranks = self._calculate_ranks(scores)
        my_rank = ranks[observation.player_id]
        
        round_wind = data.get("round_wind", 0)
        oya = data.get("oya", 0)
        is_final_round = round_wind == 0
        
        opponent_riichi_count = sum(
            1
            for seat, declared in enumerate(data["riichi_declared"])
            if declared and seat != observation.player_id
        )
        
        visible_tiles = self._visible_tiles(observation)
        remaining_tiles = 136 - len(visible_tiles)
        
        return GameState(
            remaining_tiles=remaining_tiles,
            my_score=my_score,
            my_rank=my_rank,
            scores=scores,
            ranks=ranks,
            is_final_round=is_final_round,
            opponent_riichi_count=opponent_riichi_count,
        )

    @staticmethod
    def _calculate_ranks(scores: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        sorted_seats = sorted(range(4), key=lambda i: (-scores[i], i))
        ranks = [0] * 4
        for rank, seat in enumerate(sorted_seats, start=1):
            ranks[seat] = rank
        return tuple(ranks)

    def _should_riichi(self, observation: Observation, game_state: GameState) -> bool:
        shanten = calculate_shanten(list(observation.hand))
        if shanten != 0:
            return False

        data = observation.to_dict()
        dora_indicators = data.get("dora_indicators", [])
        dora_count = self._count_dora(observation.hand, dora_indicators)

        if game_state.opponent_riichi_count >= 2:
            if dora_count >= 2 and game_state.my_score >= 8000:
                return True
            return False

        if game_state.is_final_round:
            if game_state.my_rank == 4 and game_state.remaining_tiles > 10:
                return True
            if game_state.my_rank == 1 and game_state.my_score >= 30000:
                return False

        if dora_count >= 2:
            return True

        if game_state.my_score < 10000:
            return True

        if game_state.opponent_riichi_count == 0:
            return True

        return dora_count >= 1 or game_state.my_score < 15000

    def _choose_discard(
        self,
        observation: Observation,
        discards: list[Action],
        game_state: GameState,
    ) -> Action:
        evaluations = [
            self._evaluate_discard(observation, action, game_state) 
            for action in discards
        ]

        should_fold = self._should_fold(observation, evaluations, game_state)

        if should_fold:
            safe_candidates = sorted(
                evaluations,
                key=lambda e: (
                    e.danger_score,
                    -e.safe_against_riichi,
                    -e.shanten,
                )
            )
            if safe_candidates and safe_candidates[0].danger_score < 5.0:
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

        for candidate in rational:
            ev_score = self._compute_expected_value(candidate, game_state)
            candidate.__dict__["_ev_score"] = ev_score

        rational.sort(key=lambda e: (-e.__dict__["_ev_score"], e.action.tile))
        weights = [
            max(1, int(10 + e.__dict__["_ev_score"] * 10))
            for e in rational
        ]

        return self._rng.choices(rational, weights=weights, k=1)[0].action

    def _compute_expected_value(
        self,
        evaluation: DiscardEvaluation,
        game_state: GameState,
    ) -> float:
        ev = 0.0
        
        ev += evaluation.ukeire * 2.0
        ev += evaluation.dora_count * 4.0
        ev += evaluation.potential_yaku_bonus * 3.0
        
        ev -= evaluation.danger_score * 2.0
        ev += evaluation.safe_against_riichi * 4.0
        
        if game_state.my_rank == 4:
            ev += evaluation.ukeire * 1.5
            ev += evaluation.dora_count * 2.0
        elif game_state.my_rank == 1 and game_state.is_final_round:
            ev -= evaluation.danger_score * 1.5
            ev += evaluation.safe_against_riichi * 2.0
        
        if game_state.is_final_round:
            if game_state.my_rank == 4:
                score_gap = game_state.scores[game_state.ranks.index(3)] - game_state.my_score
                if score_gap > 0:
                    urgency = min(3.0, score_gap / 4000)
                    ev += evaluation.ukeire * urgency
        
        if game_state.remaining_tiles < 20:
            danger_weight = (20 - game_state.remaining_tiles) / 10
            ev -= evaluation.danger_score * danger_weight
        
        return ev

    def _should_fold(
        self,
        observation: Observation,
        evaluations: list[DiscardEvaluation],
        game_state: GameState,
    ) -> bool:
        if game_state.opponent_riichi_count == 0:
            return False

        shanten = calculate_shanten(list(observation.hand))
        
        data = observation.to_dict()
        dora_indicators = data.get("dora_indicators", [])
        dora_count = self._count_dora(observation.hand, dora_indicators)

        if shanten >= 2 and game_state.opponent_riichi_count >= 1:
            if dora_count < 2 or game_state.my_score < 8000:
                return True

        if game_state.my_score < 5000:
            return True

        if game_state.is_final_round:
            if game_state.my_rank == 1 and game_state.my_score >= 30000:
                return True
            if game_state.my_rank == 4 and shanten <= 1 and dora_count >= 1:
                return False

        if shanten == 1 and dora_count == 0 and game_state.opponent_riichi_count >= 2:
            return True

        min_danger = min(e.danger_score for e in evaluations)
        if shanten >= 2 and min_danger > 8.0 and game_state.opponent_riichi_count >= 1:
            return True

        return False

    def _evaluate_discard(
        self,
        observation: Observation,
        action: Action,
        game_state: GameState,
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

        danger_score = self._estimate_danger_score(action.tile, observation, visible_tiles)

        expected_value = 0.0

        return DiscardEvaluation(
            action=action,
            shanten=shanten,
            ukeire=ukeire,
            dora_count=dora_count,
            potential_yaku_bonus=potential_yaku_bonus,
            danger_score=danger_score,
            safe_against_riichi=safe_against_riichi,
            expected_value=expected_value,
        )

    def _estimate_danger_score(
        self,
        tile: int,
        observation: Observation,
        visible_tiles: list[int],
    ) -> float:
        data = observation.to_dict()
        tile_kind = tile // 4

        opponent_riichi = [
            seat
            for seat, declared in enumerate(data["riichi_declared"])
            if declared and seat != observation.player_id
        ]

        if not opponent_riichi:
            return 0.0

        danger = 0.0

        for seat in opponent_riichi:
            discards = data.get("discards", [[]] * 4)[seat]
            discard_kinds = {t // 4 for t in discards}
            
            if tile_kind in discard_kinds:
                danger += 0.0
                continue

            base_danger = self._base_tile_danger(tile_kind)
            danger += base_danger

            suji_safe = self._is_suji_safe(tile_kind, discard_kinds)
            if suji_safe:
                danger -= 2.0

            wall_safe = self._is_wall_safe(tile_kind, visible_tiles)
            if wall_safe:
                danger -= 1.5

        return max(0.0, danger)

    @staticmethod
    def _base_tile_danger(tile_kind: int) -> float:
        if tile_kind >= 27:
            return 4.0
        
        rank = tile_kind % 9
        if rank in (0, 8):
            return 1.5
        elif rank in (1, 7):
            return 2.5
        else:
            return 3.5

    @staticmethod
    def _is_suji_safe(tile_kind: int, opponent_discards: set[int]) -> bool:
        if tile_kind >= 27:
            return False
        
        suit = tile_kind // 9
        rank = tile_kind % 9
        
        suji_pairs = []
        if rank >= 3:
            suji_pairs.append(suit * 9 + (rank - 3))
        if rank <= 5:
            suji_pairs.append(suit * 9 + (rank + 3))
        
        return any(suji in opponent_discards for suji in suji_pairs)

    @staticmethod
    def _is_wall_safe(tile_kind: int, visible_tiles: list[int]) -> bool:
        visible_count = sum(t // 4 == tile_kind for t in visible_tiles)
        return visible_count >= 3

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
            bonus += 1.2

        terminals = [k for k in tile_kinds if k % 9 == 0 or k % 9 == 8]
        honors = [k for k in tile_kinds if k >= 27]
        if len(terminals) + len(honors) >= 10:
            bonus += 0.6

        data = observation.to_dict()
        melds = data.get("melds", [[]] * 4)[observation.player_id]
        if not melds:
            bonus += 0.4

        suits = {tile // 9 for tile in hand if tile // 4 < 27}
        if len(suits) == 1:
            bonus += 1.0

        return bonus

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
        game_state: GameState,
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
                if self._tile_is_dora(tile, dora_indicators)
            )

            evaluated.append((new_shanten, dora_in_call, action))

        if not evaluated:
            return []

        best_shanten = min(shanten for shanten, _, _ in evaluated)

        if best_shanten > current_shanten:
            return []

        if best_shanten < current_shanten:
            improving = [action for shanten, _, action in evaluated if shanten == best_shanten]
            
            if game_state.is_final_round and game_state.my_rank == 4:
                return improving
            
            if game_state.opponent_riichi_count == 0:
                return improving
            
            return []

        candidates = [action for shanten, dora, action in evaluated if shanten == best_shanten and dora > 0]
        if candidates:
            return candidates

        if action.action_type == ActionType.PON and game_state.my_rank == 4:
            return [action for shanten, _, action in evaluated if shanten == best_shanten]

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
