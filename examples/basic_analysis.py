#!/usr/bin/env python3
"""
HeatSense basic analysis example.

Demonstrates programmatic usage of the HeatSense library for Urban Heat Island
analysis. Shows how to initialize the backend, configure parameters, execute
analysis, and process results.

Dependencies:
    - heatsense: Main analysis package

Usage:
    python examples/basic_analysis.py
"""

import sys
from pathlib import Path

# Add source directory to Python path
current_dir = Path(__file__).parent.parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from heatsense.webapp.analysis_backend import UHIAnalysisBackend


def display_temperature_analysis(temp_data: dict) -> None:
    """Display temperature analysis statistics."""
    if not temp_data:
        return
        
    print("\n🌡️ Temperature Analysis:")
    print(f"   • Grid cells analyzed: {temp_data.get('grid_cells_total', 'N/A')}")
    print(f"   • Valid temperature readings: {temp_data.get('grid_cells_valid', 'N/A')}")


def display_hotspots_information(hotspots: dict) -> None:
    """Display heat island hotspots information."""
    if not hotspots or hotspots.get('count', 0) == 0:
        return
        
    print("\n🔥 Heat Islands:")
    print(f"   • Number of hotspots: {hotspots.get('count', 'N/A')}")
    
    temp_range = hotspots.get('temperature_range', {})
    if temp_range:
        min_temp = temp_range.get('min', 'N/A')
        max_temp = temp_range.get('max', 'N/A')
        print(f"   • Hotspot temperature range: {min_temp}°C - {max_temp}°C")


def display_landuse_correlation(landuse: dict) -> None:
    """Display land use correlation analysis results."""
    if not landuse:
        return
        
    print("\n🏙️ Land Use Correlation:")
    
    correlations = landuse.get('correlations', {})
    overall = correlations.get('overall', {})
    
    correlation = overall.get('correlation', 'N/A')
    if correlation != 'N/A':
        print(f"   • Correlation coefficient: {correlation:.3f}")
    else:
        print(f"   • Correlation coefficient: {correlation}")
    
    p_value = overall.get('p_value', 'N/A')
    print(f"   • Statistical significance (p-value): {p_value}")
    print(f"   • Analysis type: {landuse.get('analysis_type', 'N/A')}")


def display_weather_validation(weather: dict) -> None:
    """Display weather station validation information."""
    if not weather:
        return
        
    print("\n🌤️ Weather Station Validation:")
    print(f"   • Stations used: {weather.get('count', 'N/A')}")
    
    temp_range = weather.get('temperature_range', {})
    if temp_range:
        min_temp = temp_range.get('min', 'N/A')
        max_temp = temp_range.get('max', 'N/A')
        print(f"   • Station temperature range: {min_temp}°C - {max_temp}°C")


def process_analysis_results(result: dict) -> None:
    """Process and display comprehensive analysis results."""
    if result['status'] != 'completed':
        print("❌ Analysis failed!")
        for error in result.get('errors', []):
            print(f"   Error: {error}")
        return
    
    data = result.get('data', {})
    summary = data.get('summary', {})
    
    print("✅ Analysis completed successfully!")
    print("\n📊 Results Summary:")
    
    # Basic metrics
    execution_time = result.get('execution_time', 'N/A')
    print(f"   • Execution time: {execution_time}s")
    
    # Temperature overview
    temp_overview = summary.get('temperature_overview', {})
    mean_temp = temp_overview.get('mean', 'N/A')
    min_temp = temp_overview.get('min', 'N/A')
    max_temp = temp_overview.get('max', 'N/A')
    
    print(f"   • Mean temperature: {mean_temp}°C")
    print(f"   • Temperature range: {min_temp}°C - {max_temp}°C")
    print(f"   • Hotspots found: {summary.get('hotspots_count', 'N/A')}")
    
    correlation_strength = summary.get('correlation_strength', 'N/A')
    if correlation_strength != 'N/A':
        print(f"   • Land use correlation: {correlation_strength:.3f}")
    else:
        print(f"   • Land use correlation: {correlation_strength}")
    
    # Detailed analysis sections
    display_temperature_analysis(data.get('temperature_data', {}))
    display_hotspots_information(data.get('hotspots', {}))
    display_landuse_correlation(data.get('landuse_correlation', {}))
    display_weather_validation(data.get('weather_stations', {}))
    
    print("\n" + "=" * 50)
    print("Analysis complete! Check temp/ directory for detailed output files.")


def main():
    """Execute basic UHI analysis example."""
    print("🔥 HeatSense Basic Analysis Example")
    print("=" * 50)
    
    # Initialize analysis backend
    backend = UHIAnalysisBackend(log_level="INFO")
    
    # Configure analysis parameters
    analysis_config = {
        "area": "Kreuzberg",
        "start_date": "2023-07-01",
        "end_date": "2023-07-31",
        "performance_mode": "fast"
    }
    
    print(f"📍 Area: {analysis_config['area']}")
    print(f"📅 Period: {analysis_config['start_date']} to {analysis_config['end_date']}")
    print(f"⚙️ Performance mode: {analysis_config['performance_mode']}")
    print("=" * 50)
    
    try:
        # Execute Urban Heat Island analysis
        result = backend.analyze(**analysis_config)
        
        # Process and display results
        process_analysis_results(result)
        
        return 0
        
    except Exception as e:
        print(f"❌ Analysis example failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())