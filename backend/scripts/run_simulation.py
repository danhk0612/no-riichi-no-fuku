#!/usr/bin/env python3
"""Run tournament simulation and output analysis results."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.simulation.tournament import (
    analyze_results,
    generate_balanced_combinations,
    run_tournament,
)


def format_statistics_table(stats_by_tier):
    """Format tier statistics as a markdown table."""
    lines = [
        "| Tier | Matches | Avg Rank | Avg Score | 1st Rate | 4th Rate | Rank Distribution |",
        "|------|---------|----------|-----------|----------|----------|-------------------|",
    ]

    for tier in ["Tier0", "Tier1", "Tier2"]:
        stats = stats_by_tier[tier]
        rank_dist = ", ".join(
            f"{rank}위:{stats.rank_counts.get(rank, 0)}"
            for rank in [1, 2, 3, 4]
        )
        lines.append(
            f"| {tier} | {stats.match_count} | {stats.average_rank:.3f} | "
            f"{stats.average_score:.1f} | {stats.first_place_rate:.1%} | "
            f"{stats.fourth_place_rate:.1%} | {rank_dist} |"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Run fixed-seed tournament simulation for tier analysis"
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[5, 7, 11, 13, 17, 19, 23, 29, 31, 37],
        help="Match seeds to test (default: first 10 primes)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output file for raw results",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        help="Optional markdown output file for formatted results",
    )
    args = parser.parse_args()

    print(f"Running tournament with {len(args.seeds)} seeds...")
    print(f"Seeds: {args.seeds}")

    combinations = generate_balanced_combinations()
    print(f"Testing {len(combinations)} tier combinations per seed")

    results = run_tournament(seeds=args.seeds, tier_combinations=combinations)
    print(f"Completed {len(results)} matches\n")

    stats_by_tier = analyze_results(results)

    print("=== Tournament Results ===\n")
    print(format_statistics_table(stats_by_tier))
    print()

    if args.output:
        output_data = {
            "seeds": args.seeds,
            "total_matches": len(results),
            "statistics": {
                tier: {
                    "match_count": stats.match_count,
                    "average_rank": stats.average_rank,
                    "average_score": stats.average_score,
                    "first_place_rate": stats.first_place_rate,
                    "fourth_place_rate": stats.fourth_place_rate,
                    "rank_counts": stats.rank_counts,
                }
                for tier, stats in stats_by_tier.items()
            },
            "matches": [
                {
                    "seed": r.match_seed,
                    "tiers": r.seat_tiers,
                    "scores": r.scores,
                    "ranks": r.ranks,
                    "steps": r.steps,
                }
                for r in results
            ],
        }
        args.output.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
        print(f"Raw results saved to {args.output}")

    if args.markdown:
        md_lines = [
            "# Tier Tournament Simulation Results",
            "",
            f"- Seeds tested: {len(args.seeds)}",
            f"- Total matches: {len(results)}",
            f"- Combinations per seed: {len(combinations)}",
            "",
            "## Aggregate Statistics",
            "",
            format_statistics_table(stats_by_tier),
            "",
            "## Methodology",
            "",
            "Each tier was tested across multiple fixed seeds with balanced seat assignments.",
            "Combinations include homogeneous (all same tier) and heterogeneous (mixed tiers) matches.",
            "",
            f"Seeds: {', '.join(map(str, args.seeds))}",
        ]
        args.markdown.write_text("\n".join(md_lines), encoding="utf-8")
        print(f"Markdown report saved to {args.markdown}")


if __name__ == "__main__":
    main()
