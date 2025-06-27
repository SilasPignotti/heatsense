#!/usr/bin/env python3
"""
Comprehensive test suite for the FastUrbanHeatIslandAnalyzer class.

This test suite validates the fast UHI analyzer with caching optimizations including:
- Initialization with performance modes
- Cache manager integration
- Performance optimizations
- Earth Engine integration (mocked for testing)
- Analysis components with caching
- Error handling
- Cache statistics and management
"""

import pytest
import geopandas as gpd
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch
from shapely.geometry import Point, Polygon
import tempfile

# Import the class under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from uhi_analyzer.data.fast_urban_heat_island_analyzer import FastUrbanHeatIslandAnalyzer
from uhi_analyzer.utils.cache_manager import CacheManager
from uhi_analyzer.config.settings import (
    UHI_CLOUD_COVER_THRESHOLD, UHI_GRID_CELL_SIZE, 
    UHI_HOTSPOT_THRESHOLD, UHI_MIN_CLUSTER_SIZE, CRS_CONFIG, UHI_PERFORMANCE_MODES
)


class TestFastUrbanHeatIslandAnalyzer:
    """Test suite for FastUrbanHeatIslandAnalyzer class."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_city_boundary(self):
        """Create a sample city boundary GeoDataFrame."""
        polygon = Polygon([
            (13.0883, 52.3381),  # Southwest
            (13.7611, 52.3381),  # Southeast  
            (13.7611, 52.6755),  # Northeast
            (13.0883, 52.6755),  # Northwest
            (13.0883, 52.3381)   # Close polygon
        ])
        
        gdf = gpd.GeoDataFrame(
            {'name': ['Berlin']},
            geometry=[polygon],
            crs=CRS_CONFIG["OUTPUT"]
        )
        return gdf

    @pytest.fixture
    def sample_landuse_data(self):
        """Create sample land use data."""
        polygons = []
        landuse_types = []
        impervious_areas = []
        
        # Urban areas
        for i in range(3):
            poly = Polygon([
                (13.1 + i*0.1, 52.4 + i*0.05),
                (13.15 + i*0.1, 52.4 + i*0.05),
                (13.15 + i*0.1, 52.45 + i*0.05),
                (13.1 + i*0.1, 52.45 + i*0.05),
                (13.1 + i*0.1, 52.4 + i*0.05)
            ])
            polygons.append(poly)
            landuse_types.append('urban_continuous')
            impervious_areas.append(0.85)
        
        # Green areas
        for i in range(2):
            poly = Polygon([
                (13.4 + i*0.1, 52.5 + i*0.05),
                (13.45 + i*0.1, 52.5 + i*0.05),
                (13.45 + i*0.1, 52.55 + i*0.05),
                (13.4 + i*0.1, 52.55 + i*0.05),
                (13.4 + i*0.1, 52.5 + i*0.05)
            ])
            polygons.append(poly)
            landuse_types.append('green_urban_areas')
            impervious_areas.append(0.15)

        gdf = gpd.GeoDataFrame({
            'landuse_type': landuse_types,
            'impervious_area': impervious_areas
        }, geometry=polygons, crs=CRS_CONFIG["OUTPUT"])
        
        return gdf

    @pytest.fixture
    def sample_weather_stations(self):
        """Create sample weather station data."""
        points = [
            Point(13.2, 52.4),
            Point(13.3, 52.5),
            Point(13.4, 52.6)
        ]
        
        gdf = gpd.GeoDataFrame({
            'station_id': ['001', '002', '003'],
            'temperature': [25.5, 23.2, 21.8],
            'measurement_count': [100, 95, 102]
        }, geometry=points, crs=CRS_CONFIG["OUTPUT"])
        
        return gdf

    @pytest.fixture
    def fast_analyzer(self, temp_cache_dir):
        """Create a fast analyzer instance for testing."""
        return FastUrbanHeatIslandAnalyzer(
            cloud_cover_threshold=20,
            grid_cell_size=200,
            hotspot_threshold=0.8,
            min_cluster_size=3,
            cache_dir=temp_cache_dir,
            max_cache_age_days=1
        )

    def test_initialization_default_parameters(self, temp_cache_dir):
        """Test fast analyzer initialization with default parameters."""
        analyzer = FastUrbanHeatIslandAnalyzer(cache_dir=temp_cache_dir)
        
        assert analyzer.cloud_threshold == UHI_CLOUD_COVER_THRESHOLD
        assert analyzer.grid_cell_size == UHI_GRID_CELL_SIZE
        assert analyzer.hotspot_threshold == UHI_HOTSPOT_THRESHOLD
        assert analyzer.min_cluster_size == UHI_MIN_CLUSTER_SIZE
        assert not analyzer.initialized
        assert analyzer.logger is not None
        assert isinstance(analyzer.cache, CacheManager)
        assert analyzer.performance_mode is None

    def test_initialization_with_performance_mode(self, temp_cache_dir):
        """Test fast analyzer initialization with performance mode."""
        analyzer = FastUrbanHeatIslandAnalyzer(
            performance_mode="fast",
            cache_dir=temp_cache_dir
        )
        
        expected_config = UHI_PERFORMANCE_MODES["fast"]
        assert analyzer.performance_mode == "fast"
        assert analyzer.cloud_threshold == expected_config["cloud_cover_threshold"]
        assert analyzer.grid_cell_size == expected_config["grid_cell_size"]
        assert analyzer.batch_size == expected_config.get("batch_size", 3000)

    def test_initialization_custom_parameters(self, temp_cache_dir):
        """Test fast analyzer initialization with custom parameters."""
        analyzer = FastUrbanHeatIslandAnalyzer(
            cloud_cover_threshold=15,
            grid_cell_size=150,
            hotspot_threshold=0.95,
            min_cluster_size=8,
            cache_dir=temp_cache_dir,
            max_cache_age_days=7
        )
        
        assert analyzer.cloud_threshold == 15
        assert analyzer.grid_cell_size == 150
        assert analyzer.hotspot_threshold == 0.95
        assert analyzer.min_cluster_size == 8

    def test_performance_modes_available(self):
        """Test that all performance modes are available."""
        modes = FastUrbanHeatIslandAnalyzer.get_available_performance_modes()
        assert isinstance(modes, list)
        assert len(modes) > 0
        for mode in ["preview", "fast", "standard", "detailed"]:
            assert mode in modes

    def test_performance_mode_config(self):
        """Test getting performance mode configuration."""
        config = FastUrbanHeatIslandAnalyzer.get_performance_mode_config("fast")
        assert isinstance(config, dict)
        assert "grid_cell_size" in config
        assert "cloud_cover_threshold" in config

    def test_create_with_performance_mode(self, temp_cache_dir):
        """Test factory method for creating analyzer with performance mode."""
        analyzer = FastUrbanHeatIslandAnalyzer.create_with_performance_mode(
            "preview",
            cache_dir=temp_cache_dir
        )
        
        assert analyzer.performance_mode == "preview"
        expected_config = UHI_PERFORMANCE_MODES["preview"]
        assert analyzer.grid_cell_size == expected_config["grid_cell_size"]

    @patch('uhi_analyzer.data.fast_urban_heat_island_analyzer.ee')
    def test_initialize_earth_engine_success(self, mock_ee, fast_analyzer):
        """Test successful Earth Engine initialization."""
        mock_ee.data._credentials = None
        mock_ee.Authenticate.return_value = None
        mock_ee.Initialize.return_value = None
        
        fast_analyzer.initialize_earth_engine()
        
        assert fast_analyzer.initialized
        mock_ee.Authenticate.assert_called_once()
        mock_ee.Initialize.assert_called_once()

    @patch('uhi_analyzer.data.fast_urban_heat_island_analyzer.ee')
    def test_initialize_earth_engine_failure(self, mock_ee, fast_analyzer):
        """Test Earth Engine initialization failure."""
        mock_ee.data._credentials = False
        mock_ee.Authenticate.side_effect = Exception("Authentication failed")
        
        with pytest.raises(RuntimeError):
            fast_analyzer.initialize_earth_engine()
        
        assert not fast_analyzer.initialized

    def test_cache_manager_integration(self, fast_analyzer):
        """Test cache manager integration."""
        assert isinstance(fast_analyzer.cache, CacheManager)
        
        # Test cache stats
        stats = fast_analyzer.get_cache_stats()
        assert isinstance(stats, dict)
        assert "total_files" in stats

    def test_cache_operations(self, fast_analyzer):
        """Test cache operations."""
        # Test clearing cache
        fast_analyzer.clear_cache()
        
        # Test clearing specific cache type
        fast_analyzer.clear_cache("temperatures")

    def test_load_geodata_cached(self, fast_analyzer, sample_city_boundary):
        """Test cached geodata loading."""
        result = fast_analyzer._load_geodata_cached(sample_city_boundary, "boundary")
        
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == len(sample_city_boundary)
        assert result.crs is not None

    def test_load_geodata_from_file_path(self, fast_analyzer, sample_city_boundary, temp_cache_dir):
        """Test loading geodata from file path with caching."""
        # Save sample data to file
        test_file = temp_cache_dir / "test_boundary.geojson"
        sample_city_boundary.to_file(test_file)
        
        # Load using file path
        result = fast_analyzer._load_geodata_cached(str(test_file), "boundary")
        
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == len(sample_city_boundary)

    def test_get_default_parameters(self):
        """Test getting default configuration parameters."""
        defaults = FastUrbanHeatIslandAnalyzer.get_default_parameters()
        
        assert isinstance(defaults, dict)
        assert 'earth_engine_project' in defaults
        assert 'cloud_cover_threshold' in defaults
        assert 'grid_cell_size' in defaults
        assert 'hotspot_threshold' in defaults
        assert 'performance_mode' in defaults
        assert 'cache_enabled' in defaults

    @pytest.mark.skip(reason="Complex Earth Engine mock setup - integration test")
    @patch('uhi_analyzer.data.fast_urban_heat_island_analyzer.ee')
    def test_analyze_heat_islands_with_cache(self, mock_ee, fast_analyzer, 
                                           sample_city_boundary, sample_landuse_data):
        """Test heat island analysis with caching (mocked)."""
        # Setup Earth Engine mocks
        mock_collection = Mock()
        mock_image = Mock()
        mock_ee.ImageCollection.return_value = mock_collection
        mock_collection.filterBounds.return_value = mock_collection
        mock_collection.filterDate.return_value = mock_collection
        mock_collection.filter.return_value = mock_collection
        mock_collection.median.return_value = mock_image
        mock_collection.size.return_value = Mock()
        mock_collection.size().getInfo.return_value = 5
        
        # Mock temperature extraction - more detailed mock setup
        mock_sample_result = Mock()
        mock_sample_result.getInfo.return_value = {
            'features': [
                {'properties': {'temperature': 25.5, 'grid_id': 0}},
                {'properties': {'temperature': 23.2, 'grid_id': 1}},
                {'properties': {'temperature': 21.8, 'grid_id': 2}}
            ]
        }
        
        mock_image.select.return_value = mock_image
        mock_image.multiply.return_value = mock_image
        mock_image.add.return_value = mock_image
        mock_image.subtract.return_value = mock_image
        mock_image.sampleRegions.return_value = mock_sample_result
        
        fast_analyzer.initialized = True
        
        # Test the analysis
        with patch.object(fast_analyzer, '_create_analysis_grid_optimized') as mock_grid:
            # Create mock grid
            grid_geometry = [
                Point(13.2, 52.4).buffer(0.01),
                Point(13.3, 52.5).buffer(0.01),
                Point(13.4, 52.6).buffer(0.01)
            ]
            mock_grid_df = gpd.GeoDataFrame({
                'grid_id': [0, 1, 2]
            }, geometry=grid_geometry, crs=CRS_CONFIG["OUTPUT"])
            mock_grid.return_value = mock_grid_df
            
            results = fast_analyzer.analyze_heat_islands(
                city_boundary=sample_city_boundary,
                date_range=(date(2023, 7, 1), date(2023, 7, 31)),
                landuse_data=sample_landuse_data
            )
        
        # Verify results structure
        assert isinstance(results, dict)
        assert 'temperature_data' in results
        assert 'analysis_summary' in results
        assert 'metadata' in results

    def test_save_results(self, fast_analyzer, temp_cache_dir):
        """Test saving analysis results."""
        # Create mock results
        results = {
            'temperature_data': gpd.GeoDataFrame({
                'temperature': [25.5, 23.2, 21.8],
                'grid_id': [0, 1, 2]
            }, geometry=[Point(13.2, 52.4), Point(13.3, 52.5), Point(13.4, 52.6)]),
            'analysis_summary': {
                'mean_temperature': 23.5,
                'max_temperature': 25.5,
                'hotspot_count': 1
            },
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'grid_cell_size': 200,
                'performance_mode': 'fast'
            }
        }
        
        saved_files = fast_analyzer.save_results(results, temp_cache_dir)
        
        assert isinstance(saved_files, dict)
        assert len(saved_files) > 0
        
        # Check that files were actually created
        for file_path in saved_files.values():
            assert Path(file_path).exists()

    def test_error_handling_invalid_performance_mode(self, temp_cache_dir):
        """Test error handling for invalid performance mode."""
        # Should not raise error, but use default values
        analyzer = FastUrbanHeatIslandAnalyzer(
            performance_mode="invalid_mode",
            cache_dir=temp_cache_dir
        )
        
        # Should fall back to defaults when invalid mode is provided
        assert analyzer.performance_mode is None or analyzer.performance_mode == "invalid_mode"
        assert analyzer.cloud_threshold == UHI_CLOUD_COVER_THRESHOLD

    def test_cache_statistics(self, fast_analyzer):
        """Test cache statistics reporting."""
        stats = fast_analyzer.get_cache_stats()
        
        assert isinstance(stats, dict)
        assert 'total_files' in stats
        assert 'total_size_mb' in stats

    def test_performance_mode_skip_temporal_trends(self, temp_cache_dir):
        """Test that preview mode skips temporal trends."""
        analyzer = FastUrbanHeatIslandAnalyzer(
            performance_mode="preview",
            cache_dir=temp_cache_dir
        )
        
        # Check that temporal trends are skipped for preview mode
        expected_config = UHI_PERFORMANCE_MODES["preview"]
        if "skip_temporal_trends" in expected_config:
            assert analyzer.skip_temporal_trends == expected_config["skip_temporal_trends"]

    def test_logging_configuration(self, temp_cache_dir):
        """Test logging configuration for fast analyzer."""
        log_file = temp_cache_dir / "test.log"
        analyzer = FastUrbanHeatIslandAnalyzer(
            cache_dir=temp_cache_dir,
            log_file=log_file
        )
        
        assert analyzer.logger is not None
        # Check that log file was created if file handler was set up
        if hasattr(analyzer, '_file_handler') and analyzer._file_handler is not None:
            assert log_file.exists()

    def test_cache_dir_creation(self):
        """Test that cache directory is created automatically."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "new_cache"
            analyzer = FastUrbanHeatIslandAnalyzer(cache_dir=cache_dir)
            
            assert cache_dir.exists()
            assert analyzer.cache.cache_dir == cache_dir

    def test_memory_efficiency_batch_processing(self, fast_analyzer):
        """Test that batch processing parameters are set correctly."""
        # Test default batch size
        assert hasattr(fast_analyzer, 'batch_size')
        assert fast_analyzer.batch_size > 0
        
        # Test max pixels setting
        assert hasattr(fast_analyzer, 'max_pixels')
        assert fast_analyzer.max_pixels > 0

    def test_performance_mode_inheritance(self, temp_cache_dir):
        """Test that performance mode settings are properly inherited."""
        for mode in ["preview", "fast", "standard", "detailed"]:
            analyzer = FastUrbanHeatIslandAnalyzer(
                performance_mode=mode,
                cache_dir=temp_cache_dir
            )
            
            expected_config = UHI_PERFORMANCE_MODES[mode]
            assert analyzer.performance_mode == mode
            assert analyzer.grid_cell_size == expected_config["grid_cell_size"]
            assert analyzer.cloud_threshold == expected_config["cloud_cover_threshold"] 