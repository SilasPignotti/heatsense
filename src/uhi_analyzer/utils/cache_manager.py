"""
Performance caching system for Urban Heat Island Analysis.

This module provides intelligent caching to dramatically improve analysis performance
by avoiding redundant API calls and computations.
"""

import hashlib
import json
import pickle
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple
import logging
import geopandas as gpd

from uhi_analyzer.config.settings import UHI_CACHE_DIR


class CacheManager:
    """
    Intelligent caching system for UHI analysis components.
    
    Caches:
    - Earth Engine collections and temperature data
    - Boundary data downloads 
    - CORINE land cover data
    - Processed analysis grids
    - Correlation calculations
    """
    
    def __init__(
        self, 
        cache_dir: Union[str, Path] = None,
        max_age_days: int = 30,
        max_cache_size_gb: float = 5.0,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files
            max_age_days: Maximum age for cached items
            max_cache_size_gb: Maximum total cache size in GB
            logger: Optional logger instance
        """
        self.cache_dir = Path(cache_dir or UHI_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = timedelta(days=max_age_days)
        self.max_size_bytes = max_cache_size_gb * 1024**3
        self.logger = logger or logging.getLogger(__name__)
        
        # Create subdirectories for different cache types
        (self.cache_dir / "earth_engine").mkdir(exist_ok=True)
        (self.cache_dir / "boundaries").mkdir(exist_ok=True)
        (self.cache_dir / "landcover").mkdir(exist_ok=True)
        (self.cache_dir / "grids").mkdir(exist_ok=True)
        (self.cache_dir / "temperatures").mkdir(exist_ok=True)
        
        self.logger.info(f"Cache manager initialized: {self.cache_dir}")
    
    def _generate_key(self, data: Dict[str, Any]) -> str:
        """Generate a unique cache key from parameters."""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(sorted_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_file: Path) -> bool:
        """Check if cache file is valid (exists and not too old)."""
        if not cache_file.exists():
            return False
        
        # Check age
        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_age > self.max_age:
            self.logger.debug(f"Cache expired: {cache_file.name}")
            return False
        
        return True
    
    def _cleanup_cache(self):
        """Remove old cache files and enforce size limits."""
        cache_files = list(self.cache_dir.rglob("*"))
        cache_files = [f for f in cache_files if f.is_file()]
        
        # Remove expired files
        for cache_file in cache_files:
            if not self._is_cache_valid(cache_file):
                try:
                    cache_file.unlink()
                    self.logger.debug(f"Removed expired cache: {cache_file.name}")
                except OSError:
                    pass
        
        # Check total size and remove oldest files if needed
        cache_files = [f for f in self.cache_dir.rglob("*") if f.is_file()]
        total_size = sum(f.stat().st_size for f in cache_files)
        
        if total_size > self.max_size_bytes:
            # Sort by modification time (oldest first)
            cache_files.sort(key=lambda f: f.stat().st_mtime)
            
            while total_size > self.max_size_bytes and cache_files:
                oldest_file = cache_files.pop(0)
                file_size = oldest_file.stat().st_size
                try:
                    oldest_file.unlink()
                    total_size -= file_size
                    self.logger.debug(f"Removed old cache file: {oldest_file.name}")
                except OSError:
                    pass
    
    # Earth Engine Data Caching
    def cache_earth_engine_collection(
        self, 
        geometry_bounds: Tuple[float, float, float, float],
        date_range: Tuple[date, date],
        cloud_threshold: float,
        data: Dict[str, Any]
    ) -> str:
        """Cache Earth Engine collection data."""
        cache_key = self._generate_key({
            'type': 'earth_engine_collection',
            'bounds': geometry_bounds,
            'start_date': date_range[0].isoformat(),
            'end_date': date_range[1].isoformat(),
            'cloud_threshold': cloud_threshold
        })
        
        cache_file = self.cache_dir / "earth_engine" / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            self.logger.debug(f"Cached Earth Engine collection: {cache_key}")
        except Exception as e:
            self.logger.warning(f"Failed to cache Earth Engine data: {e}")
        
        return cache_key
    
    def get_earth_engine_collection(
        self,
        geometry_bounds: Tuple[float, float, float, float],
        date_range: Tuple[date, date],
        cloud_threshold: float
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached Earth Engine collection data."""
        cache_key = self._generate_key({
            'type': 'earth_engine_collection',
            'bounds': geometry_bounds,
            'start_date': date_range[0].isoformat(),
            'end_date': date_range[1].isoformat(),
            'cloud_threshold': cloud_threshold
        })
        
        cache_file = self.cache_dir / "earth_engine" / f"{cache_key}.pkl"
        
        if self._is_cache_valid(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                self.logger.info(f"🚀 Using cached Earth Engine data: {cache_key[:8]}...")
                return data
            except Exception as e:
                self.logger.warning(f"Failed to load cached Earth Engine data: {e}")
        
        return None
    
    # Temperature Grid Caching
    def cache_temperature_grid(
        self,
        geometry_bounds: Tuple[float, float, float, float],
        date_range: Tuple[date, date],
        grid_size: float,
        cloud_threshold: float,
        temperature_grid: gpd.GeoDataFrame
    ) -> str:
        """Cache processed temperature grid."""
        cache_key = self._generate_key({
            'type': 'temperature_grid',
            'bounds': geometry_bounds,
            'start_date': date_range[0].isoformat(),
            'end_date': date_range[1].isoformat(),
            'grid_size': grid_size,
            'cloud_threshold': cloud_threshold
        })
        
        cache_file = self.cache_dir / "temperatures" / f"{cache_key}.geojson"
        
        try:
            temperature_grid.to_file(cache_file)
            self.logger.debug(f"Cached temperature grid: {cache_key}")
        except Exception as e:
            self.logger.warning(f"Failed to cache temperature grid: {e}")
        
        return cache_key
    
    def get_temperature_grid(
        self,
        geometry_bounds: Tuple[float, float, float, float],
        date_range: Tuple[date, date],
        grid_size: float,
        cloud_threshold: float
    ) -> Optional[gpd.GeoDataFrame]:
        """Retrieve cached temperature grid."""
        cache_key = self._generate_key({
            'type': 'temperature_grid',
            'bounds': geometry_bounds,
            'start_date': date_range[0].isoformat(),
            'end_date': date_range[1].isoformat(),
            'grid_size': grid_size,
            'cloud_threshold': cloud_threshold
        })
        
        cache_file = self.cache_dir / "temperatures" / f"{cache_key}.geojson"
        
        if self._is_cache_valid(cache_file):
            try:
                grid = gpd.read_file(cache_file)
                self.logger.info(f"🚀 Using cached temperature grid: {cache_key[:8]}... ({len(grid)} cells)")
                return grid
            except Exception as e:
                self.logger.warning(f"Failed to load cached temperature grid: {e}")
        
        return None
    
    # Boundary Data Caching
    def cache_boundary_data(self, suburb: str, boundary_data: gpd.GeoDataFrame) -> str:
        """Cache boundary data for a suburb."""
        cache_key = self._generate_key({
            'type': 'boundary',
            'suburb': suburb.lower().replace(' ', '_')
        })
        
        cache_file = self.cache_dir / "boundaries" / f"{cache_key}.geojson"
        
        try:
            boundary_data.to_file(cache_file)
            self.logger.debug(f"Cached boundary data: {suburb}")
        except Exception as e:
            self.logger.warning(f"Failed to cache boundary data: {e}")
        
        return cache_key
    
    def get_boundary_data(self, suburb: str) -> Optional[gpd.GeoDataFrame]:
        """Retrieve cached boundary data."""
        cache_key = self._generate_key({
            'type': 'boundary',
            'suburb': suburb.lower().replace(' ', '_')
        })
        
        cache_file = self.cache_dir / "boundaries" / f"{cache_key}.geojson"
        
        if self._is_cache_valid(cache_file):
            try:
                boundary = gpd.read_file(cache_file)
                self.logger.info(f"🚀 Using cached boundary data: {suburb}")
                return boundary
            except Exception as e:
                self.logger.warning(f"Failed to load cached boundary data: {e}")
        
        return None
    
    # Land Cover Caching
    def cache_landcover_data(
        self,
        geometry_bounds: Tuple[float, float, float, float],
        year: int,
        landcover_data: gpd.GeoDataFrame
    ) -> str:
        """Cache land cover data."""
        cache_key = self._generate_key({
            'type': 'landcover',
            'bounds': geometry_bounds,
            'year': year
        })
        
        cache_file = self.cache_dir / "landcover" / f"{cache_key}.geojson"
        
        try:
            landcover_data.to_file(cache_file)
            self.logger.debug(f"Cached landcover data: {year}")
        except Exception as e:
            self.logger.warning(f"Failed to cache landcover data: {e}")
        
        return cache_key
    
    def get_landcover_data(
        self,
        geometry_bounds: Tuple[float, float, float, float],
        year: int
    ) -> Optional[gpd.GeoDataFrame]:
        """Retrieve cached land cover data."""
        cache_key = self._generate_key({
            'type': 'landcover',
            'bounds': geometry_bounds,
            'year': year
        })
        
        cache_file = self.cache_dir / "landcover" / f"{cache_key}.geojson"
        
        if self._is_cache_valid(cache_file):
            try:
                landcover = gpd.read_file(cache_file)
                self.logger.info(f"🚀 Using cached landcover data: {year} ({len(landcover)} features)")
                return landcover
            except Exception as e:
                self.logger.warning(f"Failed to load cached landcover data: {e}")
        
        return None
    
    # Analysis Grid Caching
    def cache_analysis_grid(
        self,
        geometry_bounds: Tuple[float, float, float, float],
        grid_size: float,
        grid_data: gpd.GeoDataFrame
    ) -> str:
        """Cache analysis grid."""
        cache_key = self._generate_key({
            'type': 'analysis_grid',
            'bounds': geometry_bounds,
            'grid_size': grid_size
        })
        
        cache_file = self.cache_dir / "grids" / f"{cache_key}.geojson"
        
        try:
            grid_data.to_file(cache_file)
            self.logger.debug(f"Cached analysis grid: {grid_size}m")
        except Exception as e:
            self.logger.warning(f"Failed to cache analysis grid: {e}")
        
        return cache_key
    
    def get_analysis_grid(
        self,
        geometry_bounds: Tuple[float, float, float, float],
        grid_size: float
    ) -> Optional[gpd.GeoDataFrame]:
        """Retrieve cached analysis grid."""
        cache_key = self._generate_key({
            'type': 'analysis_grid',
            'bounds': geometry_bounds,
            'grid_size': grid_size
        })
        
        cache_file = self.cache_dir / "grids" / f"{cache_key}.geojson"
        
        if self._is_cache_valid(cache_file):
            try:
                grid = gpd.read_file(cache_file)
                self.logger.info(f"🚀 Using cached analysis grid: {grid_size}m ({len(grid)} cells)")
                return grid
            except Exception as e:
                self.logger.warning(f"Failed to load cached analysis grid: {e}")
        
        return None
    
    def clear_cache(self, cache_type: Optional[str] = None):
        """Clear cache files."""
        if cache_type:
            cache_subdir = self.cache_dir / cache_type
            if cache_subdir.exists():
                for file in cache_subdir.glob("*"):
                    file.unlink()
                self.logger.info(f"Cleared {cache_type} cache")
        else:
            for file in self.cache_dir.rglob("*"):
                if file.is_file():
                    file.unlink()
            self.logger.info("Cleared all cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.rglob("*"))
        cache_files = [f for f in cache_files if f.is_file()]
        
        total_size = sum(f.stat().st_size for f in cache_files)
        
        stats_by_type = {}
        for cache_type in ["earth_engine", "boundaries", "landcover", "grids", "temperatures"]:
            type_files = list((self.cache_dir / cache_type).glob("*"))
            type_size = sum(f.stat().st_size for f in type_files if f.is_file())
            stats_by_type[cache_type] = {
                'files': len(type_files),
                'size_mb': round(type_size / 1024**2, 2)
            }
        
        return {
            'total_files': len(cache_files),
            'total_size_mb': round(total_size / 1024**2, 2),
            'max_size_gb': self.max_size_bytes / 1024**3,
            'max_age_days': self.max_age.days,
            'by_type': stats_by_type
        } 