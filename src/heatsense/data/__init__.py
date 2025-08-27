"""
Data acquisition and analysis modules for Urban Heat Island research.

This module provides classes for downloading geospatial data from various sources
and the main Urban Heat Island analysis engine.
"""

from .corine_downloader import CorineDataDownloader
from .dwd_downloader import DWDDataDownloader
from .urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
from .wfs_downloader import WFSDataDownloader

__all__ = [
    "CorineDataDownloader",
    "DWDDataDownloader", 
    "UrbanHeatIslandAnalyzer",
    "WFSDataDownloader",
] 