#!/usr/bin/env python3
"""
Urban Heat Island analysis backend API.

This module provides the backend foundation for UHI analysis applications with
structured JSON output, comprehensive error handling, and multiple performance
modes for different analysis requirements.

Dependencies:
    - geopandas: Geospatial data processing
    - numpy/pandas: Numerical analysis
    - heatsense.data: Data acquisition modules
    - heatsense.utils: Data processing utilities
    - heatsense.config: Configuration settings
"""

import json
import logging
import time
from datetime import date, datetime
from typing import Any, Dict, Optional

import geopandas as gpd
import numpy as np
import pandas as pd

from heatsense.config.settings import (
    BERLIN_WFS_ENDPOINTS,
    BERLIN_WFS_FEATURE_TYPES,
    CRS_CONFIG,
    UHI_PERFORMANCE_MODES,
)
from heatsense.data.corine_downloader import CorineDataDownloader
from heatsense.data.dwd_downloader import DWDDataDownloader
from heatsense.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
from heatsense.data.wfs_downloader import WFSDataDownloader
from heatsense.utils.data_processor import process_corine_for_uhi


class UHIAnalysisBackend:
    """
    Backend API for Urban Heat Island analysis.
    
    Provides a high-level interface for performing comprehensive UHI analysis
    with configurable performance modes, structured result formatting, and
    integrated error handling for web applications.
    
    Key features:
    - Multiple performance modes (preview, fast, standard, detailed)
    - Automatic data acquisition from multiple sources
    - Structured JSON output with comprehensive metadata
    - Progress tracking and performance metrics
    - Robust error handling and validation
    
    Args:
        log_level: Logging verbosity level (DEBUG, INFO, WARNING, ERROR)
    """
    
    def __init__(self, log_level: str = "INFO"):
        self.logger = self._setup_logging(log_level)
        self.performance_modes = UHI_PERFORMANCE_MODES
        
        self.logger.info("UHI Analysis Backend initialized")
        
    def _setup_logging(self, level: str) -> logging.Logger:
        """Configure logging for the backend with console output."""
        logger = logging.getLogger("uhi_backend")
        logger.setLevel(getattr(logging, level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _convert_to_json_serializable(self, obj: Any) -> Any:
        """Convert NumPy/Pandas types to JSON-serializable Python types."""
        # Handle numpy numeric types (NumPy 2.0 compatible)
        if isinstance(obj, (np.integer, np.int8, np.int16, np.int32, np.int64)):
            return int(obj)
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
        Execute comprehensive Urban Heat Island analysis.
        
        Performs complete UHI analysis workflow including data acquisition,
        processing, analysis execution, and result formatting. Handles all
        aspects of the analysis pipeline with comprehensive error handling.
        
        Args:
            area: Target area name (Berlin district, locality, or "Berlin")
            start_date: Analysis start date in YYYY-MM-DD format
            end_date: Analysis end date in YYYY-MM-DD format
            performance_mode: Analysis performance mode (preview/fast/standard/detailed)
            
        Returns:
            Comprehensive analysis results with the following structure:
            - status: Analysis completion status (completed/error/in_progress)
            - progress: Completion percentage (0-100)
            - metadata: Analysis configuration and performance metrics
            - data: Structured analysis results (temperature, hotspots, correlations, etc.)
            - errors: List of error messages if analysis failed
            - warnings: List of warning messages
            - execution_time: Total analysis duration in seconds
            
        Raises:
            ValueError: If invalid performance mode is specified
        """
        start_time = time.time()
        
        self.logger.info(f"🔥 Starting UHI Analysis for {area}")
        self.logger.info(f"   Period: {start_date} to {end_date}")
        self.logger.info(f"   Performance mode: {performance_mode}")
        
        # Validate performance mode
        if performance_mode not in UHI_PERFORMANCE_MODES:
            raise ValueError(f"Invalid performance mode: {performance_mode}. "
                           f"Available modes: {list(UHI_PERFORMANCE_MODES.keys())}")
        
        mode_config = UHI_PERFORMANCE_MODES[performance_mode]
        include_weather = mode_config.get('include_weather', False)

        # Initialize structured result container
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
            # Step 1: Parse and validate input parameters
            self.logger.info("📋 Step 1/6: Parsing and validating inputs...")
            start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            if start_date_parsed >= end_date_parsed:
                raise ValueError("Start date must be before end date")
            
            result["progress"] = 10
            
            # Step 2: Download geographical boundary data
            self.logger.info("🗺️ Step 2/6: Acquiring boundary data...")
            boundary_data = self._download_boundary_data(area)
            result["progress"] = 25
            
            if boundary_data is None or boundary_data.empty:
                result["status"] = "error"
                result["errors"].append(f"No boundary data found for area '{area}'")
                result["execution_time"] = time.time() - start_time
                return self._convert_to_json_serializable(result)
            
            # Step 3: Download CORINE Land Cover data
            self.logger.info("🌱 Step 3/6: Acquiring land cover data...")
            landcover_data = self._download_landcover_data(boundary_data, start_date_parsed, end_date_parsed)
            result["progress"] = 40
            
            if landcover_data is None or landcover_data.empty:
                result["status"] = "error"
                result["errors"].append("Failed to acquire land cover data for the specified area and period")
                result["execution_time"] = time.time() - start_time
                return self._convert_to_json_serializable(result)
            
            # Step 4: Download weather data (optional based on performance mode)
            weather_stations = None
            weather_stations_interpolated = None
            if include_weather:
                self.logger.info("🌤️ Step 4/6: Acquiring weather station data...")
                weather_stations, weather_stations_interpolated = self._download_weather_data(
                    boundary_data, start_date_parsed, end_date_parsed
                )
                if weather_stations is None:
                    result["warnings"].append("Weather station data unavailable, continuing without ground validation")
            
            # Step 5: Configure analysis engine
            self.logger.info("⚙️ Step 5/6: Configuring analysis engine...")
            analyzer = self._create_analyzer(performance_mode)
            result["progress"] = 60
            
            # Step 6: Execute UHI analysis
            self.logger.info("🔥 Step 6/6: Executing heat island analysis...")
            analysis_results = analyzer.analyze_heat_islands(
                city_boundary=boundary_data,
                date_range=(start_date_parsed, end_date_parsed),
                landuse_data=landcover_data,
                weather_stations=weather_stations_interpolated
            )
            result["progress"] = 80
            
            # Attach raw data for result processing
            analysis_results["raw_weather_stations"] = weather_stations
            analysis_results["boundary_data"] = boundary_data
            analysis_results["raw_landcover_data"] = landcover_data
            
            # Process and structure analysis results
            self.logger.info("📊 Processing and formatting results...")
            result["data"] = self._process_analysis_results(analysis_results)
            result["progress"] = 100
            result["status"] = "completed"
            
            # Add performance metrics and timing
            execution_time = time.time() - start_time
            result["execution_time"] = round(execution_time, 2)
            result["metadata"]["performance_metrics"] = self._get_performance_metrics(
                analysis_results, execution_time, performance_mode
            )
            
            self.logger.info(f"✅ Analysis completed successfully in {execution_time:.1f}s")
            
        except Exception as e:
            self.logger.error(f"❌ Analysis execution failed: {str(e)}")
            result["status"] = "error"
            result["errors"].append(f"Analysis execution failed: {str(e)}")
            result["execution_time"] = time.time() - start_time
        
        return self._convert_to_json_serializable(result)
    
    def _get_boundary_type(self, area: str) -> str:
        """Determine appropriate boundary type based on area name."""
        area_lower = area.lower()
        
        # Berlin administrative districts
        berlin_districts = [
            'charlottenburg-wilmersdorf', 'friedrichshain-kreuzberg', 'lichtenberg',
            'marzahn-hellersdorf', 'mitte', 'neukölln', 'pankow', 'reinickendorf',
            'spandau', 'steglitz-zehlendorf', 'tempelhof-schöneberg', 'treptow-köpenick'
        ]
        
        if any(district in area_lower for district in berlin_districts):
            return "district_boundary"
        elif area_lower in ['berlin']:
            return "state_boundary"
        else:
            return "locality_boundary"

    def _download_boundary_data(self, area: str) -> Optional[gpd.GeoDataFrame]:
        """Download geographical boundary data for the specified area."""
        try:
            boundary_type = self._get_boundary_type(area)
            
            endpoint_url = BERLIN_WFS_ENDPOINTS[boundary_type]
            feature_type = BERLIN_WFS_FEATURE_TYPES[boundary_type]
            target_crs = CRS_CONFIG["OUTPUT"]
            
            wfs_downloader = WFSDataDownloader(endpoint_url=endpoint_url, verbose=False)
            
            boundaries_gdf = wfs_downloader.download_to_geodataframe(
                type_name=feature_type,
                target_crs=target_crs
            )
            
            if boundaries_gdf.empty:
                self.logger.error(f"No {boundary_type} data available")
                return None
            
            # Determine appropriate name column based on boundary type
            name_column_mapping = {
                "state_boundary": "namlan",
                "district_boundary": "namgem", 
                "locality_boundary": "nam"
            }
            
            name_column = name_column_mapping.get(boundary_type)
            
            if not name_column or name_column not in boundaries_gdf.columns:
                self.logger.error(f"Expected name column '{name_column}' not found in {boundary_type}")
                return None
            
            # Filter for the specific area (case-insensitive)
            area_mask = boundaries_gdf[name_column].str.contains(area, case=False, na=False)
            area_gdf = boundaries_gdf[area_mask]
            
            if len(area_gdf) == 0:
                available_areas = boundaries_gdf[name_column].tolist()
                self.logger.error(f"Area '{area}' not found. Available areas: {available_areas}")
                return None
            
            if len(area_gdf) > 1:
                selected_area = area_gdf[name_column].iloc[0]
                self.logger.warning(f"Multiple matches for '{area}', using: {selected_area}")
                area_gdf = area_gdf.iloc[[0]]
            
            self.logger.info(f"Successfully acquired boundary data for '{area}'")
            return area_gdf
            
        except Exception as e:
            self.logger.error(f"Boundary data acquisition failed: {e}")
            return None
    
    def _download_landcover_data(self, boundary_data: gpd.GeoDataFrame, 
                               start_date: date, end_date: date) -> Optional[gpd.GeoDataFrame]:
        """Download CORINE Land Cover data for the boundary area."""
        try:
            # Convert dates for CORINE downloader compatibility
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            corine_downloader = CorineDataDownloader(
                year_or_period=(start_datetime, end_datetime),
                verbose=False
            )
            
            landcover_gdf = corine_downloader.download_for_area(
                boundary_data, 
                target_crs=CRS_CONFIG["OUTPUT"]
            )
            
            if landcover_gdf.empty:
                self.logger.error("No land cover data available for the specified area and period")
                return None
            
            self.logger.info(f"Successfully acquired {len(landcover_gdf)} land cover features")
            return landcover_gdf
            
        except Exception as e:
            self.logger.error(f"Land cover data acquisition failed: {e}")
            return None
    
    def _download_weather_data(self, boundary_data: gpd.GeoDataFrame, 
                             start_date: date, end_date: date) -> tuple:
        """Download weather station data for ground validation."""
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            dwd_downloader = DWDDataDownloader(
                verbose=False,
                interpolate_by_default=True
            )
            
            weather_result = dwd_downloader.download_for_area(
                geometry=boundary_data,
                start_date=start_datetime,
                end_date=end_datetime
            )
            
            if isinstance(weather_result, tuple):
                weather_stations, weather_interpolated = weather_result
            else:
                weather_stations = weather_result
                weather_interpolated = None
            
            if weather_stations is None or weather_stations.empty:
                self.logger.warning("No weather station data available for the specified area and period")
                return None, None
            
            self.logger.info(f"Successfully acquired {len(weather_stations)} weather station records")
            return weather_stations, weather_interpolated
            
        except Exception as e:
            self.logger.error(f"Weather data acquisition failed: {e}")
            return None, None
    
    def _create_analyzer(self, performance_mode: str) -> UrbanHeatIslandAnalyzer:
        """Create and configure UHI analyzer based on performance mode."""
        mode_config = UHI_PERFORMANCE_MODES[performance_mode]
        
        analyzer_kwargs = {
            'cloud_cover_threshold': mode_config.get('cloud_cover_threshold', 20),
            'grid_cell_size': mode_config.get('grid_cell_size', 100),
            'hotspot_threshold': mode_config.get('hotspot_threshold', 0.9),
            'min_cluster_size': mode_config.get('min_cluster_size', 5),
        }
        
        analyzer = UrbanHeatIslandAnalyzer(**analyzer_kwargs)
        
        self.logger.info(f"🚀 Created analyzer with {performance_mode} mode configuration")
        return analyzer
    
    def _process_analysis_results(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process and structure analysis results for API consumption."""
        processed = {
            "summary": {},
            "temperature_data": {},
            "hotspots": {},
            "landuse_correlation": {},
            "weather_stations": {},
            "recommendations": {},
            "landuse_data": {},
            "boundary": {}
        }
        
        # Process temperature analysis
        self._process_temperature_data(analysis_results, processed)
        
        # Process heat island hotspots
        self._process_hotspots_data(analysis_results, processed)
        
        # Process land use correlation analysis
        self._process_landuse_correlation(analysis_results, processed)
        
        # Process weather station validation data
        self._process_weather_stations(analysis_results, processed)
        
        # Process mitigation recommendations
        self._process_recommendations(analysis_results, processed)
        
        # Process geospatial boundary data
        self._process_boundary_data(analysis_results, processed)
        
        # Process land cover visualization data
        self._process_landcover_data(analysis_results, processed)
        
        # Generate analysis summary
        processed["summary"] = self._generate_analysis_summary(processed)
        
        return processed
    
    def _process_temperature_data(self, analysis_results: Dict[str, Any], processed: Dict[str, Any]) -> None:
        """Process temperature statistics and grid data."""
        if "temperature_statistics" not in analysis_results:
            return
            
        temp_stats = analysis_results["temperature_statistics"]
        if temp_stats is None or 'temperature' not in temp_stats.columns:
            return
            
        valid_temps = temp_stats['temperature'].dropna()
        
        if len(valid_temps) == 0:
            return
        
        processed["temperature_data"] = {
            "grid_cells_total": len(temp_stats),
            "grid_cells_valid": len(valid_temps),
            "statistics": {
                "mean": round(valid_temps.mean(), 2),
                "std": round(valid_temps.std(), 2),
                "min": round(valid_temps.min(), 2),
                "max": round(valid_temps.max(), 2),
                "percentiles": {
                    "p25": round(valid_temps.quantile(0.25), 2),
                    "p50": round(valid_temps.quantile(0.50), 2),
                    "p75": round(valid_temps.quantile(0.75), 2),
                    "p90": round(valid_temps.quantile(0.90), 2)
                }
            },
            "geojson": json.loads(temp_stats.to_json())
        }
    
    def _process_hotspots_data(self, analysis_results: Dict[str, Any], processed: Dict[str, Any]) -> None:
        """Process heat island hotspots identification results."""
        if "hot_spots" not in analysis_results:
            return
            
        hotspots = analysis_results["hot_spots"]
        if hotspots is None or len(hotspots) == 0:
            return
            
        temp_data = {}
        if 'temperature' in hotspots.columns:
            temp_data = {
                "min": round(hotspots['temperature'].min(), 2),
                "max": round(hotspots['temperature'].max(), 2)
            }
        
        processed["hotspots"] = {
            "count": len(hotspots),
            "temperature_range": temp_data,
            "geojson": json.loads(hotspots.to_json())
        }
    
    def _process_landuse_correlation(self, analysis_results: Dict[str, Any], processed: Dict[str, Any]) -> None:
        """Process land use correlation analysis results."""
        if "land_use_correlation" not in analysis_results:
            return
            
        landuse = analysis_results["land_use_correlation"]
        if not landuse:
            return
            
        processed["landuse_correlation"] = {
            "statistics": landuse.get("statistics", {}),
            "correlations": landuse.get("correlations", {}),
            "category_descriptions": landuse.get("category_descriptions", {}),
            "analysis_type": landuse.get("analysis_type", "grouped"),
            "summary": landuse.get("summary", {})
        }
    
    def _process_weather_stations(self, analysis_results: Dict[str, Any], processed: Dict[str, Any]) -> None:
        """Process weather station validation data."""
        weather_data = analysis_results.get("raw_weather_stations")
        
        if weather_data is None or weather_data.empty:
            # Try alternative source
            ground_validation = analysis_results.get("ground_validation", {})
            weather_data = ground_validation.get("station_data")
        
        if weather_data is None or weather_data.empty:
            return
        
        try:
            weather_copy = weather_data.copy()
            
            # Convert datetime columns for JSON serialization
            for col in weather_copy.columns:
                if weather_copy[col].dtype == 'datetime64[ns]':
                    weather_copy[col] = weather_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                elif str(weather_copy[col].dtype).startswith('datetime'):
                    weather_copy[col] = weather_copy[col].astype(str)
            
            temp_range = {}
            if 'ground_temp' in weather_copy.columns:
                temp_range = {
                    "min": round(weather_copy['ground_temp'].min(), 2),
                    "max": round(weather_copy['ground_temp'].max(), 2)
                }
            
            processed["weather_stations"] = {
                "count": len(weather_copy),
                "temperature_range": temp_range,
                "geojson": json.loads(weather_copy.to_json())
            }
            
        except Exception as e:
            self.logger.warning(f"Weather station data processing failed: {e}")
    
    def _process_recommendations(self, analysis_results: Dict[str, Any], processed: Dict[str, Any]) -> None:
        """Process mitigation recommendations."""
        if "mitigation_recommendations" not in analysis_results:
            return
            
        recommendations = analysis_results["mitigation_recommendations"]
        if not recommendations:
            return
            
        if isinstance(recommendations, list):
            processed["recommendations"] = {
                "strategies": recommendations,
                "total_count": len(recommendations)
            }
        else:
            processed["recommendations"] = recommendations
    
    def _process_boundary_data(self, analysis_results: Dict[str, Any], processed: Dict[str, Any]) -> None:
        """Process geographical boundary data."""
        if "boundary_data" not in analysis_results:
            return
            
        boundary_data = analysis_results["boundary_data"]
        if boundary_data is None:
            return
            
        try:
            processed["boundary"] = json.loads(boundary_data.to_json())
        except Exception as e:
            self.logger.warning(f"Boundary data processing failed: {e}")
    
    def _process_landcover_data(self, analysis_results: Dict[str, Any], processed: Dict[str, Any]) -> None:
        """Process land cover data for visualization."""
        landcover_data = analysis_results.get("raw_landcover_data")
        boundary_data = analysis_results.get("boundary_data")
        
        if landcover_data is None or landcover_data.empty:
            return
        
        try:
            landcover_copy = landcover_data.copy()
            
            # Clip to boundary area if available
            if boundary_data is not None and not boundary_data.empty:
                landcover_copy = gpd.overlay(landcover_copy, boundary_data, how='intersection')
            
            if landcover_copy.empty:
                return
            
            # Process using standardized CORINE classification
            landcover_copy = self._standardize_landcover_data(landcover_copy)
            
            processed["landuse_data"] = {
                "geojson": json.loads(landcover_copy.to_json())
            }
            
        except Exception as e:
            self.logger.warning(f"Land cover data processing failed: {e}")
    
    def _standardize_landcover_data(self, landcover_data: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Standardize land cover data using CORINE classification system."""
        # Find CORINE code column
        code_columns = ['Code_18', 'CODE_18', 'corine_code', 'Code_12', 'CODE_12', 
                       'Code_06', 'CODE_06', 'CODE_00', 'CODE_90', 'gridcode', 'GRIDCODE']
        
        code_column = None
        for col in code_columns:
            if col in landcover_data.columns:
                code_column = col
                break
        
        if code_column:
            landcover_data['corine_code'] = landcover_data[code_column].astype(int)
            
            try:
                # Process using unified classification system
                landcover_data = process_corine_for_uhi(landcover_data, logger=self.logger)
                
                # Ensure frontend compatibility
                if 'impervious_area' in landcover_data.columns:
                    landcover_data['impervious_coefficient'] = landcover_data['impervious_area']
                if 'landuse_type' in landcover_data.columns:
                    landcover_data['land_use_type'] = landcover_data['landuse_type']
                    
            except Exception as e:
                self.logger.warning(f"CORINE processing failed: {e}")
                # Apply fallback values
                self._apply_fallback_landcover_values(landcover_data)
        else:
            self.logger.warning("No CORINE code column found, using fallback values")
            self._apply_fallback_landcover_values(landcover_data)
        
        return landcover_data
    
    def _apply_fallback_landcover_values(self, landcover_data: gpd.GeoDataFrame) -> None:
        """Apply fallback values when CORINE processing fails."""
        landcover_data['land_use_type'] = 'unknown'
        landcover_data['impervious_coefficient'] = 0.3
        landcover_data['land_use_description'] = 'Unknown Land Use'
    
    def _generate_analysis_summary(self, processed: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive analysis summary."""
        summary = {
            "analysis_type": "Urban Heat Island Analysis",
            "temperature_overview": processed["temperature_data"].get("statistics", {}),
            "hotspots_count": processed["hotspots"].get("count", 0),
        }
        
        # Extract correlation strength
        correlation_data = processed["landuse_correlation"].get("correlations", {})
        overall_correlation = correlation_data.get("overall", {})
        summary["correlation_strength"] = overall_correlation.get("correlation", 0)
        
        # Extract recommendation count
        recommendations = processed["recommendations"]
        if isinstance(recommendations, dict):
            summary["recommendations_count"] = len(recommendations.get("strategies", []))
        elif isinstance(recommendations, list):
            summary["recommendations_count"] = len(recommendations)
        else:
            summary["recommendations_count"] = 0
        
        return summary
    
    def _get_performance_metrics(self, analysis_results: Dict[str, Any], 
                               execution_time: float, performance_mode: str) -> Dict[str, Any]:
        """Generate performance metrics for analysis assessment."""
        temp_stats = analysis_results.get("temperature_statistics")
        
        return {
            "execution_time_seconds": execution_time,
            "performance_mode": performance_mode,
            "grid_cells_processed": len(temp_stats) if temp_stats is not None else 0,
            "data_sources": {
                "satellite_data": True,
                "weather_stations": performance_mode in ["detailed", "standard"],
                "land_cover": True
            }
        }