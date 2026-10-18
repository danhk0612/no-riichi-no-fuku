from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_member, get_session
from app.db.models import CharacterContent, GameSessionRecord, LocalPlayRoster, User, UserCpuProgress
from app.schemas.game import CreateGameSessionResponse
from app.schemas.local_play import (
    LocalEndingAckRequest,
    LocalPlayStateResponse,
    LocalResetRequest,
    LocalRosterRequest,
)
from app.services.game_registry import GameRegistry, get_game_registry
from app.services.game_setup import InvalidCpuSelectionError
from app.services.local_play import (
    LocalPlayConflict,
    acknowledge_ending,
    confirm_roster,
    get_local_play_state,
    reset_local_play,
    roster_candidates,
    roster_cpu_ids,
)


router = APIRouter(prefix="/api/local/play", tags=["local-play"])


def _error(error: LocalPlayConflict) -> HTTPException:
    status_code = 409 if error.code != "invalid_confirmation" else 400
    return HTTPException(status_code=status_code, detail={"code": error.code, "message": str(error)})


def _state_payload(session: Session, user_id: int) -> dict[str, object]:
    state = get_local_play_state(session, user_id)
    ids = roster_cpu_ids(session, user_id)
    stages = dict(session.execute(select(
        UserCpuProgress.cpu_character_id, UserCpuProgress.defeat_stage
    ).where(UserCpuProgress.user_id == user_id, UserCpuProgress.cpu_character_id.in_(ids))).all()) if ids else {}
    active = session.scalar(select(GameSessionRecord.id).where(
        GameSessionRecord.user_id == user_id, GameSessionRecord.status == "active"
    ))
    recent = None
    if active is None:
        recent = session.scalar(select(GameSessionRecord.id).where(
            GameSessionRecord.user_id == user_id,
            GameSessionRecord.status == "completed",
            GameSessionRecord.play_generation == state.generation,
        ).order_by(desc(GameSessionRecord.updated_at), desc(GameSessionRecord.id)).limit(1))
    has_legacy_active = session.scalar(select(GameSessionRecord.id).where(
        GameSessionRecord.user_id == user_id,
        GameSessionRecord.status == "active",
        GameSessionRecord.rules_snapshot.is_(None),
    )) is not None
    return {
        "generation": state.generation,
        "phase": state.phase,
        "roster": [{"cpu_character_id": cpu_id, "defeat_stage": stages.get(cpu_id, 0)} for cpu_id in ids],
        "ending_event_id": state.ending_event_id,
        "ending_payload": state.ending_payload,
        "active_session_id": active,
        "recent_session_id": recent,
        "legacy_active": has_legacy_active,
    }


@router.get("", response_model=LocalPlayStateResponse)
def get_play(
    user: User = Depends(get_current_member), session: Session = Depends(get_session)
) -> dict[str, object]:
    return _state_payload(session, user.id)


@router.get("/roster-candidates")
def get_roster_candidates(
    user: User = Depends(get_current_member), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    from app.services.difficulty import DifficultyError, read_setting, resolve
    state = get_local_play_state(session, user.id)
    choices = roster_candidates(session, user.id)
    ids = set(roster_cpu_ids(session, user.id))
    content_rows = session.scalars(select(CharacterContent).where(
        CharacterContent.cpu_id.in_([choice.id for choice in choices])
    )).all() if choices else []
    measurements_by_cpu = {
        item.cpu_id: item.measurements_cm for item in content_rows
    }
    unfinished = sum(c.defeat_stage < 3 for c in choices if c.id in ids)
    try:
        setting = read_setting(session)
        result = []
        for choice in choices:
            preview = None
            if choice.id in ids and state.phase in ("progress", "omake") and (
                choice.defeat_stage < 3 or state.phase == "omake" or 0 < unfinished < 3
            ):
                snapshot = resolve(choice.defeat_stage, state.phase, setting["setting"], setting["revision"])
                preview = {"level": snapshot["profile"]["level"], "profile_version": snapshot["profile"]["version"], "reason": snapshot["reason"]}
            result.append({
                "id": choice.id, "slug": choice.slug, "name": choice.name,
                "measurements_cm": {
                    key: (measurements_by_cpu.get(choice.id) or {}).get(key)
                    for key in ("height", "bust", "waist", "hips")
                },
                "age_adult": choice.age_adult, "style": choice.style,
                "short_description": choice.short_description, "long_description": choice.long_description,
                "profile_image_key": choice.profile_image_key, "defeat_stage": choice.defeat_stage,
                "difficulty_preview": preview, "difficulty_setting_revision": setting["revision"],
            })
        return result
    except DifficultyError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.post("/roster", response_model=LocalPlayStateResponse)
def post_roster(
    request: LocalRosterRequest,
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        confirm_roster(session, user, request.generation, request.cpu_character_ids)
        session.commit()
    except LocalPlayConflict as error:
        session.rollback()
        raise _error(error) from None
    except (InvalidCpuSelectionError, ValueError) as error:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from None
    except Exception:
        session.rollback()
        raise
    return _state_payload(session, user.id)


@router.post("/reset", response_model=LocalPlayStateResponse)
def post_reset(
    request: LocalResetRequest,
    raw_request: Request,
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
    registry: GameRegistry = Depends(get_game_registry),
) -> dict[str, object]:
    if request.confirm is not True:
        raise HTTPException(status_code=400, detail={"code": "invalid_confirmation", "message": "reset confirmation is required"})
    old_generation = request.generation
    old_active = None
    try:
        old_active = session.scalar(select(GameSessionRecord.id).where(
            GameSessionRecord.user_id == user.id,
            GameSessionRecord.status == "active",
            GameSessionRecord.play_generation == old_generation,
        ))
        state = reset_local_play(session, user.id, old_generation)
        session.commit()
    except LocalPlayConflict as error:
        session.rollback()
        raise _error(error) from None
    except Exception:
        session.rollback()
        if old_active:
            registry.evict(old_active)
        raise
    runtime = getattr(raw_request.app.state, "local_runtime", None)
    if old_active:
        registry.evict(old_active)
    if runtime is not None:
        runtime.close_generation_sockets(user.id, old_generation)
    return _state_payload(session, user.id)


@router.post("/ending/ack", response_model=LocalPlayStateResponse)
def post_ending_ack(
    request: LocalEndingAckRequest,
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        acknowledge_ending(session, user.id, request.generation, request.ending_event_id)
        session.commit()
    except LocalPlayConflict as error:
        session.rollback()
        raise _error(error) from None
    except Exception:
        session.rollback()
        raise
    return _state_payload(session, user.id)
