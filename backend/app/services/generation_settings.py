"""Stored image generation preferences. Reading them never performs network I/O."""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StringConstraints, field_validator

from app.db.models import GameSetting
from app.services.anima_adapter import Comfy, Settings

KEY = "local.anima.settings.v1"
Name = Annotated[str, StringConstraints(strip_whitespace=True, max_length=512)]


class Form(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Lora(Form):
    name: Annotated[Name, Field(min_length=1)]
    trigger: Name = ""
    strength: FiniteFloat


class Character(Form):
    model: Name = ""
    loras: list[Lora] = Field(default_factory=list)


class Common(Character):
    model_revision: int = Field(default=1, ge=1)
    encoder: Name = ""
    vae: Name = ""
    width: int = Field(default=1024, ge=16, le=16384, multiple_of=16)
    height: int = Field(default=1024, ge=16, le=16384, multiple_of=16)
    steps: int = Field(default=20, gt=0)
    cfg: FiniteFloat = 4
    sampler: Name = "euler"
    scheduler: Name = "normal"


    @field_validator("width", "height", mode="before")
    @classmethod
    def align_dimension(cls, value):
        if isinstance(value, int) or isinstance(value, str) and value.isdecimal():
            return max(16, min(16384, (int(value) + 8) // 16 * 16))
        return value


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

    def triggers_for(self, cpu_id):
        return ", ".join(row.trigger for row in self.characters.get(cpu_id, Character()).loras if row.trigger)

    def inputs_for(self, cpu_id):
        c = self.common
        profile = self.characters.get(cpu_id, Character())
        values = c.model_dump(exclude={"loras"})
        return (Settings(**values, loras=tuple((x.name, x.strength) for x in c.loras)),
                {"character_model": profile.model or None,
                 "character_loras": tuple((x.name, x.strength) for x in profile.loras)})


def read_settings(session):
    row = session.get(GameSetting, KEY)
    return row.value if row else {"revision": 0, **Config().model_dump(mode="json")}


def match_inputs(session):
    from pydantic import ValidationError

    saved = read_settings(session)
    if not isinstance(saved, dict):
        return None
    try:
        return Config.model_validate({k: v for k, v in saved.items() if k != "revision"})
    except ValidationError:
        # Damaged optional image preferences must not prevent a mahjong match.
        return None
