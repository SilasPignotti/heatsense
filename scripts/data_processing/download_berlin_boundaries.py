#!/usr/bin/env python3
"""
Download Berlin administrative boundaries using WFS service.

This script uses the WFSDataDownloader class to download Berlin's administrative boundaries
via the WFS service of the Berlin Geodata Infrastructure.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from src.uhi_analyzer.data import WFSDataDownloader
from src.uhi_analyzer.config.wfs_config import BERLIN_ADMIN_BOUNDARIES_CONFIG

def main():
    """Download Berlin administrative boundaries."""
    
    # Initialize WFS-DataDownloader
    downloader = WFSDataDownloader(
        config=BERLIN_ADMIN_BOUNDARIES_CONFIG
    )
    
    # Output directory
    output_dir = Path(__file__).parent.parent.parent / "data" / "raw" / "boundaries"
    output_file = output_dir / "berlin_admin_boundaries.geojson"
    
    # Log file for better tracking
    log_file = Path(__file__).parent.parent.parent / "logs" / "wfs_downloads.log"
    
    # Show available endpoints
    print(f"Available endpoints: {downloader.get_available_endpoints()}")
    
    # Download and validate data
    success = downloader.download_and_validate(
        endpoint_name="berlin_admin_boundaries",
        output_path=output_file,
        validate=True
    )
    
    if success:
        print("✅ Download of Berlin administrative boundaries completed successfully")
        return True
    else:
        print("❌ Download failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 