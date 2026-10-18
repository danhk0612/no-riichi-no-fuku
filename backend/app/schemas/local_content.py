"""Pack manifest v1; data validation only, with no content defaults or application."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import PureWindowsPath
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

PackKind = Literal["character", "sfx", "bgm", "voice"]
Digest = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[StrictStr, Field(min_length=1)]


class PackValidationError(ValueError):
    pass


def relative_file(value: str) -> str:
    parts = value.split("/")
    if (
        not value
        or PureWindowsPath(value).drive
        or "\\" in value
        or ":" in value
        or any(p in {"", ".", ".."} or p.endswith((" ", ".")) for p in parts)
        or any(any(ord(c) < 32 or c in '<>"|?*' for c in p) for p in parts)
        or any(
            re.fullmatch(r"(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", p, re.I)
            for p in parts
        )
    ):
        raise PackValidationError("invalid relative file reference")
    return value


# IDs become directory components in distributable Windows packs.
EnglishId = Annotated[
    StrictStr,
    Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$", max_length=80),
    AfterValidator(relative_file),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PromptPair(StrictModel):
    positive: StrictStr
    negative: StrictStr


class CharacterPrompts(StrictModel):
    appearance: PromptPair
    upper_underwear: PromptPair
    lower_underwear: PromptPair


class ImageReferences(StrictModel):
    profile: StrictStr | None
    full_body: StrictStr | None
    cg: StrictStr | None

    @field_validator("profile", "full_body", "cg")
    @classmethod
    def safe_reference(cls, value):
        return relative_file(value) if value is not None else None


class ImageFraming(StrictModel):
    profile: PromptPair
    full_body: PromptPair
    cg: PromptPair


class CharacterLevel(StrictModel):
    images: ImageReferences
    framing: ImageFraming


class SharedDependency(StrictModel):
    namespace: EnglishId
    id: EnglishId
    revision_digest: Digest


class VoiceReference(StrictModel):
    character_id: EnglishId
    id: EnglishId


class CharacterMetadata(BaseModel):
    # Preserve all metadata fields; measurement interpretation belongs to explicit application.
    model_config = ConfigDict(extra="allow", strict=True)
    name: Text
    adult: StrictBool
    description: StrictStr | None = None
    style: StrictStr | None = None

    @field_validator("adult")
    @classmethod
    def adult_required(cls, value):
        if value is not True:
            raise ValueError("adult must be true")
        return value


class PackManifest(StrictModel):
    schema_version: StrictInt
    kind: PackKind
    id: EnglishId
    version: Text
    label: Text
    character_id: EnglishId | None = None
    metadata: CharacterMetadata | None = None
    prompts: CharacterPrompts | None = None
    levels: dict[StrictStr, CharacterLevel] | None = None
    shared_dependencies: list[SharedDependency] | None = None
    default_voice_pack: VoiceReference | None = None
    slots: dict[StrictStr, StrictStr] | None = None

    @model_validator(mode="after")
    def validate_kind(self):
        if self.schema_version != 1:
            raise ValueError("unsupported schema_version")
        common = {"schema_version", "kind", "id", "version", "label"}
        if self.kind == "character":
            allowed = common | {
                "character_id",
                "metadata",
                "prompts",
                "levels",
                "shared_dependencies",
                "default_voice_pack",
            }
            if (
                self.character_id != self.id
                or self.metadata is None
                or self.prompts is None
                or self.levels is None
                or set(self.levels) != {"0", "1", "2", "3"}
                or self.shared_dependencies is None
                or "default_voice_pack" not in self.model_fields_set
            ):
                raise ValueError(
                    "character requires identity, metadata, prompts, four levels and dependency/default references"
                )
        else:
            allowed = (
                common
                | {"slots"}
                | ({"character_id"} if self.kind == "voice" else set())
            )
            if self.slots is None or (
                self.kind == "voice" and self.character_id is None
            ):
                raise ValueError("audio requires slots and voice requires character_id")
            allowed_slots = {
                "sfx": {"tile_discard", "tile_shuffle", "riichi_stick"},
                "bgm": {"title", "selection", "game", "result"},
                "voice": {
                    "chi",
                    "pon",
                    "kan",
                    "riichi",
                    "ron",
                    "tsumo",
                "win",
                    "defeat_stage_1",
                    "defeat_stage_2",
                    "defeat_stage_3",
                    "match_first",
                    "match_last",
                },
            }[self.kind]
            if set(self.slots) - allowed_slots:
                raise ValueError("unsupported v1 slot")
            for value in self.slots.values():
                relative_file(value)
        if self.model_fields_set - allowed:
            raise ValueError("fields do not belong to pack kind")
        if (
            not self.label.strip()
            or not self.version.strip()
            or (self.metadata and not self.metadata.name.strip())
        ):
            raise ValueError("blank label/version/name")
        return self

    def references(self) -> dict[str, str]:
        if self.kind == "character":
            return {
                path: "image"
                for level in self.levels.values()
                for path in level.images.model_dump().values()
                if path is not None
            }
        return {path: "audio" for path in self.slots.values()}

    def identity(self) -> tuple[str, str, str]:
        return self.kind, self.character_id if self.kind == "voice" else "", self.id


class PromptEdit(StrictModel):
    positive: StrictStr | None = None
    negative: StrictStr | None = None

    @model_validator(mode="after")
    def require_a_field(self):
        prompt_fields = self.model_fields_set & {"positive", "negative"}
        if not prompt_fields:
            raise ValueError("at least one prompt field is required")
        if any(getattr(self, key) is None for key in prompt_fields):
            raise ValueError("prompt fields must be strings; null is not an edit")
        return self


class FramingEdit(PromptEdit):
    level: StrictInt = Field(ge=0, le=3)
    kind: Literal["profile", "full_body", "cg"]


MEASUREMENT_KEYS = ("height", "bust", "waist", "hips")


def normalize_measurement(value: str) -> str:
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise ValueError("measurement must be a positive decimal string in cm")
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("measurement must be a positive decimal string in cm") from error
    if not number.is_finite() or number <= 0 or number.as_tuple().exponent < -1:
        raise ValueError("measurement must be positive with at most one decimal place")
    canonical = format(number, "f")
    return canonical if number.as_tuple().exponent == -1 else f"{canonical}.0"


class MeasurementsPatch(StrictModel):
    height: StrictStr | None = None
    bust: StrictStr | None = None
    waist: StrictStr | None = None
    hips: StrictStr | None = None

    @field_validator(*MEASUREMENT_KEYS)
    @classmethod
    def valid_measurement(cls, value):
        return normalize_measurement(value) if value is not None else None

    @model_validator(mode="after")
    def require_a_measurement(self):
        if not self.model_fields_set:
            raise ValueError("at least one measurement field is required")
        return self


class CharacterContentPatch(StrictModel):
    expected_revision: StrictInt = Field(ge=0)
    prompts: dict[Literal["appearance", "upper_underwear", "lower_underwear"], PromptEdit] = Field(default_factory=dict)
    framing: list[FramingEdit] = Field(default_factory=list)
    measurements_cm: MeasurementsPatch | None = None

    @model_validator(mode="after")
    def require_edits(self):
        if "measurements_cm" in self.model_fields_set and self.measurements_cm is None:
            raise ValueError("measurements_cm must be an object")
        if not self.prompts and not self.framing and self.measurements_cm is None:
            raise ValueError("at least one explicit field edit is required")
        return self


class CharacterPackApplication(StrictModel):
    expected_revision: StrictInt = Field(ge=0)
    pack_id: Annotated[StrictStr, Field(min_length=1, max_length=36)]
    registered_revision_id: Annotated[StrictStr, Field(min_length=1, max_length=36)]
