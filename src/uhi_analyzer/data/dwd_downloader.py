#!/usr/bin/env python3
"""
DWD Weather Data Downloader - Downloads weather data based on geometry and time period.
"""

import logging
from datetime import datetime
from typing import Union, Dict, Any
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon, MultiPolygon, shape
import json
import numpy as np
from scipy.interpolate import griddata

from wetterdienst import Settings
from wetterdienst.provider.dwd.observation import DwdObservationRequest

from ..config.settings import (
    DWD_SETTINGS, DWD_TEMPERATURE_PARAMETERS,
    DWD_BUFFER_DISTANCE, DWD_INTERPOLATION_RESOLUTION, 
    DWD_INTERPOLATION_METHOD, DWD_INTERPOLATE_BY_DEFAULT,
    CRS_CONFIG
)

# Configure logging
logger = logging.getLogger(__name__)


class DWDDataDownloader:
    """
    Service for retrieving and averaging weather data based on geometry and time period.
    """
    
    def __init__(self, buffer_distance: float = None, interpolation_method: str = None,
                 interpolate_by_default: bool = None, interpolation_resolution: float = None):
        """
        Initializes the Weather Service.
        
        Args:
            buffer_distance: Optional buffer in meters (default from config)
            interpolation_method: Optional interpolation method (default from config)
            interpolate_by_default: Whether to interpolate by default (default from config)
            interpolation_resolution: Resolution of the interpolation grid in meters (default from config)
        """
        # Create settings with project configurations
        settings_kwargs = {
            "ts_shape": DWD_SETTINGS["ts_shape"],
            "ts_humanize": DWD_SETTINGS["ts_humanize"],
            "ts_convert_units": DWD_SETTINGS["ts_convert_units"],
        }
        self.settings = Settings(**settings_kwargs)
        
        # Set buffer and interpolation settings
        self.buffer_distance = buffer_distance or DWD_BUFFER_DISTANCE
        self.interpolation_method = interpolation_method or DWD_INTERPOLATION_METHOD
        self.interpolate_by_default = interpolate_by_default if interpolate_by_default is not None else DWD_INTERPOLATE_BY_DEFAULT
        self.interpolation_resolution = interpolation_resolution or DWD_INTERPOLATION_RESOLUTION
    
    def _create_geometry_from_geojson(self, geojson: Union[str, Dict[str, Any]]) -> Union[Point, Polygon, MultiPolygon]:
        """
        Creates a Shapely geometry from GeoJSON.
        
        Args:
            geojson: GeoJSON as string or dictionary
            
        Returns:
            Shapely geometry
        """
        if isinstance(geojson, str):
            geojson = json.loads(geojson)
        
        return shape(geojson)
    
    def _get_bounding_box_from_geometry(self, geometry: Union[Point, Polygon, MultiPolygon]) -> Dict[str, float]:
        """
        Creates a bounding box from a geometry.
        
        Args:
            geometry: Shapely geometry
            
        Returns:
            Dictionary with min/max coordinates
        """
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
    
    def _create_interpolation_grid(self, geometry: Union[Point, Polygon, MultiPolygon], 
                                 resolution: float = 1000) -> gpd.GeoDataFrame:
        """
        Creates a regular grid for interpolation.
        
        Args:
            geometry: Shapely geometry
            resolution: Grid resolution in meters
            
        Returns:
            GeoDataFrame with grid points
        """
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
        
        logger.info(f"Interpolation grid created: {len(grid_gdf)} points with {resolution}m resolution")
        return grid_gdf
    
    def _interpolate_temperature(self, stations_gdf: gpd.GeoDataFrame, 
                               target_gdf: gpd.GeoDataFrame,
                               method: str = 'linear') -> gpd.GeoDataFrame:
        """
        Interpolates temperature data from weather stations onto a grid.
        
        Args:
            stations_gdf: GeoDataFrame with averaged station data
            target_gdf: GeoDataFrame with target points
            method: Interpolation method ('linear', 'nearest', 'cubic')
            
        Returns:
            GeoDataFrame with interpolated temperatures
        """
        if len(stations_gdf) < 3:
            logger.warning("Too few stations for interpolation. Using Nearest Neighbor.")
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
            logger.info("Filling NaN values with Nearest Neighbor interpolation")
            nan_mask = np.isnan(result_gdf['ground_temp'])
            if np.any(nan_mask):
                nearest_temps = griddata(
                    station_coords, 
                    station_temps, 
                    target_coords[nan_mask], 
                    method='nearest'
                )
                result_gdf.loc[nan_mask, 'ground_temp'] = nearest_temps
        
        logger.info(f"Temperature interpolation completed: {len(result_gdf)} points")
        return result_gdf
    
    def _get_stations_in_area(self, geometry: Union[Point, Polygon, MultiPolygon]) -> gpd.GeoDataFrame:
        """
        Retrieves all weather stations in a given area.
        
        Args:
            geometry: Shapely geometry
            
        Returns:
            GeoDataFrame with station data
        """
        # Convert geometry to projected CRS for buffer operation
        if isinstance(geometry, (gpd.GeoDataFrame, gpd.GeoSeries)):
            geometry_proj = geometry.to_crs(CRS_CONFIG["PROCESSING"])
        else:
            geometry_proj = gpd.GeoSeries([geometry], crs=CRS_CONFIG["GEOGRAPHIC"]).to_crs(CRS_CONFIG["PROCESSING"])[0]
        
        # Add buffer in meters
        buffered_geometry = geometry_proj.buffer(self.buffer_distance)
        logger.info(f"Geometry extended with {self.buffer_distance}m buffer")
        
        # Back to input CRS for bounding box
        buffered_geometry = gpd.GeoSeries([buffered_geometry], crs=CRS_CONFIG["PROCESSING"]).to_crs(CRS_CONFIG["GEOGRAPHIC"])[0]
        
        # Create bounding box from extended geometry
        bbox = self._get_bounding_box_from_geometry(buffered_geometry)
        logger.info(f"Bounding box: {bbox}")
        
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
            logger.error("No stations available!")
            return gpd.GeoDataFrame()
        
        # Filter stations within the bounding box
        stations_in_bbox = stations_df.filter(
            (stations_df["latitude"] >= bbox['min_lat']) &
            (stations_df["latitude"] <= bbox['max_lat']) &
            (stations_df["longitude"] >= bbox['min_lon']) &
            (stations_df["longitude"] <= bbox['max_lon'])
        )
        
        if stations_in_bbox.is_empty():
            logger.error("No stations available in the bounding box!")
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
        """
        Retrieves temperature data for a period.
        
        Args:
            station_ids: List of station IDs
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with temperature data
        """
        logger.info(f"Loading temperature data for {len(station_ids)} stations from {start_date} to {end_date}")
        
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
            logger.error("No temperature data available!")
            return pd.DataFrame()
        
        # Convert to Pandas DataFrame
        temp_df = temp_data.to_pandas()
        
        logger.info(f"Successfully: {len(temp_df)} temperature measurements loaded")
        return temp_df
    
    def _calculate_station_averages(
        self,
        stations_gdf: gpd.GeoDataFrame,
        temp_data: pd.DataFrame
    ) -> gpd.GeoDataFrame:
        """
        Calculates average temperatures per station.
        
        Args:
            stations_gdf: GeoDataFrame with station data
            temp_data: DataFrame with temperature data
            
        Returns:
            GeoDataFrame with averaged temperatures
        """
        logger.info("Calculating average temperatures per station")
        
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
        
        logger.info(f"Average temperatures calculated for {len(stations_with_temp)} stations")
        
        # Output statistics
        for _, station in stations_with_temp.iterrows():
            logger.info(
                f"Station {station['station_id']} ({station['name']}): "
                f"Ø {station['ground_temp']:.1f}°C "
                f"({station['measurement_count']} measurements, "
                f"σ={station['temp_std']:.1f}°C)"
            )
        
        return stations_with_temp
    
    def get_weather_data(
        self,
        geometry: Union[Point, Polygon, MultiPolygon, str, Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        interpolate: bool = None,
        resolution: float = None
    ) -> gpd.GeoDataFrame:
        """
        Retrieves weather data for a geometry and time period.
        
        Args:
            geometry: Geometry as Shapely object, GeoJSON string, or dictionary
            start_date: Start date
            end_date: End date
            interpolate: Whether to interpolate (default from config)
            resolution: Resolution of the interpolation grid in meters (default from config)
            
        Returns:
            GeoDataFrame with temperature data
        """
        # Parameter set
        interpolate = self.interpolate_by_default if interpolate is None else interpolate
        resolution = self.interpolation_resolution if resolution is None else resolution
        
        logger.info(f"Loading weather data for period {start_date} to {end_date}")
        logger.info(f"Buffer: {self.buffer_distance}m, Resolution: {resolution}m, Interpolation: {interpolate}")
        
        # Create geometry from input
        if isinstance(geometry, (str, dict)):
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
        
        logger.info(f"Returning {len(stations_with_temp)} stations with average temperatures")
        
        # Optional: Perform interpolation
        if interpolate:
            logger.info("Starting temperature interpolation of average values...")
            
            # Create interpolation grid
            grid_gdf = self._create_interpolation_grid(geometry, resolution)
            
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
            
            logger.info(f"Interpolation of average values completed: {len(result_gdf)} points created")
            return result_gdf
        
        # If no interpolation: Return station data
        stations_with_temp['source'] = 'station'
        return stations_with_temp 