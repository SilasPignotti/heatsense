# HeatSense

*An AI-powered web application for analyzing urban heat islands using satellite data, land use classification, and weather measurements to identify heat hotspots and generate evidence-based recommendations for sustainable urban planning*

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-API-orange.svg)](https://earthengine.google.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

A comprehensive tool for analyzing urban heat island effects using satellite imagery, weather station data, and land use information. Built for Berlin suburb analysis.

## Features

- **🛰️ Satellite Analysis**: Landsat thermal band processing via Google Earth Engine
- **🌡️ Weather Validation**: DWD weather station data integration for ground truth validation
- **🏙️ Land Use Correlation**: CORINE land cover data correlation analysis
- **📊 Spatial Analysis**: Advanced heat island hotspot identification and clustering
- **🌐 Web Interface**: Modern Flask-based web application
- **⚡ Multiple Performance Modes**: From quick preview to detailed analysis
- **📱 Interactive Maps**: Real-time visualization with Leaflet maps

## Quick Start

### Prerequisites

- Python 3.11+
- Google Earth Engine account
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

### Installation with uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/HeatSense.git
cd HeatSense

# Install dependencies with uv
uv sync

# Set up Google Earth Engine authentication
uv run python -c "import ee; ee.Authenticate()"

# Copy environment configuration
cp .env.example .env
# Edit .env and add your Google Earth Engine project ID
```

### Alternative Installation with pip

```bash
# Clone the repository
git clone https://github.com/your-username/HeatSense.git
cd HeatSense

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package in development mode
pip install -e .

# Set up Google Earth Engine authentication
python -c "import ee; ee.Authenticate()"

# Copy environment configuration
cp .env.example .env
```

### Launch Web Application

```bash
# With uv (recommended)
uv run python run_webapp.py

# Or with pip installation
python run_webapp.py
```

Open your browser to **http://localhost:8000** 🎉

### Command Line Analysis

```bash
# Quick analysis with uv
uv run python run_analysis.py --area "Friedrichshain-Kreuzberg" --start-date 2023-07-01 --end-date 2023-07-31

# Detailed analysis with output file
uv run python run_analysis.py --area "Berlin" --start-date 2023-06-01 --end-date 2023-08-31 --mode detailed --output results.json

# With verbose logging
uv run python run_analysis.py --area "Mitte" --start-date 2023-07-15 --end-date 2023-07-20 --mode preview --verbose
```

### Programmatic Usage

```python
from src.heatsense.webapp.analysis_backend import UHIAnalysisBackend

# Initialize backend
backend = UHIAnalysisBackend()

# Run analysis
result = backend.analyze(
    area="Friedrichshain-Kreuzberg",
    start_date="2023-07-01",
    end_date="2023-07-31",
    performance_mode="standard"
)

# Access results
print(f"Mean temperature: {result['data']['summary']['temperature_overview']['mean']}°C")
print(f"Hotspots found: {result['data']['summary']['hotspots_count']}")
```

## Performance Modes

| Mode         | Speed    | Resolution | Weather Data | Use Case            |
| ------------ | -------- | ---------- | ------------ | ------------------- |
| **Preview**  | <30s     | 300m       | ❌           | Quick exploration   |
| **Fast**     | 30-60s   | 200m       | ❌           | General analysis    |
| **Standard** | 1-3 min  | 100m       | ✅           | Balanced quality    |
| **Detailed** | 3-10 min | 50m        | ✅           | Research & planning |

## Project Structure

```
HeatSense/
├── run_webapp.py          # 🎯 Launch web application
├── run_analysis.py        # 🎯 CLI analysis tool
├── pyproject.toml         # Python project configuration
├── .env.example           # Environment variables template
├── src/
│   └── heatsense/         # Main package
│       ├── config/        # Configuration files
│       ├── data/          # Data processing modules
│       ├── utils/         # Utility functions
│       └── webapp/        # Web application
├── docs/                  # Documentation
├── examples/              # Usage examples
└── temp/                  # Temporary analysis files
```

## Data Sources

- **🛰️ Satellite Data**: Landsat 8 thermal imagery (Google Earth Engine)
- **🌡️ Weather Data**: DWD (German Weather Service) station network
- **🏙️ Land Use Data**: CORINE Land Cover (European Environment Agency)
- **🗺️ Administrative Boundaries**: Berlin WFS services

## Examples

Check out the `examples/` directory:

```bash
# Run basic analysis example
uv run python examples/basic_analysis.py
```

## Documentation

Detailed documentation in the `docs/` directory:

- **[UrbanHeatIslandAnalyzer.md](docs/UrbanHeatIslandAnalyzer.md)** - Core analysis engine
- **[DWDDataDownloader.md](docs/DWDDataDownloader.md)** - Weather data integration
- **[CorineDataDownloader.md](docs/CorineDataDownloader.md)** - Land use processing
- **[WFSDataDownloader.md](docs/WFSDataDownloader.md)** - Boundary data access

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Google Earth Engine** for satellite data access
- **DWD (Deutscher Wetterdienst)** for weather station data
- **European Environment Agency** for CORINE land cover data
- **Berlin Senate** for administrative boundary data

## Issues & Support

Found a bug or need help? Please [open an issue](https://github.com/your-username/HeatSense/issues) on GitHub.

---
