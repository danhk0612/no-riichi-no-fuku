"""Serial wall/CPU timing and complete repeated seeded match trace check."""
import json
from pathlib import Path
import statistics
import sys
import time

from compare import match
from profiles import PROFILES, ProfileAgent
from verify import corpus


def benchmark():
    observations = corpus()
    timings = []
    for level in (1, 5, 10):
        agent = ProfileAgent(PROFILES[level - 1], seed=9001)
        wall, cpu = [], []
        for obs in observations:
            before_wall, before_cpu = time.perf_counter_ns(), time.process_time_ns()
            agent.choose_action(obs)
            cpu.append((time.process_time_ns() - before_cpu) / 1e6)
            wall.append((time.perf_counter_ns() - before_wall) / 1e6)
        timings.append(dict(level=level, decisions=len(wall), wall_mean_ms=statistics.mean(wall),
                            wall_p95_ms=sorted(wall)[int((len(wall) - 1) * .95)],
                            wall_max_ms=max(wall), cpu_mean_ms=statistics.mean(cpu),
                            cpu_p95_ms=sorted(cpu)[int((len(cpu) - 1) * .95)], cpu_max_ms=max(cpu)))
    repeats = []
    for level in (1, 5, 10):
        a, b = match((level, 107, 2)), match((level, 107, 2))
        assert all(a[k] == b[k] for k in ("trace", "scores", "ranks", "steps"))
        repeats.append(dict(level=level, seed=107, seat=2, trace=a["trace"],
                            scores=a["scores"], ranks=a["ranks"], steps=a["steps"]))
    return dict(corpus_seed=117, agent_seed=9001, timings=timings,
                repeated_full_match_traces=repeats)


if __name__ == "__main__":
    Path(sys.argv[1]).write_text(json.dumps(benchmark(), indent=2) + "\n")
