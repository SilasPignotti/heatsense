#!/usr/bin/env python3
"""
HeatSense Web Application Launcher

Launch the HeatSense Urban Heat Island Analyzer web interface.
This is the main entry point for running the web application.

Usage:
    python run_webapp.py
    or
    uv run run_webapp.py

The webapp will be available at: http://localhost:8000
"""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

try:
    from heatsense.webapp.app import app
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you have installed the dependencies:")
    print("   uv sync")
    print("   or")
    print("   pip install -e .")
    sys.exit(1)

def main():
    """Launch the HeatSense Flask web application."""
    print("🔥 HeatSense - Urban Heat Island Analyzer")
    print("=" * 50)
    print("📍 Starting web interface...")
    print("🌐 URL: http://localhost:8000")
    print("🚀 Press Ctrl+C to stop the server")
    print("=" * 50)
    
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
        print("\n🛑 HeatSense webapp stopped by user")
    except Exception as e:
        print(f"❌ Failed to start webapp: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()