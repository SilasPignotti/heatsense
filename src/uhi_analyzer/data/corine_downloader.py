"""
Corine Data Downloader for Urban Heat Island Analysis.

Simple downloader for Corine Land Cover data with minimal configuration.
"""

from pathlib import Path
from typing import Tuple, Union, Optional, List
from urllib.parse import urlencode
import logging
import requests
from pyproj import Transformer
import geopandas as gpd
import pandas as pd
from datetime import datetime

from ..config.settings import CORINE_BASE_URLS, CORINE_YEARS


class CorineDataDownloader:
    """
    Simple downloader for Corine Land Cover data.
    
    Args:
        year_or_period: Single year, date range, or specific date
        record_count: Number of records per API request
        timeout: Request timeout in seconds
        verbose: Enable console logging
        log_file: Optional log file path
    """

    
    def __init__(
        self, 
        year_or_period: Union[int, str, datetime, Tuple[Union[int, str, datetime], Union[int, str, datetime]]], 
        record_count: int = 1000,
        timeout: int = 30,
        verbose: bool = True,
        log_file: Optional[str] = None,
        corine_years: List[int] = CORINE_YEARS,
        corine_base_urls: dict [int, str] = CORINE_BASE_URLS
    ):
        self.record_count = record_count
        self.timeout = timeout
        self.corine_years = corine_years
        self.corine_base_urls = corine_base_urls
        self.logger = self._setup_logger(log_file) if verbose or log_file else None
        
        # Parse year/period input
        self.start_year, self.end_year = self._parse_year_or_period(year_or_period)
        
        # Determine the best available year for the period
        self.selected_year = self._get_best_year_for_range(self.start_year, self.end_year)
        self.base_url = self.corine_base_urls[self.selected_year]
        
        if self.logger:
            if self.start_year == self.end_year:
                self.logger.info(f"Using Corine {self.selected_year} for analysis year {self.start_year}")
            else:
                self.logger.info(f"Using Corine {self.selected_year} for period {self.start_year}-{self.end_year}")

    def _setup_logger(self, log_file: Optional[str] = None) -> logging.Logger:
        """Set up simple logger."""
        logger = logging.getLogger(f"{__name__}.CorineDataDownloader")
        
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

    def _get_best_year_for_range(self, start_year: int, end_year: int) -> int:
        """Find the best available Corine year for a date range."""
        if start_year > end_year:
            raise ValueError(f"Start year ({start_year}) must be before end year ({end_year})")
        
        # Find years within the range
        years_in_range = [year for year in self.corine_years if start_year <= year <= end_year]
        
        if years_in_range:
            # Take the newest year within the range
            return max(years_in_range)
        else:
            # If no year within the range, take the closest to the range midpoint
            midpoint = (start_year + end_year) / 2
            return min(self.corine_years, key=lambda x: abs(x - midpoint))

    def _parse_year_or_period(
        self, 
        year_or_period: Union[int, str, datetime, Tuple[Union[int, str, datetime], Union[int, str, datetime]]]
    ) -> Tuple[int, int]:
        """Parse various year/period inputs into start and end years."""
        if isinstance(year_or_period, tuple):
            start_year = self._extract_year(year_or_period[0])
            end_year = self._extract_year(year_or_period[1])
            return start_year, end_year
        else:
            year = self._extract_year(year_or_period)
            return year, year

    def _extract_year(self, date_input: Union[str, datetime, int]) -> int:
        """Extract the year from various date inputs."""
        if isinstance(date_input, int):
            if date_input < 1900 or date_input > 2100:
                raise ValueError(f"Year {date_input} is outside reasonable range (1900-2100)")
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.year
        elif isinstance(date_input, str):
            # Try different formats
            if len(date_input) == 4 and date_input.isdigit():
                year = int(date_input)
                if year < 1900 or year > 2100:
                    raise ValueError(f"Year {year} is outside reasonable range (1900-2100)")
                return year
            elif '-' in date_input:
                # Try YYYY-MM-DD or YYYY-MM
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
            raise ValueError(f"Unsupported date type: {type(date_input)}")

    def get_bbox_from_geometry(self, geometry_input: Union[str, Path, gpd.GeoDataFrame]) -> Tuple[float, float, float, float]:
        """Extract bounding box from geometry and transform to Web Mercator."""
        if isinstance(geometry_input, (str, Path)):
            gdf = gpd.read_file(geometry_input)
        elif isinstance(geometry_input, gpd.GeoDataFrame):
            gdf = geometry_input.copy()
        else:
            raise ValueError(f"Unsupported geometry input type: {type(geometry_input)}")
        
        # Ensure CRS is set
        if gdf.crs is None:
            if self.logger:
                self.logger.warning("No CRS found, assuming WGS84")
            gdf.set_crs("EPSG:4326", inplace=True)
        
        # Get bounds in original CRS
        bbox_original = gdf.total_bounds  # (xmin, ymin, xmax, ymax)
        
        # Transform to Web Mercator if needed
        if gdf.crs != "EPSG:3857":
            transformer = Transformer.from_crs(gdf.crs, "EPSG:3857", always_xy=True)
            xmin, ymin = transformer.transform(bbox_original[0], bbox_original[1])
            xmax, ymax = transformer.transform(bbox_original[2], bbox_original[3])
            return (xmin, ymin, xmax, ymax)
        else:
            return tuple(bbox_original)

    def build_query_url(self, bbox: Tuple[float, float, float, float], offset: int = 0, target_crs: str = "EPSG:4326") -> str:
        """Build query URL for the ArcGIS REST API."""
        xmin, ymin, xmax, ymax = bbox
        params = {
            'f': 'geojson',
            'where': '1=1',
            'geometryType': 'esriGeometryEnvelope',
            'geometry': f'{xmin},{ymin},{xmax},{ymax}',
            'input_crs': '3857',  # Web Mercator
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'true',
            'output_crs': target_crs,  # WGS84
            'resultRecordCount': self.record_count,
            'resultOffset': offset
        }
        return f"{self.base_url}/query?{urlencode(params)}"

    def download_for_area(self, geometry_input: Union[str, Path, gpd.GeoDataFrame], target_crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
        """
        Download Corine Land Cover data for a specific area.
        
        Args:
            geometry_input: Geometry specification (file path or GeoDataFrame)
            
        Returns:
            GeoDataFrame with Corine land cover data
        """
        bbox = self.get_bbox_from_geometry(geometry_input)
        all_features = []
        offset = 0
        
        if self.logger:
            self.logger.info(f"Downloading Corine {self.selected_year} data for area")
        
        while True:
            url = self.build_query_url(bbox, offset, target_crs)
            
            try:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                
                if 'features' not in data:
                    if self.logger:
                        self.logger.error(f"Unexpected response format: {data}")
                    break
                    
                features = data['features']
                all_features.extend(features)
                
                # Check if we have all data
                if len(features) < self.record_count:
                    break
                
                # Check for exceededTransferLimit flag
                if data.get('exceededTransferLimit', False):
                    offset += self.record_count
                    if self.logger:
                        self.logger.debug(f"Continuing download at offset {offset}")
                else:
                    break
                    
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error during download: {e}")
                raise
        
        if not all_features:
            raise ValueError("No features downloaded")
        
        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(all_features, crs="EPSG:4326")
        
        # Find and standardize the code column
        code_column = self._find_code_column(gdf)
        gdf['corine_code'] = pd.to_numeric(gdf[code_column], errors='coerce')
        
        if self.logger:
            self.logger.info(f"Downloaded {len(gdf)} features")
        
        return gdf

    def _find_code_column(self, gdf: gpd.GeoDataFrame) -> str:
        """Find the Corine code column in the GeoDataFrame."""
        # Prioritize by year (newer first)
        possible_code_columns = ['CODE_18', 'CODE_12', 'CODE_06', 'CODE_00', 'CODE_90', 'gridcode', 'GRIDCODE']
        
        for col in possible_code_columns:
            if col in gdf.columns:
                return col
        
        # Fallback: search for any column with "code" in the name
        code_columns = [col for col in gdf.columns if 'code' in col.lower()]
        if code_columns:
            return code_columns[0]
        
        raise ValueError(f"No Corine code column found. Available columns: {list(gdf.columns)}")

    @property
    def year(self) -> int:
        """Selected Corine year."""
        return self.selected_year

    @staticmethod
    def get_available_years() -> List[int]:
        """Get all available Corine years."""
        return sorted(CorineDataDownloader.corine_years)


if __name__ == "__main__":
    # Simple usage example
    downloader = CorineDataDownloader(year_or_period=2018)
    
    # Create a simple test geometry (Berlin center)
    import shapely.geometry
    test_geom = gpd.GeoDataFrame(
        [1], 
        geometry=[shapely.geometry.box(13.3, 52.4, 13.5, 52.6)], 
        crs="EPSG:4326"
    )
    
    try:
        gdf = downloader.download_for_area(test_geom)
        print(f"✓ Downloaded {len(gdf)} features")
        print(f"Columns: {list(gdf.columns)}")
    except Exception as e:
        print(f"✗ Failed: {e}") 