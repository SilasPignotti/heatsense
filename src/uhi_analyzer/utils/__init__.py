"""
Utility modules for the Urban Heat Island Analyzer.

This package contains utility functions and setup scripts for the UHI analyzer.
"""

from .setup_earth_engine import authenticate_earth_engine, check_earth_engine_installed

__all__ = ['authenticate_earth_engine', 'check_earth_engine_installed'] 