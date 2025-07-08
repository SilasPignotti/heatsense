"""
Analyzer factory for creating the appropriate UHI analyzer based on configuration.

This module provides a factory function to choose between regular and fast analyzers
based on performance mode settings.
"""

from typing import Union, Optional


from uhi_analyzer.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer

from uhi_analyzer.config.settings import UHI_PERFORMANCE_MODES


def create_analyzer(
    performance_mode: Optional[str] = None
) -> Union["UrbanHeatIslandAnalyzer"]:
    """
    Create the appropriate UHI analyzer based on performance mode configuration.
    
    Args:
        performance_mode: Performance mode ('preview', 'fast', 'standard', 'detailed')
        
    Returns:
        Configured analyzer instance
    """
    if performance_mode and performance_mode in UHI_PERFORMANCE_MODES:
        mode_config = UHI_PERFORMANCE_MODES[performance_mode]
        
        # Apply mode defaults
        analyzer_kwargs = {
                'cloud_cover_threshold': mode_config.get('cloud_cover_threshold', 20),
                'grid_cell_size': mode_config.get('grid_cell_size', 100),
                'hotspot_threshold': mode_config.get('hotspot_threshold', 0.9),
                'min_cluster_size': mode_config.get('min_cluster_size', 5),
                'skip_temporal_trends': mode_config.get('skip_temporal_trends', False),
            }
            
        return UrbanHeatIslandAnalyzer(**analyzer_kwargs)
    else:
        raise ValueError(f"Invalid performance mode: {performance_mode}")