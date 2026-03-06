# UrbanHeatIslandAnalyzer

## Overview

`UrbanHeatIslandAnalyzer` is the core analysis engine in HeatSense. It combines
satellite temperature data, land cover data, and optional weather station inputs to
identify heat hotspots and summarize urban heat island patterns.

## Import

```python
from datetime import date

from heatsense.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
```

## Basic usage

```python
from datetime import date

from heatsense.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer


analyzer = UrbanHeatIslandAnalyzer(
    cloud_cover_threshold=20,
    grid_cell_size=100,
    hotspot_threshold=0.9,
)

analyzer.initialize_earth_engine(project="your-gee-project-id")

results = analyzer.analyze_heat_islands(
    city_boundary="data/boundary.geojson",
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    landuse_data="data/corine.geojson",
)
```

## With weather station validation

```python
results = analyzer.analyze_heat_islands(
    city_boundary=boundary_gdf,
    date_range=(start_date, end_date),
    landuse_data=landcover_gdf,
    weather_stations=weather_gdf,
)
```

## Key parameters

### Constructor

- `cloud_cover_threshold`: maximum allowed scene cloud cover percentage
- `grid_cell_size`: analysis grid cell size in meters
- `hotspot_threshold`: percentile threshold used to identify hotspots
- `min_cluster_size`: minimum hotspot cluster size
- `use_grouped_categories`: whether grouped land-use categories are used
- `log_file`: optional log file path
- `logger`: optional injected logger

### `initialize_earth_engine()`

- `project`: optional Earth Engine project ID override

### `analyze_heat_islands()`

- `city_boundary`: file path or `GeoDataFrame`
- `date_range`: `(start_date, end_date)` tuple
- `landuse_data`: file path or `GeoDataFrame`
- `weather_stations`: optional `GeoDataFrame`

## Returns

`analyze_heat_islands()` returns a dictionary with analysis outputs such as:

- temperature statistics
- land-use correlation summaries
- hotspot results
- mitigation recommendations
- optional weather validation metrics

## Notes

- Earth Engine must be authenticated before running satellite analysis.
- The analyzer uses the CRS and performance settings defined in
  `src/heatsense/config/settings.py`.
- For most app and CLI workflows, `UHIAnalysisBackend` is the easier entry point.
