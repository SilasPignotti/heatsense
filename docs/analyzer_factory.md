# AnalyzerFactory Documentation 🏭

Ein intelligentes Factory-Pattern zur automatischen Auswahl des optimalen UHI-Analyzers basierend auf Performance-Modi und Analyse-Anforderungen.

## Überblick

Das `analyzer_factory` Modul bietet Factory-Funktionen zur Erstellung der geeigneten UHI-Analyzer-Instanz:

- **Automatische Auswahl** zwischen `UrbanHeatIslandAnalyzer` und `FastUrbanHeatIslandAnalyzer`
- **Performance-Mode basierte Konfiguration**
- **Intelligente Empfehlungen** basierend auf Analysegebietsgröße
- **Einheitliche API** für alle Analyzer-Typen

## Performance-Modi

### Verfügbare Modi

| Modus | Grid-Größe | Cloud-Threshold | Analyzer-Typ | Anwendung |
|-------|------------|-----------------|--------------|-----------|
| `preview` | 300m | 40% | Fast | Web-Vorschau, sehr große Gebiete (>500 km²) |
| `fast` | 200m | 30% | Fast | Interaktive Analyse, große Gebiete (200-500 km²) |
| `standard` | 100m | 20% | Regular | Ausgewogene Analyse, mittlere Gebiete (50-200 km²) |
| `detailed` | 50m | 20% | Regular | Höchste Qualität, kleine Gebiete (<50 km²) |

## API-Referenz

### Analyzer erstellen

```python
from uhi_analyzer.utils.analyzer_factory import create_analyzer

# Standard-Analyzer (automatisch Fast-Analyzer)
analyzer = create_analyzer()

# Mit Performance-Modus
analyzer = create_analyzer(
    performance_mode="fast",
    cache_dir="/custom/cache",
    max_cache_age_days=7
)

# Mit benutzerdefinierten Parametern
analyzer = create_analyzer(
    performance_mode="detailed",
    cloud_cover_threshold=15,
    grid_cell_size=75
)
```

### Empfehlungen basierend auf Gebietsgröße

```python
from uhi_analyzer.utils.analyzer_factory import get_analyzer_recommendation

# Empfehlung für verschiedene Gebietsgrößen
small_area = get_analyzer_recommendation(25)    # → "detailed"
medium_area = get_analyzer_recommendation(150)  # → "standard"
large_area = get_analyzer_recommendation(400)   # → "fast"
huge_area = get_analyzer_recommendation(800)    # → "preview"

# Analyzer basierend auf Empfehlung erstellen
area_km2 = 120
recommended_mode = get_analyzer_recommendation(area_km2)
analyzer = create_analyzer(performance_mode=recommended_mode)
```

### Performance-Modi auflisten

```python
from uhi_analyzer.utils.analyzer_factory import list_performance_modes

modes = list_performance_modes()
for mode, config in modes.items():
    print(f"{mode}:")
    print(f"  Grid-Größe: {config['grid_size_m']}m")
    print(f"  Cloud-Threshold: {config['cloud_threshold_pct']}%")
    print(f"  Empfohlen für: {config['recommended_for']}")
```

## Intelligente Auswahl-Logik

### Analyzer-Typ Auswahl

Die Factory wählt automatisch den optimalen Analyzer-Typ:

```python
# FastUrbanHeatIslandAnalyzer für Performance-Modi
if mode_config.get("use_fast_analyzer", True):
    return FastUrbanHeatIslandAnalyzer(...)
    
# UrbanHeatIslandAnalyzer für höchste Qualität
else:
    return UrbanHeatIslandAnalyzer(...)
```

### Parameter-Vererbung

Performance-Modi überschreiben Standardparameter:

```python
# Mode-Konfiguration wird angewendet
analyzer = create_analyzer(
    performance_mode="fast",
    custom_parameter="wird_überschrieben"
)

# Mode-Parameter haben Vorrang vor benutzerdefinierten Werten
```

## Praktische Anwendung

### Web-Anwendung

```python
# Schnelle Vorschau für Webapp
preview_analyzer = create_analyzer(
    performance_mode="preview",
    cache_dir="./webapp_cache"
)

# Vollständige Analyse auf Anfrage
detailed_analyzer = create_analyzer(
    performance_mode="detailed",
    cache_dir="./analysis_cache"
)
```

### Wissenschaftliche Analyse

```python
# Gebietsgröße bestimmen
area_bounds = (13.0883, 52.3381, 13.7611, 52.6755)
area_km2 = calculate_area_km2(area_bounds)

# Optimaler Modus basierend auf Gebietsgröße
mode = get_analyzer_recommendation(area_km2)
analyzer = create_analyzer(
    performance_mode=mode,
    cache_dir=f"./cache_{mode}",
    max_cache_age_days=30
)

print(f"Analysegebiet: {area_km2:.1f} km²")
print(f"Gewählter Modus: {mode}")
print(f"Analyzer-Typ: {analyzer.__class__.__name__}")
```

### Batch-Processing

```python
# Verschiedene Gebiete mit optimalen Einstellungen
areas = {
    "Mitte": 25,      # Klein → detailed
    "Kreuzberg": 100, # Mittel → standard  
    "Pankow": 350,    # Groß → fast
    "Brandenburg": 850 # Sehr groß → preview
}

analyzers = {}
for area_name, area_km2 in areas.items():
    mode = get_analyzer_recommendation(area_km2)
    analyzers[area_name] = create_analyzer(
        performance_mode=mode,
        cache_dir=f"./cache_{area_name.lower()}"
    )
    print(f"{area_name}: {mode} mode ({area_km2} km²)")
```

## Konfiguration

### Umgebungsvariablen

```bash
export UHI_CACHE_DIR="/opt/uhi_cache"
export UHI_CACHE_MAX_AGE_DAYS=14
export UHI_PERFORMANCE_MODE="fast"
```

### Custom Performance-Modi

```python
# Eigene Performance-Modi in settings.py definieren
CUSTOM_PERFORMANCE_MODES = {
    "ultra_fast": {
        "grid_cell_size": 500,
        "cloud_cover_threshold": 50,
        "use_fast_analyzer": True,
        "skip_temporal_trends": True
    }
}
```

## Best Practices

### Modus-Auswahl Richtlinien

1. **preview**: Nur für erste Einschätzungen und sehr große Gebiete
2. **fast**: Standard für interaktive Anwendungen und große Gebiete
3. **standard**: Ausgewogen für wissenschaftliche Analysen mittlerer Gebiete
4. **detailed**: Nur für finale, hochqualitative Analysen kleiner Gebiete

### Performance-Optimierung

```python
# Cache-Verzeichnis pro Anwendung trennen
webapp_analyzer = create_analyzer(
    performance_mode="fast",
    cache_dir="./cache_webapp"
)

research_analyzer = create_analyzer(
    performance_mode="detailed", 
    cache_dir="./cache_research",
    max_cache_age_days=7  # Kürzere Gültigkeit für Forschung
)
```

### Fehlerbehandlung

```python
def create_robust_analyzer(performance_mode="fast", **kwargs):
    """Robuste Analyzer-Erstellung mit Fallback."""
    try:
        return create_analyzer(
            performance_mode=performance_mode,
            **kwargs
        )
    except Exception as e:
        print(f"Fehler mit Modus {performance_mode}: {e}")
        print("Fallback zu Standard-Analyzer...")
        return create_analyzer()  # Standard ohne Modus
```

## Monitoring & Debugging

### Performance-Vergleich

```python
import time

modes = ["preview", "fast", "standard"]
results = {}

for mode in modes:
    analyzer = create_analyzer(performance_mode=mode)
    
    start_time = time.time()
    # Analyse durchführen...
    end_time = time.time()
    
    results[mode] = {
        "duration": end_time - start_time,
        "analyzer_type": analyzer.__class__.__name__,
        "grid_size": analyzer.grid_cell_size
    }

for mode, stats in results.items():
    print(f"{mode}: {stats['duration']:.1f}s "
          f"({stats['analyzer_type']}, {stats['grid_size']}m)")
```

### Cache-Effizienz überwachen

```python
analyzer = create_analyzer(performance_mode="fast")
stats = analyzer.get_cache_stats()

print(f"Cache-Hits: {stats.get('cache_hits', 0)}")
print(f"Cache-Misses: {stats.get('cache_misses', 0)}")
print(f"Cache-Größe: {stats['total_size_mb']:.1f} MB")
```

## Troubleshooting

### Häufige Probleme

**Unerwarteter Analyzer-Typ**
```python
# Prüfen der Mode-Konfiguration
from uhi_analyzer.config.settings import UHI_PERFORMANCE_MODES
print(UHI_PERFORMANCE_MODES["standard"]["use_fast_analyzer"])
```

**Parameter werden überschrieben**
```python
# Performance-Modi haben Vorrang - explizit prüfen
analyzer = create_analyzer(performance_mode="fast")
print(f"Tatsächliche Grid-Größe: {analyzer.grid_cell_size}")
```

**Cache-Probleme**
```python
# Cache-Verzeichnis manuell setzen
analyzer = create_analyzer(
    cache_dir="/tmp/debug_cache",
    max_cache_age_days=1
)
```
