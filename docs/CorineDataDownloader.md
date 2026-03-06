# CorineDataDownloader

## Overview

`CorineDataDownloader` downloads CORINE Land Cover polygons for a study area from the
European Environment Agency ArcGIS service.

Use it when you already have a boundary geometry and need land cover input for the
HeatSense analysis workflow.

## Import

```python
from heatsense.data.corine_downloader import CorineDataDownloader
```

## Basic usage

```python
from heatsense.data.corine_downloader import CorineDataDownloader


downloader = CorineDataDownloader(year_or_period=(2015, 2020))
landcover = downloader.download_for_area("data/boundary.geojson")

print(downloader.selected_year)
print(len(landcover))
```

## Key parameters

### Constructor

- `year_or_period`: year, date string, `datetime`, or `(start, end)` tuple
- `record_count`: page size for API requests
- `timeout`: request timeout in seconds
- `verbose`: enable console logging
- `log_file`: optional log file path

### `download_for_area()`

- `geometry_input`: boundary as file path, `Path`, or `GeoDataFrame`
- `target_crs`: output CRS, default `EPSG:4326`

## Returns

`download_for_area()` returns a `GeoDataFrame` with CORINE polygons and attributes.

## Notes

- The downloader automatically chooses the best available CORINE year for the requested
  period and exposes it as `selected_year`.
- Bounding boxes are transformed to Web Mercator internally because the upstream CORINE
  service expects that projection.
- Large downloads are handled through pagination.
