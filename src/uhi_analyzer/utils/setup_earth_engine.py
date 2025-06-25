#!/usr/bin/env python3
"""
Google Earth Engine Authentication Setup Module

This module provides functions to authenticate with Google Earth Engine, which is required
for accessing satellite data in the Urban Heat Island Analyzer.
"""

import subprocess
import sys
from pathlib import Path


def check_earth_engine_installed() -> bool:
    """Check if Earth Engine API is installed."""
    try:
        import ee
        return True
    except ImportError:
        return False


def authenticate_earth_engine() -> bool:
    """Authenticate with Google Earth Engine."""
    try:
        import ee
        
        # Check if already authenticated
        try:
            ee.Initialize(project='urban-heat-island-analyzer')
            print("✅ Google Earth Engine is already authenticated!")
            return True
        except Exception:
            pass
        
        # Try to authenticate
        print("🔐 Authenticating with Google Earth Engine...")
        print("This will open a browser window for authentication.")
        print("Follow the instructions in the browser to complete authentication.")
        
        ee.Authenticate()
        
        # Try to initialize with the project
        try:
            ee.Initialize(project='urban-heat-island-analyzer')
            print("✅ Google Earth Engine authentication successful!")
            return True
        except Exception as init_error:
            if "no project found" in str(init_error):
                print("⚠️  No Google Cloud project found. Trying to initialize without project...")
                try:
                    # Try initializing without specifying a project
                    ee.Initialize(project=None)
                    print("✅ Google Earth Engine initialized without project!")
                    return True
                except Exception as e2:
                    print(f"❌ Failed to initialize without project: {e2}")
                    print("\n💡 To fix this, you can:")
                    print("1. Set up a Google Cloud project: https://console.cloud.google.com/")
                    print("2. Or use the Earth Engine Code Editor: https://code.earthengine.google.com/")
                    print("3. Or try running with: export GOOGLE_CLOUD_PROJECT=your-project-id")
                    return False
            else:
                print(f"❌ Initialization failed: {init_error}")
                return False
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False


def install_earth_engine() -> bool:
    """Install Earth Engine API if not already installed."""
    if check_earth_engine_installed():
        print("✅ Earth Engine API is already installed")
        return True
    
    print("📦 Installing Earth Engine API...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "earthengine-api"
        ])
        print("✅ Earth Engine API installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Earth Engine API: {e}")
        return False


def setup_earth_engine() -> bool:
    """Complete Earth Engine setup including installation and authentication."""
    print("🌍 Google Earth Engine Setup for Urban Heat Island Analyzer")
    print("=" * 60)
    
    # Check if Earth Engine is installed
    if not check_earth_engine_installed():
        print("Earth Engine API not found. Installing...")
        if not install_earth_engine():
            print("❌ Setup failed. Please install Earth Engine API manually:")
            print("   pip install earthengine-api")
            return False
    
    # Authenticate
    if authenticate_earth_engine():
        print("\n🎉 Setup completed successfully!")
        print("You can now run the UHI analysis script with satellite data.")
        return True
    else:
        print("\n❌ Setup failed. Please try the following:")
        print("1. Make sure you have a Google account")
        print("2. Visit https://earthengine.google.com/ to sign up for Earth Engine")
        print("3. Run this setup again after approval")
        return False


def main():
    """Main function to set up Earth Engine authentication (for command line use)."""
    if setup_earth_engine():
        print("\nExample usage:")
        print("  uv run scripts/analysis/analyze_heat_islands.py")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main()) 