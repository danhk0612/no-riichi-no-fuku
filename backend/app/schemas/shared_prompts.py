from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

PromptKind = Literal["clothing_state", "pose", "situation"]
SituationEvent = Literal['chi', 'pon', 'kan', 'riichi', 'ron_band_1', 'ron_band_2', 'ron_band_3', 'tsumo_band_1', 'tsumo_band_2', 'tsumo_band_3', 'defeat_stage_1', 'defeat_stage_2', 'defeat_stage_3', 'match_first', 'match_last']
Label = Annotated[StrictStr, Field(min_length=1, max_length=160)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SituationFields(StrictModel):
    allowed_events: list[SituationEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_events(self):
        if len(set(self.allowed_events)) != len(self.allowed_events):
            raise ValueError("duplicate event")
        self.allowed_events.sort()
        return self


class SharedPromptCreate(SituationFields):
    kind: PromptKind
    level: StrictInt = Field(ge=0, le=3)
    label: Label
    positive: StrictStr
    negative: StrictStr

    @model_validator(mode="after")
    def nonblank_label(self):
        if self.kind != "situation" and "allowed_events" in self.model_fields_set:
            raise ValueError("events require a situation")
        if not self.label.strip():
            raise ValueError("label must not be blank")
        return self


class SharedPromptPatch(SituationFields):
    expected_revision: StrictInt = Field(ge=1)
    label: Label | None = None
    positive: StrictStr | None = None
    negative: StrictStr | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        edits = self.model_fields_set - {"expected_revision"}
        if not edits or any(getattr(self, key) is None for key in edits):
            raise ValueError("at least one non-null field edit is required")
        if "label" in edits and not self.label.strip():
            raise ValueError("label must not be blank")
        return self


class DefaultWrite(StrictModel):
    expected_revision: StrictInt = Field(ge=0)
    item_id: StrictStr | None


class CandidateWrite(StrictModel):
    expected_revision: StrictInt = Field(ge=0)
    item_ids: list[StrictStr]


class ChangePreviewRequest(StrictModel):
    expected_revision: StrictInt = Field(ge=1)
    action: Literal["move", "delete"]
    target_level: StrictInt | None = Field(default=None, ge=0, le=3)

    @model_validator(mode="after")
    def target_matches_action(self):
        if (self.action == "move") != (self.target_level is not None):
            raise ValueError("target_level is required only for move")
        return self


class ChangeConfirmation(ChangePreviewRequest):
    preview_digest: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
