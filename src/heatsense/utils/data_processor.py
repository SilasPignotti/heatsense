"""
Data processing utilities for Urban Heat Island analysis.

This module provides specialized functions for processing geospatial data
in the context of Urban Heat Island (UHI) research. Key features include:
- CORINE Land Cover data transformation for UHI categorization
- Weather station data standardization and enhancement
- Imperviousness coefficient mapping for thermal analysis

Dependencies:
    - geopandas: Geospatial data operations
    - logging: Standardized logging functionality
"""

import logging
from typing import Optional

import geopandas as gpd

logger = logging.getLogger(__name__)

# CORINE Land Cover code mapping to UHI analysis categories
# Based on European Environment Agency CORINE Land Cover nomenclature
CORINE_TO_UHI_MAPPING = {
    # Urban fabric - high imperviousness
    111: "dense_urban",        # Continuous urban fabric
    121: "dense_urban",        # Industrial or commercial units
    
    # Residential areas - medium imperviousness
    112: "residential",        # Discontinuous urban fabric
    
    # Transport infrastructure - very high imperviousness
    122: "transport",          # Road and rail networks
    123: "transport",          # Port areas
    124: "transport",          # Airports
    
    # Industrial areas - high imperviousness
    131: "industrial",         # Mineral extraction sites
    132: "industrial",         # Dump sites
    133: "industrial",         # Construction sites
    
    # Urban green spaces - low imperviousness
    141: "urban_green",        # Green urban areas
    142: "urban_green",        # Sport and leisure facilities
    
    # Agricultural areas - very low imperviousness
    211: "agriculture",        # Non-irrigated arable land
    212: "agriculture",        # Permanently irrigated land
    213: "agriculture",        # Rice fields
    221: "agriculture",        # Vineyards
    222: "agriculture",        # Fruit trees and berry plantations
    223: "agriculture",        # Olive groves
    231: "agriculture",        # Pastures
    241: "agriculture",        # Annual crops associated with permanent crops
    242: "agriculture",        # Complex cultivation patterns
    243: "agriculture",        # Land principally occupied by agriculture
    244: "agriculture",        # Agro-forestry areas
    
    # Forest and semi-natural areas - minimal imperviousness
    311: "forest",             # Broad-leaved forest
    312: "forest",             # Coniferous forest
    313: "forest",             # Mixed forest
    321: "natural",            # Natural grasslands
    322: "natural",            # Moors and heathland
    323: "natural",            # Sclerophyllous vegetation
    324: "natural",            # Transitional woodland-shrub
    
    # Water bodies - zero imperviousness
    411: "water",              # Inland marshes
    412: "water",              # Peat bogs
    421: "water",              # Salt marshes
    422: "water",              # Salines
    423: "water",              # Intertidal flats
    511: "water",              # Water courses
    512: "water",              # Water bodies
    521: "water",              # Coastal lagoons
    522: "water",              # Estuaries
    523: "water",              # Sea and ocean
    
    # Open areas - low imperviousness
    331: "open_areas",         # Beaches, dunes, sands
    332: "open_areas",         # Bare rocks
    333: "open_areas",         # Sparsely vegetated areas
    334: "open_areas",         # Burnt areas
    335: "open_areas"          # Glaciers and perpetual snow
}

# Imperviousness coefficients for UHI categories
# Values represent fraction of impervious surface (0.0 to 1.0)
UHI_IMPERVIOUSNESS_COEFFICIENTS = {
    "dense_urban": 0.90,       # City centers, industrial areas
    "residential": 0.65,       # Suburban residential areas
    "industrial": 0.85,        # Industrial zones
    "transport": 0.95,         # Roads, railways, airports
    "urban_green": 0.15,       # Parks, sports facilities
    "agriculture": 0.05,       # Farmland, crops
    "forest": 0.02,            # Forests, natural vegetation
    "natural": 0.03,           # Grasslands, heathland
    "water": 0.00,             # Water bodies
    "open_areas": 0.05         # Beaches, bare rock
}

# Human-readable descriptions for UHI categories
UHI_CATEGORY_DESCRIPTIONS = {
    "dense_urban": "Dense Urban Development",
    "residential": "Residential Areas",
    "industrial": "Industrial Areas", 
    "transport": "Transport Infrastructure",
    "urban_green": "Urban Green Spaces",
    "agriculture": "Agricultural Areas",
    "forest": "Forest Areas",
    "natural": "Natural Vegetation",
    "water": "Water Bodies",
    "open_areas": "Natural Open Areas"
}


def process_corine_for_uhi(
    corine_gdf: gpd.GeoDataFrame,
    logger_instance: Optional[logging.Logger] = None
) -> gpd.GeoDataFrame:
    """
    Transform CORINE Land Cover data for Urban Heat Island analysis.
    
    Maps land cover codes to UHI categories and adds imperviousness coefficients.
    Handles various CORINE column naming conventions automatically.
    
    Args:
        corine_gdf: GeoDataFrame with CORINE land cover data
        logger_instance: Optional logger for processing information
        
    Returns:
        Enhanced GeoDataFrame with landuse_category, landuse_description, 
        and imperviousness_coefficient columns
        
    Raises:
        ValueError: If no valid CORINE code column is found
    """
    if logger_instance:
        logger_instance.info("Starting CORINE Land Cover processing for UHI analysis")
    else:
        logger.info("Starting CORINE Land Cover processing for UHI analysis")
    
    processed_gdf = corine_gdf.copy()
    
    # Search for CORINE code column - various naming conventions exist
    possible_code_columns = [
        'Code_18', 'CODE_18', 'corine_code', 'Code_12', 'CODE_12',
        'Code_06', 'CODE_06', 'CODE_00', 'CODE_90', 'gridcode', 'GRIDCODE'
    ]
    
    code_column = None
    for column_name in possible_code_columns:
        if column_name in processed_gdf.columns:
            code_column = column_name
            break
    
    if code_column is None:
        available_columns = list(processed_gdf.columns)
        error_msg = f"No CORINE code column found. Available columns: {available_columns}"
        if logger_instance:
            logger_instance.error(error_msg)
        else:
            logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Standardize code column and apply UHI mapping
    processed_gdf['corine_code'] = processed_gdf[code_column].astype(int)
    processed_gdf['landuse_category'] = processed_gdf['corine_code'].map(CORINE_TO_UHI_MAPPING)
    processed_gdf['landuse_description'] = processed_gdf['landuse_category'].map(UHI_CATEGORY_DESCRIPTIONS)
    processed_gdf['imperviousness_coefficient'] = processed_gdf['landuse_category'].map(UHI_IMPERVIOUSNESS_COEFFICIENTS)
    
    # Handle unmapped CORINE codes
    unmapped_mask = processed_gdf['landuse_category'].isna()
    if unmapped_mask.any():
        unmapped_codes = processed_gdf.loc[unmapped_mask, 'corine_code'].unique()
        
        # Assign default values for unmapped codes
        processed_gdf.loc[unmapped_mask, 'landuse_category'] = 'unknown'
        processed_gdf.loc[unmapped_mask, 'landuse_description'] = 'Unknown Land Use'
        processed_gdf.loc[unmapped_mask, 'imperviousness_coefficient'] = 0.5
        
        warning_msg = f"Unmapped CORINE codes found: {unmapped_codes}. Assigned default values."
        if logger_instance:
            logger_instance.warning(warning_msg)
        else:
            logger.warning(warning_msg)
    
    # Log processing summary
    total_features = len(processed_gdf)
    category_count = len(processed_gdf['landuse_category'].value_counts())
    summary_msg = f"Processed {total_features} features into {category_count} UHI categories"
    
    if logger_instance:
        logger_instance.info(summary_msg)
    else:
        logger.info(summary_msg)
    
    return processed_gdf


def standardize_weather_data(
    weather_gdf: gpd.GeoDataFrame,
    logger_instance: Optional[logging.Logger] = None
) -> gpd.GeoDataFrame:
    """Standardize weather station data with consistent temperature column naming."""
    if logger_instance:
        logger_instance.info("Standardizing weather station data for UHI analysis")
    else:
        logger.info("Standardizing weather station data for UHI analysis")
    
    standardized_gdf = weather_gdf.copy()
    
    # Search for temperature column - various naming conventions
    possible_temperature_columns = [
        'temperature', 'temp', 'ground_temp', 'air_temperature', 
        'mean_temp', 'avg_temp', 'value', 'measurement'
    ]
    
    if 'temperature' not in standardized_gdf.columns:
        temperature_column = None
        for column_name in possible_temperature_columns:
            if column_name in standardized_gdf.columns:
                temperature_column = column_name
                break
        
        if temperature_column:
            standardized_gdf['temperature'] = standardized_gdf[temperature_column]
            info_msg = f"Using '{temperature_column}' as standardized temperature column"
            if logger_instance:
                logger_instance.info(info_msg)
            else:
                logger.info(info_msg)
        else:
            available_columns = list(standardized_gdf.columns)
            warning_msg = f"No temperature column found. Available columns: {available_columns}"
            if logger_instance:
                logger_instance.warning(warning_msg)
            else:
                logger.warning(warning_msg)
    
    if logger_instance:
        logger_instance.info(f"Standardized {len(standardized_gdf)} weather station records")
    else:
        logger.info(f"Standardized {len(standardized_gdf)} weather station records")
    
    return standardized_gdf