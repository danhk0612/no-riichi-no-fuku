"""Decode the 45 release clips and audition their pon and discard sounds in manifest order."""
import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
from zipfile import ZipFile


def inspect(archive, output):
    plan = Path(__file__).resolve().parents[2] / "docs/audio/production-ja.json"
    assets = json.loads(plan.read_text("utf-8"))["assets"]
    owners = json.loads((plan.parents[2] / "backend/app/seeds/default_voice_owners.json").read_text("utf-8"))
    assets = [a for a in assets if a["kind"] != "voice" or a["character"] in owners.values()]
    paths = {asset["path"] for asset in assets}
    if len(paths) != 45:
        raise ValueError("Expected 45 distinct release paths")
    comparisons = {"pon": [], "tile_discard": []}
    with ZipFile(archive) as package:
        entries = {}
        for entry in package.infolist():
            path = PurePosixPath(entry.filename)
            if "packs" in path.parts:
                relative = "/".join(path.parts[path.parts.index("packs"):])
                if relative.startswith("packs/voices/") and relative.endswith(".ogg") and relative not in paths:
                    raise ValueError(f"Unexpected voice clip: {relative}")
                if relative in paths:
                    if relative in entries:
                        raise ValueError(f"Duplicate release clip: {relative}")
                    entries[relative] = entry
        missing = paths - entries.keys()
        if missing:
            raise ValueError(f"Missing {len(missing)} clips: {', '.join(sorted(missing))}")
        for asset in assets:
            data = package.read(entries[asset["path"]])
            pcm = subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-f", "ogg", "-i", "pipe:0",
                 "-map", "0:a:0", "-ac", "1", "-ar", "48000", "-f", "s16le", "pipe:1"],
                input=data, stdout=subprocess.PIPE, check=True,
            ).stdout
            if not pcm or not any(pcm):
                raise ValueError(f"Empty or silent clip: {asset['path']}")
            if asset["slot"] in comparisons:
                comparisons[asset["slot"]].append(pcm)
    output.mkdir(parents=True, exist_ok=True)
    for slot, clips in comparisons.items():
        subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "s16le", "-ar", "48000", "-ac", "1",
             "-i", "pipe:0", str(output / f"{slot}-comparison.wav")],
            input=bytes(48000).join(clips), check=True,
        )
    print(f"Decoded {len(paths)} Ogg clips. Comparisons: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    inspect(args.archive, args.output)
