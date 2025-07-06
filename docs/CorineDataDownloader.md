# CorineDataDownloader

## Overview
The `CorineDataDownloader` class provides a specialized interface for downloading Corine Land Cover (CLC) data from the European Environment Agency (EEA). It's designed specifically for urban heat island analysis with automatic year selection and area-based downloads.

## Features
- **Automatic Year Selection**: Intelligently selects the best available Corine year for analysis periods
- **Flexible Input Formats**: Supports various date input formats (year, date range, datetime objects)
- **Area-Based Downloads**: Downloads data for specific geographic areas with automatic bounding box calculation
- **CRS Transformation**: Automatic coordinate reference system handling and transformation
- **Comprehensive Logging**: Built-in logging with detailed progress information

## Usage

### Basic Usage
```python
from uhi_analyzer.data import CorineDataDownloader

# Initialize downloader for a specific year
downloader = CorineDataDownloader(year_or_period=2018)

# Download data for an area
gdf = downloader.download_for_area(geometry_input="path/to/boundary.geojson")
```

### Date Range Analysis
```python
# For analysis covering multiple years
downloader = CorineDataDownloader(year_or_period=(2015, 2020))

# The downloader will automatically select the best available year
print(f"Selected Corine year: {downloader.year}")
```

### Advanced Configuration
```python
downloader = CorineDataDownloader(
    year_or_period=2018,
    record_count=2000,
    timeout=60,
    verbose=True,
    log_file="corine_download.log"
)
```

## Parameters

### Initialization Parameters
- `year_or_period`: Single year, date range, or specific date
  - `int`: Single year (e.g., 2018)
  - `str`: Date string (e.g., "2018", "2018-06-15")
  - `datetime`: Python datetime object
  - `tuple`: Date range (e.g., (2015, 2020))
- `record_count` (int): Number of records per API request (default: 1000)
- `timeout` (int): Request timeout in seconds (default: 30)
- `verbose` (bool): Enable console logging (default: True)
- `log_file` (str, optional): Optional log file path
- `corine_years` (list): Available Corine years (default: [1990, 2000, 2006, 2012, 2018])
- `corine_base_urls` (dict): Base URLs for different Corine years

### Download Parameters
- `geometry_input`: Geometry specification
  - `str/Path`: File path to geometry file
  - `gpd.GeoDataFrame`: GeoDataFrame with geometry
- `target_crs` (str): Target coordinate reference system (default: "EPSG:4326")

## Methods

### `download_for_area()`
Downloads Corine Land Cover data for a specific geographic area.

**Parameters**:
- `geometry_input`: Geometry specification (file path or GeoDataFrame)
- `target_crs` (str): Target coordinate reference system

**Returns**: `gpd.GeoDataFrame` with Corine land cover data

### `get_bbox_from_geometry()`
Extracts bounding box from geometry and transforms to Web Mercator.

**Parameters**:
- `geometry_input`: Geometry specification

**Returns**: `tuple` with bounding box coordinates (xmin, ymin, xmax, ymax)

### `build_query_url()`
Builds query URL for the ArcGIS REST API.

**Parameters**:
- `bbox` (tuple): Bounding box coordinates
- `offset` (int): Result offset for pagination
- `target_crs` (str): Target coordinate reference system

**Returns**: `str` with the complete query URL

## Properties

### `year`
Returns the selected Corine year for the analysis period.

**Returns**: `int` representing the selected year

### `get_available_years()`
Static method that returns all available Corine years.

**Returns**: `list` of available years

## Examples

### Downloading Data for Berlin
```python
import geopandas as gpd
from uhi_analyzer.data import CorineDataDownloader

# Create Berlin boundary
berlin_geom = gpd.GeoDataFrame(
    [1], 
    geometry=[shapely.geometry.box(13.3, 52.4, 13.5, 52.6)], 
    crs="EPSG:4326"
)

# Download Corine data
downloader = CorineDataDownloader(2018)
corine_data = downloader.download_for_area(berlin_geom)
```

### Multi-Year Analysis
```python
# For analysis covering 2015-2020
downloader = CorineDataDownloader(year_or_period=(2015, 2020))
print(f"Using Corine data from year: {downloader.year}")

# Download data
corine_data = downloader.download_for_area("study_area.geojson")
```

### Custom Corine Configuration
```python
# Custom Corine years and URLs
custom_years = [2000, 2006, 2012, 2018]
custom_urls = {
    2000: "https://custom.corine.eea.europa.eu/CLC2000",
    2006: "https://custom.corine.eea.europa.eu/CLC2006",
    # ... other years
}

downloader = CorineDataDownloader(
    year_or_period=2012,
    corine_years=custom_years,
    corine_base_urls=custom_urls
)
```

## Data Structure
The downloaded GeoDataFrame contains:
- **Geometry**: Land cover polygons
- **corine_code**: Numeric Corine land cover codes
- **Additional columns**: Varies by Corine version (e.g., CODE_18, CODE_12, etc.)

## Error Handling
- **Invalid Years**: Validates year ranges (1900-2100)
- **Date Formats**: Supports multiple date input formats
- **Network Errors**: Handles API request failures gracefully
- **Empty Results**: Validates downloaded data completeness
- **CRS Issues**: Automatic coordinate system handling

## Notes
- Automatically handles pagination for large datasets
- Supports all Corine Land Cover versions (1990-2018)
- Uses ArcGIS REST API for data access
- Includes automatic CRS transformation to Web Mercator for API queries
- Provides detailed logging for monitoring download progress 