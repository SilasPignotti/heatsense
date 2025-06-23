"""Configuration module for the Urban Heat Island Analyzer."""

from .settings import *
from .credentials import *

__all__ = [
    # Settings
    "WFS_ENDPOINTS",
    "WFS_HEADERS", 
    "WFS_TIMEOUT",
    "CORINE_BASE_URL",
    "DEFAULT_RECORD_COUNT",
    "DEFAULT_TIMEOUT",
    "DEFAULT_OUTPUT_FORMAT",
    "DEFAULT_OUTPUT_CRS",
    "DEFAULT_INPUT_CRS"
] 