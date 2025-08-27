"""
German Weather Service (DWD) data downloader for Urban Heat Island analysis.

This module provides functionality to download weather station data from the
German Weather Service using the wetterdienst library. Supports spatial buffering,
temperature interpolation, and flexible geometry input formats.

Dependencies:
    - wetterdienst: German Weather Service API client
    - geopandas: Geospatial data handling
    - scipy: Spatial interpolation algorithms
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.interpolate import griddata
from shapely.geometry import MultiPolygon, Point, Polygon, shape
from wetterdienst import Settings
from wetterdienst.provider.dwd.observation import DwdObservationRequest

from ..config.settings import CRS_CONFIG, DWD_SETTINGS, DWD_TEMPERATURE_PARAMETERS


class DWDDataDownloader:
    """
    Download and process German Weather Service meteorological data.
    
    Provides weather station data retrieval with spatial buffering and optional
    temperature interpolation for Urban Heat Island analysis. Handles multiple
    geometry input formats and coordinate reference systems.
    
    Args:
        buffer_distance: Search radius around study area in meters (default: 10000)
        interpolation_method: Spatial interpolation algorithm (linear/nearest/cubic)
        interpolate_by_default: Enable automatic temperature interpolation
        interpolation_resolution: Grid cell size for interpolation in meters
        log_file: Optional path for detailed logging
        verbose: Enable console progress logging
    """
    
    def __init__(
        self, 
        buffer_distance: float = 10000,
        interpolation_method: str = "linear",
        interpolate_by_default: bool = True,
        interpolation_resolution: float = 30,
        log_file: Optional[str] = None,
        verbose: bool = True
    ):
        self.buffer_distance = buffer_distance
        self.interpolation_method = interpolation_method
        self.interpolate_by_default = interpolate_by_default
        self.interpolation_resolution = interpolation_resolution
        
        # Configure logging
        self.logger = self._setup_logger(log_file) if verbose or log_file else None
        
        # Initialize DWD API settings
        self.settings = Settings(**DWD_SETTINGS)
        
        if self.logger:
            self.logger.info(f"DWD Downloader initialized: buffer={self.buffer_distance}m, "
                           f"interpolation={self.interpolation_method}")

    def _setup_logger(self, log_file: Optional[str] = None) -> logging.Logger:
        """Configure logging with console and optional file output."""
        logger = logging.getLogger(f"{__name__}.DWDDataDownloader")
        
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
    
    def _create_geometry_from_geojson(self, geojson: Union[str, Dict[str, Any]]) -> Union[Point, Polygon, MultiPolygon]:
        """Convert GeoJSON to Shapely geometry object."""
        if isinstance(geojson, str):
            geojson = json.loads(geojson)
        return shape(geojson)
    
    def _get_bounding_box_from_geometry(self, geometry: Union[Point, Polygon, MultiPolygon]) -> Dict[str, float]:
        """Extract geographic bounding box coordinates from geometry."""
        # Ensure geometry is in WGS84 for lat/lon coordinates
        if isinstance(geometry, (gpd.GeoDataFrame, gpd.GeoSeries)):
            geometry = geometry.to_crs(CRS_CONFIG["GEOGRAPHIC"])
        
        bounds = geometry.bounds  # (minx, miny, maxx, maxy)
        
        return {
            'min_lat': bounds[1],
            'max_lat': bounds[3], 
            'min_lon': bounds[0],
            'max_lon': bounds[2]
        }
    
    def _create_interpolation_grid(
        self, 
        geometry: Union[Point, Polygon, MultiPolygon], 
        resolution: float = None
    ) -> gpd.GeoDataFrame:
        """Generate regular grid points within geometry for temperature interpolation."""
        resolution = resolution or self.interpolation_resolution
        
        # Convert to projected coordinates for metric grid spacing
        if isinstance(geometry, (gpd.GeoDataFrame, gpd.GeoSeries)):
            geometry_projected = geometry.to_crs(CRS_CONFIG["PROCESSING"])
        else:
            geometry_projected = gpd.GeoSeries([geometry], crs=CRS_CONFIG["GEOGRAPHIC"]).to_crs(CRS_CONFIG["PROCESSING"])[0]
        
        # Generate grid coordinates
        bounds = geometry_projected.bounds
        x_range = np.arange(bounds[0], bounds[2] + resolution, resolution)
        y_range = np.arange(bounds[1], bounds[3] + resolution, resolution)
        
        # Create grid points within geometry bounds
        grid_points = []
        for x in x_range:
            for y in y_range:
                point = Point(x, y)
                if geometry_projected.contains(point):
                    grid_points.append(point)
        
        # Create GeoDataFrame and transform back to output CRS
        grid_gdf = gpd.GeoDataFrame(
            geometry=grid_points,
            crs=CRS_CONFIG["PROCESSING"]
        ).to_crs(CRS_CONFIG["OUTPUT"])
        
        if self.logger:
            self.logger.info(f"Generated interpolation grid: {len(grid_gdf)} points at {resolution}m resolution")
        
        return grid_gdf
    
    def _interpolate_temperature(
        self, 
        stations_gdf: gpd.GeoDataFrame, 
        target_gdf: gpd.GeoDataFrame,
        method: str = None
    ) -> gpd.GeoDataFrame:
        """Perform spatial interpolation of temperature from weather stations to grid points."""
        method = method or self.interpolation_method
        
        # Use nearest neighbor for sparse station networks
        if len(stations_gdf) < 3:
            if self.logger:
                self.logger.warning("Limited stations available, using nearest neighbor interpolation")
            method = 'nearest'
        
        # Transform to projected coordinates for accurate distance calculations
        stations_projected = stations_gdf.to_crs(CRS_CONFIG["PROCESSING"])
        target_projected = target_gdf.to_crs(CRS_CONFIG["PROCESSING"])
        
        # Extract coordinates and temperature values
        station_coords = np.column_stack([
            stations_projected.geometry.x.values,
            stations_projected.geometry.y.values
        ])
        station_temps = stations_projected['ground_temp'].values
        
        target_coords = np.column_stack([
            target_projected.geometry.x.values,
            target_projected.geometry.y.values
        ])
        
        # Perform spatial interpolation
        interpolated_temps = griddata(
            station_coords, 
            station_temps, 
            target_coords, 
            method=method,
            fill_value=np.nan
        )
        
        # Handle missing values with nearest neighbor fallback
        if np.any(np.isnan(interpolated_temps)):
            if self.logger:
                self.logger.info("Filling gaps with nearest neighbor interpolation")
            nan_mask = np.isnan(interpolated_temps)
            nearest_temps = griddata(
                station_coords, 
                station_temps, 
                target_coords[nan_mask], 
                method='nearest'
            )
            interpolated_temps[nan_mask] = nearest_temps
        
        # Create result GeoDataFrame
        result_gdf = target_gdf.copy()
        result_gdf['ground_temp'] = interpolated_temps
        
        if self.logger:
            self.logger.info(f"Temperature interpolation completed for {len(result_gdf)} points")
        
        return result_gdf
    
    def _get_stations_in_area(self, geometry: Union[Point, Polygon, MultiPolygon]) -> gpd.GeoDataFrame:
        """Find all weather stations within buffered study area."""
        # Apply spatial buffer in projected coordinates
        if isinstance(geometry, (gpd.GeoDataFrame, gpd.GeoSeries)):
            geometry_projected = geometry.to_crs(CRS_CONFIG["PROCESSING"])
        else:
            geometry_projected = gpd.GeoSeries([geometry], crs=CRS_CONFIG["GEOGRAPHIC"]).to_crs(CRS_CONFIG["PROCESSING"])[0]
        
        buffered_geometry = geometry_projected.buffer(self.buffer_distance)
        
        if self.logger:
            self.logger.info(f"Searching for stations within {self.buffer_distance}m buffer")
        
        # Convert back to geographic coordinates for API query
        buffered_geographic = gpd.GeoSeries([buffered_geometry], crs=CRS_CONFIG["PROCESSING"]).to_crs(CRS_CONFIG["GEOGRAPHIC"])[0]
        bbox = self._get_bounding_box_from_geometry(buffered_geographic)
        
        # Query DWD API for available stations
        request = DwdObservationRequest(
            parameters=DWD_TEMPERATURE_PARAMETERS,
            start_date="2024-01-01",  # Brief period for station discovery
            end_date="2024-01-02",
            settings=self.settings,
        )
        
        stations_df = request.all().df
        
        if stations_df.is_empty():
            if self.logger:
                self.logger.warning("No weather stations found in DWD database")
            return gpd.GeoDataFrame()
        
        # Filter stations within bounding box
        stations_filtered = stations_df.filter(
            (stations_df["latitude"] >= bbox['min_lat']) &
            (stations_df["latitude"] <= bbox['max_lat']) &
            (stations_df["longitude"] >= bbox['min_lon']) &
            (stations_df["longitude"] <= bbox['max_lon'])
        )
        
        if stations_filtered.is_empty():
            if self.logger:
                self.logger.warning("No stations found within specified area")
            return gpd.GeoDataFrame()
        
        # Convert to GeoDataFrame
        stations_gdf = gpd.GeoDataFrame(
            stations_filtered.to_pandas(),
            geometry=gpd.points_from_xy(
                stations_filtered["longitude"],
                stations_filtered["latitude"]
            ),
            crs=CRS_CONFIG["GEOGRAPHIC"]
        )
        
        if self.logger:
            self.logger.info(f"Found {len(stations_gdf)} weather stations in area")
        
        return stations_gdf
    
    def _get_temperature_data_for_period(
        self, 
        station_ids: list, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """Download temperature measurements for specified stations and time period."""
        if self.logger:
            self.logger.info(f"Downloading temperature data for {len(station_ids)} stations "
                           f"from {start_date.date()} to {end_date.date()}")
        
        # Create DWD API request
        request = DwdObservationRequest(
            parameters=DWD_TEMPERATURE_PARAMETERS,
            start_date=start_date,
            end_date=end_date,
            settings=self.settings,
        )
        
        # Retrieve temperature data
        temp_data = request.filter_by_station_id(station_ids).values.all().df
        
        if temp_data.is_empty():
            if self.logger:
                self.logger.warning("No temperature measurements available for specified period")
            return pd.DataFrame()
        
        temp_df = temp_data.to_pandas()
        
        if self.logger:
            self.logger.info(f"Downloaded {len(temp_df)} temperature measurements")
        
        return temp_df
    
    def _calculate_station_averages(
        self,
        stations_gdf: gpd.GeoDataFrame,
        temp_data: pd.DataFrame
    ) -> gpd.GeoDataFrame:
        """Compute average temperature statistics for each weather station."""
        if self.logger:
            self.logger.info("Computing station temperature averages")
        
        if temp_data.empty:
            return gpd.GeoDataFrame()
        
        # Calculate temperature statistics per station
        station_stats = temp_data.groupby('station_id').agg({
            'value': ['mean', 'std', 'count']
        })
        station_stats.columns = ['ground_temp', 'temp_std', 'measurement_count']
        station_stats = station_stats.reset_index()
        
        # Merge with station metadata
        stations_with_temp = stations_gdf.merge(
            station_stats,
            on='station_id',
            how='inner'
        )
        
        # Add measurement period information
        stations_with_temp['period_start'] = temp_data['date'].min()
        stations_with_temp['period_end'] = temp_data['date'].max()
        
        if self.logger:
            self.logger.info(f"Computed averages for {len(stations_with_temp)} stations")
        
        return stations_with_temp
    
    def download_for_area(
        self,
        geometry: Union[Point, Polygon, MultiPolygon, str, Dict[str, Any], gpd.GeoDataFrame],
        start_date: datetime,
        end_date: datetime,
        interpolate: Optional[bool] = None,
        resolution: float = None,
    ) -> Union[gpd.GeoDataFrame, Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]]:
        """
        Download weather data for specified area and time period.
        
        Retrieves temperature measurements from DWD weather stations within the
        study area (plus buffer) and optionally performs spatial interpolation
        to a regular grid for analysis purposes.
        
        Args:
            geometry: Study area as Shapely geometry, GeoJSON, or GeoDataFrame
            start_date: Beginning of measurement period
            end_date: End of measurement period
            interpolate: Enable spatial interpolation (default from settings)
            resolution: Grid resolution for interpolation in meters
            
        Returns:
            If interpolate=False: GeoDataFrame with station data
            If interpolate=True: Tuple of (station_data, interpolated_grid)
            
        Raises:
            ValueError: If no weather stations or data available for the area/period
        """
        # Apply default parameters
        interpolate = self.interpolate_by_default if interpolate is None else interpolate
        resolution = resolution or self.interpolation_resolution
        
        if self.logger:
            self.logger.info(f"Processing weather data request for period "
                           f"{start_date.date()} to {end_date.date()}")
        
        # Standardize geometry input
        if isinstance(geometry, gpd.GeoDataFrame):
            geometry = geometry.geometry.iloc[0]
        elif isinstance(geometry, (str, dict)):
            geometry = self._create_geometry_from_geojson(geometry)
        
        # Find weather stations in area
        stations_gdf = self._get_stations_in_area(geometry)
        if stations_gdf.empty:
            raise ValueError("No weather stations found in specified area")
        
        # Download temperature data
        temp_data = self._get_temperature_data_for_period(
            station_ids=stations_gdf['station_id'].tolist(),
            start_date=start_date,
            end_date=end_date
        )
        if temp_data.empty:
            raise ValueError("No temperature data available for specified period")
        
        # Calculate station averages
        stations_with_temp = self._calculate_station_averages(stations_gdf, temp_data)
        if stations_with_temp.empty:
            raise ValueError("Unable to compute station temperature averages")
        
        # Add metadata
        stations_with_temp['source'] = 'station'
        
        # Perform interpolation if requested
        if interpolate:
            if self.logger:
                self.logger.info("Generating interpolated temperature grid")
            
            # Create interpolation grid
            grid_gdf = self._create_interpolation_grid(geometry, resolution)
            if grid_gdf.empty:
                if self.logger:
                    self.logger.warning("Unable to create interpolation grid, returning station data only")
                return stations_with_temp
            
            # Interpolate temperatures to grid
            interpolated_gdf = self._interpolate_temperature(
                stations_with_temp,
                grid_gdf,
                method=self.interpolation_method
            )
            
            # Add metadata to interpolated results
            interpolated_gdf['source'] = 'interpolated'
            interpolated_gdf['n_stations'] = len(stations_with_temp)
            interpolated_gdf['resolution_m'] = resolution
            interpolated_gdf['period_start'] = stations_with_temp['period_start'].iloc[0]
            interpolated_gdf['period_end'] = stations_with_temp['period_end'].iloc[0]
            
            return stations_with_temp, interpolated_gdf
        else:
            return stations_with_temp


if __name__ == "__main__":
    import shapely.geometry
    
    # Example usage for testing
    logging.basicConfig(level=logging.INFO)
    
    downloader = DWDDataDownloader(verbose=True)
    
    # Test with Berlin city center area
    test_geometry = gpd.GeoDataFrame(
        [1], 
        geometry=[shapely.geometry.box(13.3, 52.4, 13.5, 52.6)], 
        crs="EPSG:4326"
    )
    
    try:
        result_gdf = downloader.download_for_area(
            test_geometry, 
            datetime(2023, 7, 1), 
            datetime(2023, 7, 31),
            interpolate=False
        )
        print(f"Downloaded weather data for {len(result_gdf)} stations")
        print(f"Columns: {list(result_gdf.columns)}")
    except Exception as e:
        print(f"Download failed: {e}")