"""
WFS downloader class for various geodata services.

This class enables easy downloading of geodata via WFS services
with configurable endpoints and various output formats.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from urllib.parse import urlencode
import requests
import geopandas as gpd


class WFSDataDownloader:
    """
    Class for downloading geodata via WFS services.
    
    Attributes:
        config: WFS configuration with endpoints
        headers: HTTP headers for requests
        timeout: Timeout for HTTP requests
        logger: Logger instance
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        log_file: Optional[Path] = None
    ):
        """
        Initializes the WFSDataDownloader.
        
        Args:
            config: WFS configuration (from wfs_config.py)
            headers: Optional HTTP headers
            timeout: Timeout in seconds
            log_file: Optional path for log file
        """
        self.config = config
        self.timeout = timeout
        self.logger = self._setup_logger(log_file)
        
        # Default headers if none provided
        self.headers = headers or {
            "User-Agent": "Urban-Heat-Island-Analyzer/1.0",
            "Accept": "application/json,application/geojson"
        }
    
    def _setup_logger(self, log_file: Optional[Path] = None) -> logging.Logger:
        """Sets up the logger."""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        logger.setLevel(logging.INFO)
        
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
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def build_wfs_url(self, endpoint_name: str, **kwargs) -> str:
        """
        Builds the WFS URL with the appropriate parameters.
        
        Args:
            endpoint_name: Name of the endpoint from the configuration
            **kwargs: Additional parameters for the URL
            
        Returns:
            Complete WFS URL
            
        Raises:
            KeyError: If endpoint not found in configuration
        """
        if endpoint_name not in self.config:
            raise KeyError(f"Endpoint '{endpoint_name}' not found in configuration")
        
        endpoint_config = self.config[endpoint_name]
        
        # Base parameters
        params = {
            'service': endpoint_config['service'],
            'version': endpoint_config['version'],
            'request': endpoint_config['request'],
            'typeNames': endpoint_config['typeName'],
            'outputFormat': endpoint_config['outputFormat'],
            'srsName': endpoint_config['srsName']
        }
        
        # Add additional parameters
        params.update(kwargs)
        
        return f"{endpoint_config['url']}?{urlencode(params)}"
    
    def download_data(
        self,
        endpoint_name: str,
        output_path: Union[str, Path],
        **kwargs
    ) -> bool:
        """
        Downloads data from the WFS service and saves it.
        
        Args:
            endpoint_name: Name of the endpoint from the configuration
            output_path: Path for the output file
            **kwargs: Additional parameters for the WFS URL
            
        Returns:
            True if successful, False otherwise
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Build WFS URL
            wfs_url = self.build_wfs_url(endpoint_name, **kwargs)
            self.logger.info(f"Downloading data from: {wfs_url}")
            
            # Download data
            response = requests.get(
                wfs_url,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'json' in content_type or 'geojson' in content_type:
                # Save as GeoJSON
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                self.logger.info(f"Data successfully saved: {output_path}")
                return True
            else:
                self.logger.error(f"Unexpected response format: {content_type}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Download error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False
    
    def validate_geojson(self, file_path: Union[str, Path]) -> bool:
        """
        Validates a GeoJSON file.
        
        Args:
            file_path: Path to the GeoJSON file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            gdf = gpd.read_file(file_path)
            self.logger.info(f"GeoJSON validated: {len(gdf)} features found")
            self.logger.info(f"CRS: {gdf.crs}")
            return True
        except Exception as e:
            self.logger.error(f"GeoJSON validation failed: {e}")
            return False
    
    def download_and_validate(
        self,
        endpoint_name: str,
        output_path: Union[str, Path],
        validate: bool = True,
        **kwargs
    ) -> bool:
        """
        Downloads data and optionally validates it.
        
        Args:
            endpoint_name: Name of the endpoint from the configuration
            output_path: Path for the output file
            validate: Whether to validate the GeoJSON
            **kwargs: Additional parameters for the WFS URL
            
        Returns:
            True if successful, False otherwise
        """
        # Download data
        if not self.download_data(endpoint_name, output_path, **kwargs):
            return False
        
        # Optionally validate
        if validate:
            if not self.validate_geojson(output_path):
                return False
        
        return True
    
    def get_available_endpoints(self) -> list:
        """
        Returns all available endpoints.
        
        Returns:
            List of endpoint names
        """
        return list(self.config.keys())
    
    def get_endpoint_info(self, endpoint_name: str) -> Dict[str, Any]:
        """
        Returns information about an endpoint.
        
        Args:
            endpoint_name: Name of the endpoint
            
        Returns:
            Endpoint configuration
            
        Raises:
            KeyError: If endpoint not found
        """
        if endpoint_name not in self.config:
            raise KeyError(f"Endpoint '{endpoint_name}' not found")
        
        return self.config[endpoint_name].copy() 