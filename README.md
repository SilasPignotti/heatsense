# Urban Heat Island Analyzer 🌡️🏙️

Ein modernes Python-Tool zur Analyse städtischer Wärmeinseln mit Unterstützung für Landsat-Satellitendaten, Landnutzungsdaten und Wetterstationen.

## Features

- 🛰️ **Satellitendatenanalyse** mit Google Earth Engine (Landsat 8)
- 🗺️ **Automatischer Datendownload** für Berlin-Bezirke via WFS
- 🌱 **CORINE Landnutzungsdaten-Integration**  
- 🌡️ **DWD Wetterdaten-Integration** mit räumlicher Interpolation
- 📊 **Statistische Hotspot-Analyse** mit Moran's I
- 🚀 **Performance-Modi** für verschiedene Anwendungsfälle
- 💾 **Intelligentes Caching** für schnellere Wiederholungsanalysen
- 🌐 **Web-API Backend** für Anwendungsintegration
- 📈 **Detaillierte Visualisierungen** und Reports

## Installation

### Voraussetzungen
- Python 3.11+
- Google Earth Engine Account
- UV Package Manager

### Setup

```bash
# Repository klonen
git clone <repository-url>
cd urban_heat_island_analyzer

# Dependencies installieren
uv sync

# Google Earth Engine authentifizieren
uv run earthengine authenticate

# Environment-Variablen setzen
export UHI_EARTH_ENGINE_PROJECT="your-gee-project-id"
```

## Schnellstart

### Einfache Analyse
```python
from uhi_analyzer import FastUrbanHeatIslandAnalyzer
from datetime import date

# Analyzer initialisieren
analyzer = FastUrbanHeatIslandAnalyzer(performance_mode="fast")
analyzer.initialize_earth_engine()

# Analyse durchführen
results = analyzer.analyze_heat_islands(
    city_boundary="data/boundaries/kreuzberg.geojson",
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    landuse_data="data/landuse/corine_kreuzberg.geojson"
)
```

### Command Line Interface
```bash
# Vollständige Analyse für Berlin-Bezirk
uv run python scripts/analyze_heat_islands.py \
    --start-date 2023-07-01 \
    --end-date 2023-07-31 \
    --suburb "Kreuzberg"

# Web-Backend API
uv run python src/uhi_analyzer/webapp/backend/uhi_backend_api.py \
    --area "Mitte" \
    --start-date 2023-06-01 \
    --end-date 2023-08-31 \
    --performance-mode fast
```

## Architektur

### Performance-Modi
- **preview**: Schnelle Vorschau (300m Grid, reduzierte Qualität)
- **fast**: Ausgewogene Geschwindigkeit/Qualität (200m Grid) 
- **standard**: Standard-Qualität (100m Grid)
- **detailed**: Höchste Qualität (50m Grid, wissenschaftlich)

### Cache-System
Das System nutzt intelligentes Caching für optimale Performance:

```
src/uhi_analyzer/webapp/backend/cache/
├── boundaries/       # Bezirksgrenzen
├── earth_engine/     # Satellitendaten-Metadaten  
├── grids/           # Räumliche Analyseraster
├── landcover/       # Landnutzungsklassifikation
└── temperatures/    # Berechnete Temperaturraster
```

### Datenquellen
- **Satellitendaten**: Landsat 8 Collection 2 Tier 1 Level 2
- **Grenzdaten**: Berlin WFS (FIS-Broker)
- **Landnutzung**: CORINE Land Cover (Copernicus)
- **Wetterdaten**: DWD Climate Data Center

## Konfiguration

Zentrale Konfiguration in `src/uhi_analyzer/config/settings.py`:

```python
# Cache-Konfiguration  
UHI_CACHE_DIR = Path(__file__).parent.parent / "webapp" / "backend" / "cache"
UHI_CACHE_MAX_AGE_DAYS = 30
UHI_CACHE_MAX_SIZE_GB = 5.0

# Performance-Modi
UHI_PERFORMANCE_MODES = {
    "preview": {"grid_cell_size": 300, "cloud_cover_threshold": 40},
    "fast": {"grid_cell_size": 200, "cloud_cover_threshold": 30},
    # ...
}
```

## API-Referenz

### FastUrbanHeatIslandAnalyzer
```python
analyzer = FastUrbanHeatIslandAnalyzer(
    performance_mode="fast",           # Performance-Modus
    cache_dir=None,                   # Auto: verwendet UHI_CACHE_DIR
    max_cache_age_days=30,            # Cache-Gültigkeit
    cloud_cover_threshold=20          # Wolkenabdeckung (%)
)
```

### Web-Backend
```python
from uhi_analyzer.webapp.backend import UHIAnalysisBackend

backend = UHIAnalysisBackend(cache_enabled=True)
result = backend.analyze(
    area="Kreuzberg",
    start_date="2023-07-01", 
    end_date="2023-07-31",
    performance_mode="fast"
)
```

## Projektstruktur

```
urban_heat_island_analyzer/
├── src/uhi_analyzer/
│   ├── config/              # Konfiguration
│   ├── data/               # Datenanalyse und -download
│   ├── utils/              # Hilfsfunktionen und Cache
│   └── webapp/backend/     # Web-API Backend
│       └── cache/          # 🆕 Zentraler Cache-Speicher
├── scripts/                # Ausführbare Scripte
├── tests/                 # Unit-Tests
├── docs/                  # Dokumentation
└── data/                  # Ein-/Ausgabedaten
```

## Testing

```bash
# Unit-Tests ausführen
uv run pytest tests/

# Einzelnen Test ausführen
uv run pytest tests/test_urban_heat_island_analyzer.py -v

# Mit Coverage
uv run pytest --cov=uhi_analyzer tests/
```

## Performance-Optimierung

### Cache-Management
```python
# Cache-Statistiken anzeigen
analyzer = FastUrbanHeatIslandAnalyzer()
stats = analyzer.get_cache_stats()
print(f"Cache: {stats['total_files']} Dateien, {stats['total_size_mb']} MB")

# Cache-Typen löschen
analyzer.clear_cache('temperatures')  # Nur Temperaturdaten
analyzer.clear_cache()               # Komplett
```

### Best Practices
- Verwende **fast_cached** Modus für interaktive Anwendungen
- **preview** Modus für schnelle Erkundung
- **detailed** Modus nur für finale Analysen
- Cache-Verzeichnis auf SSD für beste Performance
- Regelmäßige Cache-Bereinigung bei Speicherplatzmangel

## Troubleshooting

### Google Earth Engine Authentifizierung
```bash
# Neu authentifizieren
uv run earthengine authenticate

# Service Account verwenden
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

### Cache-Probleme
```bash
# Cache neu initialisieren
rm -rf src/uhi_analyzer/webapp/backend/cache/
# Analyzer neu starten -> erstellt Cache-Struktur automatisch
```

### Performance-Probleme
- Reduziere `grid_cell_size` für größere Gebiete
- Verwende `performance_mode="preview"` für Tests
- Prüfe verfügbaren Arbeitsspeicher bei detaillierten Analysen

## Beitragen

1. Fork des Repositories
2. Feature-Branch erstellen (`git checkout -b feature/amazing-feature`)
3. Änderungen committen (`git commit -m 'Add amazing feature'`)
4. Branch pushen (`git push origin feature/amazing-feature`)
5. Pull Request erstellen

## Lizenz

MIT Lizenz - siehe `LICENSE` Datei für Details.

## Changelog

### v2.0.0 (Latest)
- ✨ Zentralisierte Cache-Architektur in `webapp/backend/cache/`
- 🚀 Verbesserte Performance durch optimierte Cache-Verwaltung
- 🧹 Bereinigung redundanter Cache-Ordner
- 📦 Einheitliche Konfiguration über `UHI_CACHE_DIR`
- 🔧 Vereinfachte Cache-Parameter in allen Komponenten

### v1.9.0
- 🌐 Web-Backend API für Anwendungsintegration
- 📊 Erweiterte Statistiken und Metadaten
- 🎛️ Flexible Performance-Modi
- 💾 Intelligentes Caching-System

## Support

Bei Fragen oder Problemen:
- Issues im GitHub Repository erstellen
- Dokumentation in `docs/` konsultieren  
- Performance-Leitfäden für Optimierung nutzen
