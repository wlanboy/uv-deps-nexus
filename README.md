# uv

Nexus Python Cache Filler – installiert eine breite Menge gängiger
Python-Pakete über [uv](https://docs.astral.sh/uv/), um den Nexus-PyPI-Proxy
vorzuwärmen (Cache-Füllung), statt eine eigenständige Anwendung
bereitzustellen.

## Voraussetzungen

- Python 3.12 (siehe `.python-version`)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Setup

```bash
uv sync
```

Installiert alle in `pyproject.toml` deklarierten Abhängigkeiten in die lokale `.venv`.

## Ausführen

`main.py` durchsucht rekursiv ein Verzeichnis (Standard: `~/git`) nach
uv-Projekten (erkannt an `uv.lock` oder einer `[tool.uv]`-Sektion in der
`pyproject.toml`), sammelt deren Dependencies (inkl. `optional-dependencies`
und `dependency-groups`) und übernimmt die Paketnamen (ohne
Versions-Constraints, um Auflösungskonflikte zwischen Projekten zu vermeiden)
in die `dependencies`-Liste dieses Projekts. Ein anschließendes `uv sync`
lädt damit alle Pakete über den Nexus-Proxy und füllt so dessen Cache.

```bash
uv run main.py
```

Optionen:

| Flag | Standard | Bedeutung |
|------|----------|-----------|
| `--root PFAD` | `~/git` | Verzeichnis, das nach uv-Projekten durchsucht wird |
| `--pyproject PFAD` | `pyproject.toml` dieses Projekts | Ziel-`pyproject.toml`, in die die Dependencies geschrieben werden |
| `--dry-run` | aus | Zeigt nur an, was geändert würde, ohne zu schreiben |

Beispiel mit anderem Suchpfad:

```bash
uv run main.py --root /pfad/zu/anderen/projekten --dry-run
```

Danach den Cache tatsächlich befüllen:

```bash
uv sync
```

## Nexus als Package-Proxy

Alle Python-Pakete werden nicht direkt von PyPI, sondern über einen internen
Nexus-Proxy (`pypi-proxy`) bezogen. Das reduziert die Abhängigkeit von
externen Servern, beschleunigt wiederholte Installationen durch Caching und
erlaubt eine zentrale Kontrolle über erlaubte Pakete.

Konfiguriert wird das in `pyproject.toml`:

```toml
[[tool.uv.index]]
name = "nexus"
url = "http://localhost:8081/repository/pypi-proxy/simple"
default = true
```

- `name` – Bezeichner des Index, wird u. a. in Log-Ausgaben von `uv` verwendet.
- `url` – Simple-Index-Endpunkt des Nexus-Repositories vom Typ `pypi-proxy`.
- `default = true` – ersetzt den Standard-Index (PyPI) vollständig, d. h.
  `uv add`/`uv sync`/`uv lock` lösen alle Pakete ausschließlich über Nexus auf.

### Voraussetzungen für die Nutzung

- Ein erreichbarer Nexus-Server mit einem PyPI-Proxy-Repository unter
  `http://localhost:8081/repository/pypi-proxy/simple` (Adresse ggf. anpassen,
  falls Nexus nicht lokal läuft, z. B. via VPN/Tunnel oder abweichender
  Host/Port-Kombination).
- Falls das Repository nicht anonym lesbar ist, müssen Zugangsdaten hinterlegt
  werden, z. B. über Umgebungsvariablen:

  ```bash
  export UV_INDEX_NEXUS_USERNAME=<username>
  export UV_INDEX_NEXUS_PASSWORD=<password>
  ```

  (`NEXUS` entspricht hier dem großgeschriebenen `name` aus der Index-Definition.)

### Verhalten bei Sync/Lock

Da `default = true` gesetzt ist, verwendet `uv` **ausschließlich** Nexus als
Quelle – es erfolgt kein Fallback auf das offizielle PyPI. Ist der Nexus-Server
nicht erreichbar, schlagen `uv sync`, `uv add` und `uv lock` fehl.

## Projekte klonen (`clone.sh`)

`clone.sh` klont alle in `projects.txt` gelisteten GitHub-Repositories nach
`~/git`, damit `main.py` möglichst viele uv-Projekte zum Sammeln der
Dependencies vorfindet. Bereits vorhandene Repos (erkannt am `.git`-Ordner
im Zielverzeichnis) werden übersprungen.

```bash
./clone.sh [zielverzeichnis] [projects.txt]
```

| Argument | Standard | Bedeutung |
|----------|----------|-----------|
| `zielverzeichnis` | `.` | Verzeichnis, in das geklont wird |
| `projects.txt` | `projects.txt` | Datei mit einer Repository-URL pro Zeile (Leerzeilen und Zeilen mit `#` werden ignoriert) |

Typischer Ablauf, um den Nexus-Cache mit möglichst vielen Paketen zu befüllen:

```bash
./clone.sh ~/gittest projects.txt
uv run main.py --root ~/gittest
uv sync
```
