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
from uhi_analyzer.config.settings import BERLIN_CRS

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

    def test_station_data(self, berlin_geometry):
        start_date = datetime(2024, 7, 15)
        end_date = datetime(2024, 7, 17)
        downloader = DWDDataDownloader()
        station_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            interpolate=False
        )
        assert not station_data.empty
        assert 'ground_temp' in station_data.columns
        assert 'geometry' in station_data.columns
        assert 'station_id' in station_data.columns
        assert 'measurement_count' in station_data.columns

    def test_interpolated_data(self, berlin_geometry):
        start_date = datetime(2024, 7, 15)
        end_date = datetime(2024, 7, 17)
        downloader = DWDDataDownloader()
        interpolated_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            interpolate=True,
            resolution=1000
        )
        assert not interpolated_data.empty
        assert 'ground_temp' in interpolated_data.columns
        assert 'geometry' in interpolated_data.columns
        assert 'source' in interpolated_data.columns
        assert 'n_stations' in interpolated_data.columns

    def test_compatibility_with_uhi_analyzer(self, berlin_geometry):
        start_date = datetime(2024, 7, 15)
        end_date = datetime(2024, 7, 17)
        downloader = DWDDataDownloader()
        station_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            interpolate=False
        )
        station_data_proj = station_data.to_crs(BERLIN_CRS)
        satellite_temps = gpd.GeoDataFrame({
            'satellite_temp': [20.5, 21.0, 22.0],
            'geometry': [station_data_proj.geometry.iloc[0],
                         station_data_proj.geometry.iloc[1] if len(station_data_proj) > 1 else station_data_proj.geometry.iloc[0],
                         station_data_proj.geometry.iloc[0]]
        }, crs=BERLIN_CRS)
        joined = gpd.sjoin_nearest(station_data_proj, satellite_temps)
        assert len(joined) > 0
        assert 'ground_temp' in joined.columns


if __name__ == "__main__":
    pytest.main() 