# UrbanHeatIslandAnalyzer - Comprehensive UHI Analysis Framework

## Overview

The `UrbanHeatIslandAnalyzer` is a specialized framework for comprehensive Urban Heat Island (UHI) analysis using satellite imagery, land use data, and weather station validation. It integrates Google Earth Engine for satellite data processing with advanced spatial analysis techniques to identify, analyze, and visualize urban heat patterns.

## Key Features

### 🛰️ **Satellite Data Integration**
- **Landsat 8 Thermal Analysis**: Automated processing of thermal infrared data
- **Google Earth Engine**: Cloud-based satellite data processing
- **Cloud Filtering**: Configurable cloud cover thresholds
- **Temporal Analysis**: Multi-date and seasonal trend analysis

### 🗺️ **Advanced Spatial Analysis**
- **Grid-based Analysis**: Configurable resolution analysis grids
- **Hotspot Detection**: Statistical identification of heat islands
- **Spatial Clustering**: Connected component analysis of heat patterns
- **Land Use Correlation**: Statistical correlation with land cover types

### 📊 **Statistical Methods**
- **Moran's I Analysis**: Spatial autocorrelation testing
- **Percentile-based Hotspots**: Configurable intensity thresholds
- **Correlation Analysis**: Land use temperature relationships
- **Ground Validation**: Weather station comparison

### 🎯 **Professional Output**
- **Comprehensive Reports**: Structured analysis results
- **Mitigation Recommendations**: Science-based cooling strategies
- **Multiple File Formats**: GeoJSON, JSON for analysis results
- **High-Quality Visualizations**: Publication-ready maps and charts

## Installation and Setup

### Dependencies

```bash
# Core dependencies
uv add earthengine-api geopandas pandas numpy scipy
uv add matplotlib seaborn libpysal esda

# Earth Engine authentication
pip install earthengine-api --upgrade
earthengine authenticate
```

### Earth Engine Setup

```bash
# 1. Set up your Google Earth Engine project
cp .env.example .env
# Edit .env and set your Google Earth Engine project ID

# 2. Authenticate with Google Earth Engine
earthengine authenticate

# 3. The analyzer will use your configured project from .env
# You can also override this by providing a custom project ID when initializing
```

## Basic Usage

### Quick Start Analysis

```python
from uhi_analyzer.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
from datetime import date

# Initialize analyzer
analyzer = UrbanHeatIslandAnalyzer(
    cloud_cover_threshold=20,  # Maximum 20% cloud cover
    grid_cell_size=100,        # 100m analysis grid
    hotspot_threshold=0.9      # Top 10% temperature threshold
)

# Authenticate Earth Engine (first time only)
analyzer.initialize_earth_engine()

# Perform comprehensive UHI analysis
results = analyzer.analyze_heat_islands(
    city_boundary="data/raw/boundaries/berlin_admin_boundaries.geojson",
    date_range=(date(2022, 6, 1), date(2022, 8, 31)),  # Summer 2022
    landuse_data="data/raw/landcover/berlin_corine_landcover.geojson"
)
```

### Advanced Configuration

```python
# Custom analyzer configuration
analyzer = UrbanHeatIslandAnalyzer(
    cloud_cover_threshold=15,     # Stricter cloud filtering
    grid_cell_size=50,            # Higher resolution (50m grid)
    hotspot_threshold=0.95,       # Top 5% temperatures only
    min_cluster_size=10,          # Larger minimum cluster size
    log_file=Path("logs/uhi_analysis.log")
)

# Use custom Earth Engine project (if different from default)
analyzer.initialize_earth_engine(project="your-custom-project-id")

# Analysis with weather station validation
results = analyzer.analyze_heat_islands(
    city_boundary="berlin_boundary.geojson",
    date_range=(date(2022, 7, 1), date(2022, 7, 31)),
    landuse_data="berlin_landcover.geojson",
    weather_stations=weather_station_data,  # GeoDataFrame with temperature data
    save_intermediate=True,
    output_dir=Path("data/processed/uhi_analysis_2022")
)
```

## Analysis Components

### 1. Temperature Analysis

The analyzer extracts and processes satellite thermal data:

```python
# Temperature statistics are automatically calculated
temp_stats = results['temperature_statistics']
print(f"Mean temperature: {temp_stats['temperature'].mean():.1f}°C")
print(f"Temperature range: {temp_stats['temperature'].min():.1f}°C to {temp_stats['temperature'].max():.1f}°C")

# Temperature data includes spatial information
print(f"Grid cells analyzed: {len(temp_stats)}")
```

### 2. Land Use Correlation

Analyzes relationships between land cover and temperature:

```python
# Land use correlation results
correlation = results['land_use_correlation']

# Statistics by land use type
print("Temperature by land use type:")
for land_type, stats in correlation['statistics'].items():
    print(f"  {land_type}: {stats['temperature_mean']:.1f}°C (±{stats['temperature_std']:.1f})")

# Correlation coefficients
print("\nCorrelations with imperviousness:")
for land_type, corr_data in correlation['correlations'].items():
    if 'correlation' in corr_data:
        print(f"  {land_type}: r={corr_data['correlation']:.3f}, p={corr_data['p_value']:.3f}")
```

### 3. Heat Hotspot Detection

Identifies statistically significant heat islands:

```python
# Heat hotspots
hotspots = results['hot_spots']
print(f"Heat hotspots identified: {len(hotspots)} clusters")

if not hotspots.empty:
    print(f"Hotspot temperatures: {hotspots['temperature'].min():.1f}°C to {hotspots['temperature'].max():.1f}°C")
    
    # Cluster analysis
    clusters = hotspots['cluster_id'].value_counts()
    print(f"Largest cluster: {clusters.iloc[0]} cells")
```

### 4. Temporal Trends

Analyzes seasonal and monthly temperature patterns:

```python
# Temporal analysis (if available)
if 'temporal_trends' in results and results['temporal_trends']:
    trends = results['temporal_trends']
    print(f"Temporal analysis: {trends['n_hotspots']} hotspots across {trends['year']}")
    
    # Extract monthly data
    monthly_data = []
    for feature in trends['features']:
        props = feature['properties']
        if 'month' in props and 'mean' in props:
            monthly_data.append({
                'month': props['month'],
                'temperature': props['mean']
            })
    
    if monthly_data:
        import pandas as pd
        df = pd.DataFrame(monthly_data)
        monthly_avg = df.groupby('month')['temperature'].mean()
        print("Monthly temperature trends in hotspots:")
        for month, temp in monthly_avg.items():
            print(f"  Month {month}: {temp:.1f}°C")
```

### 5. Ground Validation

Compares satellite temperatures with weather station data:

```python
# Ground validation (if weather stations provided)
if 'ground_validation' in results:
    validation = results['ground_validation']
    
    if 'comparison_data' in validation:
        comparison = validation['comparison_data']
        print(f"Weather stations used: {len(comparison)}")
        
        if len(comparison) > 0:
            print(f"Satellite vs Ground correlation: r={validation.get('correlation', 'N/A')}")
            print(f"Mean difference: {validation.get('mean_difference', 'N/A'):.1f}°C")
```

## Saving and Exporting Results

### Save Complete Analysis

```python
# Save all results to files
saved_files = analyzer.save_results(
    results=results,
    output_dir=Path("data/processed/uhi_analysis"),
    prefix="berlin_summer_2022"
)

print("Saved files:")
for result_type, file_path in saved_files.items():
    print(f"  {result_type}: {file_path}")
```

### Individual Component Export

```python
# Save specific components
output_dir = Path("data/processed/uhi_results")
output_dir.mkdir(parents=True, exist_ok=True)

# Temperature statistics
results['temperature_statistics'].to_file(
    output_dir / "temperature_grid.geojson"
)

# Heat hotspots
if not results['hot_spots'].empty:
    results['hot_spots'].to_file(
        output_dir / "heat_hotspots.geojson"
    )

# Land use correlation (JSON)
import json
with open(output_dir / "landuse_correlation.json", 'w') as f:
    json.dump(results['land_use_correlation'], f, indent=2)
```

## Visualization

### Built-in Visualization

```python
# Create comprehensive visualization
analyzer.visualize_results(
    results=results,
    output_path="uhi_analysis_visualization.png"
)
```

### Custom Visualization

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Temperature distribution
fig, axes = plt.subplots(2, 2, figsize=(15, 12))

# 1. Temperature histogram
temp_data = results['temperature_statistics']
temp_data['temperature'].hist(bins=30, ax=axes[0, 0])
axes[0, 0].set_title('Temperature Distribution')
axes[0, 0].set_xlabel('Temperature (°C)')

# 2. Spatial temperature map
temp_data.plot(column='temperature', cmap='coolwarm', ax=axes[0, 1], legend=True)
axes[0, 1].set_title('Temperature Map')

# 3. Land use temperatures
correlation = results['land_use_correlation']
if 'statistics' in correlation:
    land_types = []
    mean_temps = []
    for land_type, stats in correlation['statistics'].items():
        land_types.append(land_type)
        mean_temps.append(stats['temperature_mean'])
    
    axes[1, 0].bar(range(len(land_types)), mean_temps)
    axes[1, 0].set_xticks(range(len(land_types)))
    axes[1, 0].set_xticklabels(land_types, rotation=45, ha='right')
    axes[1, 0].set_title('Temperature by Land Use')
    axes[1, 0].set_ylabel('Temperature (°C)')

# 4. Hotspots map
if not results['hot_spots'].empty:
    results['hot_spots'].plot(column='temperature', cmap='Reds', ax=axes[1, 1], legend=True)
    axes[1, 1].set_title('Heat Hotspots')

plt.tight_layout()
plt.savefig('custom_uhi_analysis.png', dpi=300, bbox_inches='tight')
plt.show()
```

## Configuration Parameters

### Default Parameters

```python
# Get default configuration
defaults = UrbanHeatIslandAnalyzer.get_default_parameters()
print("Default parameters:")
for category, params in defaults.items():
    if isinstance(params, dict):
        print(f"\n{category}:")
        for key, value in params.items():
            print(f"  {key}: {value}")
    else:
        print(f"{category}: {params}")

# Example output:
# earth_engine_project: your-gee-project-id
# cloud_cover_threshold: 20
# grid_cell_size: 100
# ...
```

### Key Configuration Options

```python
# Earth Engine configuration
earth_engine_project = "your-gee-project-id"  # GEE project ID

# Temperature analysis
cloud_cover_threshold = 20      # Maximum cloud cover (%)
grid_cell_size = 100            # Analysis resolution (meters)

# Hotspot detection  
hotspot_threshold = 0.9         # Temperature percentile threshold
min_cluster_size = 5            # Minimum cells per cluster

# Statistical analysis
moran_significance = 0.05       # Spatial autocorrelation significance
correlation_threshold = 0.5     # Land use correlation threshold

# Visualization
visualization_dpi = 300         # Output image quality
figsize = (15, 15)             # Figure dimensions
colormap = "hot"               # Temperature color scheme
```

## Data Requirements

### Input Data Formats

#### City Boundary
```python
# Required columns: geometry
# Supported formats: GeoJSON, Shapefile, GeoPackage
city_boundary = "berlin_boundary.geojson"
```

#### Land Use Data
```python
# Required columns: geometry, landuse_type OR CODE_18 (CORINE)
# Optional: impervious_area
# Supported formats: GeoJSON, Shapefile, GeoPackage
landuse_data = "berlin_landcover.geojson"
```

#### Weather Stations (Optional)
```python
# Required columns: geometry, temperature (or similar)
# Format: GeoDataFrame
import geopandas as gpd
weather_stations = gpd.read_file("weather_stations.geojson")
```

### Data Coordinate Systems

The analyzer automatically handles coordinate system transformations:
- **Input**: Any standard CRS (typically WGS84)
- **Processing**: Web Mercator for spatial operations
- **Output**: WGS84 for compatibility

## Performance Optimization

### Large Study Areas

```python
# For cities >500 km², optimize grid resolution
analyzer = UrbanHeatIslandAnalyzer(
    grid_cell_size=200,          # Larger cells for faster processing
    cloud_cover_threshold=30     # More lenient cloud filtering
)
```

### High-Resolution Analysis

```python
# For detailed analysis of smaller areas
analyzer = UrbanHeatIslandAnalyzer(
    grid_cell_size=50,           # Higher resolution
    cloud_cover_threshold=10,    # Stricter quality control
    min_cluster_size=20          # Larger minimum clusters
)
```

### Memory Management

```python
# For memory-constrained environments
results = analyzer.analyze_heat_islands(
    city_boundary="boundary.geojson",
    date_range=(date(2022, 7, 1), date(2022, 7, 7)),  # Shorter time period
    landuse_data="landcover.geojson",
    save_intermediate=True,       # Save intermediate results
    output_dir=Path("temp_results")  # Reduce memory usage
)
```

## Troubleshooting

### Common Issues

#### Earth Engine Authentication
```python
# If authentication fails
import ee
ee.Authenticate()  # Follow the authentication flow

# The analyzer uses the project ID from your .env file by default
# Or specify a custom project:
analyzer.initialize_earth_engine(project="your-custom-project-id")
```

#### No Temperature Data
```python
# Check cloud cover and date range
analyzer = UrbanHeatIslandAnalyzer(cloud_cover_threshold=50)  # More lenient
# Or try different date range
date_range = (date(2022, 6, 1), date(2022, 9, 30))  # Longer period
```

#### Large Processing Times
```python
# Reduce grid resolution or study area
analyzer = UrbanHeatIslandAnalyzer(grid_cell_size=200)  # Larger cells
# Or process smaller time periods
```

### Error Handling

```python
try:
    results = analyzer.analyze_heat_islands(
        city_boundary="boundary.geojson",
        date_range=(date(2022, 7, 1), date(2022, 7, 31)),
        landuse_data="landcover.geojson"
    )
except RuntimeError as e:
    print(f"Earth Engine error: {e}")
    # Check authentication and project setup
except ValueError as e:
    print(f"Data error: {e}")
    # Check input data format and content
except Exception as e:
    print(f"Unexpected error: {e}")
    # Check logs for detailed error information
```

### Logging and Debugging

```python
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

# Or save logs to file
analyzer = UrbanHeatIslandAnalyzer(
    log_file=Path("logs/uhi_debug.log")
)
```

## Analysis Workflow Examples

### Complete City Analysis

```python
from pathlib import Path
from datetime import date

# Setup
analyzer = UrbanHeatIslandAnalyzer(
    cloud_cover_threshold=20,
    grid_cell_size=100,
    log_file=Path("logs/berlin_uhi_analysis.log")
)

# Initialize Earth Engine
analyzer.initialize_earth_engine()

# Comprehensive analysis
results = analyzer.analyze_heat_islands(
    city_boundary="data/raw/boundaries/berlin_admin_boundaries.geojson",
    date_range=(date(2022, 6, 1), date(2022, 8, 31)),
    landuse_data="data/raw/landcover/berlin_corine_landcover.geojson",
    save_intermediate=True,
    output_dir=Path("data/processed/berlin_uhi_2022")
)

# Save results
saved_files = analyzer.save_results(
    results=results,
    output_dir=Path("data/processed/berlin_uhi_2022"),
    prefix="berlin_summer_2022"
)

# Create visualization
analyzer.visualize_results(
    results=results,
    output_path="data/processed/berlin_uhi_2022/berlin_uhi_analysis.png"
)

print("Analysis completed successfully!")
print(f"Files saved: {list(saved_files.keys())}")
```

### Seasonal Comparison

```python
# Analyze multiple seasons
seasons = {
    'spring': (date(2022, 3, 1), date(2022, 5, 31)),
    'summer': (date(2022, 6, 1), date(2022, 8, 31)),
    'autumn': (date(2022, 9, 1), date(2022, 11, 30))
}

seasonal_results = {}
for season_name, date_range in seasons.items():
    print(f"Analyzing {season_name}...")
    
    results = analyzer.analyze_heat_islands(
        city_boundary="berlin_boundary.geojson",
        date_range=date_range,
        landuse_data="berlin_landcover.geojson"
    )
    
    seasonal_results[season_name] = results
    
    # Save season-specific results
    analyzer.save_results(
        results=results,
        output_dir=Path(f"data/processed/berlin_{season_name}_2022"),
        prefix=f"berlin_{season_name}_2022"
    )

# Compare seasonal results
for season, results in seasonal_results.items():
    temp_stats = results['temperature_statistics']
    if not temp_stats.empty:
        mean_temp = temp_stats['temperature'].mean()
        print(f"{season}: {mean_temp:.1f}°C average")
```

## Integration with Other Components

### With Corine Land Cover Downloader

```python
from uhi_analyzer.data.corine_downloader import CorineDataDownloader

# Download land cover data
corine_downloader = CorineDataDownloader(year=2018)
landcover_path = corine_downloader.download_and_save(
    geometry="berlin_boundary.geojson",
    output_path="data/raw/landcover/berlin_corine_2018.geojson",
    process_for_uhi=True  # Add UHI-specific processing
)

# Use in UHI analysis
results = analyzer.analyze_heat_islands(
    city_boundary="berlin_boundary.geojson",
    date_range=(date(2022, 7, 1), date(2022, 7, 31)),
    landuse_data=landcover_path
)
```

### With DWD Weather Data

```python
from uhi_analyzer.data.dwd_downloader import DWDDataDownloader
from datetime import datetime

# Download weather station data
dwd_downloader = DWDDataDownloader()
weather_data = dwd_downloader.get_weather_data(
    geometry="berlin_boundary.geojson",
    start_date=datetime(2022, 7, 1),
    end_date=datetime(2022, 7, 31),
    processing_mode='station_data'
)

# Use for ground validation
results = analyzer.analyze_heat_islands(
    city_boundary="berlin_boundary.geojson",
    date_range=(date(2022, 7, 1), date(2022, 7, 31)),
    landuse_data="berlin_landcover.geojson",
    weather_stations=weather_data  # Ground validation
)
```

## Mitigation Recommendations

The analyzer automatically generates science-based recommendations:

```python
# Access recommendations
recommendations = results['mitigation_recommendations']

print("UHI Mitigation Recommendations:")
for i, rec in enumerate(recommendations, 1):
    print(f"\n{i}. {rec['strategy']}")
    print(f"   Priority: {rec['priority']}")
    print(f"   Description: {rec['description']}")
    if 'implementation' in rec:
        print(f"   Implementation: {rec['implementation']}")
```

Example recommendations include:
- **Green Infrastructure**: Parks and green corridors
- **Cool Roofs**: Reflective roofing materials  
- **Urban Forestry**: Strategic tree planting
- **Water Features**: Fountains and water bodies
- **Sustainable Transport**: Reduced heat from vehicles

## References and Further Reading

### Scientific Background
- Voogt, J.A. & Oke, T.R. (2003). Thermal remote sensing of urban climates. Remote Sensing of Environment, 86(3), 370-384.
- Stewart, I.D. & Oke, T.R. (2012). Local climate zones for urban temperature studies. Bulletin of the American Meteorological Society, 93(12), 1879-1900.

### Technical Documentation
- [Google Earth Engine Documentation](https://developers.google.com/earth-engine)
- [Landsat 8 Data Users Handbook](https://www.usgs.gov/landsat-missions/landsat-8-data-users-handbook)
- [PySAL Spatial Analysis Library](https://pysal.org/)

### Example Publications
The UHI Analyzer has been designed based on methods from peer-reviewed urban climate research and can support analysis for academic publications, city planning, and environmental assessment reports. 