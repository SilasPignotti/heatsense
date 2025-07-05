#!/usr/bin/env python3
"""
DWD Weather Data Downloader - Simple downloader for German weather station data.

Simplified downloader with minimal configuration and direct data return.
"""

import logging
from datetime import datetime
from typing import Union, Dict, Any, Optional, Literal, Tuple
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon, MultiPolygon, shape
import json
import numpy as np
from scipy.interpolate import griddata

from wetterdienst import Settings
from wetterdienst.provider.dwd.observation import DwdObservationRequest

from ..config.settings import CRS_CONFIG, DWD_SETTINGS, DWD_TEMPERATURE_PARAMETERS

# Data processing modes
ProcessingMode = Literal['station_data', 'interpolated', 'uhi_analysis']


class DWDDataDownloader:
    """
    Simple downloader for German Weather Service (DWD) data.
    
    Features:
    - Flexible geometry input: Points, Polygons, GeoJSON
    - Configurable spatial buffers and interpolation
    - Multiple processing modes
    - Direct data return (no saving functionality)
    """
    
    def __init__(
        self, 
        buffer_distance: float = 10000, # Buffer distance in meters
        interpolation_method: str = "linear", # Interpolation method
        interpolate_by_default: bool = True, # Perform interpolation by default
        interpolation_resolution: float = 30, # Resolution in meters
        log_file: Optional[str] = None,
        verbose: bool = True
    ):
        """
        Initialize the DWD Weather Data Downloader.
        
        Args:
            buffer_distance: Buffer distance in meters for station search
            interpolation_method: Interpolation method ('linear', 'nearest', 'cubic')
            interpolate_by_default: Whether to interpolate by default
            interpolation_resolution: Resolution of the interpolation grid in meters
            log_file: Optional log file path
            verbose: Enable console logging
        """
        self.buffer_distance = buffer_distance
        self.interpolation_method = interpolation_method
        self.interpolate_by_default = interpolate_by_default
        self.interpolation_resolution = interpolation_resolution
        
        # Setup logger
        self.logger = self._setup_logger(log_file) if verbose or log_file else None
        
        # Create wetterdienst settings
        self.settings = Settings(**DWD_SETTINGS)
        
        if self.logger:
            self.logger.info(f"DWD Downloader initialized: buffer={self.buffer_distance}m, method={self.interpolation_method}")

    def _setup_logger(self, log_file: Optional[str] = None) -> logging.Logger:
        """Set up simple logger."""
        logger = logging.getLogger(f"{__name__}.DWDDataDownloader")
        
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            # Console handler
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            logger.addHandler(handler)
            
            # File handler
            if log_file:
                from pathlib import Path
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s: %(message)s'))
                logger.addHandler(file_handler)
        
        return logger
    
    def _create_geometry_from_geojson(self, geojson: Union[str, Dict[str, Any]]) -> Union[Point, Polygon, MultiPolygon]:
        """Create a Shapely geometry from GeoJSON."""
        if isinstance(geojson, str):
            geojson = json.loads(geojson)
        return shape(geojson)
    
    def _get_bounding_box_from_geometry(self, geometry: Union[Point, Polygon, MultiPolygon]) -> Dict[str, float]:
        """Create a bounding box from a geometry."""
        # Ensure the geometry is in WGS84 for lat/lon bounds
        if isinstance(geometry, (gpd.GeoDataFrame, gpd.GeoSeries)):
            geometry = geometry.to_crs(CRS_CONFIG["GEOGRAPHIC"])
        
        bounds = geometry.bounds  # (minx, miny, maxx, maxy)
        
        return {
            'min_lat': bounds[1],  # miny
            'max_lat': bounds[3],  # maxy
            'min_lon': bounds[0],  # minx
            'max_lon': bounds[2]   # maxx
        }
    
    def _create_interpolation_grid(
        self, 
        geometry: Union[Point, Polygon, MultiPolygon], 
        resolution: float = None
    ) -> gpd.GeoDataFrame:
        """Create a regular grid for interpolation."""
        resolution = resolution or self.interpolation_resolution
        
        # Convert geometry to projected CRS for metric calculations
        if isinstance(geometry, (gpd.GeoDataFrame, gpd.GeoSeries)):
            geometry = geometry.to_crs(CRS_CONFIG["PROCESSING"])
        else:
            geometry = gpd.GeoSeries([geometry], crs=CRS_CONFIG["GEOGRAPHIC"]).to_crs(CRS_CONFIG["PROCESSING"])[0]
        
        # Bounding box of the geometry
        bounds = geometry.bounds
        
        # Create grid in projected coordinates
        x_range = np.arange(bounds[0], bounds[2] + resolution, resolution)
        y_range = np.arange(bounds[1], bounds[3] + resolution, resolution)
        
        # Create all combinations
        grid_points = []
        for x in x_range:
            for y in y_range:
                point = Point(x, y)
                if geometry.contains(point):
                    grid_points.append(point)
        
        # As GeoDataFrame with projected CRS
        grid_gdf = gpd.GeoDataFrame(
            geometry=grid_points,
            crs=CRS_CONFIG["PROCESSING"]
        )
        
        # Back to output CRS
        grid_gdf = grid_gdf.to_crs(CRS_CONFIG["OUTPUT"])
        
        if self.logger:
            self.logger.info(f"Interpolation grid created: {len(grid_gdf)} points with {resolution}m resolution")
        return grid_gdf
    
    def _interpolate_temperature(
        self, 
        stations_gdf: gpd.GeoDataFrame, 
        target_gdf: gpd.GeoDataFrame,
        method: str = None
    ) -> gpd.GeoDataFrame:
        """Interpolate temperature data from weather stations onto a grid."""
        method = method or self.interpolation_method
        
        if len(stations_gdf) < 3:
            if self.logger:
                self.logger.warning("Too few stations for interpolation. Using Nearest Neighbor.")
            method = 'nearest'
        
        # Convert both DataFrames to projected CRS for metric calculations
        stations_projected = stations_gdf.to_crs(CRS_CONFIG["PROCESSING"])
        target_projected = target_gdf.to_crs(CRS_CONFIG["PROCESSING"])
        
        # Coordinates of stations (in meters)
        station_coords = np.array([
            stations_projected.geometry.x.values,
            stations_projected.geometry.y.values
        ]).T
        
        # Averaged temperature values
        station_temps = stations_projected['ground_temp'].values
        
        # Coordinates of target points (in meters)
        target_coords = np.array([
            target_projected.geometry.x.values,
            target_projected.geometry.y.values
        ]).T
        
        # Interpolation
        interpolated_temps = griddata(
            station_coords, 
            station_temps, 
            target_coords, 
            method=method,
            fill_value=np.nan
        )
        
        # Result GeoDataFrame (in output CRS)
        result_gdf = target_gdf.copy()
        result_gdf['ground_temp'] = interpolated_temps
        
        # Fill NaN values with Nearest Neighbor interpolation
        if np.any(np.isnan(result_gdf['ground_temp'])):
            if self.logger:
                self.logger.info("Filling NaN values with Nearest Neighbor interpolation")
            nan_mask = np.isnan(result_gdf['ground_temp'])
            if np.any(nan_mask):
                nearest_temps = griddata(
                    station_coords, 
                    station_temps, 
                    target_coords[nan_mask], 
                    method='nearest'
                )
                result_gdf.loc[nan_mask, 'ground_temp'] = nearest_temps
        
        if self.logger:
            self.logger.info(f"Temperature interpolation completed: {len(result_gdf)} points")
        return result_gdf
    
    def _get_stations_in_area(self, geometry: Union[Point, Polygon, MultiPolygon]) -> gpd.GeoDataFrame:
        """Retrieve all weather stations in a given area."""
        # Convert geometry to projected CRS for buffer operation
        if isinstance(geometry, (gpd.GeoDataFrame, gpd.GeoSeries)):
            geometry_proj = geometry.to_crs(CRS_CONFIG["PROCESSING"])
        else:
            geometry_proj = gpd.GeoSeries([geometry], crs=CRS_CONFIG["GEOGRAPHIC"]).to_crs(CRS_CONFIG["PROCESSING"])[0]
        
        # Add buffer in meters
        buffered_geometry = geometry_proj.buffer(self.buffer_distance)
        if self.logger:
            self.logger.info(f"Geometry extended with {self.buffer_distance}m buffer")
        
        # Back to input CRS for bounding box
        buffered_geometry = gpd.GeoSeries([buffered_geometry], crs=CRS_CONFIG["PROCESSING"]).to_crs(CRS_CONFIG["GEOGRAPHIC"])[0]
        
        # Create bounding box from extended geometry
        bbox = self._get_bounding_box_from_geometry(buffered_geometry)
        if self.logger:
            self.logger.info(f"Bounding box: {bbox}")
        
        # Create request for hourly temperature data
        request = DwdObservationRequest(
            parameters=DWD_TEMPERATURE_PARAMETERS,
            start_date="2024-01-01",  # Short period for station search
            end_date="2024-01-02",
            settings=self.settings,
        )
        
        # Retrieve all stations
        stations_df = request.all().df
        
        if stations_df.is_empty():
            if self.logger:
                self.logger.error("No stations available!")
            return gpd.GeoDataFrame()
        
        # Filter stations within the bounding box
        stations_in_bbox = stations_df.filter(
            (stations_df["latitude"] >= bbox['min_lat']) &
            (stations_df["latitude"] <= bbox['max_lat']) &
            (stations_df["longitude"] >= bbox['min_lon']) &
            (stations_df["longitude"] <= bbox['max_lon'])
        )
        
        if stations_in_bbox.is_empty():
            if self.logger:
                self.logger.error("No stations available in the bounding box!")
            return gpd.GeoDataFrame()
        
        # As GeoDataFrame with input CRS
        stations_gdf = gpd.GeoDataFrame(
            stations_in_bbox.to_pandas(),
            geometry=gpd.points_from_xy(
                stations_in_bbox["longitude"],
                stations_in_bbox["latitude"]
            ),
            crs=CRS_CONFIG["GEOGRAPHIC"]
        )
        
        return stations_gdf
    
    def _get_temperature_data_for_period(
        self, 
        station_ids: list, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """Retrieve temperature data for a period."""
        if self.logger:
            self.logger.info(f"Loading temperature data for {len(station_ids)} stations from {start_date} to {end_date}")
        
        # Create request for hourly temperature data
        request = DwdObservationRequest(
            parameters=DWD_TEMPERATURE_PARAMETERS,
            start_date=start_date,
            end_date=end_date,
            settings=self.settings,
        )
        
        # Retrieve data for the filtered stations
        temp_data = request.filter_by_station_id(station_ids).values.all().df
        
        if temp_data.is_empty():
            if self.logger:
                self.logger.error("No temperature data available!")
            return pd.DataFrame()
        
        # Convert to Pandas DataFrame
        temp_df = temp_data.to_pandas()
        
        if self.logger:
            self.logger.info(f"Successfully loaded: {len(temp_df)} temperature measurements")
        return temp_df
    
    def _calculate_station_averages(
        self,
        stations_gdf: gpd.GeoDataFrame,
        temp_data: pd.DataFrame
    ) -> gpd.GeoDataFrame:
        """Calculate average temperatures per station."""
        if self.logger:
            self.logger.info("Calculating average temperatures per station")
        
        if temp_data.empty:
            return gpd.GeoDataFrame()
        
        # Calculate average temperatures and standard deviation per station
        station_stats = temp_data.groupby('station_id').agg({
            'value': ['mean', 'std', 'count']
        })
        station_stats.columns = ['ground_temp', 'temp_std', 'measurement_count']
        station_stats = station_stats.reset_index()
        
        # Merge with station data
        stations_with_temp = stations_gdf.merge(
            station_stats,
            left_on='station_id',
            right_on='station_id',
            how='inner'
        )
        
        # Add period of measurements
        stations_with_temp['period_start'] = temp_data['date'].min()
        stations_with_temp['period_end'] = temp_data['date'].max()
        
        if self.logger:
            self.logger.info(f"Average temperatures calculated for {len(stations_with_temp)} stations")
            
            # Output statistics
            for _, station in stations_with_temp.iterrows():
                self.logger.info(
                    f"Station {station['station_id']} ({station['name']}): "
                    f"Ø {station['ground_temp']:.1f}°C "
                    f"({station['measurement_count']} measurements, "
                    f"σ={station['temp_std']:.1f}°C)"
                )
        
        return stations_with_temp


    
    def download_for_area(
        self,
        geometry: Union[Point, Polygon, MultiPolygon, str, Dict[str, Any], gpd.GeoDataFrame],
        start_date: datetime,
        end_date: datetime,
        interpolate: bool = True,
        resolution: float = None,
        processing_mode: ProcessingMode = 'station_data'
    ) -> gpd.GeoDataFrame:
        """
        Download weather data for a geometry and time period.
        
        Args:
            geometry: Geometry as Shapely object, GeoJSON string/dict, or GeoDataFrame
            start_date: Start date
            end_date: End date
            interpolate: Whether to interpolate (default from config)
            resolution: Resolution of the interpolation grid in meters
            processing_mode: Processing mode ('station_data', 'interpolated', 'uhi_analysis')
            
        Returns:
            GeoDataFrame with temperature data
        """
        # Parameter defaults
        interpolate = self.interpolate_by_default if interpolate is None else interpolate
        resolution = resolution or self.interpolation_resolution
        
        # Adjust interpolate flag based on processing mode
        if processing_mode == 'interpolated':
            interpolate = True
        elif processing_mode == 'station_data':
            interpolate = False
        
        if self.logger:
            self.logger.info(f"Loading weather data for period {start_date} to {end_date}")
            self.logger.info(f"Buffer: {self.buffer_distance}m, Resolution: {resolution}m, Mode: {processing_mode}")
        
        # Create geometry from input
        if isinstance(geometry, gpd.GeoDataFrame):
            # Use the first geometry if GeoDataFrame
            geometry = geometry.geometry.iloc[0]
        elif isinstance(geometry, (str, dict)):
            geometry = self._create_geometry_from_geojson(geometry)
        
        # Retrieve stations in area
        stations_gdf = self._get_stations_in_area(geometry)
        
        if stations_gdf.empty:
            return gpd.GeoDataFrame()
        
        # Retrieve temperature data for the period
        temp_data = self._get_temperature_data_for_period(
            station_ids=stations_gdf['station_id'].tolist(),
            start_date=start_date,
            end_date=end_date
        )
        
        if temp_data.empty:
            return gpd.GeoDataFrame()
        
        # Calculate average temperatures per station
        stations_with_temp = self._calculate_station_averages(stations_gdf, temp_data)
        
        if stations_with_temp.empty:
            return gpd.GeoDataFrame()
        
        if self.logger:
            self.logger.info(f"Found {len(stations_with_temp)} stations with temperature data")
        
        # Perform interpolation if requested
        if interpolate:
            if self.logger:
                self.logger.info("Starting temperature interpolation...")
            
            # Create interpolation grid
            grid_gdf = self._create_interpolation_grid(geometry, resolution)
            
            if grid_gdf.empty:
                if self.logger:
                    self.logger.warning("No grid points created for interpolation")
                result_gdf = stations_with_temp
            else:
                # Interpolate temperatures
                result_gdf = self._interpolate_temperature(
                    stations_with_temp,
                    grid_gdf,
                    method=self.interpolation_method
                )
                
                # Add metadata
                result_gdf['source'] = 'interpolated'
                result_gdf['n_stations'] = len(stations_with_temp)
                result_gdf['resolution_m'] = resolution
                result_gdf['period_start'] = stations_with_temp['period_start'].iloc[0]
                result_gdf['period_end'] = stations_with_temp['period_end'].iloc[0]
                
                if self.logger:
                    self.logger.info(f"Interpolation completed: {len(result_gdf)} points created")
        else:
            # Return station data
            result_gdf = stations_with_temp.copy()
            result_gdf['source'] = 'station'
        
        
        return result_gdf


if __name__ == "__main__":
    # Simple usage example
    downloader = DWDDataDownloader()
    
    # Create a simple test geometry (Berlin center)
    import shapely.geometry
    test_geom = gpd.GeoDataFrame(
        [1], 
        geometry=[shapely.geometry.box(13.3, 52.4, 13.5, 52.6)], 
        crs="EPSG:4326"
    )
    
    try:
        gdf = downloader.download_for_area(
            test_geom, 
            datetime(2023, 7, 1), 
            datetime(2023, 7, 31),
            processing_mode='uhi_analysis'
        )
        print(f"✓ Downloaded {len(gdf)} weather records")
        print(f"Columns: {list(gdf.columns)}")
    except Exception as e:
        print(f"✗ Failed: {e}") 