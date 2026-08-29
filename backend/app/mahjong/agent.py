from typing import Protocol

from riichienv import Action, Observation


class MahjongAgent(Protocol):
    def choose_action(self, observation: Observation) -> Action: ...
