#!/usr/bin/env python3
"""
HeatSense Webapp Demo

This script demonstrates the HeatSense Flask web application capabilities
by making API calls and showing expected responses.
"""

import json
import requests
import sys
import time
from pathlib import Path

# Base URL for the Flask app
BASE_URL = "http://localhost:8000"

def test_webapp_endpoints():
    """Test all webapp API endpoints."""
    print("🔥 HeatSense Webapp Demo")
    print("=" * 50)
    
    # Test if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            raise ConnectionError("Webapp not accessible")
        print("✅ Webapp is running and accessible")
    except Exception as e:
        print(f"❌ Cannot connect to webapp: {e}")
        print("💡 Make sure to start the webapp first with:")
        print("   uv run src/uhi_analyzer/webapp/run_webapp.py")
        return False
    
    # Test API endpoints
    print("\n📡 Testing API Endpoints:")
    
    # 1. Test areas endpoint
    print("\n1. Testing /api/areas endpoint...")
    try:
        # Test Bezirk areas
        response = requests.get(f"{BASE_URL}/api/areas?type=bezirk")
        areas = response.json()
        print(f"   ✅ Bezirk areas: {len(areas)} districts available")
        print(f"   📍 Sample districts: {areas[:3]}")
        
        # Test Bundesland areas
        response = requests.get(f"{BASE_URL}/api/areas?type=bundesland")
        states = response.json()
        print(f"   ✅ Bundesland areas: {states}")
        
    except Exception as e:
        print(f"   ❌ Areas endpoint failed: {e}")
    
    # 2. Test performance modes endpoint
    print("\n2. Testing /api/performance-modes endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/performance-modes")
        modes = response.json()
        print(f"   ✅ Performance modes: {len(modes)} modes available")
        for mode, details in modes.items():
            print(f"   🚀 {mode}: {details['estimated_time']} - {details['description'][:50]}...")
            
    except Exception as e:
        print(f"   ❌ Performance modes endpoint failed: {e}")
    
    # 3. Test analysis endpoint (preview mode for speed)
    print("\n3. Testing /api/analyze endpoint (preview mode)...")
    try:
        analysis_data = {
            "area_type": "bezirk",
            "area": "Friedrichshain-Kreuzberg",
            "start_date": "01.06.2025",
            "end_date": "30.06.2025",
            "performance_mode": "preview"
        }
        
        print(f"   📊 Analyzing: {analysis_data['area']}")
        print(f"   📅 Period: {analysis_data['start_date']} to {analysis_data['end_date']}")
        print(f"   ⚡ Mode: {analysis_data['performance_mode']}")
        print("   ⏳ Starting analysis... (this may take 1-2 minutes)")
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/analyze",
            json=analysis_data,
            timeout=300  # 5 minute timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            execution_time = time.time() - start_time
            
            print(f"   ✅ Analysis completed in {execution_time:.1f} seconds")
            print(f"   📈 Status: {result.get('status', 'unknown')}")
            
            # Display key results
            if result.get('data'):
                data = result['data']
                summary = data.get('summary', {})
                
                print(f"   🔥 Hotspots found: {summary.get('hotspots_count', 0)}")
                
                temp_overview = summary.get('temperature_overview', {})
                if temp_overview:
                    print(f"   🌡️  Temperature range: {temp_overview.get('min', 'N/A')}°C - {temp_overview.get('max', 'N/A')}°C")
                    print(f"   📊 Average temperature: {temp_overview.get('mean', 'N/A')}°C")
                
                print(f"   💡 Recommendations: {summary.get('recommendations_count', 0)}")
                
                # Show sample recommendation
                recommendations = data.get('recommendations', {})
                if recommendations and recommendations.get('strategies'):
                    strategies = recommendations['strategies']
                    if isinstance(strategies, list) and len(strategies) > 0:
                        sample_rec = strategies[0]
                        if isinstance(sample_rec, str):
                            print(f"   📝 Sample recommendation: {sample_rec[:100]}...")
                        else:
                            print(f"   📝 Sample recommendation: {str(sample_rec)[:100]}...")
            
        else:
            error_data = response.json()
            print(f"   ❌ Analysis failed: {error_data.get('errors', ['Unknown error'])}")
            
    except requests.exceptions.Timeout:
        print("   ⏰ Analysis timed out - this is normal for larger areas")
    except Exception as e:
        print(f"   ❌ Analysis endpoint failed: {e}")
    
    # 4. Test progress endpoint
    print("\n4. Testing /api/progress endpoint...")
    try:
        # Note: This requires a session from the analyze endpoint
        response = requests.get(f"{BASE_URL}/api/progress")
        progress = response.json()
        print(f"   ✅ Progress endpoint accessible")
        print(f"   📊 Current status: {progress.get('status', 'unknown')}")
        
    except Exception as e:
        print(f"   ❌ Progress endpoint failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Demo completed!")
    print("\n💡 To use the full interactive interface:")
    print(f"   Open your browser and go to: {BASE_URL}")
    print("\n🗺️  The webapp provides:")
    print("   • Interactive map with temperature visualization")
    print("   • Real-time analysis progress tracking")
    print("   • Comprehensive charts and statistics")
    print("   • Climate adaptation recommendations")
    print("   • Multiple performance modes for different use cases")
    
    return True

def main():
    """Run the webapp demo."""
    try:
        test_webapp_endpoints()
    except KeyboardInterrupt:
        print("\n🛑 Demo stopped by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 