"""
Settings and configuration for the Urban Heat Island Analyzer.

This module contains all configuration settings, constants, and utility functions
for the UHI analyzer application.
"""

from typing import Dict, List, Tuple
import os
from pathlib import Path

# =============================================================================
# WFS Configuration
# =============================================================================

# WFS-Endpunkte für verschiedene Geodatendienste
WFS_ENDPOINTS = {
    "berlin_admin_boundaries": {
        "url": "https://gdi.berlin.de/services/wfs/alkis_land", 
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "alkis_land:landesgrenze",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326"
    }
}

# HTTP-Header für WFS-Requests
WFS_HEADERS = {
    "User-Agent": "Urban-Heat-Island-Analyzer/1.0",
    "Accept": "application/json,application/geojson"
}

# Timeout-Einstellungen
WFS_TIMEOUT = 30  # Sekunden

# =============================================================================
# Corine Land Cover Configuration
# =============================================================================

# ArcGIS REST API Configuration für alle verfügbaren Jahre
CORINE_YEARS = [1990, 2000, 2006, 2012, 2018]

CORINE_BASE_URLS = {
    1990: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC1990_WM/MapServer/0",
    2000: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2000_WM/MapServer/0", 
    2006: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2006_WM/MapServer/0",
    2012: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2012_WM/MapServer/0",
    2018: "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2018_WM/MapServer/0"
}

# Legacy-Konfiguration für Rückwärtskompatibilität (verwendet 2018)
CORINE_BASE_URL = CORINE_BASE_URLS[2018]

# API Parameters
DEFAULT_RECORD_COUNT = 1000
DEFAULT_TIMEOUT = 30
DEFAULT_OUTPUT_FORMAT = "geojson"
DEFAULT_OUTPUT_CRS = "4326"  # WGS84
DEFAULT_INPUT_CRS = "3857"   # Web Mercator

def get_closest_corine_year(target_year: int) -> int:
    """
    Findet das nächstgelegene verfügbare Corine-Jahr.
    
    Args:
        target_year: Gewünschtes Jahr
        
    Returns:
        Nächstgelegenes verfügbares Corine-Jahr
        
    Raises:
        ValueError: Wenn keine verfügbaren Jahre vorhanden sind
    """
    if not CORINE_YEARS:
        raise ValueError("Keine verfügbaren Corine-Jahre konfiguriert")
    
    closest_year = min(CORINE_YEARS, key=lambda x: abs(x - target_year))
    return closest_year 