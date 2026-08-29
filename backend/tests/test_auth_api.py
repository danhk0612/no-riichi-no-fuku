import unittest
from collections.abc import Generator

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_session, get_settings
from app.core.config import Settings
from app.db.base import Base
from app.db.models import GameSetting, User, UserCpuProgress
from app.main import app
from app.services.bootstrap import bootstrap_superadmin, seed_cpu_characters


class AuthApiTest(unittest.IsolatedAsyncioTestCase):
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

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.engine.dispose()

    async def register_member(self) -> None:
        response = await self.client.post(
            "/api/auth/register",
            json={
                "login_id": "member-one",
                "password": "initial-password",
                "player_name": "첫 번째 회원",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)

    async def login(self, password: str = "initial-password") -> str:
        response = await self.client.post(
            "/api/auth/login",
            json={"login_id": "member-one", "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["token_type"], "bearer")
        self.assertEqual(response.json()["expires_in"], 3600)
        return response.json()["access_token"]

    async def test_member_authentication_and_profile_flow(self) -> None:
        await self.register_member()

        duplicate = await self.client.post(
            "/api/auth/register",
            json={
                "login_id": "member-one",
                "password": "initial-password",
                "player_name": "중복 회원",
            },
        )
        self.assertEqual(duplicate.status_code, 409)

        invalid_login = await self.client.post(
            "/api/auth/login",
            json={"login_id": "member-one", "password": "wrong-password"},
        )
        self.assertEqual(invalid_login.status_code, 401)

        token = await self.login()
        headers = {"Authorization": f"Bearer {token}"}
        profile = await self.client.get("/api/profile/me", headers=headers)
        self.assertEqual(profile.status_code, 200, profile.text)
        self.assertEqual(profile.json()["current_hp"], 3)
        self.assertEqual(profile.json()["max_hp"], 3)
        self.assertEqual(profile.json()["player_name"], "첫 번째 회원")
        self.assertIsNone(profile.json()["profile_image_key"])

        updated = await self.client.patch(
            "/api/profile/me",
            headers=headers,
            json={"player_name": "수정된 이름"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["player_name"], "수정된 이름")

        wrong_change = await self.client.post(
            "/api/auth/change-password",
            headers=headers,
            json={
                "current_password": "wrong-password",
                "new_password": "changed-password",
            },
        )
        self.assertEqual(wrong_change.status_code, 400)

        changed = await self.client.post(
            "/api/auth/change-password",
            headers=headers,
            json={
                "current_password": "initial-password",
                "new_password": "changed-password",
            },
        )
        self.assertEqual(changed.status_code, 204, changed.text)

        old_login = await self.client.post(
            "/api/auth/login",
            json={"login_id": "member-one", "password": "initial-password"},
        )
        self.assertEqual(old_login.status_code, 401)
        await self.login("changed-password")

        with Session(self.engine) as session:
            user = session.scalar(select(User).where(User.login_id == "member-one"))
            assert user is not None
            progress_count = session.scalar(
                select(func.count())
                .select_from(UserCpuProgress)
                .where(UserCpuProgress.user_id == user.id)
            )
            self.assertEqual(progress_count, 6)

    async def test_superadmin_must_change_initial_password(self) -> None:
        with Session(self.engine) as session:
            bootstrap_superadmin(session, "admin", "initial-admin-password")
            session.commit()

        login = await self.client.post(
            "/api/auth/login",
            json={"login_id": "admin", "password": "initial-admin-password"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        self.assertTrue(login.json()["must_change_password"])

        changed = await self.client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
            json={
                "current_password": "initial-admin-password",
                "new_password": "changed-admin-password",
            },
        )
        self.assertEqual(changed.status_code, 204, changed.text)

        next_login = await self.client.post(
            "/api/auth/login",
            json={"login_id": "admin", "password": "changed-admin-password"},
        )
        self.assertEqual(next_login.status_code, 200, next_login.text)
        self.assertFalse(next_login.json()["must_change_password"])


if __name__ == "__main__":
    unittest.main()
