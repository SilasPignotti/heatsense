"""
Analyzer factory for creating the appropriate UHI analyzer based on configuration.

This module provides a factory function to choose between regular and fast analyzers
based on performance mode settings.
"""

from typing import Union, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from ..data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
    from ..data.fast_urban_heat_island_analyzer import FastUrbanHeatIslandAnalyzer

from ..config.settings import UHI_PERFORMANCE_MODES, UHI_CACHE_DIR


def create_analyzer(
    performance_mode: Optional[str] = None,
    cache_dir: Union[str, Path] = None,
    max_cache_age_days: int = 30,
    **kwargs
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
            from ..data.fast_urban_heat_island_analyzer import FastUrbanHeatIslandAnalyzer
            return FastUrbanHeatIslandAnalyzer(
                performance_mode=performance_mode,
                cache_dir=cache_dir or UHI_CACHE_DIR,
                max_cache_age_days=max_cache_age_days,
                **kwargs
            )
        else:
            # Use regular analyzer for highest quality modes
            from ..data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
            
            # Apply mode defaults, but allow kwargs to override
            analyzer_kwargs = {
                'cloud_cover_threshold': mode_config.get('cloud_cover_threshold', 20),
                'grid_cell_size': mode_config.get('grid_cell_size', 100),
                'hotspot_threshold': mode_config.get('hotspot_threshold', 0.9),
                'min_cluster_size': mode_config.get('min_cluster_size', 5),
            }
            # Override with any custom values from kwargs
            analyzer_kwargs.update(kwargs)
            
            return UrbanHeatIslandAnalyzer(**analyzer_kwargs)
    else:
        # Default to fast analyzer if no mode specified
        from ..data.fast_urban_heat_island_analyzer import FastUrbanHeatIslandAnalyzer
        return FastUrbanHeatIslandAnalyzer(
            cache_dir=cache_dir or UHI_CACHE_DIR,
            max_cache_age_days=max_cache_age_days,
            **kwargs
        )


def get_analyzer_recommendation(area_km2: float) -> str:
    """
    Get recommended performance mode based on analysis area size.
    
    Args:
        area_km2: Analysis area in square kilometers
        
    Returns:
        Recommended performance mode
    """
    if area_km2 < 50:
        return "detailed"    # Small areas can handle high resolution
    elif area_km2 < 200:
        return "standard"    # Medium areas use standard settings
    elif area_km2 < 500:
        return "fast"        # Large areas need performance optimization
    else:
        return "preview"     # Very large areas need maximum optimization


def list_performance_modes() -> dict:
    """
    List all available performance modes with their configurations.
    
    Returns:
        Dictionary of performance modes and their settings
    """
    return {
        mode: {
            "grid_size_m": config["grid_cell_size"],
            "cloud_threshold_pct": config["cloud_cover_threshold"],
            "uses_fast_analyzer": config.get("use_fast_analyzer", True),
            "skips_temporal": config.get("skip_temporal_trends", False),
            "recommended_for": _get_mode_recommendation(mode)
        }
        for mode, config in UHI_PERFORMANCE_MODES.items()
    }


def _get_mode_recommendation(mode: str) -> str:
    """Get recommendation text for a performance mode."""
    recommendations = {
        "preview": "Web previews, very large areas (>500 km²)",
        "fast": "Interactive analysis, large areas (200-500 km²)",
        "standard": "Balanced analysis, medium areas (50-200 km²)",
        "detailed": "High-quality analysis, small areas (<50 km²)"
    }
    return recommendations.get(mode, "General purpose") 