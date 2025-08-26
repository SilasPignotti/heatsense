"""
Utility functions for processing and transforming data for Urban Heat Island analysis.

This module contains various data processing functions including:
- CORINE Land Cover data processing
- Weather station data enhancement 
- GeoDataFrame transformations
- UHI-specific data preparation

Created: 2025
"""

import logging
import geopandas as gpd
import pandas as pd

# CORINE Land Cover Code zu Deutsche UHI-Kategorien Mapping
CORINE_TO_UHI_MAPPING = {
    # Dichte städtische Bebauung
    111: "dichte_bebauung",     # Durchgängig städtische Prägung
    121: "dichte_bebauung",     # Industrie- und Gewerbeflächen
    
    # Wohngebiete
    112: "wohngebiete",         # Nicht durchgängig städtische Prägung
    
    # Industrie- und Verkehrsflächen
    122: "verkehrsflaechen",    # Straßen- und Eisenbahnnetze
    123: "verkehrsflaechen",    # Hafengebiete
    124: "verkehrsflaechen",    # Flughäfen
    131: "industrie",           # Abbauflächen
    132: "industrie",           # Deponien und Abraumhalden
    133: "industrie",           # Baustellen
    
    # Städtisches Grün
    141: "staedtisches_gruen",  # Städtische Grünflächen
    142: "staedtisches_gruen",  # Sport- und Freizeitanlagen
    
    # Landwirtschaft
    211: "landwirtschaft",      # Nicht bewässerte Ackerflächen
    212: "landwirtschaft",      # Bewässerte Ackerflächen
    213: "landwirtschaft",      # Reisfelder
    221: "landwirtschaft",      # Weinbauflächen
    222: "landwirtschaft",      # Obst- und Beerenobstbestände
    223: "landwirtschaft",      # Olivenhaine
    231: "landwirtschaft",      # Wiesen und Weiden
    241: "landwirtschaft",      # Einjährige Kulturen
    242: "landwirtschaft",      # Komplexe Parzellenstruktur
    243: "landwirtschaft",      # Landwirtschaft mit Naturraum
    244: "landwirtschaft",      # Agroforst-Gebiete
    
    # Wald
    311: "wald",                # Laubwälder
    312: "wald",                # Nadelwälder
    313: "wald",                # Mischwälder
    321: "wald",                # Natürliche Grünländer
    322: "wald",                # Heiden und Moorheiden
    323: "wald",                # Sklerophylle Vegetation
    324: "wald",                # Wald-Strauch-Übergangsstadien
    
    # Wasser
    511: "wasser",              # Wasserlauf
    512: "wasser",              # Wasserflächen
    521: "wasser",              # Lagunen
    522: "wasser",              # Mündungsgebiete
    523: "wasser",              # Meere und Ozeane
    411: "wasser",              # Sümpfe
    412: "wasser",              # Torfmoore
    421: "wasser",              # Salzwiesen
    422: "wasser",              # Salinen
    423: "wasser",              # In der Gezeitenzone liegende Flächen
    
    # Natürliche offene Flächen
    331: "natuerliche_offene_flaechen",  # Strände, Dünen, Sandflächen
    332: "natuerliche_offene_flaechen",  # Felsflächen ohne Vegetation
    333: "natuerliche_offene_flaechen",  # Flächen mit spärlicher Vegetation
    334: "natuerliche_offene_flaechen",  # Brandflächen
    335: "natuerliche_offene_flaechen"   # Gletscher und Dauerschneegebiete
}

# Deutsche UHI-Kategorien mit Versiegelungsgraden
CORINE_UHI_CATEGORIES = {
    "dichte_bebauung": 0.90,        # Stadtzentren, Industrie
    "wohngebiete": 0.65,            # Vorstädte, Wohngebiete  
    "industrie": 0.85,              # Industriegebiete
    "verkehrsflaechen": 0.95,       # Straßen, Flughäfen
    "staedtisches_gruen": 0.12,     # Parks, Grünflächen
    "landwirtschaft": 0.04,         # Landwirtschaftliche Flächen
    "wald": 0.01,                   # Wälder
    "wasser": 0.00,                 # Wasserkörper
    "natuerliche_offene_flaechen": 0.03  # Natürliche nicht bewachsene Flächen
}

# Deutsche Beschreibungen für die UHI-Kategorien
CORINE_UHI_DESCRIPTIONS = {
    "dichte_bebauung": "Dichte Bebauung",
    "wohngebiete": "Wohngebiete", 
    "industrie": "Industrie- und Gewerbeflächen",
    "verkehrsflaechen": "Verkehrsflächen",
    "staedtisches_gruen": "Städtisches Grün",
    "landwirtschaft": "Landwirtschaftliche Flächen",
    "wald": "Wald und natürliche Vegetation",
    "wasser": "Gewässer",
    "natuerliche_offene_flaechen": "Natürliche offene Flächen"
}


def process_corine_for_uhi(
    corine_gdf: gpd.GeoDataFrame, 
    logger: logging.Logger = None, 
    group_landuse: bool = True, 
    add_german_descriptions: bool = True
) -> gpd.GeoDataFrame:
    """
    Process CORINE Land Cover data for UHI analysis with German categories.
    
    Args:
        corine_gdf: GeoDataFrame with CORINE data
        logger: Optional logger for debugging
        group_landuse: Always True now (kept for compatibility)
        add_german_descriptions: Always True now (kept for compatibility)
        
    Returns:
        GeoDataFrame with processed UHI categories
    """
    if logger:
        logger.info("Processing CORINE data for UHI analysis with German categories")
    
    # Make a copy to avoid modifying original
    processed_gdf = corine_gdf.copy()
    
    # Find CORINE code column
    code_cols = ['Code_18', 'CODE_18', 'corine_code', 'Code_12', 'CODE_12', 
                 'Code_06', 'CODE_06', 'CODE_00', 'CODE_90', 'gridcode', 'GRIDCODE']
    
    code_col = None
    for col in code_cols:
        if col in processed_gdf.columns:
            code_col = col
            break
    
    if code_col is None:
        if logger:
            logger.error(f"No CORINE code column found. Available: {list(processed_gdf.columns)}")
        raise ValueError("No CORINE code column found in data")
    
    # Ensure codes are integers
    processed_gdf['corine_code'] = processed_gdf[code_col].astype(int)
    
    # Map to German UHI categories
    processed_gdf['landuse_type'] = processed_gdf['corine_code'].map(CORINE_TO_UHI_MAPPING)
    
    # Add German descriptions
    processed_gdf['land_use_description'] = processed_gdf['landuse_type'].map(CORINE_UHI_DESCRIPTIONS)
    
    # Add imperviousness coefficients
    processed_gdf['impervious_area'] = processed_gdf['landuse_type'].map(CORINE_UHI_CATEGORIES)
    
    # Handle unmapped codes
    unmapped_mask = processed_gdf['landuse_type'].isna()
    if unmapped_mask.any():
        processed_gdf.loc[unmapped_mask, 'landuse_type'] = 'unbekannt'
        processed_gdf.loc[unmapped_mask, 'land_use_description'] = 'Unbekannte Landnutzung'
        processed_gdf.loc[unmapped_mask, 'impervious_area'] = 0.5  # Default value
        
        if logger:
            unmapped_codes = processed_gdf.loc[unmapped_mask, 'corine_code'].unique()
            logger.warning(f"Unmapped CORINE codes found: {unmapped_codes}")
    
    if logger:
        unique_categories = processed_gdf['landuse_type'].value_counts()
        logger.info(f"Processed {len(processed_gdf)} CORINE features into {len(unique_categories)} UHI categories")
        for category, count in unique_categories.items():
            logger.info(f"  {category}: {count} features")
    
    return processed_gdf


def enhance_weather_data_for_uhi(weather_gdf: gpd.GeoDataFrame, logger: logging.Logger = None) -> gpd.GeoDataFrame:
    """
    Enhance weather station data for UHI analysis.
    
    Args:
        weather_gdf: GeoDataFrame with weather station data
        logger: Optional logger for debugging
        
    Returns:
        Enhanced GeoDataFrame
    """
    if logger:
        logger.info("Enhancing weather data for UHI analysis")
    
    # Make a copy to avoid modifying original
    enhanced_gdf = weather_gdf.copy()
    
    # Ensure we have a ground_temp column
    temp_columns = ['ground_temp', 'temperature', 'temp', 'air_temperature', 'mean_temp', 'value']
    
    if 'ground_temp' not in enhanced_gdf.columns:
        for col in temp_columns:
            if col in enhanced_gdf.columns:
                enhanced_gdf['ground_temp'] = enhanced_gdf[col]
                if logger:
                    logger.info(f"Using column '{col}' as ground_temp")
                break
        else:
            if logger:
                logger.warning(f"No temperature column found in weather data. Available: {list(enhanced_gdf.columns)}")
    
    if logger:
        logger.info(f"Enhanced {len(enhanced_gdf)} weather station records")
    
    return enhanced_gdf