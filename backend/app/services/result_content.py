"""Content is sampled only from a private copy taken at local match creation."""
from copy import deepcopy
from dataclasses import asdict
from random import Random
from hashlib import sha256
import json

from app.services.character_content import get_character_content
from app.services.generation_settings import match_inputs
from app.services.fixed_dialogue import read_fixed, render_text
from app.services.shared_prompts import get_candidates, get_default


def digest(snapshot):
    return sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def capture(db, record):
    seats = {}
    settings = match_inputs(db)
    for seat, choice in enumerate(record.cpu_choices, 1):
        cpu = choice["id"]
        content = get_character_content(db, cpu)
        stage = choice["defeat_stage"]
        levels = {}
        for level in sorted({stage, min(3, stage + 1)}):
            level_data = {"frame": content["levels"][str(level)]["cg"]}
            for kind in ("clothing_state", "situation", "pose"):
                candidates = get_candidates(db, cpu, level, kind)
                default = get_default(db, level, kind)
                level_data[kind] = {
                    "explicit": [] if candidates["uses_default"] else candidates["effective_items"],
                    "default": default["item"], "candidate_revision": candidates["revision"],
                    "default_revision": default["revision"],
                }
            levels[str(level)] = level_data
        seats[str(seat)] = {"id": cpu, "name": record.players[seat]["name"], "stage": stage,
                            "revision": content["revision"], "pack_revision": content["pack_revision_id"],
                            "prompts": content["prompts"], "fixed": read_fixed(db, cpu), "levels": levels}
        if settings is not None:
            common, overrides = settings.inputs_for(cpu)
            seats[str(seat)]["anima"] = {
                **asdict(common), "model": overrides["character_model"] or common.model,
                "loras": [list(row) for row in (*common.loras, *overrides["character_loras"])],
            }
    return deepcopy({"version": 1, "session": record.id, "generation": record.play_generation, "seats": seats})


def dialogue(cpu, slot):
    saved = cpu["fixed"]["slots"].get(slot)
    return {"cpu_id": cpu["id"], "slot": slot, "revision": cpu["fixed"]["revision"],
            "raw": saved["text"] if saved is not None else None,
            "text": render_text(saved["text"], cpu["name"]) if saved is not None else None}


def scene(cpu, stage, event, identity, stage_cg=False):
    level = cpu["levels"][str(stage)]
    rng = Random(identity)  # private, stable per persisted entry
    choices = {}
    for kind in ("clothing_state", "situation", "pose"):
        scope = level[kind]
        def eligible(item):
            return item is not None and (kind != "situation" or event in item["allowed_events"])
        candidates = [x for x in scope["explicit"] if eligible(x)]
        choices[kind] = rng.choice(candidates) if candidates else scope["default"] if eligible(scope["default"]) else None
    parts = [cpu["prompts"]["appearance"]]
    if stage in (1, 2):
        parts.append(cpu["prompts"]["upper_underwear"])
    if stage == 2:
        parts.append(cpu["prompts"]["lower_underwear"])
    parts += [x for x in choices.values() if x is not None] + [level["frame"]]
    result = {"cpu_id": cpu["id"], "stage": stage, "event": event, "choices": choices,
            **{k: "\n".join(p[k] for p in parts if p[k] != "") for k in ("positive", "negative")},
            "media": level["frame"]["media"] if stage_cg else None}
    if not stage_cg and "anima" in cpu:
        # Do not reinterpret older snapshots. A seed is allocated only when an artifact is requested.
        result["generation_input"] = {"workflow": "anima-txt2img-v1", "kind": "hand_cg", "stage": stage,
                                      "positive": result["positive"], "negative": result["negative"],
                                      "settings": deepcopy(cpu["anima"])}
    return result


def resolve(anchor, kind, payload, identity):
    seats = anchor["seats"]
    out = {"version": 1, "event_id": identity, "dialogues": [], "scene": None}
    if kind == "hand":
        winner = next((w for w in payload["fact_snapshot"]["winners"] if w["hora_log_offset"] == payload["displayed_hora_log_offset"]), None)
        if winner and winner["actor"] != 0:
            cpu = seats[str(winner["actor"])]
            event = f'{winner["win_kind"]}_band_{winner["score"]["band"]}'
            out.update(dialogues=[dialogue(cpu, "win")], scene=scene(cpu, cpu["stage"], event, identity))
    else:
        s = payload["presentation"]["settlement"]
        last = payload["ranks"].index(4)
        first = payload["ranks"].index(1)
        if last:
            cpu = seats[str(last)]
            stage = s["defeat_stage"] if s["mode"] == "progress" else 3
            key = f"defeat_stage_{stage}"
            out["dialogues"].append(dialogue(cpu, key))
            if s["stage_changed"]:
                out["scene"] = scene(cpu, stage, key, identity, stage_cg=True)
        if first and s["mode"] == "progress" and seats[str(first)]["stage"] == 3:
            out["dialogues"].append(dialogue(seats[str(first)], "match_first"))
    out["digest"] = digest(out)
    return out
