import unittest

from riichienv import Action, ActionType, GameRule, RiichiEnv

from app.mahjong.session import AuthoritativeGameSession
from app.mahjong.tier1 import Tier1Agent


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


class Tier1AgentTest(unittest.TestCase):
    def test_winning_action_is_prioritized(self) -> None:
        discard = Action(type=ActionType.DISCARD, tile=0, actor=1)
        ron = Action(type=ActionType.RON, actor=1)
        observation = StubObservation([discard, ron])

        selected = Tier1Agent(seed=1).choose_action(observation)  # type: ignore[arg-type]

        self.assertEqual(selected.to_dict(), ron.to_dict())

    def test_same_seed_produces_same_legal_discard_sequence(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=7,
        )
        observation = env.reset()[0]
        legal_values = [action.to_dict() for action in observation.legal_actions()]
        left = Tier1Agent(seed=101)
        right = Tier1Agent(seed=101)

        left_choices = [left.choose_action(observation).to_dict() for _ in range(20)]
        right_choices = [right.choose_action(observation).to_dict() for _ in range(20)]

        self.assertEqual(left_choices, right_choices)
        self.assertTrue(all(choice in legal_values for choice in left_choices))

    def test_discard_considers_dora_and_value(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=7,
        )
        observation = env.reset()[0]
        agent = Tier1Agent(seed=101)
        discards = [
            action
            for action in observation.legal_actions()
            if action.action_type == ActionType.DISCARD
        ]
        evaluations = [
            agent._evaluate_discard(observation, action) for action in discards
        ]

        self.assertTrue(len(evaluations) > 0)
        self.assertTrue(all(hasattr(e, "dora_count") for e in evaluations))
        self.assertTrue(all(hasattr(e, "potential_yaku_bonus") for e in evaluations))

    def test_danger_level_increases_against_riichi(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=7,
        )
        observation = env.reset()[0]
        agent = Tier1Agent(seed=101)
        discards = observation.legal_actions()

        safe_action = discards[0]
        unsafe_action = discards[1]

        class RiichiObservationView:
            def __init__(self, obs, safe_tile: int) -> None:
                self.hand = obs.hand
                self.player_id = obs.player_id
                self._observation = obs
                self._safe_tile = safe_tile

            def to_dict(self) -> dict[str, object]:
                data = self._observation.to_dict()
                data["riichi_declared"] = [False, True, False, False]
                data["discards"] = [[], [self._safe_tile], [], []]
                return data

        safe_tile = (safe_action.tile // 4) * 4
        view = RiichiObservationView(observation, safe_tile)

        safe_eval = agent._evaluate_discard(view, safe_action)  # type: ignore[arg-type]
        unsafe_eval = agent._evaluate_discard(view, unsafe_action)  # type: ignore[arg-type]

        self.assertEqual(safe_eval.safe_against_riichi, 1)
        self.assertLessEqual(safe_eval.danger_level, unsafe_eval.danger_level)

    def test_three_tier_one_cpus_complete_fixed_seed_east_match(self) -> None:
        agents = {seat: Tier1Agent(seed=600 + seat) for seat in (1, 2, 3)}
        game = AuthoritativeGameSession(
            user_id=10,
            cpu_character_ids=(101, 102, 103),
            cpu_agents=agents,
            seed=7,
        )
        game.start()

        human_turns = 0
        while not game.done:
            turn = game.human_turn()
            assert turn is not None
            human_turns += 1
            game.submit_human_action(choose_human_action_index(turn.legal_actions))

        result = game.result()
        self.assertEqual(len(result.scores), 4)
        self.assertEqual(len(result.ranks), 4)
        self.assertGreater(game.steps, 0)
        self.assertGreater(human_turns, 0)

    def test_tier1_behaves_differently_from_tier0(self) -> None:
        """Tier1 should produce different results when playing a full match against Tier0."""
        from app.mahjong.tier0 import Tier0Agent

        tier0_agents = {seat: Tier0Agent(seed=300 + seat) for seat in (1, 2, 3)}
        tier1_agents = {seat: Tier1Agent(seed=300 + seat) for seat in (1, 2, 3)}

        tier0_game = AuthoritativeGameSession(
            user_id=10,
            cpu_character_ids=(101, 102, 103),
            cpu_agents=tier0_agents,
            seed=15,
        )
        tier0_game.start()

        tier1_game = AuthoritativeGameSession(
            user_id=10,
            cpu_character_ids=(101, 102, 103),
            cpu_agents=tier1_agents,
            seed=15,
        )
        tier1_game.start()

        tier0_human_actions = []
        tier1_human_actions = []

        while not tier0_game.done:
            turn = tier0_game.human_turn()
            assert turn is not None
            action_idx = choose_human_action_index(turn.legal_actions)
            tier0_human_actions.append(action_idx)
            tier0_game.submit_human_action(action_idx)

        while not tier1_game.done:
            turn = tier1_game.human_turn()
            assert turn is not None
            action_idx = choose_human_action_index(turn.legal_actions)
            tier1_human_actions.append(action_idx)
            tier1_game.submit_human_action(action_idx)

        tier0_result = tier0_game.result()
        tier1_result = tier1_game.result()

        self.assertNotEqual(
            tier0_result.scores,
            tier1_result.scores,
            "Tier1 should produce different game outcomes from Tier0"
        )


if __name__ == "__main__":
    unittest.main()
