import unittest
from collections.abc import Generator

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_session, get_settings
from app.core.config import Settings
from app.db.base import Base
from app.db.models import GameSetting, User, UserCpuProgress
from app.main import app
from app.services.bootstrap import bootstrap_superadmin, seed_cpu_characters


class AdminApiTest(unittest.IsolatedAsyncioTestCase):
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
            bootstrap_superadmin(session, "admin", "initial-admin-password")
            session.commit()

        self.settings = Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
            jwt_secret="test-jwt-secret-with-at-least-32-bytes",
            access_token_expire_minutes=60,
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
                "player_name": "회원 한 명",
            },
        )
        self.assertEqual(registered.status_code, 201, registered.text)

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.engine.dispose()

    async def login(self, login_id: str, password: str) -> dict[str, str]:
        response = await self.client.post(
            "/api/auth/login",
            json={"login_id": login_id, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    async def admin_headers(self) -> dict[str, str]:
        initial_headers = await self.login("admin", "initial-admin-password")
        blocked = await self.client.get(
            "/api/admin/users",
            headers=initial_headers,
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()["detail"], "initial password must be changed")

        changed = await self.client.post(
            "/api/auth/change-password",
            headers=initial_headers,
            json={
                "current_password": "initial-admin-password",
                "new_password": "changed-admin-password",
            },
        )
        self.assertEqual(changed.status_code, 204, changed.text)
        return await self.login("admin", "changed-admin-password")

    async def test_admin_member_management_and_access_boundary(self) -> None:
        member_headers = await self.login("member-one", "member-password")
        forbidden = await self.client.get(
            "/api/admin/users",
            headers=member_headers,
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["detail"], "superadmin access required")

        headers = await self.admin_headers()
        members = await self.client.get("/api/admin/users", headers=headers)
        self.assertEqual(members.status_code, 200, members.text)
        self.assertEqual(len(members.json()), 1)
        self.assertEqual(members.json()[0]["login_id"], "member-one")

        member_id = members.json()[0]["id"]
        deactivated = await self.client.patch(
            f"/api/admin/users/{member_id}",
            headers=headers,
            json={"is_active": False},
        )
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        self.assertFalse(deactivated.json()["is_active"])

        rejected = await self.client.get(
            "/api/profile/me",
            headers=member_headers,
        )
        self.assertEqual(rejected.status_code, 401)

    async def test_admin_cpu_and_dialogue_management(self) -> None:
        headers = await self.admin_headers()
        created = await self.client.post(
            "/api/admin/cpus",
            headers=headers,
            json={
                "slug": "new-cpu",
                "name": "신규 CPU",
                "style": "balanced",
                "short_description": "관리 API 테스트 CPU.",
                "long_description": None,
                "active": True,
                "aggression": 1.0,
                "defense": 1.0,
                "call_preference": 1.0,
                "riichi_preference": 1.0,
                "hand_value_preference": 1.0,
                "speed_preference": 1.0,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertTrue(created.json()["age_adult"])
        self.assertIsNone(created.json()["profile_image_key"])
        cpu_id = created.json()["id"]

        duplicate = await self.client.post(
            "/api/admin/cpus",
            headers=headers,
            json={
                "slug": "new-cpu",
                "name": "중복 CPU",
                "style": "balanced",
                "short_description": "중복 slug.",
                "aggression": 1.0,
                "defense": 1.0,
                "call_preference": 1.0,
                "riichi_preference": 1.0,
                "hand_value_preference": 1.0,
                "speed_preference": 1.0,
            },
        )
        self.assertEqual(duplicate.status_code, 409)

        updated = await self.client.patch(
            f"/api/admin/cpus/{cpu_id}",
            headers=headers,
            json={"name": "수정 CPU", "active": False},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["name"], "수정 CPU")
        self.assertFalse(updated.json()["active"])

        invalid_null = await self.client.patch(
            f"/api/admin/cpus/{cpu_id}",
            headers=headers,
            json={"name": None},
        )
        self.assertEqual(invalid_null.status_code, 422)

        with Session(self.engine) as session:
            member_id = session.scalar(
                select(User.id).where(User.login_id == "member-one")
            )
            progress = session.get(UserCpuProgress, (member_id, cpu_id))
            self.assertIsNotNone(progress)
            assert progress is not None
            self.assertEqual(progress.defeat_stage, 0)

        dialogue = await self.client.post(
            f"/api/admin/cpus/{cpu_id}/dialogues",
            headers=headers,
            json={"event_key": "riichi", "text": "리치 선언."},
        )
        self.assertEqual(dialogue.status_code, 201, dialogue.text)
        dialogue_id = dialogue.json()["id"]

        updated_dialogue = await self.client.patch(
            f"/api/admin/dialogues/{dialogue_id}",
            headers=headers,
            json={"text": "리치할게.", "active": False},
        )
        self.assertEqual(updated_dialogue.status_code, 200, updated_dialogue.text)
        self.assertEqual(updated_dialogue.json()["text"], "리치할게.")
        self.assertFalse(updated_dialogue.json()["active"])

        dialogues = await self.client.get(
            f"/api/admin/cpus/{cpu_id}/dialogues",
            headers=headers,
        )
        self.assertEqual(dialogues.status_code, 200, dialogues.text)
        self.assertEqual(len(dialogues.json()), 1)

        deleted = await self.client.delete(
            f"/api/admin/dialogues/{dialogue_id}",
            headers=headers,
        )
        self.assertEqual(deleted.status_code, 204, deleted.text)

        missing = await self.client.delete(
            f"/api/admin/dialogues/{dialogue_id}",
            headers=headers,
        )
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
