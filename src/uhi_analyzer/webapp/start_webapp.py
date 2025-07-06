#!/usr/bin/env python3
"""
Urban Heat Island Analysis Web Application Starter

This script starts the Flask web application with proper Python path configuration.
"""

import os
import sys
from pathlib import Path
import webbrowser
import time
import threading

# Add the src directory to the Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Import the Flask app
from uhi_analyzer.webapp.app import app

def open_browser(host, port):
    """Open browser after a short delay."""
    time.sleep(1.5)
    webbrowser.open(f'http://{host}:{port}')

class ErrorHandler:
    """Context manager for error handling."""
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"❌ Error: {exc_val}")
            return False
        return True

def error_handler():
    """Create error handler."""
    return ErrorHandler()

if __name__ == '__main__':
    print("🔥 Urban Heat Island Analysis Web Application")
    print("="*50)
    
    host = '127.0.0.1'
    port = 8000
    
    # Create template and static directories if they don't exist
    webapp_dir = Path(__file__).parent
    template_dir = webapp_dir / 'templates'
    static_dir = webapp_dir / 'static'
    
    template_dir.mkdir(exist_ok=True)
    static_dir.mkdir(exist_ok=True)
    
    # Set Flask template and static directories
    app.template_folder = str(template_dir)
    app.static_folder = str(static_dir)
    
    print(f"🌐 Server will start at: http://{host}:{port}")
    print("📊 Ready for Urban Heat Island Analysis!")
    print("🚀 Starting server...")
    
    # Open browser in a separate thread
    browser_thread = threading.Thread(target=open_browser, args=(host, port))
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start the Flask application
    with error_handler():
        app.run(
            host=host,
            port=port,
            debug=True,
            use_reloader=False  # Disable reloader to prevent browser opening twice
        ) 