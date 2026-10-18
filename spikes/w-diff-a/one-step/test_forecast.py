"""Independent small leaf/inventory checks; no experimental observations."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from validate import HERE
from one_step import Search, OneStepAgent, PROFILES
from test_search import HAND
from riichienv import calculate_shanten, ActionType

class ForecastTests(unittest.TestCase):
    def test_fold_and_nondiscard_never_enter_search(self):
        for action_type, fold in ((ActionType.DISCARD, True), (ActionType.TSUMO, False)):
            action = SimpleNamespace(action_type=action_type, to_dict=lambda:dict(type=int(action_type)))
            expert = SimpleNamespace()
            def choose(observation):
                expert.fold = fold
                return action
            expert.choose_action = choose
            agent = OneStepAgent(PROFILES[1], seed=1)
            agent.expert = expert
            with patch('one_step.Search', side_effect=AssertionError('protected action entered search')):
                self.assertIs(agent.choose_action(object()), action)

    def test_single_possible_draw_completes_shape_without_returning_seen_tiles(self):
        remaining = [0]*34
        remaining[26] = 2  # Two unseen 9s; 7s8s completes on the simulated draw.
        hand = list(HAND)
        before = list(remaining)
        self.assertEqual(Search(100).value(hand, remaining), 1)
        self.assertEqual(hand, HAND)
        self.assertEqual(remaining, before)

    def test_cached_ukeire_matches_direct_independent_enumeration(self):
        counts = [0]*34
        for t in HAND:
            counts[t//4] += 1
        remaining = [4-n for n in counts]
        shanten = calculate_shanten(HAND)
        expected = 0
        for kind, n in enumerate(remaining):
            if n:
                tile = next(t for t in range(4*kind,4*kind+4) if t not in HAND)
                if calculate_shanten([*HAND,tile]) < shanten:
                    expected += n
        before = list(counts)
        self.assertEqual(Search(100).ukeire(counts, remaining, shanten), expected)
        self.assertEqual(counts, before)

if __name__=='__main__':
    unittest.main()
