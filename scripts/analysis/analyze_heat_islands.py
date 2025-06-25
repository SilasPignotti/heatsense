#!/usr/bin/env python3
"""
Urban Heat Island Analysis Script - Demonstrates the integrated UHI analyzer.

This script shows how to use the UrbanHeatIslandAnalyzer class with the project's
configuration settings to analyze urban heat island effects using real satellite data.
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from uhi_analyzer import UrbanHeatIslandAnalyzer
from uhi_analyzer.config.settings import (
    UHI_CLOUD_COVER_THRESHOLD,
    UHI_GRID_CELL_SIZE,
    UHI_HOTSPOT_THRESHOLD,
    UHI_LOG_DIR
)


def setup_logging() -> logging.Logger:
    """Set up logging for the script."""
    logger = logging.getLogger("uhi_analysis")
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_file = UHI_LOG_DIR / "uhi_analysis.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def analyze_berlin_heat_islands(
    city_boundary_path: str,
    landuse_data_path: str,
    start_date: date,
    end_date: date,
    output_dir: str = "data/processed/uhi_analysis",
    cloud_threshold: float = None,
    weather_stations_path: str = None
) -> None:
    """
    Analyze urban heat island effects for Berlin using real satellite data.
    
    Args:
        city_boundary_path: Path to Berlin boundary GeoJSON file
        landuse_data_path: Path to land use data GeoJSON file
        start_date: Start date for analysis
        end_date: End date for analysis
        output_dir: Output directory for results
        cloud_threshold: Cloud cover threshold (uses default if None)
        weather_stations_path: Optional path to weather station data for validation
    """
    logger = setup_logging()
    
    logger.info("=== Urban Heat Island Analysis for Berlin ===")
    logger.info(f"City boundary: {city_boundary_path}")
    logger.info(f"Land use data: {landuse_data_path}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Cloud threshold: {cloud_threshold or UHI_CLOUD_COVER_THRESHOLD}%")
    if weather_stations_path:
        logger.info(f"Weather stations: {weather_stations_path}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize analyzer
    try:
        analyzer = UrbanHeatIslandAnalyzer(
            cloud_cover_threshold=cloud_threshold,
            log_file=output_path / "uhi_analysis.log"
        )
        logger.info("UrbanHeatIslandAnalyzer initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize analyzer: {e}")
        return
    
    # Load weather stations data if provided
    weather_stations = None
    if weather_stations_path and Path(weather_stations_path).exists():
        try:
            import geopandas as gpd
            weather_stations = gpd.read_file(weather_stations_path)
            logger.info(f"Loaded weather stations data: {len(weather_stations)} stations")
        except Exception as e:
            logger.warning(f"Failed to load weather stations data: {e}")
    
    # Perform analysis using real satellite data
    try:
        logger.info("Starting heat island analysis using real satellite data...")
        logger.info("Note: This requires Google Earth Engine authentication")
        
        # Call the actual analyzer method
        results = analyzer.analyze_heat_islands(
            city_boundary=city_boundary_path,
            date_range=(start_date, end_date),
            landuse_data=landuse_data_path,
            weather_stations=weather_stations
        )
        
        logger.info("Analysis completed successfully!")
        
        # Log key results
        if 'temperature_statistics' in results:
            temp_stats = results['temperature_statistics']
            logger.info(f"Temperature analysis: Processed {len(temp_stats)} temperature points")
        
        if 'hot_spots' in results:
            hotspots = results['hot_spots']
            logger.info(f"Hotspot analysis: Identified {len(hotspots)} hotspots")
        
        if 'land_use_correlation' in results:
            correlations = results['land_use_correlation']
            logger.info(f"Land use correlations: Analyzed {len(correlations)} correlations")
        
        # Create visualization
        logger.info("Creating visualization...")
        viz_path = output_path / "uhi_analysis_visualization.png"
        analyzer.visualize_results(results, str(viz_path))
        logger.info(f"Visualization saved to: {viz_path}")
        
        # Save results summary
        summary_path = output_path / "analysis_summary.txt"
        with open(summary_path, 'w') as f:
            f.write("Urban Heat Island Analysis Summary\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Date range: {start_date} to {end_date}\n")
            f.write(f"Cloud threshold: {cloud_threshold or UHI_CLOUD_COVER_THRESHOLD}%\n")
            f.write(f"Grid cell size: {UHI_GRID_CELL_SIZE}m\n")
            f.write(f"Hotspot threshold: {UHI_HOTSPOT_THRESHOLD}\n\n")
            f.write("Analysis completed using real satellite data:\n")
            f.write(f"- City boundary: {city_boundary_path}\n")
            f.write(f"- Land use data: {landuse_data_path}\n")
            if weather_stations_path:
                f.write(f"- Weather stations: {weather_stations_path}\n")
            f.write("\n")
            
            # Add key statistics
            if 'temperature_statistics' in results:
                temp_stats = results['temperature_statistics']
                f.write("Temperature Statistics:\n")
                f.write(f"- Number of temperature points: {len(temp_stats)}\n")
                if hasattr(temp_stats, 'describe'):
                    desc = temp_stats.describe()
                    f.write(f"- Mean temperature: {desc.get('mean', 'N/A'):.2f}°C\n")
                    f.write(f"- Max temperature: {desc.get('max', 'N/A'):.2f}°C\n")
                    f.write(f"- Min temperature: {desc.get('min', 'N/A'):.2f}°C\n")
                f.write("\n")
            
            if 'hot_spots' in results:
                hotspots = results['hot_spots']
                f.write(f"Hotspot Analysis:\n")
                f.write(f"- Number of hotspots identified: {len(hotspots)}\n")
                f.write("\n")
            
            if 'mitigation_recommendations' in results:
                recommendations = results['mitigation_recommendations']
                f.write("Mitigation Recommendations:\n")
                for i, rec in enumerate(recommendations, 1):
                    f.write(f"{i}. {rec.get('description', 'N/A')} (Priority: {rec.get('priority', 'N/A')})\n")
                f.write("\n")
        
        logger.info(f"Results saved to: {output_path}")
        logger.info(f"Summary saved to: {summary_path}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        logger.error("Make sure you have authenticated with Google Earth Engine:")
        logger.error("1. Run: earthengine authenticate")
        logger.error("2. Follow the authentication process")
        raise


def main():
    """Main function to run the heat island analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze urban heat island effects using real satellite data"
    )
    
    parser.add_argument(
        "--city-boundary",
        type=str,
        default="data/raw/boundaries/berlin_admin_boundaries.geojson",
        help="Path to city boundary GeoJSON file"
    )
    
    parser.add_argument(
        "--landuse-data",
        type=str,
        default="data/raw/landcover/berlin_corine_landcover.geojson",
        help="Path to land use data GeoJSON file"
    )
    
    parser.add_argument(
        "--weather-stations",
        type=str,
        default=None,
        help="Optional path to weather station data GeoJSON file for validation"
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        default="2022-06-01",
        help="Start date for analysis (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--end-date",
        type=str,
        default="2022-08-31",
        help="End date for analysis (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed/uhi_analysis",
        help="Output directory for results"
    )
    
    parser.add_argument(
        "--cloud-threshold",
        type=float,
        default=None,
        help="Cloud cover threshold percentage (0-100)"
    )
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = date.fromisoformat(args.start_date)
        end_date = date.fromisoformat(args.end_date)
    except ValueError as e:
        print(f"Error parsing dates: {e}")
        sys.exit(1)
    
    # Check input files
    if not Path(args.city_boundary).exists():
        print(f"City boundary file not found: {args.city_boundary}")
        sys.exit(1)
    
    if not Path(args.landuse_data).exists():
        print(f"Land use data file not found: {args.landuse_data}")
        sys.exit(1)
    
    if args.weather_stations and not Path(args.weather_stations).exists():
        print(f"Weather stations file not found: {args.weather_stations}")
        sys.exit(1)
    
    # Run analysis
    try:
        analyze_berlin_heat_islands(
            city_boundary_path=args.city_boundary,
            landuse_data_path=args.landuse_data,
            start_date=start_date,
            end_date=end_date,
            output_dir=args.output_dir,
            cloud_threshold=args.cloud_threshold,
            weather_stations_path=args.weather_stations
        )
        print("✅ Analysis completed successfully!")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()