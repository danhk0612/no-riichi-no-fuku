from __future__ import annotations

from uuid import uuid4
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_member, get_session
from app.db.models import GameSetting, GameResultDelivery, GameSessionRecord, LocalPlayRoster, LocalPlayState, User, UserCpuProgress
from app.schemas.game import CreateGameSessionResponse
from app.schemas.local_play import (
    LocalEndingAckRequest,
    LocalPlayStateResponse,
    LocalResetRequest,
    LocalRosterRequest,
    LocalResultAckRequest,
)
from app.services.audio_packs import resolve_voice_slot
from app.services.hand_cg_cache import HandCG
from app.services.generation_settings import read_settings
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
from app.services.result_delivery import ResultDeliveryError, acknowledge_result, result_envelope, unresolved_generation_sessions
from app.db.session import mark_write_intent


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
            GameSessionRecord.result_delivery_version.is_(None),
        ).order_by(desc(GameSessionRecord.updated_at), desc(GameSessionRecord.id)).limit(1))
    has_legacy_active = session.scalar(select(GameSessionRecord.id).where(
        GameSessionRecord.user_id == user_id,
        GameSessionRecord.status == "active",
        GameSessionRecord.rules_snapshot.is_(None),
    )) is not None
    result_resume = None
    try:
        unresolved = unresolved_generation_sessions(session, user_id, state.generation)
        if len(unresolved) > 1:
            raise ResultDeliveryError("multiple unresolved result deliveries exist")
        if unresolved:
            record = unresolved[0]
            envelope = result_envelope(session, record)
            if envelope["route"] in {"result", "settlement_wait"}:
                result_resume = {
                    "session_id": record.id,
                    "delivery_version": record.result_delivery_version,
                    "route": envelope["route"],
                    "delivery_revision": envelope["delivery_revision"],
                }
    except ResultDeliveryError as error:
        raise HTTPException(status_code=503, detail={
            "code": "result_delivery_invalid", "message": str(error),
        }) from None
    return {
        "generation": state.generation,
        "phase": state.phase,
        "roster": [{"cpu_character_id": cpu_id, "defeat_stage": stages.get(cpu_id, 0)} for cpu_id in ids],
        "ending_event_id": state.ending_event_id,
        "ending_payload": state.ending_payload,
        "active_session_id": active,
        "recent_session_id": recent,
        "legacy_active": has_legacy_active,
        "result_resume": result_resume,
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
    from app.services.character_content import get_character_content, stage_image_urls
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
            content = get_character_content(session, choice.id)
            result.append({
                "id": choice.id, "slug": choice.slug, "name": choice.name,
                "content_revision": content["revision"],
                "measurements_cm": content["measurements_cm"],
                "stage_images": stage_image_urls(content, choice.defeat_stage),
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


class ResumeHandRequest(BaseModel):
    generation: str
    session_id: str


@router.post("/resume-hand", response_model=LocalPlayStateResponse)
def resume_current_hand(request: ResumeHandRequest, raw_request: Request,
                        user: User = Depends(get_current_member), session: Session = Depends(get_session),
                        registry: GameRegistry = Depends(get_game_registry)) -> dict[str, object]:
    mark_write_intent(session)
    play = _state_payload(session, user.id)
    if play["generation"] != request.generation or play["active_session_id"] != request.session_id:
        raise HTTPException(status_code=409, detail="저장된 대국이 변경되었습니다.")
    if not play["result_resume"]:
        record = session.get(GameSessionRecord, request.session_id)
        registry.restart_current_hand(session, record)
        runtime = getattr(raw_request.app.state, "local_runtime", None)
        if runtime:
            runtime.close_generation_sockets(user.id, request.generation)
    return play


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


@router.get("/sessions/{session_id}/results")
def get_result_delivery(
    session_id: str,
    generation: str,
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    state = session.get(LocalPlayState, user.id)
    if state is not None and generation != state.generation:
        raise HTTPException(status_code=409, detail={"code": "play_generation_stale", "message": "play state changed"})
    record = session.scalar(select(GameSessionRecord).where(
        GameSessionRecord.id == session_id, GameSessionRecord.user_id == user.id,
    ))
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "session_not_found", "message": "game session not found"})
    if record.play_generation != generation or record.status == "cancelled":
        raise HTTPException(status_code=409, detail={"code": "play_generation_stale", "message": "play state changed"})
    if record.result_delivery_version is None:
        raise HTTPException(status_code=409, detail={"code": "result_delivery_unsupported", "message": "this match uses legacy result handling"})
    try:
        return result_envelope(session, record)
    except ResultDeliveryError as error:
        raise HTTPException(status_code=503, detail={"code": "result_delivery_invalid", "message": str(error)}) from None


@router.post("/sessions/{session_id}/results/ack")
def post_result_ack(
    session_id: str,
    request: LocalResultAckRequest,
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        mark_write_intent(session)
        state = session.get(LocalPlayState, user.id)
        if state is not None and request.generation != state.generation:
            raise HTTPException(status_code=409, detail={"code": "play_generation_stale", "message": "play state changed"})
        record = session.scalar(select(GameSessionRecord).where(
            GameSessionRecord.id == session_id, GameSessionRecord.user_id == user.id,
        ).with_for_update())
        if record is None:
            raise HTTPException(status_code=404, detail={"code": "session_not_found", "message": "game session not found"})
        if record.play_generation != request.generation or record.status == "cancelled":
            raise HTTPException(status_code=409, detail={"code": "play_generation_stale", "message": "play state changed"})
        if record.result_delivery_version is None:
            raise HTTPException(status_code=409, detail={"code": "result_delivery_unsupported", "message": "this match uses legacy result handling"})
        envelope = acknowledge_result(
            session, record, generation=request.generation, event_id=request.event_id,
            ordinal=request.ordinal, expected_revision=request.expected_delivery_revision,
        )
        session.commit()
        return envelope
    except HTTPException:
        session.rollback()
        raise
    except ResultDeliveryError as error:
        session.rollback()
        code = str(error)
        status_code = 409 if code in {"play_generation_stale", "result_ack_conflict"} else 503
        if code not in {"play_generation_stale", "result_ack_conflict"}:
            code = "result_delivery_invalid"
        raise HTTPException(status_code=status_code, detail={"code": code, "message": str(error)}) from None
    except Exception:
        session.rollback()
        raise HTTPException(status_code=503, detail={"code": "persistence_failed", "message": "result acknowledgement could not be saved"}) from None


@router.post("/sessions/{session_id}/results/{event_id}/defeat-voice")
def claim_defeat_voice(session_id: str, event_id: str, generation: str, request: Request,
                       user: User = Depends(get_current_member), session: Session = Depends(get_session)):
    mark_write_intent(session)
    head = get_result_delivery(session_id, generation, user, session)["head"]
    if not head or head["event_id"] != event_id or head["kind"] != "settlement":
        raise HTTPException(409, "현재 표시 중인 결산이 아닙니다.")
    claimed = session.execute(update(GameResultDelivery).where(
        GameResultDelivery.session_id == session_id, GameResultDelivery.defeat_voice_claimed.is_(False)
    ).values(defeat_voice_claimed=True)).rowcount
    clip = None
    if claimed:
        payload = head["payload"]
        seat = payload["ranks"].index(4)
        if seat:
            snapshot = payload["presentation"]["settlement"]
            stage = 3 if snapshot["mode"] == "omake" else snapshot["defeat_stage"]
            cpu = session.get(GameSessionRecord, session_id).cpu_choices[seat - 1]["id"]
            clip = resolve_voice_slot(session, cpu, f"defeat_stage_{stage}", request.app.state.local_runtime.paths.media)
    session.commit()
    return {"url": clip["url"] if clip else None}


def _hand_cg_input(session_id, generation, event_id, user, session):
    delivery = get_result_delivery(session_id, generation, user, session)
    head = delivery.get("head") or {}
    if head.get("event_id") != event_id or head.get("kind") != "hand":
        raise HTTPException(409, "현재 표시 중인 화료가 아닙니다.")
    scene = ((head.get("payload", {}).get("content") or {}).get("scene") or {})
    if not scene.get("generation_input"):
        raise HTTPException(404, "저장된 생성 입력이 없습니다.")
    key = f"image.hand.{scene['cpu_id']}.{scene['stage']}.{scene['event'].split('_')[0]}"
    return key, scene["generation_input"]


class HandPrompt(BaseModel):
    positive: str = Field(max_length=16000)
    previous: str


@router.get("/sessions/{session_id}/results/{event_id}/cg/prompt")
def hand_prompt(session_id: str, event_id: str, generation: str, user=Depends(get_current_member), session=Depends(get_session)):
    key, frozen = _hand_cg_input(session_id, generation, event_id, user, session)
    row = session.get(GameSetting, key)
    return {"positive": (row.value.get("positive") if row else None) or frozen["positive"]}


@router.put("/sessions/{session_id}/results/{event_id}/cg/prompt")
def save_hand_prompt(session_id: str, event_id: str, generation: str, body: HandPrompt,
                     user=Depends(get_current_member), session=Depends(get_session)):
    session.rollback()
    mark_write_intent(session)
    key, frozen = _hand_cg_input(session_id, generation, event_id, user, session)
    row = session.get(GameSetting, key) or GameSetting(key=key, value={})
    if (row.value.get("positive") or frozen["positive"]) != body.previous:
        raise HTTPException(409, "프롬프트가 변경됐습니다. 다시 열어 주세요.")
    row.value = {**row.value, "positive": body.positive.strip()}
    session.add(row)
    session.commit()
    return {"positive": body.positive.strip() or frozen["positive"]}


@router.post("/sessions/{session_id}/results/{event_id}/cg")
def advance_hand_cg(session_id: str, event_id: str, generation: str, request: Request,
                    retry: str | None = None, regenerate: bool = False, user: User = Depends(get_current_member),
                    session: Session = Depends(get_session)):
    session.rollback()
    mark_write_intent(session)
    key, source = _hand_cg_input(session_id, generation, event_id, user, session)
    row = session.get(GameSetting, key) or GameSetting(key=key, value={})
    frozen = row.value.get("input")
    if regenerate or not frozen:
        frozen = {**source, "positive": row.value.get("positive") or source["positive"]}
        if not frozen["positive"].strip() or not all(frozen["settings"].get(k) for k in ("model", "vae", "encoder")):
            return {"state": "unconfigured"}
        if regenerate:
            frozen["variation"] = str(uuid4())
        row.value = {**row.value, "input": frozen}
        session.add(row)
        session.commit()
    config = read_settings(session)
    endpoint = config.get("endpoint") if isinstance(config, dict) else None
    session.rollback()  # do not hold a game DB lock across disk I/O or HTTP
    cache = HandCG(request.app.state.local_runtime.paths.root / "generated" / "hand")
    try:
        return cache.advance(frozen, endpoint, retry)
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "화료 CG를 준비하지 못했습니다.") from None


@router.get("/sessions/{session_id}/results/{event_id}/cg/{attempt}")
def read_hand_cg(session_id: str, event_id: str, attempt: str, generation: str, request: Request,
                 user: User = Depends(get_current_member), session: Session = Depends(get_session)):
    key, source = _hand_cg_input(session_id, generation, event_id, user, session)
    row = session.get(GameSetting, key)
    frozen = row.value.get("input", source) if row else source
    session.rollback()
    data = HandCG(request.app.state.local_runtime.paths.root / "generated" / "hand").image(frozen, attempt)
    if data is None:
        raise HTTPException(404, "화료 CG 파일이 없습니다.")
    return Response(content=data, media_type="image/png", headers={"Cache-Control": "no-store"})
