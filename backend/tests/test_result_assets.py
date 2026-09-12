import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_session, get_settings
from app.core.config import Settings
from app.db.base import Base
from app.db.models import (
    CpuCharacter,
    CpuResultAsset,
    GameSetting,
    User,
    UserCpuProgress,
)
from app.main import app
from app.services.bootstrap import bootstrap_superadmin, seed_cpu_characters
from app.services.result_assets import MAX_RESULT_ASSET_BYTES, storage_path


PNG_FIXTURE = b"\x89PNG\r\n\x1a\nmetadata-only-fixture"
JPEG_FIXTURE = b"\xff\xd8\xffmetadata-only-fixture"


class ResultAssetApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.media_directory = tempfile.TemporaryDirectory()
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
            self.cpu_id = session.scalar(
                select(CpuCharacter.id).order_by(CpuCharacter.id)
            )
        assert self.cpu_id is not None

        self.settings = Settings(
            _env_file=None,
            database_url="sqlite+pysqlite:///:memory:",
            jwt_secret="test-jwt-secret-with-at-least-32-bytes",
            media_root=Path(self.media_directory.name),
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
        self.member_headers = await self.login("member-one", "member-password")
        initial_admin_headers = await self.login(
            "admin", "initial-admin-password"
        )
        changed = await self.client.post(
            "/api/auth/change-password",
            headers=initial_admin_headers,
            json={
                "current_password": "initial-admin-password",
                "new_password": "changed-admin-password",
            },
        )
        self.assertEqual(changed.status_code, 204, changed.text)
        self.admin_headers = await self.login("admin", "changed-admin-password")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.media_directory.cleanup()

    async def login(self, login_id: str, password: str) -> dict[str, str]:
        response = await self.client.post(
            "/api/auth/login",
            json={"login_id": login_id, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    async def test_upload_replace_unlock_serve_and_delete(self) -> None:
        path = f"/api/admin/cpus/{self.cpu_id}/result-assets/1"
        forbidden = await self.client.put(
            path,
            headers=self.member_headers,
            files={"file": ("result.png", PNG_FIXTURE, "image/png")},
        )
        self.assertEqual(forbidden.status_code, 403)

        uploaded = await self.client.put(
            path,
            headers=self.admin_headers,
            files={"file": ("result.txt", PNG_FIXTURE, "text/plain")},
        )
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        metadata = uploaded.json()
        self.assertEqual(metadata["mime_type"], "image/png")
        self.assertRegex(
            metadata["storage_key"],
            rf"^/cpu/{self.cpu_id}/result/stage-1/[0-9a-f-]+\.png$",
        )
        old_storage_key = metadata["storage_key"]
        old_path = storage_path(self.settings.media_root, old_storage_key)
        self.assertEqual(old_path.read_bytes(), PNG_FIXTURE)
        member_metadata_url = f"/api/game/result-assets/{metadata['id']}"

        locked = await self.client.get(
            member_metadata_url,
            headers=self.member_headers,
        )
        self.assertEqual(locked.status_code, 404)
        locked_file = await self.client.get(
            metadata["url"],
            headers=self.member_headers,
        )
        self.assertEqual(locked_file.status_code, 404)

        with Session(self.engine) as session:
            member_id = session.scalar(
                select(User.id).where(User.login_id == "member-one")
            )
            progress = session.get(UserCpuProgress, (member_id, self.cpu_id))
            assert progress is not None
            progress.defeat_stage = 1
            session.commit()

        unlocked = await self.client.get(
            member_metadata_url,
            headers=self.member_headers,
        )
        self.assertEqual(unlocked.status_code, 200, unlocked.text)
        self.assertNotIn("storage_key", unlocked.json())
        served = await self.client.get(
            metadata["url"],
            headers=self.member_headers,
        )
        self.assertEqual(served.status_code, 200, served.text)
        self.assertEqual(served.headers["content-type"], "image/png")
        self.assertEqual(served.content, PNG_FIXTURE)
        self.assertEqual(served.headers["cache-control"], "private, no-store")

        replaced = await self.client.put(
            path,
            headers=self.admin_headers,
            files={"file": ("replacement.jpg", JPEG_FIXTURE, "image/jpeg")},
        )
        self.assertEqual(replaced.status_code, 200, replaced.text)
        self.assertEqual(replaced.json()["id"], metadata["id"])
        self.assertEqual(replaced.json()["mime_type"], "image/jpeg")
        self.assertFalse(old_path.exists())

        listed = await self.client.get(
            f"/api/admin/cpus/{self.cpu_id}/result-assets",
            headers=self.admin_headers,
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(len(listed.json()), 1)

        deleted = await self.client.delete(path, headers=self.admin_headers)
        self.assertEqual(deleted.status_code, 204, deleted.text)
        with Session(self.engine) as session:
            self.assertIsNone(session.get(CpuResultAsset, metadata["id"]))
        self.assertFalse(
            storage_path(
                self.settings.media_root,
                replaced.json()["storage_key"],
            ).exists()
        )

    async def test_upload_rejects_invalid_format_and_oversize_file(self) -> None:
        path = f"/api/admin/cpus/{self.cpu_id}/result-assets/2"
        invalid = await self.client.put(
            path,
            headers=self.admin_headers,
            files={"file": ("result.gif", b"GIF89a fixture", "image/gif")},
        )
        self.assertEqual(invalid.status_code, 415, invalid.text)

        oversize = await self.client.put(
            path,
            headers=self.admin_headers,
            files={
                "file": (
                    "result.png",
                    b"\x89PNG\r\n\x1a\n"
                    + b"x" * (MAX_RESULT_ASSET_BYTES - 7),
                    "image/png",
                )
            },
        )
        self.assertEqual(oversize.status_code, 413, oversize.text)
        with Session(self.engine) as session:
            assets = session.scalars(select(CpuResultAsset)).all()
            self.assertEqual(assets, [])


if __name__ == "__main__":
    unittest.main()
