from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from threading import RLock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import GameSessionRecord, LocalPlayState, User, UserCpuProgress
from app.mahjong.riichienv_adapter import MatchResult
from app.mahjong.session import AuthoritativeGameSession, CPU_SEATS, HUMAN_SEAT
from app.services.game_result import MatchSettlement, settle_completed_match
from app.services.dialogue_service import DialogueEventPolicy
from app.services.game_setup import (
    CpuChoice,
    create_game_session,
    create_game_session_from_choices,
    list_selectable_cpus,
)
from app.services.local_play import (
    LocalPlayConflict,
    _create_ending_if_complete,
    effective_choices,
)
from app.services.dialogue_service import DialogueSelector
from app.services.result_assets import get_unlocked_result_asset, result_asset_metadata


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
    dialogue_policy: DialogueEventPolicy = field(
        default_factory=DialogueEventPolicy,
        repr=False,
    )
    play_generation: str | None = None
    rules_mode: str | None = None
    presentation: dict[str, object] | None = None

    def __post_init__(self) -> None:
        self.lock = RLock()

    @property
    def done(self) -> bool:
        return self.result is not None or (self.game is not None and self.game.done)

    @property
    def generation(self) -> str | None:
        return self.play_generation


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
        *,
        generation: str | None = None,
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

            local_state = None
            if generation is not None:
                local_state = db_session.get(LocalPlayState, user.id)
                if local_state is None or local_state.generation != generation:
                    raise LocalPlayConflict("play_generation_stale", "play state changed")
                choices = effective_choices(db_session, user.id, cpu_character_ids, local_state)
                rules_mode = "omake" if local_state.phase == "omake" else "progress"
            else:
                choices_by_id = {choice.id: choice for choice in list_selectable_cpus(db_session, user.id)}
                choices = tuple(choices_by_id[cpu_id] for cpu_id in cpu_character_ids if cpu_id in choices_by_id)
                if len(choices) != 3:
                    raise InvalidCpuSelectionError("selection contains an unavailable CPU")
                rules_mode = None
            seed = self._seed_factory()
            game = create_game_session_from_choices(user.id, choices, seed=seed)
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
                play_generation=generation,
                rules_mode=rules_mode,
            )
            db_session.add(
                GameSessionRecord(
                    id=registered.session_id,
                    user_id=user.id,
                    match_seed=seed,
                    cpu_choices=[
                        {key: value for key, value in asdict(choice).items()
                         if key != "effective_tier" or value is not None}
                        for choice in choices
                    ],
                    players=[asdict(player) for player in players],
                    human_action_indices=[],
                    status="active",
                    play_generation=generation,
                    rules_snapshot={"version": 2, "mode": rules_mode} if rules_mode else None,
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
        record = db_session.scalar(
            select(GameSessionRecord).where(
                GameSessionRecord.id == session_id,
                GameSessionRecord.user_id == user_id,
            )
        )
        if record is None or record.status == "cancelled":
            raise RegisteredGameNotFoundError("game session not found")
        with self._lock:
            cached = self._games.get(session_id)
            if cached is not None:
                if cached.user_id != user_id:
                    raise RegisteredGameNotFoundError("game session not found")
                return cached
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

            if record.rules_snapshot and record.rules_snapshot.get("version") == 2:
                settlement = self._settle_local(db_session, registered, record)
            else:
                settlement = settle_completed_match(db_session, registered.game)
            result = registered.game.result()
            record.status = "completed"
            record.scores = list(result.scores)
            record.ranks = list(result.ranks)
            if registered.rules_mode is not None:
                record.settlement = dict((registered.presentation or {}).get("settlement", {}))
            else:
                record.settlement = asdict(settlement)
            if registered.rules_mode is not None:
                record.presentation = registered.presentation
                registered.presentation = None
            db_session.flush()
            return settlement

    def publish_completed(
        self, db_session: Session, registered: RegisteredGame
    ) -> None:
        """Expose persisted result data to sockets only after the transaction commits."""
        with registered.lock:
            record = db_session.get(GameSessionRecord, registered.session_id)
            if record is None or record.status != "completed":
                raise GameRegistryError("completed match was not committed")
            self._load_completed_state(registered, record)

    def evict(self, session_id: str) -> None:
        with self._lock:
            self._games.pop(session_id, None)

    def _get_or_restore(self, record: GameSessionRecord) -> RegisteredGame:
        if record.status == "cancelled":
            raise RegisteredGameNotFoundError("game session was cancelled")
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
            mode = None
            if record.rules_snapshot is not None:
                version = record.rules_snapshot.get("version")
                if version not in (1, 2):
                    raise GameRegistryError("persisted rules version is unknown")
                if version == 2:
                    mode = record.rules_snapshot.get("mode")
                    if mode not in ("progress", "omake") or any(c.effective_tier not in (0, 1, 2) for c in choices):
                        raise GameRegistryError("persisted local rules snapshot is invalid")
            game = create_game_session_from_choices(
                record.user_id,
                choices,
                seed=record.match_seed,
            )
            for legal_action_index in record.human_action_indices:
                game.submit_human_action(legal_action_index)
            # 복구 replay에서 발생한 과거 이벤트는 재전송하지 않는다.
            game.pending_events()
            registered = RegisteredGame(
                session_id=record.id,
                user_id=record.user_id,
                players=players,
                action_version=len(record.human_action_indices),
                game=game,
                play_generation=record.play_generation,
                rules_mode=mode,
            )
        self._games[registered.session_id] = registered
        return registered

    @staticmethod
    def _settle_local(db_session: Session, registered: RegisteredGame, record: GameSessionRecord) -> MatchSettlement:
        game = registered.game
        if game is None:
            raise GameRegistryError("active game state is unavailable")
        from app.mahjong.session import HUMAN_SEAT
        from app.db.models import LocalPlayState
        state = db_session.get(LocalPlayState, registered.user_id)
        if state is None or state.generation != record.play_generation:
            raise LocalPlayConflict("play_generation_stale", "the match belongs to an old play generation")
        result = game.result()
        last_seat = result.ranks.index(4)
        winner_seat = result.ranks.index(1)
        mode = record.rules_snapshot.get("mode") if record.rules_snapshot else "progress"
        cpu_id = None
        stage = None
        stage_changed = False
        completed = False
        dialogues: list[dict[str, object]] = []
        choice_by_id = {int(choice["id"]): choice for choice in record.cpu_choices}
        if mode == "progress":
            if last_seat != HUMAN_SEAT:
                cpu_id = game.cpu_character_by_seat.get(last_seat)
                choice_snapshot = choice_by_id.get(cpu_id, {}) if cpu_id is not None else {}
                stage = int(choice_snapshot.get("defeat_stage", 0))
                effective_tier = choice_snapshot.get("effective_tier")
                progress = db_session.get(UserCpuProgress, (registered.user_id, cpu_id)) if cpu_id is not None else None
                if progress is None:
                    raise GameRegistryError("CPU progress disappeared during local settlement")
                if stage < 3 and progress.defeat_stage == stage:
                    progress.defeat_stage = stage + 1
                    stage = progress.defeat_stage
                    stage_changed = True
                    completed = stage == 3
                elif progress.defeat_stage != stage:
                    raise GameRegistryError("CPU stage changed during active local match")
                settlement = MatchSettlement(last_seat, None, cpu_id, stage, False, completed)
                asset = None
                event_key = "match_last" if not stage_changed and int(choice_snapshot.get("defeat_stage", 0)) == 3 else f"defeat_stage_{stage}"
                if stage_changed and cpu_id is not None:
                    asset_row = get_unlocked_result_asset(db_session, registered.user_id, cpu_id, stage)
                    if asset_row is not None:
                        asset = result_asset_metadata(asset_row)
                if cpu_id is not None:
                    text = DialogueSelector(rng=__import__("random").Random(f"{registered.session_id}:{event_key}:{cpu_id}")).select_dialogue(db_session, cpu_id, event_key)
                    if text:
                        dialogues.append({"cpu_character_id": cpu_id, "event_key": event_key, "text": text})
            else:
                settlement = MatchSettlement(last_seat, None, None, None, False, False)
                asset = None
            # Completed CPUs can receive only the explicitly approved first/last
            # result lines during progress mode; no dialogue pool is added here.
            for seat, event_key in ((winner_seat, "match_first"), (last_seat, "match_last")):
                char_id = game.cpu_character_by_seat.get(seat)
                snapshot = choice_by_id.get(char_id, {}) if char_id is not None else {}
                if char_id is None or int(snapshot.get("defeat_stage", 0)) != 3:
                    continue
                text = DialogueSelector(rng=__import__("random").Random(f"{registered.session_id}:{event_key}:{char_id}")).select_dialogue(db_session, char_id, event_key)
                if text:
                    dialogues.append({"cpu_character_id": char_id, "event_key": event_key, "text": text})
            registered.presentation = {"version": 2, "result_asset": asset, "result_dialogues": dialogues,
                                       "settlement": {"progression_version": 2, "mode": mode,
                                           "last_place_seat": last_seat,
                                           "cpu_character_id": settlement.cpu_character_id, "defeat_stage": settlement.defeat_stage,
                                           "stage_changed": stage_changed, "cpu_completed": settlement.cpu_completed}}
        else:
            settlement = MatchSettlement(last_seat, None, None, None, False, False)
            asset = None
            registered.presentation = {"version": 2, "result_asset": None, "result_dialogues": [],
                                       "settlement": {"progression_version": 2, "mode": mode,
                                           "last_place_seat": last_seat,
                                           "cpu_character_id": None, "defeat_stage": None,
                                           "stage_changed": False, "cpu_completed": False}}
        if mode == "progress":
            _create_ending_if_complete(db_session, state)
            if state.phase == "ending_pending":
                registered.presentation["ending_event_id"] = state.ending_event_id
        else:
            registered.presentation["ending_event_id"] = None
        return settlement

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
        if record.rules_snapshot and record.rules_snapshot.get("version") == 2:
            data = record.settlement
            if data.get("progression_version") != 2 or data.get("mode") not in ("progress", "omake"):
                raise GameRegistryError("completed local settlement is invalid")
            registered.settlement = MatchSettlement(
                last_place_seat=int(data["last_place_seat"]), current_hp=None,
                cpu_character_id=data.get("cpu_character_id"),
                defeat_stage=data.get("defeat_stage"), game_over=False,
                cpu_completed=bool(data.get("cpu_completed", False)),
            )
        else:
            registered.settlement = MatchSettlement(**record.settlement)
        registered.play_generation = record.play_generation
        registered.presentation = record.presentation
        if record.rules_snapshot and record.rules_snapshot.get("version") == 2:
            mode = record.rules_snapshot.get("mode")
            if mode not in ("progress", "omake"):
                raise GameRegistryError("persisted local rules snapshot is invalid")
            registered.rules_mode = str(mode)


@lru_cache
def get_game_registry() -> GameRegistry:
    return GameRegistry()
