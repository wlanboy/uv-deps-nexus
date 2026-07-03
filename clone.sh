#!/usr/bin/env bash
set -euo pipefail

# Klont alle in projects.txt gelisteten GitHub-Repositories.
# Nutzung: ./clone.sh [zielverzeichnis] [projects.txt]

TARGET_DIR="${1:-.}"
PROJECTS_FILE="${2:-projects.txt}"

if [[ ! -f "$PROJECTS_FILE" ]]; then
  echo "Datei nicht gefunden: $PROJECTS_FILE" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"

while IFS= read -r url || [[ -n "$url" ]]; do
  [[ -z "$url" || "$url" == \#* ]] && continue

  name="$(basename "$url" .git)"
  dest="$TARGET_DIR/$name"

  if [[ -d "$dest/.git" ]]; then
    echo "== $name existiert bereits, überspringe =="
    continue
  fi

  echo "== Klone $url =="
  git clone "$url" "$dest"
done < "$PROJECTS_FILE"
