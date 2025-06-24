#!/usr/bin/env python3
"""
Urban Heat Island Analysis Script - Demonstrates the integrated UHI analyzer.

This script shows how to use the UrbanHeatIslandAnalyzer class with the project's
configuration settings to analyze urban heat island effects.
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
    cloud_threshold: float = None
) -> None:
    """
    Analyze urban heat island effects for Berlin.
    
    Args:
        city_boundary_path: Path to Berlin boundary GeoJSON file
        landuse_data_path: Path to land use data GeoJSON file
        start_date: Start date for analysis
        end_date: End date for analysis
        output_dir: Output directory for results
        cloud_threshold: Cloud cover threshold (uses default if None)
    """
    logger = setup_logging()
    
    logger.info("=== Urban Heat Island Analysis for Berlin ===")
    logger.info(f"City boundary: {city_boundary_path}")
    logger.info(f"Land use data: {landuse_data_path}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Cloud threshold: {cloud_threshold or UHI_CLOUD_COVER_THRESHOLD}%")
    
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
    
    # Perform analysis
    try:
        logger.info("Starting heat island analysis...")
    results = analyzer.analyze_heat_islands(
            city_boundary=city_boundary_path,
            date_range=(start_date, end_date),
            landuse_data=landuse_data_path
        )
        
        logger.info("Analysis completed successfully!")
        
        # Log key results
        if 'temperature_statistics' in results:
            temp_stats = results['temperature_statistics']
            logger.info(f"Temperature analysis: {len(temp_stats)} grid cells processed")
        
        if 'hot_spots' in results:
            hotspots = results['hot_spots']
            logger.info(f"Hotspot analysis: {len(hotspots)} hotspots identified")
        
        if 'land_use_correlation' in results:
            correlations = results['land_use_correlation']['correlations']
            logger.info(f"Land use correlations: {len(correlations)} types analyzed")
        
        # Create visualization
        logger.info("Creating visualization...")
        viz_path = output_path / "uhi_analysis_visualization.png"
        analyzer.visualize_results(results, str(viz_path))
        
        # Save results summary
        summary_path = output_path / "analysis_summary.txt"
        with open(summary_path, 'w') as f:
            f.write("Urban Heat Island Analysis Summary\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Date range: {start_date} to {end_date}\n")
            f.write(f"Cloud threshold: {cloud_threshold or UHI_CLOUD_COVER_THRESHOLD}%\n")
            f.write(f"Grid cell size: {UHI_GRID_CELL_SIZE}m\n")
            f.write(f"Hotspot threshold: {UHI_HOTSPOT_THRESHOLD}\n\n")
            
            if 'temperature_statistics' in results:
                f.write(f"Grid cells analyzed: {len(results['temperature_statistics'])}\n")
            
            if 'hot_spots' in results:
                f.write(f"Hotspots identified: {len(results['hot_spots'])}\n")
            
            if 'mitigation_recommendations' in results:
                f.write(f"Recommendations generated: {len(results['mitigation_recommendations'])}\n")
        
        logger.info(f"Results saved to: {output_path}")
        logger.info(f"Visualization saved to: {viz_path}")
        logger.info(f"Summary saved to: {summary_path}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


def main():
    """Main function to run the heat island analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze urban heat island effects using satellite data"
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
        default="data/raw/landcover/berlin_corine_landcover_2018.geojson",
        help="Path to land use data GeoJSON file"
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        default="2023-07-01",
        help="Start date for analysis (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--end-date",
        type=str,
        default="2023-07-31",
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
    
    # Run analysis
    try:
        analyze_berlin_heat_islands(
            city_boundary_path=args.city_boundary,
            landuse_data_path=args.landuse_data,
            start_date=start_date,
            end_date=end_date,
            output_dir=args.output_dir,
            cloud_threshold=args.cloud_threshold
        )
        print("✅ Analysis completed successfully!")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()