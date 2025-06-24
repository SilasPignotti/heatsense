import pytest
import sys
from datetime import date
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from uhi_analyzer.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
import geopandas as gpd
from shapely.geometry import Polygon

class TestUrbanHeatIslandAnalyzer:
    def test_initialization(self):
        analyzer = UrbanHeatIslandAnalyzer(cloud_cover_threshold=10.0)
        assert analyzer.cloud_threshold == 10.0
        assert hasattr(analyzer, 'logger')

    @pytest.mark.skip("Earth Engine authentication required for full test.")
    def test_analyze_heat_islands_minimal(self):
        # Minimal GeoDataFrame for city boundary and landuse
        poly = Polygon([(0,0), (1,0), (1,1), (0,1)])
        city_gdf = gpd.GeoDataFrame({'geometry': [poly]}, crs="EPSG:4326")
        landuse_gdf = gpd.GeoDataFrame({'geometry': [poly], 'landuse_type': ['urban'], 'impervious_area': [0.8]}, crs="EPSG:4326")
        analyzer = UrbanHeatIslandAnalyzer(cloud_cover_threshold=20.0)
        # This will fail if Earth Engine is not authenticated
        results = analyzer.analyze_heat_islands(
            city_boundary=city_gdf,
            date_range=(date(2022, 7, 1), date(2022, 7, 31)),
            landuse_data=landuse_gdf,
            weather_stations=None
        )
        assert isinstance(results, dict)
        assert 'temperature_statistics' in results
        assert 'land_use_correlation' in results
        assert 'hot_spots' in results
        assert 'temporal_trends' in results
        assert 'mitigation_recommendations' in results 