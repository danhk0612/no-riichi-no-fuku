from __future__ import annotations

from dataclasses import asdict, replace
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CpuCharacter,
    GameSessionRecord,
    LocalPlayRoster,
    LocalPlayState,
    User,
    UserCpuProgress,
)
from app.services.game_setup import CpuChoice, InvalidCpuSelectionError


class LocalPlayConflict(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def ensure_local_play_state(session: Session, user_id: int) -> LocalPlayState:
    state = session.get(LocalPlayState, user_id)
    if state is None:
        state = LocalPlayState(
            user_id=user_id, generation=str(uuid4()), phase="roster_required"
        )
        session.add(state)
        session.flush()
        session.query(GameSessionRecord).filter(
            GameSessionRecord.user_id == user_id,
            GameSessionRecord.play_generation.is_(None),
        ).update({GameSessionRecord.play_generation: state.generation}, synchronize_session=False)
        session.flush()
    return state


def get_local_play_state(session: Session, user_id: int) -> LocalPlayState:
    state = session.get(LocalPlayState, user_id)
    if state is None:
        raise LocalPlayConflict("local_play_state_missing", "local play state has not been initialized")
    _validate_state(session, state)
    return state


def roster_cpu_ids(session: Session, user_id: int) -> tuple[int, ...]:
    return tuple(session.scalars(
        select(LocalPlayRoster.cpu_character_id)
        .where(LocalPlayRoster.user_id == user_id)
        .order_by(LocalPlayRoster.cpu_character_id)
    ).all())


def roster_candidates(session: Session, user_id: int) -> list[CpuChoice]:
    rows = session.execute(
        select(CpuCharacter, UserCpuProgress.defeat_stage)
        .join(UserCpuProgress, UserCpuProgress.cpu_character_id == CpuCharacter.id)
        .where(
            UserCpuProgress.user_id == user_id,
            CpuCharacter.active.is_(True),
            CpuCharacter.age_adult.is_(True),
        )
        .order_by(CpuCharacter.id)
    ).all()
    return [CpuChoice(
        id=cpu.id, slug=cpu.slug, name=cpu.name, age_adult=cpu.age_adult,
        style=cpu.style, short_description=cpu.short_description,
        long_description=cpu.long_description, profile_image_key=cpu.profile_image_key,
        defeat_stage=stage, aggression=cpu.aggression, defense=cpu.defense,
        call_preference=cpu.call_preference, riichi_preference=cpu.riichi_preference,
        hand_value_preference=cpu.hand_value_preference,
        speed_preference=cpu.speed_preference, policy_version=2,
    ) for cpu, stage in rows]


def confirm_roster(
    session: Session, user: User, generation: str, cpu_character_ids: list[int]
) -> LocalPlayState:
    state = get_local_play_state(session, user.id)
    _check_generation(state, generation)
    if state.phase != "roster_required":
        raise LocalPlayConflict("roster_locked", "the participant roster is already fixed")
    if session.scalar(select(GameSessionRecord.id).where(
        GameSessionRecord.user_id == user.id, GameSessionRecord.status == "active"
    )) is not None:
        raise LocalPlayConflict("active_game", "finish the active game before fixing the roster")
    ids = tuple(cpu_character_ids)
    if len(ids) < 3 or len(ids) != len(set(ids)):
        raise InvalidCpuSelectionError("at least three distinct CPUs are required")
    allowed = {choice.id for choice in roster_candidates(session, user.id)}
    if any(cpu_id not in allowed for cpu_id in ids):
        raise InvalidCpuSelectionError("roster contains an inactive, underage, or unknown CPU")
    session.add_all(LocalPlayRoster(user_id=user.id, cpu_character_id=cpu_id) for cpu_id in ids)
    state.phase = "progress"
    _create_ending_if_complete(session, state)
    session.flush()
    return state


def effective_choices(
    session: Session, user_id: int, selected_ids: tuple[int, int, int], state: LocalPlayState
) -> tuple[CpuChoice, CpuChoice, CpuChoice]:
    ids = set(roster_cpu_ids(session, user_id))
    if len(ids) < 3 or any(cpu_id not in ids for cpu_id in selected_ids):
        raise InvalidCpuSelectionError("selection must come from the fixed participant roster")
    if state.phase not in {"progress", "omake"}:
        raise LocalPlayConflict("play_not_ready", "fix the participant roster first")
    if state.phase == "ending_pending":
        raise LocalPlayConflict("ending_pending", "acknowledge the ending before starting another match")
    candidates = {choice.id: choice for choice in roster_candidates_including_inactive_roster(session, user_id, ids)}
    stages = {row.cpu_character_id: row.defeat_stage for row in session.scalars(
        select(UserCpuProgress).where(UserCpuProgress.user_id == user_id)
    ).all()}
    unfinished = sum(stages.get(cpu_id, 0) < 3 for cpu_id in ids)
    if state.phase == "progress" and unfinished == 0:
        raise LocalPlayConflict("ending_pending", "the ending must be acknowledged")
    if state.phase == "progress" and unfinished >= 3 and any(stages.get(cpu_id, 0) >= 3 for cpu_id in selected_ids):
        raise InvalidCpuSelectionError("completed CPUs are unavailable while three or more remain")
    choices = []
    for cpu_id in selected_ids:
        choice = candidates.get(cpu_id)
        if choice is None:
            raise InvalidCpuSelectionError("roster CPU is unavailable")
        stage = stages.get(cpu_id)
        if stage is None:
            raise InvalidCpuSelectionError("roster CPU progress is missing")
        tier = 2 if state.phase == "omake" else (0 if stage == 3 else stage)
        choices.append(replace(choice, defeat_stage=stage, effective_tier=tier, policy_version=2))
    return tuple(choices)  # type: ignore[return-value]


def roster_candidates_including_inactive_roster(
    session: Session, user_id: int, roster_ids: set[int]
) -> list[CpuChoice]:
    rows = session.execute(
        select(CpuCharacter, UserCpuProgress.defeat_stage)
        .join(UserCpuProgress, UserCpuProgress.cpu_character_id == CpuCharacter.id)
        .where(UserCpuProgress.user_id == user_id, CpuCharacter.id.in_(roster_ids))
        .order_by(CpuCharacter.id)
    ).all()
    return [CpuChoice(
        id=cpu.id, slug=cpu.slug, name=cpu.name, age_adult=cpu.age_adult,
        style=cpu.style, short_description=cpu.short_description,
        long_description=cpu.long_description, profile_image_key=cpu.profile_image_key,
        defeat_stage=stage, aggression=cpu.aggression, defense=cpu.defense,
        call_preference=cpu.call_preference, riichi_preference=cpu.riichi_preference,
        hand_value_preference=cpu.hand_value_preference,
        speed_preference=cpu.speed_preference, policy_version=2,
    ) for cpu, stage in rows]


def reset_local_play(session: Session, user_id: int, generation: str) -> LocalPlayState:
    state = get_local_play_state(session, user_id)
    _check_generation(state, generation)
    for record in session.scalars(select(GameSessionRecord).where(
        GameSessionRecord.user_id == user_id,
        GameSessionRecord.status == "active",
        GameSessionRecord.play_generation == generation,
    )).all():
        record.status = "cancelled"
    for progress in session.scalars(select(UserCpuProgress).where(
        UserCpuProgress.user_id == user_id
    )).all():
        progress.defeat_stage = 0
    session.query(LocalPlayRoster).filter(LocalPlayRoster.user_id == user_id).delete(synchronize_session=False)
    state.generation = str(uuid4())
    state.phase = "roster_required"
    state.ending_event_id = None
    state.ending_payload = None
    session.flush()
    return state


def acknowledge_ending(
    session: Session, user_id: int, generation: str, event_id: str
) -> LocalPlayState:
    state = get_local_play_state(session, user_id)
    _check_generation(state, generation)
    if state.phase == "omake" and state.ending_event_id == event_id:
        return state
    if state.phase != "ending_pending" or state.ending_event_id != event_id:
        raise LocalPlayConflict("ending_event_stale", "ending event is no longer pending")
    state.phase = "omake"
    session.flush()
    return state


def _create_ending_if_complete(session: Session, state: LocalPlayState) -> None:
    ids = roster_cpu_ids(session, state.user_id)
    stages = dict(session.execute(select(
        UserCpuProgress.cpu_character_id, UserCpuProgress.defeat_stage
    ).where(UserCpuProgress.user_id == state.user_id, UserCpuProgress.cpu_character_id.in_(ids))).all())
    if ids and all(stages.get(cpu_id) == 3 for cpu_id in ids):
        state.phase = "ending_pending"
        state.ending_event_id = str(uuid4())
        state.ending_payload = {
            "version": 1, "cg_asset_id": None, "music_asset_id": None,
            "dialogue_text": None,
        }


def _validate_state(session: Session, state: LocalPlayState) -> None:
    ids = roster_cpu_ids(session, state.user_id)
    if state.phase == "roster_required":
        valid = not ids and state.ending_event_id is None and state.ending_payload is None
    elif state.phase == "progress":
        valid = len(ids) >= 3 and state.ending_event_id is None and state.ending_payload is None
    else:
        stages = dict(session.execute(select(
            UserCpuProgress.cpu_character_id, UserCpuProgress.defeat_stage
        ).where(UserCpuProgress.user_id == state.user_id, UserCpuProgress.cpu_character_id.in_(ids))).all())
        valid = bool(ids) and all(stages.get(cpu_id) == 3 for cpu_id in ids) and bool(state.ending_event_id) and state.ending_payload is not None
    if not valid:
        raise LocalPlayConflict("local_play_state_invalid", "local play state is inconsistent")


def _check_generation(state: LocalPlayState, generation: str) -> None:
    if state.generation != generation:
        raise LocalPlayConflict("play_generation_stale", "play state changed; reload before continuing")
