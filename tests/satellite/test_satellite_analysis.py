#!/usr/bin/env python3
"""
Test Script for Satellite Data Analysis

This script tests the UrbanHeatIslandAnalyzer with real satellite data
to ensure the functionality works correctly.
"""

import sys
from pathlib import Path
from datetime import date

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from uhi_analyzer import UrbanHeatIslandAnalyzer


def test_earth_engine_connection():
    """Test Google Earth Engine connection."""
    print("🔍 Testing Google Earth Engine connection...")
    
    try:
        import ee
        ee.Initialize()
        print("✅ Google Earth Engine connection successful")
        return True
    except Exception as e:
        print(f"❌ Google Earth Engine connection failed: {e}")
        return False


def test_analyzer_initialization():
    """Test analyzer initialization."""
    print("🔍 Testing analyzer initialization...")
    
    try:
        analyzer = UrbanHeatIslandAnalyzer(cloud_cover_threshold=30)
        print("✅ Analyzer initialized successfully")
        return analyzer
    except Exception as e:
        print(f"❌ Analyzer initialization failed: {e}")
        return None


def test_satellite_data_access():
    """Test satellite data access."""
    print("🔍 Testing satellite data access...")
    
    try:
        import ee
        import geopandas as gpd
        
        # Create a small test area (Berlin center)
        test_geometry = ee.Geometry.Rectangle([13.3, 52.4, 13.5, 52.6])
        
        # Try to get Landsat collection
        collection = (
            ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .filterBounds(test_geometry)
            .filterDate('2023-07-01', '2023-07-31')
            .filter(ee.Filter.lt('CLOUD_COVER', 30))
            .limit(1)
        )
        
        # Check if we have any images
        count = collection.size().getInfo()
        print(f"✅ Found {count} Landsat scenes for test area")
        return True
        
    except Exception as e:
        print(f"❌ Satellite data access failed: {e}")
        return False


def test_full_analysis():
    """Test full analysis with real data."""
    print("🔍 Testing full analysis...")
    
    # Check if required data files exist
    city_boundary = Path("data/raw/boundaries/berlin_admin_boundaries.geojson")
    landuse_data = Path("data/raw/landcover/berlin_corine_landcover.geojson")
    
    if not city_boundary.exists():
        print(f"❌ City boundary file not found: {city_boundary}")
        return False
    
    if not landuse_data.exists():
        print(f"❌ Land use data file not found: {landuse_data}")
        return False
    
    try:
        analyzer = UrbanHeatIslandAnalyzer(cloud_cover_threshold=30)
        
        # Run analysis for a short period
        results = analyzer.analyze_heat_islands(
            city_boundary=str(city_boundary),
            date_range=(date(2023, 7, 1), date(2023, 7, 15)),  # Short period
            landuse_data=str(landuse_data)
        )
        
        print("✅ Full analysis completed successfully")
        print(f"   - Temperature statistics: {len(results.get('temperature_statistics', []))}")
        print(f"   - Hotspots: {len(results.get('hot_spots', []))}")
        print(f"   - Land use correlations: {len(results.get('land_use_correlation', []))}")
        print(f"   - Mitigation recommendations: {len(results.get('mitigation_recommendations', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Full analysis failed: {e}")
        return False


def main():
    """Main test function."""
    print("🧪 Satellite Data Analysis Test Suite")
    print("=" * 50)
    
    tests = [
        ("Earth Engine Connection", test_earth_engine_connection),
        ("Analyzer Initialization", test_analyzer_initialization),
        ("Satellite Data Access", test_satellite_data_access),
        ("Full Analysis", test_full_analysis),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Satellite data analysis is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 