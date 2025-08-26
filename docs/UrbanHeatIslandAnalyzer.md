# UrbanHeatIslandAnalyzer

## Overview
The `UrbanHeatIslandAnalyzer` class is the core analysis engine for urban heat island (UHI) effects. It processes satellite imagery, land use data, and weather station data to provide comprehensive UHI analysis including temperature patterns, land use correlations, heat hotspots, and mitigation recommendations.

## Features
- **Satellite Data Processing**: Google Earth Engine integration for Landsat thermal data
- **Land Use Correlation**: Statistical analysis of land use and temperature relationships
- **Hotspot Identification**: Advanced clustering algorithms for heat island detection
- **Temporal Analysis**: Multi-seasonal trend analysis
- **Ground Validation**: Weather station data integration for validation
- **Mitigation Recommendations**: AI-powered suggestions for heat reduction
- **Comprehensive Visualization**: Professional mapping and charting capabilities

## Usage

### Basic Usage
```python
from uhi_analyzer.data import UrbanHeatIslandAnalyzer
from datetime import date

# Initialize analyzer
analyzer = UrbanHeatIslandAnalyzer(
    cloud_cover_threshold=20,
    grid_cell_size=100,
    hotspot_threshold=0.9
)

# Run analysis
results = analyzer.analyze_heat_islands(
    city_boundary="path/to/boundary.geojson",
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    landuse_data="path/to/corine_data.geojson"
)
```

### Advanced Configuration
```python
analyzer = UrbanHeatIslandAnalyzer(
    cloud_cover_threshold=15,      # Stricter cloud filtering
    grid_cell_size=50,            # Higher resolution
    hotspot_threshold=0.95,       # Higher hotspot threshold
    min_cluster_size=10,          # Larger minimum clusters
    use_grouped_categories=True,  # Use grouped land use categories
    skip_temporal_trends=False,   # Include temporal analysis
    log_file="uhi_analysis.log"
)
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
- `use_grouped_categories` (bool): Use grouped land use categories (default: True)
- `log_file` (Path, optional): Optional path for log file
- `logger` (Logger, optional): Optional logger instance
- `skip_temporal_trends` (bool): Skip temporal trends analysis (default: False)

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

1. **Data Loading**: Loads and validates input data
2. **Satellite Acquisition**: Downloads and processes Landsat thermal data
3. **Temperature Analysis**: Extracts and analyzes temperature patterns
4. **Land Use Correlation**: Analyzes land use and temperature relationships
5. **Hotspot Identification**: Identifies and clusters heat hotspots
6. **Temporal Analysis**: Analyzes seasonal and temporal trends
7. **Ground Validation**: Validates results with weather station data
8. **Recommendations**: Generates mitigation strategies

## Output Structure

The analysis returns a comprehensive dictionary with:

### Summary Data
- **temperature_range**: Min/max temperatures
- **mean_temperature**: Average temperature
- **hotspot_count**: Number of identified hotspots
- **analysis_area**: Analysis area in square kilometers

### Temperature Data
- **grid_temperatures**: Temperature data for each grid cell
- **temperature_statistics**: Statistical summary of temperatures
- **temperature_distribution**: Temperature distribution analysis

### Hotspots
- **hotspot_locations**: Geographic locations of hotspots
- **hotspot_clusters**: Clustering information
- **hotspot_statistics**: Statistical analysis of hotspots

### Land Use Correlation
- **correlation_matrix**: Correlation coefficients
- **landuse_temperatures**: Average temperatures by land use type
- **significance_tests**: Statistical significance of correlations

### Recommendations
- **mitigation_strategies**: Suggested heat reduction strategies
- **priority_areas**: Areas prioritized for intervention
- **effectiveness_estimates**: Estimated effectiveness of strategies

## Examples

### Basic Analysis
```python
from uhi_analyzer.data import UrbanHeatIslandAnalyzer
from datetime import date

analyzer = UrbanHeatIslandAnalyzer()
results = analyzer.analyze_heat_islands(
    city_boundary="berlin_boundary.geojson",
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    landuse_data="corine_2018.geojson"
)

print(f"Analysis completed:")
print(f"  Temperature range: {results['summary']['temperature_range']}")
print(f"  Hotspots found: {results['summary']['hotspot_count']}")
print(f"  Mean temperature: {results['summary']['mean_temperature']:.1f}°C")
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
correlations = results['landuse_correlation']
for landuse_type, corr_data in correlations.items():
    print(f"{landuse_type}: r={corr_data['correlation']:.3f}, p={corr_data['p_value']:.3f}")
```

## Error Handling
- **Earth Engine Issues**: Comprehensive error handling for GEE authentication and access
- **Data Quality**: Validation of input data quality and completeness
- **Cloud Cover**: Automatic handling of insufficient satellite data
- **Memory Management**: Efficient handling of large datasets
- **Network Issues**: Robust handling of API and download failures

## Notes
- Requires Google Earth Engine authentication and project access
- Uses Landsat 8/9 thermal bands for temperature analysis
- Supports multiple coordinate reference systems
- Includes automatic data quality checks and validation
- Provides detailed logging for monitoring and debugging
- Optimized for urban areas with configurable parameters 