"""Synthetic shape/inventory/budget checks before freezing measurement code."""
import unittest
from types import SimpleNamespace
from dataclasses import asdict
from validate import PROFILES, validate_profile
from one_step import Search, SearchBudgetExceeded, public_remaining
from riichienv import calculate_shanten

HAND = [0,4,8,36,40,44,72,76,80,108,109,96,100]

class SearchTests(unittest.TestCase):
    def test_canonical_shanten_and_completed_leaf(self):
        counts = [0]*34
        for tile in [*HAND,104]:
            counts[tile//4] += 1
        search = Search(100)
        self.assertEqual(search.shanten(counts), calculate_shanten([*HAND,104]))
        self.assertEqual(search.shanten(counts), -1)
        self.assertEqual(search.after_draw(counts, [2]*34), 68)

    def test_seen_physical_copy_is_not_double_counted(self):
        obs = SimpleNamespace(hand=[0,1], to_dict=lambda:dict(
            discards=[[0],[],[],[]], dora_indicators=[8],
            melds=[[SimpleNamespace(tiles=[0,2,3])],[],[],[]]))
        remaining = public_remaining(obs)
        self.assertEqual(remaining[0], 0)
        self.assertEqual(remaining[2], 3)
        self.assertEqual(remaining[1], 4)

    def test_no_unseen_tiles_has_no_forecast(self):
        self.assertIsNone(Search(1).value(HAND, [0]*34))

    def test_budget_is_deterministic_and_cache_hits_are_free(self):
        search = Search(1)
        a = [0]*34
        a[0]=1
        first = search.shanten(a)
        self.assertEqual(search.shanten(a), first)
        a[1]=1
        with self.assertRaises(SearchBudgetExceeded):
            search.shanten(a)

    def test_profile_identity_rejects_bool_and_future_version(self):
        for mutation in (dict(blend_numerator=True), dict(version='future'), dict(node_limit=3)):
            with self.assertRaises(ValueError):
                validate_profile(dict(asdict(PROFILES[1]), **mutation))

if __name__=='__main__':
    unittest.main()
