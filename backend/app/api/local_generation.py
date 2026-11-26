"""Offline configuration. Only the explicit catalog request contacts ComfyUI."""
from http.client import HTTPException as HTTPClientError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_superadmin, get_session
from app.db.models import CpuCharacter, GameSetting
from app.services.anima_adapter import Comfy
from app.services.generation_settings import Config, Endpoint, KEY, read_settings

router = APIRouter(prefix="/api/local/generation-settings", dependencies=[Depends(get_current_superadmin)])


class Write(Config):
    expected_revision: int = Field(ge=0)


@router.get("")
def read(session: Session = Depends(get_session)):
    return read_settings(session)


@router.put("")
def save(body: Write, session: Session = Depends(get_session)):
    current = read_settings(session)
    if current["revision"] != body.expected_revision:
        raise HTTPException(409, "설정이 변경됐습니다. 다시 불러온 뒤 저장해 주세요.")
    if any(session.get(CpuCharacter, cpu) is None for cpu in body.characters):
        raise HTTPException(422, "존재하지 않는 캐릭터입니다.")
    value = {**body.model_dump(mode="json", exclude={"expected_revision"}), "revision": current["revision"] + 1}
    row = session.get(GameSetting, KEY)
    if row:
        row.value = value
    else:
        session.add(GameSetting(key=KEY, value=value))
    session.commit()
    return value


@router.post("/catalog")
def catalog(body: Endpoint, session: Session = Depends(get_session)):
    session.rollback()  # do not hold the game database while waiting on the external server
    try:
        return Comfy(body.endpoint).catalog()
    except (OSError, HTTPClientError, ValueError, TypeError, AttributeError, IndexError, KeyError):
        raise HTTPException(502, "ComfyUI의 노드 목록을 읽지 못했습니다. 주소와 실행 상태를 확인해 주세요.") from None
