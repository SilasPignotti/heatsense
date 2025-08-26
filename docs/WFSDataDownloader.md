# WFSDataDownloader

## Overview
The `WFSDataDownloader` class provides a simple interface for downloading geospatial data from Web Feature Service (WFS) endpoints. It's designed for accessing geodata services with minimal configuration and robust error handling.

## Features
- **Simple Configuration**: Minimal setup required for WFS data access
- **Robust Error Handling**: Automatic retry logic with exponential backoff
- **Flexible Output**: Direct GeoDataFrame output with configurable CRS
- **Comprehensive Logging**: Built-in logging with file and console support

## Usage

### Basic Usage
```python
from uhi_analyzer.data import WFSDataDownloader

# Initialize downloader
downloader = WFSDataDownloader(
    endpoint_url="https://gdi.berlin.de/services/wfs/alkis_bezirke",
    timeout=30,
    max_features=10000
)

# Download data
gdf = downloader.download_to_geodataframe(
    type_name="alkis_bezirke:bezirksgrenzen",
    target_crs="EPSG:4326"
)
```

### Advanced Configuration
```python
downloader = WFSDataDownloader(
    endpoint_url="https://example.com/wfs",
    headers={"User-Agent": "Custom-Agent/1.0"},
    timeout=60,
    max_features=50000,
    retry_attempts=5,
    retry_delay=3,
    log_file="wfs_download.log",
    verbose=True
)
```

## Parameters

### Initialization Parameters
- `endpoint_url` (str): Base URL of the WFS service
- `headers` (dict, optional): HTTP headers for requests
- `timeout` (int): Request timeout in seconds (default: 30)
- `max_features` (int): Maximum features per request (default: 10000)
- `retry_attempts` (int): Number of retry attempts on failure (default: 3)
- `retry_delay` (int): Delay between retries in seconds (default: 2)
- `log_file` (str, optional): Optional log file path
- `verbose` (bool): Enable console logging (default: True)

### Download Parameters
- `type_name` (str): Feature type name for the WFS request
- `max_features` (int, optional): Override default max features
- `output_format` (str): Output format (default: "application/json")
- `target_crs` (str): Target coordinate reference system (default: "EPSG:4326")

## Methods

### `download_to_geodataframe()`
Downloads WFS data and returns it as a GeoDataFrame.

**Returns**: `gpd.GeoDataFrame` with downloaded data

### `build_wfs_url()`
Builds a WFS URL with the specified parameters.

**Returns**: `str` with the complete WFS URL

## Error Handling
The downloader includes comprehensive error handling:
- **Network Errors**: Automatic retry with exponential backoff
- **Invalid Responses**: Validation of WFS service responses
- **Empty Results**: Graceful handling of empty feature sets
- **CRS Issues**: Automatic CRS transformation when needed

## Examples

### Downloading Berlin District Boundaries
```python
from uhi_analyzer.data import WFSDataDownloader
from uhi_analyzer.config.settings import BERLIN_WFS_ENDPOINTS, BERLIN_WFS_FEATURE_TYPES

downloader = WFSDataDownloader(BERLIN_WFS_ENDPOINTS["district_boundary"])
districts = downloader.download_to_geodataframe(
    BERLIN_WFS_FEATURE_TYPES["district_boundary"]
)
```

### Custom WFS Service
```python
downloader = WFSDataDownloader("https://custom-wfs.example.com/wfs")
data = downloader.download_to_geodataframe(
    type_name="custom:features",
    target_crs="EPSG:25833"
)
```

## Notes
- The downloader automatically handles WFS 2.0.0 protocol
- Supports both JSON and XML output formats
- Includes built-in validation of WFS service responses
- Provides detailed logging for debugging and monitoring 