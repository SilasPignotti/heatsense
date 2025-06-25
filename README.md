# Urban Heat Island Analyzer

Ein Python-basiertes System zur Analyse von Urban Heat Islands (UHI) basierend auf Satellitendaten, Wetterdaten, Landnutzung und geografischen Grenzen.

## 🏗️ Projektstruktur

```
urban_heat_island_analyzer/
├── data/                          # Datenverzeichnis
│   ├── processed/                 # Verarbeitete Daten
│   │   ├── weather/              # Wetterdaten
│   │   └── uhi_analysis/         # UHI-Analyseergebnisse
│   └── raw/                      # Rohdaten
│       ├── boundaries/           # Verwaltungsgrenzen
│       └── landcover/            # Landnutzungsdaten
├── docs/                         # Dokumentation
│   ├── corine_downloader.md       # CorineDataDownloader-Dokumentation
│   ├── dwd_downloader.md          # DWDDataDownloader-Dokumentation
│   └── wfs_downloader.md          # WFSDataDownloader-Dokumentation
├── logs/                         # Log-Dateien
├── scripts/                      # Ausführbare Scripts
│   ├── data_processing/          # Datenverarbeitung
│   │   ├── download_berlin_boundaries.py
│   │   ├── download_berlin_weather_data.py
│   │   ├── download_corine_landcover.py
│   │   └── analyze_heat_islands.py
│   └── setup_earth_engine.py     # Google Earth Engine Setup
├── src/                          # Quellcode
│   └── uhi_analyzer/             # Hauptpaket
│       ├── config/               # Konfiguration
│       ├── data/                 # Datenmodule
│       │   ├── corine_downloader.py
│       │   ├── dwd_downloader.py
│       │   ├── wfs_downloader.py
│       │   └── urban_heat_island_analyzer.py
│       ├── utils/                # Hilfsfunktionen
│       ├── visualization/        # Visualisierung
│       └── webapp/               # Web-Anwendung
├── tests/                        # Tests
│   ├── integration/              # Integrationstests
│   └── unit/                     # Unit-Tests
├── pyproject.toml                # Projekt-Konfiguration
├── uv.lock                       # Dependency-Lock
└── README.md                     # Diese Datei
```

## 🚀 Schnellstart

### Installation

```bash
# Repository klonen
git clone <repository-url>
cd urban_heat_island_analyzer

# Dependencies installieren (mit uv)
uv sync
```

### Google Earth Engine Setup (für Satellitendaten)

Für die Analyse mit echten Satellitendaten ist eine Google Earth Engine Authentifizierung erforderlich:

```bash
# Earth Engine Setup ausführen
uv run scripts/setup_earth_engine.py
```

**Hinweis:** Sie benötigen ein Google-Konto und müssen sich für Google Earth Engine registrieren:
1. Besuchen Sie https://earthengine.google.com/
2. Registrieren Sie sich für Earth Engine
3. Warten Sie auf die Genehmigung (normalerweise 1-2 Tage)
4. Führen Sie das Setup-Script aus

### Konfiguration

1. **Umgebungsvariablen setzen** (optional):
   ```bash
   export DWD_BUFFER_DISTANCE=5000
   export DWD_INTERPOLATION_RESOLUTION=1000
   ```

2. **Logging konfigurieren**:
   ```bash
   mkdir -p logs
   ```

### Daten herunterladen

#### 1. Berliner Verwaltungsgrenzen
```bash
uv run scripts/data_processing/download_berlin_boundaries.py
```

#### 2. Wetterdaten für Berlin
```bash
uv run scripts/data_processing/download_berlin_weather_data.py --date 2024-06-15
```

#### 3. Corine Land Cover Daten
```bash
uv run scripts/data_processing/download_corine_landcover.py --year 2018
```

#### 4. Urban Heat Island Analyse mit Satellitendaten
```bash
uv run scripts/data_processing/analyze_heat_islands.py \
  --start-date 2023-07-01 \
  --end-date 2023-07-31 \
  --cloud-threshold 15
```

## 🌍 Satellitenbasierte UHI-Analyse

Das System unterstützt jetzt echte Satellitendaten-Analyse mit Google Earth Engine:

### Features
- **Landsat 8 Thermal Data**: Verwendet Landsat 8 Collection 2 Tier 1 Level 2 Daten
- **Cloud Filtering**: Automatische Filterung von wolkenbedeckten Szenen
- **Temperature Extraction**: Extraktion von Oberflächentemperaturen
- **Hotspot Detection**: Identifikation von Wärmeinseln
- **Land Use Correlation**: Korrelation zwischen Landnutzung und Temperaturen
- **Temporal Analysis**: Zeitliche Trendanalyse
- **Ground Validation**: Validierung mit Wetterstationsdaten

### Beispiel: Vollständige Satellitenanalyse

```python
from uhi_analyzer import UrbanHeatIslandAnalyzer
from datetime import date

# Analyzer mit Satellitendaten initialisieren
analyzer = UrbanHeatIslandAnalyzer(cloud_cover_threshold=20)

# Vollständige UHI-Analyse mit Satellitendaten
results = analyzer.analyze_heat_islands(
    city_boundary="data/raw/boundaries/berlin_admin_boundaries.geojson",
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    landuse_data="data/raw/landcover/berlin_corine_landcover_2018.geojson",
    weather_stations="data/processed/weather/berlin_weather_stations.geojson"  # Optional
)

# Ergebnisse visualisieren
analyzer.visualize_results(results, "uhi_satellite_analysis.png")

# Detaillierte Ergebnisse anzeigen
print(f"Temperaturen analysiert: {len(results['temperature_statistics'])}")
print(f"Hotspots identifiziert: {len(results['hot_spots'])}")
print(f"Landnutzungskorrelationen: {len(results['land_use_correlation'])}")

# Mitigationsempfehlungen
for rec in results['mitigation_recommendations']:
    print(f"{rec['type']}: {rec['description']} (Priorität: {rec['priority']})")
```

### Konfigurationsoptionen

```python
# Erweiterte Konfiguration
analyzer = UrbanHeatIslandAnalyzer(
    cloud_cover_threshold=15,  # Max. 15% Wolkenbedeckung
    log_file="logs/satellite_analysis.log"
)

# Analyse mit angepassten Parametern
results = analyzer.analyze_heat_islands(
    city_boundary="berlin.geojson",
    date_range=(date(2023, 6, 1), date(2023, 8, 31)),  # Sommer 2023
    landuse_data="corine_2018.geojson",
    weather_stations="weather_stations.geojson"  # Für Validierung
)
```

## 📊 Datenmodule

### UrbanHeatIslandAnalyzer - Satellitenbasierte UHI-Analyse

```python
from uhi_analyzer import UrbanHeatIslandAnalyzer
from datetime import date

# Analyzer initialisieren
analyzer = UrbanHeatIslandAnalyzer(cloud_cover_threshold=20)

# UHI-Analyse durchführen
results = analyzer.analyze_heat_islands(
    city_boundary="data/raw/boundaries/berlin_admin_boundaries.geojson",
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    landuse_data="data/raw/landcover/berlin_corine_landcover_2018.geojson"
)

# Ergebnisse visualisieren
analyzer.visualize_results(results, "uhi_analysis_results.png")

# Empfehlungen anzeigen
for rec in results['mitigation_recommendations']:
    print(f"{rec['type']}: {rec['description']}")
```

### DWDDataDownloader mit verschiedenen Zeitpunkten

```python
from uhi_analyzer.data.dwd_downloader import DWDDataDownloader
from datetime import datetime

# Service initialisieren
service = DWDDataDownloader(buffer_distance=5000, interpolation_method="linear")

# Daten für spezifischen Zeitpunkt abrufen
timestamp = datetime(2024, 6, 15, 14, 0, 0)  # 15. Juni 2024, 14:00 Uhr
weather_data = service.get_weather_data(
    geometry="path/to/berlin.geojson",
    timestamp=timestamp,
    interpolate=True,
    resolution=1000
)
```

### CorineDataDownloader mit verschiedenen Jahren

```python
from uhi_analyzer.data.corine_downloader import CorineDataDownloader

# Standard (2018)
downloader = CorineDataDownloader()

# Spezifisches Jahr
downloader = CorineDataDownloader(target_year=2012)

# Automatische Jahr-Auswahl
downloader = CorineDataDownloader(target_year=2015)  # Wählt 2012
```

### WFSDataDownloader für verschiedene Geodaten

```python
from uhi_analyzer.data.wfs_downloader import WFSDataDownloader
from uhi_analyzer.config.wfs_config import BERLIN_ADMIN_BOUNDARIES_CONFIG

# Downloader initialisieren
downloader = WFSDataDownloader(config=BERLIN_ADMIN_BOUNDARIES_CONFIG)

# Daten herunterladen
success = downloader.download_and_validate(
    endpoint_name="berlin_admin_boundaries",
    output_path="data/raw/boundaries/berlin.geojson"
)
```

## 🧪 Tests

```bash
# Alle Tests ausführen
uv run pytest

# Spezifische Tests
uv run pytest tests/integration/test_corine_years.py
```

## 📝 Logging

Das System verwendet strukturiertes Logging:

```python
import logging

# Logger konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/application.log'),
        logging.StreamHandler()
    ]
)
```

## 🔧 Konfiguration

### UHI-Analyzer-Einstellungen
- `UHI_CLOUD_COVER_THRESHOLD`: Maximale Wolkenbedeckung in Prozent (Standard: 20)
- `UHI_GRID_CELL_SIZE`: Rasterzellengröße in Metern (Standard: 100)
- `UHI_HOTSPOT_THRESHOLD`: Schwellenwert für Hotspot-Identifikation (Standard: 0.9)
- `UHI_LANDSAT_COLLECTION`: Landsat-Datensammlung (Standard: "LANDSAT/LC08/C02/T1_L2")

### DWD-Einstellungen
- `DWD_BUFFER_DISTANCE`: Buffer um Geometrie in Metern (Standard: 5000)
- `DWD_INTERPOLATION_RESOLUTION`: Auflösung für Interpolation in Metern (Standard: 1000)
- `DWD_INTERPOLATION_METHOD`: Interpolationsmethode (Standard: "linear")

### Corine-Einstellungen
- Unterstützte Jahre: 1990, 2000, 2006, 2012, 2018
- Automatische Jahr-Auswahl basierend auf gewünschtem Jahr

## 📚 Dokumentation

- **[UrbanHeatIslandAnalyzer](docs/urban_heat_island_analyzer.md)** - Satellitenbasierte UHI-Analyse
- **[DWDDataDownloader](docs/dwd_downloader.md)** - DWD Wetterdaten Downloader
- **[CorineDataDownloader](docs/corine_downloader.md)** - Corine Land Cover Daten Downloader
- **[WFSDataDownloader](docs/wfs_downloader.md)** - Web Feature Service Downloader

## 🤝 Beitragen

1. Fork erstellen
2. Feature-Branch erstellen (`git checkout -b feature/amazing-feature`)
3. Änderungen committen (`git commit -m 'Add amazing feature'`)
4. Branch pushen (`git push origin feature/amazing-feature`)
5. Pull Request erstellen

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.
