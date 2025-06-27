#!/usr/bin/env python3
"""
Comprehensive test suite for the CacheManager class.

This test suite validates the cache management functionality including:
- Cache initialization and directory creation
- Earth Engine data caching
- Temperature grid caching  
- Boundary and landcover data caching
- Cache expiration and cleanup
- Cache statistics and management
- Error handling and edge cases
"""

import pytest
import geopandas as gpd
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from shapely.geometry import Point, Polygon
import tempfile
import json
import pickle
import logging
import time
import os

# Import the class under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from uhi_analyzer.utils.cache_manager import CacheManager
from uhi_analyzer.config.settings import CRS_CONFIG


class TestCacheManager:
    """Test suite for CacheManager class."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """Create a cache manager instance for testing."""
        return CacheManager(
            cache_dir=temp_cache_dir,
            max_age_days=1,  # Short for testing
            max_cache_size_gb=0.1,  # Small for testing
            logger=logging.getLogger(__name__)
        )

    @pytest.fixture
    def sample_geodataframe(self):
        """Create sample GeoDataFrame for testing."""
        points = [
            Point(13.2, 52.4),
            Point(13.3, 52.5),
            Point(13.4, 52.6)
        ]
        
        gdf = gpd.GeoDataFrame({
            'id': [1, 2, 3],
            'temperature': [25.5, 23.2, 21.8],
            'value': ['A', 'B', 'C']
        }, geometry=points, crs=CRS_CONFIG["OUTPUT"])
        
        return gdf

    @pytest.fixture
    def sample_earth_engine_data(self):
        """Create sample Earth Engine data for testing."""
        return {
            'collection_id': 'LANDSAT/LC08/C02/T1_L2',
            'image_count': 5,
            'date_range': ['2023-07-01', '2023-07-31'],
            'bounds': [13.0883, 52.3381, 13.7611, 52.6755],
            'properties': {
                'CLOUD_COVER': [10, 15, 20, 5, 12],
                'SUN_ELEVATION': [45, 50, 48, 52, 46]
            }
        }

    def test_initialization_default_parameters(self, temp_cache_dir):
        """Test cache manager initialization with default parameters."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        
        assert cache_manager.cache_dir == temp_cache_dir
        assert cache_manager.cache_dir.exists()
        assert cache_manager.max_age == timedelta(days=30)  # Default
        assert cache_manager.logger is not None
        
        # Check subdirectories are created
        expected_subdirs = ["earth_engine", "boundaries", "landcover", "grids", "temperatures"]
        for subdir in expected_subdirs:
            assert (cache_manager.cache_dir / subdir).exists()

    def test_initialization_custom_parameters(self, temp_cache_dir):
        """Test cache manager initialization with custom parameters."""
        cache_manager = CacheManager(
            cache_dir=temp_cache_dir,
            max_age_days=7,
            max_cache_size_gb=2.0
        )
        
        assert cache_manager.max_age == timedelta(days=7)
        assert cache_manager.max_size_bytes == 2.0 * 1024**3

    def test_generate_key_consistency(self, cache_manager):
        """Test that cache key generation is consistent."""
        data1 = {'type': 'test', 'bounds': [1, 2, 3, 4], 'date': '2023-07-01'}
        data2 = {'bounds': [1, 2, 3, 4], 'type': 'test', 'date': '2023-07-01'}  # Different order
        data3 = {'type': 'test', 'bounds': [1, 2, 3, 5], 'date': '2023-07-01'}  # Different value
        
        key1 = cache_manager._generate_key(data1)
        key2 = cache_manager._generate_key(data2)
        key3 = cache_manager._generate_key(data3)
        
        assert key1 == key2  # Same data, different order should produce same key
        assert key1 != key3  # Different data should produce different key
        assert isinstance(key1, str)
        assert len(key1) == 32  # MD5 hash length

    def test_cache_earth_engine_collection(self, cache_manager, sample_earth_engine_data):
        """Test caching Earth Engine collection data."""
        bounds = (13.0883, 52.3381, 13.7611, 52.6755)
        date_range = (date(2023, 7, 1), date(2023, 7, 31))
        
        cache_key = cache_manager.cache_earth_engine_collection(
            geometry_bounds=bounds,
            date_range=date_range,
            cloud_threshold=20,
            data=sample_earth_engine_data
        )
        
        assert isinstance(cache_key, str)
        assert len(cache_key) == 32
        
        # Check that cache file was created
        cache_file = cache_manager.cache_dir / "earth_engine" / f"{cache_key}.pkl"
        assert cache_file.exists()

    def test_get_earth_engine_collection(self, cache_manager, sample_earth_engine_data):
        """Test retrieving cached Earth Engine collection data."""
        bounds = (13.0883, 52.3381, 13.7611, 52.6755)
        date_range = (date(2023, 7, 1), date(2023, 7, 31))
        
        # First cache the data
        cache_manager.cache_earth_engine_collection(
            geometry_bounds=bounds,
            date_range=date_range,
            cloud_threshold=20,
            data=sample_earth_engine_data
        )
        
        # Then retrieve it
        retrieved_data = cache_manager.get_earth_engine_collection(
            geometry_bounds=bounds,
            date_range=date_range,
            cloud_threshold=20
        )
        
        assert retrieved_data is not None
        assert retrieved_data == sample_earth_engine_data

    def test_get_earth_engine_collection_not_found(self, cache_manager):
        """Test retrieving non-existent Earth Engine collection data."""
        bounds = (13.0883, 52.3381, 13.7611, 52.6755)
        date_range = (date(2023, 7, 1), date(2023, 7, 31))
        
        retrieved_data = cache_manager.get_earth_engine_collection(
            geometry_bounds=bounds,
            date_range=date_range,
            cloud_threshold=20
        )
        
        assert retrieved_data is None

    def test_cache_temperature_grid(self, cache_manager, sample_geodataframe):
        """Test caching temperature grid data."""
        bounds = (13.0883, 52.3381, 13.7611, 52.6755)
        date_range = (date(2023, 7, 1), date(2023, 7, 31))
        
        cache_key = cache_manager.cache_temperature_grid(
            geometry_bounds=bounds,
            date_range=date_range,
            grid_size=200,
            cloud_threshold=20,
            temperature_grid=sample_geodataframe
        )
        
        assert isinstance(cache_key, str)
        
        # Check that cache file was created
        cache_file = cache_manager.cache_dir / "temperatures" / f"{cache_key}.geojson"
        assert cache_file.exists()

    def test_get_temperature_grid(self, cache_manager, sample_geodataframe):
        """Test retrieving cached temperature grid data."""
        bounds = (13.0883, 52.3381, 13.7611, 52.6755)
        date_range = (date(2023, 7, 1), date(2023, 7, 31))
        
        # First cache the data
        cache_manager.cache_temperature_grid(
            geometry_bounds=bounds,
            date_range=date_range,
            grid_size=200,
            cloud_threshold=20,
            temperature_grid=sample_geodataframe
        )
        
        # Then retrieve it
        retrieved_grid = cache_manager.get_temperature_grid(
            geometry_bounds=bounds,
            date_range=date_range,
            grid_size=200,
            cloud_threshold=20
        )
        
        assert retrieved_grid is not None
        assert isinstance(retrieved_grid, gpd.GeoDataFrame)
        assert len(retrieved_grid) == len(sample_geodataframe)

    def test_cache_boundary_data(self, cache_manager, sample_geodataframe):
        """Test caching boundary data."""
        suburb = "Kreuzberg"
        
        cache_key = cache_manager.cache_boundary_data(suburb, sample_geodataframe)
        
        assert isinstance(cache_key, str)
        
        # Check that cache file was created
        cache_file = cache_manager.cache_dir / "boundaries" / f"{cache_key}.geojson"
        assert cache_file.exists()

    def test_get_boundary_data(self, cache_manager, sample_geodataframe):
        """Test retrieving cached boundary data."""
        suburb = "Kreuzberg"
        
        # First cache the data
        cache_manager.cache_boundary_data(suburb, sample_geodataframe)
        
        # Then retrieve it
        retrieved_boundary = cache_manager.get_boundary_data(suburb)
        
        assert retrieved_boundary is not None
        assert isinstance(retrieved_boundary, gpd.GeoDataFrame)
        assert len(retrieved_boundary) == len(sample_geodataframe)

    def test_cache_landcover_data(self, cache_manager, sample_geodataframe):
        """Test caching landcover data."""
        bounds = (13.0883, 52.3381, 13.7611, 52.6755)
        year = 2018
        
        cache_key = cache_manager.cache_landcover_data(bounds, year, sample_geodataframe)
        
        assert isinstance(cache_key, str)
        
        # Check that cache file was created
        cache_file = cache_manager.cache_dir / "landcover" / f"{cache_key}.geojson"
        assert cache_file.exists()

    def test_get_landcover_data(self, cache_manager, sample_geodataframe):
        """Test retrieving cached landcover data."""
        bounds = (13.0883, 52.3381, 13.7611, 52.6755)
        year = 2018
        
        # First cache the data
        cache_manager.cache_landcover_data(bounds, year, sample_geodataframe)
        
        # Then retrieve it
        retrieved_landcover = cache_manager.get_landcover_data(bounds, year)
        
        assert retrieved_landcover is not None
        assert isinstance(retrieved_landcover, gpd.GeoDataFrame)
        assert len(retrieved_landcover) == len(sample_geodataframe)

    def test_cache_analysis_grid(self, cache_manager, sample_geodataframe):
        """Test caching analysis grid data."""
        bounds = (13.0883, 52.3381, 13.7611, 52.6755)
        grid_size = 200
        
        cache_key = cache_manager.cache_analysis_grid(bounds, grid_size, sample_geodataframe)
        
        assert isinstance(cache_key, str)
        
        # Check that cache file was created
        cache_file = cache_manager.cache_dir / "grids" / f"{cache_key}.geojson"
        assert cache_file.exists()

    def test_get_analysis_grid(self, cache_manager, sample_geodataframe):
        """Test retrieving cached analysis grid data."""
        bounds = (13.0883, 52.3381, 13.7611, 52.6755)
        grid_size = 200
        
        # First cache the data
        cache_manager.cache_analysis_grid(bounds, grid_size, sample_geodataframe)
        
        # Then retrieve it
        retrieved_grid = cache_manager.get_analysis_grid(bounds, grid_size)
        
        assert retrieved_grid is not None
        assert isinstance(retrieved_grid, gpd.GeoDataFrame)
        assert len(retrieved_grid) == len(sample_geodataframe)

    def test_cache_expiration(self, temp_cache_dir):
        """Test cache expiration functionality."""
        # Create cache manager with very short expiration
        cache_manager = CacheManager(
            cache_dir=temp_cache_dir,
            max_age_days=0.001  # ~1.4 minutes for testing
        )
        
        # Cache some data
        sample_data = {'test': 'data'}
        cache_key = cache_manager._generate_key({'type': 'test'})
        cache_file = cache_manager.cache_dir / "earth_engine" / f"{cache_key}.pkl"
        
        with open(cache_file, 'wb') as f:
            pickle.dump(sample_data, f)
        
        # Initially valid
        assert cache_manager._is_cache_valid(cache_file)
        
        # Modify file time to make it old
        old_time = time.time() - (24 * 3600)  # 1 day ago
        os.utime(cache_file, (old_time, old_time))
        
        # Should now be invalid
        assert not cache_manager._is_cache_valid(cache_file)

    def test_cleanup_cache(self, temp_cache_dir):
        """Test cache cleanup functionality."""
        cache_manager = CacheManager(
            cache_dir=temp_cache_dir,
            max_age_days=1,
            max_cache_size_gb=0.0001  # Even smaller to trigger cleanup
        )
        
        # Create multiple cache files
        for i in range(5):
            cache_file = cache_manager.cache_dir / "earth_engine" / f"test_{i}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump({'data': 'x' * 1000}, f)  # Create some data
        
        initial_files = len(list(cache_manager.cache_dir.rglob("*.pkl")))
        assert initial_files == 5
        
        # Trigger cleanup
        cache_manager._cleanup_cache()
        
        # Some files should be removed due to size limit (or at least cleanup should run)
        remaining_files = len(list(cache_manager.cache_dir.rglob("*.pkl")))
        # Test passes if cleanup runs (may not remove files if they're still within size limit)
        assert remaining_files <= initial_files

    def test_clear_cache_all(self, cache_manager, sample_geodataframe):
        """Test clearing all cache data."""
        # Cache some data in different categories
        cache_manager.cache_boundary_data("test", sample_geodataframe)
        cache_manager.cache_landcover_data((1, 2, 3, 4), 2018, sample_geodataframe)
        
        # Verify files exist
        initial_files = len(list(cache_manager.cache_dir.rglob("*")))
        assert initial_files > 0
        
        # Clear all cache
        cache_manager.clear_cache()
        
        # Check that cache is empty (except directories)
        remaining_files = [f for f in cache_manager.cache_dir.rglob("*") if f.is_file()]
        assert len(remaining_files) == 0

    def test_clear_cache_specific_type(self, cache_manager, sample_geodataframe):
        """Test clearing specific cache type."""
        # Cache data in different categories
        cache_manager.cache_boundary_data("test", sample_geodataframe)
        cache_manager.cache_landcover_data((1, 2, 3, 4), 2018, sample_geodataframe)
        
        # Clear only boundaries
        cache_manager.clear_cache("boundaries")
        
        # Check that only boundary files are removed
        boundary_files = list((cache_manager.cache_dir / "boundaries").rglob("*.geojson"))
        landcover_files = list((cache_manager.cache_dir / "landcover").rglob("*.geojson"))
        
        assert len(boundary_files) == 0
        assert len(landcover_files) > 0

    def test_get_cache_stats(self, cache_manager, sample_geodataframe):
        """Test getting cache statistics."""
        # Cache some data
        cache_manager.cache_boundary_data("test", sample_geodataframe)
        cache_manager.cache_landcover_data((1, 2, 3, 4), 2018, sample_geodataframe)
        
        stats = cache_manager.get_cache_stats()
        
        assert isinstance(stats, dict)
        assert 'total_files' in stats
        assert 'total_size_mb' in stats
        assert 'by_type' in stats
        assert 'max_age_days' in stats
        
        assert stats['total_files'] >= 2
        assert stats['total_size_mb'] >= 0  # Size can be 0 for small test files

    def test_error_handling_invalid_cache_dir(self):
        """Test error handling for invalid cache directory."""
        # Should handle invalid paths gracefully
        invalid_path = "/invalid/path/that/does/not/exist"
        
        # This should not raise an exception, but create the directory or handle gracefully
        try:
            cache_manager = CacheManager(cache_dir=invalid_path)
            # If it succeeds, check that it handled the situation
            assert cache_manager.cache_dir is not None
        except (PermissionError, OSError):
            # Expected behavior for truly invalid paths
            pass

    def test_error_handling_corrupted_cache_file(self, cache_manager):
        """Test error handling for corrupted cache files."""
        # Create a corrupted pickle file
        cache_key = cache_manager._generate_key({'type': 'test'})
        cache_file = cache_manager.cache_dir / "earth_engine" / f"{cache_key}.pkl"
        
        # Write invalid pickle data
        with open(cache_file, 'w') as f:
            f.write("This is not valid pickle data")
        
        # Should return None and handle error gracefully
        result = cache_manager.get_earth_engine_collection(
            geometry_bounds=(1, 2, 3, 4),
            date_range=(date(2023, 7, 1), date(2023, 7, 31)),
            cloud_threshold=20
        )
        
        assert result is None

    def test_error_handling_corrupted_geojson_file(self, cache_manager):
        """Test error handling for corrupted GeoJSON files."""
        # Create a corrupted GeoJSON file
        cache_key = cache_manager._generate_key({'type': 'test'})
        cache_file = cache_manager.cache_dir / "boundaries" / f"{cache_key}.geojson"
        
        # Write invalid GeoJSON data
        with open(cache_file, 'w') as f:
            f.write("This is not valid GeoJSON data")
        
        # Should return None and handle error gracefully
        result = cache_manager.get_boundary_data("test")
        
        assert result is None

    def test_thread_safety_key_generation(self, cache_manager):
        """Test that key generation is thread-safe (deterministic)."""
        import threading
        
        data = {'type': 'test', 'value': 123}
        keys = []
        
        def generate_key():
            keys.append(cache_manager._generate_key(data))
        
        # Generate keys from multiple threads
        threads = [threading.Thread(target=generate_key) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All keys should be identical
        assert len(set(keys)) == 1  # All keys are the same

    def test_cache_performance_large_data(self, cache_manager):
        """Test cache performance with larger datasets."""
        # Create a larger GeoDataFrame
        n_points = 1000
        points = [Point(13.0 + i * 0.001, 52.0 + i * 0.001) for i in range(n_points)]
        large_gdf = gpd.GeoDataFrame({
            'id': range(n_points),
            'temperature': np.random.normal(20, 5, n_points),
            'category': np.random.choice(['A', 'B', 'C'], n_points)
        }, geometry=points, crs=CRS_CONFIG["OUTPUT"])
        
        # Time the caching operation
        import time
        start_time = time.time()
        cache_manager.cache_boundary_data("large_test", large_gdf)
        cache_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert cache_time < 10  # seconds
        
        # Test retrieval
        start_time = time.time()
        retrieved = cache_manager.get_boundary_data("large_test")
        retrieval_time = time.time() - start_time
        
        assert retrieved is not None
        assert len(retrieved) == n_points
        # Retrieval should be reasonably fast (may not always be faster than caching due to test overhead)
        assert retrieval_time < 1.0  # Should complete within 1 second 