# WFSDownloader - Web Feature Service Downloader

## Übersicht

Der `WFSDownloader` ist ein generischer Downloader für Geodaten über Web Feature Service (WFS) APIs. Er ermöglicht das einfache Herunterladen von Geodaten von verschiedenen WFS-Services mit konfigurierbaren Endpunkten und verschiedenen Ausgabeformaten.

## Features

- **Konfigurierbare Endpunkte**: Unterstützt verschiedene WFS-Services über zentrale Konfiguration
- **Flexible Ausgabeformate**: Unterstützt GeoJSON und andere Formate
- **Automatische Validierung**: Optional GeoJSON-Validierung nach Download
- **Umfassendes Logging**: Detaillierte Protokollierung aller Operationen
- **Fehlerbehandlung**: Robuste Behandlung von Netzwerk- und API-Fehlern
- **Timeout-Konfiguration**: Anpassbare Timeouts für HTTP-Requests

## Konfiguration

### WFS-Endpunkte

Die WFS-Endpunkte sind in `src/uhi_analyzer/config/settings.py` konfiguriert:

```python
from uhi_analyzer.config import WFS_ENDPOINTS

# Beispiel-Konfiguration
WFS_ENDPOINTS = {
    "berlin_admin_boundaries": {
        "url": "https://gdi.berlin.de/services/wfs/alkis_land", 
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "alkis_land:landesgrenze",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326"
    }
}
```

### HTTP-Header

Standard-Header für WFS-Requests:

```python
WFS_HEADERS = {
    "User-Agent": "Urban-Heat-Island-Analyzer/1.0",
    "Accept": "application/json,application/geojson"
}
```

## Verwendung

### Grundlegende Initialisierung

```python
from uhi_analyzer.data.wfs_downloader import WFSDownloader
from uhi_analyzer.config import WFS_ENDPOINTS, WFS_HEADERS

# Downloader initialisieren
downloader = WFSDownloader(
    config=WFS_ENDPOINTS,
    headers=WFS_HEADERS,
    timeout=30,
    log_file=Path("logs/wfs_downloads.log")
)
```

### Daten herunterladen

```python
# Einfacher Download
success = downloader.download_data(
    endpoint_name="berlin_admin_boundaries",
    output_path="data/raw/boundaries/berlin_boundaries.geojson"
)

# Download mit zusätzlichen Parametern
success = downloader.download_data(
    endpoint_name="berlin_admin_boundaries",
    output_path="data/raw/boundaries/berlin_boundaries.geojson",
    maxFeatures=1000,
    bbox="13.0,52.0,14.0,53.0"
)
```

### Download mit Validierung

```python
# Download mit automatischer GeoJSON-Validierung
success = downloader.download_and_validate(
    endpoint_name="berlin_admin_boundaries",
    output_path="data/raw/boundaries/berlin_boundaries.geojson",
    validate=True
)
```

### URL-Generierung

```python
# WFS-URL manuell generieren
url = downloader.build_wfs_url(
    endpoint_name="berlin_admin_boundaries",
    maxFeatures=500
)
print(f"WFS-URL: {url}")
```

## Funktionalitäten

### Endpunkt-Verwaltung

```python
# Verfügbare Endpunkte anzeigen
endpoints = downloader.get_available_endpoints()
print(f"Verfügbare Endpunkte: {endpoints}")

# Endpunkt-Informationen abrufen
info = downloader.get_endpoint_info("berlin_admin_boundaries")
print(f"Endpunkt-Info: {info}")
```

### GeoJSON-Validierung

```python
# GeoJSON-Datei validieren
is_valid = downloader.validate_geojson("data/raw/boundaries/berlin_boundaries.geojson")
if is_valid:
    print("GeoJSON ist gültig")
else:
    print("GeoJSON ist ungültig")
```

### Benutzerdefinierte Konfiguration

```python
# Eigene WFS-Konfiguration erstellen
custom_config = {
    "my_wfs_service": {
        "url": "https://example.com/wfs",
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "my:layer",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326"
    }
}

# Downloader mit eigener Konfiguration
downloader = WFSDownloader(config=custom_config)
```

## Logging

Der WFSDownloader bietet umfassendes Logging:

```python
# Logger-Konfiguration
downloader = WFSDownloader(
    config=WFS_ENDPOINTS,
    log_file=Path("logs/wfs_downloads.log")
)
```

Beispiel-Log-Ausgabe:
```
2024-01-15 10:30:00 - INFO - Lade Daten von: https://gdi.berlin.de/services/wfs/alkis_land?service=WFS&version=2.0.0&request=GetFeature&typeNames=alkis_land:landesgrenze&outputFormat=application/json&srsName=EPSG:4326
2024-01-15 10:30:05 - INFO - Daten erfolgreich gespeichert: data/raw/boundaries/berlin_boundaries.geojson
2024-01-15 10:30:05 - INFO - GeoJSON validiert: 12 Features gefunden
2024-01-15 10:30:05 - INFO - CRS: EPSG:4326
```

## Fehlerbehandlung

Der Downloader behandelt verschiedene Fehlertypen:

```python
try:
    success = downloader.download_data(
        endpoint_name="invalid_endpoint",
        output_path="output.geojson"
    )
    if not success:
        print("Download fehlgeschlagen")
except KeyError as e:
    print(f"Endpunkt nicht gefunden: {e}")
except Exception as e:
    print(f"Unerwarteter Fehler: {e}")
```

## Kommandozeile

Das Download-Skript für Berliner Grenzen:

```bash
# Berliner Verwaltungsgrenzen herunterladen
uv run scripts/data_processing/download_berlin_boundaries.py
```

## Ausgabedateien

Heruntergeladene Daten werden im folgenden Format gespeichert:

```
data/raw/boundaries/
├── berlin_admin_boundaries.geojson
└── large_test_area.geojson
```

## WFS-Parameter

Häufig verwendete WFS-Parameter:

| Parameter | Beschreibung | Beispiel |
|-----------|--------------|----------|
| `maxFeatures` | Maximale Anzahl Features | `maxFeatures=1000` |
| `bbox` | Bounding Box Filter | `bbox=13.0,52.0,14.0,53.0` |
| `filter` | CQL-Filter | `filter=name='Berlin'` |
| `startIndex` | Start-Index für Paginierung | `startIndex=0` |
| `count` | Anzahl Features pro Request | `count=100` |

## Best Practices

### 1. Timeout-Konfiguration

```python
# Längere Timeouts für große Datasets
downloader = WFSDownloader(
    config=WFS_ENDPOINTS,
    timeout=60  # 60 Sekunden
)
```

### 2. Validierung aktivieren

```python
# Immer validieren für kritische Daten
success = downloader.download_and_validate(
    endpoint_name="berlin_admin_boundaries",
    output_path="output.geojson",
    validate=True
)
```

### 3. Logging verwenden

```python
# Log-Datei für Debugging
downloader = WFSDownloader(
    config=WFS_ENDPOINTS,
    log_file=Path("logs/wfs_downloads.log")
)
```

### 4. Fehlerbehandlung

```python
# Robuste Fehlerbehandlung
if not downloader.download_data(endpoint_name, output_path):
    logger.error("Download fehlgeschlagen")
    # Fallback-Logik implementieren
```

## Erweiterte Verwendung

### Batch-Downloads

```python
# Mehrere Endpunkte herunterladen
endpoints = ["berlin_admin_boundaries", "other_boundaries"]
for endpoint in endpoints:
    success = downloader.download_data(
        endpoint_name=endpoint,
        output_path=f"data/raw/boundaries/{endpoint}.geojson"
    )
    if not success:
        print(f"Download fehlgeschlagen für {endpoint}")
```

### Dynamische URL-Generierung

```python
# URLs für verschiedene Parameter generieren
bboxes = [
    "13.0,52.0,14.0,53.0",
    "12.0,51.0,15.0,54.0"
]

for i, bbox in enumerate(bboxes):
    url = downloader.build_wfs_url(
        endpoint_name="berlin_admin_boundaries",
        bbox=bbox
    )
    print(f"URL {i+1}: {url}")
``` 