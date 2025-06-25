# CorineDataDownloader - Flexible Corine Land Cover Data Downloader

## Overview

The `CorineDataDownloader` is a flexible downloader for Corine Land Cover data from the European Environment Agency (EEA). It automatically selects the best available Corine year for a given analysis period and provides flexible data processing options, including optional Urban Heat Island (UHI) analysis features.

## Features

### 🎯 **Core Capabilities**
- **Flexible year/period input**: Single year, date range, or specific date
- **Multiple output formats**: GeoJSON, GPKG, Shapefile, Parquet
- **Automatic year selection**: Based on data availability
- **Optional UHI processing**: Specialized land use classifications and impervious surface coefficients

### 📊 **Supported Corine Years**
- **1990**: Historical baseline
- **2000**: Millennium update  
- **2006**: First 6-year update
- **2012**: Second 6-year update
- **2018**: Latest available data

### 💾 **Output Formats**
- `'geojson'` - GeoJSON (default, best for web applications)
- `'gpkg'` - GeoPackage (efficient for desktop GIS)
- `'shp'` - ESRI Shapefile (legacy compatibility)
- `'parquet'` - Apache Parquet (optimized for large datasets)

## Installation

```bash
# Install core dependencies
uv add geopandas requests pyproj pandas
```

## Basic Usage

### Simple Year-Based Downloads

```python
from uhi_analyzer.data.corine_downloader import CorineDataDownloader

# Single year
downloader = CorineDataDownloader(2018)

# Year as string
downloader = CorineDataDownloader("2018")

# Specific date (year extracted automatically)
downloader = CorineDataDownloader("2018-06-15")
```

### Period-Based Downloads

```python
# Date range as tuple
downloader = CorineDataDownloader((2015, 2020))

# Mixed date formats
downloader = CorineDataDownloader(("2015", "2020-12-31"))

# The system automatically selects the best available Corine year
# For period 2015-2020, it would select 2018 (newest available within range)
```

### Download and Save Data

```python
# Basic download (raw Corine data)
path = downloader.download_and_save("berlin_boundary.geojson")

# With UHI processing (adds landuse_type and impervious_area columns)
path = downloader.download_and_save(
    "berlin_boundary.geojson",
    process_for_uhi=True
)

# Different output format
path = downloader.download_and_save(
    "berlin_boundary.geojson",
    output_format='gpkg',
    process_for_uhi=True
)
```

## Advanced Usage

### Custom Configuration

```python
# Custom API parameters
downloader = CorineDataDownloader(
    year_or_period=2018,
    record_count=2000,  # More records per API request
    timeout=60          # Longer timeout for large areas
)
```

### Working with GeoDataFrames

```python
import geopandas as gpd

# Load and modify boundary
boundary = gpd.read_file("study_area.shp")
boundary_buffered = boundary.buffer(1000)  # 1km buffer

# Use GeoDataFrame directly
downloader = CorineDataDownloader(2018)
path = downloader.download_and_save(boundary_buffered)
```

### Output Format Options

```python
# Large dataset - use Parquet for efficiency
path = downloader.download_and_save(
    "large_study_area.geojson",
    output_format='parquet',
    clip_to_boundary=False  # Skip clipping for better performance
)

# GIS compatibility - use GeoPackage
path = downloader.download_and_save(
    "study_area.geojson",
    output_format='gpkg'
)

# Web applications - use GeoJSON
path = downloader.download_and_save(
    "study_area.geojson",
    output_format='geojson'
)
```

### Direct Data Processing

```python
# Download raw data without saving
features = downloader.download_for_area("boundary.geojson")

# Process to basic GeoDataFrame
gdf_basic = downloader.process_to_geodataframe(features)

# Process for UHI analysis
gdf_uhi = downloader.process_for_uhi_analysis(features)
```

## UHI-Specific Processing

When `process_for_uhi=True` is used, the downloader adds specialized columns for Urban Heat Island analysis:

### Land Use Classifications

```python
# UHI-optimized land use types
LANDUSE_CATEGORIES = {
    "urban_continuous": "High-density urban areas",
    "urban_discontinuous": "Low-density urban areas", 
    "industrial_commercial": "Industrial/commercial zones",
    "green_urban_areas": "Parks and green spaces",
    "agricultural": "Agricultural areas",
    "forest": "Forest areas",
    "water_bodies": "Water surfaces",
    # ... and more
}
```

### Impervious Surface Coefficients

```python
# Coefficient ranges from 0.0 (fully permeable) to 1.0 (fully impervious)
IMPERVIOUS_COEFFICIENTS = {
    "urban_continuous": 0.85,
    "urban_discontinuous": 0.65,
    "industrial_commercial": 0.90,
    "green_urban_areas": 0.15,
    "forest": 0.01,
    "water_bodies": 0.00,
    # ... and more
}
```

### Example UHI Output

```json
{
  "type": "Feature", 
  "geometry": {...},
  "properties": {
    "corine_code": 111,
    "landuse_type": "urban_continuous",
    "impervious_area": 0.85,
    "Shape_Area": 5000.0
  }
}
```

## Data Analysis Examples

### Basic Land Use Analysis

```python
import geopandas as gpd
import matplotlib.pyplot as plt

# Load processed data
gdf = gpd.read_file("berlin_corine_2018_uhi.geojson")

# Land use distribution
landuse_counts = gdf['landuse_type'].value_counts()
print("Land use distribution:")
print(landuse_counts)

# Average impervious area by land use
impervious_by_landuse = gdf.groupby('landuse_type')['impervious_area'].mean()
print("\nAverage impervious area by land use:")
print(impervious_by_landuse.sort_values(ascending=False))
```

### Urban Heat Island Potential

```python
# Calculate UHI potential based on impervious surfaces
gdf['uhi_potential'] = pd.cut(
    gdf['impervious_area'],
    bins=[0, 0.2, 0.5, 0.8, 1.0],
    labels=['Low', 'Medium', 'High', 'Very High']
)

# Plot UHI potential
fig, ax = plt.subplots(figsize=(12, 8))
gdf.plot(column='uhi_potential', cmap='Reds', ax=ax, legend=True)
ax.set_title('Urban Heat Island Potential')
plt.show()
```

## Utility Functions

### Available Years

```python
# Check available Corine years
available_years = CorineDataDownloader.get_available_years()
print(f"Available years: {available_years}")

# Check if specific year is available
if CorineDataDownloader.is_year_available(2018):
    print("2018 data is available")
```

### Year Selection Logic

```python
# The system automatically selects the best year:
# 1. Newest year within the specified range
# 2. If no year in range, closest to range midpoint

downloader = CorineDataDownloader((2016, 2020))
print(f"Selected year: {downloader.selected_year}")  # Would select 2018

downloader = CorineDataDownloader((2014, 2016)) 
print(f"Selected year: {downloader.selected_year}")  # Would select 2012 (closest)
```

## Error Handling

```python
try:
    downloader = CorineDataDownloader(2018)
    path = downloader.download_and_save(
        "study_area.geojson",
        process_for_uhi=True
    )
    print(f"Success: {path}")
    
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Download error: {e}")
```

## Performance Tips

### For Large Areas

```python
# Use larger record counts
downloader = CorineDataDownloader(2018, record_count=2000)

# Skip clipping for very large areas
path = downloader.download_and_save(
    "large_region.geojson",
    clip_to_boundary=False,
    output_format='parquet'  # Efficient format
)
```

### For Multiple Downloads

```python
# Reuse downloader instance
downloader = CorineDataDownloader(2018)

boundaries = ["area1.geojson", "area2.geojson", "area3.geojson"]
for boundary in boundaries:
    path = downloader.download_and_save(boundary)
    print(f"Downloaded: {path}")
```

## Command Line Usage

```bash
# Test the functionality
uv run scripts/data_processing/test_optimized_corine.py
```

## Configuration Details

### API Parameters (in settings.py)

```python
# Core Corine configuration
CORINE_YEARS = [1990, 2000, 2006, 2012, 2018]
CORINE_BASE_URLS = {
    1990: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC1990_WM/MapServer/0",
    # ... more years
}

# Default API settings
DEFAULT_RECORD_COUNT = 1000
DEFAULT_TIMEOUT = 30
DEFAULT_OUTPUT_FORMAT = "geojson"
```

### Class-Level Configuration

```python
# Output format mapping (in CorineDataDownloader)
OUTPUT_FORMATS = {
    'geojson': {'driver': 'GeoJSON', 'extension': '.geojson'},
    'gpkg': {'driver': 'GPKG', 'extension': '.gpkg'},
    'shp': {'driver': 'ESRI Shapefile', 'extension': '.shp'},
    'parquet': {'driver': 'Parquet', 'extension': '.parquet'}
}
```

## Migration from Legacy API

### Old Usage

```python
# Legacy API (still works)
downloader = CorineDataDownloader("2018-01-01", "2018-12-31")
path = downloader.download_and_save("boundary.geojson")
```

### New Recommended Usage

```python
# New API (recommended)
downloader = CorineDataDownloader(2018)
path = downloader.download_and_save(
    "boundary.geojson",
    process_for_uhi=True,  # Optional UHI processing
    output_format='gpkg'   # Flexible output formats
)
```

## Troubleshooting

### Common Issues

1. **No data returned**: Check if boundary intersects with Corine coverage area
2. **Timeout errors**: Increase timeout parameter for large areas
3. **Unknown Corine codes**: Check log warnings for unmapped land use codes
4. **Format errors**: Ensure output format is supported

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

downloader = CorineDataDownloader(2018, logger=logger)
```

## Examples Repository

Complete examples are available in:
- `scripts/data_processing/test_optimized_corine.py` - Comprehensive testing
- `scripts/analysis/analyze_heat_islands.py` - UHI analysis workflow 