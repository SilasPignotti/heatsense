#!/usr/bin/env python3
"""
Urban Heat Island Analysis Backend API

This script serves as the backend foundation for UHI analysis applications.
It accepts user inputs, performs analysis, and returns structured results.

Features:
- Flexible input parameters
- Multiple performance modes (preview, fast, standard, detailed)
- Structured JSON output for APIs
- Comprehensive error handling
- Progress tracking
- Caching support

Usage:
    # Command line
    python uhi_backend_api.py --area "Kreuzberg" --start-date 2023-07-01 --end-date 2023-07-31
    
    # As module
    from scripts.uhi_backend_api import UHIAnalysisBackend
    backend = UHIAnalysisBackend()
    result = backend.analyze(area="Kreuzberg", start_date="2023-07-01", end_date="2023-07-31")
"""

import json
import logging
import sys
import time
import os
from datetime import date, datetime
from typing import Dict, Any, Optional, List, Union
import geopandas as gpd
import numpy as np
import pandas as pd

from heatsense.data.wfs_downloader import WFSDataDownloader
from heatsense.data.corine_downloader import CorineDataDownloader
from heatsense.data.dwd_downloader import DWDDataDownloader
from heatsense.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
from heatsense.config.settings import (
    BERLIN_WFS_ENDPOINTS,
    BERLIN_WFS_FEATURE_TYPES,
    CRS_CONFIG,
    UHI_PERFORMANCE_MODES, 
)


class UHIAnalysisBackend:
    """
    Backend class for Urban Heat Island analysis.
    
    Provides a clean API for performing UHI analysis with various options
    and returns structured results suitable for web applications.
    """
    
    def __init__(self, log_level: str = "INFO"):
        """
        Initialize the UHI Analysis Backend.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.logger = self._setup_logging(log_level)
        self.performance_modes = UHI_PERFORMANCE_MODES
        
        
    def _setup_logging(self, level: str) -> logging.Logger:
        """Set up logging for the backend."""
        logger = logging.getLogger("uhi_backend")
        logger.setLevel(getattr(logging, level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _convert_to_json_serializable(self, obj: Any) -> Any:
        """
        Convert numpy/pandas types to JSON-serializable Python types.
        
        Args:
            obj: Object to convert
            
        Returns:
            JSON-serializable version of the object
        """
        # Handle numpy integer types (NumPy 2.0 compatible)
        if isinstance(obj, (np.integer, np.int8, np.int16, np.int32, np.int64)):
            return int(obj)
        # Handle numpy floating point types (NumPy 2.0 compatible)
        elif isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Series):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._convert_to_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_serializable(item) for item in obj]
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    def analyze(self, area: str, start_date: str, end_date: str, 
                performance_mode: str = "standard") -> Dict[str, Any]:
        """
        Perform UHI analysis with given parameters.
        
        Args:
            area: Area name (Berlin suburb/locality)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            performance_mode: Performance mode (preview, fast, standard, detailed)
            include_weather: Whether to include weather station data
            cloud_threshold: Cloud cover threshold (0-100), None for mode default
            
        Returns:
            Dict with analysis results, metadata, and status
        """
        start_time = time.time()
        
        self.logger.info(f"🔥 Starting UHI Analysis")
        self.logger.info(f"   Area: {area}")
        self.logger.info(f"   Period: {start_date} to {end_date}")
        self.logger.info(f"   Mode: {performance_mode}")
        
        # Get include_weather setting from performance mode config
        mode_config = UHI_PERFORMANCE_MODES.get(performance_mode, {})
        include_weather = mode_config.get('include_weather', False)

        # Initialize result structure
        result = {
            "status": "in_progress",
            "progress": 0,
            "metadata": {
                "area": area,
                "start_date": start_date,
                "end_date": end_date,
                "performance_mode": performance_mode,
                "include_weather": include_weather,
                "timestamp": datetime.now().isoformat(),
                "version": "1.0"
            },
            "data": {},
            "errors": [],
            "warnings": [],
            "execution_time": 0
        }
        
        try:
            # Step 1: Parse inputs
            self.logger.info("📋 Step 1/6: Parsing inputs...")
            start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
            result["progress"] = 10
            
            # Step 2: Download boundary data
            self.logger.info("🗺️  Step 2/6: Downloading boundary data...")
            boundary_data = self._download_boundary_data(area)
            result["progress"] = 25
            
            if boundary_data is None or boundary_data.empty:
                result["status"] = "error"
                result["errors"].append("Failed to download boundary data")
                result["execution_time"] = time.time() - start_time
                return result
            
            # Step 3: Download land cover data
            self.logger.info("🌱 Step 3/6: Downloading land cover data...")
            landcover_data = self._download_landcover_data(
                boundary_data, start_date_parsed, end_date_parsed
            )
            result["progress"] = 40
            
            if landcover_data is None or landcover_data.empty:
                result["status"] = "error"
                result["errors"].append("Failed to download land cover data")
                result["execution_time"] = time.time() - start_time
                return result
            
            # Step 4: Download weather data
            weather_stations = None
            weather_stations_interpolated = None
            if include_weather:
                self.logger.info("🌤️  Step 4/6: Downloading weather data...")
                weather_stations, weather_stations_interpolated = self._download_weather_data(
                    boundary_data, start_date_parsed, end_date_parsed
                )
            
            # Step 5: Configure analyzer
            self.logger.info("⚙️  Step 5/6: Configuring analyzer...")
            analyzer = self._create_analyzer(performance_mode)
            result["progress"] = 60
            
            # Step 6: Run analysis
            self.logger.info("🔥 Step 6/6: Running UHI analysis...")
            analysis_results = analyzer.analyze_heat_islands(
                city_boundary=boundary_data,
                date_range=(start_date_parsed, end_date_parsed),
                landuse_data=landcover_data,
                weather_stations=weather_stations_interpolated
            )
            result["progress"] = 80
            
            # Store raw data for processing
            analysis_results["raw_weather_stations"] = weather_stations
            analysis_results["boundary_data"] = boundary_data
            
            # Process results
            self.logger.info("📊 Processing results...")
            result["data"] = self._process_analysis_results(analysis_results)
            result["progress"] = 100
            result["status"] = "completed"
            
            # Add performance metrics
            execution_time = time.time() - start_time
            result["execution_time"] = self._convert_to_json_serializable(round(execution_time, 2))
            result["metadata"]["performance_metrics"] = self._get_performance_metrics(
                analysis_results, execution_time, performance_mode
            )
            
            self.logger.info(f"✅ Analysis completed in {execution_time:.1f}s")
            
            # Ensure the entire result is JSON serializable
            result = self._convert_to_json_serializable(result)
            
            
        except Exception as e:
            self.logger.error(f"❌ Analysis failed: {str(e)}")
            result["status"] = "error"
            result["errors"].append(f"Analysis failed: {str(e)}")
            result["execution_time"] = self._convert_to_json_serializable(time.time() - start_time)
            # Ensure error result is also JSON serializable
            result = self._convert_to_json_serializable(result)
        
        
        return result
    
    def _get_boundary_type(self, area: str) -> str:
        """
        Determine boundary type based on area name.
        
        Returns:
            str: One of 'locality_boundary', 'district_boundary', 'state_boundary'
        """
        # Simple heuristic - in practice you might want more sophisticated logic
        area_lower = area.lower()
        
        # Check for district names (Bezirke)
        berlin_districts = [
            'charlottenburg-wilmersdorf', 'friedrichshain-kreuzberg', 'lichtenberg',
            'marzahn-hellersdorf', 'mitte', 'neukölln', 'pankow', 'reinickendorf',
            'spandau', 'steglitz-zehlendorf', 'tempelhof-schöneberg', 'treptow-köpenick'
        ]
        
        if any(district in area_lower for district in berlin_districts):
            return "district_boundary"
        
        # Check for state-level requests (Berlin, Brandenburg)
        if area_lower in ['berlin']:
            return "state_boundary"
        
        # Default to locality (Ortsteil)
        return "locality_boundary"

    def _download_boundary_data(self, area: str) -> Optional[gpd.GeoDataFrame]:
        """Download boundary data for the specified area and return as GeoDataFrame."""
        try:
            # Determine the appropriate boundary type
            boundary_type = self._get_boundary_type(area)
            
            # Get endpoint URL and feature type from settings
            endpoint_url = BERLIN_WFS_ENDPOINTS[boundary_type]
            feature_type = BERLIN_WFS_FEATURE_TYPES[boundary_type]
            target_crs = CRS_CONFIG["OUTPUT"]
            
            # Use simplified WFS downloader with direct URL
            wfs_downloader = WFSDataDownloader(
                endpoint_url=endpoint_url,
                verbose=False  # Silent mode for backend
            )
            
            # Download all boundaries directly to memory
            boundaries_gdf = wfs_downloader.download_to_geodataframe(
                type_name=feature_type,
                target_crs=target_crs
            )
            
            if boundaries_gdf.empty:
                self.logger.error(f"No {boundary_type} data downloaded")
                return None
            
            # Determine the correct column name based on boundary type
            if boundary_type == "state_boundary":
                name_column = "namlan"
            elif boundary_type == "district_boundary":
                name_column = "namgem"
            elif boundary_type == "locality_boundary":
                name_column = "nam"
            else:
                # Fallback to original logic
                name_columns = ['namlan', 'namgem', 'nam']
                name_column = None
                for col in name_columns:
                    if col in boundaries_gdf.columns:
                        name_column = col
                        break
            
            if not name_column or name_column not in boundaries_gdf.columns:
                self.logger.error(f"Name column '{name_column}' not found in {boundary_type}")
                return gpd.GeoDataFrame(columns=boundaries_gdf.columns, crs=boundaries_gdf.crs)
            
            # Debug: Log available area names
            available_areas = boundaries_gdf[name_column].tolist()
            self.logger.info(f"Available areas in {boundary_type} (column '{name_column}'): {available_areas}")
            
            # Filter for the specific area (case insensitive)
            area_mask = boundaries_gdf[name_column].str.contains(area, case=False, na=False)
            area_gdf = boundaries_gdf[area_mask]
            
            if len(area_gdf) == 0:
                self.logger.error(f"Area '{area}' not found in {boundary_type}. Available: {available_areas}")
                return gpd.GeoDataFrame(columns=boundaries_gdf.columns, crs=boundaries_gdf.crs)
            
            # If multiple matches, take the first one
            if len(area_gdf) > 1:
                self.logger.warning(f"Multiple matches found for '{area}', using the first one: {area_gdf[name_column].iloc[0]}")
                area_gdf = area_gdf.iloc[[0]]
            
            self.logger.info(f"Successfully filtered to {len(area_gdf)} boundary(ies) for '{area}' using column '{name_column}'")
            return area_gdf
            
        except Exception as e:
            self.logger.error(f"Error downloading boundary data: {e}")
            return None
    
    def _download_landcover_data(self, boundary_data: gpd.GeoDataFrame, start_date: date, 
                                end_date: date) -> Optional[gpd.GeoDataFrame]:
        """Download land cover data for the boundary area and return as GeoDataFrame."""
        try:
            # Convert dates to datetime for the Corine downloader
            from datetime import datetime
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            # Use simplified Corine downloader with date range
            corine_downloader = CorineDataDownloader(
                year_or_period=(start_datetime, end_datetime),
                verbose=False  # Silent mode for backend
            )
            
            # Download data directly to memory
            landcover_gdf = corine_downloader.download_for_area(boundary_data, target_crs=CRS_CONFIG["OUTPUT"])
            
            if landcover_gdf.empty:
                self.logger.error("No land cover data downloaded")
                return None
            
            self.logger.info(f"Downloaded {len(landcover_gdf)} land cover features")
            return landcover_gdf
            
        except Exception as e:
            self.logger.error(f"Error downloading landcover data: {e}")
            return None
    
    def _download_weather_data(self, boundary_data: gpd.GeoDataFrame, start_date: date, 
                            end_date: date, interpolate: bool = True) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:  
        """Download weather station data for the boundary area and return as GeoDataFrame."""
        try:
            # Convert dates to datetime for the DWD downloader
            from datetime import datetime
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            # Use DWD downloader with reasonable defaults for backend
            dwd_downloader = DWDDataDownloader(
                verbose=False,  # Silent mode for backend
                interpolate_by_default=interpolate
            )
            
            # Download weather data for the area
            weather_gdf, weather_gdf_interpolated = dwd_downloader.download_for_area(
                geometry=boundary_data,
                start_date=start_datetime,
                end_date=end_datetime
            )
            
            if weather_gdf.empty:
                self.logger.warning("No weather station data downloaded")
                return None, None
            
            self.logger.info(f"Downloaded {len(weather_gdf)} weather station records")
            return weather_gdf, weather_gdf_interpolated
            
        except Exception as e:
            self.logger.error(f"Error downloading weather data: {e}")
            return None, None
    
    def _create_analyzer(self, performance_mode: str):
        """Create analyzer directly with performance mode configuration."""

        if performance_mode not in UHI_PERFORMANCE_MODES:
            raise ValueError(f"Invalid performance mode: {performance_mode}")
        
        mode_config = UHI_PERFORMANCE_MODES[performance_mode]
        
        # Apply mode defaults
        analyzer_kwargs = {
            'cloud_cover_threshold': mode_config.get('cloud_cover_threshold', 20),
            'grid_cell_size': mode_config.get('grid_cell_size', 100),
            'hotspot_threshold': mode_config.get('hotspot_threshold', 0.9),
            'min_cluster_size': mode_config.get('min_cluster_size', 5),
        }
        
        analyzer = UrbanHeatIslandAnalyzer(**analyzer_kwargs)
        
        analyzer_type = type(analyzer).__name__
        self.logger.info(f"🚀 Created {analyzer_type} with {performance_mode} mode")
        
        return analyzer
    
    def _process_analysis_results(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process analysis results into structured format."""
        processed = {
            "summary": {},
            "temperature_data": {},
            "hotspots": {},
            "landuse_correlation": {},
            "recommendations": {},
            "visualizations": {},
            "boundary": {}
        }
        
        # Process temperature statistics
        if "temperature_statistics" in analysis_results:
            temp_stats = analysis_results["temperature_statistics"]
            if temp_stats is not None and 'temperature' in temp_stats.columns:
                valid_temps = temp_stats['temperature'].dropna()
                
                processed["temperature_data"] = {
                    "grid_cells_total": self._convert_to_json_serializable(len(temp_stats)),
                    "grid_cells_valid": self._convert_to_json_serializable(len(valid_temps)),
                    "statistics": {
                        "mean": self._convert_to_json_serializable(round(valid_temps.mean(), 2)) if len(valid_temps) > 0 else None,
                        "std": self._convert_to_json_serializable(round(valid_temps.std(), 2)) if len(valid_temps) > 0 else None,
                        "min": self._convert_to_json_serializable(round(valid_temps.min(), 2)) if len(valid_temps) > 0 else None,
                        "max": self._convert_to_json_serializable(round(valid_temps.max(), 2)) if len(valid_temps) > 0 else None,
                        "percentiles": {
                            "p25": self._convert_to_json_serializable(round(valid_temps.quantile(0.25), 2)) if len(valid_temps) > 0 else None,
                            "p50": self._convert_to_json_serializable(round(valid_temps.quantile(0.50), 2)) if len(valid_temps) > 0 else None,
                            "p75": self._convert_to_json_serializable(round(valid_temps.quantile(0.75), 2)) if len(valid_temps) > 0 else None,
                            "p90": self._convert_to_json_serializable(round(valid_temps.quantile(0.90), 2)) if len(valid_temps) > 0 else None
                        }
                    },
                    "geojson": json.loads(temp_stats.to_json())
                }
        
        # Process hotspots
        if "hot_spots" in analysis_results:
            hotspots = analysis_results["hot_spots"]
            if hotspots is not None and len(hotspots) > 0:
                processed["hotspots"] = {
                    "count": self._convert_to_json_serializable(len(hotspots)),
                    "temperature_range": {
                        "min": self._convert_to_json_serializable(round(hotspots['temperature'].min(), 2)) if 'temperature' in hotspots.columns else None,
                        "max": self._convert_to_json_serializable(round(hotspots['temperature'].max(), 2)) if 'temperature' in hotspots.columns else None
                    },
                    "geojson": json.loads(hotspots.to_json())
                }
        
        # Process land use correlations with updated structure
        if "land_use_correlation" in analysis_results:
            landuse = analysis_results["land_use_correlation"]
            if landuse:
                processed["landuse_correlation"] = {
                    "statistics": self._convert_to_json_serializable(landuse.get("statistics", {})),
                    "correlations": self._convert_to_json_serializable(landuse.get("correlations", {})),
                    "category_descriptions": landuse.get("category_descriptions", {}),
                    "analysis_type": landuse.get("analysis_type", "grouped"),
                    "summary": self._convert_to_json_serializable(landuse.get("summary", {}))
                }
                        
        # Process weather station data (from raw data if available)
        if "raw_weather_stations" in analysis_results and analysis_results["raw_weather_stations"] is not None:
            weather_stations = analysis_results["raw_weather_stations"]
            try:
                processed["weather_stations"] = {
                    "count": self._convert_to_json_serializable(len(weather_stations)),
                    "temperature_range": {
                        "min": self._convert_to_json_serializable(round(weather_stations['ground_temp'].min(), 2)) if 'ground_temp' in weather_stations.columns else None,
                        "max": self._convert_to_json_serializable(round(weather_stations['ground_temp'].max(), 2)) if 'ground_temp' in weather_stations.columns else None
                    },
                    "geojson": json.loads(weather_stations.to_json())
                }
            except Exception as e:
                self.logger.warning(f"Failed to process weather station data: {e}")
        elif "ground_validation" in analysis_results:
            weather_data = analysis_results["ground_validation"]
            if weather_data and "station_data" in weather_data:
                station_data = weather_data["station_data"]
                try:
                    processed["weather_stations"] = {
                        "count": self._convert_to_json_serializable(len(station_data)),
                        "temperature_range": {
                            "min": self._convert_to_json_serializable(round(station_data['ground_temp'].min(), 2)) if 'ground_temp' in station_data.columns else None,
                            "max": self._convert_to_json_serializable(round(station_data['ground_temp'].max(), 2)) if 'ground_temp' in station_data.columns else None
                        },
                        "geojson": json.loads(station_data.to_json())
                    }
                except Exception as e:
                    self.logger.warning(f"Failed to process weather station data: {e}")
        
        # Process recommendations
        if "mitigation_recommendations" in analysis_results:
            recommendations = analysis_results["mitigation_recommendations"]
            if recommendations:
                # Handle both list and dict formats
                if isinstance(recommendations, list):
                    processed["recommendations"] = {
                        "strategies": recommendations,
                        "total_count": len(recommendations)
                    }
                else:
                    processed["recommendations"] = recommendations
        
        # Process boundary data
        if "boundary_data" in analysis_results and analysis_results["boundary_data"] is not None:
            boundary_data = analysis_results["boundary_data"]
            try:
                processed["boundary"] = json.loads(boundary_data.to_json())
            except Exception as e:
                self.logger.warning(f"Failed to process boundary data: {e}")
        
        # Create summary
        processed["summary"] = {
            "analysis_type": "Urban Heat Island Analysis",
            "temperature_overview": processed["temperature_data"].get("statistics", {}),
            "hotspots_count": processed["hotspots"].get("count", 0),
            "correlation_strength": self._convert_to_json_serializable(processed["landuse_correlation"].get("correlations", {}).get("overall", {}).get("correlation", 0)),
            "recommendations_count": self._convert_to_json_serializable(
                len(processed["recommendations"].get("strategies", [])) 
                if isinstance(processed["recommendations"], dict) 
                else len(processed["recommendations"]) if processed["recommendations"] else 0
            )
        }
        
        return processed
    
    def _get_performance_metrics(self, analysis_results: Dict[str, Any], 
                                execution_time: float, performance_mode: str) -> Dict[str, Any]:
        """Get performance metrics for the analysis."""
        temp_stats = analysis_results.get("temperature_statistics")
        metadata = analysis_results.get("metadata", {})
        
        # Check if weather stations were used based on performance mode
        used_weather_stations = performance_mode in ["detailed", "standard"]
        
        return {
            "execution_time_seconds": self._convert_to_json_serializable(execution_time),
            "performance_mode": performance_mode,
            "analyzer_type": metadata.get("performance_mode", "unknown"),
            "grid_cells_processed": self._convert_to_json_serializable(len(temp_stats)) if temp_stats is not None else 0,
            "data_sources": {
                "satellite_data": True,
                "weather_stations": used_weather_stations,
                "land_cover": True
            }
        }
    
    

