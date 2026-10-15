import json
import unittest
from pathlib import Path

from app.simulation.tournament import (
    MatchConfig,
    TierStatistics,
    analyze_results,
    generate_balanced_combinations,
    run_single_match,
    run_tournament,
)


class TournamentTest(unittest.TestCase):
    def test_single_match_completes_with_fixed_seed(self) -> None:
        config = MatchConfig(
            match_seed=5,
            seat_tiers=("Tier0", "Tier1", "Tier2", "Tier0"),
        )

        result = run_single_match(config)

        self.assertEqual(result.match_seed, 5)
        self.assertEqual(result.seat_tiers, ("Tier0", "Tier1", "Tier2", "Tier0"))
        self.assertEqual(len(result.scores), 4)
        self.assertEqual(len(result.ranks), 4)
        self.assertGreater(result.steps, 0)
        self.assertEqual(set(result.ranks), {1, 2, 3, 4})

    def test_homogeneous_tier0_match_produces_varied_ranks(self) -> None:
        config = MatchConfig(
            match_seed=7,
            seat_tiers=("Tier0", "Tier0", "Tier0", "Tier0"),
        )

        result = run_single_match(config)

        self.assertEqual(set(result.ranks), {1, 2, 3, 4})

    def test_tournament_runs_multiple_seeds_and_combinations(self) -> None:
        seeds = [5, 7]
        combinations = [
            ("Tier0", "Tier0", "Tier0", "Tier0"),
            ("Tier1", "Tier1", "Tier1", "Tier1"),
        ]

        results = run_tournament(seeds=seeds, tier_combinations=combinations)

        self.assertEqual(len(results), 4)
        unique_configs = {(r.match_seed, r.seat_tiers) for r in results}
        self.assertEqual(len(unique_configs), 4)

    def test_analyze_results_computes_tier_statistics(self) -> None:
        seeds = [5, 7]
        combinations = [
            ("Tier0", "Tier1", "Tier2", "Tier0"),
            ("Tier1", "Tier2", "Tier0", "Tier1"),
        ]
        results = run_tournament(seeds=seeds, tier_combinations=combinations)

        stats_by_tier = analyze_results(results)

        self.assertIn("Tier0", stats_by_tier)
        self.assertIn("Tier1", stats_by_tier)
        self.assertIn("Tier2", stats_by_tier)

        for tier, stats in stats_by_tier.items():
            self.assertIsInstance(stats, TierStatistics)
            self.assertEqual(stats.tier, tier)
            self.assertGreater(stats.match_count, 0)
            self.assertGreaterEqual(stats.average_rank, 1.0)
            self.assertLessEqual(stats.average_rank, 4.0)
            self.assertGreaterEqual(stats.first_place_rate, 0.0)
            self.assertLessEqual(stats.first_place_rate, 1.0)
            self.assertGreaterEqual(stats.fourth_place_rate, 0.0)
            self.assertLessEqual(stats.fourth_place_rate, 1.0)

    def test_balanced_combinations_cover_all_tiers(self) -> None:
        combinations = generate_balanced_combinations()

        tier_seat_counts = {"Tier0": 0, "Tier1": 0, "Tier2": 0}
        for combo in combinations:
            for tier in combo:
                tier_seat_counts[tier] += 1

        self.assertGreater(len(combinations), 0)
        for tier, count in tier_seat_counts.items():
            self.assertGreater(count, 0, f"{tier} should appear at least once")

    def test_tier_statistics_properties(self) -> None:
        stats = TierStatistics(
            tier="Tier0",
            match_count=10,
            rank_counts={1: 3, 2: 2, 3: 3, 4: 2},
            total_score=250000,
            first_place_count=3,
            fourth_place_count=2,
        )

        self.assertEqual(stats.average_rank, 2.4)
        self.assertEqual(stats.average_score, 25000.0)
        self.assertEqual(stats.first_place_rate, 0.3)
        self.assertEqual(stats.fourth_place_rate, 0.2)

    def test_small_tournament_produces_complete_results(self) -> None:
        """Integration test: run a small tournament and verify all data is present."""
        seeds = [5, 7, 11]
        combinations = generate_balanced_combinations()

        results = run_tournament(seeds=seeds, tier_combinations=combinations)
        stats_by_tier = analyze_results(results)

        expected_matches = len(seeds) * len(combinations)
        self.assertEqual(len(results), expected_matches)

        total_tier_matches = sum(s.match_count for s in stats_by_tier.values())
        self.assertEqual(total_tier_matches, expected_matches * 4)

        for tier in ["Tier0", "Tier1", "Tier2"]:
            stats = stats_by_tier[tier]
            self.assertGreater(stats.match_count, 0)
            rank_sum = sum(stats.rank_counts.values())
            self.assertEqual(rank_sum, stats.match_count)


if __name__ == "__main__":
    unittest.main()
