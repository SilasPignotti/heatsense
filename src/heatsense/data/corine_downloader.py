"""
CORINE Land Cover data downloader for Urban Heat Island analysis.

This module provides functionality to download CORINE Land Cover data from the
European Environment Agency's ArcGIS REST services. Supports flexible date/period
input and automatic coordinate system transformations.

Dependencies:
    - requests: HTTP client for API calls
    - geopandas: Geospatial data handling
    - pyproj: Coordinate reference system transformations
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Union
from urllib.parse import urlencode

import geopandas as gpd
import pandas as pd
import requests
from pyproj import Transformer

from ..config.settings import CORINE_BASE_URLS, CORINE_YEARS


class CorineDataDownloader:
    """
    Download CORINE Land Cover data for specified geographical areas and time periods.
    
    Automatically selects the most appropriate CORINE dataset year based on the
    requested analysis period and handles large area downloads through pagination.
    
    Args:
        year_or_period: Analysis year, date, or period tuple for data selection
        record_count: Maximum records per API request (default: 1000)
        timeout: HTTP request timeout in seconds (default: 30)
        verbose: Enable progress logging (default: True)
        log_file: Optional path for detailed logging
        corine_years: Available CORINE dataset years (from settings)
        corine_base_urls: Service URLs by year (from settings)
    """

    def __init__(
        self,
        year_or_period: Union[int, str, datetime, Tuple[Union[int, str, datetime], Union[int, str, datetime]]],
        record_count: int = 1000,
        timeout: int = 30,
        verbose: bool = True,
        log_file: Optional[str] = None,
        corine_years: List[int] = CORINE_YEARS,
        corine_base_urls: dict = CORINE_BASE_URLS
    ):
        self.record_count = record_count
        self.timeout = timeout
        self.corine_years = corine_years
        self.corine_base_urls = corine_base_urls
        self.logger = self._setup_logger(log_file) if verbose or log_file else None
        
        # Parse and validate input period
        self.start_year, self.end_year = self._parse_year_or_period(year_or_period)
        self.selected_year = self._get_best_year_for_range(self.start_year, self.end_year)
        self.base_url = self.corine_base_urls[self.selected_year]
        
        if self.logger:
            if self.start_year == self.end_year:
                self.logger.info(f"Using CORINE {self.selected_year} for analysis year {self.start_year}")
            else:
                self.logger.info(f"Using CORINE {self.selected_year} for period {self.start_year}-{self.end_year}")

    def _setup_logger(self, log_file: Optional[str] = None) -> logging.Logger:
        """Configure logging with console and optional file output."""
        logger = logging.getLogger(f"{__name__}.CorineDataDownloader")
        
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

    def _get_best_year_for_range(self, start_year: int, end_year: int) -> int:
        """Select the most appropriate CORINE dataset year for the analysis period."""
        if start_year > end_year:
            raise ValueError(f"Start year ({start_year}) must be before end year ({end_year})")
        
        # Find CORINE datasets within the requested period
        years_in_range = [year for year in self.corine_years if start_year <= year <= end_year]
        
        if years_in_range:
            # Use the most recent dataset within the period
            return max(years_in_range)
        else:
            # Use the dataset closest to the period midpoint
            midpoint = (start_year + end_year) / 2
            return min(self.corine_years, key=lambda x: abs(x - midpoint))

    def _parse_year_or_period(
        self, 
        year_or_period: Union[int, str, datetime, Tuple[Union[int, str, datetime], Union[int, str, datetime]]]
    ) -> Tuple[int, int]:
        """Parse various date input formats into start and end years."""
        if isinstance(year_or_period, tuple):
            start_year = self._extract_year(year_or_period[0])
            end_year = self._extract_year(year_or_period[1])
            return start_year, end_year
        else:
            year = self._extract_year(year_or_period)
            return year, year

    def _extract_year(self, date_input: Union[str, datetime, int]) -> int:
        """Extract year from various date input formats."""
        if isinstance(date_input, int):
            if date_input < 1900 or date_input > 2100:
                raise ValueError(f"Year {date_input} is outside valid range (1900-2100)")
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.year
        elif isinstance(date_input, str):
            # Handle 4-digit year strings
            if len(date_input) == 4 and date_input.isdigit():
                year = int(date_input)
                if year < 1900 or year > 2100:
                    raise ValueError(f"Year {year} is outside valid range (1900-2100)")
                return year
            # Handle date strings with separators
            elif '-' in date_input:
                try:
                    dt = datetime.strptime(date_input, "%Y-%m-%d")
                    return dt.year
                except ValueError:
                    try:
                        dt = datetime.strptime(date_input, "%Y-%m")
                        return dt.year
                    except ValueError:
                        raise ValueError(f"Invalid date format: {date_input}")
            else:
                raise ValueError(f"Unknown date format: {date_input}")
        else:
            raise ValueError(f"Unsupported date input type: {type(date_input)}")

    def get_bbox_from_geometry(self, geometry_input: Union[str, Path, gpd.GeoDataFrame]) -> Tuple[float, float, float, float]:
        """Extract bounding box from geometry and transform to Web Mercator projection."""
        if isinstance(geometry_input, (str, Path)):
            gdf = gpd.read_file(geometry_input)
        elif isinstance(geometry_input, gpd.GeoDataFrame):
            gdf = geometry_input.copy()
        else:
            raise ValueError(f"Unsupported geometry input type: {type(geometry_input)}")
        
        # Set default CRS if missing
        if gdf.crs is None:
            if self.logger:
                self.logger.warning("No CRS specified, assuming WGS84 (EPSG:4326)")
            gdf.set_crs("EPSG:4326", inplace=True)
        
        # Get original bounds
        bbox_original = gdf.total_bounds  # (xmin, ymin, xmax, ymax)
        
        # Transform to Web Mercator for CORINE service compatibility
        if gdf.crs != "EPSG:3857":
            transformer = Transformer.from_crs(gdf.crs, "EPSG:3857", always_xy=True)
            xmin, ymin = transformer.transform(bbox_original[0], bbox_original[1])
            xmax, ymax = transformer.transform(bbox_original[2], bbox_original[3])
            return (xmin, ymin, xmax, ymax)
        else:
            return tuple(bbox_original)

    def build_query_url(self, bbox: Tuple[float, float, float, float], offset: int = 0, target_crs: str = "EPSG:4326") -> str:
        """Construct ArcGIS REST API query URL with spatial and pagination parameters."""
        xmin, ymin, xmax, ymax = bbox
        params = {
            'f': 'geojson',
            'where': '1=1',
            'geometryType': 'esriGeometryEnvelope',
            'geometry': f'{xmin},{ymin},{xmax},{ymax}',
            'input_crs': '3857',  # Web Mercator for geometry
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'true',
            'output_crs': target_crs,
            'resultRecordCount': self.record_count,
            'resultOffset': offset
        }
        return f"{self.base_url}/query?{urlencode(params)}"

    def download_for_area(self, geometry_input: Union[str, Path, gpd.GeoDataFrame], target_crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
        """
        Download CORINE Land Cover data for the specified geographical area.
        
        Handles large areas through automatic pagination and provides comprehensive
        error handling for network and data processing issues.
        
        Args:
            geometry_input: Study area as file path or GeoDataFrame
            target_crs: Output coordinate reference system
            
        Returns:
            GeoDataFrame containing CORINE land cover polygons with attributes
            
        Raises:
            ValueError: If no data is available for the specified area
            requests.RequestException: If API requests fail
        """
        bbox = self.get_bbox_from_geometry(geometry_input)
        all_features = []
        offset = 0
        
        if self.logger:
            self.logger.info(f"Downloading CORINE {self.selected_year} data for study area")
        
        # Handle paginated API responses
        while True:
            url = self.build_query_url(bbox, offset, target_crs)
            
            try:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                
                if 'features' not in data:
                    if self.logger:
                        self.logger.error(f"Unexpected API response format: {data}")
                    break
                    
                features = data['features']
                all_features.extend(features)
                
                # Check if more data is available
                if len(features) < self.record_count:
                    break
                
                if data.get('exceededTransferLimit', False):
                    offset += self.record_count
                    if self.logger:
                        self.logger.debug(f"Fetching additional data at offset {offset}")
                else:
                    break
                    
            except Exception as e:
                if self.logger:
                    self.logger.error(f"API request failed: {e}")
                raise
        
        if not all_features:
            raise ValueError("No CORINE data available for the specified area")
        
        # Process downloaded features
        gdf = gpd.GeoDataFrame.from_features(all_features, crs="EPSG:4326")
        
        # Standardize land cover code column
        code_column = self._find_code_column(gdf)
        gdf['corine_code'] = pd.to_numeric(gdf[code_column], errors='coerce')
        
        if self.logger:
            self.logger.info(f"Successfully downloaded {len(gdf)} CORINE features")
        
        return gdf

    def _find_code_column(self, gdf: gpd.GeoDataFrame) -> str:
        """Identify the CORINE land cover code column in downloaded data."""
        # Check for standard CORINE code columns (prioritize recent years)
        standard_columns = ['CODE_18', 'CODE_12', 'CODE_06', 'CODE_00', 'CODE_90', 'gridcode', 'GRIDCODE']
        
        for col in standard_columns:
            if col in gdf.columns:
                return col
        
        # Fallback: find any column containing "code"
        code_columns = [col for col in gdf.columns if 'code' in col.lower()]
        if code_columns:
            return code_columns[0]
        
        raise ValueError(f"No CORINE code column found. Available columns: {list(gdf.columns)}")

    @property
    def year(self) -> int:
        """Get the selected CORINE dataset year."""
        return self.selected_year

    @staticmethod
    def get_available_years() -> List[int]:
        """Get all available CORINE dataset years."""
        return sorted(CORINE_YEARS)


if __name__ == "__main__":
    import shapely.geometry
    
    # Example usage for testing
    logging.basicConfig(level=logging.INFO)
    
    downloader = CorineDataDownloader(year_or_period=2018, verbose=True)
    
    # Test with Berlin city center area
    test_geometry = gpd.GeoDataFrame(
        [1], 
        geometry=[shapely.geometry.box(13.3, 52.4, 13.5, 52.6)], 
        crs="EPSG:4326"
    )
    
    try:
        result_gdf = downloader.download_for_area(test_geometry)
        print(f"Downloaded {len(result_gdf)} features")
        print(f"Columns: {list(result_gdf.columns)}")
    except Exception as e:
        print(f"Download failed: {e}")