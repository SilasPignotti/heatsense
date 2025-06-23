# Urban Heat Island Analyzer

Ein Python-basiertes Tool zur Analyse von Urban Heat Island Effekten in Berlin.

## Projektstruktur

```
urban_heat_island_analyzer/
├── src/
│   └── uhi_analyzer/              # Hauptpaket
│       ├── __init__.py
│       ├── config/                # Konsolidierte Konfiguration
│       │   ├── __init__.py
│       │   ├── settings.py        # Alle Einstellungen und Konstanten
│       │   ├── credentials.py     # API-Schlüssel und Credentials
│       │   └── copernicus_api_key.json
│       ├── data/                  # Datenverarbeitung
│       │   ├── __init__.py
│       │   ├── wfs_downloader.py
│       │   └── corine_downloader.py  # Corine Land Cover Downloader
│       ├── analysis/              # Analyse-Module
│       │   └── __init__.py
│       ├── utils/                 # Hilfsfunktionen
│       │   └── __init__.py
│       ├── visualization/         # Visualisierung
│       │   └── __init__.py
│       └── webapp/                # Web-Anwendung
│           └── __init__.py
├── scripts/                       # Konsolidierte Scripts
│   └── data_processing/
│       ├── download_berlin_boundaries.py
│       └── download_corine_landcover.py
├── notebooks/                     # Jupyter Notebooks
├── data/                          # Vereinfachte Datenstruktur
│   ├── raw/                       # Rohdaten
│   │   ├── boundaries/
│   │   └── landcover/
│   ├── processed/                 # Verarbeitete Daten
│   └── external/                  # Externe Daten
├── results/                       # Ergebnisse
│   ├── figures/
│   ├── maps/
│   └── reports/
├── tests/                         # Tests
│   ├── integration/
│   │   └── test_corine_years.py   # Integrationstests für Corine-Jahre
│   └── unit/
├── docs/                          # Dokumentation
│   ├── corine_downloader.md       # CorineDownloader-Dokumentation
│   └── wfs_downloader.md          # WFSDownloader-Dokumentation
├── logs/                          # Log-Dateien
├── pyproject.toml                 # Projekt-Konfiguration
└── README.md
```

## Hauptverbesserungen

### ✅ Konsolidierte Konfiguration
- **Alle Einstellungen** in `src/uhi_analyzer/config/settings.py`
- **API-Credentials** in `src/uhi_analyzer/config/credentials.py`
- **Keine doppelten Config-Ordner** mehr

### ✅ Vereinfachte Struktur
- **Entfernte unnötige Ordner**: `api/`, `config/` (Root-Level)
- **Konsolidierte Scripts**: Nur noch `scripts/data_processing/`
- **Saubere Notebooks**: Direkt in `notebooks/`

### ✅ Bessere Organisation
- **Klare Trennung** zwischen Code (`src/`) und Daten (`data/`)
- **Zentrale Konfiguration** im Hauptpaket
- **Vereinfachte Imports** durch konsolidierte Module

### ✅ Mehrjährige Corine-Unterstützung
- **Unterstützung für Jahre**: 1990, 2000, 2006, 2012, 2018
- **Automatische Jahr-Auswahl**: Wählt nächstgelegenes verfügbares Jahr
- **Rückwärtskompatibilität**: Bestehende Skripte funktionieren weiterhin

## Installation

```bash
# Mit uv (empfohlen)
uv sync
uv run python -m uhi_analyzer

# Oder mit pip
pip install -e .
```

## Verwendung

### Daten herunterladen

```bash
# Berliner Verwaltungsgrenzen
uv run python scripts/data_processing/download_berlin_boundaries.py

# Corine Land Cover Daten (Standard: 2018)
uv run python scripts/data_processing/download_corine_landcover.py

# Corine Land Cover Daten für spezifisches Jahr
uv run python scripts/data_processing/download_corine_landcover.py --year 2012

# Corine Land Cover Daten mit automatischer Jahr-Auswahl
uv run python scripts/data_processing/download_corine_landcover.py --year 2015  # Wählt 2012
```

### CorineDownloader mit verschiedenen Jahren

```python
from uhi_analyzer.data.corine_downloader import CorineDownloader

# Standard: 2018
downloader = CorineDownloader()

# Spezifisches Jahr
downloader = CorineDownloader(target_year=2012)

# Automatische Auswahl des nächstgelegenen Jahres
downloader = CorineDownloader(target_year=2015)  # Wählt 2012

print(f"Verwendetes Jahr: {downloader.year}")
```

### Konfiguration

Alle Einstellungen sind in `src/uhi_analyzer/config/settings.py` zentralisiert:

```python
from uhi_analyzer.config import WFS_ENDPOINTS, CORINE_BASE_URLS, CORINE_YEARS

# WFS-Konfiguration
print(WFS_ENDPOINTS["berlin_admin_boundaries"])

# Corine-Konfiguration für alle Jahre
print(CORINE_YEARS)  # [1990, 2000, 2006, 2012, 2018]
print(CORINE_BASE_URLS[2012])  # URL für 2012
```

## Entwicklung

Das Projekt folgt modernen Python-Best-Practices:

- **Type Hints** für bessere Code-Qualität
- **Modulare Struktur** für einfache Wartung
- **Zentrale Konfiguration** für einfache Anpassungen
- **Klare Trennung** von Code, Daten und Konfiguration

### Testen der Corine-Funktionalität

```bash
# Test der Jahr-Auswahl und URL-Generierung
uv run python tests/integration/test_corine_years.py
```

## Dokumentation

Weitere Details zu den Downloader-Komponenten finden Sie in der Dokumentation:

- **[CorineDownloader](docs/corine_downloader.md)** - Corine Land Cover Daten Downloader
- **[WFSDownloader](docs/wfs_downloader.md)** - Web Feature Service Downloader
