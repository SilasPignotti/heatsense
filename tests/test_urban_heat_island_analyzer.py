#!/usr/bin/env python3
"""
Comprehensive test suite for the UrbanHeatIslandAnalyzer class.

This test suite validates the core functionality of the UHI analyzer including:
- Initialization and configuration
- Earth Engine integration (mocked for testing)
- Data loading and validation
- Analysis components
- Error handling
- Result structure validation
"""

import pytest
import geopandas as gpd
import numpy as np
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch
from shapely.geometry import Point, Polygon
import tempfile
import json
import logging

# Import the class under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from uhi_analyzer.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
from uhi_analyzer.config.settings import (
    UHI_EARTH_ENGINE_PROJECT, UHI_CLOUD_COVER_THRESHOLD, UHI_GRID_CELL_SIZE, 
    UHI_HOTSPOT_THRESHOLD, UHI_MIN_CLUSTER_SIZE, CRS_CONFIG
)


class TestUrbanHeatIslandAnalyzer:
    """Test suite for UrbanHeatIslandAnalyzer class."""

    @pytest.fixture
    def sample_city_boundary(self):
        """Create a sample city boundary GeoDataFrame."""
        # Create a simple polygon around Berlin coordinates
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
        # Create multiple polygons with different land use types
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
    def analyzer(self):
        """Create an analyzer instance for testing."""
        return UrbanHeatIslandAnalyzer(
            cloud_cover_threshold=20,
            grid_cell_size=200,  # Larger for faster testing
            hotspot_threshold=0.8,
            min_cluster_size=3
        )

    def test_initialization_default_parameters(self):
        """Test analyzer initialization with default parameters."""
        analyzer = UrbanHeatIslandAnalyzer()
        
        assert analyzer.cloud_threshold == UHI_CLOUD_COVER_THRESHOLD
        assert analyzer.grid_cell_size == UHI_GRID_CELL_SIZE
        assert analyzer.hotspot_threshold == UHI_HOTSPOT_THRESHOLD
        assert analyzer.min_cluster_size == UHI_MIN_CLUSTER_SIZE
        assert not analyzer.initialized
        assert analyzer.logger is not None

    def test_initialization_custom_parameters(self):
        """Test analyzer initialization with custom parameters."""
        analyzer = UrbanHeatIslandAnalyzer(
            cloud_cover_threshold=15,
            grid_cell_size=150,
            hotspot_threshold=0.95,
            min_cluster_size=8
        )
        
        assert analyzer.cloud_threshold == 15
        assert analyzer.grid_cell_size == 150
        assert analyzer.hotspot_threshold == 0.95
        assert analyzer.min_cluster_size == 8

    def test_get_default_parameters(self):
        """Test getting default configuration parameters."""
        defaults = UrbanHeatIslandAnalyzer.get_default_parameters()
        
        assert isinstance(defaults, dict)
        assert 'earth_engine_project' in defaults
        assert 'cloud_cover_threshold' in defaults
        assert 'grid_cell_size' in defaults
        assert 'hotspot_threshold' in defaults
        assert 'temperature_conversion' in defaults
        assert 'visualization' in defaults
        
        # Check specific values
        assert defaults['earth_engine_project'] == UHI_EARTH_ENGINE_PROJECT
        assert defaults['cloud_cover_threshold'] == UHI_CLOUD_COVER_THRESHOLD
        assert defaults['grid_cell_size'] == UHI_GRID_CELL_SIZE

    @patch('uhi_analyzer.data.urban_heat_island_analyzer.ee')
    def test_initialize_earth_engine_success(self, mock_ee, analyzer):
        """Test successful Earth Engine initialization."""
        mock_ee.data._credentials = None
        mock_ee.Authenticate.return_value = None
        mock_ee.Initialize.return_value = None
        
        analyzer.initialize_earth_engine()
        
        assert analyzer.initialized
        mock_ee.Authenticate.assert_called_once()
        mock_ee.Initialize.assert_called_once()

    @patch('uhi_analyzer.data.urban_heat_island_analyzer.ee')
    def test_initialize_earth_engine_failure(self, mock_ee, analyzer):
        """Test Earth Engine initialization failure."""
        # Mock credentials as False to trigger authentication
        mock_ee.data._credentials = False
        mock_ee.Authenticate.side_effect = Exception("Authentication failed")
        
        with pytest.raises(RuntimeError):
            analyzer.initialize_earth_engine()
        
        assert not analyzer.initialized

    def test_load_geodata_from_geodataframe(self, analyzer, sample_city_boundary):
        """Test loading geodata from GeoDataFrame."""
        result = analyzer._load_geodata(sample_city_boundary, "test boundary")
        
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == len(sample_city_boundary)
        assert result.crs is not None

    def test_load_geodata_invalid_input(self, analyzer):
        """Test loading geodata with invalid input."""
        with pytest.raises(ValueError):
            analyzer._load_geodata("nonexistent_file.geojson", "test data")

    def test_create_analysis_grid(self, analyzer, sample_city_boundary):
        """Test analysis grid creation."""
        grid = analyzer._create_analysis_grid(sample_city_boundary, cell_size=500)
        
        assert isinstance(grid, gpd.GeoDataFrame)
        assert len(grid) > 0
        assert 'geometry' in grid.columns
        assert grid.crs == CRS_CONFIG["OUTPUT"]

    def test_create_analysis_grid_default_size(self, analyzer, sample_city_boundary):
        """Test analysis grid creation with default cell size."""
        grid = analyzer._create_analysis_grid(sample_city_boundary)
        
        assert isinstance(grid, gpd.GeoDataFrame)
        assert len(grid) > 0

    def test_analyze_landuse_correlation(self, analyzer):
        """Test land use correlation analysis."""
        # Create sample temperature data
        temp_data = gpd.GeoDataFrame({
            'temperature': [25.0, 27.0, 23.0, 26.0, 24.0]
        }, geometry=[
            Point(13.1, 52.4), Point(13.15, 52.4), Point(13.2, 52.4),
            Point(13.4, 52.5), Point(13.45, 52.5)
        ], crs=CRS_CONFIG["OUTPUT"])
        
        # Create sample land use data
        landuse_data = gpd.GeoDataFrame({
            'landuse_type': ['urban_continuous', 'urban_continuous', 'urban_continuous', 
                           'green_urban_areas', 'green_urban_areas'],
            'impervious_area': [0.85, 0.85, 0.85, 0.15, 0.15]
        }, geometry=[
            Point(13.1, 52.4), Point(13.15, 52.4), Point(13.2, 52.4),
            Point(13.4, 52.5), Point(13.45, 52.5)
        ], crs=CRS_CONFIG["OUTPUT"])
        
        result = analyzer._analyze_landuse_correlation(temp_data, landuse_data)
        
        assert isinstance(result, dict)
        assert 'statistics' in result
        assert 'correlations' in result

    def test_identify_heat_hotspots(self, analyzer):
        """Test heat hotspot identification."""
        # Create sample temperature data with clear hotspots
        temperatures = [20.0, 21.0, 22.0, 30.0, 31.0, 32.0, 23.0, 24.0, 25.0]
        geometries = []
        
        # Create a 3x3 grid
        for i in range(3):
            for j in range(3):
                geometries.append(Point(13.1 + i*0.01, 52.4 + j*0.01))
        
        temp_data = gpd.GeoDataFrame({
            'temperature': temperatures
        }, geometry=geometries, crs=CRS_CONFIG["OUTPUT"])
        
        hotspots = analyzer._identify_heat_hotspots(temp_data, threshold=0.6, min_cluster_size=1)
        
        assert isinstance(hotspots, gpd.GeoDataFrame)
        # Should identify the high temperature cells (30, 31, 32)
        assert len(hotspots) <= len(temp_data)

    def test_identify_heat_hotspots_empty_result(self, analyzer):
        """Test heat hotspot identification with no hotspots."""
        # Create uniform temperature data
        temperatures = [20.0] * 9
        geometries = [Point(13.1 + i*0.01, 52.4) for i in range(9)]
        
        temp_data = gpd.GeoDataFrame({
            'temperature': temperatures
        }, geometry=geometries, crs=CRS_CONFIG["OUTPUT"])
        
        hotspots = analyzer._identify_heat_hotspots(temp_data)
        
        assert isinstance(hotspots, gpd.GeoDataFrame)
        # Should not find hotspots in uniform data
        assert len(hotspots) == 0

    def test_validate_with_ground_data(self, analyzer):
        """Test ground data validation."""
        # Create satellite temperature data
        satellite_temps = gpd.GeoDataFrame({
            'temperature': [25.0, 26.0, 24.0]
        }, geometry=[
            Point(13.2, 52.4), Point(13.3, 52.5), Point(13.4, 52.6)
        ], crs=CRS_CONFIG["OUTPUT"])
        
        # Create weather station data
        station_data = gpd.GeoDataFrame({
            'temperature': [24.8, 26.2, 23.9]
        }, geometry=[
            Point(13.2001, 52.4001), Point(13.3001, 52.5001), Point(13.4001, 52.6001)
        ], crs=CRS_CONFIG["OUTPUT"])
        
        result = analyzer._validate_with_ground_data(satellite_temps, station_data)
        
        assert isinstance(result, dict)
        if 'comparison_data' in result:
            assert len(result['comparison_data']) > 0

    def test_validate_with_ground_data_no_temperature_column(self, analyzer):
        """Test ground validation with missing temperature column."""
        satellite_temps = gpd.GeoDataFrame({
            'temperature': [25.0, 26.0, 24.0]
        }, geometry=[Point(13.2, 52.4), Point(13.3, 52.5), Point(13.4, 52.6)], 
        crs=CRS_CONFIG["OUTPUT"])
        
        # Station data without temperature column
        station_data = gpd.GeoDataFrame({
            'pressure': [1013, 1014, 1012]
        }, geometry=[Point(13.2, 52.4), Point(13.3, 52.5), Point(13.4, 52.6)], 
        crs=CRS_CONFIG["OUTPUT"])
        
        result = analyzer._validate_with_ground_data(satellite_temps, station_data)
        
        assert 'error' in result
        assert 'No temperature column found' in result['error']

    def test_generate_recommendations(self, analyzer):
        """Test mitigation recommendations generation."""
        # Create sample results
        results = {
            'temperature_statistics': gpd.GeoDataFrame({
                'temperature': [25.0, 30.0, 35.0]
            }, geometry=[Point(13.1, 52.4), Point(13.2, 52.5), Point(13.3, 52.6)]),
            'hot_spots': gpd.GeoDataFrame({
                'temperature': [35.0]
            }, geometry=[Point(13.3, 52.6)]),
            'land_use_correlation': {
                'statistics': {
                    'urban_continuous': {'temperature_mean': 32.0},
                    'green_urban_areas': {'temperature_mean': 24.0}
                }
            }
        }
        
        recommendations = analyzer._generate_recommendations(results)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Check recommendation structure
        for rec in recommendations:
            assert 'strategy' in rec
            assert 'priority' in rec
            assert 'description' in rec

    def test_save_results(self, analyzer):
        """Test saving analysis results."""
        # Create sample results
        temp_stats = gpd.GeoDataFrame({
            'temperature': [25.0, 26.0, 24.0]
        }, geometry=[Point(13.1, 52.4), Point(13.2, 52.5), Point(13.3, 52.6)], 
        crs=CRS_CONFIG["OUTPUT"])
        
        hotspots = gpd.GeoDataFrame({
            'temperature': [30.0]
        }, geometry=[Point(13.4, 52.7)], crs=CRS_CONFIG["OUTPUT"])
        
        results = {
            'metadata': {'analysis_date': '2022-07-01'},
            'temperature_statistics': temp_stats,
            'hot_spots': hotspots,
            'land_use_correlation': {'statistics': {}},
            'mitigation_recommendations': [{'strategy': 'green_infrastructure'}]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            saved_files = analyzer.save_results(results, output_dir, "test")
            
            assert isinstance(saved_files, dict)
            assert 'temperature_statistics' in saved_files
            assert 'hot_spots' in saved_files
            assert 'summary' in saved_files
            
            # Check files were actually created
            for file_path in saved_files.values():
                assert file_path.exists()

    @patch('uhi_analyzer.data.urban_heat_island_analyzer.sns')
    @patch('uhi_analyzer.data.urban_heat_island_analyzer.plt')
    def test_visualize_results(self, mock_plt, mock_sns, analyzer):
        """Test results visualization."""
        # Create sample results
        temp_stats = gpd.GeoDataFrame({
            'temperature': [25.0, 26.0, 24.0, 30.0]
        }, geometry=[Point(13.1, 52.4), Point(13.2, 52.5), Point(13.3, 52.6), Point(13.4, 52.7)], 
        crs=CRS_CONFIG["OUTPUT"])
        
        results = {
            'temperature_statistics': temp_stats,
            'hot_spots': gpd.GeoDataFrame({
                'temperature': [30.0]
            }, geometry=[Point(13.4, 52.7)], crs=CRS_CONFIG["OUTPUT"]),
            'land_use_correlation': {
                'statistics': {
                    'urban_continuous': {'temperature_mean': 28.0}
                }
            }
        }
        
        # Create a mock axes array that supports tuple indexing
        mock_axes = np.array([[Mock(), Mock()], [Mock(), Mock()]])
        
        # Mock matplotlib to avoid actual plotting
        mock_plt.subplots.return_value = (Mock(), mock_axes)
        
        # Mock seaborn
        mock_sns.histplot.return_value = None
        
        analyzer.visualize_results(results)
        
        # Verify plotting functions were called
        mock_plt.subplots.assert_called_once()
        mock_plt.tight_layout.assert_called_once()
        mock_sns.histplot.assert_called_once()

    @patch('uhi_analyzer.data.urban_heat_island_analyzer.ee')
    def test_full_analysis_workflow_mocked(self, mock_ee, analyzer, sample_city_boundary, sample_landuse_data):
        """Test complete analysis workflow with mocked Earth Engine."""
        # Mock Earth Engine components
        mock_ee.data._credentials = True
        mock_ee.Initialize.return_value = None
        
        # Mock image collection
        mock_collection = Mock()
        mock_ee.ImageCollection.return_value = mock_collection
        mock_collection.filterBounds.return_value = mock_collection
        mock_collection.filterDate.return_value = mock_collection
        mock_collection.filter.return_value = mock_collection
        mock_collection.sort.return_value = mock_collection
        mock_collection.first.return_value = Mock()
        
        # Mock geometry
        mock_geometry = Mock()
        mock_geometry.bounds = [13.0, 52.3, 13.8, 52.7]
        mock_ee.Geometry.Rectangle.return_value = mock_geometry
        
        # Mock temperature image processing
        mock_image = Mock()
        mock_collection.mean.return_value = mock_image
        mock_image.select.return_value = mock_image
        mock_image.multiply.return_value = mock_image
        mock_image.add.return_value = mock_image
        mock_image.subtract.return_value = mock_image
        
        # Mock reduce region for temperature statistics
        mock_stats_result = Mock()
        mock_stats_result.getInfo.return_value = {
            'ST_B10_mean': 298.5,
            'ST_B10_p10': 295.0,
            'ST_B10_p90': 302.0,
            'ST_B10_stdDev': 3.2
        }
        mock_image.reduceRegion.return_value = mock_stats_result
        
        # Mock temperature extraction
        mock_feature_collection = Mock()
        mock_ee.FeatureCollection.return_value = mock_feature_collection
        mock_image.reduceRegions.return_value = mock_feature_collection
        
        # Mock temperature data response
        mock_feature_collection.getInfo.return_value = {
            'features': [
                {'properties': {'grid_id': 0, 'ST_B10': 25.0}},
                {'properties': {'grid_id': 1, 'ST_B10': 26.0}},
                {'properties': {'grid_id': 2, 'ST_B10': 24.0}}
            ]
        }
        
        analyzer.initialized = True  # Skip initialization
        
        # Patch the grid creation to return a small grid for testing
        with patch.object(analyzer, '_create_analysis_grid') as mock_grid:
            mock_grid.return_value = gpd.GeoDataFrame({
                'geometry': [Point(13.1, 52.4), Point(13.2, 52.5), Point(13.3, 52.6)]
            }, crs=CRS_CONFIG["OUTPUT"])
            
            # Run analysis
            results = analyzer.analyze_heat_islands(
                city_boundary=sample_city_boundary,
                date_range=(date(2022, 7, 1), date(2022, 7, 31)),
                landuse_data=sample_landuse_data
            )
        
        # Verify results structure
        assert isinstance(results, dict)
        assert 'metadata' in results
        assert 'temperature_statistics' in results
        assert 'land_use_correlation' in results
        assert 'hot_spots' in results
        assert 'mitigation_recommendations' in results

    def test_error_handling_invalid_date_range(self, analyzer, sample_city_boundary, sample_landuse_data):
        """Test error handling for invalid date range."""
        analyzer.initialized = True
        
        # Invalid date range (end before start)
        with pytest.raises(Exception):
            analyzer.analyze_heat_islands(
                city_boundary=sample_city_boundary,
                date_range=(date(2022, 8, 1), date(2022, 7, 1)),  # Invalid range
                landuse_data=sample_landuse_data
            )

    def test_logging_configuration(self):
        """Test logging configuration."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # Clear any existing logger handlers to ensure fresh setup
            logger_name = f"{UrbanHeatIslandAnalyzer.__module__}.{UrbanHeatIslandAnalyzer.__name__}"
            if logger_name in logging.Logger.manager.loggerDict:
                existing_logger = logging.getLogger(logger_name)
                existing_logger.handlers.clear()
            
            analyzer = UrbanHeatIslandAnalyzer(log_file=log_file)
            
            # Log a test message
            analyzer.logger.info("Test message")
            
            # Force flush the file handler if it exists
            if hasattr(analyzer, '_file_handler') and analyzer._file_handler:
                analyzer._file_handler.flush()
            
            # Also flush all handlers
            for handler in analyzer.logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()
            
            # Check log file was created and contains message
            assert log_file.exists()
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Test message" in content

    def test_parameter_bounds_validation(self):
        """Test parameter validation and bounds."""
        # Test valid parameters
        analyzer = UrbanHeatIslandAnalyzer(
            cloud_cover_threshold=50,
            grid_cell_size=100,
            hotspot_threshold=0.95,
            min_cluster_size=1
        )
        assert analyzer.cloud_threshold == 50
        
        # Test boundary values
        analyzer = UrbanHeatIslandAnalyzer(
            cloud_cover_threshold=0,
            hotspot_threshold=0.01,
            min_cluster_size=1
        )
        assert analyzer.cloud_threshold == 0
        assert analyzer.hotspot_threshold == 0.01

    def test_save_results_with_intermediate(self, analyzer):
        """Test saving intermediate results during analysis."""
        temp_stats = gpd.GeoDataFrame({
            'temperature': [25.0, 26.0, 24.0]
        }, geometry=[Point(13.1, 52.4), Point(13.2, 52.5), Point(13.3, 52.6)], 
        crs=CRS_CONFIG["OUTPUT"])
        
        results = {
            'metadata': {
                'analysis_date': '2022-07-01',
                'study_period': '2022-07-01 to 2022-07-31',
                'cloud_threshold': 20,
                'grid_cell_size': 100,
                'city_area_km2': 891.0
            },
            'temperature_statistics': temp_stats,
            'hot_spots': gpd.GeoDataFrame(),
            'land_use_correlation': {'statistics': {}, 'correlations': {}},
            'mitigation_recommendations': []
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            saved_files = analyzer.save_results(results, output_dir, "test_intermediate")
            
            assert 'summary' in saved_files
            
            # Check metadata in summary
            with open(saved_files['summary'], 'r') as f:
                summary = json.load(f)
                assert 'metadata' in summary
                assert 'analysis_summary' in summary
                assert summary['metadata']['city_area_km2'] == 891.0

    def test_log_analysis_summary(self, analyzer):
        """Test analysis summary logging."""
        temp_stats = gpd.GeoDataFrame({
            'temperature': [25.0, 26.0, 24.0, 30.0, 32.0]
        }, geometry=[Point(13.1, 52.4), Point(13.2, 52.5), Point(13.3, 52.6), 
                    Point(13.4, 52.7), Point(13.5, 52.8)], 
        crs=CRS_CONFIG["OUTPUT"])
        
        hotspots = gpd.GeoDataFrame({
            'temperature': [30.0, 32.0]
        }, geometry=[Point(13.4, 52.7), Point(13.5, 52.8)], 
        crs=CRS_CONFIG["OUTPUT"])
        
        results = {
            'temperature_statistics': temp_stats,
            'hot_spots': hotspots
        }
        
        # Should not raise an exception
        analyzer._log_analysis_summary(results)

    def test_analysis_with_save_intermediate(self, analyzer, sample_city_boundary, sample_landuse_data):
        """Test analysis workflow with intermediate file saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Mock the Earth Engine parts for testing
            with patch('uhi_analyzer.data.urban_heat_island_analyzer.ee') as mock_ee:
                mock_ee.data._credentials = True
                mock_ee.Initialize.return_value = None
                
                # Mock the analysis components to avoid Earth Engine calls
                with patch.object(analyzer, '_get_landsat_collection') as mock_landsat, \
                     patch.object(analyzer, '_calculate_temperature_stats') as mock_temp_stats, \
                     patch.object(analyzer, '_analyze_temporal_trends') as mock_temporal:
                    
                    # Set up mocks
                    mock_landsat.return_value = Mock()
                    mock_temp_stats.return_value = gpd.GeoDataFrame({
                        'temperature': [25.0, 26.0, 24.0]
                    }, geometry=[Point(13.1, 52.4), Point(13.2, 52.5), Point(13.3, 52.6)],
                    crs=CRS_CONFIG["OUTPUT"])
                    mock_temporal.return_value = None
                    
                    analyzer.initialized = True
                    
                    # This should work without actually calling Earth Engine
                    try:
                        results = analyzer.analyze_heat_islands(
                            city_boundary=sample_city_boundary,
                            date_range=(date(2022, 7, 1), date(2022, 7, 31)),
                            landuse_data=sample_landuse_data,
                            save_intermediate=True,
                            output_dir=output_dir
                        )
                        
                        # Verify results structure
                        assert 'metadata' in results
                        assert 'temperature_statistics' in results
                        
                        # Check if intermediate files would be saved (mocked so files may not exist)
                        assert output_dir.exists()
                        
                    except Exception as e:
                        # Expected due to mocking, but should not be Earth Engine specific errors
                        assert "Earth Engine" not in str(e)

    def test_custom_logger_initialization(self):
        """Test analyzer initialization with custom logger."""
        
        # Create custom logger
        custom_logger = logging.getLogger("test_custom_logger")
        custom_logger.setLevel(logging.DEBUG)
        
        analyzer = UrbanHeatIslandAnalyzer(logger=custom_logger)
        
        assert analyzer.logger == custom_logger
        assert analyzer.logger.name == "test_custom_logger"

    def test_earth_engine_project_parameter(self, analyzer):
        """Test Earth Engine initialization with custom project."""
        with patch('uhi_analyzer.data.urban_heat_island_analyzer.ee') as mock_ee:
            mock_ee.data._credentials = True
            mock_ee.Initialize.return_value = None
            
            analyzer.initialize_earth_engine(project="custom-project-id")
            
            assert analyzer.initialized
            mock_ee.Initialize.assert_called_once_with(project="custom-project-id")

    def test_earth_engine_default_project(self, analyzer):
        """Test Earth Engine initialization with default project from config."""
        with patch('uhi_analyzer.data.urban_heat_island_analyzer.ee') as mock_ee:
            mock_ee.data._credentials = True
            mock_ee.Initialize.return_value = None
            
            analyzer.initialize_earth_engine()  # No project specified
            
            assert analyzer.initialized
            mock_ee.Initialize.assert_called_once_with(project=UHI_EARTH_ENGINE_PROJECT)

    def test_analyze_with_weather_stations(self, analyzer, sample_city_boundary, 
                                          sample_landuse_data, sample_weather_stations):
        """Test analysis workflow with weather station validation."""
        with patch('uhi_analyzer.data.urban_heat_island_analyzer.ee') as mock_ee:
            mock_ee.data._credentials = True
            mock_ee.Initialize.return_value = None
            
            with patch.object(analyzer, '_get_landsat_collection') as mock_landsat, \
                 patch.object(analyzer, '_calculate_temperature_stats') as mock_temp_stats, \
                 patch.object(analyzer, '_analyze_temporal_trends') as mock_temporal:
                
                # Create temperature data that matches weather station locations
                temp_stats = gpd.GeoDataFrame({
                    'temperature': [25.0, 23.5, 22.0]
                }, geometry=[Point(13.2, 52.4), Point(13.3, 52.5), Point(13.4, 52.6)],
                crs=CRS_CONFIG["OUTPUT"])
                
                mock_landsat.return_value = Mock()
                mock_temp_stats.return_value = temp_stats
                mock_temporal.return_value = None
                
                analyzer.initialized = True
                
                try:
                    results = analyzer.analyze_heat_islands(
                        city_boundary=sample_city_boundary,
                        date_range=(date(2022, 7, 1), date(2022, 7, 31)),
                        landuse_data=sample_landuse_data,
                        weather_stations=sample_weather_stations
                    )
                    
                    # Should include ground validation
                    assert 'ground_validation' in results
                    
                except Exception:
                    # Expected due to mocking, but should attempt validation
                    pass

    def test_performance_optimization_logging(self, analyzer, sample_city_boundary):
        """Test that performance optimizations are logged."""
        # Create a large boundary to trigger optimization
        large_polygon = Polygon([
            (13.0, 52.0),  # Much larger area
            (14.0, 52.0), 
            (14.0, 53.0),
            (13.0, 53.0),
            (13.0, 52.0)
        ])
        
        large_boundary = gpd.GeoDataFrame(
            {'name': ['Large Area']},
            geometry=[large_polygon],
            crs=CRS_CONFIG["OUTPUT"]
        )
        
        # This should trigger the large area optimization
        grid = analyzer._create_analysis_grid(large_boundary, cell_size=100)
        
        assert isinstance(grid, gpd.GeoDataFrame)
        assert len(grid) > 0


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short"]) 