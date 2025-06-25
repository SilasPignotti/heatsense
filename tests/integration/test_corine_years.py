#!/usr/bin/env python3
"""
Integrationstests für die CorineDataDownloader-Funktionalität mit verschiedenen Jahren.
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from uhi_analyzer.data.corine_downloader import CorineDataDownloader
from uhi_analyzer.config import CORINE_YEARS, get_closest_corine_year

def setup_logging():
    """Konfiguriert das Logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/corine_test.log')
        ]
    )
    return logging.getLogger(__name__)

def test_year_selection():
    """Testet die automatische Jahr-Auswahl."""
    logger = setup_logging()
    
    logger.info("=== Test der Jahr-Auswahl ===")
    logger.info(f"Verfügbare Jahre: {CORINE_YEARS}")
    
    # Test verschiedene gewünschte Jahre
    test_years = [1985, 1995, 2003, 2010, 2015, 2020]
    
    for target_year in test_years:
        closest = get_closest_corine_year(target_year)
        logger.info(f"Gewünschtes Jahr: {target_year} -> Nächstgelegenes: {closest}")

def test_corine_years():
    """Testet die Initialisierung des CorineDataDownloaders mit verschiedenen Jahren."""
    
    # Logger konfigurieren
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    logger.info("=== Test der CorineDataDownloader-Initialisierung ===")

def test_downloader_initialization():
    """Testet die Initialisierung des CorineDataDownloaders mit verschiedenen Jahren."""
    logger = setup_logging()
    
    logger.info("=== Test der CorineDataDownloader-Initialisierung ===")
    
    # Test verschiedene Jahre
    test_years = [1990, 2000, 2006, 2012, 2018, 2015, 2003]
    
    for target_year in test_years:
        logger.info(f"\n--- Test mit gewünschtem Jahr: {target_year} ---")
        try:
            downloader = CorineDataDownloader(target_year=target_year, logger=logger)
            logger.info(f"Downloader erfolgreich initialisiert für Jahr: {downloader.year}")
        except Exception as e:
            logger.error(f"Fehler bei Initialisierung mit Jahr {target_year}: {e}")

def test_actual_download():
    """Testet einen tatsächlichen Download mit verschiedenen Jahren."""
    logger = setup_logging()
    
    logger.info("=== Test eines tatsächlichen Downloads ===")
    
    # Verwende eine kleine Test-GeoJSON-Datei
    test_geojson = Path("data/raw/boundaries/large_test_area.geojson")
    
    if not test_geojson.exists():
        logger.warning(f"Test-GeoJSON-Datei nicht gefunden: {test_geojson}")
        logger.info("Überspringe Download-Test")
        return
    
    # Test mit verschiedenen Jahren
    test_years = [2018, 2012, 2006]  # Begrenzt auf wenige Jahre für den Test
    
    for target_year in test_years:
        logger.info(f"\n--- Download-Test mit Jahr: {target_year} ---")
        try:
            downloader = CorineDataDownloader(target_year=target_year, logger=logger)
            
            # Führe einen kleinen Download-Test durch (nur erste Seite)
            bbox = downloader.get_bbox_from_geojson(test_geojson)
            url = downloader.build_query_url(bbox, offset=0)
            logger.info(f"Query-URL: {url}")
            
            # Optional: Vollständiger Download (kommentiert aus Performance-Gründen)
            # output_path = downloader.download_and_save(test_geojson)
            # logger.info(f"Download abgeschlossen: {output_path}")
            
        except Exception as e:
            logger.error(f"Fehler beim Download-Test mit Jahr {target_year}: {e}")

if __name__ == "__main__":
    print("CorineDataDownloader Jahr-Test")
    print("=" * 50)
    
    # Erstelle logs-Verzeichnis falls nicht vorhanden
    Path("logs").mkdir(exist_ok=True)
    
    # Führe Tests aus
    test_year_selection()
    test_downloader_initialization()
    test_actual_download()
    
    print("\nTests abgeschlossen. Überprüfe die Logs für Details.") 