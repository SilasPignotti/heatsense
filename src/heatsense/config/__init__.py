"""
Configuration settings for HeatSense Urban Heat Island analysis.

This module provides centralized configuration constants for coordinate systems,
external service endpoints, and performance optimization parameters.
"""

from .settings import (
    BERLIN_WFS_ENDPOINTS,
    BERLIN_WFS_FEATURE_TYPES,
    CORINE_BASE_URLS,
    CORINE_YEARS,
    CRS_CONFIG,
    DWD_SETTINGS,
    DWD_TEMPERATURE_PARAMETERS,
    UHI_EARTH_ENGINE_PROJECT,
    UHI_LOG_DIR,
    UHI_LOG_LEVEL,
    UHI_PERFORMANCE_MODES,
)

__all__ = [
    "CRS_CONFIG",
    "BERLIN_WFS_ENDPOINTS",
    "BERLIN_WFS_FEATURE_TYPES",
    "CORINE_BASE_URLS",
    "CORINE_YEARS",
    "DWD_SETTINGS",
    "DWD_TEMPERATURE_PARAMETERS",
    "UHI_EARTH_ENGINE_PROJECT",
    "UHI_LOG_DIR",
    "UHI_LOG_LEVEL",
    "UHI_PERFORMANCE_MODES",
] 