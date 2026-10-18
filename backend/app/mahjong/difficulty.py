"""Immutable bounded-lapse profiles using the suit-corrected Tier2 policy."""
from dataclasses import dataclass
import random
from riichienv import ActionType
from app.mahjong.tier2 import Tier2Agent

@dataclass(frozen=True)
class Profile:
    level: int
    lapse_numerator: int
    version: str = "tier2-bounded-lapse-suitfix-v1"
    denominator: int = 1000
    max_shanten_excess: int = 1
    max_tile_kinds: int = 6

PROFILES = tuple(Profile(i, p) for i, p in enumerate(
    (650, 480, 380, 290, 210, 145, 90, 50, 20, 0), 1))

class RecordingTier2(Tier2Agent):
    """Observe evaluations already made by the unmodified policy2 code."""
    def _evaluate_discard(self, observation, action, game_state):
        evaluation = super()._evaluate_discard(observation, action, game_state)
        self.evaluations.append(evaluation)
        return evaluation

    def _should_fold(self, observation, evaluations, game_state):
        self.fold = super()._should_fold(observation, evaluations, game_state)
        self.state = game_state
        return self.fold

class ProfileAgent:
    def __init__(self, profile, *, seed, **personality):
        self.profile = profile
        self.expert = RecordingTier2(seed=seed, policy_version=2, **personality)
        self.lapse_rng = random.Random(seed ^ 0x574449464641)
        self.decisions = self.lapses = self.changed = self.protected_folds = 0
        self.last_selected = None
        self.last_pool = []

    def choose_action(self, observation):
        self.expert.evaluations = []
        self.expert.fold = False
        selected = self.expert.choose_action(observation)
        self.last_selected = selected
        self.last_pool = []
        self.decisions += 1
        if selected.action_type != ActionType.DISCARD:
            return selected
        if self.expert.fold:
            self.protected_folds += 1
            return selected
        p = self.profile
        if not p.lapse_numerator:
            return selected
        evaluations = self.expert.evaluations
        best = min(e.shanten for e in evaluations)
        bounded = [e for e in evaluations if e.shanten <= best + p.max_shanten_excess]
        bounded.sort(key=lambda e: (e.shanten, -self.expert._compute_expected_value(e, self.expert.state), e.action.tile))
        # Physical copies must not overweight a tile kind. Keep first legal copy.
        kinds = {}
        for e in bounded:
            kinds.setdefault(e.action.tile // 4, e)
        pool = list(kinds.values())[:p.max_tile_kinds]
        self.last_pool = pool
        if len(pool) > 1 and self.lapse_rng.random() < p.lapse_numerator / p.denominator:
            self.lapses += 1
            weights = [max(1, int(10 + self.expert._compute_expected_value(e, self.expert.state) * 10))
                       / (4 if e.shanten > best else 1) for e in pool]
            action = self.lapse_rng.choices(pool, weights=weights, k=1)[0].action
            self.changed += action.to_dict() != selected.to_dict()
            return action
        return selected
