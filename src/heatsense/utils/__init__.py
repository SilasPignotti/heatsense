"""
Data processing utilities for Urban Heat Island analysis.

This module provides functions for processing and transforming geospatial data
used in UHI analysis, including CORINE Land Cover data and weather station data.
"""

from heatsense.utils.data_processor import (
    UHI_CATEGORY_DESCRIPTIONS,
    UHI_IMPERVIOUSNESS_COEFFICIENTS,
    process_corine_for_uhi,
    standardize_weather_data,
)

__all__ = [
    'process_corine_for_uhi',
    'standardize_weather_data',
    'UHI_CATEGORY_DESCRIPTIONS',
    'UHI_IMPERVIOUSNESS_COEFFICIENTS'
] 