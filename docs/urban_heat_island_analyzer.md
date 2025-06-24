# UrbanHeatIslandAnalyzer - Urban Heat Island Analysis Tool

## Overview

The `UrbanHeatIslandAnalyzer` is a comprehensive tool for analyzing urban heat island effects using satellite imagery, land use data, and ground weather station measurements. It integrates multiple data sources to provide detailed spatial and temporal analysis of urban heat patterns.

## Features

- **Satellite Data Integration**: Uses Landsat thermal imagery for surface temperature mapping
- **Land Use Correlation**: Analyzes relationships between land use types and temperature patterns
- **Hotspot Detection**: Identifies statistically significant heat island clusters
- **Temporal Analysis**: Tracks temperature trends over time
- **Ground Validation**: Validates satellite data with weather station measurements
- **Spatial Statistics**: Uses spatial autocorrelation and clustering analysis
- **Visualization**: Creates comprehensive visualizations of analysis results
- **Mitigation Recommendations**: Generates actionable recommendations based on findings

## Installation

```bash
# Install dependencies
uv add earthengine-api geopandas pandas numpy libpysal esda matplotlib seaborn scipy
```

## Basic Usage

```python
from uhi_analyzer.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
from datetime import date

# Initialize analyzer
analyzer = UrbanHeatIslandAnalyzer(cloud_cover_threshold=20)

# Analyze heat islands
results = analyzer.analyze_heat_islands(
    city_boundary="data/raw/boundaries/berlin_admin_boundaries.geojson",
    date_range=(date(2022, 6, 1), date(2022, 8, 31)),
    landuse_data="data/raw/landcover/berlin_corine_2018.geojson",
    weather_stations="data/processed/weather/berlin_weather_stations.geojson"
)

# Visualize results
analyzer.visualize_results(results, "output/uhi_analysis_results.png")
```

## Configuration

### Environment Variables

```bash
# Cloud cover threshold for satellite imagery
export UHI_CLOUD_COVER_THRESHOLD=20

# Landsat collection to use
export UHI_LANDSAT_COLLECTION="LANDSAT/LC08/C02/T1_L2"

# Temperature band name
export UHI_TEMPERATURE_BAND="ST_B10"

# Analysis parameters
export UHI_GRID_CELL_SIZE=1000
export UHI_HOTSPOT_THRESHOLD=0.9
export UHI_MIN_CLUSTER_SIZE=5
```

### Parameters

- `cloud_cover_threshold`: Maximum acceptable cloud cover percentage (0-100)
- `log_file`: Optional path for log file

## Advanced Usage

### Custom Analysis Grid

```python
# Initialize with custom parameters
analyzer = UrbanHeatIslandAnalyzer(
    cloud_cover_threshold=15,
    log_file="logs/uhi_analysis.log"
)

# Initialize Earth Engine (required for satellite data)
analyzer.initialize_earth_engine()

# Perform analysis with custom date range
results = analyzer.analyze_heat_islands(
    city_boundary=city_gdf,  # GeoDataFrame
    date_range=(date(2022, 7, 1), date(2022, 7, 31)),  # Summer period
    landuse_data=landuse_gdf,  # GeoDataFrame
    weather_stations=weather_gdf  # Optional validation data
)
```

### Data Input Formats

```python
# City boundary can be file path or GeoDataFrame
city_boundary = "data/raw/boundaries/berlin.geojson"
# or
city_boundary = gpd.read_file("data/raw/boundaries/berlin.geojson")

# Land use data with required columns
landuse_data = gpd.read_file("data/raw/landcover/corine_data.geojson")
# Must contain: 'landuse_type', 'impervious_area', 'geometry'

# Weather station data for validation
weather_stations = gpd.read_file("data/processed/weather/stations.geojson")
# Must contain: 'ground_temp', 'geometry'
```

## Analysis Components

### Temperature Statistics

The analyzer calculates comprehensive temperature statistics:

```python
# Access temperature statistics
temp_stats = results['temperature_statistics']
print(f"Average temperature: {temp_stats['temperature'].mean():.2f}°C")
print(f"Temperature range: {temp_stats['temperature'].min():.2f}°C - {temp_stats['temperature'].max():.2f}°C")
print(f"Standard deviation: {temp_stats['temperature'].std():.2f}°C")
```

### Land Use Correlation Analysis

Analyzes relationships between land use and temperature:

```python
# Access land use correlation results
landuse_corr = results['land_use_correlation']

# Statistics by land use type
stats = landuse_corr['statistics']
for landuse_type, data in stats.items():
    print(f"{landuse_type}: {data['temperature']['mean']:.2f}°C")

# Correlation coefficients
correlations = landuse_corr['correlations']
for landuse_type, corr_data in correlations.items():
    print(f"{landuse_type}: r={corr_data['correlation']:.3f}, p={corr_data['p_value']:.3f}")
```

### Hotspot Detection

Identifies statistically significant heat island clusters:

```python
# Access hotspot results
hotspots = results['hot_spots']
print(f"Found {len(hotspots)} heat island hotspots")
print(f"Number of clusters: {hotspots['cluster_id'].nunique()}")

# Analyze hotspot characteristics
for cluster_id in hotspots['cluster_id'].unique():
    cluster = hotspots[hotspots['cluster_id'] == cluster_id]
    print(f"Cluster {cluster_id}: {len(cluster)} cells, avg temp: {cluster['temperature'].mean():.2f}°C")
```

### Temporal Trends

Analyzes temperature changes over time:

```python
# Access temporal analysis results
temporal = results['temporal_trends']
if temporal:
    print(f"Temperature trend slope: {temporal['trend_slope']:.3f}°C/day")
    print(f"Number of observations: {len(temporal['dates'])}")
    
    # Plot trend
    import matplotlib.pyplot as plt
    plt.plot(temporal['dates'], temporal['temperatures'])
    plt.title('Temperature Trends Over Time')
    plt.show()
```

### Ground Validation

Validates satellite data with ground measurements:

```python
# Access validation results
validation = results['ground_validation']
print(f"RMSE: {validation['rmse']:.2f}°C")
print(f"MAE: {validation['mae']:.2f}°C")
print(f"Bias: {validation['bias']:.2f}°C")
print(f"Correlation: {validation['correlation']:.3f}")
```

## Output Structure

The analyzer returns a comprehensive dictionary with the following structure:

```python
results = {
    'temperature_statistics': gpd.GeoDataFrame,  # Grid with temperature values
    'land_use_correlation': {
        'statistics': dict,  # Temperature stats by land use type
        'correlations': dict  # Correlation coefficients
    },
    'hot_spots': gpd.GeoDataFrame,  # Identified heat island clusters
    'temporal_trends': dict,  # Time series analysis (if multiple dates)
    'ground_validation': dict,  # Validation metrics (if weather stations provided)
    'mitigation_recommendations': list  # Actionable recommendations
}
```

## Visualization

### Automatic Visualization

```python
# Create comprehensive visualization
analyzer.visualize_results(
    results=results,
    output_path="output/uhi_analysis_visualization.png"
)
```

### Custom Visualizations

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Temperature distribution
fig, axes = plt.subplots(2, 2, figsize=(15, 12))

# Temperature histogram
sns.histplot(data=results['temperature_statistics'], x='temperature', ax=axes[0,0])
axes[0,0].set_title('Temperature Distribution')

# Land use correlation
landuse_stats = pd.DataFrame(results['land_use_correlation']['statistics'])
sns.barplot(data=landuse_stats, x='landuse_type', y=('temperature', 'mean'), ax=axes[0,1])
axes[0,1].set_title('Temperature by Land Use Type')

# Hotspot map
results['hot_spots'].plot(column='temperature', cmap='Reds', ax=axes[1,0])
axes[1,0].set_title('Heat Island Hotspots')

# Temporal trends
if results['temporal_trends']:
    dates = pd.to_datetime(results['temporal_trends']['dates'])
    temps = results['temporal_trends']['temperatures']
    axes[1,1].plot(dates, temps, marker='o')
    axes[1,1].set_title('Temperature Trends Over Time')

plt.tight_layout()
plt.savefig('custom_uhi_analysis.png', dpi=300, bbox_inches='tight')
```

## Mitigation Recommendations

The analyzer generates actionable recommendations based on findings:

```python
# Access recommendations
recommendations = results['mitigation_recommendations']

for rec in recommendations:
    print(f"Type: {rec['type']}")
    print(f"Description: {rec['description']}")
    print(f"Priority: {rec['priority']}")
    if 'locations' in rec:
        print(f"Locations: {rec['locations']}")
    print("---")
```

## Error Handling

```python
try:
    # Initialize Earth Engine
    analyzer.initialize_earth_engine()
    
    # Perform analysis
    results = analyzer.analyze_heat_islands(
        city_boundary=city_boundary,
        date_range=date_range,
        landuse_data=landuse_data
    )
    
    print("Analysis completed successfully")
    
except Exception as e:
    print(f"Analysis failed: {e}")
    # Check logs for detailed error information
```

## Performance Optimization

### Cloud Cover Threshold
- **Lower threshold (10-20%)**: Better data quality, fewer scenes
- **Higher threshold (30-50%)**: More scenes, potential data quality issues

### Grid Cell Size
- **Smaller cells (100-500m)**: Higher resolution, more computation time
- **Larger cells (1000-2000m)**: Lower resolution, faster computation

### Date Range
- **Shorter periods**: Faster processing, less temporal variation
- **Longer periods**: More comprehensive analysis, longer processing time

## Troubleshooting

### Common Issues

1. **No Landsat scenes found**: 
   - Increase cloud cover threshold
   - Extend date range
   - Check area size

2. **Earth Engine authentication error**:
   - Run `earthengine authenticate` in terminal
   - Check API credentials

3. **Memory issues with large areas**:
   - Reduce grid cell size
   - Process smaller sub-areas
   - Increase system memory

4. **No hotspots detected**:
   - Lower hotspot threshold
   - Reduce minimum cluster size
   - Check temperature data quality

### Debug Mode

```python
import logging

# Enable debug logging
logging.getLogger("uhi_analyzer.data.urban_heat_island_analyzer").setLevel(logging.DEBUG)

# Use analyzer
analyzer = UrbanHeatIslandAnalyzer()
# Detailed logs will be output
```

## Examples

### Complete Analysis Pipeline

```python
from uhi_analyzer.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
from datetime import date
import geopandas as gpd

# Initialize analyzer
analyzer = UrbanHeatIslandAnalyzer(
    cloud_cover_threshold=20,
    log_file="logs/berlin_uhi_analysis.log"
)

# Load data
city_boundary = gpd.read_file("data/raw/boundaries/berlin_admin_boundaries.geojson")
landuse_data = gpd.read_file("data/raw/landcover/berlin_corine_2018.geojson")
weather_stations = gpd.read_file("data/processed/weather/berlin_weather_stations.geojson")

# Define analysis period (summer 2022)
date_range = (date(2022, 6, 1), date(2022, 8, 31))

# Perform analysis
results = analyzer.analyze_heat_islands(
    city_boundary=city_boundary,
    date_range=date_range,
    landuse_data=landuse_data,
    weather_stations=weather_stations
)

# Generate visualizations
analyzer.visualize_results(
    results=results,
    output_path="output/berlin_uhi_analysis_2022.png"
)

# Print summary
print("=== Urban Heat Island Analysis Summary ===")
print(f"Analysis period: {date_range[0]} to {date_range[1]}")
print(f"Average temperature: {results['temperature_statistics']['temperature'].mean():.2f}°C")
print(f"Hotspots identified: {len(results['hot_spots'])}")
print(f"Recommendations generated: {len(results['mitigation_recommendations'])}")
```

### Seasonal Comparison

```python
# Analyze different seasons
seasons = {
    'winter': (date(2022, 12, 1), date(2023, 2, 28)),
    'spring': (date(2022, 3, 1), date(2022, 5, 31)),
    'summer': (date(2022, 6, 1), date(2022, 8, 31)),
    'autumn': (date(2022, 9, 1), date(2022, 11, 30))
}

seasonal_results = {}

for season, date_range in seasons.items():
    print(f"Analyzing {season}...")
    
    results = analyzer.analyze_heat_islands(
        city_boundary=city_boundary,
        date_range=date_range,
        landuse_data=landuse_data
    )
    
    seasonal_results[season] = results
    
    # Save seasonal visualization
    analyzer.visualize_results(
        results=results,
        output_path=f"output/berlin_uhi_{season}_2022.png"
    )

# Compare seasonal patterns
for season, results in seasonal_results.items():
    avg_temp = results['temperature_statistics']['temperature'].mean()
    hotspot_count = len(results['hot_spots'])
    print(f"{season.capitalize()}: {avg_temp:.2f}°C, {hotspot_count} hotspots")
```

---

**Author:** Urban Heat Island Analyzer Team 