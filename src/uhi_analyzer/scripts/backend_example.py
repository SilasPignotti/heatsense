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
from datetime import date, datetime
from typing import Dict, Any, Optional, List
import geopandas as gpd

from uhi_analyzer.data.wfs_downloader import WFSDataDownloader
from uhi_analyzer.data.corine_downloader import CorineDataDownloader
from uhi_analyzer.data.dwd_downloader import DWDDataDownloader
from uhi_analyzer.data.urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
from uhi_analyzer.config.settings import (
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
        
        if performance_mode in ["detailed", "standard"]:
            include_weather = True
        else:
            include_weather = False

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
            
            # Process results
            self.logger.info("📊 Processing results...")
            result["data"] = self._process_analysis_results(analysis_results)
            result["progress"] = 100
            result["status"] = "completed"
            
            # Add performance metrics
            execution_time = time.time() - start_time
            result["execution_time"] = round(execution_time, 2)
            result["metadata"]["performance_metrics"] = self._get_performance_metrics(
                analysis_results, execution_time, performance_mode
            )
            
            self.logger.info(f"✅ Analysis completed in {execution_time:.1f}s")
            
        except Exception as e:
            self.logger.error(f"❌ Analysis failed: {str(e)}")
            result["status"] = "error"
            result["errors"].append(f"Analysis failed: {str(e)}")
            result["execution_time"] = time.time() - start_time
        
        
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
            
            # Find matching areas (try different column names)
            name_columns = ['namlan', 'namgem', 'nam']
            matching_column = None
            
            for col in name_columns:
                if col in boundaries_gdf.columns:
                    matching_column = col
                    break
            
            if not matching_column:
                self.logger.warning(f"Could not find name column in {boundary_type}, using all boundaries")
                return boundaries_gdf
            
            # Filter for the specific area
            area_mask = boundaries_gdf[matching_column].str.contains(area, case=False, na=False)
            area_gdf = boundaries_gdf[area_mask]
            
            if len(area_gdf) == 0:
                self.logger.warning(f"Area '{area}' not found in {boundary_type}, using all boundaries")
                return boundaries_gdf
            
            self.logger.info(f"Found {len(area_gdf)} boundaries matching '{area}' in {boundary_type}")
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
                               end_date: date, interpolate: bool = True) -> Optional[gpd.GeoDataFrame]:
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
            weather_gdf = dwd_downloader.download_for_area(
                geometry=boundary_data,
                start_date=start_datetime,
                end_date=end_datetime
            )
            
            if weather_gdf.empty:
                self.logger.warning("No weather station data downloaded")
                return None
            
            self.logger.info(f"Downloaded {len(weather_gdf)} weather station records")
            return weather_gdf
            
        except Exception as e:
            self.logger.error(f"Error downloading weather data: {e}")
            return None
    
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
            'skip_temporal_trends': mode_config.get('skip_temporal_trends', False),
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
            "visualizations": {}
        }
        
        # Process temperature statistics
        if "temperature_statistics" in analysis_results:
            temp_stats = analysis_results["temperature_statistics"]
            if temp_stats is not None and 'temperature' in temp_stats.columns:
                valid_temps = temp_stats['temperature'].dropna()
                
                processed["temperature_data"] = {
                    "grid_cells_total": len(temp_stats),
                    "grid_cells_valid": len(valid_temps),
                    "statistics": {
                        "mean": round(valid_temps.mean(), 2) if len(valid_temps) > 0 else None,
                        "std": round(valid_temps.std(), 2) if len(valid_temps) > 0 else None,
                        "min": round(valid_temps.min(), 2) if len(valid_temps) > 0 else None,
                        "max": round(valid_temps.max(), 2) if len(valid_temps) > 0 else None,
                        "percentiles": {
                            "p25": round(valid_temps.quantile(0.25), 2) if len(valid_temps) > 0 else None,
                            "p50": round(valid_temps.quantile(0.50), 2) if len(valid_temps) > 0 else None,
                            "p75": round(valid_temps.quantile(0.75), 2) if len(valid_temps) > 0 else None,
                            "p90": round(valid_temps.quantile(0.90), 2) if len(valid_temps) > 0 else None
                        }
                    },
                    "geojson": json.loads(temp_stats.to_json())
                }
        
        # Process hotspots
        if "hot_spots" in analysis_results:
            hotspots = analysis_results["hot_spots"]
            if hotspots is not None and len(hotspots) > 0:
                processed["hotspots"] = {
                    "count": len(hotspots),
                    "temperature_range": {
                        "min": round(hotspots['temperature'].min(), 2) if 'temperature' in hotspots.columns else None,
                        "max": round(hotspots['temperature'].max(), 2) if 'temperature' in hotspots.columns else None
                    },
                    "geojson": json.loads(hotspots.to_json())
                }
        
        # Process land use correlations with updated structure
        if "land_use_correlation" in analysis_results:
            landuse = analysis_results["land_use_correlation"]
            if landuse:
                processed["landuse_correlation"] = {
                    "statistics": landuse.get("statistics", {}),
                    "correlations": landuse.get("correlations", {}),
                    "category_descriptions": landuse.get("category_descriptions", {}),
                    "analysis_type": landuse.get("analysis_type", "grouped"),
                    "summary": landuse.get("summary", {})
                }
                        
        # Process weather station data (from raw data if available)
        if "raw_weather_stations" in analysis_results and analysis_results["raw_weather_stations"] is not None:
            weather_stations = analysis_results["raw_weather_stations"]
            try:
                processed["weather_stations"] = {
                    "count": len(weather_stations),
                    "temperature_range": {
                        "min": round(weather_stations['ground_temp'].min(), 2) if 'ground_temp' in weather_stations.columns else None,
                        "max": round(weather_stations['ground_temp'].max(), 2) if 'ground_temp' in weather_stations.columns else None
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
                        "count": len(station_data),
                        "temperature_range": {
                            "min": round(station_data['ground_temp'].min(), 2) if 'ground_temp' in station_data.columns else None,
                            "max": round(station_data['ground_temp'].max(), 2) if 'ground_temp' in station_data.columns else None
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
        
        # Create summary
        processed["summary"] = {
            "analysis_type": "Urban Heat Island Analysis",
            "temperature_overview": processed["temperature_data"].get("statistics", {}),
            "hotspots_count": processed["hotspots"].get("count", 0),
            "correlation_strength": processed["landuse_correlation"].get("correlations", {}).get("overall", {}).get("correlation", 0),
            "recommendations_count": (
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
            "execution_time_seconds": execution_time,
            "performance_mode": performance_mode,
            "analyzer_type": metadata.get("performance_mode", "unknown"),
            "grid_cells_processed": len(temp_stats) if temp_stats is not None else 0,
            "data_sources": {
                "satellite_data": True,
                "weather_stations": used_weather_stations,
                "land_cover": True
            }
        }


def main():
    """Simple test function for UHI Analysis Backend development."""
    print("🔥 UHI Analysis Backend - Development Mode")
    print("="*50)
    
    # Predefined test inputs for frontend development
    test_scenarios = [
        {
            "name": "Kreuzberg Summer Analysis",
            "area": "Kreuzberg",
            "start_date": "2023-07-01",
            "end_date": "2023-07-31",
            "performance_mode": "fast"
        },
        {
            "name": "Mitte Quick Preview",
            "area": "Mitte", 
            "start_date": "2023-07-15",
            "end_date": "2023-07-20",
            "performance_mode": "preview"
        },
        {
            "name": "Berlin District Analysis",
            "area": "Charlottenburg-Wilmersdorf",
            "start_date": "2023-06-01", 
            "end_date": "2023-08-31",
            "performance_mode": "standard"
        }
    ]
    
    # Run the first scenario by default
    selected_scenario = test_scenarios[0]
    
    print(f"Running: {selected_scenario['name']}")
    print(f"Area: {selected_scenario['area']}")
    print(f"Period: {selected_scenario['start_date']} to {selected_scenario['end_date']}")
    print(f"Mode: {selected_scenario['performance_mode']}")
    print("-" * 50)
    
    # Initialize backend
    backend = UHIAnalysisBackend(log_level="INFO")
    
    # Run analysis
    result = backend.analyze(
        area=selected_scenario["area"],
        start_date=selected_scenario["start_date"],
        end_date=selected_scenario["end_date"],
        performance_mode=selected_scenario["performance_mode"]
    )
    
    # Print summary
    print("\n" + "="*60)
    print("🔥 UHI ANALYSIS RESULTS")
    print("="*60)
    
    if result["status"] == "completed":
        summary = result["data"]["summary"]
        print(f"✅ Status: {result['status'].upper()}")
        print(f"⏱️  Execution time: {result['execution_time']:.1f}s")
        print(f"🌡️  Mean temperature: {summary['temperature_overview'].get('mean', 'N/A')}°C")
        print(f"🔥 Hotspots found: {summary['hotspots_count']}")
        print(f"📊 Correlation strength: {summary['correlation_strength']:.3f}")
        print(f"💡 Recommendations: {summary['recommendations_count']}")
    else:
        print(f"❌ Status: {result['status'].upper()}")
        for error in result["errors"]:
            print(f"   Error: {error}")
    
    print(f"\n📋 Full JSON result has {len(str(result))} characters")
    
    # Save result for frontend development
    output_file = "backend_test_result.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"📄 Results saved to: {output_file}")
    
    return result


if __name__ == "__main__":
    main() 