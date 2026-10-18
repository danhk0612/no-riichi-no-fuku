from __future__ import annotations

import hmac
import os
import secrets
import asyncio
from threading import RLock
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session, sessionmaker

from app.api.admin import router as admin_router
from app.api.dependencies import (
    get_current_member,
    get_current_superadmin,
    get_current_user,
    get_database_session_factory,
    get_session,
    get_settings,
)
from app.api.game import router as game_router
from app.api.local_play import router as local_play_router
from app.api.local_difficulty import router as local_difficulty_router
from app.api.local_sound import router as local_sound_router
from app.api.audio_packs import router as audio_packs_router
from app.api.local_content import character_router as local_character_content_router
from app.api.local_content import router as local_content_router
from app.api.local_shared_prompts import router as local_shared_prompts_router
from app.services.content_packs import ContentPackRegistry
from app.api.profile import router as profile_router
from app.core.config import Settings
from app.core.security import hash_password
from app.db.models import CpuCharacter, GameSessionRecord, GameSetting, LocalPlayState, User, UserCpuProgress
from app.db.session import (
    LocalRuntimeSession,
    create_database_engine,
    mark_write_intent,
)
from app.services.bootstrap import (
    seed_cpu_characters,
    seed_cpu_dialogues,
    seed_result_asset_slots,
)
from app.services.game_registry import GameRegistry, get_game_registry
from app.services.local_play import ensure_local_play_state
from app.schemas.game import CreateGameSessionResponse


PRODUCT_DIRECTORY = "NoRiichiNoFuku"
LOCAL_PLAYER_LOGIN = "__local_player__"
LOCAL_ADMIN_LOGIN = "__local_admin__"


@dataclass(frozen=True)
class DataPaths:
    root: Path
    database: Path
    media: Path
    config: Path


def resolve_data_paths(data_root: Path | None = None) -> DataPaths:
    if data_root is None:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA is unavailable; pass an explicit data root")
        root = Path(local_app_data) / PRODUCT_DIRECTORY
    else:
        root = Path(data_root)
    root = root.expanduser().resolve()
    return DataPaths(root, root / "game.db", root / "media", root / "config")


class DataRootLock:
    """Non-blocking, process-wide exclusive owner lock for one local data root."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                if handle.read(1) == b"":
                    handle.seek(0)
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError):
            handle.close()
            raise RuntimeError("another engine owns this local data root") from None
        self._file = handle

    def release(self) -> None:
        handle, self._file = self._file, None
        if handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _migrate(engine: Engine) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    with engine.connect() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")


def _ensure_single_local_profile(session: Session) -> tuple[User, User]:
    game_setting = session.get(GameSetting, "player_max_hp")
    if game_setting is None or type(game_setting.value) is not int or game_setting.value <= 0:
        raise RuntimeError("player_max_hp must be configured before local startup")
    member = session.scalar(select(User).where(User.login_id == LOCAL_PLAYER_LOGIN))
    if member is None:
        member = User(
            login_id=LOCAL_PLAYER_LOGIN,
            password_hash=hash_password(secrets.token_urlsafe(48)),
            player_name="플레이어",
            current_hp=game_setting.value,
            max_hp=game_setting.value,
            role="member",
            must_change_password=False,
            is_active=True,
        )
        session.add(member)
        session.flush()
    elif member.role != "member":
        raise RuntimeError("reserved local player identity has an invalid role")

    cpus = session.scalars(select(CpuCharacter)).all()
    existing_progress = set(
        session.execute(
            select(UserCpuProgress.cpu_character_id).where(
                UserCpuProgress.user_id == member.id
            )
        ).scalars()
    )
    session.add_all(
        UserCpuProgress(user_id=member.id, cpu_character_id=cpu.id, defeat_stage=0)
        for cpu in cpus
        if cpu.id not in existing_progress
    )

    admin = session.scalar(select(User).where(User.login_id == LOCAL_ADMIN_LOGIN))
    if admin is None:
        admin = User(
            login_id=LOCAL_ADMIN_LOGIN,
            password_hash=hash_password(secrets.token_urlsafe(48)),
            player_name=None,
            current_hp=None,
            max_hp=None,
            role="superadmin",
            must_change_password=True,
            is_active=True,
        )
        session.add(admin)
    elif admin.role != "superadmin":
        raise RuntimeError("reserved local admin identity has an invalid role")
    session.flush()
    return member, admin


@dataclass
class LocalRuntime:
    app: FastAPI
    paths: DataPaths
    capability: str
    engine: Engine
    session_factory: sessionmaker[Session]
    member_id: int
    admin_id: int
    lock: DataRootLock
    registry: GameRegistry
    sockets: dict[object, tuple[int, str | None, object]]
    sockets_lock: object
    content_packs: ContentPackRegistry

    def accepts_capability(self, candidate: object) -> bool:
        return isinstance(candidate, str) and candidate.isascii() and hmac.compare_digest(
            candidate, self.capability
        )

    def websocket_member(self, candidate: object) -> User | None:
        if not self.accepts_capability(candidate):
            return None
        with self.session_factory() as session:
            user = session.get(User, self.member_id)
            if user is None or not user.is_active or user.role != "member":
                return None
            session.expunge(user)
            return user

    def register_socket(self, websocket, user_id: int, generation: str | None) -> None:
        with self.sockets_lock:
            self.sockets[websocket] = (user_id, generation, asyncio.get_running_loop())

    def unregister_socket(self, websocket) -> None:
        with self.sockets_lock:
            self.sockets.pop(websocket, None)

    def close_generation_sockets(self, user_id: int, generation: str) -> None:
        with self.sockets_lock:
            targets = [(socket, identity[2]) for socket, identity in self.sockets.items()
                       if identity[:2] == (user_id, generation)]
        for socket, loop in targets:
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(lambda target=socket: asyncio.create_task(target.close(code=4409)))

    def close(self) -> None:
        self.engine.dispose()
        self.lock.release()


def create_local_runtime(data_root: Path | None = None) -> LocalRuntime:
    paths = resolve_data_paths(data_root)
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.media.mkdir(parents=True, exist_ok=True)
    paths.config.mkdir(parents=True, exist_ok=True)
    lock = DataRootLock(paths.root / ".engine.lock")
    lock.acquire()
    engine: Engine | None = None
    try:
        database_url = URL.create("sqlite", database=str(paths.database))
        engine = create_database_engine(
            database_url, sqlite_begin_immediate_by_intent=True
        )
        _migrate(engine)
        session_factory = sessionmaker(
            bind=engine, class_=LocalRuntimeSession, expire_on_commit=False
        )
        settings = Settings(
            _env_file=None,
            database_url=database_url.render_as_string(hide_password=False),
            media_root=paths.media,
        )
        with session_factory.begin() as session:
            mark_write_intent(session)
            seed_cpu_characters(session)
            seed_cpu_dialogues(session)
            seed_result_asset_slots(session)
            member, admin = _ensure_single_local_profile(session)
            ensure_local_play_state(session, member.id)
            member_id, admin_id = member.id, admin.id

        capability = secrets.token_urlsafe(32)
        app = FastAPI(title="No Riichi No Fuku Local Engine")
        local_admin_router = APIRouter(dependencies=[Depends(get_current_superadmin)])
        local_admin_router.routes.extend(
            route
            for route in admin_router.routes
            if getattr(route, "path", None) not in {"/api/admin/users", "/api/admin/users/{user_id}"}
        )
        app.include_router(local_admin_router)
        app.include_router(game_router)
        app.include_router(local_play_router)
        app.include_router(local_difficulty_router)
        app.include_router(local_sound_router)
        app.include_router(audio_packs_router)
        app.include_router(local_content_router)
        app.include_router(local_character_content_router)
        app.include_router(local_shared_prompts_router)
        app.include_router(profile_router)
        registry = GameRegistry()
        app.state.local_runtime = None  # assigned below after runtime construction

        def authenticate(value: str | None, session: Session) -> User:
            if not isinstance(value, str) or not value.isascii() or not hmac.compare_digest(
                value, capability
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid local capability",
                )
            user = session.get(User, member_id)
            if user is None or not user.is_active:
                raise HTTPException(status_code=401, detail="local profile unavailable")
            return user

        def local_user(
            x_local_capability: str | None = Header(default=None),
            session: Session = Depends(get_session),
        ) -> User:
            return authenticate(x_local_capability, session)

        def local_member(user: User = Depends(local_user)) -> User:
            if user.role != "member":
                raise HTTPException(status_code=403, detail="member access required")
            return user

        @app.get("/api/game/sessions/recent", response_model=CreateGameSessionResponse | None)
        def recent_local_game(
            user: User = Depends(local_member),
            session: Session = Depends(get_session),
        ):
            state = session.get(LocalPlayState, user.id)
            record = session.scalar(
                select(GameSessionRecord)
                .where(
                    GameSessionRecord.user_id == user.id,
                    GameSessionRecord.status == "completed",
                    GameSessionRecord.play_generation == (state.generation if state else ""),
                )
                .order_by(desc(GameSessionRecord.updated_at), desc(GameSessionRecord.id))
                .limit(1)
            )
            if record is None:
                return None
            return registry.get_owned(session, record.id, user.id)

        def local_admin(
            x_local_capability: str | None = Header(default=None),
            session: Session = Depends(get_session),
        ) -> User:
            if not isinstance(x_local_capability, str) or not x_local_capability.isascii() or not hmac.compare_digest(
                x_local_capability, capability
            ):
                raise HTTPException(status_code=401, detail="invalid local capability")
            user = session.get(User, admin_id)
            if user is None or not user.is_active or user.role != "superadmin":
                raise HTTPException(status_code=403, detail="local admin unavailable")
            return user

        app.dependency_overrides[get_current_user] = local_user
        app.dependency_overrides[get_current_member] = local_member
        app.dependency_overrides[get_current_superadmin] = local_admin
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_database_session_factory] = lambda: session_factory
        app.dependency_overrides[get_session] = _session_dependency(session_factory)
        app.dependency_overrides[get_game_registry] = lambda: registry
        runtime = LocalRuntime(
            app, paths, capability, engine, session_factory, member_id, admin_id,
            lock, registry, {}, RLock(), ContentPackRegistry(paths.root, paths.media, session_factory)
        )
        app.state.local_runtime = runtime
        runtime.content_packs.scan()
        return runtime
    except Exception:
        if engine is not None:
            engine.dispose()
        lock.release()
        raise


def _session_dependency(session_factory: sessionmaker[Session]):
    def get_local_session(request: Request):
        with session_factory() as session:
            try:
                # Media bytes are streamed to an owned temporary file before the
                # metadata writer transaction is reserved by the upload route.
                defer_media_writer = request.method.upper() == "POST" and request.url.path in {"/api/local/media", "/api/local/packs/rescan"}
                if request.method.upper() not in {"GET", "HEAD", "OPTIONS"} and not defer_media_writer:
                    mark_write_intent(session)
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    return get_local_session
