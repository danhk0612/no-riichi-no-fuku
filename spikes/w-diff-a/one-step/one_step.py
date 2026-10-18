"""Finite own-draw/discard lookahead using public observations only."""
from dataclasses import dataclass, replace, asdict
from collections import Counter
import random
from riichienv import ActionType, calculate_shanten
from app.mahjong.tier2 import Tier2Agent

VERSION = 'public-one-draw-v1'

@dataclass(frozen=True)
class Profile:
    label: str
    blend_numerator: int
    version: str = VERSION
    denominator: int = 4
    node_limit: int = 50000

PROFILES = (Profile('baseline', 0), Profile('candidate', 1))

def validate_profile(data):
    for p in PROFILES:
        expected = asdict(p)
        if isinstance(data, dict) and data.keys() == expected.keys() and all(
                type(data[k]) is type(v) and data[k] == v for k, v in expected.items()):
            return p
    raise ValueError('unknown immutable one-step profile')

def public_remaining(observation):
    data = observation.to_dict()
    seen = set(observation.hand)
    seen.update(t for row in data['discards'] for t in row)
    seen.update(data['dora_indicators'])
    seen.update(t for row in data['melds'] for meld in row for t in meld.tiles)
    counts = Counter(t // 4 for t in seen)
    return tuple(max(0, 4 - counts[k]) for k in range(34))

class SearchBudgetExceeded(RuntimeError):
    pass

class Search:
    def __init__(self, limit):
        self.limit = limit
        self.cache = {}

    def shanten(self, counts):
        key = tuple(counts)
        if key not in self.cache:
            if len(self.cache) >= self.limit:
                raise SearchBudgetExceeded(f'shanten cache miss limit {self.limit}')
            physical = [k * 4 + c for k, n in enumerate(key) for c in range(n)]
            self.cache[key] = calculate_shanten(physical)
        return self.cache[key]

    def ukeire(self, counts, remaining, shanten):
        total = 0
        for kind, unseen in enumerate(remaining):
            if unseen and counts[kind] < 4:
                counts[kind] += 1
                total += unseen * (self.shanten(counts) < shanten)
                counts[kind] -= 1
        return total

    def after_draw(self, counts, remaining):
        # This is shape completion, not a legal yaku/win prediction.
        if self.shanten(counts) == -1:
            return sum(remaining)
        options = []
        for kind, n in enumerate(counts):
            if n:
                counts[kind] -= 1
                options.append((self.shanten(counts), kind))
                counts[kind] += 1
        best = min(s for s, _ in options)
        result = 0
        for shanten, kind in options:
            if shanten == best:
                counts[kind] -= 1
                result = max(result, self.ukeire(counts, remaining, shanten))
                counts[kind] += 1
        return result

    def value(self, hand_after_discard, remaining):
        denominator = sum(remaining)
        if not denominator:
            return None
        counts = [0] * 34
        for tile in hand_after_discard:
            counts[tile // 4] += 1
        numerator = 0
        for kind, unseen in enumerate(remaining):
            if not unseen:
                continue
            assert counts[kind] < 4
            counts[kind] += 1
            after = list(remaining)
            after[kind] -= 1
            numerator += unseen * self.after_draw(counts, after)
            counts[kind] -= 1
        return numerator / denominator

class RecordingTier2(Tier2Agent):
    def _choose_discard(self, observation, discards, game_state):
        self.selection_state = self._rng.getstate()
        return super()._choose_discard(observation, discards, game_state)

    def _evaluate_discard(self, observation, action, game_state):
        value = super()._evaluate_discard(observation, action, game_state)
        self.evaluations.append(value)
        return value

    def _should_fold(self, observation, evaluations, game_state):
        self.fold = super()._should_fold(observation, evaluations, game_state)
        self.state = game_state
        return self.fold

class OneStepAgent:
    def __init__(self, profile, *, seed, **personality):
        self.profile = validate_profile(asdict(profile))
        self.expert = RecordingTier2(seed=seed, policy_version=2, **personality)
        self.last = {}

    def choose_action(self, observation):
        expert = self.expert
        expert.evaluations, expert.fold = [], False
        selected = expert.choose_action(observation)
        self.last = dict(baseline=selected.to_dict(), fold=expert.fold, nodes=0, values={})
        if not self.profile.blend_numerator or selected.action_type != ActionType.DISCARD or expert.fold:
            return selected
        evaluations = expert.evaluations
        best = min(e.shanten for e in evaluations)
        efficient = [e for e in evaluations if e.shanten == best]
        cutoff = max(e.ukeire for e in efficient) - 4
        pool = [e for e in efficient if e.ukeire >= cutoff]
        if len({e.action.tile // 4 for e in pool}) <= 1:
            return selected
        search = Search(self.profile.node_limit)
        remaining = public_remaining(observation)
        values = {}
        for e in pool:
            kind = e.action.tile // 4
            if kind not in values:
                hand = list(observation.hand)
                hand.remove(e.action.tile)
                value = search.value(hand, remaining)
                values[kind] = e.ukeire if value is None else value
        alpha = self.profile.blend_numerator / self.profile.denominator
        adjusted = [replace(e, ukeire=(1-alpha)*e.ukeire+alpha*values[e.action.tile//4]) for e in pool]
        adjusted.sort(key=lambda e: (-expert._compute_expected_value(e, expert.state), e.action.tile))
        weights = [max(1, int(10+expert._compute_expected_value(e, expert.state)*10)) for e in adjusted]
        rng = random.Random(0)
        rng.setstate(expert.selection_state)
        self.last.update(nodes=len(search.cache), values=values)
        return rng.choices(adjusted, weights=weights, k=1)[0].action
