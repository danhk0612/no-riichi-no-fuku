"""Run the unmodified four W01 browser checks with an owned Vite process."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import socket

root = Path(__file__).resolve().parents[2]
frontend = root / "frontend"
node = shutil.which("node")
env = dict(os.environ, TEST_PYTHON=sys.executable,
           PLAYWRIGHT_MODULE_PATH=str(root / "spikes/w02/out/browser/node_modules/playwright"))
# Refuse to attach to an existing Vite.
with socket.socket() as probe:
    probe.bind(("127.0.0.1", 5173))
vite = subprocess.Popen([node, "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5173", "--strictPort"], cwd=frontend)
try:
    for _ in range(300):
        if vite.poll() is not None:
            raise RuntimeError("Vite exited before ready")
        try:
            with urllib.request.urlopen("http://127.0.0.1:5173", timeout=1):
                break
        except OSError:
            time.sleep(.1)
    else:
        raise RuntimeError("Vite readiness timeout")
    for name in ["dialogue", "connection", "result-asset", "live-game"]:
        subprocess.run([node, f"tests/{name}.browser.mjs"], cwd=frontend, env=env, check=True)
finally:
    vite.terminate()
    vite.wait(timeout=15)
