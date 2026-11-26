"""Durable, local hand-CG cache. The game already owns an exclusive data-root lock."""
import hashlib
import json
import os
from http.client import HTTPException
from dataclasses import asdict
from pathlib import Path
from zlib import crc32
from secrets import randbits
from threading import Lock
from time import time
from uuid import UUID, uuid4

from app.services.anima_adapter import Comfy, LEGACY_WORKFLOW, PromptValidationRejected, Settings, WORKFLOW, graph

_locks = tuple(Lock() for _ in range(64))


def encoded(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def replace(path, data):
    tmp = path.with_name(str(uuid4()) + ".tmp")
    try:
        with tmp.open("xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def valid_png(data):
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or data[12:16] != b"IHDR":
        return False
    pos, pixels = 8, False
    while pos + 12 <= len(data):
        size = int.from_bytes(data[pos:pos+4], "big")
        end = pos + size + 8
        if end + 4 > len(data) or int.from_bytes(data[end:end+4], "big") != crc32(data[pos+4:end]):
            return False
        kind = data[pos+4:pos+8]
        pixels |= kind == b"IDAT" and size > 0
        pos = end + 4
        if kind == b"IEND":
            return pixels and size == 0 and pos == len(data)
    return False


class HandCG:
    def __init__(self, root: Path, client=Comfy):
        self.root, self.client = root, client

    def directory(self, frozen):
        # Normalize optional defaults across old/new snapshots, excluding labels and event IDs.
        identity = {**frozen, "settings": asdict(Settings(**frozen["settings"]))}
        return self.root / hashlib.sha256(encoded(identity)).hexdigest()

    def advance(self, frozen, endpoint, retry=None):
        settings = Settings(**frozen["settings"])
        workflow = frozen["workflow"]
        if workflow not in (LEGACY_WORKFLOW, WORKFLOW) or frozen["kind"] not in ("hand_cg", "profile", "full_body", "cg", "ending"):
            return {"state": "unsupported"}
        if not all((settings.model, settings.encoder, settings.vae)):
            return {"state": "unconfigured"}
        directory = self.directory(frozen)
        with _locks[int(directory.name[:2], 16) % len(_locks)]:
            directory.mkdir(parents=True, exist_ok=True)
            meta = directory / "state.json"
            record = json.loads(meta.read_bytes()) if meta.exists() else None

            def save(state):
                record["state"] = state
                replace(meta, encoded(record))
                return {"state": state, "attempt": record["attempt"]}

            if record and record["state"] == "ready":
                if self._image(directory, record) is not None:
                    return {"state": "ready", "attempt": record["attempt"]}
                return save("missing")
            if record and record["state"] in ("failed", "rejected", "uncertain", "missing", "disconnected") and retry != record["attempt"]:
                return {"state": record["state"], "attempt": record["attempt"]}
            if not record or record["state"] not in ("pending", "disconnected"):
                record = {"attempt": str(uuid4()), "seed": record["seed"] if record else randbits(63),
                          "endpoint": endpoint, "started": time()}
                save("uncertain")  # crash or lost POST reply must never cause automatic resubmission
                client = self.client(endpoint)
                _, output = graph(settings, frozen["positive"], frozen["negative"], record["seed"], workflow=workflow)
                try:
                    job = client.submit(settings, frozen["positive"], frozen["negative"], record["seed"], workflow=workflow)
                except PromptValidationRejected:
                    return save("rejected")
                except (ValueError, KeyError, TypeError):
                    return save("failed")
                except (OSError, HTTPException):
                    return save("uncertain")
                record.update(job=job, output=output)
                return save("pending")

            # Poll the original endpoint even if settings were edited after submission.
            try:
                data = self.client(record["endpoint"]).saved_result(record["job"], record["output"])
            except (OSError, HTTPException):
                return save("disconnected")
            except (ValueError, KeyError, TypeError):
                return save("failed")
            if data is None:
                if time() - record["started"] > 3600:
                    return save("failed")
                if record["state"] != "pending":
                    return save("pending")
                return {"state": "pending", "attempt": record["attempt"]}
            if not valid_png(data):
                return save("failed")
            replace(directory / (record["attempt"] + ".png"), data)
            record["digest"] = hashlib.sha256(data).hexdigest()
            return save("ready")

    @staticmethod
    def _image(directory, record):
        path = directory / (str(UUID(record["attempt"])) + ".png")
        if not path.is_file():
            return None
        data = path.read_bytes()
        return data if hashlib.sha256(data).hexdigest() == record["digest"] else None

    def image(self, frozen, attempt):
        directory = self.directory(frozen)
        meta = directory / "state.json"
        if not meta.exists():
            return None
        record = json.loads(meta.read_bytes())
        if record["state"] == "ready" and attempt == record["attempt"]:
            return self._image(directory, record)
