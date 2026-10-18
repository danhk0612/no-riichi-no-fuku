"""Isolated discard-only factorial probe; no production registration."""
from dataclasses import dataclass, replace, asdict
import random
from riichienv import ActionType
from app.mahjong.tier2 import Tier2Agent

VERSION = 'decision-axis-probe-v1'
LABELS = tuple(f'{i:03b}' for i in range(8))

@dataclass(frozen=True)
class Profile:
    label: str
    version: str = VERSION

PROFILES = tuple(Profile(label) for label in LABELS)

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

def candidates(expert, evaluations):
    best = min(e.shanten for e in evaluations)
    efficient = [e for e in evaluations if e.shanten == best]
    cutoff = max(e.ukeire for e in efficient) - 4
    pool = [e for e in efficient if e.ukeire >= cutoff]
    return sorted(pool, key=lambda e: (-expert._compute_expected_value(e, expert.state), e.action.tile))

def base_danger(expert, tile, observation):
    data = observation.to_dict()
    kind = tile // 4
    return sum(expert._base_tile_danger(kind)
               for seat, declared in enumerate(data['riichi_declared'])
               if declared and seat != observation.player_id
               and kind not in {t // 4 for t in data['discards'][seat]})

class ProbeAgent:
    def __init__(self, profile, *, seed, **personality):
        if profile not in PROFILES:
            raise ValueError('unknown immutable probe profile')
        self.profile = profile
        self.expert = RecordingTier2(seed=seed, policy_version=2, **personality)
        self.last = {}

    def choose_action(self, observation):
        expert = self.expert
        expert.evaluations, expert.fold = [], False
        selected = expert.choose_action(observation)
        self.last = dict(baseline=selected.to_dict(), fold=expert.fold, pool=[],
                         original_pool=[], ukeire_changes=0, danger_changes=0)
        if selected.action_type != ActionType.DISCARD or expert.fold:
            return selected
        u, d, m = map(int, self.profile.label)
        original = expert.evaluations
        evaluated = [replace(e, ukeire=4*(e.ukeire//4) if u else e.ukeire,
                             danger_score=base_danger(expert,e.action.tile,observation) if d else e.danger_score)
                     for e in original]
        pool = candidates(expert, evaluated)
        self.last.update(pool=[e.action.to_dict() for e in pool],
                         original_pool=[e.action.to_dict() for e in candidates(expert, original)],
                         ukeire_changes=sum(a.ukeire != b.ukeire for a,b in zip(original,evaluated)),
                         danger_changes=sum(a.danger_score != b.danger_score for a,b in zip(original,evaluated)))
        if self.profile.label == '000':
            return selected
        if m:
            return pool[0].action
        # Clone the original pre-discard RNG: same random quantile across axes.
        # Shadow expert consumes exactly its original draws; this clone cannot
        # affect future calls/riichi/fold or any engine/content RNG.
        rng = random.Random()
        rng.setstate(expert.selection_state)
        weights = [max(1,int(10+expert._compute_expected_value(e,expert.state)*10)) for e in pool]
        return rng.choices(pool, weights=weights, k=1)[0].action

def validate_profile(data):
    if data not in [asdict(p) for p in PROFILES]:
        raise ValueError('unknown immutable probe profile')
    return PROFILES[LABELS.index(data['label'])]
