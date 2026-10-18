import unittest
from types import SimpleNamespace

from app.mahjong.tier1 import Tier1Agent
from app.mahjong.tier2 import Tier2Agent


class CpuSuitEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.observation = SimpleNamespace(
            player_id=0, to_dict=lambda: {"melds": [[], [], [], []]}
        )

    def test_physical_copy_does_not_change_suit_bonus(self):
        # 8 and 9 are two physical copies of the same 3m tile, neither red.
        for agent in (Tier1Agent, Tier2Agent):
            with self.subTest(agent=agent.__name__):
                self.assertEqual(
                    agent._estimate_yaku_bonus([0, 4, 5, 8], self.observation),
                    agent._estimate_yaku_bonus([0, 4, 5, 9], self.observation),
                )

    def test_single_suit_across_all_ranks_gets_existing_bonus(self):
        # All hands contain terminals, so only the existing closed-hand and
        # single-suit heuristic terms apply. This is not a legal yaku scorer.
        for agent, closed, single_suit in ((Tier1Agent, .3, .8), (Tier2Agent, .4, 1.0)):
            for suit in range(3):
                hand = [4*(suit*9+rank) for rank in range(9)]
                hand += [hand[0]+1, hand[1]+1, hand[2]+1, hand[3]+1]
                with self.subTest(agent=agent.__name__, suit=suit):
                    self.assertAlmostEqual(
                        agent._estimate_yaku_bonus(hand, self.observation),
                        closed+single_suit,
                    )

    def test_mixed_suits_do_not_get_single_suit_bonus(self):
        for agent, closed in ((Tier1Agent, .3), (Tier2Agent, .4)):
            with self.subTest(agent=agent.__name__):
                self.assertAlmostEqual(
                    agent._estimate_yaku_bonus([0, 4, 36, 40], self.observation), closed
                )

    def test_honors_do_not_create_a_second_numbered_suit(self):
        for agent, closed, single_suit in ((Tier1Agent, .3, .8), (Tier2Agent, .4, 1.0)):
            with self.subTest(agent=agent.__name__):
                self.assertAlmostEqual(
                    agent._estimate_yaku_bonus([0, 4, 32, 108], self.observation),
                    closed+single_suit,
                )
                # Honor-only hand has no numbered suit and keeps the old score.
                self.assertAlmostEqual(
                    agent._estimate_yaku_bonus([108, 112, 116, 120], self.observation), closed
                )


if __name__ == "__main__":
    unittest.main()
