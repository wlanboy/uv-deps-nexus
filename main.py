"""Sammelt Dependencies aus allen uv-Projekten unter ~/git und übernimmt sie
in dieses Projekt, damit ein `uv sync` den Nexus PyPI-Proxy-Cache befüllt."""

import argparse
import re
import tomllib
from pathlib import Path

SKIP_DIRS = {
    ".venv", ".git", "__pycache__", "node_modules",
    "target", "dist", "build", ".tox", ".mypy_cache", ".ruff_cache",
}

REQ_RE = re.compile(
    r"^\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(\[[^\]]*\])?"
)


def normalize_name(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def parse_requirement(req: str) -> tuple[str, set[str]] | None:
    req = req.split(";", 1)[0].strip()  # environment marker abschneiden
    match = REQ_RE.match(req)
    if not match:
        return None
    name, extras = match.groups()
    extras_set = set()
    if extras:
        extras_set = {e.strip() for e in extras.strip("[]").split(",") if e.strip()}
    return name, extras_set


def find_pyproject_files(root: Path, exclude: Path) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in root.walk():
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if dirpath == exclude:
            dirnames[:] = []
            continue
        if "pyproject.toml" in filenames:
            found.append(dirpath / "pyproject.toml")
    return found


def is_uv_project(pyproject_path: Path, data: dict) -> bool:
    if (pyproject_path.parent / "uv.lock").exists():
        return True
    return "uv" in data.get("tool", {})


def extract_requirements(data: dict) -> list[str]:
    reqs = list(data.get("project", {}).get("dependencies", []))
    for group_reqs in data.get("project", {}).get("optional-dependencies", {}).values():
        reqs.extend(group_reqs)
    for group_reqs in data.get("dependency-groups", {}).values():
        for item in group_reqs:
            if isinstance(item, str):
                reqs.append(item)
    return reqs


def merge_requirement(merged: dict[str, tuple[str, set[str]]], req: str) -> None:
    parsed = parse_requirement(req)
    if parsed is None:
        return
    name, extras = parsed
    key = normalize_name(name)
    if key not in merged:
        merged[key] = (name, extras)
        return
    existing_name, existing_extras = merged[key]
    merged[key] = (existing_name, existing_extras | extras)


def format_requirement(name: str, extras: set[str]) -> str:
    extras_part = f"[{','.join(sorted(extras))}]" if extras else ""
    return f"{name}{extras_part}"


def find_array_end(text: str, open_bracket_index: int) -> int:
    """Findet den Index der zu open_bracket_index passenden schließenden ']',
    ohne Klammern innerhalb von Stringliteralen (z.B. "foo[extra]") zu zählen."""
    depth = 0
    in_string = False
    i = open_bracket_index
    while i < len(text):
        char = text[i]
        if in_string:
            if char == "\\":
                i += 1  # escaped Zeichen überspringen
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise RuntimeError("Kein passendes ']' gefunden")


def rewrite_dependencies(pyproject_path: Path, deps: list[str], dry_run: bool) -> None:
    text = pyproject_path.read_text()
    match = re.search(r"dependencies = \[", text)
    if not match:
        raise RuntimeError(f"Kein dependencies-Block in {pyproject_path} gefunden")
    start = match.start()
    open_bracket_index = match.end() - 1
    end = find_array_end(text, open_bracket_index)
    new_block = "dependencies = [\n" + "".join(f'    "{dep}",\n' for dep in deps) + "]"
    new_text = text[:start] + new_block + text[end + 1:]
    if dry_run:
        print(f"[dry-run] {pyproject_path} würde aktualisiert (nicht geschrieben)")
        return
    pyproject_path.write_text(new_text)
    print(f"{pyproject_path} aktualisiert mit {len(deps)} Dependencies")


def collect(root: Path, target_pyproject: Path, dry_run: bool) -> None:
    target_data = tomllib.loads(target_pyproject.read_text())
    merged: dict[str, tuple[str, set[str]]] = {}
    for req in target_data.get("project", {}).get("dependencies", []):
        merge_requirement(merged, req)

    pyproject_files = find_pyproject_files(root, target_pyproject.parent)
    scanned = 0
    for path in pyproject_files:
        try:
            data = tomllib.loads(path.read_text())
        except (tomllib.TOMLDecodeError, OSError) as exc:
            print(f"Übersprungen ({exc}): {path}")
            continue
        if not is_uv_project(path, data):
            continue
        scanned += 1
        for req in extract_requirements(data):
            merge_requirement(merged, req)

    deps = sorted(
        (format_requirement(name, extras) for name, extras in merged.values()),
        key=str.lower,
    )
    print(f"{scanned} uv-Projekte gefunden unter {root}, {len(deps)} Dependencies zusammengeführt")
    rewrite_dependencies(target_pyproject, deps, dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.home() / "git",
                         help="Verzeichnis, das nach uv-Projekten durchsucht wird")
    parser.add_argument("--pyproject", type=Path, default=Path(__file__).parent / "pyproject.toml",
                         help="pyproject.toml, in die die Dependencies übernommen werden")
    parser.add_argument("--dry-run", action="store_true",
                         help="Nur anzeigen, nicht schreiben")
    args = parser.parse_args()
    collect(args.root.expanduser().resolve(), args.pyproject.resolve(), args.dry_run)


if __name__ == "__main__":
    main()
