"""Windows desktop entry point for the existing local runtime."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import threading
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

from app.local_runtime import create_local_runtime


def _frontend_directory() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    candidate = base / "frontend"
    if not candidate.is_dir():
        raise RuntimeError("bundled React files are missing")
    return candidate


async def _serve(data_root: Path, identity: str, port: int) -> None:
    runtime = create_local_runtime(data_root)
    app = runtime.app
    app.state.local_identity = identity

    @app.get("/api/health")
    def local_health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/_local/identity")
    def local_identity() -> dict[str, str]:
        return {"identity": identity}

    app.mount("/", StaticFiles(directory=_frontend_directory(), html=True), name="desktop-ui")
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
        loop="asyncio",
        http="h11",
        ws="websockets",
    )
    server = uvicorn.Server(config)
    def read_host_commands() -> None:
        try:
            for line in sys.stdin:
                try:
                    command = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if command == {"type": "capability"}:
                    print(json.dumps({"type": "capability", "value": runtime.capability}), flush=True)
                elif command == {"type": "shutdown"}:
                    server.should_exit = True
                    return
        finally:
            server.should_exit = True

    reader = threading.Thread(target=read_host_commands, name="desktop-host-channel", daemon=True)
    reader.start()
    try:
        serve_task = asyncio.create_task(server.serve())
        while not server.started and not serve_task.done():
            await asyncio.sleep(0.025)
        if not server.started:
            await serve_task
            raise RuntimeError("loopback server did not become ready")
        bound_port = int(server.servers[0].sockets[0].getsockname()[1])
        print(json.dumps({"type": "ready", "identity": identity, "pid": os.getpid(), "port": bound_port}), flush=True)
        await serve_task
    finally:
        runtime.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="No Riichi No Fuku local engine")
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    if not args.identity.isascii() or not args.identity or len(args.identity) > 80:
        print("invalid host identity", file=sys.stderr)
        return 2
    if not 0 <= args.port <= 65535:
        print("invalid loopback port", file=sys.stderr)
        return 2
    try:
        asyncio.run(_serve(args.data, args.identity, args.port))
    except Exception as error:
        print(f"local engine startup failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
