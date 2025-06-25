#!/usr/bin/env python3
"""
Example: Satellite-based Urban Heat Island Analysis

This script demonstrates how to use the UrbanHeatIslandAnalyzer with real satellite data
to analyze urban heat island effects in Berlin.
"""

import sys
from pathlib import Path
from datetime import date

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from uhi_analyzer import UrbanHeatIslandAnalyzer


def run_summer_analysis():
    """Run analysis for summer 2023."""
    print("🌡️  Summer 2023 Urban Heat Island Analysis")
    print("=" * 50)
    
    # Initialize analyzer with conservative cloud threshold
    analyzer = UrbanHeatIslandAnalyzer(
        cloud_cover_threshold=20,  # Max 20% cloud cover
        log_file="logs/summer_analysis.log"
    )
    
    # Define analysis parameters
    city_boundary = "data/raw/boundaries/berlin_admin_boundaries.geojson"
    landuse_data = "data/raw/landcover/berlin_corine_landcover.geojson"
    start_date = date(2023, 7, 1)
    end_date = date(2023, 7, 31)
    output_dir = "data/processed/uhi_analysis_summer"
    
    print(f"📅 Analysis period: {start_date} to {end_date}")
    print(f"☁️  Cloud threshold: 20%")
    print(f"🗺️  City boundary: {city_boundary}")
    print(f"🌱 Land use data: {landuse_data}")
    print(f"📁 Output directory: {output_dir}")
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        # Run analysis
        print("\n🔄 Starting satellite data analysis...")
        results = analyzer.analyze_heat_islands(
            city_boundary=city_boundary,
            date_range=(start_date, end_date),
            landuse_data=landuse_data
        )
        
        print("✅ Analysis completed successfully!")
        
        # Display results summary
        print("\n📊 Analysis Results:")
        print("-" * 30)
        
        if 'temperature_statistics' in results:
            temp_stats = results['temperature_statistics']
            print(f"🌡️  Temperature points analyzed: {len(temp_stats)}")
            if hasattr(temp_stats, 'describe'):
                desc = temp_stats.describe()
                print(f"   - Mean temperature: {desc.get('mean', 'N/A'):.1f}°C")
                print(f"   - Max temperature: {desc.get('max', 'N/A'):.1f}°C")
                print(f"   - Min temperature: {desc.get('min', 'N/A'):.1f}°C")
        
        if 'hot_spots' in results:
            hotspots = results['hot_spots']
            print(f"🔥 Hotspots identified: {len(hotspots)}")
        
        if 'land_use_correlation' in results:
            correlations = results['land_use_correlation']
            print(f"🏗️  Land use correlations: {len(correlations)}")
        
        if 'temporal_trends' in results:
            trends = results['temporal_trends']
            print(f"📈 Temporal trends analyzed: {len(trends)}")
        
        # Generate visualization
        print("\n🎨 Generating visualization...")
        viz_path = f"{output_dir}/summer_uhi_analysis.png"
        analyzer.visualize_results(results, viz_path)
        print(f"📊 Visualization saved to: {viz_path}")
        
        # Save detailed results
        print("\n💾 Saving detailed results...")
        summary_path = f"{output_dir}/analysis_summary.txt"
        with open(summary_path, 'w') as f:
            f.write("Summer 2023 Urban Heat Island Analysis Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Analysis Period: {start_date} to {end_date}\n")
            f.write(f"Cloud Cover Threshold: 20%\n\n")
            
            # Temperature statistics
            if 'temperature_statistics' in results:
                f.write("Temperature Statistics:\n")
                f.write(f"- Points analyzed: {len(results['temperature_statistics'])}\n")
                f.write("\n")
            
            # Hotspots
            if 'hot_spots' in results:
                f.write("Hotspot Analysis:\n")
                f.write(f"- Hotspots identified: {len(results['hot_spots'])}\n")
                f.write("\n")
            
            # Mitigation recommendations
            if 'mitigation_recommendations' in results:
                f.write("Mitigation Recommendations:\n")
                for i, rec in enumerate(results['mitigation_recommendations'], 1):
                    f.write(f"{i}. {rec.get('description', 'N/A')}\n")
                    f.write(f"   Priority: {rec.get('priority', 'N/A')}\n")
                f.write("\n")
        
        print(f"📄 Summary saved to: {summary_path}")
        
        return results
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure you have authenticated with Google Earth Engine")
        print("2. Check that all input data files exist")
        print("3. Verify your internet connection")
        print("4. Try running: uv run scripts/setup_earth_engine.py")
        raise


def run_comparison_analysis():
    """Run analysis comparing different seasons."""
    print("\n🌍 Seasonal Comparison Analysis")
    print("=" * 40)
    
    seasons = [
        ("Winter", date(2023, 1, 1), date(2023, 1, 31)),
        ("Spring", date(2023, 4, 1), date(2023, 4, 30)),
        ("Summer", date(2023, 7, 1), date(2023, 7, 31)),
        ("Autumn", date(2023, 10, 1), date(2023, 10, 31)),
    ]
    
    analyzer = UrbanHeatIslandAnalyzer(cloud_cover_threshold=30)
    
    for season_name, start_date, end_date in seasons:
        print(f"\n🌡️  Analyzing {season_name} 2023...")
        
        try:
            results = analyzer.analyze_heat_islands(
                city_boundary="data/raw/boundaries/berlin_admin_boundaries.geojson",
                date_range=(start_date, end_date),
                landuse_data="data/raw/landcover/berlin_corine_landcover.geojson"
            )
            
            if 'temperature_statistics' in results:
                temp_stats = results['temperature_statistics']
                print(f"   ✅ {season_name}: {len(temp_stats)} temperature points")
            else:
                print(f"   ⚠️  {season_name}: No temperature data available")
                
        except Exception as e:
            print(f"   ❌ {season_name}: Analysis failed - {e}")


def main():
    """Main function."""
    print("🌍 Urban Heat Island Analysis with Satellite Data")
    print("=" * 60)
    
    # Check if required data exists
    required_files = [
        "data/raw/boundaries/berlin_admin_boundaries.geojson",
        "data/raw/landcover/berlin_corine_landcover.geojson"
    ]
    
    missing_files = [f for f in required_files if not Path(f).exists()]
    if missing_files:
        print("❌ Missing required data files:")
        for f in missing_files:
            print(f"   - {f}")
        print("\n📥 Please download the required data first:")
        print("   uv run scripts/data_processing/download_berlin_boundaries.py")
        print("   uv run scripts/data_processing/download_corine_landcover.py")
        return 1
    
    try:
        # Run summer analysis
        results = run_summer_analysis()
        
        # Optionally run seasonal comparison
        print("\n" + "=" * 60)
        response = input("Would you like to run seasonal comparison analysis? (y/n): ")
        if response.lower() in ['y', 'yes']:
            run_comparison_analysis()
        
        print("\n🎉 Analysis completed successfully!")
        print("📁 Check the output directory for results and visualizations.")
        
    except KeyboardInterrupt:
        print("\n⏹️  Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 