#!/usr/bin/env python3
"""
Integration tests for CorineDataDownloader functionality with date ranges.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from uhi_analyzer.data.corine_downloader import CorineDataDownloader
from uhi_analyzer.config import CORINE_YEARS, get_best_corine_year_for_date_range

def setup_logging():
    """Configures the logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/corine_test.log')
        ]
    )
    return logging.getLogger(__name__)

def test_date_range_selection():
    """Tests the automatic year selection for date ranges."""
    logger = setup_logging()
    
    logger.info("=== Test of date range year selection ===")
    logger.info(f"Available Corine years: {CORINE_YEARS}")
    
    # Test various date ranges
    test_ranges = [
        (1985, 1995),    # Before all available years
        (1990, 1995),    # Contains 1990
        (1995, 2005),    # Contains 2000
        (2003, 2008),    # Contains 2006
        (2010, 2015),    # Contains 2012
        (2015, 2020),    # Contains 2018
        (2020, 2025),    # After all available years
        (2018, 2022),    # Contains 2018
        (2022, 2024),    # After all available years
    ]
    
    for start_year, end_year in test_ranges:
        try:
            selected_year = get_best_corine_year_for_date_range(start_year, end_year)
            logger.info(f"Period {start_year}-{end_year} -> Selected year: {selected_year}")
        except Exception as e:
            logger.error(f"Error for period {start_year}-{end_year}: {e}")

def test_downloader_initialization():
    """Tests the initialization of CorineDataDownloader with various date ranges."""
    logger = setup_logging()
    
    logger.info("=== Test of CorineDataDownloader initialization ===")
    
    # Test various date ranges
    test_cases = [
        # (start_date, end_date, description)
        (2020, 2022, "One year period"),
        ("2021-06", "2021-12", "6 month period"),
        (2018, 2023, "5 year period"),
        ("2020-01-01", "2020-12-31", "One year with date strings"),
        (datetime(2019, 6, 1), datetime(2021, 8, 31), "With datetime objects"),
        (2015, 2017, "Short period"),
        (2025, 2027, "Future period"),
    ]
    
    for start_date, end_date, description in test_cases:
        logger.info(f"\n--- Test: {description} ---")
        logger.info(f"Start: {start_date}, End: {end_date}")
        try:
            downloader = CorineDataDownloader(start_date=start_date, end_date=end_date, logger=logger)
            logger.info(f"✓ Downloader initialized successfully")
            logger.info(f"  Period: {downloader.start_year}-{downloader.end_year}")
            logger.info(f"  Selected Corine year: {downloader.selected_year}")
        except Exception as e:
            logger.error(f"✗ Error during initialization: {e}")

def test_date_format_parsing():
    """Tests parsing of various date formats."""
    logger = setup_logging()
    
    logger.info("=== Test of date format parsing ===")
    
    test_formats = [
        (2022, "Integer year"),
        ("2022", "String year"),
        ("2022-06-15", "ISO date"),
        ("2022-06", "Year-month"),
        (datetime(2022, 6, 15), "datetime object"),
    ]
    
    for date_input, description in test_formats:
        logger.info(f"\n--- Test: {description} ---")
        logger.info(f"Input: {date_input} (Type: {type(date_input)})")
        try:
            downloader = CorineDataDownloader(start_date=date_input, end_date=2023, logger=logger)
            logger.info(f"✓ Successfully parsed: {downloader.start_year}")
        except Exception as e:
            logger.error(f"✗ Parsing error: {e}")

def test_error_handling():
    """Tests error handling for invalid inputs."""
    logger = setup_logging()
    
    logger.info("=== Test of error handling ===")
    
    error_cases = [
        (2023, 2022, "Start after end"),
        ("invalid", 2022, "Invalid start date"),
        (2022, "invalid", "Invalid end date"),
        ("2022-13-01", 2023, "Invalid month"),
        ("2022-12-32", 2023, "Invalid day"),
    ]
    
    for start_date, end_date, description in error_cases:
        logger.info(f"\n--- Test: {description} ---")
        logger.info(f"Start: {start_date}, End: {end_date}")
        try:
            downloader = CorineDataDownloader(start_date=start_date, end_date=end_date, logger=logger)
            logger.warning(f"⚠ Expected error did not occur!")
        except Exception as e:
            logger.info(f"✓ Expected error caught: {type(e).__name__}: {e}")

def test_actual_download():
    """Tests an actual download with various date ranges."""
    logger = setup_logging()
    
    logger.info("=== Test of actual download ===")
    
    # Use a small test GeoJSON file
    test_geojson = Path("data/raw/boundaries/berlin_admin_boundaries.geojson")
    
    if not test_geojson.exists():
        logger.warning(f"Test GeoJSON file not found: {test_geojson}")
        logger.info("Skipping download test")
        return
    
    # Test with various date ranges
    test_ranges = [
        (2020, 2022, "Short period"),
        (2018, 2023, "Longer period"),
    ]
    
    for start_year, end_year, description in test_ranges:
        logger.info(f"\n--- Download test: {description} ({start_year}-{end_year}) ---")
        try:
            downloader = CorineDataDownloader(start_date=start_year, end_date=end_year, logger=logger)
            
            # Test bounding box extraction
            bbox = downloader.get_bbox_from_geojson(test_geojson)
            logger.info(f"✓ Bounding box extracted: {bbox}")
            
            # Test URL building
            url = downloader.build_query_url(bbox, offset=0)
            logger.info(f"✓ Query URL created: {url[:100]}...")
            
            # Optional: Full download (commented out for performance reasons)
            # output_path = downloader.download_and_save(test_geojson)
            # logger.info(f"✓ Download completed: {output_path}")
            
        except Exception as e:
            logger.error(f"✗ Error during download test: {e}")

if __name__ == "__main__":
    print("CorineDataDownloader Date Range Test")
    print("=" * 50)
    
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Run tests
    test_date_range_selection()
    test_downloader_initialization()
    test_date_format_parsing()
    test_error_handling()
    test_actual_download()
    
    print("\nTests completed. Check the logs for details.") 