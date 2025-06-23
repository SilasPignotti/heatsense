# CorineDownloader - Corine Land Cover Daten Downloader

## Übersicht

Der `CorineDownloader` ist ein spezialisierter Downloader für Corine Land Cover Daten der Europäischen Umweltagentur (EEA). Das System unterstützt verschiedene Jahre und wählt automatisch das nächstgelegene verfügbare Jahr aus, wenn das gewünschte Jahr nicht verfügbar ist.

## Verfügbare Jahre

Die folgenden Corine Land Cover Jahre sind verfügbar:
- **1990** - Corine Land Cover 1990
- **2000** - Corine Land Cover 2000  
- **2006** - Corine Land Cover 2006
- **2012** - Corine Land Cover 2012
- **2018** - Corine Land Cover 2018 (Standard)

## Verwendung

### Grundlegende Verwendung

```python
from uhi_analyzer.data.corine_downloader import CorineDownloader

# Standard: 2018
downloader = CorineDownloader()

# Spezifisches Jahr
downloader = CorineDownloader(target_year=2012)

# Automatische Auswahl des nächstgelegenen Jahres
downloader = CorineDownloader(target_year=2015)  # Wählt 2012
```

### Kommandozeile

```bash
# Standard (2018)
uv run scripts/data_processing/download_corine_landcover.py

# Spezifisches Jahr
uv run scripts/data_processing/download_corine_landcover.py --year 2012

# Automatische Auswahl
uv run scripts/data_processing/download_corine_landcover.py --year 2015
```

## Automatische Jahr-Auswahl

Das System verwendet die Funktion `get_closest_corine_year()` um das nächstgelegene verfügbare Jahr zu finden:

```python
from uhi_analyzer.config import get_closest_corine_year

# Beispiele
get_closest_corine_year(1985)  # → 1990
get_closest_corine_year(1995)  # → 2000
get_closest_corine_year(2003)  # → 2000
get_closest_corine_year(2010)  # → 2012
get_closest_corine_year(2015)  # → 2012
get_closest_corine_year(2020)  # → 2018
```

## API-Endpunkte

Jedes Jahr hat seinen eigenen ArcGIS REST API-Endpunkt:

- **1990**: `https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC1990_WM/MapServer/0`
- **2000**: `https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2000_WM/MapServer/0`
- **2006**: `https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2006_WM/MapServer/0`
- **2012**: `https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2012_WM/MapServer/0`
- **2018**: `https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2018_WM/MapServer/0`

## Funktionalitäten

### Bounding Box-Extraktion

```python
# Extrahiert Bounding Box aus GeoJSON und transformiert zu EPSG:3857
bbox = downloader.get_bbox_from_geojson("path/to/area.geojson")
```

### URL-Generierung

```python
# Generiert Query-URL für ArcGIS REST API
url = downloader.build_query_url(bbox, offset=0)
```

### Daten-Download

```python
# Lädt alle Features für ein Gebiet herunter (mit Paginierung)
features = downloader.download_for_area("path/to/area.geojson")
```

### Download und Speicherung

```python
# Lädt Daten herunter, clippt sie auf das Polygon und speichert sie
output_path = downloader.download_and_save("path/to/area.geojson")
```

## Ausgabedateien

Die Ausgabedateien werden automatisch mit dem tatsächlich verwendeten Jahr benannt:

```
data/raw/landcover/
├── berlin_corine_landcover_1990.geojson
├── berlin_corine_landcover_2000.geojson
├── berlin_corine_landcover_2006.geojson
├── berlin_corine_landcover_2012.geojson
└── berlin_corine_landcover_2018.geojson
```

## Logging

Das System protokolliert automatisch:
- Das gewünschte Jahr
- Das tatsächlich verwendete Jahr
- Die verwendete Base-URL
- Den Download-Fortschritt

Beispiel-Log:
```
2024-01-15 10:30:00 - INFO - Gewünschtes Jahr 2015 nicht verfügbar. Verwende nächstgelegenes Jahr: 2012
2024-01-15 10:30:00 - INFO - Verwende Corine-Daten für Jahr: 2012
2024-01-15 10:30:00 - INFO - Base URL: https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2012_WM/MapServer/0
```

## Konfiguration

Alle Einstellungen sind in `src/uhi_analyzer/config/settings.py` zentralisiert:

```python
from uhi_analyzer.config import CORINE_YEARS, CORINE_BASE_URLS

# Verfügbare Jahre
print(CORINE_YEARS)  # [1990, 2000, 2006, 2012, 2018]

# URLs für alle Jahre
print(CORINE_BASE_URLS[2012])  # URL für 2012
```

## Testen

Führen Sie das Test-Skript aus, um die Funktionalität zu testen:

```bash
uv run python tests/integration/test_corine_years.py
```

Das Test-Skript überprüft:
- Automatische Jahr-Auswahl
- Downloader-Initialisierung mit verschiedenen Jahren
- URL-Generierung für verschiedene Jahre 