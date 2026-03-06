# WFSDataDownloader

## Overview

`WFSDataDownloader` downloads boundary and reference layers from WFS endpoints and
returns them as `GeoDataFrame` objects.

In HeatSense it is mainly used for Berlin administrative boundaries.

## Import

```python
from heatsense.data.wfs_downloader import WFSDataDownloader
from heatsense.config.settings import BERLIN_WFS_ENDPOINTS, BERLIN_WFS_FEATURE_TYPES
```

## Basic usage

```python
from heatsense.data.wfs_downloader import WFSDataDownloader
from heatsense.config.settings import BERLIN_WFS_ENDPOINTS, BERLIN_WFS_FEATURE_TYPES


downloader = WFSDataDownloader(BERLIN_WFS_ENDPOINTS["district_boundary"])
districts = downloader.download_to_geodataframe(
    BERLIN_WFS_FEATURE_TYPES["district_boundary"]
)
```

## Key parameters

### Constructor

- `endpoint_url`: base WFS URL
- `headers`: optional HTTP headers
- `timeout`: request timeout in seconds
- `max_features`: default feature limit per request
- `retry_attempts`: retry count for failed requests
- `retry_delay`: initial retry delay in seconds
- `log_file`: optional log file path
- `verbose`: enable console logging

### `download_to_geodataframe()`

- `type_name`: feature type name
- `max_features`: optional request-specific limit
- `target_crs`: optional output CRS

## Returns

`download_to_geodataframe()` returns a `GeoDataFrame`.

## Notes

- Requests use retry logic with exponential backoff.
- XML WFS exception responses are detected before parsing as geodata.
- If `target_crs` is provided, the result is reprojected automatically.
