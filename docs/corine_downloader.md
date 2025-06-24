# CorineDataDownloader - Corine Land Cover Data Downloader

## Overview

The `CorineDataDownloader` is a specialized downloader for Corine Land Cover data from the European Environment Agency (EEA). The system automatically selects the best available Corine year for a given analysis period and provides UHI-optimized data with land use classifications and impervious surface coefficients.

## Supported Years

- **1990**: Historical data
- **2000**: Millennium update
- **2006**: First 6-year update
- **2012**: Second 6-year update
- **2018**: Latest available data

## Installation

```bash
# Install dependencies
uv add geopandas requests pyproj
```

## Basic Usage

```python
from uhi_analyzer.data.corine_downloader import CorineDataDownloader
from datetime import datetime

# Analysis period (automatically selects best Corine year)
downloader = CorineDataDownloader(
    start_date="2020-01-01",
    end_date="2020-12-31"
)

# Using datetime objects
downloader = CorineDataDownloader(
    start_date=datetime(2020, 1, 1),
    end_date=datetime(2020, 12, 31)
)

# Using years only
downloader = CorineDataDownloader(
    start_date=2020,
    end_date=2020
)
```

## Command Line

```bash
# Analysis period (automatically selects best Corine year)
uv run scripts/data_processing/download_corine_landcover.py --start-date 2020-01-01 --end-date 2020-12-31

# Using years only
uv run scripts/data_processing/download_corine_landcover.py --start-date 2020 --end-date 2020
```

## Configuration

### Environment Variables

```bash
# HTTP request timeout
export CORINE_TIMEOUT=30

# Default output format
export CORINE_OUTPUT_FORMAT="json"

# Default CRS
export CORINE_OUTPUT_CRS="EPSG:4326"
```

### Parameters

- `start_date`: Start date of analysis period (YYYY, YYYY-MM-DD, or datetime)
- `end_date`: End date of analysis period (YYYY, YYYY-MM-DD, or datetime)
- `logger`: Logger instance (optional)

## Advanced Usage

### Download for Specific Area

```python
from pathlib import Path

# Initialize downloader
downloader = CorineDataDownloader(
    start_date="2020-01-01",
    end_date="2020-12-31"
)

# GeoJSON file of the area
geojson_path = Path("data/raw/boundaries/berlin_admin_boundaries.geojson")

# Download and save data
output_path = downloader.download_and_save(
    geojson_path=geojson_path,
    output_path="data/raw/landcover/berlin_corine_2018.geojson"
)

print(f"Data saved: {output_path}")
```

### Download Only (without saving)

```python
# Download raw data
features = downloader.download_for_area(geojson_path)
print(f"Features downloaded: {len(features)}")
```

### Extract Bounding Box

```python
# Extract bounding box from GeoJSON
bbox = downloader.get_bbox_from_geojson(geojson_path)
print(f"Bounding Box: {bbox}")
```

## Output Formats

### GeoJSON File

The downloaded data is saved as GeoJSON with UHI-optimized properties:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[13.0, 52.0], [14.0, 52.0], [14.0, 53.0], [13.0, 53.0], [13.0, 52.0]]]
      },
      "properties": {
        "OBJECTID": 1,
        "CODE_18": "111",
        "LABEL3": "Continuous urban fabric",
        "landuse_type": "urban_fabric",
        "impervious_area": 0.9
      }
    }
  ]
}
```

### GeoDataFrame

```python
import geopandas as gpd

# Load GeoJSON
gdf = gpd.read_file("data/raw/landcover/berlin_corine_2018.geojson")

# Show properties
print(gdf.columns)
# ['OBJECTID', 'CODE_18', 'LABEL3', 'landuse_type', 'impervious_area', 'geometry']

# Count land use classes
print(gdf['landuse_type'].value_counts())

# Calculate average impervious area
print(f"Average impervious area: {gdf['impervious_area'].mean():.2f}")
```

## Land Use Classes

Corine Land Cover uses a hierarchical classification system optimized for UHI analysis:

### Level 1 (5 Main Categories)
1. **Artificial surfaces** (1xx)
2. **Agricultural areas** (2xx)
3. **Forest and seminatural areas** (3xx)
4. **Wetlands** (4xx)
5. **Water bodies** (5xx)

### UHI-Optimized Categories
- **urban_fabric**: Continuous and discontinuous urban fabric
- **industrial_commercial**: Industrial or commercial units
- **transport**: Road and rail networks, ports, airports
- **artificial_non_urban**: Mineral extraction, dump sites, construction
- **green_urban**: Green urban areas, sport and leisure facilities
- **agricultural**: Arable land, permanent crops, pastures
- **forest**: Broad-leaved, coniferous, and mixed forest
- **natural_vegetation**: Natural grasslands, moors, heathland
- **wetlands**: Inland and coastal wetlands
- **water**: Water bodies

## Error Handling

```python
try:
    downloader = CorineDataDownloader(
        start_date="2020-01-01",
        end_date="2020-12-31"
    )
    output_path = downloader.download_and_save(geojson_path)
    print(f"Download successful: {output_path}")
except Exception as e:
    print(f"Download error: {e}")
```

## Logging

The downloader provides comprehensive logging:

```python
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)

# Use downloader
downloader = CorineDataDownloader(
    start_date="2020-01-01",
    end_date="2020-12-31"
)
# Logs show: year selection, download progress, etc.
```

## Performance Optimization

- **Pagination**: Automatic handling of large datasets
- **Clipping**: Exact boundary clipping to target area
- **Caching**: Avoidance of duplicate downloads
- **CRS Transformation**: Efficient coordinate system handling

## Examples

### Complete Example

```python
from uhi_analyzer.data.corine_downloader import CorineDataDownloader
from pathlib import Path
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize downloader
downloader = CorineDataDownloader(
    start_date="2020-01-01",
    end_date="2020-12-31",
    logger=logger
)

# Define paths
input_path = Path("data/raw/boundaries/berlin_admin_boundaries.geojson")
output_path = Path("data/raw/landcover/berlin_corine_2018.geojson")

# Download data
try:
    result_path = downloader.download_and_save(
        geojson_path=input_path,
        output_path=output_path
    )
    print(f"Corine data successfully downloaded: {result_path}")
except Exception as e:
    print(f"Download error: {e}")
```

### Multiple Periods Comparison

```python
periods = [
    ("2000-01-01", "2000-12-31"),
    ("2006-01-01", "2006-12-31"),
    ("2012-01-01", "2012-12-31"),
    ("2018-01-01", "2018-12-31")
]

for start_date, end_date in periods:
    downloader = CorineDataDownloader(
        start_date=start_date,
        end_date=end_date
    )
    output_path = f"data/raw/landcover/berlin_corine_{downloader.selected_year}.geojson"
    
    result_path = downloader.download_and_save(
        geojson_path="data/raw/boundaries/berlin_admin_boundaries.geojson",
        output_path=output_path
    )
    print(f"Period {start_date}-{end_date} (Corine {downloader.selected_year}): {result_path}")
```

## Testing

```bash
# Run integration tests
uv run pytest tests/integration/test_corine_years.py

# Run specific test
uv run python tests/integration/test_corine_years.py
```

## UHI Analysis Features

The downloader is specifically optimized for Urban Heat Island analysis:

### Impervious Surface Coefficients
- **0.0-0.1**: Natural areas (forest, water, wetlands)
- **0.1-0.3**: Agricultural areas
- **0.3-0.7**: Discontinuous urban fabric
- **0.7-1.0**: Continuous urban fabric, industrial areas

### Land Use Classification
- Simplified categories for UHI modeling
- Consistent classification across different Corine years
- Integration with impervious surface coefficients

---

**Author:** Urban Heat Island Analyzer Team 