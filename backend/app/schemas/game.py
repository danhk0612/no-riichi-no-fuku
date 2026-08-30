from pydantic import BaseModel, ConfigDict


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
