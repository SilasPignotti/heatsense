#!/usr/bin/env python3
"""
Berlin Weather Data Downloader - Downloads temperature data for Berlin for a specified time period.
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
import sys
import json

# Add project path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from uhi_analyzer.data.dwd_downloader import DWDDataDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/berlin_weather_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_berlin_geometry() -> dict:
    """
    Loads the Berlin geometry from the GeoJSON file.
    
    Returns:
        dict: The geometry of Berlin as a GeoJSON object
    """
    berlin_geojson_path = Path("data/raw/boundaries/berlin_admin_boundaries.geojson")
    
    if not berlin_geojson_path.exists():
        raise FileNotFoundError(f"Berlin geometry not found: {berlin_geojson_path}")
    
    with open(berlin_geojson_path, 'r', encoding='utf-8') as f:
        geojson = json.load(f)
        if geojson.get("type") == "FeatureCollection":
            return geojson['features'][0]['geometry']
        elif geojson.get("type") in ["Polygon", "MultiPolygon"]:
            return geojson
        else:
            raise ValueError(f"Unexpected GeoJSON type: {geojson.get('type')}")


def download_berlin_weather(
    start_date: datetime,
    end_date: datetime,
    output_dir: str = "data/processed/weather",
    interpolate: bool = True,
    resolution: float = 30
) -> bool:
    """
    Downloads temperature data for Berlin for a specified time period.
    
    Args:
        start_date: Start date
        end_date: End date
        output_dir: Output directory
        interpolate: Whether to interpolate
        resolution: Resolution in meters
        
    Returns:
        bool: True if successful
    """
    logger.info(f"Downloading temperature data from {start_date.date()} to {end_date.date()}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load Berlin geometry
        berlin_geometry = load_berlin_geometry()
        
        # Initialize DWD downloader
        downloader = DWDDataDownloader()
        
        # Get weather data (average over the entire period)
        weather_data = downloader.get_weather_data(
            geometry=berlin_geometry,
            start_date=start_date,
            end_date=end_date,
            interpolate=interpolate,
            resolution=resolution
        )
        
        if weather_data.empty:
            logger.error(f"No weather data received for period {start_date.date()} to {end_date.date()}!")
            return False
        
        # Create output filename
        period_str = f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
        if interpolate:
            filename = f"berlin_temperature_{period_str}_interpolated.geojson"
        else:
            filename = f"berlin_temperature_{period_str}_stations.geojson"
        
        output_file = output_path / filename
        
        # Save as GeoJSON
        weather_data.to_file(output_file, driver="GeoJSON")
        
        logger.info(f"Successfully saved: {output_file}")
        
        # Statistics
        if interpolate:
            logger.info(f"  Interpolated points: {len(weather_data)}")
            logger.info(f"  Stations used: {weather_data['n_stations'].iloc[0]}")
        else:
            logger.info(f"  Stations: {len(weather_data)}")
        
        logger.info(f"  Temperature range: {weather_data['ground_temp'].min():.1f}°C - {weather_data['ground_temp'].max():.1f}°C")
        logger.info(f"  Average temperature: {weather_data['ground_temp'].mean():.1f}°C")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during download for period {start_date.date()} to {end_date.date()}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main function for command line interface."""
    parser = argparse.ArgumentParser(
        description="Downloads temperature data for Berlin for a specified time period"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed/weather",
        help="Output directory (default: data/processed/weather)"
    )
    parser.add_argument(
        "--no-interpolate",
        action="store_true",
        help="Don't perform interpolation, only station data"
    )
    parser.add_argument(
        "--resolution",
        type=float,
        default=30,
        help="Resolution of interpolation grid in meters (default: 30m)"
    )
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        sys.exit(1)
        
    if end_date < start_date:
        logger.error("End date must be after start date")
        sys.exit(1)
    
    # Create log directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Perform download
    success = download_berlin_weather(
        start_date=start_date,
        end_date=end_date,
        output_dir=args.output_dir,
        interpolate=not args.no_interpolate,
        resolution=args.resolution
    )
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main() 