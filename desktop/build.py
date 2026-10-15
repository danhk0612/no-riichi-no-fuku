from pathlib import Path
import os
import shutil
import subprocess
import sys


root = Path(__file__).resolve().parents[1]
out = root / "out/w05"
engine_dist = out / "engine"
spec = out / "spec"
engine_dist.mkdir(parents=True, exist_ok=True)
arguments = [
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--noupx",
    "--python-option", "X utf8", "--name", "no-riichi-engine",
    "--distpath", str(engine_dist), "--workpath", str(out / "work"), "--specpath", str(spec),
    "--paths", str(root / "backend"),
]
for package in ["app", "riichienv", "uvicorn", "sqlalchemy", "alembic", "fastapi", "starlette"]:
    arguments += ["--collect-all", package]
arguments += [
    "--hidden-import", "app.simulation.tournament",
    "--hidden-import", "uvicorn.logging",
    "--add-data", f"{root / 'backend/app/seeds'}:app/seeds",
    "--add-data", f"{root / 'backend/alembic'}:alembic",
    "--add-data", f"{root / 'backend/alembic.ini'}:.",
    "--add-data", f"{root / 'frontend/dist'}:frontend",
    str(root / "backend/app/windows_engine.py"),
]
subprocess.run(arguments, check=True, cwd=root, env={**os.environ, "PYTHONPATH": str(root / "backend")})

shell = out / "shell-source"
if shell.exists():
    shutil.rmtree(shell)
shell.mkdir(parents=True)
for name in ["main.cjs", "preload.cjs", "quit.cjs"]:
    shutil.copy2(root / "desktop" / name, shell / name)
(shell / "package.json").write_text(
    '{"name":"no-riichi-no-fuku-desktop","version":"0.1.0","private":true,"main":"main.cjs","license":"MIT"}\n',
    encoding="utf-8",
)
shutil.copytree(engine_dist / "no-riichi-engine", shell / "engine")
shutil.copy2(root / "LICENSE", shell / "LICENSE")
shutil.copy2(root / "THIRD_PARTY_NOTICES.md", shell / "THIRD_PARTY_NOTICES.md")
electron = root / "desktop/node_modules/@electron/packager/bin/electron-packager.mjs"
subprocess.run([
    shutil.which("node"), str(electron), str(shell), "No-Riichi-No-Fuku",
    "--platform=win32", "--arch=x64", "--electron-version=44.7.2",
    f"--out={out / 'package'}", "--overwrite", "--no-prune", "--no-asar",
], check=True, cwd=root)
