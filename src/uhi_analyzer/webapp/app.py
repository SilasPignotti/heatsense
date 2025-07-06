#!/usr/bin/env python3
"""
Urban Heat Island Analysis Web Application

Flask-based web application providing an interactive interface for UHI analysis.
"""

import json
import logging
import os
import sys
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add the src directory to the Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# Import our existing backend
from uhi_analyzer.scripts.backend_example import UHIAnalysisBackend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'uhi-analyzer-secret-key'
CORS(app)

# Initialize backend
backend = UHIAnalysisBackend(log_level="INFO")

# Global variables for analysis state
current_analysis = None
analysis_results = {}


def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        # Check for NaN or infinite values
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.number):
        # Handle any numpy numeric type not caught above
        try:
            return obj.item()
        except (ValueError, TypeError):
            return float(obj) if np.issubdtype(obj.dtype, np.floating) else int(obj)
    elif hasattr(obj, 'dtype') and hasattr(obj, 'item'):
        # Handle other numpy scalar types
        try:
            return obj.item()
        except (ValueError, TypeError):
            return str(obj)
    else:
        return obj


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Main API endpoint for UHI analysis."""
    try:
        data = request.json
        
        # Validate input data
        required_fields = ['area', 'start_date', 'end_date', 'performance_mode']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Run analysis
        result = backend.analyze(
            area=data['area'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            performance_mode=data['performance_mode']
        )
        
        # Store results globally for progress tracking
        global analysis_results
        analysis_results = result
        
        # Convert numpy types to native Python types for JSON serialization
        result = convert_numpy_types(result)
        
        # Log the result structure for debugging
        logger.info(f"Analysis result structure: {list(result.keys())}")
        if 'data' in result:
            logger.info(f"Data structure: {list(result['data'].keys())}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/areas', methods=['GET'])
def get_areas():
    """Get available areas for analysis."""
    # Berlin areas that work with the backend
    berlin_areas = [
        "Kreuzberg", "Mitte", "Prenzlauer Berg", "Friedrichshain", 
        "Charlottenburg", "Wilmersdorf", "Schöneberg", "Tempelhof",
        "Neukölln", "Treptow", "Köpenick", "Lichtenberg", "Pankow",
        "Wedding", "Moabit", "Tiergarten", "Spandau", "Steglitz",
        "Zehlendorf", "Reinickendorf", "Marzahn", "Hellersdorf",
        "Charlottenburg-Wilmersdorf", "Friedrichshain-Kreuzberg",
        "Tempelhof-Schöneberg", "Treptow-Köpenick", "Marzahn-Hellersdorf"
    ]
    
    return jsonify({
        'areas': berlin_areas,
        'default': 'Kreuzberg'
    })


@app.route('/api/performance-modes', methods=['GET'])
def get_performance_modes():
    """Get available performance modes."""
    modes = {
        'preview': {
            'name': 'Preview',
            'description': 'Schnellste Analyse für erste Einblicke',
            'duration': '< 30s',
            'accuracy': 'Basis'
        },
        'fast': {
            'name': 'Fast',
            'description': 'Empfohlen für die meisten Anwendungen',
            'duration': '30-60s',
            'accuracy': 'Gut'
        },
        'standard': {
            'name': 'Standard',
            'description': 'Ausgewogene Performance und Detail',
            'duration': '1-3 min',
            'accuracy': 'Hoch'
        },
        'detailed': {
            'name': 'Detailed',
            'description': 'Vollständige Analyse mit Wetterdaten',
            'duration': '3-10 min',
            'accuracy': 'Sehr hoch'
        }
    }
    
    return jsonify(modes)


@app.route('/api/progress', methods=['GET'])
def get_progress():
    """Get current analysis progress."""
    global analysis_results
    if analysis_results:
        return jsonify({
            'progress': analysis_results.get('progress', 0),
            'status': analysis_results.get('status', 'unknown'),
            'execution_time': analysis_results.get('execution_time', 0)
        })
    return jsonify({'progress': 0, 'status': 'idle', 'execution_time': 0})


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Create template and static directories if they don't exist
    template_dir = Path(__file__).parent / 'templates'
    static_dir = Path(__file__).parent / 'static'
    
    template_dir.mkdir(exist_ok=True)
    static_dir.mkdir(exist_ok=True)
    
    # Set Flask template and static directories
    app.template_folder = str(template_dir)
    app.static_folder = str(static_dir)
    
    # Run the app
    app.run(
        host='127.0.0.1',
        port=8000,
        debug=True,
        use_reloader=True
    ) 