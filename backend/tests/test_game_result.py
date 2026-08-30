import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from riichienv import ActionType

from app.db.base import Base
from app.db.models import CpuCharacter, User, UserCpuProgress
from app.mahjong.riichienv_adapter import MatchResult
from app.mahjong.session import AuthoritativeGameSession, GameSessionStateError
from app.mahjong.tier0 import Tier0Agent
from app.services.game_result import (
    MatchAlreadySettledError,
    MatchSettlementStateError,
    settle_completed_match,
)


class CompletedGameStub:
    def __init__(self, user_id: int, ranks: tuple[int, int, int, int]) -> None:
        self.user_id = user_id
        self.cpu_character_by_seat = {1: 101, 2: 102, 3: 103}
        self.result_settled = False
        self._result = MatchResult(
            scores=(25000, 25000, 25000, 25000),
            ranks=ranks,
        )

    def result(self) -> MatchResult:
        return self._result

    def mark_result_settled(self) -> None:
        self.result_settled = True


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


def complete_tier_zero_match(user_id: int) -> AuthoritativeGameSession:
    game = AuthoritativeGameSession(
        user_id=user_id,
        cpu_character_ids=(101, 102, 103),
        cpu_agents={
            seat: Tier0Agent(seed=500 + seat) for seat in (1, 2, 3)
        },
        seed=5,
    )
    game.start()
    while not game.done:
        turn = game.human_turn()
        assert turn is not None
        game.submit_human_action(choose_human_action_index(turn.legal_actions))
    return game


def cpu(cpu_id: int) -> CpuCharacter:
    return CpuCharacter(
        id=cpu_id,
        slug=f"cpu-{cpu_id}",
        name=f"CPU {cpu_id}",
        age_adult=True,
        style="balanced",
        short_description="test CPU",
        active=True,
        aggression=1.0,
        defense=1.0,
        call_preference=1.0,
        riichi_preference=1.0,
        hand_value_preference=1.0,
        speed_preference=1.0,
    )


class MatchResultSettlementTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.member = User(
            id=1,
            login_id="member",
            password_hash="not-used",
            player_name="Player",
            current_hp=3,
            max_hp=3,
            role="member",
            must_change_password=False,
            is_active=True,
        )
        cpus = [cpu(cpu_id) for cpu_id in (101, 102, 103)]
        self.session.add_all([self.member, *cpus])
        self.session.add_all(
            UserCpuProgress(
                user_id=self.member.id,
                cpu_character_id=cpu_character.id,
                defeat_stage=0,
            )
            for cpu_character in cpus
        )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_player_last_decrements_only_hp_and_detects_game_over(self) -> None:
        self.member.current_hp = 1
        game = CompletedGameStub(self.member.id, (4, 1, 2, 3))

        settlement = settle_completed_match(self.session, game)  # type: ignore[arg-type]

        stages = self.session.scalars(
            select(UserCpuProgress.defeat_stage).order_by(
                UserCpuProgress.cpu_character_id
            )
        ).all()
        self.assertEqual(settlement.last_place_seat, 0)
        self.assertEqual(settlement.current_hp, 0)
        self.assertTrue(settlement.game_over)
        self.assertIsNone(settlement.cpu_character_id)
        self.assertEqual(stages, [0, 0, 0])

    def test_unfinished_authoritative_session_cannot_be_settled(self) -> None:
        game = AuthoritativeGameSession(
            user_id=self.member.id,
            cpu_character_ids=(101, 102, 103),
            cpu_agents={
                seat: Tier0Agent(seed=700 + seat) for seat in (1, 2, 3)
            },
            seed=5,
        )

        with self.assertRaisesRegex(GameSessionStateError, "not complete"):
            settle_completed_match(self.session, game)

        self.assertEqual(self.member.current_hp, 3)
        self.assertFalse(game.result_settled)

    def test_cpu_last_increments_only_mapped_progress(self) -> None:
        progress = self.session.get(UserCpuProgress, (self.member.id, 103))
        assert progress is not None
        progress.defeat_stage = 2
        game = complete_tier_zero_match(self.member.id)

        settlement = settle_completed_match(self.session, game)

        stages = self.session.scalars(
            select(UserCpuProgress.defeat_stage).order_by(
                UserCpuProgress.cpu_character_id
            )
        ).all()
        self.assertEqual(settlement.last_place_seat, 3)
        self.assertEqual(settlement.cpu_character_id, 103)
        self.assertEqual(settlement.defeat_stage, 3)
        self.assertTrue(settlement.cpu_completed)
        self.assertEqual(settlement.current_hp, 3)
        self.assertEqual(stages, [0, 0, 3])

    def test_same_session_cannot_be_settled_twice(self) -> None:
        game = CompletedGameStub(self.member.id, (4, 1, 2, 3))
        settle_completed_match(self.session, game)  # type: ignore[arg-type]

        with self.assertRaises(MatchAlreadySettledError):
            settle_completed_match(self.session, game)  # type: ignore[arg-type]

        self.assertEqual(self.member.current_hp, 2)

    def test_zero_hp_member_is_rejected_without_changes(self) -> None:
        self.member.current_hp = 0
        game = CompletedGameStub(self.member.id, (4, 1, 2, 3))

        with self.assertRaisesRegex(MatchSettlementStateError, "no remaining HP"):
            settle_completed_match(self.session, game)  # type: ignore[arg-type]

        self.assertEqual(self.member.current_hp, 0)
        self.assertFalse(game.result_settled)

    def test_completed_cpu_progress_is_rejected_without_hp_change(self) -> None:
        progress = self.session.get(UserCpuProgress, (self.member.id, 101))
        assert progress is not None
        progress.defeat_stage = 3
        game = CompletedGameStub(self.member.id, (1, 4, 2, 3))

        with self.assertRaisesRegex(MatchSettlementStateError, "already complete"):
            settle_completed_match(self.session, game)  # type: ignore[arg-type]

        self.assertEqual(progress.defeat_stage, 3)
        self.assertEqual(self.member.current_hp, 3)
        self.assertFalse(game.result_settled)


if __name__ == "__main__":
    unittest.main()
