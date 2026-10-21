from pydantic import BaseModel, Field, StrictInt


class LocalPlayStateResponse(BaseModel):
    generation: str
    phase: str
    roster: list[dict[str, object]]
    ending_event_id: str | None
    ending_payload: dict[str, object] | None
    active_session_id: str | None
    recent_session_id: str | None
    legacy_active: bool
    result_resume: dict[str, object] | None = None


class LocalRosterRequest(BaseModel):
    generation: str
    cpu_character_ids: list[int] = Field(min_length=3)


class LocalResetRequest(BaseModel):
    generation: str
    confirm: bool


class LocalEndingAckRequest(BaseModel):
    generation: str
    ending_event_id: str


class LocalResultAckRequest(BaseModel):
    generation: str
    event_id: str
    ordinal: StrictInt = Field(ge=1)
    expected_delivery_revision: StrictInt = Field(ge=0)
