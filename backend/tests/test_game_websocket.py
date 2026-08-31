import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from riichienv import ActionType
from starlette.websockets import WebSocketDisconnect

from app.api.dependencies import (
    get_database_session_factory,
    get_session,
    get_settings,
)
from app.core.config import Settings
from app.db.base import Base
from app.db.models import (
    CpuCharacter,
    GameSessionRecord,
    GameSetting,
    User,
    UserCpuProgress,
)
from app.main import app
from app.services.bootstrap import seed_cpu_characters
from app.services.game_registry import GameRegistry, get_game_registry


def choose_human_action_index(actions: list[dict[str, object]]) -> int:
    for action_type in (ActionType.TSUMO, ActionType.RON, ActionType.RIICHI):
        for index, action in enumerate(actions):
            if action["type"] == int(action_type):
                return index
    for action_type in (ActionType.PASS, ActionType.DISCARD):
        for index, action in enumerate(actions):
            if action["type"] == int(action_type):
                return index
    return 0


class GameWebSocketApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        with self.session_factory() as session:
            session.add(GameSetting(key="player_max_hp", value=3))
            seed_cpu_characters(session)
            session.commit()

        self.settings = Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
            jwt_secret="test-jwt-secret-with-at-least-32-bytes",
        )
        self.registry = GameRegistry(seed_factory=lambda: 5)

        def override_session() -> Generator[Session, None, None]:
            with self.session_factory() as session:
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_database_session_factory] = (
            lambda: self.session_factory
        )
        app.dependency_overrides[get_settings] = lambda: self.settings
        app.dependency_overrides[get_game_registry] = lambda: self.registry
        self.client = TestClient(app)
        self.member_token = self.register_and_login("member-one", "회원")
        with self.session_factory() as session:
            self.cpu_ids = tuple(
                session.scalars(
                    select(CpuCharacter.id).order_by(CpuCharacter.id)
                ).all()[:3]
            )

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def register_and_login(self, login_id: str, player_name: str) -> str:
        registered = self.client.post(
            "/api/auth/register",
            json={
                "login_id": login_id,
                "password": "member-password",
                "player_name": player_name,
            },
        )
        self.assertEqual(registered.status_code, 201, registered.text)
        login = self.client.post(
            "/api/auth/login",
            json={"login_id": login_id, "password": "member-password"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        return login.json()["access_token"]

    def create_game(self, token: str | None = None) -> dict[str, object]:
        response = self.client.post(
            "/api/game/sessions",
            headers={"Authorization": f"Bearer {token or self.member_token}"},
            json={"cpu_character_ids": self.cpu_ids},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def authenticate(self, websocket, token: str | None = None) -> None:
        websocket.send_json(
            {"type": "authenticate", "access_token": token or self.member_token}
        )

    def test_session_creation_enforces_single_unfinished_game(self) -> None:
        created = self.create_game()

        self.assertEqual(len(created["players"]), 4)
        self.assertEqual(created["players"][0]["name"], "회원")
        self.assertTrue(created["players"][0]["isHuman"])
        active = self.client.get(
            "/api/game/sessions/active",
            headers={"Authorization": f"Bearer {self.member_token}"},
        )
        self.assertEqual(active.status_code, 200, active.text)
        self.assertEqual(active.json(), created)
        with self.session_factory() as session:
            record = session.get(GameSessionRecord, created["session_id"])
            assert record is not None
            self.assertEqual(record.status, "active")
            self.assertEqual(record.human_action_indices, [])
        duplicate = self.client.post(
            "/api/game/sessions",
            headers={"Authorization": f"Bearer {self.member_token}"},
            json={"cpu_character_ids": self.cpu_ids},
        )
        self.assertEqual(duplicate.status_code, 409, duplicate.text)

    def test_websocket_requires_first_message_authentication_and_owner(self) -> None:
        created = self.create_game()
        path = f"/api/game/sessions/{created['session_id']}/ws"
        with self.client.websocket_connect(path) as websocket:
            websocket.send_json({"type": "action", "legal_action_index": 0})
            error = websocket.receive_json()
            self.assertEqual(error["code"], "authentication_required")
            with self.assertRaises(WebSocketDisconnect) as closed:
                websocket.receive_json()
            self.assertEqual(closed.exception.code, 4401)

        other_token = self.register_and_login("member-two", "다른 회원")
        with self.client.websocket_connect(path) as websocket:
            self.authenticate(websocket, other_token)
            error = websocket.receive_json()
            self.assertEqual(error["code"], "session_not_found")
            with self.assertRaises(WebSocketDisconnect) as closed:
                websocket.receive_json()
            self.assertEqual(closed.exception.code, 4404)

    def test_invalid_action_preserves_turn_across_reconnect(self) -> None:
        created = self.create_game()
        path = f"/api/game/sessions/{created['session_id']}/ws"
        with self.client.websocket_connect(path) as websocket:
            self.authenticate(websocket)
            first_turn = websocket.receive_json()
            self.assertEqual(first_turn["type"], "human_turn")
            websocket.send_json(
                {
                    "type": "action",
                    "legal_action_index": 999,
                    "action_version": first_turn["action_version"],
                }
            )
            error = websocket.receive_json()
            self.assertEqual(error["code"], "invalid_action")

        with self.client.websocket_connect(path) as websocket:
            self.authenticate(websocket)
            reconnected_turn = websocket.receive_json()
            self.assertEqual(reconnected_turn, first_turn)

    def test_persisted_action_restores_same_turn_with_fresh_registry(self) -> None:
        created = self.create_game()
        path = f"/api/game/sessions/{created['session_id']}/ws"
        with self.client.websocket_connect(path) as websocket:
            self.authenticate(websocket)
            first_turn = websocket.receive_json()
            action_index = choose_human_action_index(
                first_turn["turn"]["legal_actions"]
            )
            websocket.send_json(
                {
                    "type": "action",
                    "legal_action_index": action_index,
                    "action_version": first_turn["action_version"],
                }
            )
            expected_turn = websocket.receive_json()

        with self.session_factory() as session:
            record = session.get(GameSessionRecord, created["session_id"])
            assert record is not None
            self.assertEqual(record.human_action_indices, [action_index])

        self.registry = GameRegistry(seed_factory=lambda: 999)
        app.dependency_overrides[get_game_registry] = lambda: self.registry
        with self.client.websocket_connect(path) as websocket:
            self.authenticate(websocket)
            self.assertEqual(websocket.receive_json(), expected_turn)

    def test_stale_action_is_rejected_and_latest_turn_is_resent(self) -> None:
        created = self.create_game()
        path = f"/api/game/sessions/{created['session_id']}/ws"
        with self.client.websocket_connect(path) as websocket:
            self.authenticate(websocket)
            first_turn = websocket.receive_json()
            websocket.send_json(
                {
                    "type": "action",
                    "legal_action_index": 0,
                    "action_version": first_turn["action_version"] + 1,
                }
            )
            error = websocket.receive_json()
            self.assertEqual(error["code"], "stale_action")
            self.assertEqual(websocket.receive_json(), first_turn)

    def test_fixed_seed_match_completes_and_persists_server_settlement(self) -> None:
        created = self.create_game()
        path = f"/api/game/sessions/{created['session_id']}/ws"
        with self.client.websocket_connect(path) as websocket:
            self.authenticate(websocket)
            message = websocket.receive_json()
            while message["type"] == "human_turn":
                action_index = choose_human_action_index(
                    message["turn"]["legal_actions"]
                )
                websocket.send_json(
                    {
                        "type": "action",
                        "legal_action_index": action_index,
                        "action_version": message["action_version"],
                    }
                )
                message = websocket.receive_json()

        self.assertEqual(message["type"], "match_complete")
        self.assertEqual(sorted(message["result"]["ranks"]), [1, 2, 3, 4])
        settlement = message["settlement"]
        last_place_seat = message["result"]["ranks"].index(4)
        self.assertEqual(settlement["last_place_seat"], last_place_seat)

        with self.session_factory() as session:
            member = session.scalar(select(User).where(User.login_id == "member-one"))
            assert member is not None
            stages = {
                progress.cpu_character_id: progress.defeat_stage
                for progress in session.scalars(
                    select(UserCpuProgress).where(UserCpuProgress.user_id == member.id)
                )
            }
            self.assertEqual(member.current_hp, settlement["current_hp"])
            if last_place_seat == 0:
                self.assertEqual(member.current_hp, 2)
                self.assertTrue(all(stage == 0 for stage in stages.values()))
            else:
                defeated_cpu_id = self.cpu_ids[last_place_seat - 1]
                self.assertEqual(settlement["cpu_character_id"], defeated_cpu_id)
                self.assertEqual(stages[defeated_cpu_id], 1)
            record = session.get(GameSessionRecord, created["session_id"])
            assert record is not None
            self.assertEqual(record.status, "completed")
            self.assertEqual(record.scores, message["result"]["scores"])
            self.assertEqual(record.ranks, message["result"]["ranks"])
            self.assertEqual(record.settlement, settlement)

        self.registry = GameRegistry(seed_factory=lambda: 999)
        app.dependency_overrides[get_game_registry] = lambda: self.registry
        with self.client.websocket_connect(path) as websocket:
            self.authenticate(websocket)
            self.assertEqual(websocket.receive_json(), message)

        active = self.client.get(
            "/api/game/sessions/active",
            headers={"Authorization": f"Bearer {self.member_token}"},
        )
        self.assertEqual(active.status_code, 200, active.text)
        self.assertIsNone(active.json())


if __name__ == "__main__":
    unittest.main()
