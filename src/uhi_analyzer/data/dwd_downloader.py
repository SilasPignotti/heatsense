#!/usr/bin/env python3
"""
DWD Weather Data Downloader - Flexible downloader for German weather station data.
"""

import logging
from datetime import datetime
from typing import Union, Dict, Any, Optional, Literal
from pathlib import Path
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

# Data processing modes
ProcessingMode = Literal['station_data', 'interpolated', 'uhi_analysis']

# Configure logging
logger = logging.getLogger(__name__)


class DWDDataDownloader:
    """
    Flexible downloader for German Weather Service (DWD) data.
    
    This downloader retrieves and processes weather station data with options for:
    - Basic station data retrieval
    - Temperature interpolation on custom grids
    - Optional UHI-specific analysis processing
    
    Features:
    - Flexible geometry input: Points, Polygons, GeoJSON
    - Configurable spatial buffers and interpolation
    - Multiple output formats and processing modes
    - Optional UHI analysis features
    """
    
    def __init__(
        self, 
        buffer_distance: float = DWD_BUFFER_DISTANCE,
        interpolation_method: str = DWD_INTERPOLATION_METHOD,
        interpolate_by_default: bool = DWD_INTERPOLATE_BY_DEFAULT,
        interpolation_resolution: float = DWD_INTERPOLATION_RESOLUTION,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initializes the DWD Weather Data Downloader.
        
        Args:
            buffer_distance: Buffer distance in meters for station search (default from config)
            interpolation_method: Interpolation method ('linear', 'nearest', 'cubic')
            interpolate_by_default: Whether to interpolate by default
            interpolation_resolution: Resolution of the interpolation grid in meters
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Create wetterdienst settings with project configurations
        settings_kwargs = {
            "ts_shape": DWD_SETTINGS["ts_shape"],
            "ts_humanize": DWD_SETTINGS["ts_humanize"],
            "ts_convert_units": DWD_SETTINGS["ts_convert_units"],
        }
        self.settings = Settings(**settings_kwargs)
        
        # Set processing parameters
        self.buffer_distance = buffer_distance
        self.interpolation_method = interpolation_method
        self.interpolate_by_default = interpolate_by_default
        self.interpolation_resolution = interpolation_resolution
        
        self.logger.info(f"DWD Downloader initialized: buffer={buffer_distance}m, method={interpolation_method}")
    
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
    
    def _create_interpolation_grid(
        self, 
        geometry: Union[Point, Polygon, MultiPolygon], 
        resolution: float = 1000
    ) -> gpd.GeoDataFrame:
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
        
        self.logger.info(f"Interpolation grid created: {len(grid_gdf)} points with {resolution}m resolution")
        return grid_gdf
    
    def _interpolate_temperature(
        self, 
        stations_gdf: gpd.GeoDataFrame, 
        target_gdf: gpd.GeoDataFrame,
        method: str = 'linear'
    ) -> gpd.GeoDataFrame:
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
        
        self.logger.info(f"Temperature interpolation completed: {len(result_gdf)} points")
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
        self.logger.info(f"Geometry extended with {self.buffer_distance}m buffer")
        
        # Back to input CRS for bounding box
        buffered_geometry = gpd.GeoSeries([buffered_geometry], crs=CRS_CONFIG["PROCESSING"]).to_crs(CRS_CONFIG["GEOGRAPHIC"])[0]
        
        # Create bounding box from extended geometry
        bbox = self._get_bounding_box_from_geometry(buffered_geometry)
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
        """
        Retrieves temperature data for a period.
        
        Args:
            station_ids: List of station IDs
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with temperature data
        """
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
            self.logger.error("No temperature data available!")
            return pd.DataFrame()
        
        # Convert to Pandas DataFrame
        temp_df = temp_data.to_pandas()
        
        self.logger.info(f"Successfully loaded: {len(temp_df)} temperature measurements")
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

    def process_for_uhi_analysis(self, weather_data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Processes weather data specifically for Urban Heat Island analysis.
        
        This method adds UHI-specific columns and calculations:
        - temperature_category: Categorical temperature classification
        - heat_stress_potential: Heat stress indicator based on temperature thresholds
        - measurement_quality: Quality indicator based on station count and std deviation
        
        Args:
            weather_data: GeoDataFrame with temperature data
            
        Returns:
            GeoDataFrame with UHI-specific columns added
        """
        if weather_data.empty:
            return weather_data
        
        result_gdf = weather_data.copy()
        
        # Add temperature categories for UHI analysis
        if 'ground_temp' in result_gdf.columns:
            result_gdf['temperature_category'] = pd.cut(
                result_gdf['ground_temp'],
                bins=[-np.inf, 0, 10, 20, 30, np.inf],
                labels=['very_cold', 'cold', 'moderate', 'warm', 'hot']
            )
            
            # Heat stress potential (relevant for UHI studies)
            result_gdf['heat_stress_potential'] = pd.cut(
                result_gdf['ground_temp'],
                bins=[-np.inf, 15, 25, 30, 35, np.inf],
                labels=['low', 'moderate', 'high', 'very_high', 'extreme']
            )
        
        # Add measurement quality indicator - always add for UHI analysis
        result_gdf['measurement_quality'] = 'unknown'
        
        if 'temp_std' in result_gdf.columns and 'measurement_count' in result_gdf.columns:
            # Quality based on measurement count and low standard deviation
            result_gdf.loc[
                (result_gdf['measurement_count'] >= 100) & (result_gdf['temp_std'] <= 5), 
                'measurement_quality'
            ] = 'high'
            result_gdf.loc[
                (result_gdf['measurement_count'] >= 50) & (result_gdf['temp_std'] <= 8), 
                'measurement_quality'
            ] = 'medium'
            result_gdf.loc[
                result_gdf['measurement_quality'] == 'unknown', 
                'measurement_quality'
            ] = 'low'
        else:
            # Default quality for interpolated data or data without quality indicators
            result_gdf['measurement_quality'] = 'medium'
        
        # Add grid ID for interpolated data (useful for UHI spatial analysis)
        if 'source' in result_gdf.columns and 'interpolated' in result_gdf['source'].values:
            result_gdf['grid_id'] = range(len(result_gdf))
        
        self.logger.info("UHI-specific processing completed")
        return result_gdf
    
    def get_weather_data(
        self,
        geometry: Union[Point, Polygon, MultiPolygon, str, Dict[str, Any], gpd.GeoDataFrame],
        start_date: datetime,
        end_date: datetime,
        interpolate: bool = None,
        resolution: float = None,
        processing_mode: ProcessingMode = 'station_data'
    ) -> gpd.GeoDataFrame:
        """
        Retrieves weather data for a geometry and time period.
        
        Args:
            geometry: Geometry as Shapely object, GeoJSON string/dict, or GeoDataFrame
            start_date: Start date
            end_date: End date
            interpolate: Whether to interpolate (default from config)
            resolution: Resolution of the interpolation grid in meters (default from config)
            processing_mode: Processing mode ('station_data', 'interpolated', 'uhi_analysis')
            
        Returns:
            GeoDataFrame with temperature data
        """
        # Parameter defaults
        interpolate = self.interpolate_by_default if interpolate is None else interpolate
        resolution = self.interpolation_resolution if resolution is None else resolution
        
        # Adjust interpolate flag based on processing mode
        if processing_mode == 'interpolated':
            interpolate = True
        elif processing_mode == 'station_data':
            interpolate = False
        
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
        
        self.logger.info(f"Found {len(stations_with_temp)} stations with temperature data")
        
        # Perform interpolation if requested
        if interpolate:
            self.logger.info("Starting temperature interpolation...")
            
            # Create interpolation grid
            grid_gdf = self._create_interpolation_grid(geometry, resolution)
            
            if grid_gdf.empty:
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
                
                self.logger.info(f"Interpolation completed: {len(result_gdf)} points created")
        else:
            # Return station data
            result_gdf = stations_with_temp.copy()
            result_gdf['source'] = 'station'
        
        # Apply UHI-specific processing if requested
        if processing_mode == 'uhi_analysis':
            result_gdf = self.process_for_uhi_analysis(result_gdf)
        
        return result_gdf
    
    def download_and_save(
        self,
        geometry: Union[Point, Polygon, MultiPolygon, str, Dict[str, Any], gpd.GeoDataFrame],
        start_date: datetime,
        end_date: datetime,
        output_path: Optional[Union[str, Path]] = None,
        output_format: str = 'geojson',
        interpolate: bool = None,
        resolution: float = None,
        processing_mode: ProcessingMode = 'station_data'
    ) -> Path:
        """
        Downloads weather data and saves it to a file.
        
        Args:
            geometry: Geometry specification
            start_date: Start date
            end_date: End date
            output_path: Path for output file (auto-generated if None)
            output_format: Output format ('geojson', 'gpkg', 'csv')
            interpolate: Whether to interpolate
            resolution: Interpolation resolution in meters
            processing_mode: Processing mode ('station_data', 'interpolated', 'uhi_analysis')
            
        Returns:
            Path to the saved file
        """
        # Get weather data
        weather_data = self.get_weather_data(
            geometry=geometry,
            start_date=start_date,
            end_date=end_date,
            interpolate=interpolate,
            resolution=resolution,
            processing_mode=processing_mode
        )
        
        if weather_data.empty:
            raise ValueError("No weather data retrieved")
        
        # Generate output path if not provided
        if output_path is None:
            date_str = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
            mode_suffix = f"_{processing_mode}" if processing_mode != 'station_data' else ""
            
            if output_format == 'csv':
                ext = '.csv'
            elif output_format == 'gpkg':
                ext = '.gpkg'
            else:
                ext = '.geojson'
            
            output_path = Path(f"data/processed/weather/dwd_weather_{date_str}{mode_suffix}{ext}")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save data
        if output_format == 'csv':
            # For CSV, include coordinates as columns
            weather_data_csv = weather_data.copy()
            weather_data_csv['longitude'] = weather_data_csv.geometry.x
            weather_data_csv['latitude'] = weather_data_csv.geometry.y
            weather_data_csv.drop('geometry', axis=1).to_csv(output_path, index=False)
        elif output_format == 'gpkg':
            weather_data.to_file(output_path, driver='GPKG')
        else:  # geojson
            weather_data.to_file(output_path, driver='GeoJSON')
        
        self.logger.info(f"Weather data saved: {output_path} ({len(weather_data)} records)")
        return output_path

    @staticmethod
    def get_default_parameters() -> Dict[str, Any]:
        """
        Returns default configuration parameters.
        
        Returns:
            Dictionary with default parameters
        """
        return {
            'buffer_distance': DWD_BUFFER_DISTANCE,
            'interpolation_method': DWD_INTERPOLATION_METHOD,
            'interpolate_by_default': DWD_INTERPOLATE_BY_DEFAULT,
            'interpolation_resolution': DWD_INTERPOLATION_RESOLUTION,
            'temperature_parameters': DWD_TEMPERATURE_PARAMETERS,
            'settings': DWD_SETTINGS
        } 