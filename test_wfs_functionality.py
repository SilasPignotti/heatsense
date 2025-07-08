#!/usr/bin/env python3
"""
Test script for WFS functionality in HeatSense Urban Heat Island Analyzer

This script demonstrates how to:
1. Test WFS capabilities endpoint
2. Test layer download functionality
3. Test different output formats
"""

import requests
import json
from typing import Dict, Any

def test_wfs_capabilities(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Test WFS capabilities endpoint."""
    try:
        response = requests.get(f"{base_url}/api/wfs/capabilities")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error testing capabilities: {e}")
        return {}

def test_available_layers(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Test available layers endpoint."""
    try:
        response = requests.get(f"{base_url}/api/wfs/layers")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error testing layers: {e}")
        return {}

def test_layer_download(base_url: str = "http://localhost:8000", 
                       layer_name: str = "temperature",
                       format_type: str = "geojson") -> bool:
    """Test layer download (without actual analysis session)."""
    try:
        response = requests.get(f"{base_url}/api/wfs/download/{layer_name}?format={format_type}")
        
        # We expect a 404 since no analysis session is active
        if response.status_code == 404:
            error_data = response.json()
            if "No analysis results available" in str(error_data.get('errors', [])):
                print(f"✅ Layer download endpoint working correctly (no session)")
                return True
        
        print(f"❌ Unexpected response: {response.status_code}")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"Error testing layer download: {e}")
        return False

def main():
    """Run WFS functionality tests."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing WFS Functionality")
    print("=" * 40)
    print("ℹ️  Hinweis: Webapp muss gestartet sein (uv run python -m src.uhi_analyzer.webapp.app)")
    print("ℹ️  Für echte Daten-Downloads: Erst Analyse in der Web-UI durchführen!")
    print("=" * 40)
    
    # Test capabilities
    print("\n1. Testing WFS Capabilities...")
    capabilities = test_wfs_capabilities(base_url)
    if capabilities:
        print("✅ WFS Capabilities endpoint working")
        print(f"   Service: {capabilities.get('service', 'N/A')}")
        print(f"   Version: {capabilities.get('version', 'N/A')}")
        print(f"   Feature Types: {len(capabilities.get('feature_types', []))}")
    else:
        print("❌ WFS Capabilities endpoint failed")
    
    # Test available layers
    print("\n2. Testing Available Layers...")
    layers = test_available_layers(base_url)
    if layers:
        print("✅ Available layers endpoint working")
        layer_list = layers.get('layers', [])
        print(f"   Available layers: {len(layer_list)}")
        for layer in layer_list:
            print(f"   - {layer.get('name', 'N/A')}: {layer.get('title', 'N/A')}")
    else:
        print("❌ Available layers endpoint failed")
    
    # Test layer downloads
    print("\n3. Testing Layer Downloads...")
    test_layers = ['temperature', 'heat_islands', 'boundary']
    for layer in test_layers:
        success = test_layer_download(base_url, layer, 'geojson')
        if success:
            print(f"✅ {layer} download endpoint working")
        else:
            print(f"❌ {layer} download endpoint failed")
    
    print("\n" + "=" * 40)
    print("🎉 WFS Functionality Test Complete")
    print("\nTo test with actual data:")
    print("1. Start the webapp: uv run python -m src.uhi_analyzer.webapp.app")
    print("2. Run an analysis in the web interface")
    print("3. Use the WFS-Layer dropdown to download layers")
    print("4. Or use direct API calls:")
    print("   - GET /api/wfs/capabilities")
    print("   - GET /api/wfs/layers") 
    print("   - GET /api/wfs/download/temperature?format=geojson")

if __name__ == "__main__":
    main() 