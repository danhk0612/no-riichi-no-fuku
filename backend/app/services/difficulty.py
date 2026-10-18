"""Local difficulty settings and immutable match-start calculation."""
from dataclasses import asdict

from sqlalchemy.orm import Session

from app.db.models import GameSetting
from app.mahjong.difficulty import PROFILES

KEY = "local_cpu_difficulty"
FORMULA = "stage-offset-v1"
FIELDS = ("aggression", "defense", "call_preference", "riichi_preference",
          "hand_value_preference", "speed_preference")


class DifficultyError(ValueError):
    pass


def _integer(value, low, high=None):
    if type(value) is not int or value < low or (high is not None and value > high):
        raise DifficultyError("invalid difficulty integer")
    return value


def read_setting(session: Session):
    row = session.get(GameSetting, KEY)
    value = {"version": 1, "revision": 0, "setting": 5} if row is None else row.value
    if not isinstance(value, dict) or set(value) != {"version", "revision", "setting"}:
        raise DifficultyError("invalid saved difficulty setting")
    if type(value["version"]) is not int or value["version"] != 1:
        raise DifficultyError("unknown difficulty setting version")
    _integer(value["revision"], 0)
    _integer(value["setting"], 1, 10)
    return dict(value)


def resolve(stage: int, mode: str, setting: int, revision: int):
    _integer(stage, 0, 3)
    _integer(setting, 1, 10)
    _integer(revision, 0)
    if mode not in ("progress", "omake") or (mode == "omake" and stage != 3):
        raise DifficultyError("invalid difficulty mode/stage")
    base = None
    if mode == "omake":
        level, reason = 10, "omake"
    elif stage == 3:
        level, reason = 1, "completed_fill"
    else:
        base = (3, 6, 9)[stage]
        level, reason = max(1, min(10, base + setting - 5)), "stage_setting"
    return {"version": 1, "profile": asdict(PROFILES[level - 1]), "formula_version": FORMULA,
            "setting": setting, "setting_revision": revision, "base_level": base, "reason": reason}


def validate_snapshot(snapshot, stage, mode=None):
    if not isinstance(snapshot, dict):
        raise DifficultyError("missing difficulty snapshot")
    mode = mode or ("omake" if snapshot.get("reason") == "omake" else "progress")
    expected = resolve(stage, mode, snapshot.get("setting"), snapshot.get("setting_revision"))
    # Type-sensitive comparison: JSON booleans/floats are not integer identities.
    import json
    if json.dumps(snapshot, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise DifficultyError("unknown or malformed difficulty snapshot")
    return PROFILES[expected["profile"]["level"] - 1]


def summaries(choices):
    if not any(c.difficulty_snapshot is not None or c.policy_version == 3 for c in choices):
        return None
    result = []
    for seat, choice in enumerate(choices, 1):
        if type(choice.policy_version) is not int or choice.policy_version != 3:
            raise DifficultyError("mixed difficulty policies")
        profile = validate_snapshot(choice.difficulty_snapshot, choice.defeat_stage)
        result.append({"seat": seat, "cpu_character_id": choice.id, "level": profile.level,
                       "profile_version": profile.version, "reason": choice.difficulty_snapshot["reason"]})
    return result
