from pydantic import BaseModel, ConfigDict, Field


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login_id: str
    player_name: str | None
    profile_image_key: str | None
    current_hp: int | None
    max_hp: int | None
    role: str
    must_change_password: bool


class UpdateProfileRequest(BaseModel):
    player_name: str = Field(min_length=1, max_length=80)
