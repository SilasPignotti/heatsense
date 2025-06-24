# DWDDataDownloader – DWD Weather Data Downloader

## Overview

The `DWDDataDownloader` is a specialized service for downloading and interpolating weather data (particularly temperature) for Berlin and surrounding areas. It uses the DWD API through the wetterdienst package and provides advanced features such as spatial interpolation and time period-specific data queries.

## Features

- **Time period-specific data queries**: Retrieval of weather data for specific time periods
- **Spatial interpolation**: Interpolation of station data onto regular grids
- **Geometry-based queries**: Support for points, polygons, and multipolygons
- **Configurable parameters**: Buffer distance, interpolation method, resolution
- **Robust error handling**: Comprehensive logging and error handling
- **CRS management**: Automatic coordinate system transformations

## Installation

```bash
# Install dependencies
uv add wetterdienst geopandas scipy
```

## Basic Usage

```python
from uhi_analyzer.data.dwd_downloader import DWDDataDownloader
from datetime import datetime

# Initialize service
service = DWDDataDownloader(
    buffer_distance=5000, 
    interpolation_method="linear"
)

# Get data for specific time period
start_date = datetime(2024, 6, 15, 14, 0, 0)  # June 15, 2024, 14:00
end_date = datetime(2024, 6, 15, 16, 0, 0)    # June 15, 2024, 16:00

weather_data = service.get_weather_data(
    geometry="path/to/berlin.geojson",
    start_date=start_date,
    end_date=end_date,
    interpolate=True,
    resolution=1000
)
```

## Configuration

### Environment Variables

```bash
# Buffer around geometry in meters
export DWD_BUFFER_DISTANCE=5000

# Resolution for interpolation in meters
export DWD_INTERPOLATION_RESOLUTION=1000

# Interpolation method
export DWD_INTERPOLATION_METHOD="linear"

# Default interpolation enabled
export DWD_INTERPOLATE_BY_DEFAULT=true
```

### Parameters

- `buffer_distance`: Buffer around geometry in meters (default: 5000)
- `interpolation_method`: Interpolation method ("linear", "nearest", "cubic")
- `interpolate_by_default`: Whether to interpolate data by default
- `interpolation_resolution`: Resolution of interpolation grid in meters

## Advanced Usage

### Different Geometries

```python
from shapely.geometry import Point, Polygon

# Point geometry
point = Point(13.4050, 52.5200)  # Berlin-Mitte
weather_data = service.get_weather_data(
    geometry=point,
    start_date=start_date,
    end_date=end_date
)

# Polygon geometry
polygon = Polygon([(13.0, 52.0), (14.0, 52.0), (14.0, 53.0), (13.0, 53.0)])
weather_data = service.get_weather_data(
    geometry=polygon,
    start_date=start_date,
    end_date=end_date
)
```

### GeoJSON Support

```python
# GeoJSON as string
geojson_str = '{"type": "Point", "coordinates": [13.4050, 52.5200]}'
weather_data = service.get_weather_data(
    geometry=geojson_str,
    start_date=start_date,
    end_date=end_date
)

# GeoJSON as dictionary
geojson_dict = {
    "type": "Feature",
    "geometry": {
        "type": "Point",
        "coordinates": [13.4050, 52.5200]
    }
}
weather_data = service.get_weather_data(
    geometry=geojson_dict,
    start_date=start_date,
    end_date=end_date
)
```

## Output Formats

### Station Data (without interpolation)

```python
# GeoDataFrame with station data
print(weather_data.columns)
# ['station_id', 'name', 'latitude', 'longitude', 'height', 
#  'geometry', 'date', 'value', 'quality', 'parameter']
```

### Interpolated Data

```python
# GeoDataFrame with interpolated temperatures
print(weather_data.columns)
# ['geometry', 'ground_temp', 'date', 'source', 'n_stations', 
#  'resolution_m', 'target_timestamp']
```

## Logging

The service provides comprehensive logging:

```python
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)

# Use service
service = DWDDataDownloader()
# Logs show: stations found, interpolation, etc.
```

## Error Handling

```python
try:
    weather_data = service.get_weather_data(
        geometry=geometry,
        start_date=start_date,
        end_date=end_date
    )
    if weather_data.empty:
        print("No data available")
    else:
        print(f"Data successfully loaded: {len(weather_data)} points")
except Exception as e:
    print(f"Error loading data: {e}")
```

## Performance Optimization

- **Buffer distance**: Smaller buffers for faster queries
- **Interpolation resolution**: Higher resolution = more computation time
- **Time period**: Shorter periods for faster downloads
- **CRS transformations**: Efficient coordinate system handling

## Examples

### Complete Example

```python
from uhi_analyzer.data.dwd_downloader import DWDDataDownloader
from datetime import datetime
import geopandas as gpd

# Initialize service
service = DWDDataDownloader(
    buffer_distance=3000,
    interpolation_method="linear"
)

# Define time period
start_date = datetime(2024, 6, 15, 14, 0, 0)
end_date = datetime(2024, 6, 15, 16, 0, 0)

# Load geometry
geometry = gpd.read_file("data/raw/boundaries/berlin_admin_boundaries.geojson")

# Get weather data
weather_data = service.get_weather_data(
    geometry=geometry,
    start_date=start_date,
    end_date=end_date,
    interpolate=True,
    resolution=500
)

# Save results
weather_data.to_file("data/processed/weather/berlin_weather_2024-06-15_14-16h.geojson")

print(f"Weather data successfully saved: {len(weather_data)} points")
```

### Multiple Time Periods

```python
# Define multiple time periods
time_periods = [
    (datetime(2024, 6, 15, 14, 0, 0), datetime(2024, 6, 15, 16, 0, 0)),
    (datetime(2024, 6, 15, 18, 0, 0), datetime(2024, 6, 15, 20, 0, 0)),
    (datetime(2024, 6, 16, 6, 0, 0), datetime(2024, 6, 16, 8, 0, 0))
]

for i, (start_date, end_date) in enumerate(time_periods):
    weather_data = service.get_weather_data(
        geometry=geometry,
        start_date=start_date,
        end_date=end_date,
        interpolate=True
    )
    
    output_file = f"data/processed/weather/berlin_weather_period_{i+1}.geojson"
    weather_data.to_file(output_file)
    print(f"Period {i+1}: {len(weather_data)} points saved to {output_file}")
```

### Temperature Analysis

```python
# Analyze temperature patterns
weather_data = service.get_weather_data(
    geometry=geometry,
    start_date=start_date,
    end_date=end_date,
    interpolate=True,
    resolution=1000
)

# Calculate statistics
print(f"Average temperature: {weather_data['ground_temp'].mean():.2f}°C")
print(f"Temperature range: {weather_data['ground_temp'].min():.2f}°C - {weather_data['ground_temp'].max():.2f}°C")
print(f"Number of stations used: {weather_data['n_stations'].iloc[0]}")
```

## Interpolation Methods

### Linear Interpolation
- **Use case**: Smooth temperature gradients
- **Advantage**: Good for continuous temperature fields
- **Requirement**: At least 3 stations

### Nearest Neighbor
- **Use case**: When few stations available
- **Advantage**: Works with minimal data
- **Requirement**: At least 1 station

### Cubic Interpolation
- **Use case**: High-resolution temperature mapping
- **Advantage**: Smooth, detailed results
- **Requirement**: At least 4 stations

## Coordinate Systems

The service automatically handles coordinate system transformations:

- **Input**: WGS84 (EPSG:4326) for geometry
- **Processing**: ETRS89 / UTM zone 33N (EPSG:25833) for calculations
- **Output**: WGS84 (EPSG:4326) for results

## Troubleshooting

### Common Issues

1. **No stations found**: Increase buffer distance
2. **Interpolation fails**: Check if enough stations are available
3. **CRS errors**: Ensure input geometry is in WGS84

### Debug Mode

```python
import logging

# Enable debug logging
logging.getLogger("uhi_analyzer.data.dwd_downloader").setLevel(logging.DEBUG)

# Use service
service = DWDDataDownloader()
# Detailed logs will be output
```

---

**Author:** Urban Heat Island Analyzer Team 