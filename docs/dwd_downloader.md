# DWDDataDownloader - Flexible German Weather Data Downloader

## Overview

The `DWDDataDownloader` is a flexible downloader for German Weather Service (DWD) weather station data. It retrieves and processes temperature data with options for basic station data, spatial interpolation, and optional Urban Heat Island (UHI) analysis features.

## Features

### 🎯 **Core Capabilities**
- **Flexible geometry input**: Points, Polygons, GeoJSON, GeoDataFrames
- **Multiple processing modes**: Station data, interpolated grids, UHI analysis
- **Configurable spatial parameters**: Buffer distances and interpolation settings
- **Multiple output formats**: GeoJSON, GeoPackage, CSV
- **Robust error handling**: Comprehensive logging and validation

### 📊 **Data Sources**
- **DWD Hourly Temperature Data**: From German weather stations
- **Spatial Coverage**: Germany and surrounding areas
- **Temporal Resolution**: Hourly measurements
- **Quality Control**: Built-in data validation and filtering

### 💾 **Processing Modes**
- `'station_data'` - Raw station data (default, fastest)
- `'interpolated'` - Spatial interpolation on custom grids
- `'uhi_analysis'` - UHI-specific processing with additional metrics

## Installation

```bash
# Install core dependencies
uv add wetterdienst geopandas scipy pandas
```

## Basic Usage

### Simple Station Data Retrieval

```python
from uhi_analyzer.data.dwd_downloader import DWDDataDownloader
from datetime import datetime, timedelta

# Initialize downloader
downloader = DWDDataDownloader()

# Define time period (last week)
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

# Get station data for Berlin
weather_data = downloader.get_weather_data(
    geometry="path/to/berlin_boundary.geojson",
    start_date=start_date,
    end_date=end_date,
    processing_mode='station_data'
)
```

### Spatial Interpolation

```python
# Get interpolated temperature grid
weather_data = downloader.get_weather_data(
    geometry="boundary.geojson",
    start_date=start_date,
    end_date=end_date,
    processing_mode='interpolated',
    resolution=1000  # 1km grid resolution
)
```

### UHI Analysis Mode

```python
# Get data with UHI-specific metrics
weather_data = downloader.get_weather_data(
    geometry="urban_area.geojson",
    start_date=start_date,
    end_date=end_date,
    processing_mode='uhi_analysis'
)
```

## Advanced Usage

### Custom Configuration

```python
# Advanced configuration
downloader = DWDDataDownloader(
    buffer_distance=10000,  # 10km search radius
    interpolation_method='cubic',  # High-quality interpolation
    interpolation_resolution=500,  # 500m grid resolution
    interpolate_by_default=True
)
```

### Working with Different Geometries

```python
from shapely.geometry import Point, Polygon
import geopandas as gpd

# Point geometry
berlin_center = Point(13.4050, 52.5200)
weather_data = downloader.get_weather_data(
    geometry=berlin_center,
    start_date=start_date,
    end_date=end_date
)

# Polygon from coordinates
study_area = Polygon([
    (13.0, 52.0), (14.0, 52.0), 
    (14.0, 53.0), (13.0, 53.0), (13.0, 52.0)
])

# GeoDataFrame input
boundary_gdf = gpd.read_file("study_area.shp")
weather_data = downloader.get_weather_data(
    geometry=boundary_gdf,
    start_date=start_date,
    end_date=end_date
)
```

### GeoJSON Support

```python
# GeoJSON string
geojson_str = '{"type": "Point", "coordinates": [13.4050, 52.5200]}'
weather_data = downloader.get_weather_data(geometry=geojson_str, ...)

# GeoJSON dictionary
geojson_dict = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [13.4050, 52.5200]}
}
weather_data = downloader.get_weather_data(geometry=geojson_dict, ...)
```

## Processing Modes Explained

### Station Data Mode

```python
# Basic station data (fastest)
weather_data = downloader.get_weather_data(
    geometry="area.geojson",
    start_date=start_date,
    end_date=end_date,
    processing_mode='station_data'
)

# Returns station locations with averaged temperatures
print(weather_data.columns)
# ['station_id', 'name', 'latitude', 'longitude', 'ground_temp', 
#  'temp_std', 'measurement_count', 'period_start', 'period_end', 'geometry']
```

### Interpolated Mode

```python
# Spatial interpolation on regular grid
weather_data = downloader.get_weather_data(
    geometry="area.geojson",
    start_date=start_date,
    end_date=end_date,
    processing_mode='interpolated',
    resolution=1000  # 1km grid
)

# Returns grid points with interpolated temperatures
print(weather_data.columns)
# ['geometry', 'ground_temp', 'source', 'n_stations', 
#  'resolution_m', 'period_start', 'period_end']
```

### UHI Analysis Mode

```python
# UHI-specific analysis
weather_data = downloader.get_weather_data(
    geometry="urban_area.geojson",
    start_date=start_date,
    end_date=end_date,
    processing_mode='uhi_analysis'
)

# Returns data with additional UHI metrics
print(weather_data.columns)
# [...basic columns..., 'temperature_category', 'heat_stress_potential', 
#  'measurement_quality', 'grid_id']
```

## UHI Analysis Features

When using `processing_mode='uhi_analysis'`, additional columns are added:

### Temperature Classifications

```python
# Temperature categories for UHI analysis
temperature_categories = {
    'very_cold': '< 0°C',
    'cold': '0-10°C', 
    'moderate': '10-20°C',
    'warm': '20-30°C',
    'hot': '> 30°C'
}

# Heat stress potential
heat_stress_levels = {
    'low': '< 15°C',
    'moderate': '15-25°C',
    'high': '25-30°C',
    'very_high': '30-35°C',
    'extreme': '> 35°C'
}
```

### Data Quality Indicators

```python
# Measurement quality based on station data
quality_levels = {
    'high': '≥100 measurements, σ ≤ 5°C',
    'medium': '≥50 measurements, σ ≤ 8°C', 
    'low': 'Below medium thresholds'
}
```

## Output and File Formats

### Download and Save Data

```python
# Save as different formats
path_geojson = downloader.download_and_save(
    geometry="area.geojson",
    start_date=start_date,
    end_date=end_date,
    output_format='geojson'
)

path_gpkg = downloader.download_and_save(
    geometry="area.geojson",
    start_date=start_date,
    end_date=end_date,
    output_format='gpkg'
)

# CSV format (includes lat/lon columns)
path_csv = downloader.download_and_save(
    geometry="area.geojson",
    start_date=start_date,
    end_date=end_date,
    output_format='csv'
)
```

### Auto-Generated File Names

```python
# Files are automatically named with date and processing mode
# Examples:
# dwd_weather_20240615_20240622.geojson
# dwd_weather_20240615_20240622_interpolated.gpkg
# dwd_weather_20240615_20240622_uhi_analysis.csv
```

## Data Analysis Examples

### Basic Temperature Analysis

```python
import matplotlib.pyplot as plt

# Load weather data
weather_data = downloader.get_weather_data(
    geometry="study_area.geojson",
    start_date=start_date,
    end_date=end_date,
    processing_mode='station_data'
)

# Temperature statistics
print(f"Temperature range: {weather_data['ground_temp'].min():.1f}°C to {weather_data['ground_temp'].max():.1f}°C")
print(f"Average temperature: {weather_data['ground_temp'].mean():.1f}°C")
print(f"Number of stations: {len(weather_data)}")

# Plot temperature distribution
weather_data['ground_temp'].hist(bins=20)
plt.xlabel('Temperature (°C)')
plt.ylabel('Frequency')
plt.title('Temperature Distribution')
plt.show()
```

### UHI Intensity Analysis

```python
# UHI analysis with temperature categories
uhi_data = downloader.get_weather_data(
    geometry="urban_area.geojson",
    start_date=start_date,
    end_date=end_date,
    processing_mode='uhi_analysis'
)

# Analyze heat stress distribution
heat_stress_dist = uhi_data['heat_stress_potential'].value_counts()
print("Heat stress distribution:")
print(heat_stress_dist)

# Data quality assessment
quality_dist = uhi_data['measurement_quality'].value_counts()
print("\nData quality distribution:")
print(quality_dist)
```

### Spatial Interpolation Visualization

```python
# Get interpolated data
grid_data = downloader.get_weather_data(
    geometry="region.geojson",
    start_date=start_date,
    end_date=end_date,
    processing_mode='interpolated',
    resolution=1000
)

# Plot temperature map
fig, ax = plt.subplots(figsize=(12, 8))
grid_data.plot(column='ground_temp', cmap='coolwarm', ax=ax, legend=True)
ax.set_title('Interpolated Temperature Map')
plt.show()
```

## Performance Optimization

### For Large Areas

```python
# Use larger buffer and lower resolution for speed
downloader = DWDDataDownloader(
    buffer_distance=20000,  # Large search radius
    interpolation_resolution=5000,  # Lower resolution
    interpolation_method='nearest'  # Faster method
)
```

### For High Precision

```python
# Use smaller buffer and higher resolution for precision
downloader = DWDDataDownloader(
    buffer_distance=5000,  # Focused search
    interpolation_resolution=500,  # High resolution
    interpolation_method='cubic'  # High-quality interpolation
)
```

### Memory Optimization

```python
# For very large datasets, use station_data mode
weather_data = downloader.get_weather_data(
    geometry="large_region.geojson",
    start_date=start_date,
    end_date=end_date,
    processing_mode='station_data'  # No interpolation
)
```

## Configuration Management

### Default Parameters

```python
# Check default configuration
defaults = DWDDataDownloader.get_default_parameters()
print("Default configuration:")
for key, value in defaults.items():
    print(f"  {key}: {value}")
```

### Environment Variables

```bash
# Set custom defaults via environment
export DWD_BUFFER_DISTANCE=15000
export DWD_INTERPOLATION_RESOLUTION=2000
export DWD_INTERPOLATION_METHOD="cubic"
export DWD_INTERPOLATE_BY_DEFAULT=false
```

## Error Handling and Troubleshooting

### Common Issues

```python
try:
    weather_data = downloader.get_weather_data(
        geometry="area.geojson",
        start_date=start_date,
        end_date=end_date
    )
    
    if weather_data.empty:
        print("No weather stations found in the area")
    else:
        print(f"Success: {len(weather_data)} data points")
        
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Download error: {e}")
```

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

downloader = DWDDataDownloader(logger=logger)
```

### Data Validation

```python
# Check data quality
if 'measurement_count' in weather_data.columns:
    low_quality = weather_data[weather_data['measurement_count'] < 50]
    if not low_quality.empty:
        print(f"Warning: {len(low_quality)} stations have <50 measurements")

# Check for missing data
missing_temp = weather_data[weather_data['ground_temp'].isna()]
if not missing_temp.empty:
    print(f"Warning: {len(missing_temp)} stations have no temperature data")
```

## Integration Examples

### With Corine Land Cover Data

```python
from uhi_analyzer.data.corine_downloader import CorineDataDownloader

# Get weather and land cover data for the same area
corine_downloader = CorineDataDownloader(2018)
landcover_data = corine_downloader.download_and_save(
    "study_area.geojson", 
    process_for_uhi=True
)

weather_data = downloader.get_weather_data(
    geometry="study_area.geojson",
    start_date=start_date,
    end_date=end_date,
    processing_mode='uhi_analysis'
)

# Spatial join for combined analysis
combined_data = weather_data.sjoin_nearest(landcover_data)
```

### Batch Processing

```python
# Process multiple time periods
from datetime import timedelta

time_periods = [
    (datetime(2024, 6, 1), datetime(2024, 6, 7)),   # Week 1
    (datetime(2024, 6, 8), datetime(2024, 6, 14)),  # Week 2
    (datetime(2024, 6, 15), datetime(2024, 6, 21)), # Week 3
]

for i, (start, end) in enumerate(time_periods):
    weather_data = downloader.download_and_save(
        geometry="area.geojson",
        start_date=start,
        end_date=end,
        output_path=f"weather_week_{i+1}.geojson",
        processing_mode='interpolated'
    )
    print(f"Week {i+1} processed: {weather_data}")
```

## Command Line Usage

```bash
# Test the functionality
uv run scripts/data_processing/test_optimized_dwd.py
```

## Technical Details

### Coordinate Systems

The downloader automatically handles coordinate system transformations:
- **Input**: WGS84 (EPSG:4326) for lat/lon coordinates
- **Processing**: UTM Zone 33N (EPSG:25833) for metric calculations
- **Output**: WGS84 (EPSG:4326) for compatibility

### Interpolation Methods

```python
interpolation_methods = {
    'linear': 'Linear interpolation (default, good balance)',
    'nearest': 'Nearest neighbor (fastest, less smooth)',
    'cubic': 'Cubic interpolation (slowest, smoothest)'
}
```

### Buffer Strategy

Buffers are applied to ensure adequate station coverage:
- **Small areas**: 5km buffer (default)
- **Medium areas**: 10-15km buffer
- **Large areas**: 20km+ buffer

## API Reference

### Class Methods

```python
# Main data retrieval method
get_weather_data(geometry, start_date, end_date, processing_mode='station_data')

# Download and save method
download_and_save(geometry, start_date, end_date, output_format='geojson')

# UHI processing method
process_for_uhi_analysis(weather_data)

# Static utility method
get_default_parameters()
```

### Configuration Parameters

```python
DWDDataDownloader(
    buffer_distance=5000,           # Search radius in meters
    interpolation_method='linear',   # 'linear', 'nearest', 'cubic'
    interpolate_by_default=True,    # Default interpolation setting
    interpolation_resolution=30,     # Grid resolution in meters
    logger=None                     # Custom logger instance
)
```

## Examples Repository

Complete examples are available in:
- `scripts/data_processing/test_optimized_dwd.py` - Comprehensive testing
- `scripts/analysis/analyze_heat_islands.py` - UHI analysis workflow 