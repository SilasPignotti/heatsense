# UrbanHeatIslandAnalyzer

## Overview
The `UrbanHeatIslandAnalyzer` class is the core analysis engine for urban heat island (UHI) effects. It processes satellite imagery, land use data, and weather station data to provide comprehensive UHI analysis including temperature patterns, land use correlations, heat hotspots, and mitigation recommendations.

## Features
- **Satellite Data Processing**: Google Earth Engine integration for Landsat 8 Collection 2 thermal data
- **German UHI Categories**: Specialized CORINE land cover processing with German UHI categorization
- **Hotspot Identification**: Spatial clustering algorithms using Moran's I for heat island detection
- **Ground Validation**: Weather station data integration for satellite validation
- **Mitigation Recommendations**: Comprehensive strategies based on size, intensity, and land use correlations
- **Flexible Grid Resolution**: Configurable analysis grid from 50m to 300m resolution

## Usage

### Basic Usage
```python
from heatsense.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
from datetime import date

# Initialize analyzer
analyzer = UrbanHeatIslandAnalyzer(
    cloud_cover_threshold=20,
    grid_cell_size=100,
    hotspot_threshold=0.9
)

# Initialize Google Earth Engine (required)
analyzer.initialize_earth_engine()

# Run analysis
results = analyzer.analyze_heat_islands(
    city_boundary="path/to/boundary.geojson",
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    landuse_data="path/to/corine_data.geojson"
)
```

### Advanced Configuration
```python
from pathlib import Path

analyzer = UrbanHeatIslandAnalyzer(
    cloud_cover_threshold=15,      # Stricter cloud filtering
    grid_cell_size=50,            # Higher resolution (50m grid)
    hotspot_threshold=0.95,       # Higher hotspot threshold (top 5%)
    min_cluster_size=10,          # Larger minimum clusters
    use_grouped_categories=True,  # Use German UHI categories (default)
    log_file=Path("analysis.log") # Optional logging to file
)

# Initialize with specific Google Earth Engine project
analyzer.initialize_earth_engine(project="your-gee-project-id")
```

### With Weather Station Validation
```python
# Include weather station data for ground validation
results = analyzer.analyze_heat_islands(
    city_boundary=city_boundary,
    date_range=(start_date, end_date),
    landuse_data=landuse_data,
    weather_stations=weather_station_data
)
```

## Parameters

### Initialization Parameters
- `cloud_cover_threshold` (float): Maximum acceptable cloud cover percentage (0-100, default: 20)
- `grid_cell_size` (float): Analysis grid cell size in meters (default: 100)
- `hotspot_threshold` (float): Percentile threshold for hotspot identification (0-1, default: 0.9)
- `min_cluster_size` (int): Minimum number of cells for valid hotspot clusters (default: 5)
- `use_grouped_categories` (bool): Use German UHI land use categories (default: True)
- `log_file` (Path, optional): Optional path for log file
- `logger` (Logger, optional): Optional logger instance

### Analysis Parameters
- `city_boundary`: City boundary specification
  - `str`: Path to boundary file
  - `gpd.GeoDataFrame`: GeoDataFrame with boundary geometry
- `date_range` (tuple): Tuple of start and end dates for analysis
- `landuse_data`: Land use data specification
  - `str`: Path to land use file
  - `gpd.GeoDataFrame`: GeoDataFrame with land use data
- `weather_stations` (gpd.GeoDataFrame, optional): Weather station data for validation

## Methods

### `analyze_heat_islands()`
Performs comprehensive urban heat island analysis.

**Parameters**:
- `city_boundary`: City boundary specification
- `date_range` (tuple): Analysis date range
- `landuse_data`: Land use data specification
- `weather_stations` (optional): Weather station data

**Returns**: `Dict` with comprehensive analysis results

### `initialize_earth_engine()`
Initializes Google Earth Engine with authentication.

**Parameters**:
- `project` (str, optional): Earth Engine project ID

### `_calculate_temperature_stats()`
Calculates temperature statistics from satellite data.

**Parameters**:
- `collection` (ee.ImageCollection): Landsat image collection
- `boundary` (gpd.GeoDataFrame): Analysis boundary

**Returns**: `pd.DataFrame` with temperature statistics

### `_analyze_landuse_correlation()`
Analyzes correlations between land use and temperature.

**Parameters**:
- `temp_data` (gpd.GeoDataFrame): Temperature data
- `landuse` (gpd.GeoDataFrame): Land use data
- `use_grouped_categories` (bool): Use grouped categories

**Returns**: `Dict` with correlation analysis results

### `_identify_heat_hotspots()`
Identifies heat island hotspots using clustering.

**Parameters**:
- `temp_data` (gpd.GeoDataFrame): Temperature data
- `threshold` (float): Hotspot threshold
- `min_cluster_size` (int): Minimum cluster size

**Returns**: `gpd.GeoDataFrame` with hotspot data

## Analysis Phases

The analyzer performs analysis in the following phases:

1. **Data Loading**: Loads and validates input data with CRS handling
2. **Satellite Acquisition**: Filters and downloads Landsat 8 Collection 2 thermal data via Google Earth Engine
3. **Temperature Analysis**: Creates analysis grid and extracts temperature values for each cell
4. **Land Use Correlation**: Processes CORINE data with German UHI categories and calculates correlations
5. **Hotspot Identification**: Uses Moran's I spatial statistics to identify significant heat clusters
6. **Weather Enhancement**: Enhances weather station data for UHI-specific analysis (if provided)
7. **Recommendations**: Generates size-based, intensity-based, and land-use-specific mitigation strategies

## Output Structure

The analysis returns a comprehensive dictionary with:

### Metadata
- **analysis_date**: Analysis timestamp
- **study_period**: Analysis period
- **cloud_threshold**: Used cloud cover threshold
- **grid_cell_size**: Used grid cell size
- **city_area_km2**: Analysis area in square kilometers

### Temperature Statistics (GeoDataFrame)
- **geometry**: Grid cell geometries
- **temperature**: Temperature values in Celsius
- Grid cells with spatial temperature distribution

### Land Use Correlation
- **statistics**: Temperature statistics by German UHI land use categories
- **correlations**: Correlation coefficients and p-values for each category
- **category_descriptions**: German descriptions for each land use type
- **analysis_type**: "german_categories"
- **summary**: Analysis summary statistics

### Hot Spots (GeoDataFrame)
- **geometry**: Hotspot locations
- **temperature**: Hotspot temperatures
- **cluster_id**: Cluster identifiers
- Spatially clustered significant heat islands

### Mitigation Recommendations (List)
- **strategy**: Strategy name
- **description**: Detailed recommendation in German
- **priority**: Priority level (low/medium/high/critical)
- **category**: Strategy category
- **affected_areas**: Number of affected areas

## Examples

### Basic Analysis
```python
from heatsense.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
from datetime import date

analyzer = UrbanHeatIslandAnalyzer()
analyzer.initialize_earth_engine()

results = analyzer.analyze_heat_islands(
    city_boundary="berlin_boundary.geojson",
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    landuse_data="corine_2018.geojson"
)

print(f"Analysis completed:")
print(f"  Analysis area: {results['metadata']['city_area_km2']:.2f} km²")
print(f"  Grid cells: {len(results['temperature_statistics'])}")
print(f"  Hotspots found: {len(results['hot_spots'])}")

# Access temperature statistics
temp_stats = results['temperature_statistics']
valid_temps = temp_stats['temperature'].dropna()
print(f"  Temperature range: {valid_temps.min():.1f}°C - {valid_temps.max():.1f}°C")
```

### High-Resolution Analysis
```python
analyzer = UrbanHeatIslandAnalyzer(
    grid_cell_size=50,        # 50m resolution
    cloud_cover_threshold=10, # Very strict cloud filtering
    hotspot_threshold=0.95    # Only top 5% as hotspots
)

results = analyzer.analyze_heat_islands(
    city_boundary=city_boundary,
    date_range=(start_date, end_date),
    landuse_data=landuse_data,
    weather_stations=weather_data
)
```

### Land Use Correlation Analysis
```python
# Access land use correlation results
correlations = results['land_use_correlation']['correlations']
descriptions = results['land_use_correlation']['category_descriptions']

print("German UHI Land Use Categories:")
for landuse_type, corr_data in correlations.items():
    if isinstance(corr_data, dict) and 'correlation' in corr_data:
        description = descriptions.get(landuse_type, landuse_type)
        print(f"{description}:")
        print(f"  Correlation: r={corr_data['correlation']:.3f}")
        print(f"  Mean temp: {corr_data.get('mean_temp', 'N/A')}°C")
        print(f"  Samples: {corr_data.get('n_samples', 'N/A')}")

# Access mitigation recommendations
recommendations = results['mitigation_recommendations']
for rec in recommendations[:3]:  # Show first 3 recommendations
    print(f"\n{rec['strategy']} ({rec['priority']}):")
    print(f"  {rec['description']}")
```

## Error Handling
- **Earth Engine Issues**: Comprehensive error handling for GEE authentication and access
- **Data Quality**: Validation of input data quality and completeness
- **Cloud Cover**: Automatic handling of insufficient satellite data
- **Memory Management**: Efficient handling of large datasets
- **Network Issues**: Robust handling of API and download failures

## German UHI Categories

The analyzer uses specialized German UHI categories optimized for urban heat analysis:

- **dichte_bebauung**: Dense urban development (high heat retention)
- **wohngebiete**: Residential areas (moderate heat)
- **industrie**: Industrial areas (high heat generation)
- **verkehrsflaechen**: Transport infrastructure (very high heat)
- **staedtisches_gruen**: Urban green spaces (cooling effect)
- **landwirtschaft**: Agricultural areas (low heat)
- **wald**: Forest areas (strong cooling effect)
- **wasser**: Water bodies (strongest cooling effect)
- **natuerliche_offene_flaechen**: Natural open areas (variable heat)

## Notes
- Requires Google Earth Engine authentication and project access
- Uses Landsat 8 Collection 2 Surface Temperature (ST_B10) for thermal analysis
- Automatically handles coordinate reference system conversions
- Includes robust error handling and batch processing for large areas
- Provides detailed logging for monitoring and debugging
- Optimized for German cities with CORINE land cover integration
- Supports flexible grid resolutions from 50m to 300m 