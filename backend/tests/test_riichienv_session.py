import unittest

from riichienv import Action, ActionType, Observation

from app.mahjong.riichienv_adapter import IllegalActionError, RiichiEnvAdapter
from app.mahjong.session import AuthoritativeGameSession, GameSessionStateError


class DeterministicTestAgent:
    def __init__(self) -> None:
        self.calls = 0

    def choose_action(self, observation: Observation) -> Action:
        self.calls += 1
        legal_actions = observation.legal_actions()
        for action_type in (ActionType.TSUMO, ActionType.RON, ActionType.RIICHI):
            for action in legal_actions:
                if action.action_type == action_type:
                    return action
        for action in legal_actions:
            if action.action_type == ActionType.PASS:
                return action
        for action in legal_actions:
            if action.action_type == ActionType.DISCARD:
                return action
        return legal_actions[0]


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


class RiichiEnvAdapterTest(unittest.TestCase):
    def test_adapter_requires_every_pending_seat_action(self) -> None:
        adapter = RiichiEnvAdapter(seed=5)
        observations = adapter.start()
        self.assertTrue(observations)
        with self.assertRaises(IllegalActionError):
            adapter.step({})

    def test_adapter_rejects_action_outside_current_legal_actions(self) -> None:
        adapter = RiichiEnvAdapter(seed=5)
        observations = adapter.start()
        self.assertEqual(set(observations), {0})
        illegal_pass = Action(type=ActionType.PASS, actor=0)
        with self.assertRaises(IllegalActionError):
            adapter.step({0: illegal_pass})


class AuthoritativeGameSessionTest(unittest.TestCase):
    def test_four_seat_east_match_completes_through_human_boundary(self) -> None:
        agents = {seat: DeterministicTestAgent() for seat in (1, 2, 3)}
        game = AuthoritativeGameSession(
            user_id=10,
            cpu_character_ids=(101, 102, 103),
            cpu_agents=agents,
            seed=5,
        )
        game.start()

        checked_hidden_hands = False
        while not game.done:
            turn = game.human_turn()
            assert turn is not None
            self.assertEqual(turn.observation["player_id"], 0)
            self.assertEqual(
                list(turn.legal_actions),
                turn.observation["legal_actions"],
            )
            if not checked_hidden_hands:
                hands = turn.observation["hands"]
                assert isinstance(hands, list)
                self.assertTrue(hands[0])
                self.assertEqual(hands[1:], [[], [], []])
                checked_hidden_hands = True

            action_index = choose_human_action_index(turn.legal_actions)
            game.submit_human_action(action_index)

        result = game.result()
        self.assertEqual(result.scores, (16700, 25000, 33300, 25000))
        self.assertEqual(result.ranks, (4, 2, 1, 3))
        self.assertEqual(game.steps, 300)
        self.assertTrue(all(agent.calls > 0 for agent in agents.values()))

    def test_invalid_human_action_index_does_not_advance(self) -> None:
        agents = {seat: DeterministicTestAgent() for seat in (1, 2, 3)}
        game = AuthoritativeGameSession(
            user_id=10,
            cpu_character_ids=(101, 102, 103),
            cpu_agents=agents,
            seed=5,
        )
        game.start()
        steps_before = game.steps
        with self.assertRaises(GameSessionStateError):
            game.submit_human_action(-1)
        self.assertEqual(game.steps, steps_before)


if __name__ == "__main__":
    unittest.main()
