# WFSDataDownloader - Web Feature Service Downloader

## Overview

The `WFSDataDownloader` is a generic downloader for geodata via Web Feature Service (WFS) APIs. It enables easy downloading of geodata from various WFS services with configurable endpoints and comprehensive logging.

## Features

- **Generic WFS Support**: Works with all WFS 2.0.0 services
- **Configurable Endpoints**: Easy configuration via JSON/YAML
- **Automatic Validation**: GeoJSON validation after download
- **Comprehensive Logging**: Detailed logging of all operations
- **Error Handling**: Robust handling of network and API errors
- **Flexible Output**: Support for various output formats

## Installation

```bash
# Install dependencies
uv add geopandas requests
```

## Basic Usage

```python
from uhi_analyzer.data.wfs_downloader import WFSDataDownloader
from uhi_analyzer.config.wfs_config import BERLIN_ADMIN_BOUNDARIES_CONFIG

# Initialize downloader
downloader = WFSDataDownloader(config=BERLIN_ADMIN_BOUNDARIES_CONFIG)

# Download data
success = downloader.download_and_validate(
    endpoint_name="berlin_admin_boundaries",
    output_path="data/raw/boundaries/berlin.geojson"
)

if success:
    print("Download successful!")
else:
    print("Download failed!")
```

## Configuration

### WFS Endpoint Configuration

```python
# Example configuration
BERLIN_ADMIN_BOUNDARIES_CONFIG = {
    "berlin_admin_boundaries": {
        "url": "https://gdi.berlin.de/services/wfs/alkis_land",
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "alkis_land:landesgrenze",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326"
    }
}
```

### Parameters

- `config`: WFS configuration with endpoints
- `headers`: Optional HTTP headers
- `timeout`: Timeout in seconds (default: 30)
- `log_file`: Optional path for log file

## Advanced Usage

### Multiple Endpoints

```python
# Configuration with multiple endpoints
config = {
    "berlin_boundaries": {
        "url": "https://gdi.berlin.de/services/wfs/alkis_land",
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "alkis_land:landesgrenze",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326"
    },
    "berlin_districts": {
        "url": "https://gdi.berlin.de/services/wfs/alkis_land",
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "alkis_land:bezirksgrenze",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326"
    }
}

downloader = WFSDataDownloader(config=config)

# Use different endpoints
downloader.download_and_validate("berlin_boundaries", "boundaries.geojson")
downloader.download_and_validate("berlin_districts", "districts.geojson")
```

### Custom Headers

```python
# Custom headers for special services
headers = {
    "User-Agent": "MyApp/1.0",
    "Accept": "application/json,application/geojson",
    "Authorization": "Bearer your-token"
}

downloader = WFSDataDownloader(
    config=config,
    headers=headers,
    timeout=60
)
```

### Configure Logging

```python
from pathlib import Path

# Specify log file
log_file = Path("logs/wfs_downloads.log")

downloader = WFSDataDownloader(
    config=config,
    log_file=log_file
)
```

## API Methods

### `download_data(endpoint_name, output_path, **kwargs)`

Downloads data from the WFS service and saves it.

```python
success = downloader.download_data(
    endpoint_name="berlin_boundaries",
    output_path="data/raw/boundaries.geojson",
    maxFeatures=1000  # Additional parameters
)
```

### `validate_geojson(file_path)`

Validates a GeoJSON file.

```python
is_valid = downloader.validate_geojson("data/raw/boundaries.geojson")
if is_valid:
    print("GeoJSON is valid")
```

### `download_and_validate(endpoint_name, output_path, validate=True, **kwargs)`

Downloads data and optionally validates it.

```python
success = downloader.download_and_validate(
    endpoint_name="berlin_boundaries",
    output_path="data/raw/boundaries.geojson",
    validate=True,
    maxFeatures=1000
)
```

### `get_available_endpoints()`

Returns all available endpoints.

```python
endpoints = downloader.get_available_endpoints()
print(f"Available endpoints: {endpoints}")
```

### `get_endpoint_info(endpoint_name)`

Returns information about a specific endpoint.

```python
info = downloader.get_endpoint_info("berlin_boundaries")
print(f"Endpoint info: {info}")
```

## WFS URL Generation

### Automatic URL Generation

```python
# URL is automatically generated from configuration
url = downloader.build_wfs_url("berlin_boundaries")
print(f"WFS URL: {url}")
```

### Additional Parameters

```python
# URL with additional parameters
url = downloader.build_wfs_url(
    "berlin_boundaries",
    maxFeatures=1000,
    filter="name='Berlin'"
)
```

## Error Handling

### Network Errors

```python
try:
    success = downloader.download_data("endpoint", "output.geojson")
    if not success:
        print("Download failed")
except Exception as e:
    print(f"Error: {e}")
```

### Validation Errors

```python
# GeoJSON validation
if downloader.validate_geojson("file.geojson"):
    print("File is valid")
else:
    print("File is invalid")
```

## Logging

The WFSDataDownloader provides comprehensive logging:

```python
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)

# Use downloader
downloader = WFSDataDownloader(config=config)
# Logs show: URL generation, download progress, validation, etc.
```

### Log Examples

```
2024-01-15 10:30:00 - INFO - Downloading data from: https://gdi.berlin.de/services/wfs/alkis_land?...
2024-01-15 10:30:01 - INFO - Data successfully saved: data/raw/boundaries.geojson
2024-01-15 10:30:02 - INFO - GeoJSON validated: 1 features found
2024-01-15 10:30:02 - INFO - CRS: EPSG:4326
```

## Examples

### Complete Example

```python
from uhi_analyzer.data.wfs_downloader import WFSDataDownloader
from pathlib import Path

# Configuration
config = {
    "berlin_boundaries": {
        "url": "https://gdi.berlin.de/services/wfs/alkis_land",
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "alkis_land:landesgrenze",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326"
    }
}

# Initialize downloader
downloader = WFSDataDownloader(
    config=config,
    timeout=30,
    log_file=Path("logs/wfs_downloads.log")
)

# Show available endpoints
print(f"Available endpoints: {downloader.get_available_endpoints()}")

# Download and validate data
success = downloader.download_and_validate(
    endpoint_name="berlin_boundaries",
    output_path="data/raw/boundaries/berlin.geojson",
    validate=True
)

if success:
    print("✅ Download successfully completed")
else:
    print("❌ Download failed")
```

### Multiple Services

```python
# Different WFS services
services = {
    "berlin_boundaries": BERLIN_CONFIG,
    "custom_service": CUSTOM_CONFIG
}

for service_name, service_config in services.items():
    downloader = WFSDataDownloader(config=service_config)
    
    success = downloader.download_and_validate(
        endpoint_name=list(service_config.keys())[0],
        output_path=f"data/raw/{service_name}.geojson"
    )
    
    print(f"{service_name}: {'✅' if success else '❌'}")
```

### Dynamic Configuration

```python
# Create dynamic configuration
def create_wfs_config(base_url, type_name):
    return {
        "endpoint": {
            "url": base_url,
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": type_name,
            "outputFormat": "application/json",
            "srsName": "EPSG:4326"
        }
    }

# Create configuration
config = create_wfs_config(
    "https://example.com/wfs",
    "namespace:feature_type"
)

downloader = WFSDataDownloader(config=config)
```

### Batch Processing

```python
# Process multiple endpoints
endpoints = [
    ("berlin_boundaries", "data/raw/berlin_boundaries.geojson"),
    ("berlin_districts", "data/raw/berlin_districts.geojson"),
    ("berlin_neighborhoods", "data/raw/berlin_neighborhoods.geojson")
]

for endpoint_name, output_path in endpoints:
    success = downloader.download_and_validate(
        endpoint_name=endpoint_name,
        output_path=output_path,
        validate=True
    )
    
    status = "✅" if success else "❌"
    print(f"{endpoint_name}: {status} -> {output_path}")
```

## Performance Optimization

- **Timeout Setting**: Adjust to network speed
- **Caching**: Avoid duplicate downloads
- **Validation**: Only enable when needed
- **Batch Processing**: Process multiple endpoints efficiently

## Troubleshooting

### Common Problems

1. **400 Bad Request**: Check the `typeName` and URL
2. **Timeout**: Increase the timeout value
3. **Invalid GeoJSON**: Check the API response
4. **CRS Issues**: Ensure correct coordinate system

### Debug Mode

```python
import logging

# Enable debug logging
logging.getLogger("uhi_analyzer.data.wfs_downloader").setLevel(logging.DEBUG)

# Use downloader
downloader = WFSDataDownloader(config=config)
# Detailed logs will be output
```

### Error Recovery

```python
# Retry mechanism
max_retries = 3
for attempt in range(max_retries):
    try:
        success = downloader.download_data("endpoint", "output.geojson")
        if success:
            break
    except Exception as e:
        print(f"Attempt {attempt + 1} failed: {e}")
        if attempt == max_retries - 1:
            print("All attempts failed")
```

## Supported WFS Versions

- **WFS 1.0.0**: Basic feature service
- **WFS 1.1.0**: Enhanced feature service
- **WFS 2.0.0**: Full feature service (recommended)

## Output Formats

- **GeoJSON**: Default format for web applications
- **GML**: Geographic Markup Language
- **Shapefile**: ESRI format (via conversion)
- **KML**: Google Earth format (via conversion)

---

**Author:** Urban Heat Island Analyzer Team 