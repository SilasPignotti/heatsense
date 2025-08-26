"""
Settings and configuration for the Urban Heat Island Analyzer.

This module contains all configuration settings, constants, and utility functions
for the UHI analyzer application.
"""

import os
from pathlib import Path

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

# =============================================================================
# Coordinate Reference Systems (CRS) Configuration
# =============================================================================

# Standard coordinate reference systems used throughout the application
CRS_CONFIG = {
    # Geographic coordinate systems
    "GEOGRAPHIC": "EPSG:4326",  # WGS84 - Standard for geographic coordinates
    
    # Projected coordinate systems for different regions
    "BERLIN": "EPSG:25833",     # ETRS89 / UTM Zone 33N - Standard for Berlin
    "WEB_MERCATOR": "EPSG:3857",  # Web Mercator - Standard for web maps
    
    # Processing coordinate systems (for spatial operations)
    "PROCESSING": "EPSG:25833",  # Standard for spatial operations in Berlin
    
    # Output coordinate systems
    "OUTPUT": "EPSG:4326",       # Standard output format (WGS84)
}

# =============================================================================
# WFS Configuration
# =============================================================================

# Common WFS endpoints for Berlin geodata services
BERLIN_WFS_ENDPOINTS = {
    "state_boundary": "https://gdi.berlin.de/services/wfs/alkis_land",
    "district_boundary": "https://gdi.berlin.de/services/wfs/alkis_bezirke", 
    "locality_boundary": "https://gdi.berlin.de/services/wfs/alkis_ortsteile"
}

# Common feature type names for Berlin WFS services
BERLIN_WFS_FEATURE_TYPES = {
    "state_boundary": "alkis_land:landesgrenze",
    "district_boundary": "alkis_bezirke:bezirksgrenzen",
    "locality_boundary": "alkis_ortsteile:ortsteile"
}

# =============================================================================
# Corine Configuration
# =============================================================================

CORINE_YEARS = [1990, 2000, 2006, 2012, 2018]
CORINE_BASE_URLS = {
    1990: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC1990_WM/MapServer/0",
    2000: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2000_WM/MapServer/0", 
    2006: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2006_WM/MapServer/0",
    2012: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2012_WM/MapServer/0",
    2018: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2018_WM/MapServer/0"
}

# =============================================================================
# DWD Configuration
# =============================================================================

# Default settings for DWD wetterdienst requests
DWD_SETTINGS = {
    "ts_shape": "long",
    "ts_humanize": True,
    "ts_convert_units": True,
}

# Temperature parameters for DWD weather station data
DWD_TEMPERATURE_PARAMETERS = [("hourly", "temperature_air", "temperature_air_mean_2m")]

# =============================================================================
# Performance Configuration
# =============================================================================

# Performance Modes for different use cases (KEEP - used by calling functions)
UHI_PERFORMANCE_MODES = {
    # Webapp preview mode - fast but lower resolution
    "preview": {
        "grid_cell_size": 300,           # Larger cells for speed
        "cloud_cover_threshold": 40,     # More lenient cloud filtering
        "hotspot_threshold": 0.85,       # Slightly lower threshold
        "min_cluster_size": 3,           # Smaller minimum clusters
        "include_weather": False,        # No weather data for fastest mode
        "max_pixels": 5e8,              # Reduced pixel limit
        "batch_size": 1000,             # Smaller batches
    },
    
    # Fast mode - balanced speed and quality
    "fast": {
        "grid_cell_size": 200,           # Medium resolution
        "cloud_cover_threshold": 30,     # Balanced cloud filtering
        "hotspot_threshold": 0.9,        # Standard threshold
        "min_cluster_size": 5,           # Standard clusters
        "include_weather": False,        # No weather data for fast mode
        "max_pixels": 1e9,              # Standard pixel limit
        "batch_size": 3000,             # Medium batches
    },
    
    # Standard mode - default settings
    "standard": {
        "grid_cell_size": 100,           # Standard resolution
        "cloud_cover_threshold": 20,     # Standard cloud filtering
        "hotspot_threshold": 0.9,        # Standard threshold
        "min_cluster_size": 5,           # Standard clusters
        "include_weather": True,         # Include weather data for validation
        "max_pixels": 1e9,              # Standard pixel limit
        "batch_size": 5000,             # Standard batches
    },
    
    # High quality mode - detailed analysis
    "detailed": {
        "grid_cell_size": 50,            # High resolution
        "cloud_cover_threshold": 20,     # Reasonable cloud filtering
        "hotspot_threshold": 0.95,       # High threshold
        "min_cluster_size": 10,          # Larger minimum clusters
        "include_weather": True,         # Include weather data for validation
        "max_pixels": 2e9,              # Higher pixel limit
        "batch_size": 2000,             # Smaller batches for precision
    }
}

# =============================================================================
# UHI Analyzer Configuration
# =============================================================================

# Google Earth Engine Configuration
UHI_EARTH_ENGINE_PROJECT = os.getenv("UHI_EARTH_ENGINE_PROJECT", "your-gee-project-id")  # GEE project ID from environment

# Logging Configuration
UHI_LOG_DIR = Path("logs")  # Directory for log files
UHI_LOG_LEVEL = "INFO"  # Logging level


 