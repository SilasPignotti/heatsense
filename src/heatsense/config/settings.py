"""
Configuration settings for HeatSense Urban Heat Island analysis.

This module provides centralized configuration for coordinate reference systems,
data source endpoints, performance parameters, and external service settings.
All environment-dependent settings are loaded from environment variables.

Dependencies:
    - dotenv: Environment variable loading (optional)
"""

import os
from pathlib import Path

# Load environment variables if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Coordinate Reference Systems for different processing stages
CRS_CONFIG = {
    "GEOGRAPHIC": "EPSG:4326",     # WGS84 for geographic data
    "BERLIN": "EPSG:25833",        # ETRS89 UTM Zone 33N for Berlin area
    "WEB_MERCATOR": "EPSG:3857",   # Web Mercator for web mapping
    "PROCESSING": "EPSG:25833",    # Primary CRS for spatial operations
    "OUTPUT": "EPSG:4326",         # Standard output format
}

# Berlin open data WFS service endpoints
BERLIN_WFS_ENDPOINTS = {
    "state_boundary": "https://gdi.berlin.de/services/wfs/alkis_land",
    "district_boundary": "https://gdi.berlin.de/services/wfs/alkis_bezirke", 
    "locality_boundary": "https://gdi.berlin.de/services/wfs/alkis_ortsteile"
}

# Feature type identifiers for Berlin WFS services
BERLIN_WFS_FEATURE_TYPES = {
    "state_boundary": "alkis_land:landesgrenze",
    "district_boundary": "alkis_bezirke:bezirksgrenzen",
    "locality_boundary": "alkis_ortsteile:ortsteile"
}

# Available CORINE Land Cover dataset years
CORINE_YEARS = [1990, 2000, 2006, 2012, 2018]

# European Environment Agency CORINE Land Cover service URLs
CORINE_BASE_URLS = {
    1990: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC1990_WM/MapServer/0",
    2000: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2000_WM/MapServer/0", 
    2006: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2006_WM/MapServer/0",
    2012: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2012_WM/MapServer/0",
    2018: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2018_WM/MapServer/0"
}

# German Weather Service (DWD) API configuration
DWD_SETTINGS = {
    "ts_shape": "long",
    "ts_humanize": True,
    "ts_convert_units": True,
}

# DWD temperature data parameters for API requests
DWD_TEMPERATURE_PARAMETERS = [("hourly", "temperature_air", "temperature_air_mean_2m")]

# Performance optimization presets for different analysis requirements
UHI_PERFORMANCE_MODES = {
    "preview": {
        "grid_cell_size": 300,           # Coarse grid for fast preview
        "cloud_cover_threshold": 40,     # Relaxed cloud filtering
        "hotspot_threshold": 0.85,       # Lower sensitivity
        "min_cluster_size": 3,           # Small clusters allowed
        "include_weather": False,        # Skip weather validation
        "max_pixels": 5e8,              # Conservative memory limit
        "batch_size": 1000,             # Small batches
    },
    "fast": {
        "grid_cell_size": 200,           # Balanced resolution
        "cloud_cover_threshold": 30,     # Moderate cloud filtering
        "hotspot_threshold": 0.9,        # Standard sensitivity
        "min_cluster_size": 5,           # Medium clusters
        "include_weather": False,        # Skip weather validation
        "max_pixels": 1e9,              # Higher memory limit
        "batch_size": 3000,             # Larger batches
    },
    "standard": {
        "grid_cell_size": 100,           # Standard resolution
        "cloud_cover_threshold": 20,     # Strict cloud filtering
        "hotspot_threshold": 0.9,        # Standard sensitivity
        "min_cluster_size": 5,           # Medium clusters
        "include_weather": True,         # Include weather validation
        "max_pixels": 1e9,              # Standard memory limit
        "batch_size": 5000,             # Optimal batch size
    },
    "detailed": {
        "grid_cell_size": 50,            # High resolution
        "cloud_cover_threshold": 20,     # Strict cloud filtering
        "hotspot_threshold": 0.95,       # High sensitivity
        "min_cluster_size": 10,          # Large clusters only
        "include_weather": True,         # Include weather validation
        "max_pixels": 2e9,              # High memory limit
        "batch_size": 2000,             # Conservative for memory
    }
}

# External service configuration from environment variables
UHI_EARTH_ENGINE_PROJECT = os.getenv("UHI_EARTH_ENGINE_PROJECT", "your-gee-project-id")
UHI_LOG_DIR = Path("logs")
UHI_LOG_LEVEL = os.getenv("UHI_LOG_LEVEL", "INFO")