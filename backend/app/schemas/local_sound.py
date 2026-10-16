from pydantic import BaseModel, ConfigDict, Field


class SoundEffectSetWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=120)
    active: bool = True
    clips: dict[str, str] = Field(default_factory=dict)


class BackgroundTrackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1, max_length=120)
    active: bool = True
    media_asset_id: str


class BackgroundTrackUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str | None = Field(default=None, min_length=1, max_length=120)
    active: bool | None = None
    media_asset_id: str | None = None


class SoundSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effect_set_id: str | None = None
    bgm_ids: list[str] = Field(default_factory=list)


class EndingResources(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cg_asset_id: str | None = None
    music_track_id: str | None = None
    dialogue_text: str | None = Field(default=None, max_length=4000)
