import unittest
from collections.abc import Generator

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_session, get_settings
from app.core.config import Settings
from app.db.base import Base
from app.db.models import CpuCharacter, GameSetting, User, UserCpuProgress
from app.main import app
from app.mahjong.riichienv_adapter import MatchResult
from app.mahjong.tier0 import Tier0Agent
from app.services.bootstrap import seed_cpu_characters
from app.services.game_result import settle_completed_match
from app.services.game_setup import (
    CpuTierUnavailableError,
    GameSetupError,
    InvalidCpuSelectionError,
    create_game_session,
    list_selectable_cpus,
)


class CompletedGameStub:
    def __init__(self, user_id: int, cpu_ids: tuple[int, int, int]) -> None:
        self.user_id = user_id
        self.cpu_character_by_seat = dict(zip((1, 2, 3), cpu_ids))
        self.result_settled = False

    def result(self) -> MatchResult:
        return MatchResult(
            scores=(30000, 26000, 24000, 20000),
            ranks=(1, 2, 3, 4),
        )

    def mark_result_settled(self) -> None:
        self.result_settled = True


class GameSetupServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        seed_cpu_characters(self.session)
        self.member = User(
            login_id="member",
            password_hash="not-used",
            player_name="Player",
            current_hp=3,
            max_hp=3,
            role="member",
            must_change_password=False,
            is_active=True,
        )
        self.session.add(self.member)
        self.session.flush()
        cpu_ids = self.session.scalars(select(CpuCharacter.id).order_by(CpuCharacter.id)).all()
        self.session.add_all(
            UserCpuProgress(
                user_id=self.member.id,
                cpu_character_id=cpu_id,
                defeat_stage=0,
            )
            for cpu_id in cpu_ids
        )
        self.session.commit()
        self.cpu_ids = tuple(cpu_ids)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_stage_zero_selection_creates_started_authoritative_session(self) -> None:
        selected = self.cpu_ids[:3]

        game = create_game_session(
            self.session,
            self.member,
            selected,
            seed=5,
        )

        self.assertTrue(game.started)
        self.assertFalse(game.done)
        self.assertEqual(tuple(game.cpu_character_by_seat.values()), selected)
        self.assertIsNotNone(game.human_turn())

    def test_selection_requires_three_distinct_available_cpus_and_hp(self) -> None:
        first, second, _ = self.cpu_ids[:3]
        with self.assertRaises(InvalidCpuSelectionError):
            create_game_session(
                self.session,
                self.member,
                (first, first, second),
                seed=5,
            )

        unavailable = self.session.get(CpuCharacter, first)
        assert unavailable is not None
        unavailable.active = False
        with self.assertRaisesRegex(InvalidCpuSelectionError, "unavailable"):
            create_game_session(
                self.session,
                self.member,
                self.cpu_ids[:3],
                seed=5,
            )

        unavailable.active = True
        self.member.current_hp = 0
        with self.assertRaisesRegex(GameSetupError, "no remaining HP"):
            create_game_session(
                self.session,
                self.member,
                self.cpu_ids[:3],
                seed=5,
            )

    def test_stage_is_passed_to_factory_without_tier_zero_fallback(self) -> None:
        first = self.cpu_ids[0]
        progress = self.session.get(UserCpuProgress, (self.member.id, first))
        assert progress is not None
        progress.defeat_stage = 1
        with self.assertRaisesRegex(CpuTierUnavailableError, "tier 1"):
            create_game_session(
                self.session,
                self.member,
                self.cpu_ids[:3],
                seed=5,
            )

        received: list[tuple[int, int | None]] = []

        def test_factory(choice, *, seed):
            received.append((choice.defeat_stage, seed))
            return Tier0Agent(seed=seed)

        game = create_game_session(
            self.session,
            self.member,
            self.cpu_ids[:3],
            seed=5,
            agent_factory=test_factory,
        )
        self.assertTrue(game.started)
        self.assertEqual(received, [(1, 51), (0, 52), (0, 53)])

    def test_settled_stage_three_cpu_is_removed_from_replay_choices(self) -> None:
        selected = self.cpu_ids[:3]
        last_cpu_id = selected[2]
        progress = self.session.get(UserCpuProgress, (self.member.id, last_cpu_id))
        assert progress is not None
        progress.defeat_stage = 2
        game = CompletedGameStub(self.member.id, selected)

        settlement = settle_completed_match(self.session, game)  # type: ignore[arg-type]
        choices = list_selectable_cpus(self.session, self.member.id)

        self.assertTrue(settlement.cpu_completed)
        self.assertNotIn(last_cpu_id, {choice.id for choice in choices})


class GameSetupApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            session.add(GameSetting(key="player_max_hp", value=3))
            seed_cpu_characters(session)
            session.commit()

        self.settings = Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
            jwt_secret="test-jwt-secret-with-at-least-32-bytes",
        )

        def override_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_settings] = lambda: self.settings
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        )
        registered = await self.client.post(
            "/api/auth/register",
            json={
                "login_id": "member-one",
                "password": "member-password",
                "player_name": "회원",
            },
        )
        self.assertEqual(registered.status_code, 201, registered.text)
        login = await self.client.post(
            "/api/auth/login",
            json={"login_id": "member-one", "password": "member-password"},
        )
        self.headers = {
            "Authorization": f"Bearer {login.json()['access_token']}"
        }

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.engine.dispose()

    async def test_member_lists_only_active_incomplete_cpu_choices(self) -> None:
        with Session(self.engine) as session:
            member = session.scalar(select(User).where(User.login_id == "member-one"))
            cpus = session.scalars(select(CpuCharacter).order_by(CpuCharacter.id)).all()
            assert member is not None
            first_progress = session.get(UserCpuProgress, (member.id, cpus[0].id))
            assert first_progress is not None
            first_progress.defeat_stage = 3
            cpus[1].active = False
            third_progress = session.get(UserCpuProgress, (member.id, cpus[2].id))
            assert third_progress is not None
            third_progress.defeat_stage = 2
            excluded_ids = {cpus[0].id, cpus[1].id}
            third_id = cpus[2].id
            session.commit()

        response = await self.client.get("/api/game/cpus", headers=self.headers)

        self.assertEqual(response.status_code, 200, response.text)
        choices = response.json()
        self.assertEqual(len(choices), 4)
        self.assertTrue(excluded_ids.isdisjoint({choice["id"] for choice in choices}))
        third = next(choice for choice in choices if choice["id"] == third_id)
        self.assertEqual(third["defeat_stage"], 2)
        self.assertNotIn("aggression", third)

    async def test_cpu_choices_require_member_authentication(self) -> None:
        anonymous = await self.client.get("/api/game/cpus")
        self.assertEqual(anonymous.status_code, 401)


if __name__ == "__main__":
    unittest.main()
