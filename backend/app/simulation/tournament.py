"""Fixed-seed tournament simulation for tier difficulty analysis."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from riichienv import Action, ActionType

from app.mahjong.agent import MahjongAgent
from app.mahjong.session import AuthoritativeGameSession
from app.mahjong.tier0 import Tier0Agent
from app.mahjong.tier1 import Tier1Agent
from app.mahjong.tier2 import Tier2Agent

TierLabel = Literal["Tier0", "Tier1", "Tier2"]

TIER_CLASSES: dict[TierLabel, type[MahjongAgent]] = {
    "Tier0": Tier0Agent,
    "Tier1": Tier1Agent,
    "Tier2": Tier2Agent,
}


@dataclass(frozen=True)
class MatchConfig:
    """Configuration for a single match."""

    match_seed: int
    seat_tiers: tuple[TierLabel, TierLabel, TierLabel, TierLabel]


@dataclass(frozen=True)
class MatchResult:
    """Result of a single match."""

    match_seed: int
    seat_tiers: tuple[TierLabel, TierLabel, TierLabel, TierLabel]
    scores: tuple[int, int, int, int]
    ranks: tuple[int, int, int, int]
    steps: int


@dataclass
class TierStatistics:
    """Aggregated statistics for a single tier."""

    tier: TierLabel
    match_count: int
    rank_counts: dict[int, int]
    total_score: int
    first_place_count: int
    fourth_place_count: int

    @property
    def average_rank(self) -> float:
        """Calculate average rank (1.0 = best, 4.0 = worst)."""
        if self.match_count == 0:
            return 0.0
        total_rank_sum = sum(rank * count for rank, count in self.rank_counts.items())
        return total_rank_sum / self.match_count

    @property
    def average_score(self) -> float:
        """Calculate average score across all matches."""
        if self.match_count == 0:
            return 0.0
        return self.total_score / self.match_count

    @property
    def first_place_rate(self) -> float:
        """Calculate rate of first place finishes."""
        if self.match_count == 0:
            return 0.0
        return self.first_place_count / self.match_count

    @property
    def fourth_place_rate(self) -> float:
        """Calculate rate of fourth place finishes."""
        if self.match_count == 0:
            return 0.0
        return self.fourth_place_count / self.match_count


class DeterministicHumanAgent(MahjongAgent):
    """Deterministic human-seat agent for tournament simulation.
    
    Prioritizes win > riichi > first legal discard > pass > first legal action.
    """

    def choose_action(self, observation) -> Action:
        legal_actions = observation.legal_actions()
        if not legal_actions:
            raise ValueError("observation has no legal actions")

        for action_type in (ActionType.TSUMO, ActionType.RON):
            for action in legal_actions:
                if action.action_type == action_type:
                    return action

        for action in legal_actions:
            if action.action_type == ActionType.RIICHI:
                return action

        for action in legal_actions:
            if action.action_type == ActionType.DISCARD:
                return action

        for action in legal_actions:
            if action.action_type == ActionType.PASS:
                return action

        return legal_actions[0]


def run_single_match(config: MatchConfig) -> MatchResult:
    """Run a single match with the given configuration.
    
    Args:
        config: Match configuration with seed and tier assignments
        
    Returns:
        MatchResult containing scores, ranks, and metadata
    """
    agents: dict[int, MahjongAgent] = {}
    for seat, tier_label in enumerate(config.seat_tiers):
        agent_class = TIER_CLASSES[tier_label]
        agent_seed = config.match_seed * 10 + seat
        agents[seat] = agent_class(seed=agent_seed)

    session = AuthoritativeGameSession(
        user_id=1,
        cpu_character_ids=(1, 2, 3),
        cpu_agents={1: agents[1], 2: agents[2], 3: agents[3]},
        seed=config.match_seed,
    )
    session.start()

    while not session.done:
        turn = session.human_turn()
        if turn is None:
            break
        human_action = agents[0].choose_action(session._adapter.pending_observations[0])
        legal_actions_list = [
            action for action in session._adapter.pending_observations[0].legal_actions()
        ]
        action_index = next(
            i
            for i, action in enumerate(legal_actions_list)
            if action.to_dict() == human_action.to_dict()
        )
        session.submit_human_action(action_index)

    result = session.result()
    return MatchResult(
        match_seed=config.match_seed,
        seat_tiers=config.seat_tiers,
        scores=result.scores,
        ranks=result.ranks,
        steps=session.steps,
    )


def run_tournament(
    seeds: list[int],
    tier_combinations: list[tuple[TierLabel, TierLabel, TierLabel, TierLabel]],
) -> list[MatchResult]:
    """Run a tournament with multiple seeds and tier combinations.
    
    Args:
        seeds: List of match seeds to test
        tier_combinations: List of four-seat tier assignments
        
    Returns:
        List of MatchResult objects for all completed matches
    """
    results: list[MatchResult] = []
    for seed in seeds:
        for combination in tier_combinations:
            config = MatchConfig(match_seed=seed, seat_tiers=combination)
            result = run_single_match(config)
            results.append(result)
    return results


def analyze_results(results: list[MatchResult]) -> dict[TierLabel, TierStatistics]:
    """Analyze tournament results and compute tier statistics.
    
    Args:
        results: List of completed match results
        
    Returns:
        Dictionary mapping tier labels to their aggregated statistics
    """
    tier_data: dict[TierLabel, dict] = {
        tier: {
            "match_count": 0,
            "rank_counts": defaultdict(int),
            "total_score": 0,
            "first_place_count": 0,
            "fourth_place_count": 0,
        }
        for tier in TIER_CLASSES
    }

    for result in results:
        for seat, tier_label in enumerate(result.seat_tiers):
            rank = result.ranks[seat]
            score = result.scores[seat]

            data = tier_data[tier_label]
            data["match_count"] += 1
            data["rank_counts"][rank] += 1
            data["total_score"] += score
            if rank == 1:
                data["first_place_count"] += 1
            if rank == 4:
                data["fourth_place_count"] += 1

    return {
        tier: TierStatistics(
            tier=tier,
            match_count=data["match_count"],
            rank_counts=dict(data["rank_counts"]),
            total_score=data["total_score"],
            first_place_count=data["first_place_count"],
            fourth_place_count=data["fourth_place_count"],
        )
        for tier, data in tier_data.items()
    }


def generate_balanced_combinations() -> list[
    tuple[TierLabel, TierLabel, TierLabel, TierLabel]
]:
    """Generate balanced tier combinations for tournament testing.
    
    Returns combinations where each tier appears in different seats to minimize
    positional bias.
    """
    combinations: list[tuple[TierLabel, TierLabel, TierLabel, TierLabel]] = [
        ("Tier0", "Tier0", "Tier0", "Tier0"),
        ("Tier1", "Tier1", "Tier1", "Tier1"),
        ("Tier2", "Tier2", "Tier2", "Tier2"),
        ("Tier0", "Tier1", "Tier2", "Tier0"),
        ("Tier1", "Tier2", "Tier0", "Tier1"),
        ("Tier2", "Tier0", "Tier1", "Tier2"),
        ("Tier0", "Tier2", "Tier1", "Tier0"),
        ("Tier1", "Tier0", "Tier2", "Tier1"),
        ("Tier2", "Tier1", "Tier0", "Tier2"),
    ]
    return combinations
