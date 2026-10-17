"""Seeded, seat-rotated matches against three unchanged policy-2 Tier2 agents."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time

from app.mahjong.riichienv_adapter import RiichiEnvAdapter
from app.mahjong.tier0 import Tier0Agent
from app.mahjong.tier1 import Tier1Agent
from app.mahjong.tier2 import Tier2Agent
from profiles import PROFILES, ProfileAgent


def match(job):
    label, seed, seat = job
    agents = [Tier2Agent(seed=seed * 10 + s) for s in range(4)]
    if isinstance(label, int):
        agents[seat] = ProfileAgent(PROFILES[label - 1], seed=seed * 10 + seat)
    elif label == "tier0":
        agents[seat] = Tier0Agent(seed=seed * 10 + seat)
    elif label == "tier1":
        agents[seat] = Tier1Agent(seed=seed * 10 + seat)
    adapter = RiichiEnvAdapter(seed=seed)
    adapter.start()
    trace = hashlib.sha256()
    durations = []
    steps = 0
    started = time.perf_counter()
    while not adapter.done:
        actions = {}
        for s, observation in adapter.pending_observations.items():
            before = time.perf_counter_ns()
            actions[s] = agents[s].choose_action(observation)
            if s == seat:
                durations.append((time.perf_counter_ns() - before) / 1e6)
        trace.update(json.dumps({s: a.to_dict() for s, a in actions.items()},
                                sort_keys=True).encode())
        adapter.step(actions)  # validates every seat's action against legal actions
        steps += 1
        if steps > 5000:
            raise AssertionError("step limit")
    result = adapter.result()
    target = agents[seat]
    return dict(label=label, seed=seed, seat=seat, scores=result.scores,
                ranks=result.ranks, steps=steps, trace=trace.hexdigest(),
                elapsed_s=time.perf_counter() - started,
                decisions=len(durations), decision_ms_sum=sum(durations),
                decision_ms_p95=sorted(durations)[int((len(durations) - 1) * .95)],
                decision_ms_max=max(durations),
                lapses=getattr(target, "lapses", 0),
                changed=getattr(target, "changed", 0))


def summarize(rows):
    result = []
    for label in dict.fromkeys(row["label"] for row in rows):
        group = [r for r in rows if r["label"] == label]
        scores = [r["scores"][r["seat"]] for r in group]
        ranks = [r["ranks"][r["seat"]] for r in group]
        # Use seed blocks, not correlated seat rotations, for uncertainty.
        blocks = [statistics.mean(r["scores"][r["seat"]] for r in group if r["seed"] == s)
                  for s in sorted({r["seed"] for r in group})]
        result.append(dict(label=label, matches=len(group), mean_score=statistics.mean(scores),
                           mean_rank=statistics.mean(ranks), first=ranks.count(1),
                           last=ranks.count(4), seed_block_score_se=(statistics.stdev(blocks)
                           / len(blocks) ** .5 if len(blocks) > 1 else None),
                           decision_ms_mean=sum(r["decision_ms_sum"] for r in group)
                           / sum(r["decisions"] for r in group),
                           max_match_p95_ms=max(r["decision_ms_p95"] for r in group),
                           decision_ms_max=max(r["decision_ms_max"] for r in group),
                           decisions=sum(r["decisions"] for r in group),
                           lapses=sum(r["lapses"] for r in group),
                           changed=sum(r["changed"] for r in group)))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    labels = [*range(1, 11), "tier0", "tier1", "tier2"]
    jobs = [(label, seed, seat) for label in labels
            for seed in range(100, 100 + args.seeds) for seat in range(4)]
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = []
        for row in pool.map(match, jobs):
            rows.append(row)
            if len(rows) % (args.seeds * 4) == 0:
                print(json.dumps(summarize(rows)[-1]), flush=True)
    payload = dict(source="8fb9b80a471090b43ac648597051e788c0767186",
                   python=platform.python_version(), platform=platform.platform(),
                   riichienv="0.4.8", seed_start=100, seed_count=args.seeds,
                   workers=args.workers, elapsed_s=time.perf_counter() - started,
                   profiles=[asdict(p) for p in PROFILES],
                   summary=summarize(rows), matches=rows)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
