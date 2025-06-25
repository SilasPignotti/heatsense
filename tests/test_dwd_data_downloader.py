#!/usr/bin/env python3
"""
Test script for the revised DWDDataDownloader.
Tests the functionality with time periods and averaging.
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys
import geopandas as gpd

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from uhi_analyzer.data.dwd_downloader import DWDDataDownloader
from uhi_analyzer.config.settings import CRS_CONFIG

class TestDWDDataDownloader:
    @pytest.fixture(scope="class")
    def berlin_geometry(self):
        import json
        berlin_geojson_path = Path("data/raw/boundaries/berlin_admin_boundaries.geojson")
        if not berlin_geojson_path.exists():
            pytest.skip(f"Berlin geometry not found: {berlin_geojson_path}")
        with open(berlin_geojson_path, 'r', encoding='utf-8') as f:
            geojson = json.load(f)
            if geojson.get("type") == "FeatureCollection":
                return geojson['features'][0]['geometry']
            elif geojson.get("type") in ["Polygon", "MultiPolygon"]:
                return geojson
            else:
                raise ValueError(f"Unexpected GeoJSON type: {geojson.get('type')}")

    def test_station_data_mode(self, berlin_geometry):
        """Test basic station data retrieval (new API)."""
        start_date = datetime(2024, 7, 15)
        end_date = datetime(2024, 7, 17)
        downloader = DWDDataDownloader()
        station_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            processing_mode='station_data'
        )
        assert not station_data.empty
        assert 'ground_temp' in station_data.columns
        assert 'geometry' in station_data.columns
        assert 'station_id' in station_data.columns
        assert 'measurement_count' in station_data.columns
        assert 'source' in station_data.columns
        assert station_data['source'].iloc[0] == 'station'

    def test_interpolated_mode(self, berlin_geometry):
        """Test interpolated data mode (new API)."""
        start_date = datetime(2024, 7, 15)
        end_date = datetime(2024, 7, 17)
        downloader = DWDDataDownloader()
        interpolated_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            processing_mode='interpolated',
            resolution=2000  # Lower resolution for faster testing
        )
        assert not interpolated_data.empty
        assert 'ground_temp' in interpolated_data.columns
        assert 'geometry' in interpolated_data.columns
        assert 'source' in interpolated_data.columns
        assert 'n_stations' in interpolated_data.columns
        assert interpolated_data['source'].iloc[0] == 'interpolated'

    def test_uhi_analysis_mode(self, berlin_geometry):
        """Test UHI analysis mode with additional columns."""
        start_date = datetime(2024, 7, 15)
        end_date = datetime(2024, 7, 17)
        downloader = DWDDataDownloader()
        uhi_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            processing_mode='uhi_analysis'
        )
        assert not uhi_data.empty
        assert 'ground_temp' in uhi_data.columns
        assert 'temperature_category' in uhi_data.columns
        assert 'heat_stress_potential' in uhi_data.columns
        assert 'measurement_quality' in uhi_data.columns

    def test_download_and_save(self, berlin_geometry, tmp_path):
        """Test download and save functionality."""
        start_date = datetime(2024, 7, 15)
        end_date = datetime(2024, 7, 17)
        downloader = DWDDataDownloader()
        
        output_path = tmp_path / "test_weather.geojson"
        result_path = downloader.download_and_save(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            output_path=output_path,
            processing_mode='station_data'
        )
        
        assert result_path.exists()
        assert result_path == output_path
        
        # Verify we can read the saved file
        saved_data = gpd.read_file(result_path)
        assert not saved_data.empty
        assert 'ground_temp' in saved_data.columns

    def test_backward_compatibility(self, berlin_geometry):
        """Test backward compatibility with old API."""
        start_date = datetime(2024, 7, 15)
        end_date = datetime(2024, 7, 17)
        downloader = DWDDataDownloader()
        
        # Old API should still work
        station_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            interpolate=False
        )
        assert not station_data.empty
        
        interpolated_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            interpolate=True,
            resolution=2000
        )
        assert not interpolated_data.empty

    def test_compatibility_with_uhi_analyzer(self, berlin_geometry):
        """Test compatibility with UHI analyzer workflow."""
        start_date = datetime(2024, 7, 15)
        end_date = datetime(2024, 7, 17)
        downloader = DWDDataDownloader()
        station_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            processing_mode='station_data'
        )
        station_data_proj = station_data.to_crs(CRS_CONFIG["BERLIN"])
        satellite_temps = gpd.GeoDataFrame({
            'satellite_temp': [20.5, 21.0, 22.0],
            'geometry': [station_data_proj.geometry.iloc[0],
                         station_data_proj.geometry.iloc[1] if len(station_data_proj) > 1 else station_data_proj.geometry.iloc[0],
                         station_data_proj.geometry.iloc[0]]
        }, crs=CRS_CONFIG["BERLIN"])
        joined = gpd.sjoin_nearest(station_data_proj, satellite_temps)
        assert len(joined) > 0
        assert 'ground_temp' in joined.columns

    def test_default_parameters(self):
        """Test the default parameters utility method."""
        defaults = DWDDataDownloader.get_default_parameters()
        assert isinstance(defaults, dict)
        assert 'buffer_distance' in defaults
        assert 'interpolation_method' in defaults
        assert 'interpolate_by_default' in defaults
        assert 'interpolation_resolution' in defaults

    def test_uhi_processing_method(self):
        """Test the UHI processing method directly."""
        # Create sample data
        import pandas as pd
        from shapely.geometry import Point
        
        sample_data = gpd.GeoDataFrame({
            'station_id': ['12345', '67890'],
            'name': ['Test Station 1', 'Test Station 2'],
            'ground_temp': [25.5, 18.2],
            'temp_std': [3.1, 4.8],
            'measurement_count': [120, 85],
            'geometry': [Point(13.4, 52.5), Point(13.3, 52.4)]
        }, crs='EPSG:4326')
        
        downloader = DWDDataDownloader()
        uhi_data = downloader.process_for_uhi_analysis(sample_data)
        
        assert 'temperature_category' in uhi_data.columns
        assert 'heat_stress_potential' in uhi_data.columns
        assert 'measurement_quality' in uhi_data.columns
        
        # Check categories
        assert uhi_data['temperature_category'].iloc[0] == 'warm'  # 25.5°C
        assert uhi_data['temperature_category'].iloc[1] == 'moderate'  # 18.2°C


if __name__ == "__main__":
    pytest.main() 