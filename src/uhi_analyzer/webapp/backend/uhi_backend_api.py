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

import argparse
import json
import logging
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile
import uuid

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from uhi_analyzer.data.wfs_downloader import WFSDataDownloader
from uhi_analyzer.data.corine_downloader import CorineDataDownloader
from uhi_analyzer.utils import create_analyzer, get_analyzer_recommendation, list_performance_modes
from uhi_analyzer.config.settings import (
    UHI_PERFORMANCE_MODES, 
    CORINE_GROUPED_DESCRIPTIONS,
    UHI_CACHE_DIR
)


class UHIAnalysisBackend:
    """
    Backend class for Urban Heat Island analysis.
    
    Provides a clean API for performing UHI analysis with various options
    and returns structured results suitable for web applications.
    """
    
    def __init__(self, cache_enabled: bool = True, cache_dir: str = None, 
                 max_cache_age_days: int = 30, log_level: str = "INFO"):
        """
        Initialize the UHI Analysis Backend.
        
        Args:
            cache_enabled: Whether to enable caching for faster repeat analyses
            cache_dir: Directory for cache files
            max_cache_age_days: Maximum age for cached items in days
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.cache_enabled = cache_enabled
        self.cache_dir = cache_dir or str(UHI_CACHE_DIR)
        self.max_cache_age_days = max_cache_age_days
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
    
    def validate_inputs(self, area: str, start_date: str, end_date: str, 
                       performance_mode: str = "standard") -> Dict[str, Any]:
        """
        Validate user inputs and return validation result.
        
        Args:
            area: Area name (Berlin suburb/locality)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            performance_mode: Performance mode (preview, fast, standard, detailed)
            
        Returns:
            Dict with validation results and parsed values
        """
        result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "parsed_values": {}
        }
        
        # Validate area
        if not area or len(area.strip()) < 2:
            result["errors"].append("Area name must be at least 2 characters")
        else:
            result["parsed_values"]["area"] = area.strip()
        
        # Validate dates
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            if start > end:
                result["errors"].append("Start date must be before or equal to end date")
            elif start.year < 1990:
                result["errors"].append("Start date must be after 1990 (satellite data availability)")
            elif end > date.today():
                result["errors"].append("End date cannot be in the future")
            else:
                result["parsed_values"]["start_date"] = start
                result["parsed_values"]["end_date"] = end
                
                # Check date range length
                date_diff = (end - start).days
                if date_diff > 365:
                    result["warnings"].append(f"Long date range ({date_diff} days) may increase processing time")
                elif date_diff < 7:
                    result["warnings"].append(f"Short date range ({date_diff} days) may limit satellite data availability")
                    
        except ValueError:
            result["errors"].append("Invalid date format. Use YYYY-MM-DD")
        
        # Validate performance mode
        if performance_mode not in self.performance_modes:
            result["errors"].append(f"Invalid performance mode. Choose from: {list(self.performance_modes.keys())}")
        else:
            result["parsed_values"]["performance_mode"] = performance_mode
        
        result["valid"] = len(result["errors"]) == 0
        return result
    
    def get_performance_modes(self) -> Dict[str, Dict[str, Any]]:
        """
        Get available performance modes with descriptions.
        
        Returns:
            Dict of performance modes with their settings and descriptions
        """
        # Use the new utility function for consistent mode information
        modes_info = list_performance_modes()
        
        # Add backend-specific information
        modes = {}
        for mode_name, info in modes_info.items():
            modes[mode_name] = {
                "settings": self.performance_modes[mode_name],
                "grid_size_m": info["grid_size_m"],
                "uses_fast_analyzer": info["uses_fast_analyzer"],
                "skips_temporal": info["skips_temporal"],
                "description": self._get_mode_description(mode_name),
                "recommended_for": info["recommended_for"]
            }
        return modes
    
    def _get_mode_description(self, mode: str) -> str:
        """Get description for performance mode."""
        descriptions = {
            "preview": "Fast preview with lower resolution - ideal for quick exploration",
            "fast": "Balanced speed and quality - good for interactive applications",
            "standard": "Standard quality analysis - recommended for most use cases",
            "detailed": "High-quality detailed analysis - best for scientific studies"
        }
        return descriptions.get(mode, "Standard analysis mode")
    
    def _get_mode_use_cases(self, mode: str) -> List[str]:
        """Get recommended use cases for performance mode."""
        use_cases = {
            "preview": ["webapp initial load", "area exploration", "parameter testing"],
            "fast": ["interactive analysis", "real-time updates", "mobile applications"],
            "standard": ["urban planning", "research projects", "detailed reporting"],
            "detailed": ["scientific publications", "high-precision studies", "policy making"]
        }
        return use_cases.get(mode, ["general analysis"])
    
    def get_recommended_mode(self, area_km2: float) -> str:
        """
        Get recommended performance mode based on analysis area size.
        
        Args:
            area_km2: Analysis area in square kilometers
            
        Returns:
            Recommended performance mode
        """
        return get_analyzer_recommendation(area_km2)
    
    def analyze(self, area: str, start_date: str, end_date: str, 
                performance_mode: str = "standard", 
                include_weather: bool = False,
                cloud_threshold: Optional[int] = None,
                output_formats: List[str] = None) -> Dict[str, Any]:
        """
        Perform UHI analysis with given parameters.
        
        Args:
            area: Area name (Berlin suburb/locality)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            performance_mode: Performance mode (preview, fast, standard, detailed)
            include_weather: Whether to include weather station data
            cloud_threshold: Cloud cover threshold (0-100), None for mode default
            output_formats: List of output formats ["json", "geojson", "png"]
            
        Returns:
            Dict with analysis results, metadata, and status
        """
        analysis_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        self.logger.info(f"🔥 Starting UHI Analysis {analysis_id}")
        self.logger.info(f"   Area: {area}")
        self.logger.info(f"   Period: {start_date} to {end_date}")
        self.logger.info(f"   Mode: {performance_mode}")
        
        # Initialize result structure
        result = {
            "analysis_id": analysis_id,
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
            # Step 1: Validate inputs
            self.logger.info("📋 Step 1/6: Validating inputs...")
            validation = self.validate_inputs(area, start_date, end_date, performance_mode)
            result["progress"] = 10
            
            if not validation["valid"]:
                result["status"] = "error"
                result["errors"] = validation["errors"]
                result["execution_time"] = time.time() - start_time
                return result
            
            if validation["warnings"]:
                result["warnings"].extend(validation["warnings"])
            
            parsed = validation["parsed_values"]
            
            # Step 2: Download boundary data
            self.logger.info("🗺️  Step 2/6: Downloading boundary data...")
            boundary_file = self._download_boundary_data(parsed["area"], analysis_id)
            result["progress"] = 25
            
            if not boundary_file:
                result["status"] = "error"
                result["errors"].append("Failed to download boundary data")
                result["execution_time"] = time.time() - start_time
                return result
            
            # Step 3: Download land cover data
            self.logger.info("🌱 Step 3/6: Downloading land cover data...")
            landcover_file = self._download_landcover_data(
                boundary_file, parsed["start_date"], parsed["end_date"], analysis_id
            )
            result["progress"] = 40
            
            if not landcover_file:
                result["status"] = "error"
                result["errors"].append("Failed to download land cover data")
                result["execution_time"] = time.time() - start_time
                return result
            
            # Step 4: Configure analyzer
            self.logger.info("⚙️  Step 4/6: Configuring analyzer...")
            analyzer = self._create_analyzer(performance_mode, cloud_threshold)
            result["progress"] = 50
            
            # Step 5: Run analysis
            self.logger.info("🔥 Step 5/6: Running UHI analysis...")
            analysis_results = analyzer.analyze_heat_islands(
                city_boundary=str(boundary_file),
                date_range=(parsed["start_date"], parsed["end_date"]),
                landuse_data=str(landcover_file),
                save_intermediate=False
            )
            result["progress"] = 80
            
            # Step 6: Process results
            self.logger.info("📊 Step 6/6: Processing results...")
            result["data"] = self._process_analysis_results(analysis_results, output_formats or ["json"])
            result["progress"] = 100
            result["status"] = "completed"
            
            # Add performance metrics
            execution_time = time.time() - start_time
            result["execution_time"] = round(execution_time, 2)
            result["metadata"]["performance_metrics"] = self._get_performance_metrics(
                analysis_results, execution_time, performance_mode
            )
            
            self.logger.info(f"✅ Analysis {analysis_id} completed in {execution_time:.1f}s")
            
        except Exception as e:
            self.logger.error(f"❌ Analysis {analysis_id} failed: {str(e)}")
            result["status"] = "error"
            result["errors"].append(f"Analysis failed: {str(e)}")
            result["execution_time"] = time.time() - start_time
        
        finally:
            # Cleanup temporary files
            self._cleanup_temp_files(analysis_id)
        
        return result
    
    def _download_boundary_data(self, area: str, analysis_id: str) -> Optional[Path]:
        """Download boundary data for the specified area."""
        try:
            temp_dir = Path(tempfile.gettempdir()) / f"uhi_analysis_{analysis_id}"
            temp_dir.mkdir(exist_ok=True)
            
            # Download Berlin localities
            wfs_downloader = WFSDataDownloader()
            
            # Download all localities
            all_localities_file = temp_dir / "berlin_localities.geojson"
            success = wfs_downloader.download_and_save(
                endpoint_name="berlin_locality_boundary",
                output_path=all_localities_file,
                output_format="geojson"
            )
            
            if not success:
                return None
            
            # Filter for specific area
            import geopandas as gpd
            localities_gdf = gpd.read_file(all_localities_file)
            
            # Find matching localities (try different column names)
            name_columns = ['nam', 'name', 'NAME', 'bezeich', 'ortsteil', 'ORTSTEIL']
            matching_column = None
            
            for col in name_columns:
                if col in localities_gdf.columns:
                    matching_column = col
                    break
            
            if not matching_column:
                self.logger.warning("Could not find name column, using all localities")
                return all_localities_file
            
            # Filter for the specific area
            area_mask = localities_gdf[matching_column].str.contains(area, case=False, na=False)
            area_gdf = localities_gdf[area_mask]
            
            if len(area_gdf) == 0:
                self.logger.warning(f"Area '{area}' not found, using all localities")
                return all_localities_file
            
            # Save filtered boundary
            boundary_file = temp_dir / f"{area.lower().replace(' ', '_')}_boundary.geojson"
            area_gdf.to_file(boundary_file, driver="GeoJSON")
            
            return boundary_file
            
        except Exception as e:
            self.logger.error(f"Error downloading boundary data: {e}")
            return None
    
    def _download_landcover_data(self, boundary_file: Path, start_date: date, 
                                end_date: date, analysis_id: str) -> Optional[Path]:
        """Download land cover data for the boundary area."""
        try:
            temp_dir = boundary_file.parent
            
            # Load boundary and process Corine data
            
            # Download Corine data
            from datetime import datetime
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            corine_downloader = CorineDataDownloader(
                year_or_period=(start_datetime, end_datetime),
                logger=self.logger
            )
            
            # Save processed landcover data
            landcover_file = temp_dir / f"landcover_{corine_downloader.selected_year}.geojson"
            
            landcover_path = corine_downloader.download_and_save(
                geometry_input=boundary_file,
                output_path=landcover_file,
                output_format="geojson",
                clip_to_boundary=True,
                process_for_uhi=True
            )
            
            if landcover_path is None:
                return None
            
            return landcover_path
            
        except Exception as e:
            self.logger.error(f"Error downloading landcover data: {e}")
            return None
    
    def _create_analyzer(self, performance_mode: str, cloud_threshold: Optional[int]):
        """Create optimized analyzer using the new factory approach."""
        # Prepare kwargs for analyzer creation
        kwargs = {"logger": self.logger}
        
        # Add cache settings if enabled
        if self.cache_enabled:
            kwargs.update({
                "cache_dir": self.cache_dir,
                "max_cache_age_days": self.max_cache_age_days
            })
        
        # Override cloud threshold if specified (after performance mode is applied)
        if cloud_threshold is not None:
            kwargs["cloud_cover_threshold"] = cloud_threshold
        
        # Use the new factory approach for smart analyzer selection
        analyzer = create_analyzer(
            performance_mode=performance_mode,
            **kwargs
        )
        
        analyzer_type = type(analyzer).__name__
        self.logger.info(f"🚀 Created {analyzer_type} with {performance_mode} mode")
        
        return analyzer
    
    def _process_analysis_results(self, analysis_results: Dict[str, Any], 
                                 output_formats: List[str]) -> Dict[str, Any]:
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
        
        # Process land use correlations
        if "land_use_correlation" in analysis_results:
            landuse = analysis_results["land_use_correlation"]
            if landuse and "correlations" in landuse:
                processed["landuse_correlation"] = {
                    "overall": landuse["correlations"].get("overall", {}),
                    "by_category": landuse["correlations"].get("by_category", {}),
                    "descriptions": CORINE_GROUPED_DESCRIPTIONS
                }
        
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
            "correlation_strength": processed["landuse_correlation"].get("overall", {}).get("correlation", 0),
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
        
        return {
            "execution_time_seconds": execution_time,
            "performance_mode": performance_mode,
            "analyzer_type": metadata.get("performance_mode", "unknown"),
            "grid_cells_processed": len(temp_stats) if temp_stats is not None else 0,
            "data_sources": {
                "satellite_data": True,
                "weather_stations": False,  # TODO: implement weather station logic
                "land_cover": True
            },
            "cache_enabled": self.cache_enabled,
            "cache_stats": metadata.get("cache_stats", {})
        }
    
    def _cleanup_temp_files(self, analysis_id: str):
        """Clean up temporary files after analysis."""
        try:
            temp_dir = Path(tempfile.gettempdir()) / f"uhi_analysis_{analysis_id}"
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
                self.logger.debug(f"Cleaned up temporary files: {temp_dir}")
        except Exception as e:
            self.logger.warning(f"Could not clean up temporary files: {e}")


def main():
    """Command line interface for the UHI Analysis Backend."""
    parser = argparse.ArgumentParser(
        description="Urban Heat Island Analysis Backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --area "Kreuzberg" --start-date 2023-07-01 --end-date 2023-07-31
  %(prog)s --area "Mitte" --start-date 2023-06-01 --end-date 2023-08-31 --mode fast
  %(prog)s --area "Charlottenburg" --start-date 2023-07-15 --end-date 2023-07-20 --mode preview --output result.json
        """
    )
    
    parser.add_argument("--area", required=True,
                       help="Berlin area/suburb name (e.g., 'Kreuzberg', 'Mitte')")
    parser.add_argument("--start-date", required=True,
                       help="Analysis start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True,
                       help="Analysis end date (YYYY-MM-DD)")
    parser.add_argument("--mode", default="standard",
                       choices=["preview", "fast", "standard", "detailed"],
                       help="Performance mode (default: standard)")
    parser.add_argument("--cloud-threshold", type=int,
                       help="Cloud cover threshold 0-100 (default: mode-specific)")
    parser.add_argument("--include-weather", action="store_true",
                       help="Include weather station data (slower)")
    parser.add_argument("--output", type=str,
                       help="Output file path for results (JSON format)")
    parser.add_argument("--formats", nargs="+", default=["json"],
                       choices=["json", "geojson", "png"],
                       help="Output formats (default: json)")
    parser.add_argument("--log-level", default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level (default: INFO)")
    
    args = parser.parse_args()
    
    # Initialize backend
    backend = UHIAnalysisBackend(log_level=args.log_level)
    
    # Run analysis
    result = backend.analyze(
        area=args.area,
        start_date=args.start_date,
        end_date=args.end_date,
        performance_mode=args.mode,
        include_weather=args.include_weather,
        cloud_threshold=args.cloud_threshold,
        output_formats=args.formats
    )
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"📄 Results saved to: {args.output}")
    else:
        # Print summary to console
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
        
        print("\n📋 Full results available in JSON format")
        
        # Output JSON for programmatic access
        print("\n" + json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main() 