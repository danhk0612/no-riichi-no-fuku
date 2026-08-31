from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import asdict, dataclass
from functools import lru_cache
from threading import RLock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import GameSessionRecord, User
from app.mahjong.riichienv_adapter import MatchResult
from app.mahjong.session import AuthoritativeGameSession, CPU_SEATS, HUMAN_SEAT
from app.services.game_result import MatchSettlement, settle_completed_match
from app.services.game_setup import (
    CpuChoice,
    create_game_session,
    create_game_session_from_choices,
    list_selectable_cpus,
)


class GameRegistryError(RuntimeError):
    pass


class ActiveGameExistsError(GameRegistryError):
    pass


class RegisteredGameNotFoundError(GameRegistryError):
    pass


class StaleGameActionError(GameRegistryError):
    pass


@dataclass(frozen=True)
class GamePlayer:
    seat: int
    name: str
    is_human: bool


@dataclass
class RegisteredGame:
    session_id: str
    user_id: int
    players: tuple[GamePlayer, ...]
    action_version: int
    game: AuthoritativeGameSession | None = None
    result: MatchResult | None = None
    settlement: MatchSettlement | None = None

    def __post_init__(self) -> None:
        self.lock = RLock()

    @property
    def done(self) -> bool:
        return self.result is not None or (self.game is not None and self.game.done)


class GameRegistry:
    def __init__(self, seed_factory: Callable[[], int] | None = None) -> None:
        self._seed_factory = seed_factory or (lambda: secrets.randbits(63))
        self._games: dict[str, RegisteredGame] = {}
        self._lock = RLock()

    def create(
        self,
        db_session: Session,
        user: User,
        cpu_character_ids: tuple[int, int, int],
    ) -> RegisteredGame:
        with self._lock:
            active_id = db_session.scalar(
                select(GameSessionRecord.id).where(
                    GameSessionRecord.user_id == user.id,
                    GameSessionRecord.status == "active",
                )
            )
            if active_id is not None:
                raise ActiveGameExistsError(
                    "member already has an active game session"
                )

            choices_by_id = {
                choice.id: choice
                for choice in list_selectable_cpus(db_session, user.id)
            }
            seed = self._seed_factory()
            game = create_game_session(
                db_session,
                user,
                cpu_character_ids,
                seed=seed,
            )
            choices = tuple(choices_by_id[cpu_id] for cpu_id in cpu_character_ids)
            players = (
                GamePlayer(seat=HUMAN_SEAT, name=user.player_name, is_human=True),
                *(
                    GamePlayer(
                        seat=seat,
                        name=choice.name,
                        is_human=False,
                    )
                    for seat, choice in zip(CPU_SEATS, choices)
                ),
            )
            registered = RegisteredGame(
                session_id=str(uuid4()),
                user_id=user.id,
                players=players,
                action_version=0,
                game=game,
            )
            db_session.add(
                GameSessionRecord(
                    id=registered.session_id,
                    user_id=user.id,
                    match_seed=seed,
                    cpu_choices=[asdict(choice) for choice in choices],
                    players=[asdict(player) for player in players],
                    human_action_indices=[],
                    status="active",
                )
            )
            try:
                db_session.flush()
            except IntegrityError:
                raise ActiveGameExistsError(
                    "member already has an active game session"
                ) from None
            self._games[registered.session_id] = registered
            return registered

    def get_active(self, db_session: Session, user_id: int) -> RegisteredGame | None:
        record = db_session.scalar(
            select(GameSessionRecord).where(
                GameSessionRecord.user_id == user_id,
                GameSessionRecord.status == "active",
            )
        )
        if record is None:
            return None
        return self._get_or_restore(record)

    def get_owned(
        self,
        db_session: Session,
        session_id: str,
        user_id: int,
    ) -> RegisteredGame:
        with self._lock:
            cached = self._games.get(session_id)
            if cached is not None:
                if cached.user_id != user_id:
                    raise RegisteredGameNotFoundError("game session not found")
                return cached
            record = db_session.scalar(
                select(GameSessionRecord).where(
                    GameSessionRecord.id == session_id,
                    GameSessionRecord.user_id == user_id,
                )
            )
            if record is None:
                raise RegisteredGameNotFoundError("game session not found")
            return self._restore(record)

    def submit_action(
        self,
        db_session: Session,
        registered: RegisteredGame,
        legal_action_index: int,
        action_version: int,
    ) -> None:
        with registered.lock:
            record = db_session.scalar(
                select(GameSessionRecord)
                .where(
                    GameSessionRecord.id == registered.session_id,
                    GameSessionRecord.user_id == registered.user_id,
                )
                .with_for_update()
            )
            if record is None or record.status != "active":
                raise RegisteredGameNotFoundError("active game session not found")
            persisted_version = len(record.human_action_indices)
            if (
                action_version != registered.action_version
                or persisted_version != registered.action_version
            ):
                raise StaleGameActionError("game action version is stale")
            if registered.game is None:
                raise GameRegistryError("active game state is unavailable")
            registered.game.submit_human_action(legal_action_index)
            record.human_action_indices = [
                *record.human_action_indices,
                legal_action_index,
            ]
            registered.action_version += 1
            db_session.flush()

    def settle(
        self,
        db_session: Session,
        registered: RegisteredGame,
    ) -> MatchSettlement:
        with registered.lock:
            if registered.settlement is not None:
                return registered.settlement
            record = db_session.scalar(
                select(GameSessionRecord)
                .where(GameSessionRecord.id == registered.session_id)
                .with_for_update()
            )
            if record is None:
                raise RegisteredGameNotFoundError("game session not found")
            if record.status == "completed":
                self._load_completed_state(registered, record)
                assert registered.settlement is not None
                return registered.settlement
            if registered.game is None or not registered.game.done:
                raise GameRegistryError("game session is not complete")

            settlement = settle_completed_match(db_session, registered.game)
            result = registered.game.result()
            record.status = "completed"
            record.scores = list(result.scores)
            record.ranks = list(result.ranks)
            record.settlement = asdict(settlement)
            registered.result = result
            registered.settlement = settlement
            db_session.flush()
            return settlement

    def evict(self, session_id: str) -> None:
        with self._lock:
            self._games.pop(session_id, None)

    def _get_or_restore(self, record: GameSessionRecord) -> RegisteredGame:
        with self._lock:
            cached = self._games.get(record.id)
            if cached is not None:
                return cached
            return self._restore(record)

    def _restore(self, record: GameSessionRecord) -> RegisteredGame:
        players = tuple(GamePlayer(**player) for player in record.players)
        if record.status == "completed":
            registered = RegisteredGame(
                session_id=record.id,
                user_id=record.user_id,
                players=players,
                action_version=len(record.human_action_indices),
            )
            self._load_completed_state(registered, record)
        else:
            choices = tuple(CpuChoice(**choice) for choice in record.cpu_choices)
            if len(choices) != 3:
                raise GameRegistryError("persisted CPU selection is invalid")
            game = create_game_session_from_choices(
                record.user_id,
                choices,
                seed=record.match_seed,
            )
            for legal_action_index in record.human_action_indices:
                game.submit_human_action(legal_action_index)
            registered = RegisteredGame(
                session_id=record.id,
                user_id=record.user_id,
                players=players,
                action_version=len(record.human_action_indices),
                game=game,
            )
        self._games[registered.session_id] = registered
        return registered

    @staticmethod
    def _load_completed_state(
        registered: RegisteredGame,
        record: GameSessionRecord,
    ) -> None:
        if record.scores is None or record.ranks is None or record.settlement is None:
            raise GameRegistryError("completed game record is incomplete")
        registered.result = MatchResult(
            scores=tuple(record.scores),
            ranks=tuple(record.ranks),
        )
        registered.settlement = MatchSettlement(**record.settlement)


@lru_cache
def get_game_registry() -> GameRegistry:
    return GameRegistry()
