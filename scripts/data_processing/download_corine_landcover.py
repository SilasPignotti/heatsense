#!/usr/bin/env python3
"""
Script to download Corine Land Cover data for Berlin using CorineDataDownloader class.
Supports date ranges and automatically selects the best available Corine year.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from uhi_analyzer.data.corine_downloader import CorineDataDownloader
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
  {sys.argv[0]}                                    # Download data for 2022 (default)
  {sys.argv[0]} --start-date 2020 --end-date 2022 # Download data for 2020-2022 range
  {sys.argv[0]} --start-date 2018 --end-date 2023 # Download data for 2018-2023 range
  
Available Corine years: {CORINE_YEARS}
        """
    )
    
    parser.add_argument(
        "--start-date", 
        type=str, 
        default="2022",
        help="Start date for analysis period (YYYY, YYYY-MM-DD, or YYYY-MM) (default: 2022)"
    )
    
    parser.add_argument(
        "--end-date", 
        type=str, 
        default="2022",
        help="End date for analysis period (YYYY, YYYY-MM-DD, or YYYY-MM) (default: 2022)"
    )
    
    return parser.parse_args()


def main():
    args = parse_arguments()
    logger = setup_logging()
    
    logger.info(f"Starte Corine Download für Zeitraum: {args.start_date} bis {args.end_date}")
    
    # Pfade
    project_root = Path(__file__).parent.parent.parent
    berlin_geojson = project_root / "data" / "raw" / "boundaries" / "berlin_admin_boundaries.geojson"
    output_dir = project_root / "data" / "raw" / "landcover"
    
    # Erstelle output_dir falls nicht vorhanden
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Prüfe ob Berliner GeoJSON existiert
    if not berlin_geojson.exists():
        logger.error(f"Berliner GeoJSON nicht gefunden: {berlin_geojson}")
        logger.info("Bitte führe zuerst download_berlin_boundaries.py aus")
        sys.exit(1)
    
    # Downloader initialisieren mit Datumsbereich
    downloader = CorineDataDownloader(
        start_date=args.start_date, 
        end_date=args.end_date, 
        logger=logger
    )
    
    # Generiere Ausgabedateiname (immer gleich, unabhängig vom Jahr)
    output_file = output_dir / "berlin_corine_landcover.geojson"
    
    logger.info(f"Verwendetes Corine-Jahr: {downloader.selected_year}")
    logger.info(f"Ausgabedatei: {output_file}")
    
    # Daten herunterladen und speichern
    result_path = downloader.download_and_save(berlin_geojson, output_file)
    
    logger.info("Download und Verarbeitung erfolgreich abgeschlossen!")
    logger.info(f"Ausgabedatei: {result_path}")
    logger.info(f"Verwendetes Corine-Jahr: {downloader.selected_year}")


if __name__ == "__main__":
    main() 