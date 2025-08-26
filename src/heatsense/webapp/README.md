# HeatSense - Urban Heat Island Analyzer Web Application

🔥 **HeatSense** is a comprehensive Flask web application for analyzing urban heat islands in Berlin. It provides an intuitive interface for analyzing temperature distributions, identifying hotspots, and generating climate adaptation recommendations.

## Features

### 🎯 Core Functionality
- **Interactive Analysis**: Select areas (federal state or district level) and time periods for analysis
- **Multiple Performance Modes**: Choose between preview, fast, standard, and detailed analysis modes
- **Real-time Progress Tracking**: Monitor analysis progress with live updates
- **Comprehensive Results**: Temperature distribution, hotspots, land use correlations, and recommendations

### 🗺️ Interactive Mapping
- **Leaflet-based Maps**: Modern, responsive mapping interface
- **Temperature Visualization**: Color-coded temperature grids with detailed overlays
- **Hotspot Identification**: Visual markers for high-temperature areas
- **Weather Station Data**: Integration with German Weather Service (DWD) stations
- **Layer Controls**: Toggle different data layers on/off

### 📊 Data Visualization
- **Temperature Distribution Charts**: Histogram and statistical analysis
- **Land Use Correlation**: Visualize relationships between land use and temperature
- **Key Performance Indicators**: Dashboard with critical metrics
- **Recommendations Engine**: Actionable climate adaptation strategies

### 🎨 Modern Design
- **Responsive Layout**: Works on desktop, tablet, and mobile devices
- **Clean UI/UX**: Modern design following current best practices
- **Heat-themed Color Palette**: Visual design aligned with thermal analysis
- **Accessibility**: Proper contrast ratios and keyboard navigation

## Getting Started

### Prerequisites
- Python 3.11+
- UV package manager installed
- Internet connection for data downloads

### Installation

1. **Install Dependencies**:
   ```bash
   cd urban_heat_island_analyzer
   uv sync
   ```

2. **Set Up Environment Variables** (optional):
   ```bash
   # Create .env file if needed
   echo "SECRET_KEY=your-secret-key-here" > .env
   echo "UHI_EARTH_ENGINE_PROJECT=your-gee-project-id" >> .env
   ```

3. **Launch the Application**:
   ```bash
   uv run src/uhi_analyzer/webapp/run_webapp.py
   ```

   Or alternatively:
   ```bash
   cd src/uhi_analyzer/webapp
   uv run python app.py
   ```

4. **Open in Browser**:
   Navigate to `http://localhost:5000` in your web browser.

## Usage Guide

### Step 1: Geographic Selection
1. Choose between **Bundesland** (Federal State) or **Bezirk** (District)
2. Select your area of interest from the dropdown:
   - **Bundesland**: Berlin (state-wide analysis)
   - **Bezirk**: Individual Berlin districts (Charlottenburg-Wilmersdorf, Friedrichshain-Kreuzberg, etc.)

### Step 2: Time Period
1. Set the start date (default: 01.06.2025)
2. Set the end date (default: 30.06.2025)
3. Use the date picker for easy selection

### Step 3: Performance Mode
Choose the analysis mode based on your needs:

| Mode | Description | Duration | Resolution | Weather Data |
|------|-------------|----------|------------|--------------|
| **Preview** | Quick overview with reduced accuracy | 1-2 min | 300m grid | No |
| **Fast** | Balanced speed and quality | 3-5 min | 200m grid | No |
| **Standard** | Standard analysis with good detail | 5-10 min | 100m grid | Yes |
| **Detailed** | High-resolution with maximum detail | 10-20 min | 50m grid | Yes |

### Step 4: Start Analysis
1. Click **"Analyse starten"** to begin
2. Monitor progress with the real-time progress bar
3. Wait for completion (duration depends on selected mode)

### Step 5: Explore Results

#### Interactive Map
- **Temperature Layer**: Color-coded temperature grid (automatically displayed)
- **Hotspots**: Click to toggle hotspot markers
- **Weather Stations**: Available in Standard/Detailed modes
- **Boundary**: Area outline for spatial context

#### Key Performance Indicators (KPIs)
- **Hotspots Count**: Number of identified high-temperature areas
- **Average Temperature**: Mean temperature across the analysis area
- **Maximum Temperature**: Highest recorded temperature
- **Recommendations**: Number of generated adaptation strategies

#### Charts and Analysis
- **Temperature Distribution**: Statistical overview of temperature values
- **Land Use Correlation**: Relationship between land cover types and temperature
- **Recommendations**: Actionable climate adaptation strategies

## API Endpoints

The application provides RESTful API endpoints for programmatic access:

### GET `/api/areas`
Get available areas for analysis.
- **Parameters**: `type` (bundesland|bezirk)
- **Response**: Array of area names

### POST `/api/analyze`
Perform UHI analysis.
- **Request Body**:
  ```json
  {
    "area_type": "bezirk",
    "area": "Friedrichshain-Kreuzberg",
    "start_date": "01.06.2025",
    "end_date": "30.06.2025",
    "performance_mode": "standard"
  }
  ```
- **Response**: Complete analysis results

### GET `/api/progress`
Get analysis progress (session-based).

### GET `/api/performance-modes`
Get available performance modes with descriptions.

## Technical Architecture

### Backend Components
- **Flask Application** (`app.py`): Main web server and API endpoints
- **Analysis Backend** (`analysis_backend.py`): UHI analysis engine integration
- **Settings Configuration**: Centralized configuration management

### Frontend Components
- **HTML Templates**: Jinja2-based responsive templates
- **CSS Styling**: Modern CSS with CSS Grid and Flexbox
- **JavaScript**: Vanilla JS with Leaflet maps and Chart.js visualization
- **External Libraries**:
  - Leaflet for interactive mapping
  - Chart.js for data visualization
  - Font Awesome for icons
  - Flatpickr for date selection

### Data Sources
- **Sentinel-2 Satellite Data**: Temperature and land surface analysis
- **German Weather Service (DWD)**: Ground truth temperature data
- **CORINE Land Cover**: European land use classification
- **Berlin Open Data**: Administrative boundaries and geographic data

## Configuration

### Environment Variables
- `SECRET_KEY`: Flask session encryption key
- `UHI_EARTH_ENGINE_PROJECT`: Google Earth Engine project ID
- `FLASK_ENV`: Flask environment (development/production)
- `FLASK_DEBUG`: Enable debug mode

### Performance Tuning
Performance modes are configured in `src/uhi_analyzer/config/settings.py`:
- Grid cell sizes (50m to 300m)
- Cloud cover thresholds
- Processing parameters
- Memory and batch size limits

## Troubleshooting

### Common Issues

1. **Import Errors**:
   ```bash
   # Ensure dependencies are installed
   uv sync
   ```

2. **Google Earth Engine Authentication**:
   ```bash
   # Authenticate with GEE
   earthengine authenticate
   ```

3. **Port Already in Use**:
   - Change port in `app.py` or kill existing process

4. **Memory Issues**:
   - Use Preview or Fast mode for large areas
   - Check available system memory

### Debug Mode
For development and troubleshooting:
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
uv run python app.py
```

## Development

### Code Structure
```
webapp/
├── app.py                 # Main Flask application
├── analysis_backend.py   # UHI analysis integration
├── run_webapp.py         # Startup script
├── templates/            # HTML templates
│   ├── index.html       # Main application page
│   ├── 404.html         # Error pages
│   └── 500.html
└── static/              # Static assets
    ├── css/
    │   └── style.css    # Main stylesheet
    └── js/
        └── app.js       # Frontend JavaScript
```

### Contributing
1. Follow Python best practices and PEP 8
2. Use modern web standards (HTML5, CSS3, ES6+)
3. Maintain responsive design principles
4. Add proper error handling and logging
5. Update documentation for new features

### Testing
```bash
# Run backend tests
uv run pytest

# Test webapp endpoints
curl http://localhost:5000/api/performance-modes
```

## License

This project is part of the Urban Heat Island Analyzer suite. See the main project README for license information.

## Support

For technical support or feature requests:
1. Check the main project documentation
2. Review the troubleshooting section
3. Check backend logs for detailed error information
4. Ensure all dependencies are properly installed

---

**HeatSense** - Making urban climate data accessible and actionable for everyone. 🌡️🏙️ 