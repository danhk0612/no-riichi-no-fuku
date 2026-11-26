"""Shared recipe used by the editor and newly started matches."""
from app.db.models import GameSetting

KEY = "local.image.situations.v1"
EVENTS = {
    "chi": "calling chi, arranging a sequence of mahjong tiles",
    "pon": "calling pon, revealing three matching mahjong tiles",
    "kan": "declaring kan, revealing four matching mahjong tiles",
    "riichi": "declaring riichi, placing a riichi stick on the table",
    "ron": "declaring ron, revealing a winning hand across the table",
    "tsumo": "declaring tsumo, showing the winning drawn tile",
    "defeat": "after a mahjong match, looking down at the final scores",
}
EXPRESSIONS = ("gentle smile", "neutral expression", "embarrassed blush", "tearful eyes")
CLOTHING = (("top", "bottom"), ("bottom", "upper_underwear"),
            ("upper_underwear", "lower_underwear"), ())
STATES = ("fully dressed", "upper outer garment removed, lower outer garment still worn",
          "outer garments removed, wearing underwear only", "all garments removed")
WARDROBE_KEYS = tuple(f"clothing_{level}" for level in range(4))
PRESETS = {**EVENTS, **dict(zip(WARDROBE_KEYS, STATES)),
           **{f"expression_{i}": text for i, text in enumerate(EXPRESSIONS)},
           **{f"profile_{i}": "front view, face only, close-up portrait, looking at viewer" for i in range(4)},
           **{f"full_body_{i}": "front view, standing upright, full body from head to toe" for i in range(4)}}
CG_FRAME = "cinematic composition, mahjong table in the background"


def situations(db):
    row = db.get(GameSetting, KEY)
    saved = row.value if row else {}
    return {key: saved.get(key) or default for key, default in PRESETS.items()}


def compose(prompts, level, kind, frame, presets, event=None, triggers=""):
    parts = [prompts["appearance"], {"positive": triggers}]
    if kind not in ("profile", "ending"):
        parts.extend(prompts[group] for group in CLOTHING[level])
        parts.append({"positive": presets[WARDROBE_KEYS[level]]})
    if kind != "ending":
        parts.append({"positive": presets[f"expression_{level}"]})
    if kind in ("profile", "full_body"):
        if frame.get("overrides", {}).get("positive") and frame["positive"].strip():
            parts.append({"positive": frame["positive"]})
        else:
            parts.append({"positive": presets[f"{kind}_{level}"]})
        if frame.get("overrides", {}).get("negative"):
            parts.append({"negative": frame["negative"]})
    else:
        parts.append({"positive": frame["positive"] if frame["positive"].strip() else CG_FRAME,
                      "negative": frame["negative"]})
        if event:
            parts.append({"positive": presets[event]})
    return {key: "\n".join(p[key] for p in parts if p.get(key, "").strip())
            for key in ("positive", "negative")}
