"""
Web Feature Service (WFS) data downloader for geospatial boundaries.

This module provides functionality to download geospatial boundary data from
WFS endpoints with automatic retry logic and error handling. Commonly used for
administrative boundaries and reference datasets.

Dependencies:
    - requests: HTTP client for WFS requests
    - geopandas: Geospatial data processing
    - xml.etree.ElementTree: XML parsing for error detection
"""

import logging
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

import geopandas as gpd
import requests


class WFSDataDownloader:
    """
    Download geospatial features from Web Feature Service (WFS) endpoints.
    
    Provides reliable data access from WFS services with automatic retry logic,
    error handling, and coordinate reference system transformations.
    
    Args:
        endpoint_url: Base URL of the WFS service
        headers: Optional HTTP headers for requests
        timeout: Request timeout in seconds (default: 30)
        max_features: Default maximum features per request (default: 10000)
        retry_attempts: Number of retry attempts for failed requests (default: 3)
        retry_delay: Initial retry delay in seconds (default: 2)
        log_file: Optional path for detailed logging
        verbose: Enable console progress logging
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
            "User-Agent": "HeatSense-WFS-Client/1.0",
            "Accept": "application/json"
        }
        self.timeout = timeout
        self.max_features = max_features
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.logger = self._setup_logger(log_file) if verbose or log_file else None
        
        if self.logger:
            self.logger.info(f"WFS Downloader initialized for {self.endpoint_url}")
    
    def _setup_logger(self, log_file: Optional[str] = None) -> logging.Logger:
        """Configure logging with console and optional file output."""
        logger = logging.getLogger(f"{__name__}.WFSDataDownloader")
        
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            # Console output
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            logger.addHandler(console_handler)
            
            # File output if specified
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
        """
        Construct WFS GetFeature request URL with specified parameters.
        
        Args:
            type_name: WFS feature type identifier
            max_features: Maximum number of features to retrieve
            output_format: Response format (default: GeoJSON)
            target_crs: Target coordinate reference system
            
        Returns:
            Complete WFS request URL with encoded parameters
        """
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
        """Execute HTTP request with exponential backoff retry logic."""
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                last_exception = e
                if attempt < self.retry_attempts - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    if self.logger:
                        self.logger.warning(f"Request attempt {attempt + 1} failed, retrying in {delay}s")
                    time.sleep(delay)
        
        if self.logger:
            self.logger.error(f"All {self.retry_attempts} request attempts failed")
        raise last_exception
    
    def _validate_response(self, response: requests.Response) -> bool:
        """Validate WFS response and detect service exceptions."""
        content_type = response.headers.get('content-type', '').lower()
        
        # Check for XML-formatted error responses
        if 'xml' in content_type:
            try:
                root = ET.fromstring(response.text)
                if 'exception' in root.tag.lower():
                    if self.logger:
                        exception_text = root.text or "Unknown WFS exception"
                        self.logger.error(f"WFS service exception: {exception_text}")
                    return False
            except ET.ParseError:
                # Unable to parse XML, assume valid response
                pass
        
        return True
    
    def download_to_geodataframe(
        self,
        type_name: str,
        max_features: Optional[int] = None,
        target_crs: Optional[str] = None,
    ) -> gpd.GeoDataFrame:
        """
        Download WFS features and return as GeoDataFrame.
        
        Retrieves geospatial features from the WFS service with automatic retry
        handling and coordinate reference system transformation.
        
        Args:
            type_name: WFS feature type to download
            max_features: Limit number of features (default from settings)
            target_crs: Target coordinate reference system (default: EPSG:4326)
            
        Returns:
            GeoDataFrame containing downloaded features with geometries
            
        Raises:
            ValueError: If WFS service returns an exception or invalid data
            requests.RequestException: If all HTTP requests fail
        """
        if self.logger:
            self.logger.info(f"Requesting feature type '{type_name}' from WFS service")
        
        # Construct request URL
        url = self.build_wfs_url(
            type_name=type_name,
            max_features=max_features,
            target_crs=target_crs or "EPSG:4326"
        )
        
        # Execute request with retry logic
        response = self._make_request(url)
        
        # Validate response content
        if not self._validate_response(response):
            raise ValueError("WFS service returned an exception or invalid response")
        
        # Parse response to GeoDataFrame
        try:
            gdf = gpd.read_file(response.text)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to parse WFS response: {e}")
            raise ValueError(f"Unable to parse WFS response as GeoDataFrame: {e}")
        
        if gdf.empty:
            if self.logger:
                self.logger.warning(f"No features found for type '{type_name}'")
            return gdf
        
        # Apply coordinate transformation if needed
        if target_crs and gdf.crs and str(gdf.crs) != target_crs:
            if self.logger:
                self.logger.info(f"Transforming from {gdf.crs} to {target_crs}")
            gdf = gdf.to_crs(target_crs)
        
        if self.logger:
            self.logger.info(f"Successfully downloaded {len(gdf)} features")
        
        return gdf


if __name__ == "__main__":
    # Example usage for testing
    logging.basicConfig(level=logging.INFO)
    
    # Test with Berlin administrative boundaries
    berlin_wfs_url = "https://gdi.berlin.de/services/wfs/alkis_bezirke"
    downloader = WFSDataDownloader(berlin_wfs_url, verbose=True)
    
    try:
        # Download Berlin district boundaries
        districts_gdf = downloader.download_to_geodataframe(
            type_name="alkis_bezirke:bezirksgrenzen",
            max_features=20,
            target_crs="EPSG:4326"
        )
        print(f"Downloaded {len(districts_gdf)} district boundaries")
        print(f"Columns: {list(districts_gdf.columns)}")
        print(f"CRS: {districts_gdf.crs}")
    except Exception as e:
        print(f"Download failed: {e}")