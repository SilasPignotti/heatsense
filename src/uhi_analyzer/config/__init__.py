"""Configuration module for the Urban Heat Island Analyzer."""

from .settings import *

__all__ = [
    # Coordinate System Configuration
    "CRS_CONFIG",
    
    # Legacy CRS constants (for backward compatibility)
    "GEOGRAPHIC_CRS",
    "BERLIN_CRS", 
    "GERMANY_CRS",
    "GERMANY_EAST_CRS",
    "WEB_MERCATOR_CRS",
    
    # WFS Configuration
    "WFS_ENDPOINTS",
    "WFS_HEADERS", 
    "WFS_TIMEOUT",
    
    # Corine Configuration
    "CORINE_BASE_URL",
    "CORINE_BASE_URLS",
    "CORINE_YEARS",
    "CORINE_LANDUSE_MAPPING",
    "CORINE_IMPERVIOUS_COEFFICIENTS",
    "DEFAULT_RECORD_COUNT",
    "DEFAULT_TIMEOUT",
    "DEFAULT_OUTPUT_FORMAT",
    "DEFAULT_OUTPUT_CRS",
    "DEFAULT_INPUT_CRS",
    "get_best_corine_year_for_date_range",
    
    # DWD Configuration
    "DWD_SETTINGS",
    "DWD_TEMPERATURE_PARAMETERS",
    "DWD_BUFFER_DISTANCE",
    "DWD_INTERPOLATION_RESOLUTION",
    "DWD_INTERPOLATION_METHOD",
    "DWD_INTERPOLATE_BY_DEFAULT",
    "DWD_INPUT_CRS",
    "DWD_PROCESSING_CRS",
    "DWD_OUTPUT_CRS",
    
    # UHI Analyzer Configuration
    "UHI_CLOUD_COVER_THRESHOLD",
    "UHI_LANDSAT_COLLECTION",
    "UHI_TEMPERATURE_BAND",
    "UHI_SCALE",
    "UHI_MAX_PIXELS",
    "UHI_TEMP_MULTIPLIER",
    "UHI_TEMP_ADDEND",
    "UHI_KELVIN_OFFSET",
    "UHI_GRID_CELL_SIZE",
    "UHI_GRID_CRS",
    "UHI_OUTPUT_CRS",
    "UHI_HOTSPOT_THRESHOLD",
    "UHI_MIN_CLUSTER_SIZE",
    "UHI_MORAN_SIGNIFICANCE",
    "UHI_PERCENTILES",
    "UHI_CORRELATION_THRESHOLD",
    "UHI_VISUALIZATION_DPI",
    "UHI_VISUALIZATION_FIGSIZE",
    "UHI_TEMPERATURE_COLORMAP",
    "UHI_LOG_DIR",
    "UHI_LOG_LEVEL",
] 