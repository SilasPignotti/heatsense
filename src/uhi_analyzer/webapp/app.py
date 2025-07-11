#!/usr/bin/env python3
"""
HeatSense - Urban Heat Island Analyzer Web Application

A Flask web application providing an intuitive interface for urban heat island analysis.
Built with modern design principles and comprehensive data visualization.
"""

import json
import logging
import os
import sys
from datetime import datetime, date
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify, session, send_file
from flask_cors import CORS
import io
import zipfile
import geopandas as gpd
from shapely.geometry import box

# Add the src directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from uhi_analyzer.webapp.backend_logic import UHIAnalysisBackend
from uhi_analyzer.config.settings import UHI_PERFORMANCE_MODES

# Initialize Flask app
app = Flask(__name__, 
           template_folder='templates', 
           static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'heatsense-dev-key-2025')

# Enable CORS for development
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize backend
backend = UHIAnalysisBackend(log_level="INFO")

# Berlin districts for dropdown
BERLIN_DISTRICTS = [
    "Charlottenburg-Wilmersdorf",
    "Friedrichshain-Kreuzberg", 
    "Lichtenberg",
    "Marzahn-Hellersdorf",
    "Mitte",
    "Neukölln",
    "Pankow",
    "Reinickendorf",
    "Spandau",
    "Steglitz-Zehlendorf",
    "Tempelhof-Schöneberg",
    "Treptow-Köpenick"
]

# Federal states (currently only Berlin supported)
FEDERAL_STATES = ["Berlin"]

# Berlin Ortsteile for dropdown
BERLIN_ORTSTEILE = [
    "Adlershof",
    "Altglienicke",
    "Alt-Hohenschönhausen",
    "Alt-Treptow",
    "Baumschulenweg",
    "Biesdorf",
    "Blankenburg",
    "Blankenfelde",
    "Bohnsdorf",
    "Borsigwalde",
    "Britz",
    "Buch",
    "Buckow",
    "Charlottenburg",
    "Charlottenburg-Nord",
    "Dahlem",
    "Falkenberg",
    "Falkenhagener Feld",
    "Fennpfuhl",
    "Französisch Buchholz",
    "Friedenau",
    "Friedrichshagen",
    "Friedrichsfelde",
    "Friedrichshain",
    "Frohnau",
    "Gatow",
    "Gesundbrunnen",
    "Gropiusstadt",
    "Grünau",
    "Grunewald",
    "Hakenfelde",
    "Halensee",
    "Hansaviertel",
    "Haselhorst",
    "Heiligensee",
    "Heinersdorf",
    "Hellersdorf",
    "Hermsdorf",
    "Johannisthal",
    "Karlshorst",
    "Karow",
    "Kaulsdorf",
    "Kladow",
    "Konradshöhe",
    "Köpenick",
    "Kreuzberg",
    "Lankwitz",
    "Lichtenberg",
    "Lichtenrade",
    "Lichterfelde",
    "Lübars",
    "Mahlsdorf",
    "Malchow",
    "Mariendorf",
    "Marienfelde",
    "Märkisches Viertel",
    "Marzahn",
    "Mitte",
    "Moabit",
    "Müggelheim",
    "Neukölln",
    "Neu-Hohenschönhausen",
    "Niederschöneweide",
    "Niederschönhausen",
    "Nikolassee",
    "Oberschöneweide",
    "Pankow",
    "Plänterwald",
    "Prenzlauer Berg",
    "Rahnsdorf",
    "Reinickendorf",
    "Rosenthal",
    "Rudow",
    "Rummelsburg",
    "Schmargendorf",
    "Schmöckwitz",
    "Schöneberg",
    "Siemensstadt",
    "Spandau",
    "Staaken",
    "Stadtrandsiedlung Malchow",
    "Steglitz",
    "Tegel",
    "Tempelhof",
    "Tiergarten",
    "Waidmannslust",
    "Wannsee",
    "Wartenberg",
    "Wedding",
    "Weißensee",
    "Westend",
    "Wilhelmsruh",
    "Wilhelmstadt",
    "Wilmersdorf",
    "Wittenau",
    "Zehlendorf"
]

@app.route('/')
def index():
    """Main page of the HeatSense application."""
    return render_template('index.html', 
                         districts=BERLIN_DISTRICTS,
                         federal_states=FEDERAL_STATES,
                         performance_modes=UHI_PERFORMANCE_MODES)

@app.route('/api/areas')
def get_areas():
    """API endpoint to get available areas based on selection type."""
    area_type = request.args.get('type', 'bezirk')
    
    if area_type == 'stadt':
        return jsonify(FEDERAL_STATES)  # Only Berlin supported
    elif area_type == 'bezirk':
        return jsonify(BERLIN_DISTRICTS)
    elif area_type == 'ortsteil':
        return jsonify(BERLIN_ORTSTEILE)
    else:  # default to bezirk
        return jsonify(BERLIN_DISTRICTS)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """API endpoint to perform UHI analysis."""
    try:
        data = request.get_json()
        
        # Extract parameters
        area = data.get('area')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        performance_mode = data.get('performance_mode', 'standard')
        
        # Validate inputs
        if not area or not start_date or not end_date:
            return jsonify({
                'status': 'error',
                'errors': ['Missing required parameters: area, start_date, end_date']
            }), 400
        
        # Validate performance mode
        if performance_mode not in UHI_PERFORMANCE_MODES:
            return jsonify({
                'status': 'error', 
                'errors': [f'Invalid performance mode: {performance_mode}']
            }), 400
        
        # Convert dates to required format (YYYY-MM-DD)
        try:
            start_date_parsed = datetime.strptime(start_date, '%d.%m.%Y').strftime('%Y-%m-%d')
            end_date_parsed = datetime.strptime(end_date, '%d.%m.%Y').strftime('%Y-%m-%d')
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'errors': [f'Invalid date format. Use DD.MM.YYYY: {str(e)}']
            }), 400
        
        # Store analysis parameters in session for progress tracking
        session['analysis_id'] = f"{area}_{start_date}_{end_date}_{performance_mode}"
        session['analysis_status'] = 'running'
        
        logger.info(f"Starting analysis: {area}, {start_date_parsed} to {end_date_parsed}, mode: {performance_mode}")
        
        # Perform analysis using backend
        result = backend.analyze(
            area=area,
            start_date=start_date_parsed,
            end_date=end_date_parsed,
            performance_mode=performance_mode
        )
        
        # Update session status
        session['analysis_status'] = result.get('status', 'completed')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'errors': [f'Analysis failed: {str(e)}'],
            'execution_time': 0
        }), 500

@app.route('/api/progress')
def get_progress():
    """API endpoint to get analysis progress."""
    analysis_id = session.get('analysis_id')
    status = session.get('analysis_status', 'unknown')
    
    # In a real implementation, you might track progress in Redis or database
    # For now, return basic status information
    return jsonify({
        'analysis_id': analysis_id,
        'status': status,
        'progress': 100 if status == 'completed' else 50  # Simplified progress
    })

@app.route('/api/performance-modes')
def get_performance_modes():
    """API endpoint to get available performance modes with descriptions."""
    # Define modes in the desired order with German descriptions and icons
    mode_definitions = [
        {
            'key': 'preview',
            'name': 'Preview',
            'icon': 'fas fa-eye',
            'estimated_time': '<30s',
            'description': 'Spontane Analyse für erste Einblicke'
        },
        {
            'key': 'fast',
            'name': 'Fast',
            'icon': 'fas fa-bolt',
            'estimated_time': '30-60s',
            'description': 'Empfohlen für die meisten Anwendungen'
        },
        {
            'key': 'standard',
            'name': 'Standard',
            'icon': 'fas fa-balance-scale',
            'estimated_time': '1-3 min',
            'description': 'Ausgewogene Performance und Detail'
        },
        {
            'key': 'detailed',
            'name': 'Detailed',
            'icon': 'fas fa-microscope',
            'estimated_time': '3-10 min',
            'description': 'Vollständige Analyse mit Performance und Detail'
        }
    ]
    
    # Create ordered dictionary with mode information
    modes = {}
    for mode_def in mode_definitions:
        key = mode_def['key']
        if key in UHI_PERFORMANCE_MODES:
            config = UHI_PERFORMANCE_MODES[key]
            modes[key] = {
                'name': mode_def['name'],
                'icon': mode_def['icon'],
                'description': mode_def['description'],
                'estimated_time': mode_def['estimated_time'],
                'grid_cell_size': config.get('grid_cell_size', 100),
                'includes_weather': key in ['standard', 'detailed']
            }
    
    return jsonify(modes)

@app.route('/api/download-results')
def download_results():
    """API endpoint to download analysis results as JSON."""
    try:
        # Get analysis ID from session
        analysis_id = session.get('analysis_id')
        if not analysis_id:
            return jsonify({
                'status': 'error',
                'errors': ['No analysis results available for download']
            }), 404
        
        # Get stored results from session or a more persistent storage
        # For now, we'll indicate that the client should send the data
        # In a production app, you might store results in Redis or database
        
        # For now, return a response that tells the client to use JavaScript download
        return jsonify({
            'status': 'success',
            'message': 'Use client-side download',
            'analysis_id': analysis_id
        })
        
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'errors': [f'Download failed: {str(e)}']
        }), 500







@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(error)}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    
    # Run the application
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=8000, debug=debug_mode) 