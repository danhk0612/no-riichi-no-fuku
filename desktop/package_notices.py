"""Copy wheel notices for modules and files selected by the Windows freezer."""
import ast
from importlib.metadata import distributions
from pathlib import Path
import shutil


def collect_engine_notices(analysis: Path, destination: Path):
    # PyInstaller's analysis contains (destination, source, type) entries.
    sections = ast.literal_eval(analysis.read_text(encoding="utf-8"))
    sources = {
        Path(entry[1]).resolve()
        for section in sections if isinstance(section, list)
        for entry in section if isinstance(entry, tuple) and len(entry) == 3
        if isinstance(entry[1], str) and Path(entry[1]).is_absolute()
    }
    destination.mkdir(parents=True)
    inventory = []
    for dist in distributions():
        files = dist.files or []
        if not any(dist.locate_file(file).resolve() in sources for file in files):
            continue
        name = dist.metadata["Name"]
        package = destination / f"{name}-{dist.version}"
        count = 0
        for file in files:
            if ".." in file.parts or file.is_absolute():
                continue
            if not ("licenses" in file.parts or
                    file.name.lower().startswith(("license", "licence", "notice", "copying", "copyright"))):
                continue
            source = dist.locate_file(file)
            if not source.is_file() or source.suffix in {".py", ".pyc"}:
                continue
            target = package / file
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            count += 1
        inventory.append(f"{name} {dist.version} | {count}")
    (destination / "engine-packages.txt").write_text(
        "Package and version | notice files copied\n" + "\n".join(sorted(inventory, key=str.casefold)) + "\n",
        encoding="utf-8",
    )
