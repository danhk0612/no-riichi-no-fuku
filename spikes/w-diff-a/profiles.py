"""Isolated candidate v1. Never imported by the production application."""
from dataclasses import dataclass
import random

from riichienv import ActionType

from app.mahjong.tier2 import Tier2Agent


@dataclass(frozen=True)
class Profile:
    level: int
    discard_lapse: float
    version: str = "tier2-lapse-v1"


PROFILES = tuple(Profile(level, (10 - level) / 10) for level in range(1, 11))


class ProfileAgent:
    """Keep personality intact; occasionally replace a discard with a legal one.

    All win/riichi/call/fold evaluation stays in the existing policy-2 agent.
    A lapse can override its fold discard too. This measures loss of decision
    accuracy, not improved search or a claim of ten calibrated strength bands.
    """

    def __init__(self, profile, *, seed, **personality):
        self.profile = profile
        self.expert = Tier2Agent(seed=seed, policy_version=2, **personality)
        self.lapse_rng = random.Random(seed ^ 0x574449464641)
        self.decisions = self.lapses = self.changed = 0

    def choose_action(self, observation):
        selected = self.expert.choose_action(observation)
        self.decisions += 1
        if selected.action_type != ActionType.DISCARD or not self.profile.discard_lapse:
            return selected
        candidates = [a for a in observation.legal_actions()
                      if a.action_type == ActionType.DISCARD]
        if len(candidates) > 1 and self.lapse_rng.random() < self.profile.discard_lapse:
            self.lapses += 1
            replacement = self.lapse_rng.choice(candidates)
            self.changed += replacement.to_dict() != selected.to_dict()
            return replacement
        return selected
