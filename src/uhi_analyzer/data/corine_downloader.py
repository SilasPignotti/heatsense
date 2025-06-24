"""
CorineDataDownloader: Optimized downloader for Corine Land Cover data
specifically for Urban Heat Island analyses.
"""

from pathlib import Path
from typing import List, Tuple, Union, Optional
from urllib.parse import urlencode
import logging
import requests
from pyproj import Transformer
import geopandas as gpd
import pandas as pd
from datetime import datetime

from uhi_analyzer.config import (
    CORINE_BASE_URLS,
    CORINE_LANDUSE_MAPPING,
    CORINE_IMPERVIOUS_COEFFICIENTS,
    DEFAULT_RECORD_COUNT,
    DEFAULT_TIMEOUT,
    DEFAULT_OUTPUT_FORMAT,
    CRS_CONFIG,
    get_best_corine_year_for_date_range
)


class CorineDataDownloader:
    """
    Optimized downloader for Corine Land Cover data for Urban Heat Island analyses.
    
    This downloader automatically selects the best available Corine year for a
    given period and provides UHI-optimized data with:
    - landuse_type: Categorical classification of land use
    - impervious_area: Numeric coefficient for impervious surfaces (0.0-1.0)
    """
    
    def __init__(
        self, 
        start_date: Union[str, datetime, int], 
        end_date: Union[str, datetime, int],
        logger: Optional[logging.Logger] = None
    ):
        """
        Initializes the CorineDataDownloader for an analysis period.
        
        Args:
            start_date: Start date of the analysis period (YYYY, YYYY-MM-DD, or datetime)
            end_date: End date of the analysis period (YYYY, YYYY-MM-DD, or datetime)
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Convert inputs to years
        self.start_year = self._extract_year(start_date)
        self.end_year = self._extract_year(end_date)
        
        # Determine the best available year for the period
        self.selected_year = get_best_corine_year_for_date_range(self.start_year, self.end_year)
        self.base_url = CORINE_BASE_URLS[self.selected_year]
        
        self.logger.info(
            f"Analysis period: {self.start_year}-{self.end_year}, "
            f"selected Corine year: {self.selected_year}"
        )

    def _extract_year(self, date_input: Union[str, datetime, int]) -> int:
        """
        Extracts the year from various date inputs.
        
        Args:
            date_input: Date as string, datetime, or integer
            
        Returns:
            Year as integer
        """
        if isinstance(date_input, int):
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.year
        elif isinstance(date_input, str):
            # Try different formats
            try:
                # YYYY format
                if len(date_input) == 4 and date_input.isdigit():
                    return int(date_input)
                # YYYY-MM-DD format
                elif '-' in date_input:
                    return int(date_input.split('-')[0])
                else:
                    raise ValueError(f"Unknown date format: {date_input}")
            except Exception as e:
                raise ValueError(f"Error parsing date '{date_input}': {e}")
        else:
            raise ValueError(f"Unsupported date type: {type(date_input)}")

    def get_bbox_from_geojson(self, geojson_path: Union[str, Path]) -> Tuple[float, float, float, float]:
        """
        Extracts the bounding box from a GeoJSON file and transforms it to Web Mercator.
        
        Args:
            geojson_path: Path to the GeoJSON file
            
        Returns:
            Bounding box as (xmin, ymin, xmax, ymax) in Web Mercator (EPSG:3857)
        """
        try:
            gdf = gpd.read_file(geojson_path)
            bbox_wgs84 = gdf.total_bounds  # (xmin, ymin, xmax, ymax)
            
            # Transform from WGS84 to Web Mercator
            transformer = Transformer.from_crs(CRS_CONFIG["GEOGRAPHIC"], CRS_CONFIG["WEB_MERCATOR"], always_xy=True)
            
            xmin, ymin = transformer.transform(bbox_wgs84[0], bbox_wgs84[1])
            xmax, ymax = transformer.transform(bbox_wgs84[2], bbox_wgs84[3])
            
            return (xmin, ymin, xmax, ymax)
            
        except Exception as e:
            self.logger.error(f"Error reading GeoJSON file: {e}")
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
            'resultRecordCount': DEFAULT_RECORD_COUNT,
            'resultOffset': offset
        }
        query_string = urlencode(params)
        return f"{self.base_url}/query?{query_string}"

    def download_for_area(self, geojson_path: Union[str, Path]) -> List[dict]:
        """
        Downloads Corine Land Cover data for a specific area.
        
        Args:
            geojson_path: Path to the GeoJSON file of the area
            
        Returns:
            List of all features from the API
        """
        bbox = self.get_bbox_from_geojson(geojson_path)
        all_features = []
        offset = 0
        
        while True:
            url = self.build_query_url(bbox, offset)
            
            try:
                response = requests.get(url, timeout=DEFAULT_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                
                if 'features' not in data:
                    self.logger.error(f"Unexpected response format: {data}")
                    break
                    
                features = data['features']
                all_features.extend(features)
                
                # Check if we have all data
                if len(features) < DEFAULT_RECORD_COUNT:
                    break
                
                # Check for exceededTransferLimit flag
                if data.get('exceededTransferLimit', False):
                    offset += DEFAULT_RECORD_COUNT
                else:
                    break
                    
            except Exception as e:
                self.logger.error(f"Error during download: {e}")
                break
        
        self.logger.info(f"Download completed: {len(all_features)} features")
        return all_features

    def process_features_for_uhi_analysis(self, features: List[dict]) -> gpd.GeoDataFrame:
        """
        Processes downloaded features for UHI analyses.
        
        Args:
            features: List of downloaded features
            
        Returns:
            GeoDataFrame with UHI-specific columns
        """
        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(features, crs=CRS_CONFIG["GEOGRAPHIC"])
        
        # Identify the Corine code column
        code_column = None
        possible_code_columns = ['CODE_18', 'CODE_12', 'CODE_06', 'CODE_00', 'CODE_90', 'gridcode', 'GRIDCODE']
        
        for col in possible_code_columns:
            if col in gdf.columns:
                code_column = col
                break
        
        if code_column is None:
            # Fallback: search for any column with "code" in the name
            code_columns = [col for col in gdf.columns if 'code' in col.lower()]
            if code_columns:
                code_column = code_columns[0]
            else:
                raise ValueError(f"No Corine code column found. Available columns: {list(gdf.columns)}")
        
        # Convert codes to integers if necessary
        gdf[code_column] = pd.to_numeric(gdf[code_column], errors='coerce')
        
        # Add landuse_type column
        gdf['landuse_type'] = gdf[code_column].map(CORINE_LANDUSE_MAPPING)
        
        # Handle unknown codes
        gdf['landuse_type'] = gdf['landuse_type'].fillna('unknown')
        
        # Add impervious_area column
        gdf['impervious_area'] = gdf['landuse_type'].map(CORINE_IMPERVIOUS_COEFFICIENTS)
        gdf['impervious_area'] = gdf['impervious_area'].fillna(0.0)
        
        # Keep only relevant columns for UHI analysis
        essential_columns = ['geometry', 'landuse_type', 'impervious_area', code_column]
        
        # Add other useful columns if available
        optional_columns = ['Shape_Area', 'Shape_Length', 'area_ha']
        for col in optional_columns:
            if col in gdf.columns:
                essential_columns.append(col)
        
        return gdf[essential_columns]

    def download_and_save(
        self, 
        geojson_path: Union[str, Path], 
        output_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Downloads Corine Land Cover data for a specific area and saves it
        optimized for UHI analyses.
        
        Args:
            geojson_path: Path to the GeoJSON file of the area
            output_path: Path for the output file (optional)
            
        Returns:
            Path to the saved file
        """
        if output_path is None:
            # Generate default output path
            input_path = Path(geojson_path)
            output_path = (
                Path("data/processed/landcover") / 
                f"{input_path.stem}_corine_landuse_{self.year}.geojson"
            )
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Download the data
        features = self.download_for_area(geojson_path)

        # Process for UHI analysis
        gdf = self.process_features_for_uhi_analysis(features)
        
        # Clip to polygon
        clip_poly = gpd.read_file(geojson_path)
        if clip_poly.crs != gdf.crs:
            clip_poly = clip_poly.to_crs(gdf.crs)
        
        gdf_clipped = gpd.overlay(gdf, clip_poly, how="intersection")

        # Save
        gdf_clipped.to_file(output_path, driver="GeoJSON")
        
        self.logger.info(f"Corine data saved: {output_path}")
        
        return output_path 