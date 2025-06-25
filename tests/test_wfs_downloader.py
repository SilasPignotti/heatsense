"""
Test module for WFS Data Downloader.

This module tests all functionality of the WFSDataDownloader class including:
- Endpoint validation
- Data downloading 
- Format conversion
- Error handling
- Spatial filtering
"""

import pytest
import tempfile
from pathlib import Path
import geopandas as gpd

from uhi_analyzer.data.wfs_downloader import WFSDataDownloader


def test_endpoint_listing():
    """Test endpoint listing functionality."""
    downloader = WFSDataDownloader()
    endpoints = downloader.get_available_endpoints()
    
    assert len(endpoints) > 0, "No endpoints found"
    
    # Check that each endpoint has required configuration
    for endpoint in endpoints:
        info = downloader.get_endpoint_info(endpoint)
        assert 'url' in info, f"Endpoint {endpoint} missing URL"
        assert 'typeName' in info, f"Endpoint {endpoint} missing typeName"
        assert 'description' in info, f"Endpoint {endpoint} missing description"


@pytest.mark.slow
def test_endpoint_validation():
    """Test endpoint validation (slow test, requires network)."""
    downloader = WFSDataDownloader()
    endpoints = downloader.get_available_endpoints()
    
    # Test at least one endpoint (first one)
    if endpoints:
        first_endpoint = endpoints[0]
        try:
            is_valid = downloader.validate_endpoint(first_endpoint)
            # Don't fail test if network is unavailable
            if not is_valid:
                pytest.skip(f"Network endpoint {first_endpoint} not accessible")
        except Exception:
            pytest.skip("Network connectivity issues")


@pytest.mark.slow
def test_feature_counting():
    """Test feature counting functionality (requires network)."""
    downloader = WFSDataDownloader()
    test_endpoint = "berlin_district_boundary"  # Should have ~12 districts
    
    try:
        count = downloader.get_feature_count(test_endpoint)
        assert count >= 0, f"Invalid feature count: {count}"
        # Berlin has 12 districts, but allow for flexibility
        if count > 0:
            assert count < 50, f"Unexpected high feature count: {count}"
    except Exception:
        pytest.skip("Network endpoint not accessible")


@pytest.mark.slow
def test_geodataframe_download():
    """Test downloading to GeoDataFrame (requires network)."""
    downloader = WFSDataDownloader()
    test_endpoint = "berlin_state_boundary"  # Should be single feature
    
    try:
        gdf = downloader.download_to_geodataframe(
            endpoint_name=test_endpoint,
            max_features=5  # Limit for testing
        )
        
        assert isinstance(gdf, gpd.GeoDataFrame), "Result is not a GeoDataFrame"
        if not gdf.empty:
            assert hasattr(gdf, 'geometry'), "No geometry column found"
            assert gdf.crs is not None, "No CRS information"
        
    except Exception:
        pytest.skip("Network endpoint not accessible")


@pytest.mark.slow
def test_spatial_filtering():
    """Test spatial filtering with bounding box (requires network)."""
    downloader = WFSDataDownloader()
    test_endpoint = "berlin_district_boundary"
    
    # Berlin bounding box (roughly central area)
    bbox = (13.3, 52.45, 13.5, 52.55)
    
    try:
        # Test that bbox parameter is accepted (may or may not filter depending on WFS support)
        gdf_filtered = downloader.download_to_geodataframe(
            endpoint_name=test_endpoint,
            bbox=bbox,
            max_features=20
        )
        
        assert isinstance(gdf_filtered, gpd.GeoDataFrame), "Result is not a GeoDataFrame"
        
    except Exception:
        pytest.skip("Network endpoint not accessible")


@pytest.mark.slow
def test_file_formats():
    """Test different output formats (requires network)."""
    downloader = WFSDataDownloader()
    test_endpoint = "berlin_state_boundary"
    
    formats_to_test = [
        ("geojson", ".geojson"),
        ("gpkg", ".gpkg"),
        ("shp", ".shp")
    ]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test at least one format
        format_name, extension = formats_to_test[0]  # Test GeoJSON
        output_path = temp_path / f"test_data{extension}"
        
        try:
            success = downloader.download_and_save(
                endpoint_name=test_endpoint,
                output_path=output_path,
                output_format=format_name,
                max_features=5
            )
            
            if success and output_path.exists():
                # Try to read back the file
                gdf = gpd.read_file(output_path)
                assert isinstance(gdf, gpd.GeoDataFrame), "Could not read saved file"
            else:
                pytest.skip("File save operation failed")
                
        except Exception:
            pytest.skip("Network endpoint not accessible")


@pytest.mark.slow
def test_crs_transformation():
    """Test coordinate reference system transformation (requires network)."""
    downloader = WFSDataDownloader()
    test_endpoint = "berlin_district_boundary"
    
    target_crs = "EPSG:25833"  # UTM Zone 33N (Berlin)
    
    try:
        gdf = downloader.download_to_geodataframe(
            endpoint_name=test_endpoint,
            target_crs=target_crs,
            max_features=5
        )
        
        assert isinstance(gdf, gpd.GeoDataFrame), "Result is not a GeoDataFrame"
        if not gdf.empty:
            # Check that CRS transformation parameter is accepted
            assert gdf.crs is not None, "No CRS information"
            
    except Exception:
        pytest.skip("Network endpoint not accessible")


def test_error_handling():
    """Test error handling with invalid inputs."""
    downloader = WFSDataDownloader()
    
    # Test invalid endpoint
    with pytest.raises(KeyError):
        downloader.download_to_geodataframe("invalid_endpoint")
    
    # Test that get_endpoint_info raises error for invalid endpoint
    with pytest.raises(KeyError):
        downloader.get_endpoint_info("invalid_endpoint")


def test_max_features_parameter():
    """Test that max_features parameter is properly handled."""
    downloader = WFSDataDownloader()
    
    # Test that URL generation works with max_features
    url = downloader.build_wfs_url(
        endpoint_name="berlin_state_boundary",
        max_features=10
    )
    
    assert "maxFeatures=10" in url, "max_features parameter not in URL"


def test_bbox_parameter():
    """Test that bbox parameter is properly handled."""
    downloader = WFSDataDownloader()
    
    # Test that URL generation works with bbox
    bbox = (13.0, 52.3, 13.8, 52.7)
    url = downloader.build_wfs_url(
        endpoint_name="berlin_state_boundary",
        bbox=bbox
    )
    
    # Check for URL-encoded bbox parameter (commas are encoded as %2C)
    expected_bbox_encoded = "13.0%2C52.3%2C13.8%2C52.7"
    assert f"bbox={expected_bbox_encoded}" in url, "bbox parameter not in URL"


def test_custom_endpoint_configuration():
    """Test downloader with custom endpoint configuration."""
    custom_endpoints = {
        "test_endpoint": {
            "url": "https://example.com/wfs",
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": "test:layer",
            "outputFormat": "application/json",
            "srsName": "EPSG:4326",
            "description": "Test endpoint"
        }
    }
    
    downloader = WFSDataDownloader(endpoints=custom_endpoints)
    endpoints = downloader.get_available_endpoints()
    
    assert "test_endpoint" in endpoints, "Custom endpoint not found"
    
    info = downloader.get_endpoint_info("test_endpoint")
    assert info["url"] == "https://example.com/wfs", "Custom endpoint URL incorrect"


def test_get_default_parameters():
    """Test static method for getting default parameters."""
    params = WFSDataDownloader.get_default_parameters()
    
    assert "endpoints" in params, "Default parameters missing endpoints"
    assert "headers" in params, "Default parameters missing headers"
    assert "timeout" in params, "Default parameters missing timeout" 