from typing import Literal
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr, Field, model_validator

Slot = Literal['win', 'defeat_stage_1', 'defeat_stage_2', 'defeat_stage_3', 'match_first']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class ManualEdit(StrictModel):
    text: StrictStr


class LegacyEdit(StrictModel):
    legacy_dialogue_id: StrictInt
    expected_source_text: StrictStr


class FixedDialoguePatch(StrictModel):
    expected_revision: StrictInt = Field(ge=0)
    edits: dict[Slot, ManualEdit | LegacyEdit]

    @model_validator(mode='after')
    def nonempty(self):
        if not self.edits:
            raise ValueError('edits must not be empty')
        return self
