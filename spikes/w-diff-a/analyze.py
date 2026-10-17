"""Descriptive seed-block paired intervals; rotations are not independent samples."""
import json
from pathlib import Path
import statistics
import sys


def analyze(data):
    rows = data["matches"]
    by_key = {(r["label"], r["seed"], r["seat"]): r for r in rows}
    seeds = sorted({r["seed"] for r in rows})
    assert len(seeds) == 32, "interval multiplier below is specified for 31 degrees of freedom"
    assert len(by_key) == 13 * 32 * 4
    for seed in seeds:
        for seat in range(4):
            a, b = (by_key[(label, seed, seat)] for label in (10, "tier2"))
            assert all(a[k] == b[k] for k in ("trace", "scores", "ranks", "steps"))
    pairs = []
    for low, high in [*((i, i + 1) for i in range(1, 10)), (1, 10), (5, 10),
                      ("tier0", 10), ("tier1", 10)]:
        entry = dict(low=low, high=high)
        for metric in ("scores", "ranks"):
            blocks = [statistics.mean(by_key[(high, seed, seat)][metric][seat]
                                      - by_key[(low, seed, seat)][metric][seat]
                                      for seat in range(4)) for seed in seeds]
            mean = statistics.mean(blocks)
            se = statistics.stdev(blocks) / len(blocks) ** .5
            entry[metric] = dict(mean_high_minus_low=mean, se=se,
                                descriptive_95_interval=[mean - 2.04 * se, mean + 2.04 * se])
        pairs.append(entry)
    return dict(independent_seed_blocks=len(seeds), rotations_per_block=4,
                interval="paired seed-block t approximation, df31, multiplier2.04; no multiplicity correction",
                level10_equals_tier2_all_128_traces=True, pairs=pairs,
                target_decisions=sum(r["decisions"] for r in rows))


if __name__ == "__main__":
    Path(sys.argv[2]).write_text(json.dumps(analyze(json.loads(Path(sys.argv[1]).read_text())), indent=2) + "\n")
