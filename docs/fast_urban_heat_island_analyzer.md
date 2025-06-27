# FastUrbanHeatIslandAnalyzer

## Overview

The `FastUrbanHeatIslandAnalyzer` is a performance-optimized version of the standard `UrbanHeatIslandAnalyzer` that leverages intelligent caching and parallel processing to dramatically improve analysis speed while maintaining the same interface and output quality.

## Key Performance Features

### 🚀 Intelligent Caching System
- **Earth Engine Collections**: Caches satellite data collection metadata
- **Temperature Grids**: Stores computed temperature grids for reuse
- **Boundary Data**: Caches city boundary geometries
- **Land Cover Data**: Stores land use classification data
- **Analysis Grids**: Reuses spatial analysis grids

### ⚡ Performance Optimizations
- **Parallel Processing**: Concurrent execution of analysis components
- **Batch Processing**: Efficient handling of large datasets
- **Optimized Spatial Operations**: Enhanced spatial joins and overlays
- **Memory Management**: Reduced memory footprint for large analyses

### 💾 Cache Management
- **Automatic Cleanup**: Removes expired cache files
- **Size Limits**: Prevents disk overflow with configurable limits
- **Intelligent Keys**: Ensures cache consistency across parameters
- **Manual Control**: Clear specific cache types as needed

## Usage

### Basic Usage

```python
from uhi_analyzer.data import FastUrbanHeatIslandAnalyzer
from datetime import date
from pathlib import Path

# Initialize with custom settings
analyzer = FastUrbanHeatIslandAnalyzer(
    cloud_cover_threshold=20.0,
    grid_cell_size=500,  # 500m grid
    cache_dir="cache",
    max_cache_age_days=30
)

# Initialize Earth Engine
analyzer.initialize_earth_engine()

# Run analysis (first run builds cache)
results = analyzer.analyze_heat_islands(
    city_boundary="data/boundaries/kreuzberg.geojson",
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    landuse_data="data/landuse/corine_kreuzberg.geojson",
    save_intermediate=True,
    output_dir=Path("data/processed/fast_analysis")
)

# Save results
saved_files = analyzer.save_results(
    results, 
    output_dir=Path("data/processed/fast_analysis"),
    prefix="fast_uhi_analysis"
)
```

### Cache Management

```python
# Check cache statistics
cache_stats = analyzer.get_cache_stats()
print(f"Cache: {cache_stats['total_files']} files, {cache_stats['total_size_mb']} MB")

# Clear specific cache types
analyzer.clear_cache('temperatures')  # Clear temperature grids
analyzer.clear_cache('boundaries')   # Clear boundary data
analyzer.clear_cache()              # Clear all cache
```

## Performance Comparison

| Metric | Regular Analyzer | Fast Analyzer |
|--------|-----------------|---------------|
| First Run | Baseline | ~Same speed + cache building |
| Subsequent Runs | Baseline | 5-10x faster |
| API Calls | Every run | Cached/minimal |
| Disk Usage | Minimal | Cache storage required |
| Memory Usage | Standard | Optimized |

## Configuration Parameters

### Analyzer Parameters
- `cloud_cover_threshold`: Maximum cloud cover (default: 20%)
- `grid_cell_size`: Analysis grid size in meters (default: 500m)
- `hotspot_threshold`: Temperature threshold for hotspots (default: 0.8)
- `min_cluster_size`: Minimum hotspot cluster size (default: 10)

### Cache Parameters
- `cache_dir`: Cache directory path (default: "cache")
- `max_cache_age_days`: Maximum cache age (default: 30 days)

## Cache Structure

```
cache/
├── earth_engine/     # Earth Engine collection metadata
├── boundaries/       # City boundary geometries
├── landcover/       # Land use classification data
├── grids/           # Analysis spatial grids
└── temperatures/    # Computed temperature grids
```

## When to Use

### Use FastUrbanHeatIslandAnalyzer When:
- ✅ Running multiple analyses on the same area
- ✅ Iterative development and testing
- ✅ Production workflows with consistent parameters
- ✅ Have sufficient disk space for caching
- ✅ Want faster subsequent analysis runs

### Use Regular UrbanHeatIslandAnalyzer When:
- ✅ Single analysis runs
- ✅ Frequently changing parameters
- ✅ Limited disk space
- ✅ No need for repeated analyses

## API Compatibility

The `FastUrbanHeatIslandAnalyzer` is designed to be a drop-in replacement for `UrbanHeatIslandAnalyzer`:

- ✅ Same method signatures
- ✅ Same input parameters
- ✅ Same output format
- ✅ Same error handling
- ➕ Additional caching capabilities

## Cache Validation

The cache system includes intelligent validation:

- **Expiration Check**: Removes files older than `max_cache_age_days`
- **Parameter Matching**: Ensures cached data matches analysis parameters
- **Size Management**: Automatically removes old files when size limits are reached
- **Integrity Checks**: Validates cached file formats before use

## Best Practices

### 1. Cache Directory Management
```python
# Use a dedicated cache directory
analyzer = FastUrbanHeatIslandAnalyzer(cache_dir="dedicated_cache")

# Monitor cache size regularly
stats = analyzer.get_cache_stats()
if stats['total_size_mb'] > 1000:  # 1GB
    analyzer.clear_cache('temperatures')  # Clear largest cache type
```

### 2. Parameter Consistency
```python
# Use consistent parameters for maximum cache benefits
consistent_params = {
    'cloud_cover_threshold': 20.0,
    'grid_cell_size': 500,
    'hotspot_threshold': 0.8
}

analyzer = FastUrbanHeatIslandAnalyzer(**consistent_params)
```

### 3. Batch Analysis
```python
# Analyze multiple time periods efficiently
time_periods = [
    (date(2023, 6, 1), date(2023, 6, 30)),
    (date(2023, 7, 1), date(2023, 7, 31)),
    (date(2023, 8, 1), date(2023, 8, 31))
]

for start_date, end_date in time_periods:
    results = analyzer.analyze_heat_islands(
        city_boundary=boundary_path,
        date_range=(start_date, end_date),
        landuse_data=landuse_path
    )
    # Process results...
```

## Error Handling

The Fast Analyzer includes robust error handling:

- **Cache Failures**: Falls back to fresh computation
- **Earth Engine Errors**: Standard error propagation
- **Disk Space Issues**: Automatic cache cleanup
- **Corrupted Cache**: Automatic re-computation

## Logging

Enhanced logging provides cache performance insights:

```
🚀 Fast UHI Analyzer initialized with caching
✅ Using cached temperature grid: abc123... (1500 cells)
🚀 Using cached boundary data: kreuzberg
⚡ Cache hit rate: 85% - significant time saved!
```

## Migration Guide

### From Regular Analyzer
```python
# Before
from uhi_analyzer.data import UrbanHeatIslandAnalyzer
analyzer = UrbanHeatIslandAnalyzer()

# After - just change the import!
from uhi_analyzer.data import FastUrbanHeatIslandAnalyzer
analyzer = FastUrbanHeatIslandAnalyzer()
```

All existing code remains compatible with the Fast Analyzer. 