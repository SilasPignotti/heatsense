# DWDDataDownloader

## Overview
The `DWDDataDownloader` class provides a specialized interface for downloading weather data from the German Weather Service (Deutscher Wetterdienst, DWD). It's designed for urban heat island analysis with support for temperature interpolation and multiple processing modes.

## Features
- **Flexible Geometry Input**: Supports points, polygons, GeoJSON, and GeoDataFrames
- **Spatial Interpolation**: Built-in temperature interpolation with configurable methods
- **Multiple Processing Modes**: Station data, interpolated data, and UHI analysis modes
- **Configurable Buffers**: Automatic station search with configurable buffer distances
- **Comprehensive Logging**: Detailed logging for monitoring and debugging

## Usage

### Basic Usage
```python
from uhi_analyzer.data import DWDDataDownloader
from datetime import datetime

# Initialize downloader
downloader = DWDDataDownloader()

# Download weather data for an area
gdf = downloader.download_for_area(
    geometry="path/to/boundary.geojson",
    start_date=datetime(2023, 7, 1),
    end_date=datetime(2023, 7, 31)
)
```

### Advanced Configuration
```python
downloader = DWDDataDownloader(
    buffer_distance=15000,  # 15km buffer
    interpolation_method="cubic",
    interpolate_by_default=True,
    interpolation_resolution=50,  # 50m resolution
    verbose=True,
    log_file="dwd_download.log"
)
```

### Different Processing Modes
```python
# Station data only
station_data = downloader.download_for_area(
    geometry=study_area,
    start_date=start_date,
    end_date=end_date,
    processing_mode='station_data'
)

# Interpolated data
interpolated_data = downloader.download_for_area(
    geometry=study_area,
    start_date=start_date,
    end_date=end_date,
    processing_mode='interpolated'
)

# UHI analysis mode
uhi_data = downloader.download_for_area(
    geometry=study_area,
    start_date=start_date,
    end_date=end_date,
    processing_mode='uhi_analysis'
)
```

## Parameters

### Initialization Parameters
- `buffer_distance` (float): Buffer distance in meters for station search (default: 10000)
- `interpolation_method` (str): Interpolation method ('linear', 'nearest', 'cubic') (default: "linear")
- `interpolate_by_default` (bool): Whether to interpolate by default (default: True)
- `interpolation_resolution` (float): Resolution of interpolation grid in meters (default: 30)
- `log_file` (str, optional): Optional log file path
- `verbose` (bool): Enable console logging (default: True)

### Download Parameters
- `geometry`: Geometry specification
  - `Point/Polygon/MultiPolygon`: Shapely geometry objects
  - `str/dict`: GeoJSON string or dictionary
  - `gpd.GeoDataFrame`: GeoDataFrame with geometry
- `start_date` (datetime): Start date for data period
- `end_date` (datetime): End date for data period
- `interpolate` (bool): Whether to perform interpolation (default: from config)
- `resolution` (float): Resolution of interpolation grid in meters
- `processing_mode` (str): Processing mode ('station_data', 'interpolated', 'uhi_analysis')

## Methods

### `download_for_area()`
Downloads weather data for a geometry and time period.

**Parameters**:
- `geometry`: Geometry specification
- `start_date` (datetime): Start date
- `end_date` (datetime): End date
- `interpolate` (bool): Whether to interpolate
- `resolution` (float): Interpolation grid resolution
- `processing_mode` (str): Processing mode

**Returns**: `gpd.GeoDataFrame` with temperature data

### `_get_stations_in_area()`
Retrieves all weather stations in a given area.

**Parameters**:
- `geometry`: Geometry specification

**Returns**: `gpd.GeoDataFrame` with station information

### `_create_interpolation_grid()`
Creates a regular grid for temperature interpolation.

**Parameters**:
- `geometry`: Geometry specification
- `resolution` (float): Grid resolution

**Returns**: `gpd.GeoDataFrame` with interpolation grid

### `_interpolate_temperature()`
Interpolates temperature data from weather stations onto a grid.

**Parameters**:
- `stations_gdf` (gpd.GeoDataFrame): Station data with temperatures
- `target_gdf` (gpd.GeoDataFrame): Target grid for interpolation
- `method` (str): Interpolation method

**Returns**: `gpd.GeoDataFrame` with interpolated temperatures

## Data Structure

### Station Data Output
When `processing_mode='station_data'` or interpolation is disabled:
- **Geometry**: Point geometries of weather stations
- **station_id**: DWD station identifier
- **name**: Station name
- **ground_temp**: Average temperature (°C)
- **temp_std**: Temperature standard deviation
- **measurement_count**: Number of measurements
- **period_start**: Start of measurement period
- **period_end**: End of measurement period
- **source**: Data source ('station')

### Interpolated Data Output
When interpolation is enabled:
- **Geometry**: Grid point geometries
- **ground_temp**: Interpolated temperature (°C)
- **source**: Data source ('interpolated')
- **n_stations**: Number of stations used for interpolation
- **resolution_m**: Grid resolution in meters
- **period_start**: Start of measurement period
- **period_end**: End of measurement period

## Examples

### Downloading Data for Berlin
```python
import geopandas as gpd
from uhi_analyzer.data import DWDDataDownloader
from datetime import datetime

# Create Berlin boundary
berlin_geom = gpd.GeoDataFrame(
    [1], 
    geometry=[shapely.geometry.box(13.3, 52.4, 13.5, 52.6)], 
    crs="EPSG:4326"
)

# Download weather data
downloader = DWDDataDownloader(buffer_distance=20000)
weather_data = downloader.download_for_area(
    geometry=berlin_geom,
    start_date=datetime(2023, 7, 1),
    end_date=datetime(2023, 7, 31),
    processing_mode='uhi_analysis'
)
```

### Custom Interpolation
```python
downloader = DWDDataDownloader(
    interpolation_method="cubic",
    interpolation_resolution=100
)

# High-resolution interpolation
interpolated_data = downloader.download_for_area(
    geometry=study_area,
    start_date=start_date,
    end_date=end_date,
    interpolate=True,
    resolution=50
)
```

### Station Data Only
```python
# Get raw station data without interpolation
station_data = downloader.download_for_area(
    geometry=study_area,
    start_date=start_date,
    end_date=end_date,
    interpolate=False
)

print(f"Found {len(station_data)} weather stations")
for _, station in station_data.iterrows():
    print(f"Station {station['name']}: {station['ground_temp']:.1f}°C")
```

## Error Handling
- **No Stations**: Graceful handling when no stations are found in the area
- **Insufficient Data**: Automatic fallback to nearest neighbor interpolation
- **Network Errors**: Robust handling of DWD API failures
- **Invalid Geometry**: Validation of input geometry formats
- **CRS Issues**: Automatic coordinate system transformations

## Notes
- Uses the `wetterdienst` library for DWD data access
- Supports hourly temperature data from DWD weather stations
- Automatic CRS handling for metric calculations
- Includes NaN value handling with nearest neighbor fallback
- Provides detailed station statistics and measurement counts
- Supports multiple interpolation methods for different use cases 