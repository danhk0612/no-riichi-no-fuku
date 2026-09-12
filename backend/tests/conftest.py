"""Pytest fixtures for dialogue service tests"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import GameSetting
from app.services.bootstrap import seed_cpu_characters


@pytest.fixture
def session() -> Session:
    """Create a test database session"""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    
    with Session(engine) as sess:
        sess.add(GameSetting(key="player_max_hp", value=3))
        sess.commit()
        yield sess
        sess.rollback()
