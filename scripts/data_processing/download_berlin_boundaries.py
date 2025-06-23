#!/usr/bin/env python3
"""
Script zum Download der Berliner Verwaltungsgrenzen vom WFS-Service.

Dieses Script nutzt die WFSDownloader-Klasse um die Verwaltungsgrenzen von Berlin
über einen WFS-Service herunterzuladen und als GeoJSON-Datei zu speichern.
"""

import sys
from pathlib import Path

# Projektroot zum Import der Module
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.uhi_analyzer.config import WFS_ENDPOINTS, WFS_HEADERS, WFS_TIMEOUT
from src.uhi_analyzer.data import WFSDownloader


def main():
    """Hauptfunktion zum Download der Berliner Verwaltungsgrenzen."""
    # Ausgabeverzeichnis
    output_dir = project_root / "data" / "raw" / "boundaries"
    output_file = output_dir / "berlin_admin_boundaries.geojson"
    
    # Log-Datei für bessere Nachverfolgung
    log_file = project_root / "logs" / "wfs_downloads.log"
    
    # WFS-Downloader initialisieren
    downloader = WFSDownloader(
        config=WFS_ENDPOINTS,
        headers=WFS_HEADERS,
        timeout=WFS_TIMEOUT,
        log_file=log_file
    )
    
    # Verfügbare Endpunkte anzeigen
    print(f"Verfügbare Endpunkte: {downloader.get_available_endpoints()}")
    
    # Daten herunterladen und validieren
    success = downloader.download_and_validate(
        endpoint_name="berlin_admin_boundaries",
        output_path=output_file,
        validate=True
    )
    
    if success:
        print("✅ Download der Berliner Verwaltungsgrenzen erfolgreich abgeschlossen")
        return True
    else:
        print("❌ Download fehlgeschlagen")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 