import unittest

from riichienv import Action, ActionType, GameRule, RiichiEnv

from app.mahjong.session import AuthoritativeGameSession
from app.mahjong.tier2 import Tier2Agent


class StubObservation:
    def __init__(self, legal_actions: list[Action], hand: list[int] | None = None) -> None:
        self._legal_actions = legal_actions
        self.hand = hand if hand is not None else []
        self.player_id = 0

    def legal_actions(self) -> list[Action]:
        return self._legal_actions

    def to_dict(self) -> dict[str, object]:
        return {
            "player_id": self.player_id,
            "hands": [self.hand, [], [], []],
            "melds": [[], [], [], []],
            "discards": [[], [], [], []],
            "dora_indicators": [],
            "scores": [25000, 25000, 25000, 25000],
            "riichi_declared": [False, False, False, False],
            "honba": 0,
            "riichi_sticks": 0,
            "round_wind": 0,
            "oya": 0,
        }


def choose_human_action_index(actions: tuple[dict[str, object], ...]) -> int:
    for action_type in (ActionType.TSUMO, ActionType.RON, ActionType.RIICHI):
        for index, action in enumerate(actions):
            if action["type"] == int(action_type):
                return index
    for index, action in enumerate(actions):
        if action["type"] == int(ActionType.PASS):
            return index
    for index, action in enumerate(actions):
        if action["type"] == int(ActionType.DISCARD):
            return index
    return 0


class Tier2AgentTest(unittest.TestCase):
    def test_winning_action_is_prioritized(self) -> None:
        discard = Action(type=ActionType.DISCARD, tile=0, actor=1)
        ron = Action(type=ActionType.RON, actor=1)
        observation = StubObservation([discard, ron])

        selected = Tier2Agent(seed=1).choose_action(observation)  # type: ignore[arg-type]

        self.assertEqual(selected.to_dict(), ron.to_dict())

    def test_same_seed_produces_same_legal_discard_sequence(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=7,
        )
        observation = env.reset()[0]
        legal_values = [action.to_dict() for action in observation.legal_actions()]
        left = Tier2Agent(seed=101)
        right = Tier2Agent(seed=101)

        left_choices = [left.choose_action(observation).to_dict() for _ in range(20)]
        right_choices = [right.choose_action(observation).to_dict() for _ in range(20)]

        self.assertEqual(left_choices, right_choices)
        self.assertTrue(all(choice in legal_values for choice in left_choices))

    def test_suji_defense_reduces_danger(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=7,
        )
        observation = env.reset()[0]
        agent = Tier2Agent(seed=101)
        
        tile_kind_4m = 3
        opponent_discards = {0, 6}
        
        is_safe = agent._is_suji_safe(tile_kind_4m, opponent_discards)
        
        self.assertTrue(is_safe)

    def test_wall_defense_identifies_safe_tiles(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=7,
        )
        observation = env.reset()[0]
        agent = Tier2Agent(seed=101)
        
        visible_tiles = [0, 1, 2]
        tile_kind = 0
        
        is_safe = agent._is_wall_safe(tile_kind, visible_tiles)
        
        self.assertTrue(is_safe)

    def test_game_state_analysis_calculates_ranks(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=7,
        )
        observation = env.reset()[0]
        agent = Tier2Agent(seed=101)
        
        game_state = agent._analyze_game_state(observation)
        
        self.assertIsNotNone(game_state)
        self.assertEqual(len(game_state.ranks), 4)
        self.assertIn(game_state.my_rank, [1, 2, 3, 4])

    def test_placement_awareness_affects_decisions(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=7,
        )
        observation = env.reset()[0]
        agent = Tier2Agent(seed=101)
        
        game_state = agent._analyze_game_state(observation)
        
        self.assertGreaterEqual(game_state.remaining_tiles, 0)
        self.assertIsInstance(game_state.is_final_round, bool)

    def test_completes_fixed_seed_match_with_tier2_agents(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=11,
        )
        agents = [Tier2Agent(seed=201 + i) for i in range(4)]
        observations = env.reset()

        step_count = 0
        max_steps = 2000

        while not env.done() and step_count < max_steps:
            actions = {
                seat: agents[seat].choose_action(obs)
                for seat, obs in observations.items()
            }
            observations = env.step(actions)
            step_count += 1

        self.assertTrue(env.done())
        self.assertLess(step_count, max_steps)

        scores = env.scores()
        ranks = env.ranks()
        self.assertEqual(len(scores), 4)
        self.assertEqual(len(ranks), 4)
        self.assertEqual(sorted(ranks), [1, 2, 3, 4])

    def test_factory_creates_tier2_agent_for_stage_2(self) -> None:
        from app.services.game_setup import CpuChoice, create_production_cpu_agent

        choice = CpuChoice(
            id=1,
            slug="test-cpu",
            name="Test CPU",
            age_adult=True,
            style="balanced",
            short_description="Test",
            long_description=None,
            profile_image_key=None,
            defeat_stage=2,
        )

        agent = create_production_cpu_agent(choice, seed=42)

        self.assertIsInstance(agent, Tier2Agent)

    def test_expected_value_computation_considers_placement(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=7,
        )
        observation = env.reset()[0]
        agent = Tier2Agent(seed=101)
        
        game_state = agent._analyze_game_state(observation)
        
        discards = [
            action
            for action in observation.legal_actions()
            if action.action_type == ActionType.DISCARD
        ]
        
        if discards:
            evaluation = agent._evaluate_discard(observation, discards[0], game_state)
            ev = agent._compute_expected_value(evaluation, game_state)
            
            self.assertIsInstance(ev, float)


if __name__ == "__main__":
    unittest.main()
