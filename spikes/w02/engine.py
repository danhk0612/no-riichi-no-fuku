"""W02 only: frozen runtime probe, never a product entry point."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import threading

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2] / "backend"))


def environment(data: Path) -> None:
    # Refuse arbitrary existing folders. Only reuse folders created by this spike.
    marker = data / "w02-state.json"
    if data.exists() and any(data.iterdir()) and not marker.is_file():
        raise RuntimeError("not a W02-owned data directory")
    data.mkdir(parents=True, exist_ok=True)
    if not marker.exists():
        marker.write_text(json.dumps({"jwt": secrets.token_hex(32), "admin": secrets.token_urlsafe(32)}))
    state = json.loads(marker.read_text())
    os.environ.update(DATABASE_URL=f"sqlite+pysqlite:///{(data / 'game.db').as_posix()}",
                      MEDIA_ROOT=str(data / "media"), JWT_SECRET=state["jwt"],
                      SUPERADMIN_LOGIN_ID="w02-admin", SUPERADMIN_INITIAL_PASSWORD=state["admin"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["serve", "inspect", "promote", "regression"])
    parser.add_argument("--data", type=Path)
    parser.add_argument("--ready", type=Path)
    parser.add_argument("--identity", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if not getattr(sys, "frozen", False):
        sys.path.insert(0, str(ROOT))
    if args.mode == "regression":
        import unittest
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        success = unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
        import pytest
        result = pytest.main([str(ROOT / "tests/test_dialogue_service.py"), "-v"])
        sys.exit(0 if success and result == 0 else 1)
    if args.data is None:
        parser.error("--data required")
    data = args.data.resolve()
    # Reserve before touching the database; port collision must not attach to a foreign API.
    listener = None
    if args.mode == "serve":
        listener = socket.socket()
        if sys.platform == "win32":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(("127.0.0.1", args.port))
        listener.listen(128)
    environment(data)
    from app.core.config import Settings
    from app.db.session import create_database_engine, create_session_factory
    from app.db.models import GameSessionRecord, User, UserCpuProgress
    from sqlalchemy import select
    factory = create_session_factory(create_database_engine(Settings().require_database_url()))
    if args.mode == "inspect":
        with factory() as db:
            record = db.scalar(select(GameSessionRecord))
            user = db.get(User, record.user_id)
            print(json.dumps(dict(status=record.status, scores=record.scores, ranks=record.ranks,
                                  settlement=record.settlement, actions=len(record.human_action_indices),
                                  choices=record.cpu_choices, hp=user.current_hp,
                                  stages={p.cpu_character_id: p.defeat_stage for p in db.scalars(select(UserCpuProgress))})))
        return
    if args.mode == "promote":
        with factory.begin() as db:
            for progress in db.scalars(select(UserCpuProgress)):
                progress.defeat_stage = 2
        return
    from alembic import command
    from alembic.config import Config
    config = Config(str(ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    from app.bootstrap import main as bootstrap
    bootstrap()
    from app.main import app
    from fastapi.staticfiles import StaticFiles
    from app.services.game_registry import GameRegistry, get_game_registry
    if args.smoke:
        registry = GameRegistry(seed_factory=lambda: 5)
        app.dependency_overrides[get_game_registry] = lambda: registry

    @app.get("/_spike/identity")
    def identity():
        return {"identity": args.identity}

    app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="w02-ui")
    import uvicorn
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", log_level="warning", loop="asyncio", http="h11", ws="websockets"))

    def owner_pipe():
        # EOF only from the owning host's pipe. No public shutdown API.
        sys.stdin.buffer.read()
        server.should_exit = True

    threading.Thread(target=owner_pipe, daemon=True).start()
    args.ready.write_text(json.dumps({"port": listener.getsockname()[1], "identity": args.identity, "pid": os.getpid()}))
    try:
        server.run(sockets=[listener])
    finally:
        listener.close()


if __name__ == "__main__":
    main()
