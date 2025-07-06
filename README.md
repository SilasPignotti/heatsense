# Urban Heat Island Analyzer 🌡️🏙️

A modern Python tool for analyzing urban heat islands with support for Landsat satellite data, land use data, and weather stations.

## Features

- 🛰️ **Satellite Data Analysis** with Google Earth Engine (Landsat 8)
- 🗺️ **Automatic Data Download** for Berlin districts via WFS
- 🌱 **CORINE Land Use Data Integration**  
- 🌡️ **DWD Weather Data Integration** with spatial interpolation
- 📊 **Statistical Hotspot Analysis** with Moran's I
- 🚀 **Performance Modes** for different use cases
- 💾 **Intelligent Caching** for faster repeated analyses
- 🌐 **Web API Backend** for application integration
- 📈 **Detailed Visualizations** and reports

## Installation

### Prerequisites
- Python 3.11+
- Google Earth Engine Account
- UV Package Manager

### Setup

```bash
# Clone repository
git clone <repository-url>
cd urban_heat_island_analyzer

# Install dependencies
uv sync

# Authenticate Google Earth Engine
uv run earthengine authenticate

# Set environment variables
export UHI_EARTH_ENGINE_PROJECT="your-gee-project-id"
```

## Quick Start

### Simple Analysis
```python
from uhi_analyzer import FastUrbanHeatIslandAnalyzer
from datetime import date

# Initialize analyzer
analyzer = FastUrbanHeatIslandAnalyzer(performance_mode="fast")
analyzer.initialize_earth_engine()

# Run analysis
results = analyzer.analyze_heat_islands(
    city_boundary="data/boundaries/kreuzberg.geojson",
    date_range=(date(2023, 7, 1), date(2023, 7, 31)),
    landuse_data="data/landuse/corine_kreuzberg.geojson"
)
```

### Command Line Interface
```bash
# Complete analysis for Berlin district
uv run python scripts/analyze_heat_islands.py \
    --start-date 2023-07-01 \
    --end-date 2023-07-31 \
    --suburb "Kreuzberg"

# Web backend API
uv run python src/uhi_analyzer/webapp/backend/uhi_backend_api.py \
    --area "Mitte" \
    --start-date 2023-06-01 \
    --end-date 2023-08-31 \
    --performance-mode fast
```

## Architecture

### Performance Modes
- **preview**: Quick preview (300m grid, reduced quality)
- **fast**: Balanced speed/quality (200m grid) 
- **standard**: Standard quality (100m grid)
- **detailed**: Highest quality (50m grid, scientific)

### Cache System
The system uses intelligent caching for optimal performance:

```
src/uhi_analyzer/webapp/backend/cache/
├── boundaries/       # District boundaries
├── earth_engine/     # Satellite data metadata  
├── grids/           # Spatial analysis grids
├── landcover/       # Land use classification
└── temperatures/    # Calculated temperature grids
```

### Data Sources
- **Satellite Data**: Landsat 8 Collection 2 Tier 1 Level 2
- **Boundary Data**: Berlin WFS (FIS-Broker)
- **Land Use**: CORINE Land Cover (Copernicus)
- **Weather Data**: DWD Climate Data Center

## Configuration

Central configuration in `src/uhi_analyzer/config/settings.py`:

```python
# Cache configuration  
UHI_CACHE_DIR = Path(__file__).parent.parent / "webapp" / "backend" / "cache"
UHI_CACHE_MAX_AGE_DAYS = 30
UHI_CACHE_MAX_SIZE_GB = 5.0

# Performance modes
UHI_PERFORMANCE_MODES = {
    "preview": {"grid_cell_size": 300, "cloud_cover_threshold": 40},
    "fast": {"grid_cell_size": 200, "cloud_cover_threshold": 30},
    # ...
}
```

## API-Referenz

### FastUrbanHeatIslandAnalyzer
```python
analyzer = FastUrbanHeatIslandAnalyzer(
    performance_mode="fast",           # Performance mode
    cache_dir=None,                   # Auto: uses UHI_CACHE_DIR
    max_cache_age_days=30,            # Cache validity
    cloud_cover_threshold=20          # Cloud cover (%)
)
```

**TODO**: The FastUrbanHeatIslandAnalyzer logic is not yet fully implemented and documented. This will be completed in a future update.

### Web Backend
```python
from uhi_analyzer.webapp.backend import UHIAnalysisBackend

backend = UHIAnalysisBackend(cache_enabled=True)
result = backend.analyze(
    area="Kreuzberg",
    start_date="2023-07-01", 
    end_date="2023-07-31",
    performance_mode="fast"
)
```

## Project Structure

```
urban_heat_island_analyzer/
├── src/uhi_analyzer/
│   ├── config/              # Configuration
│   ├── data/               # Data analysis and download
│   ├── utils/              # Utility functions and cache
│   └── webapp/backend/     # Web API backend
│       └── cache/          # 🆕 Central cache storage
├── scripts/                # Executable scripts
├── tests/                 # Unit tests
├── docs/                  # Documentation
└── data/                  # Input/output data
```

## Testing

```bash
# Run unit tests
uv run pytest tests/

# Run single test
uv run pytest tests/test_urban_heat_island_analyzer.py -v

# With coverage
uv run pytest --cov=uhi_analyzer tests/
```

## Performance Optimization

### Cache Management
```python
# Show cache statistics
analyzer = FastUrbanHeatIslandAnalyzer()
stats = analyzer.get_cache_stats()
print(f"Cache: {stats['total_files']} files, {stats['total_size_mb']} MB")

# Clear cache types
analyzer.clear_cache('temperatures')  # Only temperature data
analyzer.clear_cache()               # Complete
```

### Best Practices
- Use **fast_cached** mode for interactive applications
- **preview** mode for quick exploration
- **detailed** mode only for final analyses
- Cache directory on SSD for best performance
- Regular cache cleanup when storage space is limited

## Troubleshooting

### Google Earth Engine Authentication
```bash
# Re-authenticate
uv run earthengine authenticate

# Use service account
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

### Cache Issues
```bash
# Re-initialize cache
rm -rf src/uhi_analyzer/webapp/backend/cache/
# Restart analyzer -> creates cache structure automatically
```

### Performance Issues
- Reduce `grid_cell_size` for larger areas
- Use `performance_mode="preview"` for tests
- Check available memory for detailed analyses

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Create pull request

## License

MIT License - see `LICENSE` file for details.

## Changelog


### v1.9.0
- 🌐 Web backend API for application integration
- 📊 Extended statistics and metadata
- 🎛️ Flexible performance modes
- 💾 Intelligent caching system

## Support

For questions or issues:
- Create issues in the GitHub repository
- Consult documentation in `docs/`  
- Use performance guides for optimization
