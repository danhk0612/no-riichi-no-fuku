import unittest

from riichienv import Action, ActionType, GameRule, RiichiEnv

from app.mahjong.session import AuthoritativeGameSession
from app.mahjong.tier0 import Tier0Agent


class StubObservation:
    def __init__(self, legal_actions: list[Action]) -> None:
        self._legal_actions = legal_actions

    def legal_actions(self) -> list[Action]:
        return self._legal_actions


class RiichiObservationView:
    def __init__(self, observation, safe_tile: int) -> None:
        self.hand = observation.hand
        self.player_id = observation.player_id
        self._observation = observation
        self._safe_tile = safe_tile

    def to_dict(self) -> dict[str, object]:
        data = self._observation.to_dict()
        data["riichi_declared"] = [False, True, False, False]
        data["discards"] = [[], [self._safe_tile], [], []]
        return data


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


class Tier0AgentTest(unittest.TestCase):
    def test_winning_action_is_prioritized(self) -> None:
        discard = Action(type=ActionType.DISCARD, tile=0, actor=1)
        ron = Action(type=ActionType.RON, actor=1)
        observation = StubObservation([discard, ron])

        selected = Tier0Agent(seed=1).choose_action(observation)  # type: ignore[arg-type]

        self.assertEqual(selected.to_dict(), ron.to_dict())

    def test_same_seed_produces_same_legal_discard_sequence(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=5,
        )
        observation = env.reset()[0]
        legal_values = [action.to_dict() for action in observation.legal_actions()]
        left = Tier0Agent(seed=91)
        right = Tier0Agent(seed=91)

        left_choices = [left.choose_action(observation).to_dict() for _ in range(20)]
        right_choices = [right.choose_action(observation).to_dict() for _ in range(20)]

        self.assertEqual(left_choices, right_choices)
        self.assertTrue(all(choice in legal_values for choice in left_choices))

    def test_discard_stays_in_top_hand_efficiency_candidates(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=5,
        )
        observation = env.reset()[0]
        agent = Tier0Agent(seed=91)
        discards = [
            action
            for action in observation.legal_actions()
            if action.action_type == ActionType.DISCARD
        ]
        evaluations = [
            agent._evaluate_discard(observation, action) for action in discards
        ]
        best_shanten = min(candidate.shanten for candidate in evaluations)
        best_ukeire = max(
            candidate.ukeire
            for candidate in evaluations
            if candidate.shanten == best_shanten
        )

        selected = agent.choose_action(observation)
        selected_evaluation = agent._evaluate_discard(observation, selected)

        self.assertEqual(selected_evaluation.shanten, best_shanten)
        self.assertGreaterEqual(selected_evaluation.ukeire, best_ukeire - 4)

    def test_riichi_genbutsu_adds_weak_safety_weight(self) -> None:
        env = RiichiEnv(
            game_mode="4p-red-east",
            rule=GameRule.default_tenhou(),
            seed=5,
        )
        observation = env.reset()[0]
        discards = observation.legal_actions()
        safe_action = discards[0]
        unsafe_action = next(
            action
            for action in discards
            if action.tile // 4 != safe_action.tile // 4
        )
        safe_tile = (safe_action.tile // 4) * 4
        view = RiichiObservationView(observation, safe_tile)
        agent = Tier0Agent(seed=91)

        safe = agent._evaluate_discard(view, safe_action)  # type: ignore[arg-type]
        unsafe = agent._evaluate_discard(view, unsafe_action)  # type: ignore[arg-type]

        self.assertEqual(safe.safe_against_riichi, 1)
        self.assertEqual(unsafe.safe_against_riichi, 0)

    def test_three_tier_zero_cpus_complete_fixed_seed_east_match(self) -> None:
        agents = {seat: Tier0Agent(seed=500 + seat) for seat in (1, 2, 3)}
        game = AuthoritativeGameSession(
            user_id=10,
            cpu_character_ids=(101, 102, 103),
            cpu_agents=agents,
            seed=5,
        )
        game.start()

        human_turns = 0
        while not game.done:
            turn = game.human_turn()
            assert turn is not None
            human_turns += 1
            game.submit_human_action(choose_human_action_index(turn.legal_actions))

        result = game.result()
        self.assertEqual(result.scores, (18600, 37000, 26600, 17800))
        self.assertEqual(result.ranks, (3, 1, 2, 4))
        self.assertEqual(game.steps, 381)
        self.assertEqual(human_turns, 92)


if __name__ == "__main__":
    unittest.main()
