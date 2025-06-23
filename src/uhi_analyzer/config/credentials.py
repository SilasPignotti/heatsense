"""
Credentials and API key management for the Urban Heat Island Analyzer.

This module handles loading and managing API credentials and keys
for various data sources used in the UHI analysis.
"""

import os
from pathlib import Path
from typing import Optional


# =============================================================================
# Environment-specific Configuration
# =============================================================================

def is_development() -> bool:
    """Check if running in development environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "development"

def is_production() -> bool:
    """Check if running in production environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"

def get_data_dir() -> Path:
    """Get the data directory path."""
    return Path("data")

def get_logs_dir() -> Path:
    """Get the logs directory path."""
    return Path("logs")

def get_results_dir() -> Path:
    """Get the results directory path."""
    return Path("results") 