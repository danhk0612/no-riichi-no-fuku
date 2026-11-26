"""Offline configuration. Only the explicit catalog request contacts ComfyUI."""
from http.client import HTTPException as HTTPClientError
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StringConstraints, field_validator
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_superadmin, get_session
from app.db.models import CpuCharacter, GameSetting
from app.services.anima_adapter import Comfy, Settings

router = APIRouter(prefix="/api/local/generation-settings", dependencies=[Depends(get_current_superadmin)])
KEY = "local.anima.settings.v1"
Name = Annotated[str, StringConstraints(strip_whitespace=True, max_length=512)]


class Form(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Lora(Form):
    name: Annotated[Name, Field(min_length=1)]
    strength: FiniteFloat


class Character(Form):
    model: Name = ""
    loras: list[Lora] = Field(default_factory=list)


class Common(Character):
    encoder: Name = ""
    vae: Name = ""
    width: int = Field(default=1024, ge=16, multiple_of=16)
    height: int = Field(default=1024, ge=16, multiple_of=16)
    steps: int = Field(default=20, gt=0)
    cfg: FiniteFloat = 4
    sampler: Name = "euler"
    scheduler: Name = "normal"


class Endpoint(Form):
    endpoint: str = "http://127.0.0.1:8188"

    @field_validator("endpoint")
    @classmethod
    def local_only(cls, value):
        Comfy(value)  # constructs a handle without connecting
        return value


class Config(Endpoint):
    common: Common = Field(default_factory=Common)
    characters: dict[int, Character] = Field(default_factory=dict)

    def inputs_for(self, cpu_id):
        c = self.common
        profile = self.characters.get(cpu_id, Character())
        values = c.model_dump(exclude={"loras"})
        return (Settings(**values, loras=tuple((x.name, x.strength) for x in c.loras)),
                {"character_model": profile.model or None,
                 "character_loras": tuple((x.name, x.strength) for x in profile.loras)})


class Write(Config):
    expected_revision: int = Field(ge=0)


@router.get("")
def read(session: Session = Depends(get_session)):
    row = session.get(GameSetting, KEY)
    return row.value if row else {"revision": 0, **Config().model_dump(mode="json")}


@router.put("")
def save(body: Write, session: Session = Depends(get_session)):
    current = read(session)
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
