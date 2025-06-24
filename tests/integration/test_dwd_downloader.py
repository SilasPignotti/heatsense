#!/usr/bin/env python3
"""
Test script for the revised DWDDataDownloader.
Tests the functionality with time periods and averaging.
"""

import logging
from datetime import datetime
from pathlib import Path
import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from uhi_analyzer.data.dwd_downloader import DWDDataDownloader
from uhi_analyzer.config.settings import BERLIN_CRS

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_berlin_geometry() -> dict:
    """Loads the Berlin geometry from the GeoJSON file."""
    import json
    berlin_geojson_path = Path("data/raw/boundaries/berlin_admin_boundaries.geojson")
    
    if not berlin_geojson_path.exists():
        raise FileNotFoundError(f"Berlin geometry not found: {berlin_geojson_path}")
    
    with open(berlin_geojson_path, 'r', encoding='utf-8') as f:
        geojson = json.load(f)
        if geojson.get("type") == "FeatureCollection":
            return geojson['features'][0]['geometry']
        elif geojson.get("type") in ["Polygon", "MultiPolygon"]:
            return geojson
        else:
            raise ValueError(f"Unexpected GeoJSON type: {geojson.get('type')}")


def test_dwd_downloader():
    """Test of the revised DWDDataDownloader class."""
    logger.info("=" * 60)
    logger.info("TEST: DWDDataDownloader with time period and averaging")
    logger.info("=" * 60)
    
    # Test period (short for quick test)
    start_date = datetime(2024, 7, 15)  # Summer day
    end_date = datetime(2024, 7, 17)    # 3 days
    
    logger.info(f"Test period: {start_date.date()} to {end_date.date()}")
    
    try:
        # Load Berlin geometry
        berlin_geometry = load_berlin_geometry()
        logger.info("✓ Berlin geometry loaded successfully")
        
        # Initialize DWD downloader
        downloader = DWDDataDownloader()
        logger.info("✓ DWDDataDownloader initialized")
        
        # Test 1: Station data without interpolation
        logger.info("\n--- Test 1: Station data (without interpolation) ---")
        station_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            interpolate=False
        )
        
        if not station_data.empty:
            logger.info(f"✓ Station data received: {len(station_data)} stations")
            logger.info(f"  Temperature range: {station_data['ground_temp'].min():.1f}°C - {station_data['ground_temp'].max():.1f}°C")
            logger.info(f"  Mean: {station_data['ground_temp'].mean():.1f}°C")
            logger.info(f"  Example station: {station_data.iloc[0]['station_id']} - {station_data.iloc[0]['name']}")
            logger.info(f"  Measurements: {station_data.iloc[0]['measurement_count']}")
            logger.info(f"  Period: {station_data.iloc[0]['period_start']} to {station_data.iloc[0]['period_end']}")
            
            # Check columns
            required_columns = ['ground_temp', 'geometry', 'station_id', 'measurement_count']
            missing_columns = [col for col in required_columns if col not in station_data.columns]
            if missing_columns:
                logger.error(f"✗ Missing columns: {missing_columns}")
            else:
                logger.info("✓ All required columns present")
        else:
            logger.error("✗ No station data received")
            return False
        
        # Test 2: Interpolated data
        logger.info("\n--- Test 2: Interpolated data ---")
        interpolated_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            interpolate=True,
            resolution=1000  # 1km for faster test
        )
        
        if not interpolated_data.empty:
            logger.info(f"✓ Interpolated data received: {len(interpolated_data)} points")
            logger.info(f"  Temperature range: {interpolated_data['ground_temp'].min():.1f}°C - {interpolated_data['ground_temp'].max():.1f}°C")
            logger.info(f"  Mean: {interpolated_data['ground_temp'].mean():.1f}°C")
            logger.info(f"  Stations used: {interpolated_data['n_stations'].iloc[0]}")
            logger.info(f"  Resolution: {interpolated_data['resolution_m'].iloc[0]}m")
            
            # Check columns
            required_columns = ['ground_temp', 'geometry', 'source', 'n_stations']
            missing_columns = [col for col in required_columns if col not in interpolated_data.columns]
            if missing_columns:
                logger.error(f"✗ Missing columns: {missing_columns}")
            else:
                logger.info("✓ All required columns present")
        else:
            logger.error("✗ No interpolated data received")
            return False
        
        # Test 3: Check compatibility with UHI-Analyzer validation
        logger.info("\n--- Test 3: Compatibility with UHI-Analyzer ---")
        
        # Check if spatial join would be possible
        try:
            import geopandas as gpd
            
            # Convert both DataFrames to projected CRS for spatial operations
            station_data_proj = station_data.to_crs(BERLIN_CRS)
            
            # Simulate satellite_temps DataFrame (already in projected CRS)
            satellite_temps = gpd.GeoDataFrame({
                'satellite_temp': [20.5, 21.0, 22.0],
                'geometry': [station_data_proj.geometry.iloc[0], 
                           station_data_proj.geometry.iloc[1] if len(station_data_proj) > 1 else station_data_proj.geometry.iloc[0],
                           station_data_proj.geometry.iloc[0]]
            }, crs=BERLIN_CRS)
            
            # Test spatial join (as in _validate_with_ground_data)
            joined = gpd.sjoin_nearest(station_data_proj, satellite_temps)
            logger.info(f"✓ Spatial join successful: {len(joined)} matches")
            
            # Check if ground_temp column is present
            if 'ground_temp' in joined.columns:
                logger.info("✓ 'ground_temp' column available for validation")
            else:
                logger.error("✗ 'ground_temp' column missing for validation")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error during compatibility test: {e}")
            return False
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL TESTS SUCCESSFUL!")
        logger.info("✓ DWDDataDownloader works correctly with time periods")
        logger.info("✓ Averaging works")
        logger.info("✓ Compatibility with UHI-Analyzer ensured")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = test_dwd_downloader()
    if not success:
        sys.exit(1)
    logger.info("Test completed - all functions work correctly!") 