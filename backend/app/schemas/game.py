from pydantic import BaseModel, ConfigDict, Field


class CpuChoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    age_adult: bool
    style: str
    short_description: str
    long_description: str | None
    profile_image_key: str | None
    defeat_stage: int


class CreateGameSessionRequest(BaseModel):
    cpu_character_ids: tuple[int, int, int]


class GamePlayerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seat: int
    name: str
    is_human: bool = Field(serialization_alias="isHuman")


class CreateGameSessionResponse(BaseModel):
    session_id: str
    players: tuple[GamePlayerResponse, ...]
