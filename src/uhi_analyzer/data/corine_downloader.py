"""
CorineDataDownloader: Optimized downloader for Corine Land Cover data.
"""

from pathlib import Path
from typing import List, Tuple, Union, Optional, Literal
from urllib.parse import urlencode
import logging
import requests
from pyproj import Transformer
import geopandas as gpd
import pandas as pd
from datetime import datetime

from uhi_analyzer.config import (
    CORINE_BASE_URLS,
    CORINE_YEARS,
    CORINE_LANDUSE_MAPPING,
    CORINE_IMPERVIOUS_COEFFICIENTS,
    DEFAULT_RECORD_COUNT,
    DEFAULT_TIMEOUT,
    DEFAULT_OUTPUT_FORMAT,
    CRS_CONFIG
)

# Output format configuration - moved to class level for flexibility
OUTPUT_FORMATS = {
    'geojson': {'driver': 'GeoJSON', 'extension': '.geojson'},
    'gpkg': {'driver': 'GPKG', 'extension': '.gpkg'},
    'shp': {'driver': 'ESRI Shapefile', 'extension': '.shp'},
    'parquet': {'driver': 'Parquet', 'extension': '.parquet'}
}

OutputFormat = Literal['geojson', 'gpkg', 'shp', 'parquet']


class CorineDataDownloader:
    """
    Optimized downloader for Corine Land Cover data for Urban Heat Island analyses.
    
    This downloader automatically selects the best available Corine year for a
    given period and provides UHI-optimized data with:
    - landuse_type: Categorical classification of land use
    - impervious_area: Numeric coefficient for impervious surfaces (0.0-1.0)
    
    Features:
    - Flexible date input: single year, date range, or specific date
    - Multiple output formats: GeoJSON, GPKG, Shapefile, Parquet
    - Automatic year selection based on data availability
    - UHI-specific data processing and optimization
    """
    
    def __init__(
        self, 
        year_or_period: Union[int, str, datetime, Tuple[Union[int, str, datetime], Union[int, str, datetime]]], 
        logger: Optional[logging.Logger] = None,
        record_count: int = DEFAULT_RECORD_COUNT,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """
        Initializes the CorineDataDownloader for a specific year or analysis period.
        
        Args:
            year_or_period: One of:
                - Single year as int (e.g., 2018)
                - Single year as string (e.g., "2018")
                - Single date as string (e.g., "2018-06-15") 
                - Date range as tuple ((start, end))
            logger: Logger instance (optional)
            record_count: Number of records per API request (optional)
            timeout: Request timeout in seconds (optional)
        """
        self.logger = logger or logging.getLogger(__name__)
        self.record_count = record_count
        self.timeout = timeout
        
        # Parse year/period input
        self.start_year, self.end_year = self._parse_year_or_period(year_or_period)
        
        # Determine the best available year for the period
        self.selected_year = self._get_best_year_for_range(self.start_year, self.end_year)
        self.base_url = CORINE_BASE_URLS[self.selected_year]
        
        if self.start_year == self.end_year:
            self.logger.info(f"Analysis year: {self.start_year}, selected Corine year: {self.selected_year}")
        else:
            self.logger.info(
                f"Analysis period: {self.start_year}-{self.end_year}, "
                f"selected Corine year: {self.selected_year}"
            )

    def _get_best_year_for_range(self, start_year: int, end_year: int) -> int:
        """
        Finds the best available Corine year for a date range.
        Prefers the newest available year within the range.
        If no year is available within the range, takes the closest year.
        
        Args:
            start_year: Start year of the analysis period
            end_year: End year of the analysis period
            
        Returns:
            Best available Corine year for the period
            
        Raises:
            ValueError: If no available years are configured or start_year > end_year
        """
        if not CORINE_YEARS:
            raise ValueError("No available Corine years configured")
        
        if start_year > end_year:
            raise ValueError(f"Start year ({start_year}) must be before end year ({end_year})")
        
        # Find years within the range
        years_in_range = [year for year in CORINE_YEARS if start_year <= year <= end_year]
        
        if years_in_range:
            # Take the newest year within the range
            return max(years_in_range)
        else:
            # If no year within the range, take the closest to the range midpoint
            midpoint = (start_year + end_year) / 2
            return min(CORINE_YEARS, key=lambda x: abs(x - midpoint))

    def _parse_year_or_period(
        self, 
        year_or_period: Union[int, str, datetime, Tuple[Union[int, str, datetime], Union[int, str, datetime]]]
    ) -> Tuple[int, int]:
        """
        Parses various year/period inputs into start and end years.
        
        Args:
            year_or_period: Year or period specification
            
        Returns:
            Tuple of (start_year, end_year)
        """
        if isinstance(year_or_period, tuple):
            # Date range provided
            start_year = self._extract_year(year_or_period[0])
            end_year = self._extract_year(year_or_period[1])
            return start_year, end_year
        else:
            # Single year/date provided
            year = self._extract_year(year_or_period)
            return year, year

    def _extract_year(self, date_input: Union[str, datetime, int]) -> int:
        """
        Extracts the year from various date inputs.
        
        Args:
            date_input: Date as string, datetime, or integer
            
        Returns:
            Year as integer
        """
        if isinstance(date_input, int):
            if date_input < 1900 or date_input > 2100:
                raise ValueError(f"Year {date_input} is outside reasonable range (1900-2100)")
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.year
        elif isinstance(date_input, str):
            # Try different formats
            try:
                # YYYY format
                if len(date_input) == 4 and date_input.isdigit():
                    year = int(date_input)
                    if year < 1900 or year > 2100:
                        raise ValueError(f"Year {year} is outside reasonable range (1900-2100)")
                    return year
                # YYYY-MM-DD or YYYY-MM format
                elif '-' in date_input:
                    # Try YYYY-MM-DD
                    try:
                        dt = datetime.strptime(date_input, "%Y-%m-%d")
                        return dt.year
                    except ValueError:
                        pass
                    # Try YYYY-MM
                    try:
                        dt = datetime.strptime(date_input, "%Y-%m")
                        return dt.year
                    except ValueError:
                        pass
                    # If both fail, it's an invalid date format
                    raise ValueError(f"Invalid date format: {date_input}")
                else:
                    raise ValueError(f"Unknown date format: {date_input}")
            except Exception as e:
                raise ValueError(f"Error parsing date '{date_input}': {e}")
        else:
            raise ValueError(f"Unsupported date type: {type(date_input)}")

    def get_bbox_from_geometry(self, geometry_input: Union[str, Path, gpd.GeoDataFrame]) -> Tuple[float, float, float, float]:
        """
        Extracts the bounding box from various geometry inputs and transforms it to Web Mercator.
        
        Args:
            geometry_input: One of:
                - Path to GeoJSON/Shapefile
                - GeoDataFrame
                
        Returns:
            Bounding box as (xmin, ymin, xmax, ymax) in Web Mercator (EPSG:3857)
        """
        try:
            if isinstance(geometry_input, (str, Path)):
                gdf = gpd.read_file(geometry_input)
            elif isinstance(geometry_input, gpd.GeoDataFrame):
                gdf = geometry_input.copy()
            else:
                raise ValueError(f"Unsupported geometry input type: {type(geometry_input)}")
            
            # Ensure CRS is set
            if gdf.crs is None:
                self.logger.warning("No CRS found, assuming WGS84")
                gdf.set_crs(CRS_CONFIG["GEOGRAPHIC"], inplace=True)
            
            # Get bounds in original CRS
            bbox_original = gdf.total_bounds  # (xmin, ymin, xmax, ymax)
            
            # Transform to Web Mercator if needed
            if gdf.crs != CRS_CONFIG["WEB_MERCATOR"]:
                transformer = Transformer.from_crs(gdf.crs, CRS_CONFIG["WEB_MERCATOR"], always_xy=True)
                xmin, ymin = transformer.transform(bbox_original[0], bbox_original[1])
                xmax, ymax = transformer.transform(bbox_original[2], bbox_original[3])
                return (xmin, ymin, xmax, ymax)
            else:
                return tuple(bbox_original)
            
        except Exception as e:
            self.logger.error(f"Error processing geometry input: {e}")
            raise

    def build_query_url(self, bbox: Tuple[float, float, float, float], offset: int = 0) -> str:
        """
        Builds the query URL for the ArcGIS REST API.
        
        Args:
            bbox: Bounding box as (xmin, ymin, xmax, ymax) in Web Mercator (EPSG:3857)
            offset: Offset for pagination
            
        Returns:
            Complete query URL
        """
        xmin, ymin, xmax, ymax = bbox
        params = {
            'f': DEFAULT_OUTPUT_FORMAT,
            'where': '1=1',
            'geometryType': 'esriGeometryEnvelope',
            'geometry': f'{xmin},{ymin},{xmax},{ymax}',
            'inSR': CRS_CONFIG["WEB_MERCATOR"].split(":")[1],  # "3857"
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'true',
            'outSR': CRS_CONFIG["GEOGRAPHIC"].split(":")[1],  # "4326"
            'resultRecordCount': self.record_count,
            'resultOffset': offset
        }
        query_string = urlencode(params)
        return f"{self.base_url}/query?{query_string}"

    def download_for_area(self, geometry_input: Union[str, Path, gpd.GeoDataFrame]) -> List[dict]:
        """
        Downloads Corine Land Cover data for a specific area.
        
        Args:
            geometry_input: Geometry specification (file path or GeoDataFrame)
            
        Returns:
            List of all features from the API
        """
        bbox = self.get_bbox_from_geometry(geometry_input)
        all_features = []
        offset = 0
        
        while True:
            url = self.build_query_url(bbox, offset)
            
            try:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                
                if 'features' not in data:
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
                    self.logger.debug(f"Continuing download at offset {offset}")
                else:
                    break
                    
            except Exception as e:
                self.logger.error(f"Error during download: {e}")
                break
        
        self.logger.info(f"Download completed: {len(all_features)} features")
        return all_features

    def process_to_geodataframe(self, features: List[dict]) -> gpd.GeoDataFrame:
        """
        Converts downloaded features to a GeoDataFrame with basic processing.
        
        Args:
            features: List of downloaded features
            
        Returns:
            GeoDataFrame with standardized columns
        """
        if not features:
            raise ValueError("No features to process")
            
        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(features, crs=CRS_CONFIG["GEOGRAPHIC"])
        
        # Identify the Corine code column
        code_column = self._find_code_column(gdf)
        
        # Convert codes to integers if necessary
        gdf[code_column] = pd.to_numeric(gdf[code_column], errors='coerce')
        
        # Rename code column to standardized name
        if code_column != 'corine_code':
            gdf['corine_code'] = gdf[code_column]
        
        return gdf

    def process_for_uhi_analysis(self, features: List[dict]) -> gpd.GeoDataFrame:
        """
        Processes downloaded features specifically for Urban Heat Island analyses.
        
        This method adds UHI-specific columns:
        - landuse_type: Categorical classification of land use
        - impervious_area: Numeric coefficient for impervious surfaces (0.0-1.0)
        
        Args:
            features: List of downloaded features
            
        Returns:
            GeoDataFrame with UHI-specific columns
        """
        # Start with basic processing
        gdf = self.process_to_geodataframe(features)
        
        # Add landuse_type column
        gdf['landuse_type'] = gdf['corine_code'].map(CORINE_LANDUSE_MAPPING)
        
        # Handle unknown codes
        unknown_codes = gdf[gdf['landuse_type'].isna()]['corine_code'].unique()
        if len(unknown_codes) > 0:
            self.logger.warning(f"Unknown Corine codes found: {unknown_codes}")
        gdf['landuse_type'] = gdf['landuse_type'].fillna('unknown')
        
        # Add impervious_area column
        gdf['impervious_area'] = gdf['landuse_type'].map(CORINE_IMPERVIOUS_COEFFICIENTS)
        gdf['impervious_area'] = gdf['impervious_area'].fillna(0.0)
        
        # Keep only relevant columns for UHI analysis
        essential_columns = ['geometry', 'landuse_type', 'impervious_area', 'corine_code']
        
        # Add other useful columns if available
        optional_columns = ['Shape_Area', 'Shape_Length', 'area_ha']
        for col in optional_columns:
            if col in gdf.columns:
                essential_columns.append(col)
        
        return gdf[essential_columns]

    def _find_code_column(self, gdf: gpd.GeoDataFrame) -> str:
        """
        Finds the Corine code column in the GeoDataFrame.
        
        Args:
            gdf: GeoDataFrame to search
            
        Returns:
            Name of the code column
            
        Raises:
            ValueError: If no code column is found
        """
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

    def download_and_save(
        self, 
        geometry_input: Union[str, Path, gpd.GeoDataFrame], 
        output_path: Optional[Union[str, Path]] = None,
        output_format: OutputFormat = 'geojson',
        clip_to_boundary: bool = True,
        process_for_uhi: bool = False
    ) -> Path:
        """
        Downloads Corine Land Cover data for a specific area and saves it
        optimized for UHI analyses.
        
        Args:
            geometry_input: Geometry specification (file path or GeoDataFrame)
            output_path: Path for the output file (optional, auto-generated if None)
            output_format: Output format ('geojson', 'gpkg', 'shp', 'parquet')
            clip_to_boundary: Whether to clip data to the exact boundary geometry
            process_for_uhi: Whether to add UHI-specific processing (landuse_type, impervious_area)
            
        Returns:
            Path to the saved file
        """
        if output_format not in OUTPUT_FORMATS:
            raise ValueError(f"Unsupported output format: {output_format}. Supported: {list(OUTPUT_FORMATS.keys())}")
        
        format_config = OUTPUT_FORMATS[output_format]
        
        if output_path is None:
            # Generate default output path
            if isinstance(geometry_input, (str, Path)):
                input_path = Path(geometry_input)
                base_name = input_path.stem
            else:
                base_name = "corine_data"
            
            suffix = "_uhi" if process_for_uhi else ""
            output_path = (
                Path("data/processed/landcover") / 
                f"{base_name}_corine_{self.selected_year}{suffix}{format_config['extension']}"
            )
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Download the data
        features = self.download_for_area(geometry_input)

        # Process the data
        if process_for_uhi:
            gdf = self.process_for_uhi_analysis(features)
        else:
            gdf = self.process_to_geodataframe(features)
        
        # Clip to polygon if requested
        if clip_to_boundary:
            if isinstance(geometry_input, (str, Path)):
                clip_poly = gpd.read_file(geometry_input)
            else:
                clip_poly = geometry_input.copy()
                
            if clip_poly.crs != gdf.crs:
                clip_poly = clip_poly.to_crs(gdf.crs)
            
            gdf = gpd.overlay(gdf, clip_poly, how="intersection")

        # Save with appropriate driver
        gdf.to_file(output_path, driver=format_config['driver'])
        
        process_type = "UHI-processed" if process_for_uhi else "basic"
        self.logger.info(f"Corine data saved ({process_type}): {output_path} ({len(gdf)} features)")
        
        return output_path

    @property
    def year(self) -> int:
        """
        Backwards compatibility property for the selected year.
        
        Returns:
            Selected Corine year
        """
        return self.selected_year

    @staticmethod
    def get_available_years() -> List[int]:
        """
        Returns a list of all available Corine years.
        
        Returns:
            Sorted list of available years
        """
        return sorted(CORINE_YEARS)

    @staticmethod
    def is_year_available(year: int) -> bool:
        """
        Checks if a specific Corine year is available.
        
        Args:
            year: Year to check
            
        Returns:
            True if the year is available, False otherwise
        """
        return year in CORINE_YEARS 