"""
WFS Data Downloader for Geospatial Applications.

Simple WFS downloader for accessing geodata services with minimal configuration.
"""

import logging
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
import requests
import geopandas as gpd
from xml.etree import ElementTree as ET


class WFSDataDownloader:
    """
    Simple WFS downloader for geodata services.
    
    Args:
        endpoint_url: Base URL of the WFS service
        headers: HTTP headers for requests (optional)
        timeout: Request timeout in seconds
        max_features: Maximum features per request
        retry_attempts: Number of retry attempts on failure
        retry_delay: Delay between retries in seconds
        log_file: Optional log file path
        verbose: Enable console logging (default: True)
    """
    
    def __init__(
        self,
        endpoint_url: str,
        headers: Optional[dict] = None,
        timeout: int = 30,
        max_features: int = 10000,
        retry_attempts: int = 3,
        retry_delay: int = 2,
        log_file: Optional[str] = None,
        verbose: bool = True
    ):
        self.endpoint_url = endpoint_url.rstrip('/')
        self.headers = headers or {
            "User-Agent": "Python-WFS-Downloader/1.0",
            "Accept": "application/json"
        }
        self.timeout = timeout
        self.max_features = max_features
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.logger = self._setup_logger(log_file) if verbose or log_file else None
    
    def _setup_logger(self, log_file: Optional[str] = None) -> logging.Logger:
        """Set up simple logger."""
        logger = logging.getLogger(f"{__name__}.WFSDataDownloader")
        
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            # Console handler
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            logger.addHandler(handler)
            
            # File handler
            if log_file:
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s: %(message)s'))
                logger.addHandler(file_handler)
        
        return logger
    
    def build_wfs_url(
        self, 
        type_name: str,
        max_features: Optional[int] = None,
        output_format: str = "application/json",
        target_crs: str = "EPSG:4326",
    ) -> str:
        """Build WFS URL with parameters."""
        params = {
            'service': 'WFS',
            'version': '2.0.0', 
            'request': 'GetFeature',
            'typeNames': type_name,
            'outputFormat': output_format,
            'outputCrs': target_crs,
            'maxFeatures': max_features or self.max_features
        }
        
        
        return f"{self.endpoint_url}?{urlencode(params)}"
    
    def _make_request(self, url: str) -> requests.Response:
        """Make HTTP request with retry logic."""
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                last_exception = e
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    if self.logger:
                        self.logger.warning(f"Request failed, retrying in {delay}s...")
                    time.sleep(delay)
        
        if self.logger:
            self.logger.error("All request attempts failed")
        raise last_exception
    
    def _validate_response(self, response: requests.Response) -> bool:
        """Simple response validation."""
        if 'xml' in response.headers.get('content-type', ''):
            try:
                root = ET.fromstring(response.text)
                if 'exception' in root.tag.lower():
                    if self.logger:
                        self.logger.error("WFS service returned an exception")
                    return False
            except ET.ParseError:
                pass
        return True
    
    def download_to_geodataframe(
        self,
        type_name: str,
        max_features: Optional[int] = None,
        target_crs: Optional[str] = None,
    ) -> gpd.GeoDataFrame:
        """
        Download WFS data to GeoDataFrame.
        
        Args:
            type_name: Feature type name
            bbox: Bounding box (minx, miny, maxx, maxy)
            cql_filter: CQL filter for features
            max_features: Maximum number of features
            target_crs: Target coordinate reference system
            **kwargs: Additional WFS parameters
            
        Returns:
            GeoDataFrame with downloaded data
        """
        if self.logger:
            self.logger.info(f"Downloading {type_name} from {self.endpoint_url}")
        
        # Build URL and make request
        url = self.build_wfs_url(
            type_name=type_name,
            max_features=max_features,
            target_crs=target_crs
        )
        
        response = self._make_request(url)
        
        if not self._validate_response(response):
            raise ValueError("Invalid WFS response")
        
        # Parse to GeoDataFrame
        gdf = gpd.read_file(response.text)
        
        if gdf.empty:
            if self.logger:
                self.logger.warning("No features returned")
            return gdf
        
        if self.logger:
            self.logger.info(f"Downloaded {len(gdf)} features")
        
        # Transform CRS if requested
        if target_crs and gdf.crs != target_crs:
            if self.logger:
                self.logger.info(f"Transforming to {target_crs}")
            gdf = gdf.to_crs(target_crs)
        
        return gdf