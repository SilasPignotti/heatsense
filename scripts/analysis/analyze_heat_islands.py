#!/usr/bin/env python3
"""
Dynamic Urban Heat Island Analysis Script for Berlin

This script performs UHI analysis for any Berlin suburb and date range by:
1. Accepting command line arguments for dates and suburb
2. Dynamically downloading necessary data using WFS, Corine, and DWD downloaders
3. Running the UHI analysis with the downloaded data

Usage:
    python analyze_heat_islands.py --start-date 2022-06-01 --end-date 2022-08-31 --suburb "Mitte"
    python analyze_heat_islands.py --start-date 2022-01-01 --end-date 2022-12-31 --suburb "Charlottenburg-Wilmersdorf"

IMPORTANT: Requires Google Earth Engine authentication.
Run: earthengine authenticate
"""

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple
import tempfile
import shutil

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from uhi_analyzer import UrbanHeatIslandAnalyzer
from uhi_analyzer.config.settings import UHI_LOG_DIR
from uhi_analyzer.data.wfs_downloader import WFSDataDownloader
from uhi_analyzer.data.corine_downloader import CorineDataDownloader
from uhi_analyzer.data.dwd_downloader import DWDDataDownloader


def setup_logging(output_dir: Path) -> logging.Logger:
    """Set up logging for the analysis script."""
    logger = logging.getLogger("uhi_dynamic_analysis")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_file = output_dir / "uhi_analysis.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger


def validate_dates(start_date: str, end_date: str) -> Tuple[date, date]:
    """
    Validate and parse date strings.
    
    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        
    Returns:
        Tuple of (start_date, end_date) as date objects
        
    Raises:
        ValueError: If dates are invalid or in wrong order
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD format. Error: {e}")
    
    if start > end:
        raise ValueError("Start date must be before or equal to end date")
    
    if start.year < 1990:
        raise ValueError("Start date must be after 1990 (earliest available satellite data)")
    
    if end > date.today():
        raise ValueError("End date cannot be in the future")
    
    return start, end


def download_boundary_data(suburb: str, output_dir: Path, logger: logging.Logger) -> Optional[Path]:
    """
    Download boundary data for the specified suburb.
    
    Args:
        suburb: Name of the Berlin suburb/locality
        output_dir: Output directory for downloaded data
        logger: Logger instance
        
    Returns:
        Path to the downloaded boundary file, or None if failed
    """
    logger.info(f"🗺️  Downloading boundary data for: {suburb}")
    
    # Create boundaries subdirectory
    boundaries_dir = output_dir / "boundaries"
    boundaries_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize WFS downloader
    wfs_downloader = WFSDataDownloader(log_file=boundaries_dir / "wfs_download.log")
    
    try:
        # First try to get all localities to see available options
        logger.info("   Fetching available Berlin localities...")
        
        # Download all localities first
        all_localities_path = boundaries_dir / "berlin_localities_all.geojson"
        success = wfs_downloader.download_and_save(
            endpoint_name="berlin_locality_boundary",
            output_path=all_localities_path,
            output_format="geojson"
        )
        
        if not success:
            logger.error("   Failed to download locality boundaries")
            return None
        
        logger.info(f"   ✅ Downloaded locality boundaries to: {all_localities_path}")
        
        # Load the GeoDataFrame to filter for specific suburb
        import geopandas as gpd
        localities_gdf = gpd.read_file(all_localities_path)
        
        # Check available column names for filtering
        logger.debug(f"   Available columns: {list(localities_gdf.columns)}")
        
        # Try different column names that might contain the locality name
        # Based on the actual Berlin WFS data structure
        name_columns = ['nam', 'name', 'NAME', 'bezeich', 'ortsteil', 'ORTSTEIL', 'bezirk', 'BEZIRK', 'spatial_name', 'spatial_alias']
        matching_column = None
        
        for col in name_columns:
            if col in localities_gdf.columns:
                matching_column = col
                break
        
        if not matching_column:
            logger.warning(f"   Could not find name column. Available columns: {list(localities_gdf.columns)}")
            logger.warning(f"   Using all localities data instead of filtering for '{suburb}'")
            return all_localities_path
        
        # Filter for the specific suburb (case-insensitive)
        suburb_mask = localities_gdf[matching_column].str.contains(suburb, case=False, na=False)
        suburb_gdf = localities_gdf[suburb_mask]
        
        if len(suburb_gdf) == 0:
            logger.warning(f"   Suburb '{suburb}' not found in {matching_column} column")
            logger.info(f"   Available localities: {localities_gdf[matching_column].tolist()}")
            logger.warning(f"   Using all localities data instead")
            return all_localities_path
        
        if len(suburb_gdf) > 1:
            logger.info(f"   Found {len(suburb_gdf)} matching localities for '{suburb}':")
            for _, row in suburb_gdf.iterrows():
                logger.info(f"     - {row[matching_column]}")
        
        # Save the filtered boundary
        suburb_boundary_path = boundaries_dir / f"{suburb.lower().replace(' ', '_')}_boundary.geojson"
        suburb_gdf.to_file(suburb_boundary_path, driver="GeoJSON")
        
        logger.info(f"   ✅ Filtered boundary saved to: {suburb_boundary_path}")
        return suburb_boundary_path
        
    except Exception as e:
        logger.error(f"   ❌ Error downloading boundary data: {e}")
        return None


def download_landcover_data(boundary_file: Path, start_date: date, end_date: date, 
                          output_dir: Path, logger: logging.Logger) -> Optional[Path]:
    """
    Download Corine land cover data for the boundary area and date range.
    
    Args:
        boundary_file: Path to the boundary GeoJSON file
        start_date: Start date for analysis
        end_date: End date for analysis  
        output_dir: Output directory for downloaded data
        logger: Logger instance
        
    Returns:
        Path to the downloaded land cover file, or None if failed
    """
    logger.info(f"🌱 Downloading land cover data for period: {start_date} to {end_date}")
    
    # Create landcover subdirectory
    landcover_dir = output_dir / "landcover"
    landcover_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize Corine downloader with date range
        # Convert date objects to datetime objects for compatibility
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        corine_downloader = CorineDataDownloader(
            year_or_period=(start_datetime, end_datetime),
            logger=logger
        )
        
        # Download land cover data for the boundary area
        landcover_path = corine_downloader.download_and_save(
            geometry_input=boundary_file,
            output_path=landcover_dir / f"landcover_{corine_downloader.selected_year}.geojson",
            output_format="geojson",
            clip_to_boundary=True,
            process_for_uhi=True  # Include UHI-specific processing
        )
        
        logger.info(f"   ✅ Land cover data saved to: {landcover_path}")
        logger.info(f"   Selected Corine year: {corine_downloader.selected_year}")
        
        return landcover_path
        
    except Exception as e:
        logger.error(f"   ❌ Error downloading land cover data: {e}")
        return None


def download_weather_data(boundary_file: Path, start_date: date, end_date: date,
                         output_dir: Path, logger: logging.Logger) -> Optional[Path]:
    """
    Download DWD weather data for the boundary area and date range.
    
    Args:
        boundary_file: Path to the boundary GeoJSON file
        start_date: Start date for analysis
        end_date: End date for analysis
        output_dir: Output directory for downloaded data
        logger: Logger instance
        
    Returns:
        Path to the downloaded weather data file, or None if failed
    """
    logger.info(f"🌡️  Downloading weather data for period: {start_date} to {end_date}")
    
    # Create weather subdirectory
    weather_dir = output_dir / "weather"
    weather_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Initialize DWD downloader
        dwd_downloader = DWDDataDownloader(
            interpolate_by_default=True,
            interpolation_resolution=500,  # 500m resolution for urban areas
            logger=logger
        )
        
        # Convert dates to datetime objects
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Load boundary geometry for DWD downloader
        import geopandas as gpd
        boundary_gdf = gpd.read_file(boundary_file)
        
        # Download weather data
        weather_path = dwd_downloader.download_and_save(
            geometry=boundary_gdf,  # Pass GeoDataFrame instead of file path
            start_date=start_datetime,
            end_date=end_datetime,
            output_path=weather_dir / f"weather_{start_date}_to_{end_date}.geojson",
            output_format="geojson",
            interpolate=True,
            processing_mode="uhi_analysis"
        )
        
        logger.info(f"   ✅ Weather data saved to: {weather_path}")
        return weather_path
        
    except Exception as e:
        logger.error(f"   ❌ Error downloading weather data: {e}")
        logger.warning(f"   Continuing analysis without ground truth weather data")
        return None


def run_uhi_analysis(boundary_file: Path, landcover_file: Path, weather_file: Optional[Path],
                    start_date: date, end_date: date, output_dir: Path, 
                    logger: logging.Logger) -> bool:
    """
    Run the Urban Heat Island analysis with the downloaded data.
    
    Args:
        boundary_file: Path to boundary GeoJSON file
        landcover_file: Path to land cover GeoJSON file  
        weather_file: Path to weather data file (optional)
        start_date: Start date for analysis
        end_date: End date for analysis
        output_dir: Output directory for results
        logger: Logger instance
        
    Returns:
        True if analysis completed successfully
    """
    logger.info("🔥 Starting Urban Heat Island analysis...")
    
    try:
        # Initialize analyzer
        analyzer = UrbanHeatIslandAnalyzer(
            cloud_cover_threshold=20,  # Conservative for urban areas
            log_file=output_dir / "uhi_analysis.log"
        )
        
        logger.info("   ✅ UHI Analyzer initialized successfully")
        
        # Run analysis
        logger.info("   🔄 Running heat island analysis...")
        logger.info("   This may take several minutes depending on data availability...")
        
        # Load weather data as GeoDataFrame if available
        weather_gdf = None
        if weather_file:
            import geopandas as gpd
            weather_gdf = gpd.read_file(weather_file)
            logger.info(f"   Loaded weather data: {len(weather_gdf)} points")
        
        results = analyzer.analyze_heat_islands(
            city_boundary=str(boundary_file),
            date_range=(start_date, end_date),
            landuse_data=str(landcover_file),
            weather_stations=weather_gdf  # Pass GeoDataFrame instead of file path
        )
        
        logger.info("   ✅ Analysis completed successfully!")
        
        # Display results summary
        logger.info("\n📊 Results Summary:")
        logger.info("-" * 30)
        
        if 'temperature_statistics' in results:
            temp_stats = results['temperature_statistics']
            valid_temps = temp_stats['temperature'][~temp_stats['temperature'].isna()]
            if len(valid_temps) > 0:
                logger.info(f"🌡️  Temperature points: {len(temp_stats)} total, {len(valid_temps)} valid")
                logger.info(f"   Mean: {valid_temps.mean():.1f}°C")
                logger.info(f"   Range: {valid_temps.min():.1f}°C - {valid_temps.max():.1f}°C")
            else:
                logger.info("🌡️  No valid temperature data extracted")
        
        if 'hot_spots' in results:
            hotspots = results['hot_spots']
            logger.info(f"🔥 Heat island hotspots: {len(hotspots)}")
        
        if 'land_use_correlation' in results:
            correlations = results['land_use_correlation']['correlations']
            logger.info(f"🏗️  Land use correlations: {len(correlations)} analyzed")
            
            # Show overall correlation if available
            if 'overall' in correlations:
                overall = correlations['overall']
                logger.info(f"   Overall temp-imperviousness correlation: {overall['correlation']:.3f}")
        
        # Generate visualization
        logger.info("🎨 Creating visualization...")
        viz_path = output_dir / f"uhi_analysis_{start_date}_to_{end_date}.png"
        
        # Store boundary data temporarily for visualization
        import geopandas as gpd
        boundary_gdf = gpd.read_file(boundary_file)
        analyzer.city_boundary = boundary_gdf  # Set the missing attribute
        
        analyzer.visualize_results(results, str(viz_path))
        logger.info(f"   Saved to: {viz_path}")
        
        # Save detailed summary
        summary_path = output_dir / "analysis_summary.txt"
        with open(summary_path, 'w') as f:
            f.write(f"Urban Heat Island Analysis Results\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Analysis completed: {date.today()}\n")
            f.write(f"Period: {start_date} to {end_date}\n")
            f.write(f"Boundary data: {boundary_file.name}\n")
            f.write(f"Land cover data: {landcover_file.name}\n")
            f.write(f"Weather data: {weather_file.name if weather_file else 'None (satellite only)'}\n")
            f.write(f"Cloud threshold: 20%\n\n")
            
            if 'temperature_statistics' in results:
                temp_stats = results['temperature_statistics']
                valid_temps = temp_stats['temperature'][~temp_stats['temperature'].isna()]
                f.write(f"Temperature Analysis:\n")
                f.write(f"- Grid cells: {len(temp_stats)}\n")
                f.write(f"- Valid temperatures: {len(valid_temps)}\n")
                if len(valid_temps) > 0:
                    f.write(f"- Mean temperature: {valid_temps.mean():.1f}°C\n")
                    f.write(f"- Temperature range: {valid_temps.min():.1f}°C - {valid_temps.max():.1f}°C\n")
                f.write("\n")
            
            if 'hot_spots' in results:
                f.write(f"Hotspots identified: {len(results['hot_spots'])}\n\n")
            
            if 'mitigation_recommendations' in results:
                f.write("Recommendations:\n")
                for i, rec in enumerate(results['mitigation_recommendations'], 1):
                    f.write(f"{i}. {rec.get('description', 'N/A')}\n")
        
        logger.info(f"📄 Summary saved to: {summary_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        logger.error("\n🔧 Troubleshooting:")
        logger.error("1. Ensure Google Earth Engine authentication: earthengine authenticate")
        logger.error("2. Check internet connection")
        logger.error("3. Verify downloaded data files are valid")
        return False


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description="Dynamic Urban Heat Island Analysis for Berlin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --start-date 2022-06-01 --end-date 2022-08-31 --suburb "Mitte"
  %(prog)s --start-date 2022-01-01 --end-date 2022-12-31 --suburb "Charlottenburg-Wilmersdorf"
  %(prog)s --start-date 2023-07-01 --end-date 2023-07-31 --suburb "Kreuzberg" --output-dir custom_output
        """
    )
    
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start date for analysis (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--end-date", 
        required=True,
        help="End date for analysis (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--suburb",
        required=True,
        help="Berlin suburb/locality name (e.g., 'Mitte', 'Charlottenburg-Wilmersdorf')"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for results (default: data/processed/uhi_analysis_SUBURB_STARTDATE_ENDDATE)"
    )
    
    parser.add_argument(
        "--cloud-threshold",
        type=int,
        default=20,
        help="Cloud cover threshold percentage (default: 20)"
    )
    
    parser.add_argument(
        "--skip-weather",
        action="store_true", 
        help="Skip weather data download (use satellite data only)"
    )
    
    parser.add_argument(
        "--keep-temp-data",
        action="store_true",
        help="Keep downloaded temporary data files"
    )
    
    args = parser.parse_args()
    
    try:
        # Validate dates
        start_date, end_date = validate_dates(args.start_date, args.end_date)
        
        # Set output directory
        if args.output_dir:
            output_dir = args.output_dir
        else:
            suburb_clean = args.suburb.lower().replace(' ', '_').replace('-', '_')
            output_dir = Path("data") / "processed" / f"uhi_analysis_{suburb_clean}_{start_date}_{end_date}"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logger = setup_logging(output_dir)
        
        print("🌡️  Dynamic Urban Heat Island Analysis")
        print("=" * 50)
        print(f"📅 Analysis period: {start_date} to {end_date}")
        print(f"🏙️  Suburb: {args.suburb}")
        print(f"📁 Output directory: {output_dir}")
        print(f"☁️  Cloud threshold: {args.cloud_threshold}%")
        print()
        
        # Step 1: Download boundary data
        boundary_file = download_boundary_data(args.suburb, output_dir, logger)
        if not boundary_file:
            print("❌ Failed to download boundary data. Exiting.")
            sys.exit(1)
        
        # Step 2: Download land cover data
        landcover_file = download_landcover_data(boundary_file, start_date, end_date, output_dir, logger)
        if not landcover_file:
            print("❌ Failed to download land cover data. Exiting.")
            sys.exit(1)
        
        # Step 3: Download weather data (optional)
        weather_file = None
        if not args.skip_weather:
            weather_file = download_weather_data(boundary_file, start_date, end_date, output_dir, logger)
        
        # Step 4: Run UHI analysis
        success = run_uhi_analysis(
            boundary_file, landcover_file, weather_file,
            start_date, end_date, output_dir, logger
        )
        
        if success:
            print(f"\n🎉 UHI analysis completed successfully!")
            print(f"📁 Results saved to: {output_dir}")
            
            # Clean up temporary data if requested
            if not args.keep_temp_data:
                temp_dirs = ['boundaries', 'landcover', 'weather']
                for temp_dir in temp_dirs:
                    temp_path = output_dir / temp_dir
                    if temp_path.exists():
                        shutil.rmtree(temp_path)
                        logger.info(f"   🧹 Cleaned up temporary directory: {temp_path}")
            
        else:
            print("❌ UHI analysis failed. Check logs for details.")
            sys.exit(1)
            
    except ValueError as e:
        print(f"❌ Invalid input: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()