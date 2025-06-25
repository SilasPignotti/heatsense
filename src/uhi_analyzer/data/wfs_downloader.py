"""
WFS Data Downloader for Geospatial Applications.

This module provides a comprehensive WFS (Web Feature Service) downloader
for accessing various geodata services with flexible configuration and
multiple output formats. It is designed to be reusable across different
geospatial projects and applications.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple
from urllib.parse import urlencode, urlparse
import requests
import geopandas as gpd
import json
from xml.etree import ElementTree as ET


class WFSDataDownloader:
    """
    Comprehensive WFS downloader for geodata services.
    
    Features:
    - Multiple endpoint support with flexible configuration
    - Various output formats (GeoJSON, GML, Shapefile, GeoPackage, etc.)
    - Automatic retry mechanism with exponential backoff
    - Coordinate reference system transformation
    - Data validation and error handling
    - Comprehensive logging
    
    Attributes:
        endpoints: Dictionary of WFS endpoint configurations
        headers: HTTP headers for requests
        timeout: Request timeout in seconds
        max_features: Maximum features per request
        retry_attempts: Number of retry attempts on failure
        retry_delay: Delay between retries in seconds
        logger: Logger instance
    """
    
    def __init__(
        self,
        endpoints: Optional[Dict[str, Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        max_features: int = 10000,
        retry_attempts: int = 3,
        retry_delay: int = 2,
        log_file: Optional[Union[str, Path]] = None
    ):
        """
        Initialize the WFS downloader.
        
        Args:
            endpoints: WFS endpoint configurations (uses default if None)
            headers: HTTP headers for requests
            timeout: Request timeout in seconds
            max_features: Maximum features per request
            retry_attempts: Number of retry attempts on failure
            retry_delay: Delay between retries in seconds
            log_file: Optional log file path
        """
        # Import here to avoid circular imports
        from ..config.settings import (
            WFS_ENDPOINTS, WFS_HEADERS, WFS_TIMEOUT, 
            WFS_MAX_FEATURES, WFS_RETRY_ATTEMPTS, WFS_RETRY_DELAY
        )
        
        self.endpoints = endpoints or WFS_ENDPOINTS
        self.headers = headers or WFS_HEADERS
        self.timeout = timeout or WFS_TIMEOUT
        self.max_features = max_features or WFS_MAX_FEATURES
        self.retry_attempts = retry_attempts or WFS_RETRY_ATTEMPTS
        self.retry_delay = retry_delay or WFS_RETRY_DELAY
        self.logger = self._setup_logger(log_file)
    
    def _setup_logger(self, log_file: Optional[Union[str, Path]] = None) -> logging.Logger:
        """Set up logger with console and optional file output."""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if logger.handlers:
            return logger
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler (if provided)
        if log_file:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def get_available_endpoints(self) -> List[str]:
        """Get list of available endpoint names."""
        return list(self.endpoints.keys())
    
    def get_endpoint_info(self, endpoint_name: str) -> Dict[str, Any]:
        """
        Get information about a specific endpoint.
        
        Args:
            endpoint_name: Name of the endpoint
            
        Returns:
            Endpoint configuration dictionary
            
        Raises:
            KeyError: If endpoint not found
        """
        if endpoint_name not in self.endpoints:
            available = ', '.join(self.get_available_endpoints())
            raise KeyError(
                f"Endpoint '{endpoint_name}' not found. "
                f"Available endpoints: {available}"
            )
        
        return self.endpoints[endpoint_name].copy()
    
    def build_wfs_url(
        self, 
        endpoint_name: str,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        cql_filter: Optional[str] = None,
        max_features: Optional[int] = None,
        output_format: Optional[str] = None,
        srs_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Build WFS URL with parameters.
        
        Args:
            endpoint_name: Name of the endpoint
            bbox: Bounding box as (minx, miny, maxx, maxy)
            cql_filter: CQL filter for features
            max_features: Maximum number of features
            output_format: Output format (overrides endpoint default)
            srs_name: Coordinate reference system (overrides endpoint default)
            **kwargs: Additional URL parameters
            
        Returns:
            Complete WFS URL
            
        Raises:
            KeyError: If endpoint not found
        """
        endpoint_config = self.get_endpoint_info(endpoint_name)
        
        # Base parameters
        params = {
            'service': endpoint_config['service'],
            'version': endpoint_config['version'], 
            'request': endpoint_config['request'],
            'typeNames': endpoint_config['typeName'],
            'outputFormat': output_format or endpoint_config['outputFormat'],
            'srsName': srs_name or endpoint_config['srsName']
        }
        
        # Add optional parameters
        if bbox:
            params['bbox'] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        
        if cql_filter:
            params['CQL_FILTER'] = cql_filter
        
        if max_features is not None:
            params['maxFeatures'] = max_features
        elif self.max_features:
            params['maxFeatures'] = self.max_features
        
        # Add additional parameters
        params.update(kwargs)
        
        base_url = endpoint_config['url']
        url = f"{base_url}?{urlencode(params)}"
        
        self.logger.debug(f"Built WFS URL: {url}")
        return url
    
    def _make_request(self, url: str) -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            url: URL to request
            
        Returns:
            HTTP response
            
        Raises:
            requests.RequestException: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                self.logger.debug(f"Request attempt {attempt + 1}/{self.retry_attempts}: {url}")
                
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.retry_attempts}): {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"All {self.retry_attempts} request attempts failed")
        
        raise last_exception
    
    def _validate_response(self, response: requests.Response) -> bool:
        """
        Validate WFS response.
        
        Args:
            response: HTTP response to validate
            
        Returns:
            True if response is valid
        """
        content_type = response.headers.get('content-type', '').lower()
        
        # Check for error responses
        if 'xml' in content_type:
            try:
                root = ET.fromstring(response.text)
                # Check for OGC exception reports
                if 'exception' in root.tag.lower():
                    self.logger.error(f"WFS service returned exception: {response.text}")
                    return False
            except ET.ParseError:
                pass
        
        # Check for valid content types
        valid_types = ['json', 'geojson', 'xml', 'gml']
        if not any(vtype in content_type for vtype in valid_types):
            self.logger.warning(f"Unexpected content type: {content_type}")
        
        return True
    
    def download_to_geodataframe(
        self,
        endpoint_name: str,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        cql_filter: Optional[str] = None,
        max_features: Optional[int] = None,
        target_crs: Optional[str] = None,
        **kwargs
    ) -> gpd.GeoDataFrame:
        """
        Download WFS data directly to GeoDataFrame.
        
        Args:
            endpoint_name: Name of the endpoint
            bbox: Bounding box as (minx, miny, maxx, maxy)
            cql_filter: CQL filter for features
            max_features: Maximum number of features
            target_crs: Target coordinate reference system
            **kwargs: Additional WFS parameters
            
        Returns:
            GeoDataFrame with downloaded data
            
        Raises:
            Exception: If download or processing fails
        """
        self.logger.info(f"Downloading data from endpoint: {endpoint_name}")
        
        try:
            # Build URL
            url = self.build_wfs_url(
                endpoint_name=endpoint_name,
                bbox=bbox,
                cql_filter=cql_filter, 
                max_features=max_features,
                output_format="application/json",
                **kwargs
            )
            
            # Make request
            response = self._make_request(url)
            
            # Validate response
            if not self._validate_response(response):
                raise ValueError("Invalid WFS response received")
            
            # Parse to GeoDataFrame
            gdf = gpd.read_file(response.text)
            
            if gdf.empty:
                self.logger.warning("No features returned from WFS service")
                return gdf
            
            self.logger.info(f"Downloaded {len(gdf)} features")
            
            # Transform CRS if requested
            if target_crs and gdf.crs != target_crs:
                self.logger.info(f"Transforming from {gdf.crs} to {target_crs}")
                gdf = gdf.to_crs(target_crs)
            
            # Log basic statistics
            if hasattr(gdf, 'geometry') and not gdf.geometry.empty:
                bounds = gdf.total_bounds
                self.logger.info(f"Data bounds: {bounds}")
                self.logger.info(f"CRS: {gdf.crs}")
            
            return gdf
            
        except Exception as e:
            self.logger.error(f"Failed to download data from {endpoint_name}: {e}")
            raise
    
    def download_and_save(
        self,
        endpoint_name: str,
        output_path: Union[str, Path],
        output_format: str = "geojson",
        bbox: Optional[Tuple[float, float, float, float]] = None,
        cql_filter: Optional[str] = None,
        max_features: Optional[int] = None,
        target_crs: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Download WFS data and save to file.
        
        Args:
            endpoint_name: Name of the endpoint
            output_path: Path for output file
            output_format: Output format ('geojson', 'gpkg', 'shp', 'gml')
            bbox: Bounding box as (minx, miny, maxx, maxy)
            cql_filter: CQL filter for features
            max_features: Maximum number of features
            target_crs: Target coordinate reference system
            **kwargs: Additional WFS parameters
            
        Returns:
            True if successful, False otherwise
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Download to GeoDataFrame
            gdf = self.download_to_geodataframe(
                endpoint_name=endpoint_name,
                bbox=bbox,
                cql_filter=cql_filter,
                max_features=max_features,
                target_crs=target_crs,
                **kwargs
            )
            
            if gdf.empty:
                self.logger.warning("No data to save")
                return False
            
            # Save in requested format
            if output_format.lower() == 'geojson':
                gdf.to_file(output_path, driver='GeoJSON')
            elif output_format.lower() == 'gpkg':
                gdf.to_file(output_path, driver='GPKG')
            elif output_format.lower() == 'shp':
                gdf.to_file(output_path, driver='ESRI Shapefile')
            elif output_format.lower() == 'gml':
                gdf.to_file(output_path, driver='GML')
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
            
            self.logger.info(f"Data saved to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download and save data: {e}")
            return False
    
    def get_feature_count(
        self,
        endpoint_name: str,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        cql_filter: Optional[str] = None,
        **kwargs
    ) -> int:
        """
        Get feature count without downloading all data.
        
        Args:
            endpoint_name: Name of the endpoint
            bbox: Bounding box as (minx, miny, maxx, maxy)
            cql_filter: CQL filter for features
            **kwargs: Additional WFS parameters
            
        Returns:
            Number of features available
        """
        try:
            url = self.build_wfs_url(
                endpoint_name=endpoint_name,
                bbox=bbox,
                cql_filter=cql_filter,
                max_features=1,
                **kwargs
            )
            
            # Modify request to get hit count
            url = url.replace('GetFeature', 'GetFeature&resultType=hits')
            
            response = self._make_request(url)
            
            # Parse XML response for hit count
            if 'xml' in response.headers.get('content-type', ''):
                root = ET.fromstring(response.text)
                for elem in root.iter():
                    if 'numberMatched' in elem.attrib:
                        return int(elem.attrib['numberMatched'])
                    elif 'numberOfFeatures' in elem.attrib:
                        return int(elem.attrib['numberOfFeatures'])
            
            # Fallback: download small sample and estimate
            gdf = self.download_to_geodataframe(
                endpoint_name=endpoint_name,
                bbox=bbox,
                cql_filter=cql_filter,
                max_features=1000,
                **kwargs
            )
            return len(gdf)
            
        except Exception as e:
            self.logger.warning(f"Could not get feature count: {e}")
            return 0
    
    def validate_endpoint(self, endpoint_name: str) -> bool:
        """
        Validate that an endpoint is accessible.
        
        Args:
            endpoint_name: Name of the endpoint to validate
            
        Returns:
            True if endpoint is accessible
        """
        try:
            self.logger.info(f"Validating endpoint: {endpoint_name}")
            
            # Try to get capabilities
            endpoint_config = self.get_endpoint_info(endpoint_name)
            capabilities_url = f"{endpoint_config['url']}?service=WFS&request=GetCapabilities"
            
            response = self._make_request(capabilities_url)
            
            if 'xml' in response.headers.get('content-type', ''):
                root = ET.fromstring(response.text)
                if 'capabilities' in root.tag.lower():
                    self.logger.info(f"Endpoint {endpoint_name} is accessible")
                    return True
            
            # Fallback: try small feature request
            gdf = self.download_to_geodataframe(
                endpoint_name=endpoint_name,
                max_features=1
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Endpoint validation failed for {endpoint_name}: {e}")
            return False
    
    @staticmethod
    def get_default_parameters() -> Dict[str, Any]:
        """Get default configuration parameters."""
        from ..config.settings import (
            WFS_ENDPOINTS, WFS_HEADERS, WFS_TIMEOUT,
            WFS_MAX_FEATURES, WFS_RETRY_ATTEMPTS, WFS_RETRY_DELAY
        )
        
        return {
            "endpoints": WFS_ENDPOINTS,
            "headers": WFS_HEADERS,
            "timeout": WFS_TIMEOUT,
            "max_features": WFS_MAX_FEATURES,
            "retry_attempts": WFS_RETRY_ATTEMPTS,
            "retry_delay": WFS_RETRY_DELAY
        } 