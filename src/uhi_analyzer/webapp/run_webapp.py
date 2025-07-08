#!/usr/bin/env python3
"""
HeatSense Webapp Startup Script

This script launches the HeatSense Flask web application for Urban Heat Island analysis.
"""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

try:
    from uhi_analyzer.webapp.app import app
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you have installed the dependencies with 'uv sync'")
    sys.exit(1)

def main():
    """Launch the HeatSense Flask web application."""
    print("🔥 Starting HeatSense Urban Heat Island Analyzer...")
    print("📍 Web interface will be available at: http://localhost:8000")
    print("🚀 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    # Set environment variables for development
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Run the Flask app
        app.run(
            host='0.0.0.0',
            port=8000,
            debug=True,
            use_reloader=True
        )
    except KeyboardInterrupt:
        print("\n🛑 HeatSense stopped by user")
    except Exception as e:
        print(f"❌ Failed to start HeatSense: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 