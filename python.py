"""Führt python_upgrade.sh für jedes gefundene uv-Projekt unter einem
Wurzelverzeichnis aus, um deren Python-Version anzuheben."""

import argparse
import subprocess
import tomllib
from pathlib import Path

SKIP_DIRS = {
    ".venv", ".git", "__pycache__", "node_modules",
    "target", "dist", "build", ".tox", ".mypy_cache", ".ruff_cache",
}


def find_pyproject_files(root: Path) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in root.walk():
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if "pyproject.toml" in filenames:
            found.append(dirpath / "pyproject.toml")
    return found


def is_uv_project(pyproject_path: Path, data: dict) -> bool:
    if (pyproject_path.parent / "uv.lock").exists():
        return True
    return "uv" in data.get("tool", {})


def find_uv_projects(root: Path) -> list[Path]:
    projects = []
    for path in find_pyproject_files(root):
        try:
            data = tomllib.loads(path.read_text())
        except (tomllib.TOMLDecodeError, OSError) as exc:
            print(f"Übersprungen ({exc}): {path}")
            continue
        if is_uv_project(path, data):
            projects.append(path.parent)
    return projects


def upgrade(project_dir: Path, script: Path, version: str, dry_run: bool) -> None:
    print(f"== {project_dir} ==")
    if dry_run:
        print(f"[dry-run] würde ausführen: {script} {version} (cwd={project_dir})")
        return
    try:
        subprocess.run(["bash", str(script), version], cwd=project_dir, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"Fehlgeschlagen ({exc}): {project_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.home() / "git",
                         help="Verzeichnis, das nach uv-Projekten durchsucht wird")
    parser.add_argument("--version", default="3.14",
                         help="Python-Version, auf die gepinnt werden soll")
    parser.add_argument("--script", type=Path, default=Path(__file__).parent / "python_upgrade.sh",
                         help="Pfad zu python_upgrade.sh")
    parser.add_argument("--dry-run", action="store_true",
                         help="Nur anzeigen, nicht ausführen")
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    script = args.script.resolve()
    projects = find_uv_projects(root)
    print(f"{len(projects)} uv-Projekte gefunden unter {root}")
    for project_dir in projects:
        upgrade(project_dir, script, args.version, args.dry_run)


if __name__ == "__main__":
    main()
