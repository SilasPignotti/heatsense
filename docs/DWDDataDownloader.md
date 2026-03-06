# DWDDataDownloader

## Overview

`DWDDataDownloader` retrieves weather station data from DWD and can optionally create
an interpolated temperature surface for a study area.

Use it when you need station-based ground validation for the urban heat island workflow.

## Import

```python
from heatsense.data.dwd_downloader import DWDDataDownloader
```

## Basic usage

```python
from datetime import datetime

from heatsense.data.dwd_downloader import DWDDataDownloader


downloader = DWDDataDownloader()
stations, interpolated = downloader.download_for_area(
    geometry="data/boundary.geojson",
    start_date=datetime(2023, 7, 1),
    end_date=datetime(2023, 7, 31),
    interpolate=True,
)
```

## Station-only usage

```python
from datetime import datetime

from heatsense.data.dwd_downloader import DWDDataDownloader


downloader = DWDDataDownloader(interpolate_by_default=False)
stations = downloader.download_for_area(
    geometry="data/boundary.geojson",
    start_date=datetime(2023, 7, 1),
    end_date=datetime(2023, 7, 31),
    interpolate=False,
)
```

## Key parameters

### Constructor

- `buffer_distance`: search buffer around the study area in meters
- `interpolation_method`: `linear`, `nearest`, or `cubic`
- `interpolate_by_default`: whether interpolation is enabled by default
- `interpolation_resolution`: grid resolution in meters
- `log_file`: optional log file path
- `verbose`: enable console logging

### `download_for_area()`

- `geometry`: study area as GeoJSON, Shapely geometry, or `GeoDataFrame`
- `start_date`: period start as `datetime`
- `end_date`: period end as `datetime`
- `interpolate`: override interpolation behavior for this call
- `resolution`: optional interpolation grid resolution override

## Returns

- If `interpolate=False`: a `GeoDataFrame` with station temperatures
- If `interpolate=True`: `(stations_gdf, interpolated_gdf)`

## Notes

- Interpolation falls back to nearest-neighbor behavior for sparse station networks.
- The downloader standardizes output so it can be passed into the higher-level analysis
  flow without extra reshaping.
