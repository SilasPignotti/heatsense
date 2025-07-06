# UHI Analysis Web Application

This web application provides an interactive interface for Urban Heat Island (UHI) analysis with a modern Flask-based frontend and comprehensive data visualization.

## Features

- **🗺️ Interactive Map**: Large-scale map visualization with temperature heatmaps and layer controls
- **📊 Real-time Statistics**: Temperature metrics, hotspot analysis, and land use correlations
- **🎛️ Input Controls**: Date range selection, area picker, and performance mode settings
- **📈 Dynamic Charts**: Temperature distribution and correlation analysis visualizations
- **🔥 Hotspot Detection**: Automated identification and mapping of urban heat islands
- **💡 Recommendations**: AI-generated mitigation strategies based on analysis results
- **📱 Responsive Design**: Modern, mobile-friendly interface with clean aesthetics

## Quick Start

### 1. Install Dependencies

All dependencies are managed via `uv` and included in `pyproject.toml`:

```bash
uv sync
```

### 2. Start the Web Application

```bash
# Start the web application
uv run src/uhi_analyzer/webapp/start_webapp.py
```

The web application will be available at: **http://127.0.0.1:8000**

The browser will open automatically, or you can manually navigate to the URL.

## Architecture

```
├── app.py                 # Flask web application
├── start_webapp.py        # Startup script
├── templates/
│   ├── base.html          # Base template with header and modals
│   └── index.html         # Main application page
├── static/
│   ├── css/
│   │   └── styles.css     # Modern CSS styling
│   └── js/
│       ├── app.js         # Main application logic
│       ├── map.js         # Map visualization (Leaflet)
│       └── charts.js      # Chart rendering (Chart.js)
├── backend/
│   └── backend_example.py # Core analysis engine
└── README.md
```

## API Endpoints

- `GET /` - Main web application interface
- `GET /api/health` - Health check and status
- `GET /api/areas` - Available analysis areas (Berlin districts)
- `GET /api/performance-modes` - Available performance modes with descriptions
- `POST /api/analyze` - Run UHI analysis with parameters
- `GET /api/progress` - Get current analysis progress

## Usage Guide

### 1. **Select Analysis Area**
Choose from 25+ Berlin districts and neighborhoods including:
- Kreuzberg, Mitte, Prenzlauer Berg
- Charlottenburg, Friedrichshain, Neukölln
- Full districts like Charlottenburg-Wilmersdorf

### 2. **Set Date Range**
- Select start and end dates for analysis
- Recommended: 1-4 weeks for optimal results
- Maximum: 365 days

### 3. **Choose Performance Mode**
- **Preview** (< 30s): Quick overview for initial insights
- **Fast** (30-60s): Recommended for most use cases
- **Standard** (1-3 min): Balanced detail and performance
- **Detailed** (3-10 min): Comprehensive analysis with weather data

### 4. **Advanced Options**
- ☑️ Include weather station data (auto-enabled for detailed mode)
- ☑️ Enable caching for faster repeated analyses

### 5. **Run Analysis**
Click "Analyse starten" to begin processing. Progress is tracked in real-time with:
- Step-by-step progress indication
- Processing time tracking
- Visual progress bar

### 6. **View Results**
**Interactive Map:**
- Temperature heatmap overlay
- Hotspot markers with click details
- Layer controls for different data types
- Zoom and pan functionality

**Statistics Dashboard:**
- Temperature statistics (mean, min, max, std)
- Hotspot count and intensity
- Land use correlation analysis
- Downloadable recommendations

**Charts:**
- Temperature distribution histogram
- Land use vs. temperature scatter plot
- Correlation trend lines

## Technical Features

### Frontend Technologies
- **Flask**: Python web framework
- **Leaflet**: Interactive maps with heatmap support
- **Chart.js**: Responsive data visualization
- **Modern CSS**: Grid layouts, animations, responsive design
- **Progressive Enhancement**: Works with JavaScript disabled

### Backend Integration
- **Seamless Integration**: Uses existing `backend_example.py` without modifications
- **Real-time Processing**: Live progress tracking and updates
- **Error Handling**: Comprehensive error reporting and recovery
- **Performance Optimization**: Multiple analysis modes for different use cases

### Map Features
- **Base Layer**: OpenStreetMap tiles
- **Heatmap Layer**: Temperature data visualization
- **Marker Layers**: Hotspots, weather stations, land use
- **Interactive Controls**: Zoom, pan, layer toggle
- **Custom Popups**: Detailed information on click

### Data Visualization
- **Temperature Heatmaps**: Color-coded temperature distribution
- **Statistical Charts**: Histogram and scatter plots
- **Real-time Updates**: Dynamic chart updates during analysis
- **Export Options**: Chart download functionality

## Development

### Environment Variables
- `UHI_WEBAPP_HOST`: Web application host (default: 127.0.0.1)
- `UHI_WEBAPP_PORT`: Web application port (default: 8000)
- `UHI_WEBAPP_DEBUG`: Debug mode (default: true)

### Customization
The application is designed for easy customization:
- **Styling**: Modify `static/css/styles.css` for appearance changes
- **Map Behavior**: Extend `static/js/map.js` for additional map features
- **Analysis Logic**: Core analysis remains in `backend/backend_example.py`
- **UI Components**: Add new components to templates

### Performance Optimization
- **Caching**: Analysis results can be cached for faster repeated requests
- **Lazy Loading**: Maps and charts load progressively
- **Responsive Design**: Optimized for desktop and mobile devices
- **Efficient Data Processing**: Streaming progress updates

## Troubleshooting

### Common Issues
1. **Dependencies**: Run `uv sync` to ensure all packages are installed
2. **Port Conflicts**: Change port using `UHI_WEBAPP_PORT` environment variable
3. **Browser Issues**: Try clearing cache or using incognito mode
4. **Analysis Errors**: Check backend logs for detailed error information

### Performance Tips
- Use "Fast" mode for initial exploration
- Limit date ranges to 1-4 weeks for optimal performance
- Enable caching for repeated analyses of the same area

## Support

For issues or questions:
1. Check the console output for error messages
2. Verify all dependencies are installed with `uv sync`
3. Review the analysis parameters for validity
4. Check the backend logs for detailed error information

The web application provides a comprehensive, user-friendly interface for urban heat island analysis with professional-grade visualizations and real-time processing capabilities. 