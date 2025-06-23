# BerlinWeatherService – DWD Wetterdaten Downloader

## Übersicht

Der `BerlinWeatherService` ist ein spezialisierter Service zum Download und zur Interpolation von Wetterdaten (insbesondere Temperatur) für Berlin und Umgebung. Er nutzt die DWD-API über das wetterdienst-Paket und unterstützt die Abfrage von Stationsdaten sowie die Interpolation auf ein reguläres Raster für beliebige Zeitpunkte.

## Features

- **Geometrie-basiert:** Abfrage für beliebige Polygone (z.B. Berlin) möglich
- **Buffer & Auflösung:** Konfigurierbarer Buffer (m) und Interpolationsraster (m)
- **Timestamp-genau:** Liefert für jeden Standort die Messung, die dem Zielzeitpunkt am nächsten liegt
- **Interpolation:** Interpoliert die Stationswerte auf ein regelmäßiges Gitter (linear, nearest, cubic)
- **Konsistente API:** Nur eine Hauptmethode für alle Anwendungsfälle
- **Robustes Logging & Fehlerbehandlung**

## Konfiguration

Alle Einstellungen werden zentral in `src/uhi_analyzer/config/settings.py` verwaltet:

```python
from uhi_analyzer.config.settings import DWD_BUFFER_DISTANCE, DWD_INTERPOLATION_RESOLUTION, DWD_INTERPOLATION_METHOD
```

## Verwendung

### Python (empfohlen)

```python
from uhi_analyzer.data.dwd_downloader import BerlinWeatherService
from shapely.geometry import shape
import geopandas as gpd
from datetime import datetime

# GeoJSON laden (z.B. Berlin)
with open("data/raw/boundaries/berlin_admin_boundaries.geojson") as f:
    geojson = f.read()
geometry = shape(gpd.read_file("data/raw/boundaries/berlin_admin_boundaries.geojson").geometry[0])

# Service initialisieren
service = BerlinWeatherService(buffer_distance=5000, interpolation_method="linear")

# Temperaturdaten für einen Zeitpunkt (z.B. Landsat-Überflug)
timestamp = datetime(2024, 1, 15, 12, 0)
weather_gdf = service.get_weather_data(
    geometry=geometry,
    timestamp=timestamp,
    interpolate=True,   # Interpoliertes Raster
    resolution=1000     # Rasterauflösung in Metern
)

# Ergebnis als GeoJSON speichern
weather_gdf.to_file("berlin_temperature_interpolated_20240115_1200.geojson", driver="GeoJSON")
```

### Kommandozeile

Das zugehörige Script kann direkt genutzt werden:

```bash
uv run scripts/data_processing/download_berlin_weather_data.py --timestamp "2024-01-15 12:00"
```

Weitere Optionen:
- `--output-dir`: Zielverzeichnis
- `--buffer`: Buffer in Metern
- `--resolution`: Rasterauflösung in Metern
- `--no-interpolate`: Nur Stationsdaten, keine Interpolation

## Hauptmethoden

### `get_weather_data(geometry, timestamp, interpolate=True, resolution=1000)`

- **geometry**: Shapely-Objekt oder GeoJSON (Polygon, MultiPolygon, Point)
- **timestamp**: Python-`datetime`-Objekt (z.B. Satellitenüberflug)
- **interpolate**: Ob ein Raster interpoliert werden soll (`True`/`False`)
- **resolution**: Rasterauflösung in Metern

**Rückgabe:**
- GeoDataFrame mit Temperaturwerten (entweder pro Station oder als Raster)

### Interne Methoden (für Fortgeschrittene)
- `_get_stations_in_area(geometry)`: Liefert alle DWD-Stationen im Gebiet
- `_get_temperature_data(station_ids, start, end)`: Holt Rohdaten für Stationen
- `_find_closest_measurements(stations_gdf, timestamp)`: Wählt pro Station die Messung, die dem Zielzeitpunkt am nächsten liegt
- `_interpolate_temperature(stations_gdf, grid_gdf, method)`: Interpoliert Werte auf Raster

## Logging

Alle Schritte werden mit Zeitstempel und Level protokolliert (siehe `logs/berlin_weather_download.log`).

Beispiel-Log:
```
2024-01-15 12:00:00 - INFO - Lade Wetterdaten für Geometrie und Zeitpunkt 2024-01-15 12:00:00
2024-01-15 12:00:01 - INFO - Interpolationsraster erstellt: 887 Punkte mit 1000m Auflösung
2024-01-15 12:00:02 - INFO - Temperaturinterpolation abgeschlossen: 887 Punkte
```

## Ausgabedateien

Die Ergebnisse werden als GeoJSON und PNG gespeichert:

```
data/processed/weather/
├── berlin_temperature_interpolated_20240115_1200.geojson
├── berlin_temperature_20240115_1200.png
```

## Fehlerbehandlung

- Gibt leere DataFrames zurück, wenn keine Stationen oder Messungen gefunden werden
- Loggt alle Fehler mit Traceback
- Bricht bei kritischen Fehlern sauber ab

## Testen

Die Funktionalität kann über das CLI-Script oder eigene Unit-Tests geprüft werden.

---

**Autor:** Urban Heat Island Analyzer Team 