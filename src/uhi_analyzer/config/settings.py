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
    "GERMANY_WEST": "EPSG:25832", # ETRS89 / UTM Zone 32N - Standard for Germany (West)
    "GERMANY_EAST": "EPSG:25833", # ETRS89 / UTM Zone 33N - Standard for Germany (East)
    "WEB_MERCATOR": "EPSG:3857",  # Web Mercator - Standard for web maps
    
    # Processing coordinate systems (for spatial operations)
    "PROCESSING": "EPSG:25833",  # Standard for spatial operations in Berlin
    
    # Output coordinate systems
    "OUTPUT": "EPSG:4326",       # Standard output format (WGS84)
}

# =============================================================================
# WFS Configuration
# =============================================================================

# WFS-Endpunkte für verschiedene Geodatendienste
WFS_ENDPOINTS = {
    "berlin_state_boundary": {
        "url": "https://gdi.berlin.de/services/wfs/alkis_land",
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "alkis_land:landesgrenze",
        "outputFormat": "application/json",
        "srsName": CRS_CONFIG["GEOGRAPHIC"],
        "description": "Berlin state administrative boundary"
    },
    "berlin_district_boundary": {
        "url": "https://gdi.berlin.de/services/wfs/alkis_bezirke",
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "alkis_bezirke:bezirksgrenzen",
        "outputFormat": "application/json",
        "srsName": CRS_CONFIG["GEOGRAPHIC"],
        "description": "Berlin district administrative boundaries from ALKIS"
    },
    "berlin_locality_boundary": {
        "url": "https://gdi.berlin.de/services/wfs/alkis_ortsteile",
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "alkis_ortsteile:ortsteile",
        "outputFormat": "application/json",
        "srsName": CRS_CONFIG["GEOGRAPHIC"],
        "description": "Berlin locality (Ortsteil) administrative boundaries from ALKIS"
    }
}

# HTTP-Header für WFS-Requests
WFS_HEADERS = {
    "User-Agent": "Python-WFS-Downloader/1.0",
    "Accept": "application/json,application/geojson,text/xml"
}

# WFS Configuration
WFS_TIMEOUT = 30  # Timeout in seconds
WFS_MAX_FEATURES = 10000  # Maximum features per request
WFS_RETRY_ATTEMPTS = 3  # Number of retry attempts on failure
WFS_RETRY_DELAY = 2  # Delay between retries in seconds

# Supported output formats
WFS_OUTPUT_FORMATS = {
    "geojson": "application/json",
    "gml": "application/gml+xml",
    "json": "application/json"
}

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

# API Parameters
DEFAULT_RECORD_COUNT = 1000
DEFAULT_TIMEOUT = 30
DEFAULT_OUTPUT_FORMAT = "geojson"

# Corine Land Cover Code zu Land Use Type Mapping
CORINE_LANDUSE_MAPPING = {
    # Urban fabric
    111: "urban_continuous",
    112: "urban_discontinuous",
    
    # Industrial, commercial and transport units
    121: "industrial_commercial",
    122: "road_transport",
    123: "port_areas", 
    124: "airports",
    
    # Mine, dump and construction sites
    131: "mineral_extraction",
    132: "dump_sites",
    133: "construction_sites",
    
    # Artificial non-agricultural vegetated areas
    141: "green_urban_areas",
    142: "sport_leisure",
    
    # Arable land
    211: "non_irrigated_arable",
    212: "irrigated_arable", 
    213: "rice_fields",
    
    # Permanent crops
    221: "vineyards",
    222: "fruit_trees",
    223: "olive_groves",
    
    # Pastures
    231: "pastures",
    
    # Heterogeneous agricultural areas
    241: "agriculture_natural_mixed",
    242: "complex_cultivation",
    243: "agriculture_natural_areas",
    244: "agro_forestry",
    
    # Forest
    311: "broad_leaved_forest",
    312: "coniferous_forest", 
    313: "mixed_forest",
    
    # Shrub and herbaceous vegetation associations
    321: "natural_grasslands",
    322: "moors_heathland",
    323: "sclerophyllous_vegetation",
    324: "transitional_woodland",
    
    # Open spaces with little or no vegetation
    331: "beaches_dunes",
    332: "bare_rocks",
    333: "sparsely_vegetated",
    334: "burnt_areas",
    335: "glaciers_snow",
    
    # Wetlands
    411: "inland_marshes",
    412: "peat_bogs",
    421: "salt_marshes",
    422: "salines",
    423: "intertidal_flats",
    
    # Water bodies
    511: "water_courses",
    512: "water_bodies",
    521: "coastal_lagoons",
    522: "estuaries",
    523: "sea_ocean"
}

# Impervious Area Coefficients für verschiedene Land Use Types
# Basierend auf wissenschaftlicher Literatur für europäische Städte
CORINE_IMPERVIOUS_COEFFICIENTS = {
    "urban_continuous": 0.85,
    "urban_discontinuous": 0.65,
    "industrial_commercial": 0.90,
    "road_transport": 0.95,
    "port_areas": 0.80,
    "airports": 0.75,
    "mineral_extraction": 0.30,
    "dump_sites": 0.40,
    "construction_sites": 0.50,
    "green_urban_areas": 0.15,
    "sport_leisure": 0.25,
    "non_irrigated_arable": 0.02,
    "irrigated_arable": 0.02,
    "rice_fields": 0.02,
    "vineyards": 0.05,
    "fruit_trees": 0.05,
    "olive_groves": 0.05,
    "pastures": 0.02,
    "agriculture_natural_mixed": 0.05,
    "complex_cultivation": 0.08,
    "agriculture_natural_areas": 0.03,
    "agro_forestry": 0.03,
    "broad_leaved_forest": 0.01,
    "coniferous_forest": 0.01,
    "mixed_forest": 0.01,
    "natural_grasslands": 0.01,
    "moors_heathland": 0.01,
    "sclerophyllous_vegetation": 0.02,
    "transitional_woodland": 0.02,
    "beaches_dunes": 0.05,
    "bare_rocks": 0.10,
    "sparsely_vegetated": 0.05,
    "burnt_areas": 0.03,
    "glaciers_snow": 0.00,
    "inland_marshes": 0.00,
    "peat_bogs": 0.00,
    "salt_marshes": 0.00,
    "salines": 0.00,
    "intertidal_flats": 0.00,
    "water_courses": 0.00,
    "water_bodies": 0.00,
    "coastal_lagoons": 0.00,
    "estuaries": 0.00,
    "sea_ocean": 0.00
}

# =============================================================================
# Grouped Land Use Categories for UHI Analysis
# =============================================================================

# Gruppierung der CORINE-Kategorien in 6 Hauptkategorien für UHI-Analyse
CORINE_GROUPED_CATEGORIES = {
    # Hochversiegelte urbane Bereiche (sehr hoher UHI-Effekt)
    "high_density_urban": [
        "urban_continuous",
        "industrial_commercial", 
        "road_transport",
        "port_areas",
        "airports"
    ],
    
    # Niedrigversiegelte urbane Bereiche (mittlerer UHI-Effekt)
    "low_density_urban": [
        "urban_discontinuous",
        "mineral_extraction",
        "dump_sites", 
        "construction_sites"
    ],
    
    # Urbane Grünflächen (kühlender Effekt)
    "urban_green": [
        "green_urban_areas",
        "sport_leisure"
    ],
    
    # Landwirtschaftliche Flächen (neutraler bis leicht kühlender Effekt)
    "agricultural": [
        "non_irrigated_arable",
        "irrigated_arable",
        "rice_fields",
        "vineyards", 
        "fruit_trees",
        "olive_groves",
        "pastures",
        "agriculture_natural_mixed",
        "complex_cultivation",
        "agriculture_natural_areas",
        "agro_forestry"
    ],
    
    # Natürliche Vegetation (starker kühlender Effekt)
    "natural_vegetation": [
        "broad_leaved_forest",
        "coniferous_forest",
        "mixed_forest",
        "natural_grasslands",
        "moors_heathland",
        "sclerophyllous_vegetation",
        "transitional_woodland"
    ],
    
    # Wasserflächen und natürliche offene Bereiche (starker kühlender Effekt)
    "water_and_natural": [
        "beaches_dunes",
        "bare_rocks", 
        "sparsely_vegetated",
        "burnt_areas",
        "glaciers_snow",
        "inland_marshes",
        "peat_bogs",
        "salt_marshes",
        "salines",
        "intertidal_flats",
        "water_courses",
        "water_bodies",
        "coastal_lagoons",
        "estuaries",
        "sea_ocean"
    ]
}

# Mapping von detaillierten zu gruppierten Kategorien
CORINE_DETAILED_TO_GROUPED = {}
for group_name, detailed_categories in CORINE_GROUPED_CATEGORIES.items():
    for detailed_cat in detailed_categories:
        CORINE_DETAILED_TO_GROUPED[detailed_cat] = group_name

# Versiegelungskoeffizienten für die gruppierten Kategorien 
# (gewichteter Durchschnitt basierend auf typischen Verteilungen)
CORINE_GROUPED_IMPERVIOUS_COEFFICIENTS = {
    "high_density_urban": 0.88,     # Sehr hoch versiegelt
    "low_density_urban": 0.56,      # Mittlere Versiegelung  
    "urban_green": 0.18,            # Niedrige Versiegelung
    "agricultural": 0.04,           # Sehr niedrige Versiegelung
    "natural_vegetation": 0.01,     # Praktisch unversiegelt
    "water_and_natural": 0.02       # Praktisch unversiegelt
}

# Beschreibungen der gruppierten Kategorien für Reports
CORINE_GROUPED_DESCRIPTIONS = {
    "high_density_urban": "Hochversiegelte urbane Bereiche (Stadtzentren, Industrie, Verkehr)",
    "low_density_urban": "Niedrigversiegelte urbane Bereiche (Vororte, Baustellen)",
    "urban_green": "Urbane Grünflächen (Parks, Sportanlagen)",
    "agricultural": "Landwirtschaftliche Flächen (Felder, Weiden, Plantagen)",
    "natural_vegetation": "Natürliche Vegetation (Wälder, Grasland)",
    "water_and_natural": "Wasserflächen und natürliche offene Bereiche"
}

# =============================================================================
# DWD Weather Service Configuration
# =============================================================================

# DWD Settings für wetterdienst
DWD_SETTINGS = {
    "ts_shape": "long",  # Tidy data format
    "ts_humanize": True,  # User-friendly parameter names
    "ts_convert_units": True,  # Convert units to SI
}

# Temperaturparameter für DWD-Abfragen
DWD_TEMPERATURE_PARAMETERS = [("hourly", "temperature_air", "temperature_air_mean_2m")]

# Interpolation und Buffer-Konfiguration
DWD_BUFFER_DISTANCE = 5000  # Buffer distance in meters to extend the geometry
DWD_INTERPOLATION_RESOLUTION = 30  # Resolution of the interpolation grid in meters
DWD_INTERPOLATION_METHOD = "linear"  # Interpolation method ('linear', 'nearest', 'cubic')
DWD_INTERPOLATE_BY_DEFAULT = True  # Perform interpolation by default



# =============================================================================
# Performance Configuration
# =============================================================================

# Central Cache Configuration
UHI_CACHE_DIR = Path(__file__).parent.parent / "webapp" / "backend" / "cache"  # Central cache directory
UHI_CACHE_MAX_AGE_DAYS = 30  # Maximum age for cached items
UHI_CACHE_MAX_SIZE_GB = 5.0  # Maximum total cache size in GB
UHI_CACHE_ENABLED = True  # Enable caching by default

# Performance Modes for different use cases (KEEP - used by calling functions)
UHI_PERFORMANCE_MODES = {
    # Webapp preview mode - fast but lower resolution
    "preview": {
        "grid_cell_size": 300,           # Larger cells for speed
        "cloud_cover_threshold": 40,     # More lenient cloud filtering
        "hotspot_threshold": 0.85,       # Slightly lower threshold
        "min_cluster_size": 3,           # Smaller minimum clusters
        "skip_temporal_trends": True,    # Skip time-consuming temporal analysis
        "max_pixels": 5e8,              # Reduced pixel limit
        "batch_size": 1000,             # Smaller batches
        "use_fast_analyzer": True        # Use FastUrbanHeatIslandAnalyzer
    },
    
    # Fast mode - balanced speed and quality
    "fast": {
        "grid_cell_size": 200,           # Medium resolution
        "cloud_cover_threshold": 30,     # Balanced cloud filtering
        "hotspot_threshold": 0.9,        # Standard threshold
        "min_cluster_size": 5,           # Standard clusters
        "skip_temporal_trends": False,   # Include temporal analysis
        "max_pixels": 1e9,              # Standard pixel limit
        "batch_size": 3000,             # Medium batches
        "use_fast_analyzer": True        # Use FastUrbanHeatIslandAnalyzer
    },
    
    # Standard mode - default settings
    "standard": {
        "grid_cell_size": 100,           # Standard resolution
        "cloud_cover_threshold": 20,     # Standard cloud filtering
        "hotspot_threshold": 0.9,        # Standard threshold
        "min_cluster_size": 5,           # Standard clusters
        "skip_temporal_trends": False,   # Include temporal analysis
        "max_pixels": 1e9,              # Standard pixel limit
        "batch_size": 5000,             # Standard batches
        "use_fast_analyzer": False       # Use regular analyzer for comparison
    },
    
    # High quality mode - detailed analysis
    "detailed": {
        "grid_cell_size": 50,            # High resolution
        "cloud_cover_threshold": 20,     # Reasonable cloud filtering
        "hotspot_threshold": 0.95,       # High threshold
        "min_cluster_size": 10,          # Larger minimum clusters
        "skip_temporal_trends": False,   # Include temporal analysis
        "max_pixels": 2e9,              # Higher pixel limit
        "batch_size": 2000,             # Smaller batches for precision
        "use_fast_analyzer": False       # Use regular analyzer for highest quality
    }
}

# =============================================================================
# UHI Analyzer Configuration
# =============================================================================

# Google Earth Engine Configuration
UHI_EARTH_ENGINE_PROJECT = os.getenv("UHI_EARTH_ENGINE_PROJECT", "your-gee-project-id")  # GEE project ID from environment

# Satellite Data Configuration
UHI_CLOUD_COVER_THRESHOLD = 20  # Maximum acceptable cloud cover percentage (0-100)
UHI_LANDSAT_COLLECTION = "LANDSAT/LC08/C02/T1_L2"  # Landsat 8 Collection 2 Tier 1 Level 2
UHI_TEMPERATURE_BAND = "ST_B10"  # Surface temperature band
UHI_SCALE = 30  # Analysis scale in meters
UHI_MAX_PIXELS = 1e9  # Maximum pixels for Earth Engine operations

# Temperature Conversion Parameters (Landsat 8)
UHI_TEMP_MULTIPLIER = 0.00341802  # Temperature conversion multiplier
UHI_TEMP_ADDEND = 149.0  # Temperature conversion addend
UHI_KELVIN_OFFSET = 273.15  # Kelvin to Celsius conversion

# Analysis Grid Configuration
UHI_GRID_CELL_SIZE = 100  # Analysis grid cell size in meters

# Hotspot Analysis Configuration
UHI_HOTSPOT_THRESHOLD = 0.9  # Percentile threshold for hotspot identification
UHI_MIN_CLUSTER_SIZE = 5  # Minimum number of cells for a valid hotspot cluster
UHI_MORAN_SIGNIFICANCE = 0.05  # Significance level for Moran's I test

# Statistical Analysis Configuration
UHI_PERCENTILES = [10, 25, 50, 75, 90]  # Percentiles for temperature statistics
UHI_CORRELATION_THRESHOLD = 0.5  # Threshold for significant land use correlations

# Visualization Configuration
UHI_VISUALIZATION_DPI = 300  # DPI for saved visualizations
UHI_VISUALIZATION_FIGSIZE = (15, 15)  # Figure size for visualizations
UHI_TEMPERATURE_COLORMAP = "hot"  # Colormap for temperature visualizations

# Logging Configuration
UHI_LOG_DIR = Path("logs")  # Directory for log files
UHI_LOG_LEVEL = "INFO"  # Logging level


 