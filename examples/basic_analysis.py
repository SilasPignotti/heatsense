#!/usr/bin/env python3
"""
HeatSense Basic Analysis Example

This example demonstrates how to perform a basic Urban Heat Island analysis
using the HeatSense library programmatically.

Usage:
    python examples/basic_analysis.py
"""

import sys
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent.parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from heatsense.webapp.analysis_backend import UHIAnalysisBackend
import json

def main():
    """Run a basic UHI analysis example."""
    print("🔥 HeatSense Basic Analysis Example")
    print("=" * 50)
    
    # Initialize the backend
    backend = UHIAnalysisBackend(log_level="INFO")
    
    # Analysis parameters
    area = "Kreuzberg"
    start_date = "2023-07-01"
    end_date = "2023-07-31"
    performance_mode = "fast"
    
    print(f"📍 Area: {area}")
    print(f"📅 Period: {start_date} to {end_date}")
    print(f"⚙️  Mode: {performance_mode}")
    print("=" * 50)
    
    try:
        # Run the analysis
        result = backend.analyze(
            area=area,
            start_date=start_date,
            end_date=end_date,
            performance_mode=performance_mode
        )
        
        # Process results
        if result['status'] == 'completed':
            data = result.get('data', {})
            summary = data.get('summary', {})
            
            print("✅ Analysis completed successfully!")
            print("\n📊 Results Summary:")
            print(f"   • Execution time: {result.get('execution_time', 'N/A')}s")
            print(f"   • Mean temperature: {summary.get('temperature_overview', {}).get('mean', 'N/A')}°C")
            print(f"   • Temperature range: {summary.get('temperature_overview', {}).get('min', 'N/A')}°C - {summary.get('temperature_overview', {}).get('max', 'N/A')}°C")
            print(f"   • Hotspots found: {summary.get('hotspots_count', 'N/A')}")
            print(f"   • Land use correlation: {summary.get('correlation_strength', 'N/A'):.3f}")
            
            # Temperature statistics
            temp_data = data.get('temperature_data', {})
            if temp_data:
                print(f"\n🌡️ Temperature Analysis:")
                print(f"   • Grid cells analyzed: {temp_data.get('grid_cells_total', 'N/A')}")
                print(f"   • Valid temperature readings: {temp_data.get('grid_cells_valid', 'N/A')}")
            
            # Hotspots information
            hotspots = data.get('hotspots', {})
            if hotspots and hotspots.get('count', 0) > 0:
                print(f"\n🔥 Heat Islands:")
                print(f"   • Number of hotspots: {hotspots.get('count', 'N/A')}")
                temp_range = hotspots.get('temperature_range', {})
                print(f"   • Hotspot temperature range: {temp_range.get('min', 'N/A')}°C - {temp_range.get('max', 'N/A')}°C")
            
            # Land use correlation
            landuse = data.get('landuse_correlation', {})
            if landuse:
                correlations = landuse.get('correlations', {})
                overall = correlations.get('overall', {})
                print(f"\n🏙️ Land Use Correlation:")
                print(f"   • Correlation coefficient: {overall.get('correlation', 'N/A'):.3f}")
                print(f"   • Statistical significance (p-value): {overall.get('p_value', 'N/A')}")
                print(f"   • Analysis type: {landuse.get('analysis_type', 'N/A')}")
            
            # Weather stations (if available)
            weather = data.get('weather_stations', {})
            if weather:
                print(f"\n🌤️ Weather Station Validation:")
                print(f"   • Stations used: {weather.get('count', 'N/A')}")
                temp_range = weather.get('temperature_range', {})
                print(f"   • Station temperature range: {temp_range.get('min', 'N/A')}°C - {temp_range.get('max', 'N/A')}°C")
            
            print("\n" + "=" * 50)
            print("Example completed! Check the temp/ directory for detailed output files.")
            
        else:
            print("❌ Analysis failed!")
            for error in result.get('errors', []):
                print(f"   Error: {error}")
                
    except Exception as e:
        print(f"❌ Example failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())