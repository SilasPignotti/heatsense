"""
Analyzer factory for creating the appropriate UHI analyzer based on configuration.

This module provides a factory function to choose between regular and fast analyzers
based on performance mode settings.
"""

from typing import Union, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from uhi_analyzer.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
    from uhi_analyzer.data.fast_urban_heat_island_analyzer import FastUrbanHeatIslandAnalyzer

from uhi_analyzer.config.settings import UHI_PERFORMANCE_MODES, UHI_CACHE_DIR, UHI_CACHE_MAX_AGE_DAYS


def create_analyzer(
    performance_mode: Optional[str] = None
) -> Union["UrbanHeatIslandAnalyzer", "FastUrbanHeatIslandAnalyzer"]:
    """
    Create the appropriate UHI analyzer based on performance mode configuration.
    
    Args:
        performance_mode: Performance mode ('preview', 'fast', 'standard', 'detailed')
        cache_dir: Directory for cache files (only used for FastUrbanHeatIslandAnalyzer)
        max_cache_age_days: Maximum age for cached items
        **kwargs: Additional arguments for analyzer initialization
        
    Returns:
        Configured analyzer instance (either regular or fast)
    """
    if performance_mode and performance_mode in UHI_PERFORMANCE_MODES:
        mode_config = UHI_PERFORMANCE_MODES[performance_mode]
        use_fast_analyzer = mode_config.get('use_fast_analyzer', True)
        
        if use_fast_analyzer:
            # Import here to avoid circular import
            from uhi_analyzer.data.fast_urban_heat_island_analyzer import FastUrbanHeatIslandAnalyzer
            return FastUrbanHeatIslandAnalyzer(
                performance_mode=performance_mode,
                cache_dir=UHI_CACHE_DIR,
                max_cache_age_days=UHI_CACHE_MAX_AGE_DAYS
            )
        else:
            # Use regular analyzer for highest quality modes
            from uhi_analyzer.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
            
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
        # Default to fast analyzer if no mode specified
        from uhi_analyzer.data.fast_urban_heat_island_analyzer import FastUrbanHeatIslandAnalyzer
        return FastUrbanHeatIslandAnalyzer(
            cache_dir=UHI_CACHE_DIR,
            max_cache_age_days=UHI_CACHE_MAX_AGE_DAYS
        ) 