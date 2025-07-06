"""
Corine Data Processing Utilities for Urban Heat Island Analysis.

This module provides functions for processing Corine Land Cover data
specifically for Urban Heat Island analysis.
"""

from typing import Optional
import pandas as pd
import geopandas as gpd
import numpy as np
import logging

# Corine Land Cover Code to Land Use Type Mapping
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

# Impervious Area Coefficients for different Land Use Types
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

# Grouping of CORINE categories into 6 main categories for UHI analysis
CORINE_GROUPED_CATEGORIES = {
    # High-density urban areas (very high UHI effect)
    "high_density_urban": [
        "urban_continuous",
        "industrial_commercial", 
        "road_transport",
        "port_areas",
        "airports"
    ],
    
    # Low-density urban areas (medium UHI effect)
    "low_density_urban": [
        "urban_discontinuous",
        "mineral_extraction",
        "dump_sites", 
        "construction_sites"
    ],
    
    # Urban green areas (cooling effect)
    "urban_green": [
        "green_urban_areas",
        "sport_leisure"
    ],
    
    # Agricultural areas (neutral to slightly cooling effect)
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
    
    # Natural vegetation (strong cooling effect)
    "natural_vegetation": [
        "broad_leaved_forest",
        "coniferous_forest",
        "mixed_forest",
        "natural_grasslands",
        "moors_heathland",
        "sclerophyllous_vegetation",
        "transitional_woodland"
    ],
    
    # Water bodies and natural open areas (strong cooling effect)
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

# Descriptions of grouped categories for reports
CORINE_GROUPED_DESCRIPTIONS = {
    "high_density_urban": "High-density urban areas (city centers, industry, transport)",
    "low_density_urban": "Low-density urban areas (suburbs, construction sites)",
    "urban_green": "Urban green areas (parks, sports facilities)",
    "agricultural": "Agricultural areas (fields, pastures, plantations)",
    "natural_vegetation": "Natural vegetation (forests, grasslands)",
    "water_and_natural": "Water bodies and natural open areas"
}

def process_corine_for_uhi(
    gdf: gpd.GeoDataFrame,
    logger: Optional[logging.Logger] = None,
    group_landuse: bool = True
) -> gpd.GeoDataFrame:
    """
    Process Corine Land Cover data for Urban Heat Island analysis.
    
    This function adds UHI-specific columns:
    - landuse_type: Categorical classification of land use
    - impervious_area: Numeric coefficient for impervious surfaces (0.0-1.0)
    
    Args:
        gdf: GeoDataFrame with Corine data (must have 'corine_code' column)
        logger: Optional logger instance
        
    Returns:
        GeoDataFrame with UHI-specific columns
        
    Raises:
        ValueError: If required 'corine_code' column is missing
    """
    if 'corine_code' not in gdf.columns:
        raise ValueError("GeoDataFrame must have a 'corine_code' column")
    
    # Create a copy to avoid modifying the original
    result_gdf = gdf.copy()
    
    # Add landuse_type column
    result_gdf['landuse_type'] = result_gdf['corine_code'].map(CORINE_LANDUSE_MAPPING)
    
    # Handle unknown codes
    unknown_codes = result_gdf[result_gdf['landuse_type'].isna()]['corine_code'].unique()
    if len(unknown_codes) > 0:
        if logger:
            logger.warning(f"Unknown Corine codes found: {unknown_codes}")
        result_gdf['landuse_type'] = result_gdf['landuse_type'].fillna('unknown')
    
    # Add impervious_area column
    result_gdf['impervious_area'] = result_gdf['landuse_type'].map(CORINE_IMPERVIOUS_COEFFICIENTS)
    result_gdf['impervious_area'] = result_gdf['impervious_area'].fillna(0.0)
    
    if group_landuse:
        result_gdf['landuse_type'] = result_gdf['landuse_type'].map(CORINE_DETAILED_TO_GROUPED)
        result_gdf['impervious_area'] = result_gdf['landuse_type'].map(CORINE_GROUPED_IMPERVIOUS_COEFFICIENTS)
    
    # Keep only relevant columns for UHI analysis
    essential_columns = ['geometry', 'landuse_type', 'impervious_area', 'corine_code']
    
    return result_gdf[essential_columns]

def enhance_weather_data_for_uhi(
    weather_data: gpd.GeoDataFrame,
    logger: Optional[logging.Logger] = None
) -> gpd.GeoDataFrame:
    """
    Enhance weather data with UHI-specific columns for analysis.
    
    Adds the following columns to the weather data:
    - temperature_category: Categorical temperature classification
    - heat_stress_potential: Heat stress indicator based on temperature thresholds
    - measurement_quality: Quality indicator based on data source and statistics
    - grid_id: Grid identifier for interpolated data
    
    Args:
        weather_data: GeoDataFrame containing weather data with temperature information
        logger: Optional logger for status messages
        
    Returns:
        Enhanced GeoDataFrame with UHI-specific columns added
    """
    if weather_data.empty:
        if logger:
            logger.warning("Empty weather data provided to enhance_weather_data_for_uhi")
        return weather_data
    
    if logger:
        logger.info("Enhancing weather data with UHI-specific columns")
    
    result_gdf = weather_data.copy()
    
    # Add temperature categories for UHI analysis
    if 'ground_temp' in result_gdf.columns:
        result_gdf['temperature_category'] = pd.cut(
            result_gdf['ground_temp'],
            bins=[-np.inf, 0, 10, 20, 30, np.inf],
            labels=['very_cold', 'cold', 'moderate', 'warm', 'hot']
        )
        
        # Heat stress potential (relevant for UHI studies)
        result_gdf['heat_stress_potential'] = pd.cut(
            result_gdf['ground_temp'],
            bins=[-np.inf, 15, 25, 30, 35, np.inf],
            labels=['low', 'moderate', 'high', 'very_high', 'extreme']
        )
    
    # Add measurement quality indicator
    result_gdf['measurement_quality'] = 'unknown'
    
    if 'temp_std' in result_gdf.columns and 'measurement_count' in result_gdf.columns:
        # Quality based on measurement count and low standard deviation
        result_gdf.loc[
            (result_gdf['measurement_count'] >= 100) & (result_gdf['temp_std'] <= 5), 
            'measurement_quality'
        ] = 'high'
        result_gdf.loc[
            (result_gdf['measurement_count'] >= 50) & (result_gdf['temp_std'] <= 8), 
            'measurement_quality'
        ] = 'medium'
        result_gdf.loc[
            result_gdf['measurement_quality'] == 'unknown', 
            'measurement_quality'
        ] = 'low'
    else:
        # Default quality for interpolated data
        result_gdf['measurement_quality'] = 'medium'
    
    # Add grid ID for interpolated data
    if 'source' in result_gdf.columns and 'interpolated' in result_gdf['source'].values:
        result_gdf['grid_id'] = range(len(result_gdf))
    
    if logger:
        logger.info(f"UHI enhancement completed for {len(result_gdf)} weather data records")
    
    return result_gdf


 