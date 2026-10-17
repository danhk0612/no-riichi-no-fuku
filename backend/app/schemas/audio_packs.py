from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AudioPackSelectionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    sfx_mode: Literal["legacy", "pack"]
    sfx_pack_id: str | None = None
    bgm_mode: Literal["legacy", "pack"]
    bgm_pack_id: str | None = None


class CharacterVoiceSelectionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    selection_mode: Literal["default", "selected", "off"]
    selected_pack_id: str | None = None
