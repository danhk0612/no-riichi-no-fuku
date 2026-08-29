import unittest

from argon2 import PasswordHasher
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.db.models import CpuCharacter, User
from app.services.bootstrap import bootstrap_superadmin, seed_cpu_characters


class BackendFoundationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_settings_require_explicit_secrets(self) -> None:
        settings = Settings(_env_file=None)
        with self.assertRaises(RuntimeError):
            settings.require_database_url()
        with self.assertRaises(RuntimeError):
            settings.require_superadmin_credentials()
        with self.assertRaises(RuntimeError):
            settings.require_jwt_secret()

        short_jwt = Settings(_env_file=None, jwt_secret="too-short")
        with self.assertRaises(RuntimeError):
            short_jwt.require_jwt_secret()

    def test_settings_build_database_url_from_postgres_fields(self) -> None:
        settings = Settings(
            _env_file=None,
            postgres_db="nrnf_test",
            postgres_user="tester",
            postgres_password="p@ss word",
            postgres_host="db.local",
            postgres_port=5544,
        )
        self.assertEqual(
            settings.require_database_url(),
            "postgresql+psycopg://tester:p%40ss word@db.local:5544/nrnf_test",
        )

    def test_superadmin_is_created_once_without_player_defaults(self) -> None:
        hasher = PasswordHasher()
        created = bootstrap_superadmin(
            self.session,
            "root-admin",
            "initial-password",
            password_hasher=hasher,
        )
        self.session.commit()

        admin = self.session.scalar(select(User).where(User.role == "superadmin"))
        self.assertTrue(created)
        self.assertIsNotNone(admin)
        assert admin is not None
        self.assertTrue(admin.must_change_password)
        self.assertTrue(admin.is_active)
        self.assertIsNone(admin.current_hp)
        self.assertIsNone(admin.max_hp)
        self.assertTrue(hasher.verify(admin.password_hash, "initial-password"))

        original_hash = admin.password_hash
        created_again = bootstrap_superadmin(
            self.session,
            "another-login",
            "replacement-password",
            password_hasher=hasher,
        )
        self.session.commit()
        self.assertFalse(created_again)
        self.assertEqual(admin.password_hash, original_hash)

    def test_cpu_seed_is_idempotent(self) -> None:
        first_created = seed_cpu_characters(self.session)
        self.session.commit()
        second_created = seed_cpu_characters(self.session)
        self.session.commit()

        count = self.session.scalar(select(func.count()).select_from(CpuCharacter))
        self.assertEqual(first_created, 6)
        self.assertEqual(second_created, 0)
        self.assertEqual(count, 6)
        self.assertTrue(
            all(
                cpu.age_adult
                for cpu in self.session.scalars(select(CpuCharacter)).all()
            )
        )


if __name__ == "__main__":
    unittest.main()
