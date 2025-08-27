#!/usr/bin/env python3
"""
HeatSense web application - Flask interface for Urban Heat Island analysis.

This module provides a web-based interface for conducting UHI analysis with
interactive forms, real-time progress tracking, and comprehensive result
visualization. Built with Flask and modern web technologies.

Dependencies:
    - flask: Web framework
    - flask_cors: Cross-origin resource sharing support
"""

import logging
import os
import sys
from datetime import datetime

from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from heatsense.config.settings import UHI_PERFORMANCE_MODES
from heatsense.webapp.analysis_backend import UHIAnalysisBackend

# Configure Flask application
app = Flask(__name__, 
           template_folder='templates', 
           static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'development-only-change-in-production')

# Enable Cross-Origin Resource Sharing
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize analysis backend
backend = UHIAnalysisBackend(log_level="INFO")

# Berlin administrative divisions for area selection
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

FEDERAL_STATES = ["Berlin"]

BERLIN_ORTSTEILE = [
    "Adlershof", "Altglienicke", "Alt-Hohenschönhausen", "Alt-Treptow",
    "Baumschulenweg", "Biesdorf", "Blankenburg", "Blankenfelde", "Bohnsdorf",
    "Borsigwalde", "Britz", "Buch", "Buckow", "Charlottenburg", "Charlottenburg-Nord",
    "Dahlem", "Falkenberg", "Falkenhagener Feld", "Fennpfuhl", "Französisch Buchholz",
    "Friedenau", "Friedrichshagen", "Friedrichsfelde", "Friedrichshain", "Frohnau",
    "Gatow", "Gesundbrunnen", "Gropiusstadt", "Grünau", "Grunewald", "Hakenfelde",
    "Halensee", "Hansaviertel", "Haselhorst", "Heiligensee", "Heinersdorf",
    "Hellersdorf", "Hermsdorf", "Johannisthal", "Karlshorst", "Karow", "Kaulsdorf",
    "Kladow", "Konradshöhe", "Köpenick", "Kreuzberg", "Lankwitz", "Lichtenberg",
    "Lichtenrade", "Lichterfelde", "Lübars", "Mahlsdorf", "Malchow", "Mariendorf",
    "Marienfelde", "Märkisches Viertel", "Marzahn", "Mitte", "Moabit", "Müggelheim",
    "Neukölln", "Neu-Hohenschönhausen", "Niederschöneweide", "Niederschönhausen",
    "Nikolassee", "Oberschöneweide", "Pankow", "Plänterwald", "Prenzlauer Berg",
    "Rahnsdorf", "Reinickendorf", "Rosenthal", "Rudow", "Rummelsburg", "Schmargendorf",
    "Schmöckwitz", "Schöneberg", "Siemensstadt", "Spandau", "Staaken",
    "Stadtrandsiedlung Malchow", "Steglitz", "Tegel", "Tempelhof", "Tiergarten",
    "Waidmannslust", "Wannsee", "Wartenberg", "Wedding", "Weißensee", "Westend",
    "Wilhelmsruh", "Wilhelmstadt", "Wilmersdorf", "Wittenau", "Zehlendorf"
]


@app.route('/')
def index():
    """Render main application page with area selection options."""
    return render_template('index.html', 
                         districts=BERLIN_DISTRICTS,
                         federal_states=FEDERAL_STATES,
                         performance_modes=UHI_PERFORMANCE_MODES)


@app.route('/api/areas')
def get_areas():
    """Get available geographical areas based on administrative level."""
    area_type = request.args.get('type', 'bezirk')
    
    area_mappings = {
        'stadt': FEDERAL_STATES,
        'bezirk': BERLIN_DISTRICTS,
        'ortsteil': BERLIN_ORTSTEILE
    }
    
    return jsonify(area_mappings.get(area_type, BERLIN_DISTRICTS))


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Execute Urban Heat Island analysis with user-specified parameters."""
    try:
        data = request.get_json()
        
        # Extract and validate required parameters
        area = data.get('area')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        performance_mode = data.get('performance_mode', 'standard')
        
        if not all([area, start_date, end_date]):
            return jsonify({
                'status': 'error',
                'errors': ['Missing required parameters: area, start_date, end_date']
            }), 400
        
        if performance_mode not in UHI_PERFORMANCE_MODES:
            return jsonify({
                'status': 'error', 
                'errors': [f'Invalid performance mode: {performance_mode}']
            }), 400
        
        # Parse and validate date format
        try:
            start_date_parsed = datetime.strptime(start_date, '%d.%m.%Y').strftime('%Y-%m-%d')
            end_date_parsed = datetime.strptime(end_date, '%d.%m.%Y').strftime('%Y-%m-%d')
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'errors': [f'Invalid date format. Use DD.MM.YYYY: {str(e)}']
            }), 400
        
        # Store analysis session information
        analysis_id = f"{area}_{start_date}_{end_date}_{performance_mode}"
        session['analysis_id'] = analysis_id
        session['analysis_status'] = 'running'
        
        logger.info(f"Starting UHI analysis: {area}, {start_date_parsed} to {end_date_parsed}, mode: {performance_mode}")
        
        # Execute analysis
        result = backend.analyze(
            area=area,
            start_date=start_date_parsed,
            end_date=end_date_parsed,
            performance_mode=performance_mode
        )
        
        session['analysis_status'] = result.get('status', 'completed')
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Analysis execution failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'errors': [f'Analysis failed: {str(e)}'],
            'execution_time': 0
        }), 500


@app.route('/api/progress')
def get_progress():
    """Get current analysis progress and status."""
    analysis_id = session.get('analysis_id')
    status = session.get('analysis_status', 'unknown')
    
    return jsonify({
        'analysis_id': analysis_id,
        'status': status,
        'progress': 100 if status == 'completed' else 50
    })


@app.route('/api/performance-modes')
def get_performance_modes():
    """Get available performance modes with detailed descriptions."""
    mode_definitions = [
        {
            'key': 'preview',
            'name': 'Preview',
            'icon': 'fas fa-eye',
            'estimated_time': '<30s',
            'description': 'Quick analysis for initial insights'
        },
        {
            'key': 'fast',
            'name': 'Fast',
            'icon': 'fas fa-bolt',
            'estimated_time': '30-60s',
            'description': 'Recommended for most applications'
        },
        {
            'key': 'standard',
            'name': 'Standard',
            'icon': 'fas fa-balance-scale',
            'estimated_time': '1-3 min',
            'description': 'Balanced performance and detail'
        },
        {
            'key': 'detailed',
            'name': 'Detailed',
            'icon': 'fas fa-microscope',
            'estimated_time': '3-10 min',
            'description': 'Comprehensive analysis with full detail'
        }
    ]
    
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
                'includes_weather': config.get('include_weather', False)
            }
    
    return jsonify(modes)


@app.route('/api/download-results')
def download_results():
    """Prepare analysis results for client-side download."""
    try:
        analysis_id = session.get('analysis_id')
        if not analysis_id:
            return jsonify({
                'status': 'error',
                'errors': ['No analysis results available for download']
            }), 404
        
        return jsonify({
            'status': 'success',
            'message': 'Use client-side download functionality',
            'analysis_id': analysis_id
        })
        
    except Exception as e:
        logger.error(f"Download preparation failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'errors': [f'Download failed: {str(e)}']
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle HTTP 404 Not Found errors."""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle HTTP 500 Internal Server errors."""
    logger.error(f"Internal server error: {str(error)}")
    return render_template('500.html'), 500


if __name__ == '__main__':
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Configure development/production mode
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info("Starting HeatSense web application")
    app.run(host='0.0.0.0', port=8000, debug=debug_mode)