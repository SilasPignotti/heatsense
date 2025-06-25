# WFS Data Downloader Documentation

The `WFSDataDownloader` class provides a comprehensive solution for downloading geospatial data from WFS (Web Feature Service) endpoints with flexible configuration and robust error handling.

## Overview

The WFS downloader supports:
- Multiple WFS endpoints with flexible configuration
- Various output formats (GeoJSON, GeoPackage, Shapefile, GML)
- Automatic retry mechanism with exponential backoff
- Coordinate reference system transformation
- Data validation and comprehensive logging
- Feature counting and endpoint validation

## Quick Start

### Basic Usage

```python
from uhi_analyzer.data.wfs_downloader import WFSDataDownloader

# Initialize with default Berlin WFS endpoints
downloader = WFSDataDownloader()

# Download Berlin districts as GeoDataFrame
districts_gdf = downloader.download_to_geodataframe("berlin_districts")

# Save Berlin state boundary to file
downloader.download_and_save(
    endpoint_name="berlin_state_boundary",
    output_path="berlin_boundary.geojson",
    output_format="geojson"
)
```

### Command Line Usage

```bash
# Download all Berlin boundaries
uv run scripts/data_processing/download_berlin_boundaries.py

# Download only districts in GeoPackage format
uv run scripts/data_processing/download_berlin_boundaries.py --type districts --format gpkg

# Download to specific directory with CRS transformation
uv run scripts/data_processing/download_berlin_boundaries.py \
  --type state \
  --format shp \
  --output-dir custom_output \
  --crs EPSG:25833

# List available endpoints
uv run scripts/data_processing/download_berlin_boundaries.py --list-endpoints
```

## Available WFS Endpoints

The downloader comes pre-configured with Berlin-specific WFS endpoints:

| Endpoint Name | Description | Data Source |
|---------------|-------------|-------------|
| `berlin_state_boundary` | Berlin state administrative boundary | ALKIS Land |
| `berlin_districts` | Berlin districts (Bezirke) | Datenvielfalt |
| `berlin_ortsteile` | Berlin neighborhoods (Ortsteile) | Datenvielfalt |
| `berlin_lor_planungsraeume` | LOR planning areas | Datenvielfalt |
| `berlin_bezirke_alkis` | Berlin districts from ALKIS | ALKIS Verwaltung |

## API Reference

### Class: WFSDataDownloader

#### Constructor

```python
WFSDataDownloader(
    endpoints: Optional[Dict[str, Dict[str, Any]]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    max_features: int = 10000,
    retry_attempts: int = 3,
    retry_delay: int = 2,
    log_file: Optional[Union[str, Path]] = None
)
```

**Parameters:**
- `endpoints`: WFS endpoint configurations (uses default if None)
- `headers`: HTTP headers for requests
- `timeout`: Request timeout in seconds
- `max_features`: Maximum features per request
- `retry_attempts`: Number of retry attempts on failure
- `retry_delay`: Delay between retries in seconds
- `log_file`: Optional log file path

#### Core Methods

##### download_to_geodataframe()

Download WFS data directly to a GeoDataFrame.

```python
gdf = downloader.download_to_geodataframe(
    endpoint_name="berlin_districts",
    bbox=(13.0, 52.3, 13.8, 52.7),  # Bounding box (minx, miny, maxx, maxy)
    cql_filter="BEZIRK='Mitte'",    # CQL filter
    max_features=100,               # Limit features
    target_crs="EPSG:25833"        # Transform to UTM
)
```

**Parameters:**
- `endpoint_name`: Name of the WFS endpoint
- `bbox`: Optional bounding box as (minx, miny, maxx, maxy)
- `cql_filter`: Optional CQL filter for features
- `max_features`: Maximum number of features to download
- `target_crs`: Target coordinate reference system for transformation
- `**kwargs`: Additional WFS parameters

**Returns:** GeoDataFrame with downloaded data

##### download_and_save()

Download WFS data and save to file.

```python
success = downloader.download_and_save(
    endpoint_name="berlin_ortsteile",
    output_path="berlin_neighborhoods.gpkg",
    output_format="gpkg",
    bbox=(13.2, 52.4, 13.6, 52.6),
    target_crs="EPSG:25833"
)
```

**Parameters:**
- `endpoint_name`: Name of the WFS endpoint
- `output_path`: Path for output file
- `output_format`: Output format ('geojson', 'gpkg', 'shp', 'gml')
- `bbox`: Optional bounding box
- `cql_filter`: Optional CQL filter
- `max_features`: Maximum features to download
- `target_crs`: Target CRS for transformation
- `**kwargs`: Additional WFS parameters

**Returns:** True if successful, False otherwise

#### Utility Methods

##### get_available_endpoints()

```python
endpoints = downloader.get_available_endpoints()
# Returns: ['berlin_state_boundary', 'berlin_districts', ...]
```

##### get_endpoint_info()

```python
info = downloader.get_endpoint_info("berlin_districts")
# Returns endpoint configuration dictionary
```

##### get_feature_count()

```python
count = downloader.get_feature_count(
    endpoint_name="berlin_districts",
    cql_filter="BEZIRK='Mitte'"
)
print(f"Available features: {count}")
```

##### validate_endpoint()

```python
is_valid = downloader.validate_endpoint("berlin_districts")
if is_valid:
    print("Endpoint is accessible")
```

## Advanced Usage

### Custom WFS Endpoints

```python
# Define custom endpoints
custom_endpoints = {
    "my_custom_layer": {
        "url": "https://example.com/wfs",
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "my_layer:features",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "description": "My custom WFS layer"
    }
}

# Initialize with custom endpoints
downloader = WFSDataDownloader(endpoints=custom_endpoints)
```

### Spatial Filtering

```python
# Download only features within a bounding box
gdf = downloader.download_to_geodataframe(
    endpoint_name="berlin_districts",
    bbox=(13.3, 52.45, 13.5, 52.55)  # Central Berlin area
)

# Use CQL filter for attribute-based filtering
gdf = downloader.download_to_geodataframe(
    endpoint_name="berlin_districts",
    cql_filter="BEZIRK IN ('Mitte', 'Kreuzberg')"
)
```

### Error Handling and Logging

```python
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)

# Initialize with log file
downloader = WFSDataDownloader(
    log_file="logs/wfs_downloads.log",
    retry_attempts=5,
    retry_delay=3
)

try:
    gdf = downloader.download_to_geodataframe("berlin_districts")
    print(f"Downloaded {len(gdf)} features")
except Exception as e:
    print(f"Download failed: {e}")
```

### Batch Downloads

```python
# Download multiple boundary types
boundary_types = [
    ("berlin_state_boundary", "state_boundary.geojson"),
    ("berlin_districts", "districts.geojson"),
    ("berlin_ortsteile", "neighborhoods.geojson")
]

for endpoint, filename in boundary_types:
    print(f"Downloading {endpoint}...")
    success = downloader.download_and_save(
        endpoint_name=endpoint,
        output_path=f"boundaries/{filename}",
        output_format="geojson"
    )
    if success:
        print(f"✅ Downloaded {filename}")
    else:
        print(f"❌ Failed to download {filename}")
```

## Configuration

### Default Settings

The downloader uses settings from `src/uhi_analyzer/config/settings.py`:

```python
# WFS Configuration
WFS_TIMEOUT = 30                    # Request timeout in seconds
WFS_MAX_FEATURES = 10000           # Maximum features per request
WFS_RETRY_ATTEMPTS = 3             # Number of retry attempts
WFS_RETRY_DELAY = 2                # Delay between retries in seconds

# HTTP Headers
WFS_HEADERS = {
    "User-Agent": "Urban-Heat-Island-Analyzer/1.0",
    "Accept": "application/json,application/geojson,text/xml"
}
```

### Output Formats

| Format | File Extension | Description |
|--------|----------------|-------------|
| `geojson` | `.geojson` | GeoJSON format (default) |
| `gpkg` | `.gpkg` | GeoPackage format |
| `shp` | `.shp` | ESRI Shapefile |
| `gml` | `.gml` | Geography Markup Language |

## Integration Examples

### With Other Downloaders

```python
from uhi_analyzer.data.wfs_downloader import WFSDataDownloader
from uhi_analyzer.data.corine_downloader import CorineDataDownloader

# Download Berlin boundary
wfs_downloader = WFSDataDownloader()
berlin_boundary = wfs_downloader.download_to_geodataframe("berlin_state_boundary")

# Use boundary for Corine land cover download
corine_downloader = CorineDataDownloader()
landcover_data = corine_downloader.process_to_geodataframe(
    year_or_period=2018,
    geometry=berlin_boundary
)
```

### With UHI Analysis

```python
from uhi_analyzer.data.wfs_downloader import WFSDataDownloader
from uhi_analyzer.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer

# Download boundaries
downloader = WFSDataDownloader()
downloader.download_and_save(
    endpoint_name="berlin_state_boundary",
    output_path="data/raw/boundaries/berlin_boundary.geojson"
)

# Use in UHI analysis
uhi_analyzer = UrbanHeatIslandAnalyzer()
results = uhi_analyzer.analyze_heat_islands(
    city_boundary="data/raw/boundaries/berlin_boundary.geojson",
    # ... other parameters
)
```

## Troubleshooting

### Common Issues

1. **Connection Timeouts**
   ```python
   # Increase timeout for slow connections
   downloader = WFSDataDownloader(timeout=60, retry_attempts=5)
   ```

2. **Large Downloads**
   ```python
   # Handle large datasets with chunking
   total_features = downloader.get_feature_count("berlin_ortsteile")
   chunk_size = 1000
   
   all_data = []
   for offset in range(0, total_features, chunk_size):
       chunk = downloader.download_to_geodataframe(
           endpoint_name="berlin_ortsteile",
           max_features=chunk_size,
           startIndex=offset
       )
       all_data.append(chunk)
   
   combined_gdf = gpd.pd.concat(all_data, ignore_index=True)
   ```

3. **CRS Issues**
   ```python
   # Always specify target CRS for consistent results
   gdf = downloader.download_to_geodataframe(
       endpoint_name="berlin_districts",
       target_crs="EPSG:25833"  # UTM Zone 33N for Berlin
   )
   ```

### Endpoint Validation

```python
# Test all endpoints
downloader = WFSDataDownloader()
for endpoint in downloader.get_available_endpoints():
    is_valid = downloader.validate_endpoint(endpoint)
    status = "✅" if is_valid else "❌"
    print(f"{status} {endpoint}")
```

### Debug Mode

```python
import logging

# Enable debug logging for detailed information
logging.getLogger("uhi_analyzer.data.wfs_downloader").setLevel(logging.DEBUG)

# This will show:
# - Built WFS URLs
# - Request attempts and retries
# - Response validation details
# - CRS transformations
```

## Performance Tips

1. **Use appropriate max_features**: Don't download more data than needed
2. **Apply spatial filters**: Use bounding boxes to limit geographic scope
3. **Use CQL filters**: Filter by attributes to reduce data volume
4. **Choose efficient formats**: GeoPackage is often faster than Shapefile for large datasets
5. **Cache results**: Save frequently used boundaries locally
6. **Validate endpoints**: Check endpoint availability before batch operations

## Related Documentation

- [Berlin WFS Services](https://gdi.berlin.de/)
- [OGC WFS Specification](https://www.ogc.org/standards/wfs)
- [GeoPandas Documentation](https://geopandas.org/)
- [CQL Filter Specification](https://docs.geoserver.org/stable/en/user/tutorials/cql/cql_tutorial.html) 