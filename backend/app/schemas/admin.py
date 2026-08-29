from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.profile import ProfileResponse


class MemberResponse(ProfileResponse):
    is_active: bool


class MemberActiveUpdateRequest(BaseModel):
    is_active: bool


class CpuCharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    age_adult: bool
    style: str
    short_description: str
    long_description: str | None
    profile_image_key: str | None
    active: bool
    aggression: float
    defense: float
    call_preference: float
    riichi_preference: float
    hand_value_preference: float
    speed_preference: float


class CpuCharacterCreateRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=80)
    style: str = Field(min_length=1, max_length=40)
    short_description: str = Field(min_length=1, max_length=255)
    long_description: str | None = None
    active: bool = True
    aggression: float
    defense: float
    call_preference: float
    riichi_preference: float
    hand_value_preference: float
    speed_preference: float


class CpuCharacterUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    style: str | None = Field(default=None, min_length=1, max_length=40)
    short_description: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    long_description: str | None = None
    active: bool | None = None
    aggression: float | None = None
    defense: float | None = None
    call_preference: float | None = None
    riichi_preference: float | None = None
    hand_value_preference: float | None = None
    speed_preference: float | None = None

    @model_validator(mode="after")
    def reject_null_for_required_fields(self) -> Self:
        nullable_fields = {"long_description"}
        for field in self.model_fields_set - nullable_fields:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class CpuDialogueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cpu_character_id: int
    event_key: str
    text: str
    active: bool


class CpuDialogueCreateRequest(BaseModel):
    event_key: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1)
    active: bool = True


class CpuDialogueUpdateRequest(BaseModel):
    event_key: str | None = Field(default=None, min_length=1, max_length=64)
    text: str | None = Field(default=None, min_length=1)
    active: bool | None = None

    @model_validator(mode="after")
    def reject_null_fields(self) -> Self:
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self
