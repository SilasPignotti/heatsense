# CacheManager Documentation 🗄️

Eine intelligente Caching-Lösung für die Urban Heat Island Analyse zur dramatischen Verbesserung der Performance durch Vermeidung redundanter API-Aufrufe und Berechnungen.

## Überblick

Die `CacheManager`-Klasse bietet ein fortschrittliches Caching-System, das verschiedene Datentypen der UHI-Analyse intelligent zwischenspeichert:

- **Earth Engine Collections** und Temperaturdaten
- **Bezirksgrenzen** (WFS-Downloads)
- **CORINE-Landnutzungsdaten**
- **Analyse-Raster** (Grid-Daten)
- **Korrelationsberechnungen**

## Architektur

### Cache-Verzeichnisstruktur

```
cache/
├── earth_engine/     # Satellitendaten-Metadaten
├── boundaries/       # Bezirksgrenzen  
├── landcover/        # Landnutzungsklassifikation
├── grids/           # Räumliche Analyseraster
└── temperatures/    # Berechnete Temperaturraster
```

### Intelligente Cache-Verwaltung

- **Automatische Bereinigung** alter Dateien
- **Größenbeschränkung** zur Speicherplatz-Kontrolle
- **Eindeutige Schlüssel** basierend auf Parametern
- **Thread-sichere** Operationen

## API-Referenz

### Initialisierung

```python
from uhi_analyzer.utils.cache_manager import CacheManager

cache = CacheManager(
    cache_dir="path/to/cache",     # Cache-Verzeichnis
    max_age_days=30,               # Maximales Alter (Tage)
    max_cache_size_gb=5.0,         # Maximale Größe (GB)
    logger=None                    # Optionaler Logger
)
```

### Earth Engine Daten

```python
# Caching von Earth Engine Collections
cache_key = cache.cache_earth_engine_collection(
    geometry_bounds=(13.0883, 52.3381, 13.7611, 52.6755),
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    cloud_threshold=20,
    data=collection_metadata
)

# Abrufen gecachter Daten
cached_data = cache.get_earth_engine_collection(
    geometry_bounds=(13.0883, 52.3381, 13.7611, 52.6755),
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    cloud_threshold=20
)
```

### Cache-Verwaltung

```python
# Statistiken abrufen
stats = cache.get_cache_stats()
print(f"Dateien gesamt: {stats['total_files']}")
print(f"Größe gesamt: {stats['total_size_mb']} MB")

# Cache leeren
cache.clear_cache()  # Gesamten Cache leeren
cache.clear_cache("temperatures")  # Spezifischen Typ leeren
```

## Integration

```python
from uhi_analyzer.data.fast_urban_heat_island_analyzer import FastUrbanHeatIslandAnalyzer

analyzer = FastUrbanHeatIslandAnalyzer(
    cache_dir="/custom/cache/path",
    max_cache_age_days=14
)

# Cache-Manager ist automatisch integriert
stats = analyzer.get_cache_stats()
analyzer.clear_cache("temperatures")
```
