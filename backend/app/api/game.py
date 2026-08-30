from __future__ import annotations

import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import (
    get_current_member,
    get_database_session_factory,
    get_session,
    get_settings,
)
from app.core.config import Settings
from app.core.security import decode_access_token
from app.db.models import User
from app.mahjong.session import GameSessionStateError
from app.schemas.game import (
    CpuChoiceResponse,
    CreateGameSessionRequest,
    CreateGameSessionResponse,
)
from app.services.game_registry import (
    ActiveGameExistsError,
    GameRegistry,
    RegisteredGame,
    RegisteredGameNotFoundError,
    get_game_registry,
)
from app.services.game_result import settle_completed_match
from app.services.game_setup import (
    CpuChoice,
    CpuTierUnavailableError,
    GameSetupError,
    InvalidCpuSelectionError,
    list_selectable_cpus,
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
    user: User = Depends(get_current_member),
    session: Session = Depends(get_session),
    registry: GameRegistry = Depends(get_game_registry),
) -> RegisteredGame:
    try:
        return registry.create(session, user, request.cpu_character_ids)
    except InvalidCpuSelectionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except ActiveGameExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except CpuTierUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except GameSetupError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


async def send_websocket_error(
    websocket: WebSocket,
    code: str,
    message: str,
) -> None:
    await websocket.send_json({"type": "error", "code": code, "message": message})


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
) -> None:
    with registered.lock:
        if not registered.game.done:
            turn = registered.game.human_turn()
            if turn is None:
                raise RuntimeError("unfinished game has no human turn")
            message = {
                "type": "human_turn",
                "turn": {
                    "observation": turn.observation,
                    "legal_actions": turn.legal_actions,
                },
            }
        else:
            if registered.settlement is None:
                with session_factory() as session:
                    try:
                        registered.settlement = settle_completed_match(
                            session,
                            registered.game,
                        )
                        session.commit()
                    except Exception:
                        session.rollback()
                        raise
            result = registered.game.result()
            message = {
                "type": "match_complete",
                "result": {"scores": result.scores, "ranks": result.ranks},
                "settlement": {
                    "last_place_seat": registered.settlement.last_place_seat,
                    "current_hp": registered.settlement.current_hp,
                    "cpu_character_id": registered.settlement.cpu_character_id,
                    "defeat_stage": registered.settlement.defeat_stage,
                    "game_over": registered.settlement.game_over,
                    "cpu_completed": registered.settlement.cpu_completed,
                },
            }
    await websocket.send_json(message)


@router.websocket("/sessions/{session_id}/ws")
async def game_session_websocket(
    websocket: WebSocket,
    session_id: str,
    settings: Settings = Depends(get_settings),
    session_factory: sessionmaker[Session] = Depends(get_database_session_factory),
    registry: GameRegistry = Depends(get_game_registry),
) -> None:
    await websocket.accept()
    try:
        message = await websocket.receive_json()
        if not isinstance(message, dict) or message.get("type") != "authenticate":
            await send_websocket_error(
                websocket,
                "authentication_required",
                "the first message must authenticate the connection",
            )
            await websocket.close(code=4401)
            return
        user = authenticate_websocket_member(
            message.get("access_token"), settings, session_factory
        )
        if user is None:
            await send_websocket_error(
                websocket, "invalid_authentication", "invalid authentication credentials"
            )
            await websocket.close(code=4401)
            return
        try:
            registered = registry.get_owned(session_id, user.id)
        except RegisteredGameNotFoundError:
            await send_websocket_error(
                websocket, "session_not_found", "game session not found"
            )
            await websocket.close(code=4404)
            return

        await send_registered_game_state(websocket, registered, session_factory)
        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict) or message.get("type") != "action":
                await send_websocket_error(
                    websocket, "invalid_message", "an action message is required"
                )
                continue
            action_index = message.get("legal_action_index")
            if type(action_index) is not int:
                await send_websocket_error(
                    websocket,
                    "invalid_action",
                    "legal_action_index must be an integer",
                )
                continue
            try:
                with registered.lock:
                    registered.game.submit_human_action(action_index)
            except GameSessionStateError as error:
                await send_websocket_error(websocket, "invalid_action", str(error))
                continue
            await send_registered_game_state(websocket, registered, session_factory)
    except WebSocketDisconnect:
        return
