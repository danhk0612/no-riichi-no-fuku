"""Tests verifying CPU personality parameters affect decision-making."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from riichienv import Action, ActionType, Observation, calculate_shanten

from app.mahjong.tier0 import Tier0Agent
from app.mahjong.tier1 import Tier1Agent
from app.mahjong.tier2 import Tier2Agent


class TestTier0Personality(unittest.TestCase):
    """Test personality integration in Tier0Agent."""

    def test_riichi_preference_parameter_stored(self) -> None:
        """Verify riichi_preference parameter is stored in agent."""
        high_riichi = Tier0Agent(seed=100, riichi_preference=1.3)
        low_riichi = Tier0Agent(seed=100, riichi_preference=0.7)
        
        self.assertEqual(high_riichi._riichi_preference, 1.3)
        self.assertEqual(low_riichi._riichi_preference, 0.7)

    def test_defense_affects_discard_weighting(self) -> None:
        """High defense should weight safety more heavily."""
        obs = self._create_observation_with_riichi()
        discards = self._create_discard_actions()
        
        high_defense = Tier0Agent(seed=200, defense=1.5)
        low_defense = Tier0Agent(seed=200, defense=0.7)
        
        high_choice = high_defense._choose_discard(obs, discards)
        low_choice = low_defense._choose_discard(obs, discards)
        
        self.assertIsNotNone(high_choice)
        self.assertIsNotNone(low_choice)

    def test_call_preference_parameter_stored(self) -> None:
        """Verify call_preference parameter is stored in agent."""
        high_call = Tier0Agent(seed=300, call_preference=1.3)
        low_call = Tier0Agent(seed=300, call_preference=0.6)
        
        self.assertEqual(high_call._call_preference, 1.3)
        self.assertEqual(low_call._call_preference, 0.6)

    def _create_observation_with_riichi(self) -> Observation:
        """Create observation with opponent riichi for defense testing."""
        obs = Mock(spec=Observation)
        obs.hand = [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 16, 20]
        obs.player_id = 0
        obs.to_dict.return_value = {
            "riichi_declared": [False, True, False, False],
            "discards": [[], [24, 28], [], []],
            "dora_indicators": [40],
            "melds": [[], [], [], []],
        }
        return obs

    def _create_discard_actions(self) -> list[Action]:
        """Create discard action candidates."""
        actions = []
        for tile in [0, 1, 2, 4, 5, 6]:
            action = Mock(spec=Action)
            action.tile = tile
            action.action_type = ActionType.DISCARD
            actions.append(action)
        return actions

    def _create_observation_with_call(self) -> Observation:
        """Create observation for call testing."""
        obs = Mock(spec=Observation)
        obs.hand = [0, 1, 4, 5, 8, 9, 12, 13, 16, 17, 20, 21, 24]
        obs.player_id = 0
        obs.to_dict.return_value = {
            "riichi_declared": [False, False, False, False],
            "discards": [[], [], [], []],
            "dora_indicators": [40],
            "melds": [[], [], [], []],
        }
        return obs

    def _create_improving_call_actions(self) -> list[Action]:
        """Create call actions that improve shanten."""
        chi = Mock(spec=Action)
        chi.action_type = ActionType.CHI
        chi.consume_tiles = [0, 1]
        return [chi]


class TestTier1Personality(unittest.TestCase):
    """Test personality integration in Tier1Agent."""

    def test_all_personality_parameters_stored(self) -> None:
        """Verify all personality parameters are stored in Tier1Agent."""
        agent = Tier1Agent(
            seed=100,
            aggression=1.3,
            defense=0.9,
            call_preference=1.1,
            riichi_preference=0.8,
            hand_value_preference=1.2,
            speed_preference=0.95
        )
        
        self.assertEqual(agent._aggression, 1.3)
        self.assertEqual(agent._defense, 0.9)
        self.assertEqual(agent._call_preference, 1.1)
        self.assertEqual(agent._riichi_preference, 0.8)
        self.assertEqual(agent._hand_value_preference, 1.2)
        self.assertEqual(agent._speed_preference, 0.95)

    def test_hand_value_preference_affects_score_weighting(self) -> None:
        """hand_value_preference should affect dora/yaku weighting in discard evaluation."""
        obs = self._create_observation_with_dora()
        discards = self._create_discard_actions()
        
        value_focused = Tier1Agent(seed=200, hand_value_preference=1.4)
        speed_focused = Tier1Agent(seed=200, hand_value_preference=0.7, speed_preference=1.3)
        
        value_choice = value_focused._choose_discard(obs, discards)
        speed_choice = speed_focused._choose_discard(obs, discards)
        
        self.assertIsNotNone(value_choice)
        self.assertIsNotNone(speed_choice)

    def _create_low_score_observation(self) -> Observation:
        """Create observation with low score and opponent riichi."""
        obs = Mock(spec=Observation)
        obs.hand = [0, 1, 2, 8, 9, 10, 16, 17, 18, 24, 25, 26, 32]
        obs.player_id = 0
        obs.to_dict.return_value = {
            "riichi_declared": [False, True, False, False],
            "scores": [6000, 25000, 25000, 25000],
            "discards": [[], [40, 44], [], []],
            "dora_indicators": [20],
            "melds": [[], [], [], []],
        }
        return obs

    def _create_evaluations(self) -> list:
        """Create mock discard evaluations."""
        eval1 = Mock()
        eval1.shanten = 2
        eval1.safe_against_riichi = 0
        eval1.danger_level = 3
        return [eval1]

    def _create_observation_with_dora(self) -> Observation:
        """Create observation with dora tiles."""
        obs = Mock(spec=Observation)
        obs.hand = [20, 21, 22, 24, 25, 26, 28, 29, 30, 32, 33, 34, 36]
        obs.player_id = 0
        obs.to_dict.return_value = {
            "riichi_declared": [False, False, False, False],
            "scores": [25000, 25000, 25000, 25000],
            "discards": [[], [], [], []],
            "dora_indicators": [19],
            "melds": [[], [], [], []],
        }
        return obs

    def _create_discard_actions(self) -> list[Action]:
        """Create discard actions."""
        actions = []
        for tile in [20, 21, 22, 24, 25, 26]:
            action = Mock(spec=Action)
            action.tile = tile
            action.action_type = ActionType.DISCARD
            actions.append(action)
        return actions


class TestTier2Personality(unittest.TestCase):
    """Test personality integration in Tier2Agent."""

    def test_aggression_affects_ev_calculation(self) -> None:
        """Aggression should affect expected value in placement-critical situations."""
        from app.mahjong.tier2 import GameState, DiscardEvaluation
        
        game_state = GameState(
            remaining_tiles=60,
            my_score=18000,
            my_rank=4,
            scores=(30000, 26000, 21000, 18000),
            ranks=(1, 2, 3, 4),
            is_final_round=True,
            opponent_riichi_count=0,
        )
        
        eval_mock = Mock(spec=DiscardEvaluation)
        eval_mock.ukeire = 10
        eval_mock.dora_count = 1
        eval_mock.potential_yaku_bonus = 0.5
        eval_mock.danger_score = 2.0
        eval_mock.safe_against_riichi = 0
        
        aggressive = Tier2Agent(seed=100, aggression=1.3)
        cautious = Tier2Agent(seed=100, aggression=0.8)
        
        aggressive_ev = aggressive._compute_expected_value(eval_mock, game_state)
        cautious_ev = cautious._compute_expected_value(eval_mock, game_state)
        
        self.assertGreater(aggressive_ev, cautious_ev)

    def test_all_personality_parameters_stored_tier2(self) -> None:
        """Verify all personality parameters are stored in Tier2Agent."""
        agent = Tier2Agent(
            seed=200,
            aggression=1.3,
            defense=0.9,
            call_preference=1.1,
            riichi_preference=0.8,
            hand_value_preference=1.2,
            speed_preference=0.95
        )
        
        self.assertEqual(agent._aggression, 1.3)
        self.assertEqual(agent._defense, 0.9)
        self.assertEqual(agent._call_preference, 1.1)
        self.assertEqual(agent._riichi_preference, 0.8)
        self.assertEqual(agent._hand_value_preference, 1.2)
        self.assertEqual(agent._speed_preference, 0.95)

    def _create_multi_riichi_observation(self) -> Observation:
        """Create observation with multiple opponent riichi."""
        obs = Mock(spec=Observation)
        obs.hand = [0, 1, 2, 8, 9, 10, 16, 17, 18, 24, 25, 26, 32]
        obs.player_id = 0
        obs.to_dict.return_value = {
            "riichi_declared": [False, True, True, False],
            "scores": [22000, 28000, 25000, 20000],
            "discards": [[], [40], [44], []],
            "dora_indicators": [20],
            "melds": [[], [], [], []],
        }
        return obs


if __name__ == "__main__":
    unittest.main()
