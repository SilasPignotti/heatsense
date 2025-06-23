#!/usr/bin/env python3
"""
Script to download Corine Land Cover data for Berlin using CorineDownloader class.
Supports different years (1990, 2000, 2006, 2012, 2018).
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from uhi_analyzer.data.corine_downloader import CorineDownloader
from uhi_analyzer.config import CORINE_YEARS


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("corine_download")
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download Corine Land Cover data for Berlin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  {sys.argv[0]}                    # Download 2018 data (default)
  {sys.argv[0]} --year 2012       # Download 2012 data
  {sys.argv[0]} --year 2006       # Download 2006 data
  {sys.argv[0]} --year 2015       # Download 2012 data (closest to 2015)
  
Available years: {CORINE_YEARS}
        """
    )
    
    parser.add_argument(
        "--year", 
        type=int, 
        default=2018,
        help=f"Target year for Corine data (default: 2018, available: {CORINE_YEARS})"
    )
    
    return parser.parse_args()


def main():
    args = parse_arguments()
    logger = setup_logging()
    
    logger.info(f"Starte Corine Download für gewünschtes Jahr: {args.year}")
    
    # Pfade
    project_root = Path(__file__).parent.parent.parent
    berlin_geojson = project_root / "data" / "raw" / "boundaries" / "berlin_admin_boundaries.geojson"
    output_dir = project_root / "data" / "raw" / "landcover"
    
    # Prüfe ob Berliner GeoJSON existiert
    if not berlin_geojson.exists():
        logger.error(f"Berliner GeoJSON nicht gefunden: {berlin_geojson}")
        logger.info("Bitte führe zuerst download_berlin_boundaries.py aus")
        sys.exit(1)
    
    # Downloader initialisieren und Daten herunterladen & clippen
    downloader = CorineDownloader(target_year=args.year, logger=logger)
    
    # Generiere Ausgabedateiname basierend auf tatsächlich verwendetem Jahr
    output_file = output_dir / f"berlin_corine_landcover_{downloader.year}.geojson"
    
    result_path = downloader.download_and_save(berlin_geojson, output_file)
    
    logger.info("Download und Clipping erfolgreich abgeschlossen!")
    logger.info(f"Ausgabedatei: {result_path}")
    logger.info(f"Verwendetes Corine-Jahr: {downloader.year}")


if __name__ == "__main__":
    main() 