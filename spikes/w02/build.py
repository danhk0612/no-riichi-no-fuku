"""Build on the target OS. Copy source/data only into the isolated build tree."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
out = root / "spikes/w02/out"
out.mkdir(exist_ok=True)
args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--noupx",
        "--python-option", "X utf8",
        "--name", "w02-engine", "--distpath", str(out / "engine"), "--workpath", str(out / "work"),
        "--specpath", str(out), "--paths", str(root / "backend")]
for name in ["app", "riichienv", "uvicorn", "sqlalchemy", "alembic", "pytest", "httpx", "psycopg", "psycopg_binary"]:
    args += ["--collect-all", name]
for name in ["fastapi.testclient", "app.spikes.riichienv_0_4_8", "app.simulation.tournament"]:
    args += ["--hidden-import", name]
for source, target in [("backend/app/seeds", "app/seeds"), ("backend/alembic", "alembic"),
                       ("backend/alembic.ini", "."), ("backend/tests", "tests"), ("frontend/dist", "frontend")]:
    args += ["--add-data", f"{root / source}:{target}"]
args.append(str(root / "spikes/w02/engine.py"))
subprocess.run(args, check=True, cwd=root, env={**os.environ, "PYTHONPATH": str(root / "backend")})
shell = out / "shell-source"
shell.mkdir(exist_ok=True)
for name in ["main.cjs", "package.json"]:
    shutil.copy2(root / "spikes/w02" / name, shell / name)
shutil.copytree(out / "engine/w02-engine", shell / "engine", dirs_exist_ok=True)
subprocess.run([shutil.which("node"), str(root / "spikes/w02/node_modules/@electron/packager/bin/electron-packager.mjs"),
                str(shell), "W02-Spike", "--platform=win32", "--arch=x64", "--electron-version=44.7.2",
                f"--out={out / 'shell'}", "--overwrite", "--no-prune"], check=True)
