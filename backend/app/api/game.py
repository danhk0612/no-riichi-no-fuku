from __future__ import annotations

import random
import json

import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import (
    get_current_member,
    get_database_session_factory,
    get_session,
    get_settings,
)
from app.core.config import Settings
from app.core.security import decode_access_token
from app.db.models import GameSessionRecord, LocalPlayState, User
from app.db.session import mark_write_intent
from app.mahjong.hand_scores import HandScoreCaptureError
from app.mahjong.session import GameSessionStateError
from app.schemas.game import (
    CpuChoiceResponse,
    CreateGameSessionRequest,
    CreateGameSessionResponse,
    DialogueEventResponse,
    ResultAssetResponse,
)
from app.services.game_registry import (
    ActiveGameExistsError,
    GameRegistry,
    GameRegistryError,
    RegisteredGame,
    RegisteredGameNotFoundError,
    StaleGameActionError,
    get_game_registry,
)
from app.services.dialogue_service import DialogueSelector, _map_event_type_to_key, extract_game_events
from app.services.game_setup import (
    CpuChoice,
    CpuTierUnavailableError,
    GameSetupError,
    InvalidCpuSelectionError,
    list_selectable_cpus,
)
from app.services.local_play import LocalPlayConflict
from app.services.difficulty import DifficultyError
from app.services.local_sound import selected_effect_clip
from app.services.audio_packs import resolve_audio_pack_slot, resolve_voice_slot
from app.services.result_assets import (
    get_unlocked_result_asset,
    get_unlocked_result_asset_by_id,
    result_asset_metadata,
    storage_path,
)


router = APIRouter(prefix="/api/game", tags=["game"])


@router.get("/cpus", response_model=list[CpuChoiceResponse])
def get_selectable_cpu_characters(
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> list[CpuChoice]:
    return list_selectable_cpus(session, user.id)


@router.post(
    "/sessions",
    response_model=CreateGameSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_registered_game_session(
    request: CreateGameSessionRequest,
    raw_request: Request,
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
    registry: GameRegistry = Depends(get_game_registry),
) -> RegisteredGame:
    try:
        local_runtime = getattr(raw_request.app.state, "local_runtime", None)
        if local_runtime is not None:
            if not request.generation:
                raise HTTPException(status_code=409, detail={"code": "generation_required", "message": "current play generation is required"})
            registered = registry.create(session, user, request.cpu_character_ids, generation=request.generation)
            try:
                session.commit()
            except Exception:
                session.rollback()
                registry.evict(registered.session_id)
                raise
            return registered
        return registry.create(session, user, request.cpu_character_ids)
    except InvalidCpuSelectionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except ActiveGameExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except CpuTierUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except GameSetupError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except DifficultyError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail={"code": "invalid_difficulty", "message": str(error)}) from None
    except LocalPlayConflict as error:
        session.rollback()
        raise HTTPException(status_code=409, detail={"code": error.code, "message": str(error)}) from None


@router.get(
    "/sessions/active",
    response_model=CreateGameSessionResponse | None,
)
def get_active_game_session(
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
    registry: GameRegistry = Depends(get_game_registry),
) -> RegisteredGame | None:
    try:
        return registry.get_active(session, user.id)
    except HandScoreCaptureError:
        raise HTTPException(status_code=503, detail={
            "code": "hand_score_failed", "message": "saved winning hand could not be verified",
        }) from None
    except (DifficultyError, GameSetupError, GameRegistryError) as error:
        raise HTTPException(status_code=409, detail={"code": "invalid_cpu_snapshot", "message": str(error)}) from None


@router.get(
    "/result-assets/{asset_id}",
    response_model=ResultAssetResponse,
)
def get_result_asset_metadata(
    asset_id: int,
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    asset = get_unlocked_result_asset_by_id(session, user.id, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="result CG not found")
    return result_asset_metadata(asset)


@router.get("/result-assets/{asset_id}/file", response_class=FileResponse)
def get_result_asset_file(
    asset_id: int,
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    asset = get_unlocked_result_asset_by_id(session, user.id, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="result CG not found")
    path = storage_path(settings.media_root, asset.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="result CG file not found")
    return FileResponse(
        path,
        media_type=asset.mime_type or "application/octet-stream",
        headers={"Cache-Control": "private, no-store"},
    )


async def send_websocket_error(
    websocket: WebSocket,
    code: str,
    message: str,
    *,
    generation: str | None = None,
    session_id: str | None = None,
) -> None:
    payload: dict[str, object] = {"type": "error", "code": code, "message": message}
    if generation is not None:
        payload["generation"] = generation
    if session_id is not None:
        payload["session_id"] = session_id
    await websocket.send_json(payload)


def authenticate_websocket_member(
    access_token: object,
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> User | None:
    if not isinstance(access_token, str):
        return None
    try:
        user_id = decode_access_token(access_token, settings.require_jwt_secret())
    except (jwt.InvalidTokenError, RuntimeError):
        return None
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None or not user.is_active or user.role != "member":
            return None
        session.expunge(user)
        return user


async def send_registered_game_state(
    websocket: WebSocket,
    registered: RegisteredGame,
    session_factory: sessionmaker[Session],
    registry: GameRegistry,
    *,
    local_runtime=None,
) -> bool:
    """Build a snapshot under the registry lock, then perform network IO unlocked."""
    dialogue_messages: list[dict[str, object]] = []
    sound_messages: list[dict[str, object]] = []
    result_voice_message: dict[str, object] | None = None
    with registered.lock:
        game = registered.game
        if game is not None:
            pending = game.pending_events()
            if pending.events and local_runtime is not None and registered.play_generation is not None:
                with session_factory() as session:
                    for event_index, event_raw in enumerate(pending.events):
                        try:
                            event = json.loads(event_raw) if isinstance(event_raw, str) else event_raw
                        except (json.JSONDecodeError, TypeError):
                            continue
                        if not isinstance(event, dict):
                            continue
                        event_type = event.get("type")
                        actor = event.get("actor")
                        event_key = _map_event_type_to_key(event_type, event)
                        if isinstance(actor, int) and actor in game.cpu_character_by_seat and event_key in {"chi", "pon", "kan", "riichi", "ron", "tsumo"}:
                            cpu_id = game.cpu_character_by_seat[actor]
                            clip = resolve_voice_slot(session, cpu_id, event_key, local_runtime.paths.media)
                            if clip:
                                sound_messages.append({"type": "voice_effect", "generation": registered.play_generation,
                                    "session_id": registered.session_id, "action_version": registered.action_version,
                                    "event_index": event_index, "actor_seat": actor, "event_key": event_key, **clip})
                            if event_key in {"ron", "tsumo"}:
                                win_clip = resolve_voice_slot(session, cpu_id, "win", local_runtime.paths.media)
                                if win_clip:
                                    sound_messages.append({"type": "voice_effect", "generation": registered.play_generation,
                                        "session_id": registered.session_id, "action_version": registered.action_version,
                                        "event_index": event_index, "actor_seat": actor, "event_key": "win", **win_clip})
                            dialogue_messages.append({"type": "dialogue_event", "cpu_character_id": cpu_id,
                                "seat": actor, "event_key": event_key, "text": {
                                    "chi": "치", "pon": "퐁", "kan": "깡", "riichi": "리치", "ron": "론", "tsumo": "쯔모",
                                }[event_key], "generation": registered.play_generation, "session_id": registered.session_id})
                        sfx_slot = {"dahai": "tile_discard", "reach_accepted": "riichi_stick", "start_kyoku": "tile_shuffle"}.get(event_type)
                        if sfx_slot:
                            clip = resolve_audio_pack_slot(session, kind="sfx", slot=sfx_slot, media_root=local_runtime.paths.media)
                            if clip:
                                sound_messages.append({"type": "sound_effect", "generation": registered.play_generation,
                                    "session_id": registered.session_id, "action_version": registered.action_version,
                                    "event_index": event_index, "event_key": sfx_slot, **clip})
                        if event_key in {"chi", "pon", "kan", "riichi", "ron", "tsumo"}:
                            legacy_clip = selected_effect_clip(session, event_key, local_runtime.paths.media)
                            if legacy_clip:
                                sound_messages.append({"type": "sound_effect", "generation": registered.play_generation,
                                    "session_id": registered.session_id, "action_version": registered.action_version,
                                    "event_index": event_index, "event_key": event_key, **legacy_clip})
            if pending.events and local_runtime is None and registered.rules_mode != "omake":
                with session_factory() as session:
                    events = extract_game_events(
                        events=pending.events,
                        cpu_character_by_seat=dict(game.cpu_character_by_seat),
                        dialogue_selector=DialogueSelector(),
                        dialogue_policy=registered.dialogue_policy,
                        event_turn=registered.action_version,
                        session=session,
                    )
                    dialogue_messages = []
                    for item in events:
                        dialogue_message = {
                            "type": "dialogue_event", "cpu_character_id": item.cpu_character_id,
                            "seat": item.seat, "event_key": item.event_key, "text": item.text,
                        }
                        if registered.play_generation is not None:
                            dialogue_message.update({"generation": registered.play_generation, "session_id": registered.session_id})
                        dialogue_messages.append(dialogue_message)
        is_done = registered.done
        if not is_done:
            if game is None:
                raise GameRegistryError("active game state is unavailable")
            turn = game.human_turn()
            if turn is None:
                raise RuntimeError("unfinished game has no human turn")
            message = {
                "type": "human_turn", "action_version": registered.action_version,
                "turn": {"observation": turn.observation, "legal_actions": turn.legal_actions},
            }
            if registered.play_generation is not None:
                message.update({"generation": registered.play_generation, "session_id": registered.session_id})

    if is_done and registered.settlement is None:
        with session_factory() as session:
            try:
                mark_write_intent(session)
                registry.settle(session, registered)
                session.commit()
                registry.publish_completed(session, registered)
                if local_runtime is not None and registered.play_generation is not None:
                    presentation = registered.presentation or {}
                    settlement = presentation.get("settlement", {})
                    cpu_id = settlement.get("cpu_character_id")
                    stage = settlement.get("defeat_stage")
                    if registered.rules_mode == "omake":
                        last_seat = settlement.get("last_place_seat")
                        if isinstance(last_seat, int) and last_seat != 0:
                            cpu_id = registered.game.cpu_character_by_seat.get(last_seat) if registered.game else None
                            stage = 3
                    if isinstance(cpu_id, int) and isinstance(stage, int):
                        voice = resolve_voice_slot(session, cpu_id, f"defeat_stage_{stage}", local_runtime.paths.media)
                        if voice:
                            result_voice_message = {"type": "voice_effect", "generation": registered.play_generation,
                                "session_id": registered.session_id, "action_version": registered.action_version,
                                "event_index": 0, "actor_seat": presentation.get("settlement", {}).get("last_place_seat"),
                                "event_key": f"defeat_stage_{stage}", "source_kind": "result", **voice}
            except Exception:
                session.rollback()
                registry.evict(registered.session_id)
                raise

    if local_runtime is not None and registered.play_generation is not None:
        with session_factory() as session:
            state = session.get(LocalPlayState, registered.user_id)
            record = session.get(GameSessionRecord, registered.session_id)
            if state is None or state.generation != registered.play_generation or record is None or record.play_generation != state.generation:
                await websocket.close(code=4409)
                return False

    for dialogue in dialogue_messages:
        await websocket.send_json(dialogue)
    for sound in sound_messages:
        await websocket.send_json(sound)
    if is_done:
        result = registered.result
        if result is None:
            if registered.game is None:
                raise GameRegistryError("completed game result is unavailable")
            result = registered.game.result()
        if registered.rules_mode is not None:
            presentation = registered.presentation or {}
            message = {
                "type": "match_complete", "result": {"scores": result.scores, "ranks": result.ranks},
                "settlement": presentation.get("settlement", {"progression_version": 2, "mode": registered.rules_mode}),
                "result_asset": presentation.get("result_asset"),
                "result_dialogues": presentation.get("result_dialogues", []),
                "ending_event_id": presentation.get("ending_event_id"),
                "generation": registered.play_generation, "session_id": registered.session_id,
            }
        else:
            settlement = registered.settlement
            if settlement is None:
                raise GameRegistryError("completed settlement is unavailable")
            result_asset = None
            result_dialogue = None
            if settlement.cpu_character_id is not None and settlement.defeat_stage is not None:
                with session_factory() as session:
                    event_key = f"defeat_stage_{settlement.defeat_stage}"
                    dialogue_text = DialogueSelector(rng=random.Random(f"{registered.session_id}:{event_key}")).select_dialogue(session, settlement.cpu_character_id, event_key)
                    if dialogue_text is not None:
                        result_dialogue = {"cpu_character_id": settlement.cpu_character_id, "event_key": event_key, "text": dialogue_text}
                    asset = get_unlocked_result_asset(session, registered.user_id, settlement.cpu_character_id, settlement.defeat_stage)
                    if asset is not None:
                        result_asset = result_asset_metadata(asset)
            message = {
                "type": "match_complete", "result": {"scores": result.scores, "ranks": result.ranks},
                "settlement": ({"last_place_seat": settlement.last_place_seat,
                    "cpu_character_id": settlement.cpu_character_id, "defeat_stage": settlement.defeat_stage,
                    "cpu_completed": settlement.cpu_completed} if local_runtime is not None else {
                    "last_place_seat": settlement.last_place_seat, "current_hp": settlement.current_hp,
                    "cpu_character_id": settlement.cpu_character_id, "defeat_stage": settlement.defeat_stage,
                    "game_over": settlement.game_over, "cpu_completed": settlement.cpu_completed}),
                "result_asset": result_asset, "result_dialogue": result_dialogue,
            }
            if local_runtime is not None:
                message.update({"generation": registered.play_generation, "session_id": registered.session_id})
    else:
        message = message
    if registered.play_generation is not None:
        message["cpu_difficulties"] = registered.cpu_difficulties
    await websocket.send_json(message)
    if result_voice_message is not None:
        await websocket.send_json(result_voice_message)
    return True


@router.websocket("/sessions/{session_id}/ws")
async def game_session_websocket(
    websocket: WebSocket,
    session_id: str,
    settings: Settings = Depends(get_settings),
    session_factory: sessionmaker[Session] = Depends(get_database_session_factory),
    registry: GameRegistry = Depends(get_game_registry),
) -> None:
    local_runtime = getattr(websocket.app.state, "local_runtime", None)
    await websocket.accept()
    try:
        message = await websocket.receive_json()
        if not isinstance(message, dict) or message.get("type") != "authenticate":
            await send_websocket_error(
                websocket,
                "authentication_required",
                "the first message must authenticate the connection",
                session_id=session_id if local_runtime is not None else None,
            )
            await websocket.close(code=4401)
            return
        if local_runtime is not None:
            # Desktop host attaches this over its private loopback request hook;
            # retain the W04 message path for in-process/local-runtime tests.
            capability = websocket.headers.get("x-local-capability")
            if capability is None:
                capability = message.get("capability")
            user = local_runtime.websocket_member(capability)
        else:
            user = authenticate_websocket_member(
                message.get("access_token"), settings, session_factory
            )
        if user is None:
            await send_websocket_error(
                websocket, "invalid_authentication", "invalid authentication credentials",
                generation=message.get("generation") if isinstance(message.get("generation"), str) else None,
                session_id=session_id if local_runtime is not None else None,
            )
            await websocket.close(code=4401)
            return
        requested_generation = message.get("generation")
        try:
            with session_factory() as session:
                if local_runtime is not None:
                    state = session.get(LocalPlayState, user.id)
                    record = session.get(GameSessionRecord, session_id)
                    if (
                        not isinstance(requested_generation, str)
                        or state is None
                        or record is None
                        or requested_generation != state.generation
                        or record.play_generation != state.generation
                        or record.status == "cancelled"
                    ):
                        raise RegisteredGameNotFoundError("stale play generation")
                registered = registry.get_owned(session, session_id, user.id)
        except RegisteredGameNotFoundError:
            await send_websocket_error(
                websocket, "session_not_found", "game session not found",
                generation=requested_generation if isinstance(requested_generation, str) else None,
                session_id=session_id if local_runtime is not None else None,
            )
            await websocket.close(code=4404)
            return

        except HandScoreCaptureError:
            await send_websocket_error(
                websocket, "hand_score_failed", "saved winning hand could not be verified",
                generation=requested_generation if isinstance(requested_generation, str) else None,
                session_id=session_id if local_runtime is not None else None,
            )
            await websocket.close(code=1011)
            return

        except (DifficultyError, GameSetupError, GameRegistryError) as error:
            await send_websocket_error(websocket, "invalid_cpu_snapshot", str(error),
                generation=requested_generation if isinstance(requested_generation, str) else None,
                session_id=session_id if local_runtime is not None else None)
            await websocket.close(code=4409)
            return

        if local_runtime is not None:
            local_runtime.register_socket(websocket, user.id, requested_generation)

        if not await send_registered_game_state(
            websocket, registered, session_factory, registry, local_runtime=local_runtime
        ):
            return
        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict) or message.get("type") != "action":
                await send_websocket_error(
                    websocket, "invalid_message", "an action message is required",
                    generation=registered.play_generation, session_id=session_id if local_runtime is not None else None,
                )
                continue
            action_index = message.get("legal_action_index")
            action_version = message.get("action_version")
            if type(action_index) is not int or type(action_version) is not int:
                await send_websocket_error(
                    websocket,
                    "invalid_action",
                    "legal_action_index and action_version must be integers",
                    generation=registered.play_generation, session_id=session_id if local_runtime is not None else None,
                )
                continue
            try:
                with session_factory() as session:
                    try:
                        mark_write_intent(session)
                        if local_runtime is not None:
                            state = session.get(LocalPlayState, user.id)
                            record = session.get(GameSessionRecord, session_id)
                            if (
                                not isinstance(message.get("generation"), str)
                                or state is None
                                or record is None
                                or message.get("generation") != state.generation
                                or record.play_generation != state.generation
                                or registered.play_generation != state.generation
                            ):
                                raise LocalPlayConflict("play_generation_stale", "play state changed")
                        registry.submit_action(
                            session,
                            registered,
                            action_index,
                            action_version,
                        )
                        session.commit()
                    except Exception:
                        session.rollback()
                        raise
            except GameSessionStateError as error:
                await send_websocket_error(websocket, "invalid_action", str(error),
                                           generation=registered.play_generation, session_id=session_id if local_runtime is not None else None)
                continue
            except StaleGameActionError:
                registry.evict(registered.session_id)
                try:
                    with session_factory() as session:
                        registered = registry.get_owned(session, session_id, user.id)
                except HandScoreCaptureError:
                    await send_websocket_error(
                        websocket, "hand_score_failed", "saved winning hand could not be verified",
                        generation=registered.play_generation, session_id=session_id if local_runtime is not None else None,
                    )
                    await websocket.close(code=1011)
                    return
                await send_websocket_error(
                    websocket,
                    "stale_action",
                    "game state changed; use the latest turn",
                    generation=registered.play_generation, session_id=session_id if local_runtime is not None else None,
                )
                await send_registered_game_state(
                    websocket, registered, session_factory, registry, local_runtime=local_runtime
                )
                continue
            except LocalPlayConflict:
                registry.evict(registered.session_id)
                await send_websocket_error(websocket, "play_generation_stale", "play state changed; reload the current play",
                                           generation=registered.play_generation, session_id=session_id if local_runtime is not None else None)
                await websocket.close(code=4409)
                return
            except HandScoreCaptureError:
                await send_websocket_error(
                    websocket, "hand_score_failed", "winning hand could not be verified",
                    generation=registered.play_generation, session_id=session_id if local_runtime is not None else None,
                )
                await websocket.close(code=1011)
                return
            except SQLAlchemyError:
                registry.evict(registered.session_id)
                await send_websocket_error(
                    websocket,
                    "persistence_failed",
                    "game action could not be saved",
                    generation=registered.play_generation, session_id=session_id if local_runtime is not None else None,
                )
                await websocket.close(code=1011)
                return
            if not await send_registered_game_state(
                websocket, registered, session_factory, registry, local_runtime=local_runtime
            ):
                return
    except WebSocketDisconnect:
        return
    finally:
        if local_runtime is not None:
            local_runtime.unregister_socket(websocket)
