from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from threading import RLock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import User
from app.mahjong.session import AuthoritativeGameSession, CPU_SEATS, HUMAN_SEAT
from app.services.game_result import MatchSettlement
from app.services.game_setup import create_game_session, list_selectable_cpus


class GameRegistryError(RuntimeError):
    pass


class ActiveGameExistsError(GameRegistryError):
    pass


class RegisteredGameNotFoundError(GameRegistryError):
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
    game: AuthoritativeGameSession
    players: tuple[GamePlayer, ...]
    settlement: MatchSettlement | None = None

    def __post_init__(self) -> None:
        self.lock = RLock()


class GameRegistry:
    def __init__(self, seed_factory: Callable[[], int] | None = None) -> None:
        self._seed_factory = seed_factory or (lambda: secrets.randbits(63))
        self._games: dict[str, RegisteredGame] = {}
        self._active_by_user: dict[int, str] = {}
        self._lock = RLock()

    def create(
        self,
        db_session: Session,
        user: User,
        cpu_character_ids: tuple[int, int, int],
    ) -> RegisteredGame:
        with self._lock:
            active_id = self._active_by_user.get(user.id)
            if active_id is not None:
                active = self._games[active_id]
                if not active.game.done or active.settlement is None:
                    raise ActiveGameExistsError(
                        "member already has an active game session"
                    )

            choices = {
                choice.id: choice for choice in list_selectable_cpus(db_session, user.id)
            }
            game = create_game_session(
                db_session,
                user,
                cpu_character_ids,
                seed=self._seed_factory(),
            )
            players = (
                GamePlayer(seat=HUMAN_SEAT, name=user.player_name, is_human=True),
                *(
                    GamePlayer(
                        seat=seat,
                        name=choices[cpu_id].name,
                        is_human=False,
                    )
                    for seat, cpu_id in zip(CPU_SEATS, cpu_character_ids)
                ),
            )
            registered = RegisteredGame(
                session_id=str(uuid4()),
                user_id=user.id,
                game=game,
                players=players,
            )
            self._games[registered.session_id] = registered
            self._active_by_user[user.id] = registered.session_id
            return registered

    def get_owned(self, session_id: str, user_id: int) -> RegisteredGame:
        with self._lock:
            registered = self._games.get(session_id)
            if registered is None or registered.user_id != user_id:
                raise RegisteredGameNotFoundError("game session not found")
            return registered


@lru_cache
def get_game_registry() -> GameRegistry:
    return GameRegistry()
