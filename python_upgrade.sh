#!/usr/bin/env bash
set -euo pipefail

# Hebt die für dieses Projekt gepinnte Python-Version an.
# Nutzung: ./python_upgrade.sh [version]

VERSION="${1:-3.14}"
MAJOR_MINOR="$(cut -d. -f1,2 <<< "$VERSION")"

echo "== Installiere Python $VERSION (falls nicht vorhanden) =="
uv python install "$VERSION"

echo "== Pinne Projekt auf Python $VERSION =="
uv python pin "$VERSION"

echo "== Setze requires-python in pyproject.toml auf >=$MAJOR_MINOR =="
sed -i -E "s/^requires-python = \">=[0-9]+\.[0-9]+\"/requires-python = \">=${MAJOR_MINOR}\"/" pyproject.toml

echo "== Entferne bestehende .venv =="
rm -rf .venv

echo "== Baue .venv neu und synce Abhängigkeiten =="
CMAKE_POLICY_VERSION_MINIMUM=3.5 uv sync
