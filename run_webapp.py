#!/usr/bin/env python3
"""
HeatSense web application launcher.

Starts the Flask web interface for Urban Heat Island analysis with proper
configuration for development and production environments.

Dependencies:
    - flask: Web application framework
    - heatsense: Main analysis package

Usage:
    python run_webapp.py
    or
    uv run run_webapp.py

The web application will be available at: http://localhost:8000
"""

import logging
import os
import sys
from pathlib import Path

# Add source directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

try:
    from heatsense.webapp.app import app
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Install dependencies with:")
    print("   uv sync")
    print("   or")
    print("   pip install -e .")
    sys.exit(1)


def configure_logging():
    """Set up logging configuration for the web application."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def display_startup_info():
    """Display application startup information."""
    print("🔥 HeatSense - Urban Heat Island Analyzer")
    print("=" * 50)
    print("📍 Starting web interface...")
    print("🌐 Access URL: http://localhost:8000")
    print("🌐 Network URL: http://0.0.0.0:8000")
    print("🚀 Press Ctrl+C to stop the server")
    print("=" * 50)


def main():
    """Launch the HeatSense Flask web application."""
    configure_logging()
    display_startup_info()

    # Determine environment configuration
    is_development = os.environ.get("FLASK_ENV", "production") == "development"

    if is_development:
        print("🔧 Running in DEVELOPMENT mode")
    else:
        print("🚀 Running in PRODUCTION mode")

    try:
        app.run(host="0.0.0.0", port=8000, debug=is_development, use_reloader=is_development)
    except KeyboardInterrupt:
        print("\n🛑 HeatSense webapp stopped by user")
    except Exception as e:
        print(f"❌ Failed to start web application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
