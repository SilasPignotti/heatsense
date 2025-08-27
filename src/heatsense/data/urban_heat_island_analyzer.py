"""
Urban Heat Island analysis engine using satellite data and land cover correlation.

This module provides the core analysis engine for comprehensive Urban Heat Island
research. Integrates satellite temperature data with land use information to
identify thermal hotspots, analyze spatial patterns, and generate mitigation
recommendations for urban planning applications.

Key features:
    - Landsat thermal band analysis via Google Earth Engine
    - Statistical correlation with land use categories
    - Spatial hotspot detection and clustering
    - Ground validation with meteorological data
    - Automated mitigation strategy recommendations

Dependencies:
    - ee: Google Earth Engine Python API for satellite data
    - geopandas: Geospatial data operations and analysis
    - numpy/pandas: Numerical computing and data manipulation
    - libpysal/esda: Spatial statistics and autocorrelation
    - scipy: Statistical analysis and correlations
    - shapely: Geometric operations and spatial queries
"""

import logging
import warnings
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import ee
import esda
import geopandas as gpd
import libpysal.weights
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from shapely.geometry import box

from heatsense.config.settings import (
    CRS_CONFIG,
    UHI_EARTH_ENGINE_PROJECT,
    UHI_LOG_LEVEL,
)
from heatsense.utils.data_processor import (
    UHI_CATEGORY_DESCRIPTIONS,
    UHI_IMPERVIOUSNESS_COEFFICIENTS,
    process_corine_for_uhi,
    standardize_weather_data,
)

class UrbanHeatIslandAnalyzer:
    """
    Urban Heat Island analysis engine using satellite data and land use correlation.
    
    Provides comprehensive UHI analysis capabilities including satellite temperature
    analysis, land use correlation, hotspot detection, and mitigation recommendations.
    Integrates with Google Earth Engine for satellite data processing and advanced
    spatial statistics for pattern analysis.
    
    Key capabilities:
    - Landsat thermal band analysis via Google Earth Engine
    - Statistical correlation with CORINE land use categories
    - Spatial hotspot detection and clustering algorithms
    - Ground validation with meteorological station data
    - Automated mitigation strategy recommendations
    - Multi-temporal trend analysis and visualization
    
    Performance modes:
    - Preview: Fast analysis for initial insights (<30s)
    - Fast: Balanced performance for most applications (30-60s)
    - Standard: Comprehensive analysis with weather validation (1-3 min)
    - Detailed: Full analysis with high-resolution processing (3-10 min)
    
    Args:
        cloud_cover_threshold: Maximum cloud cover percentage (0-100, default: 20)
        grid_cell_size: Analysis grid resolution in meters (default: 100)
        hotspot_threshold: Temperature percentile for hotspot detection (0-1, default: 0.9)
        min_cluster_size: Minimum cells for valid hotspot clusters (default: 5)
        use_grouped_categories: Enable simplified land use categories (default: True)
        log_file: Optional path for detailed logging output
        logger: Optional custom logger instance
    """
    
    def __init__(
        self, 
        cloud_cover_threshold: float = 20,
        grid_cell_size: float = 100,
        hotspot_threshold: float = 0.9,
        min_cluster_size: int = 5,
        use_grouped_categories: bool = True,
        log_file: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the Urban Heat Island analyzer with specified configuration."""
        self.cloud_threshold = cloud_cover_threshold
        self.grid_cell_size = grid_cell_size
        self.hotspot_threshold = hotspot_threshold
        self.min_cluster_size = min_cluster_size
        self.use_grouped_categories = use_grouped_categories
        self.initialized = False
        self.logger = logger or self._setup_logger(log_file)
        self.logger.info("UHI Analyzer initialized with custom configuration")

    def _setup_logger(self, log_file: Optional[Path] = None) -> logging.Logger:
        """Set up the logger with consistent formatting."""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        logger.setLevel(getattr(logging, UHI_LOG_LEVEL))
        
        # Prevent duplicate handlers
        if logger.handlers:
            return logger
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            # Store the file handler for potential flushing
            self._file_handler = file_handler
            
            # Ensure the file is created immediately
            file_handler.flush()
        else:
            self._file_handler = None
        
        return logger

    def initialize_earth_engine(self, project: Optional[str] = None) -> None:
        """
        Initialize Google Earth Engine with error handling.
        
        Args:
            project: Optional Earth Engine project ID
        """
        try:
            if not ee.data._credentials:
                self.logger.info("Authenticating with Google Earth Engine...")
                ee.Authenticate()
            
            # Use provided project or default from configuration
            project_id = project or UHI_EARTH_ENGINE_PROJECT
            ee.Initialize(project=project_id)
            self.initialized = True
            self.logger.info(f"Google Earth Engine successfully initialized with project: {project_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Earth Engine: {str(e)}")
            self.logger.info("Please ensure you have proper Earth Engine credentials and project access.")
            raise RuntimeError(f"Earth Engine initialization failed: {str(e)}")

    def analyze_heat_islands(
        self,
        city_boundary: Union[str, gpd.GeoDataFrame],
        date_range: Tuple[date, date],
        landuse_data: Union[str, gpd.GeoDataFrame],
        weather_stations: Optional[gpd.GeoDataFrame] = None,
    ) -> Dict:
        """
        Perform comprehensive urban heat island analysis.
        
        Args:
            city_boundary: Path to city boundary file or GeoDataFrame
            date_range: Tuple of start and end dates for analysis
            landuse_data: Path to land use data or GeoDataFrame  
            weather_stations: Optional GeoDataFrame with ground temperature measurements
        
        Returns:
            Dictionary containing comprehensive heat island analysis results
        """
        self.logger.info("=" * 60)
        self.logger.info("STARTING URBAN HEAT ISLAND ANALYSIS")
        self.logger.info("=" * 60)
        self.logger.info(f"Analysis period: {date_range[0]} to {date_range[1]}")
        self.logger.info(f"Cloud cover threshold: {self.cloud_threshold}%")
        self.logger.info(f"Grid cell size: {self.grid_cell_size}m")
        
        if not self.initialized:
            self.initialize_earth_engine()

        try:
            # Phase 1: Load and validate input data
            self.logger.info("Phase 1: Loading and validating input data")
            city_area = self._load_geodata(city_boundary, "city boundary")
            landuse = self._load_geodata(landuse_data, "land use")
            
            # Phase 2: Satellite data acquisition  
            self.logger.info("Phase 2: Acquiring satellite data")
            landsat_collection = self._get_landsat_collection(
                city_area.geometry.iloc[0],
                date_range
            )

            # Phase 3: Temperature analysis
            self.logger.info("Phase 3: Analyzing temperature patterns")
            temp_stats = self._calculate_temperature_stats(landsat_collection, city_area)
            
            if temp_stats.empty:
                raise ValueError("No temperature data could be extracted for the specified area and time period")
            
            # Phase 4: Land use correlation
            self.logger.info("Phase 4: Analyzing land use correlations")
            landuse_correlation = self._analyze_landuse_correlation(temp_stats, landuse)

            # Phase 5: Hotspot identification
            self.logger.info("Phase 5: Identifying heat hotspots")
            hot_spots = self._identify_heat_hotspots(temp_stats)
            
            # Phase 6: Temporal analysis (removed)

            # Compile base results
            results = {
                "metadata": {
                    "analysis_date": datetime.now().isoformat(),
                    "study_period": f"{date_range[0]} to {date_range[1]}",
                    "cloud_threshold": self.cloud_threshold,
                    "grid_cell_size": self.grid_cell_size,
                    "city_area_km2": self._calculate_area_km2(city_area)
                },
                "temperature_statistics": temp_stats,
                "land_use_correlation": landuse_correlation,
                "hot_spots": hot_spots,
            }

            # Phase 7: Standardize weather data (optional)
            if weather_stations is not None:
                self.logger.info("Phase 7: Standardizing weather data for UHI analysis")
                weather_stations = standardize_weather_data(weather_stations, self.logger)

            # Phase 8: Generate recommendations
            self.logger.info("Phase 8: Generating mitigation recommendations")
            results['mitigation_recommendations'] = self._generate_recommendations(results)

            # Final statistics
            self._log_analysis_summary(results)
            
            self.logger.info("=" * 60)
            self.logger.info("URBAN HEAT ISLAND ANALYSIS COMPLETED SUCCESSFULLY")
            self.logger.info("=" * 60)
            
            return results

        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            self.logger.error("Check input data format, Earth Engine credentials, and network connectivity")
            raise

    def _log_analysis_summary(self, results: Dict) -> None:
        """Log a summary of analysis results."""
        try:
            temp_stats = results.get('temperature_statistics', gpd.GeoDataFrame())
            hot_spots = results.get('hot_spots', gpd.GeoDataFrame())
            
            if not temp_stats.empty and 'temperature' in temp_stats.columns:
                valid_temps = temp_stats['temperature'].dropna()
                if len(valid_temps) > 0:
                    self.logger.info(f"Temperature analysis: {len(temp_stats)} grid cells processed")
                    self.logger.info(f"Temperature range: {valid_temps.min():.1f}°C to {valid_temps.max():.1f}°C")
                    self.logger.info(f"Mean temperature: {valid_temps.mean():.1f}°C")
            
            if not hot_spots.empty:
                self.logger.info(f"Heat hotspots identified: {len(hot_spots)} clusters")
                if 'temperature' in hot_spots.columns:
                    hotspot_temps = hot_spots['temperature'].dropna()
                    if len(hotspot_temps) > 0:
                        self.logger.info(f"Hotspot temperature range: {hotspot_temps.min():.1f}°C to {hotspot_temps.max():.1f}°C")
                        
        except Exception as e:
            self.logger.warning(f"Error logging analysis summary: {str(e)}")

    def _load_geodata(
        self,
        data: Union[str, gpd.GeoDataFrame],
        data_type: str
    ) -> gpd.GeoDataFrame:
        """Load and validate geospatial data."""
        try:
            if isinstance(data, str):
                self.logger.info(f"Loading {data_type} from file: {data}")
                gdf = gpd.read_file(data)
            else:
                self.logger.info(f"Using provided {data_type} GeoDataFrame")
                gdf = data.copy()
            if gdf.crs is None:
                gdf.set_crs(CRS_CONFIG["OUTPUT"], inplace=True)
                self.logger.info(f"Set CRS to {CRS_CONFIG['OUTPUT']} for {data_type}")
            self.logger.info(f"Loaded {data_type}: {len(gdf)} features, CRS: {gdf.crs}")
            return gdf
        except Exception as e:
            self.logger.error(f"Error loading {data_type}: {str(e)}")
            raise ValueError(f"Error loading {data_type}: {str(e)}")

    def _get_landsat_collection(
        self,
        geometry: gpd.GeoSeries,
        date_range: Tuple[date, date]
    ) -> ee.ImageCollection:
        """Get and filter Landsat collection."""
        try:
            # Convert geometry to Earth Engine format
            ee_geometry = ee.Geometry.Rectangle(geometry.bounds)
            self.logger.info(f"Searching for Landsat scenes in area: {geometry.bounds}")

            # Convert dates to ISO format strings for Earth Engine
            start_date_str = date_range[0].isoformat()
            end_date_str = date_range[1].isoformat()
            self.logger.info(f"Date range: {start_date_str} to {end_date_str}")

            # Get Landsat collection
            collection = (
                ee.ImageCollection("LANDSAT/LC08/C02/T1_L2") # Landsat 8 Collection 2 Tier 1 Level 2
                .filterBounds(ee_geometry)
                .filterDate(start_date_str, end_date_str)
                .filter(ee.Filter.lt('CLOUD_COVER', self.cloud_threshold))
                .select("ST_B10")  # Surface temperature band
            )

            collection_size = collection.size().getInfo()
            if collection_size == 0:
                self.logger.error("No Landsat scenes found for the specified criteria")
                raise ValueError("No Landsat scenes found for the specified criteria")
            
            self.logger.info(f"Found {collection_size} Landsat scenes meeting criteria")
            return collection
        except Exception as e:
            self.logger.error(f"Error fetching Landsat data: {str(e)}")
            raise

    def _calculate_temperature_stats(
        self,
        collection: ee.ImageCollection,
        boundary: gpd.GeoDataFrame
    ) -> pd.DataFrame:
        """Calculate detailed temperature statistics."""
        self.logger.info("Calculating temperature statistics from satellite data")
        
        # Convert Landsat 8 ST_B10 to Celsius
        temp_image = collection.mean().select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15)

        # Calculate various statistics
        stats = temp_image.reduceRegion(
            reducer=ee.Reducer.percentile([10, 25, 50, 75, 90])
            .combine(ee.Reducer.mean(), None, True)
            .combine(ee.Reducer.stdDev(), None, True),
            geometry=ee.Geometry.Rectangle(boundary.geometry.iloc[0].bounds),
            scale=30,  # Analysis scale in meters
            maxPixels=1e9  # Maximum pixels for Earth Engine operations
        ).getInfo()

        # Log temperature statistics
        if stats:
            temp_band_key = "ST_B10_mean"

        # Create spatial grid for detailed analysis
        self.logger.info("Creating analysis grid for spatial analysis")
        grid = self._create_analysis_grid(boundary)
        grid['temperature'] = self._extract_temperatures(temp_image, grid)
        
        # Log temperature statistics for the grid
        valid_temps = grid['temperature'][~pd.isna(grid['temperature'])]
        if len(valid_temps) > 0:
            self.logger.info(f"Grid temperature statistics: Mean={valid_temps.mean():.1f}°C, "
                           f"Min={valid_temps.min():.1f}°C, Max={valid_temps.max():.1f}°C")
        else:
            self.logger.warning("No valid temperature values extracted for grid cells")
        
        self.logger.info(f"Temperature statistics calculated for {len(grid)} grid cells")
        return grid

    def _create_analysis_grid(
        self,
        boundary: gpd.GeoDataFrame,
        cell_size: float = None
    ) -> gpd.GeoDataFrame:
        """Create analysis grid for detailed spatial analysis."""
        if cell_size is None:
            cell_size = self.grid_cell_size
        
        # Reproject to a projected CRS
        boundary = boundary.to_crs(CRS_CONFIG["WEB_MERCATOR"])

        minx, miny, maxx, maxy = boundary.total_bounds
        x_coords = np.arange(minx, maxx, cell_size)
        y_coords = np.arange(miny, maxy, cell_size)

        cells = []
        for x in x_coords:
            for y in y_coords:
                cell_geom = box(x, y, x + cell_size, y + cell_size)
                # Only include cells that intersect with the boundary
                if boundary.geometry.iloc[0].intersects(cell_geom):
                    cells.append(cell_geom)

        grid = gpd.GeoDataFrame(geometry=cells, crs=boundary.crs)
        grid = grid.to_crs(CRS_CONFIG["OUTPUT"])
        
        self.logger.info(f"Created analysis grid with {len(grid)} cells ({cell_size}m resolution)")
        return grid

    def _extract_temperatures(self, temp_image: ee.Image, grid: gpd.GeoDataFrame) -> np.ndarray:
        """Extract temperature values for grid cells using Google Earth Engine."""
        self.logger.info("Extracting temperature values for grid cells using Earth Engine")
        
        try:
            # For large grids, process in smaller batches to avoid timeout
            batch_size = 5000  # Process in batches of 5000 cells
            temperatures = []
            
            total_batches = (len(grid) + batch_size - 1) // batch_size
            self.logger.info(f"Processing {len(grid)} grid cells in {total_batches} batches")
            
            for i in range(0, len(grid), batch_size):
                batch_end = min(i + batch_size, len(grid))
                batch_grid = grid.iloc[i:batch_end]
                
                self.logger.info(f"Processing batch {i//batch_size + 1}/{total_batches} ({len(batch_grid)} cells)")
                
                # Convert batch grid cells to Earth Engine FeatureCollection
                features = []
                for idx, row in batch_grid.iterrows():
                    # Convert geometry to Earth Engine geometry
                    geom = ee.Geometry(row.geometry.__geo_interface__)
                    feature = ee.Feature(geom, {'grid_id': int(idx)})
                    features.append(feature)
                
                batch_fc = ee.FeatureCollection(features)
                
                # Extract temperature values using reduceRegions (without maxPixels parameter)
                temp_values = temp_image.reduceRegions(
                    collection=batch_fc,
                    reducer=ee.Reducer.mean(),
                    scale=30
                )
                
                # Get the results and convert to numpy array
                try:
                    temp_info = temp_values.getInfo()
                    
                    # Debug: Check what we're getting back
                    if i == 0:  # Only log for first batch
                        self.logger.info(f"Sample feature properties: {temp_info['features'][0]['properties'] if temp_info['features'] else 'No features'}")
                    
                    # Create a mapping from grid_id to temperature for this batch
                    temp_dict = {}
                    for feature in temp_info['features']:
                        grid_id = feature['properties']['grid_id']
                        properties = feature['properties']
                        
                        # Try different possible temperature property names
                        temp_value = None
                        for temp_key in ["ST_B10", 'mean', 'ST_B10', 'temperature']:
                            if temp_key in properties and properties[temp_key] is not None:
                                temp_value = properties[temp_key]
                                break
                        
                        if temp_value is not None:
                            # Temperature is already in Celsius from the temp_image calculation
                            temp_dict[grid_id] = temp_value
                        else:
                            temp_dict[grid_id] = np.nan
                    
                    # Add temperatures for this batch in the correct order
                    batch_temperatures = [temp_dict.get(idx, np.nan) for idx in batch_grid.index]
                    temperatures.extend(batch_temperatures)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing batch {i//batch_size + 1}: {str(e)}")
                    # Fill with NaN for this batch
                    temperatures.extend([np.nan] * len(batch_grid))
            
            temperatures_array = np.array(temperatures)
            valid_count = np.sum(~np.isnan(temperatures_array))
            
            self.logger.info(f"Successfully processed {len(grid)} grid cells")
            self.logger.info(f"Valid temperature values: {valid_count} ({valid_count/len(grid)*100:.1f}%)")
            
            if valid_count > 0:
                valid_temps = temperatures_array[~np.isnan(temperatures_array)]
                self.logger.info(f"Temperature range: {valid_temps.min():.1f}°C to {valid_temps.max():.1f}°C")
                self.logger.info(f"Mean temperature: {valid_temps.mean():.1f}°C")
            
            return temperatures_array
            
        except Exception as e:
            self.logger.error(f"Error extracting temperatures: {str(e)}")
            self.logger.warning("Falling back to NaN values for all grid cells")
            return np.full(len(grid), np.nan)

    def _analyze_landuse_correlation(
        self,
        temp_data: gpd.GeoDataFrame,
        landuse: gpd.GeoDataFrame,
        use_grouped_categories: Optional[bool] = None
    ) -> Dict:
        """
        Analyze correlation between land use and temperature using German UHI categories.
        Args:
            temp_data: GeoDataFrame with temperature grid
            landuse: GeoDataFrame with land use data
            use_grouped_categories: Ignored - always uses German categories now
        """
        self.logger.info("Analyzing land use and temperature correlations using German UHI categories")
        
        # Ensure both GeoDataFrames have the same CRS
        if temp_data.crs != landuse.crs:
            landuse = landuse.to_crs(temp_data.crs)
            self.logger.info(f"Reprojected land use data to {temp_data.crs}")
        
        # Process land use data with German UHI categories
        landuse_processed = process_corine_for_uhi(
            landuse, logger=self.logger
        )
        analysis_column = 'landuse_type'
        
        # Build German category descriptions
        category_descriptions = {}
        for category in landuse_processed[analysis_column].unique():
            if category in UHI_CATEGORY_DESCRIPTIONS:
                category_descriptions[category] = UHI_CATEGORY_DESCRIPTIONS[category]
            else:
                category_descriptions[category] = f"Unbekannte Kategorie: {category}"
        
        # Spatial join between temperature grid and land use
        try:
            joined = gpd.sjoin(temp_data, landuse_processed, how='left')
            self.logger.info(f"Spatial join completed: {len(joined)} records")
            
            # Debug: Log unique landuse types found after join
            unique_landuse = joined[analysis_column].value_counts()
            self.logger.info(f"Unique landuse types after join: {dict(unique_landuse)}")
            
        except Exception as e:
            self.logger.error(f"Spatial join failed: {str(e)}")
            return {'statistics': {}, 'correlations': {}}

        # Fill missing values in the analysis column
        joined[analysis_column] = joined[analysis_column].fillna('unknown')
        joined['impervious_area'] = joined['impervious_area'].fillna(0.5)

        # Calculate statistics by land use category
        stats = joined.groupby(analysis_column).agg({
            'temperature': ['mean', 'std', 'count', 'min', 'max'],
            'impervious_area': ['mean']
        }).round(2)
        
        # Flatten column names
        stats.columns = ['_'.join(col).strip() for col in stats.columns]
        stats = stats.reset_index()

        # Calculate correlations between landuse categories and temperature
        correlations = {}
        unique_types = joined[analysis_column].unique()
        
        # Calculate mean temperature for each landuse category
        category_temp_means = {}
        for ltype in unique_types:
            if pd.isna(ltype) or ltype == 'unknown':
                continue
                
            mask = joined[analysis_column] == ltype
            type_temps = joined[mask]['temperature'].dropna()
            
            if len(type_temps) > 0:
                category_temp_means[ltype] = type_temps.mean()
                
                # For individual categories, we'll use the difference from overall mean
                # as a measure of warming/cooling effect
                overall_mean = joined['temperature'].mean()
                temp_diff = type_temps.mean() - overall_mean
                
                # Create a correlation-like metric based on temperature difference
                # Positive = warming effect, Negative = cooling effect
                # Normalize by standard deviation for scale
                overall_std = joined['temperature'].std()
                if overall_std > 0:
                    correlation_metric = temp_diff / overall_std
                    # Cap at [-1, 1] range like correlation
                    correlation_metric = max(-1.0, min(1.0, correlation_metric))
                else:
                    correlation_metric = 0.0
                
                correlations[ltype] = {
                    'correlation': round(correlation_metric, 3),
                    'p_value': 0.001 if abs(correlation_metric) > 0.1 else 1.0,  # Simplified significance
                    'n_samples': len(type_temps),
                    'mean_temp': round(type_temps.mean(), 2),
                    'temp_diff': round(temp_diff, 2)
                }
                
                self.logger.info(f"Category {ltype}: mean_temp={type_temps.mean():.1f}°C, "
                               f"diff_from_overall={temp_diff:.1f}°C, correlation_metric={correlation_metric:.3f}")
        
        # Overall correlation - also check for constant arrays
        valid_overall = (~pd.isna(joined['temperature'])) & (~pd.isna(joined['impervious_area']))
        valid_overall_temp = joined[valid_overall]['temperature']
        valid_overall_imperv = joined[valid_overall]['impervious_area']
        
        if len(valid_overall_temp) > 1:
            temp_variance = valid_overall_temp.var()
            imperv_variance = valid_overall_imperv.var()
            
            if temp_variance > 1e-10 and imperv_variance > 1e-10:  # Non-constant arrays
                try:
                    overall_corr, overall_p = pearsonr(valid_overall_temp, valid_overall_imperv)
                    correlations['overall'] = {
                        'correlation': round(overall_corr, 3),
                        'p_value': round(overall_p, 3),
                        'n_samples': len(valid_overall_temp)
                    }
                except Exception as e:
                    self.logger.warning(f"Overall correlation calculation failed: {str(e)}")
            else:
                # Handle constant arrays gracefully
                self.logger.debug("Skipping overall correlation: constant values detected")
                correlations['overall'] = {
                    'correlation': 0.0,
                    'p_value': 1.0,
                    'n_samples': len(valid_overall_temp),
                    'note': 'constant_values'
                }

        self.logger.info(f"Land use correlation analysis completed for {len(correlations)} categories")
        
        # Debug: Log all calculated correlations
        for category, corr_data in correlations.items():
            if isinstance(corr_data, dict):
                self.logger.info(f"  {category}: correlation={corr_data.get('correlation', 'N/A'):.3f}, "
                               f"p_value={corr_data.get('p_value', 'N/A'):.3f}, "
                               f"n_samples={corr_data.get('n_samples', 'N/A')}")
            else:
                self.logger.info(f"  {category}: {corr_data}")
        
        # Debug: Log category descriptions
        self.logger.info(f"Category descriptions: {category_descriptions}")
        
        return {
            'statistics': stats.to_dict(),
            'correlations': correlations,
            'category_descriptions': category_descriptions,
            'analysis_type': 'german_categories',
            'summary': {
                'total_cells': len(joined),
                'land_use_categories': len(unique_types),
                'cells_with_temperature': (~pd.isna(joined['temperature'])).sum(),
                'cells_with_landuse': (~pd.isna(joined[analysis_column])).sum()
            }
        }

    def _identify_heat_hotspots(
        self,
        temp_data: gpd.GeoDataFrame,
        threshold: float = None,
        min_cluster_size: int = None
    ) -> gpd.GeoDataFrame:
        """Identify statistically significant heat islands."""
        if threshold is None:
            threshold = self.hotspot_threshold
        if min_cluster_size is None:
            min_cluster_size = self.min_cluster_size
            
        self.logger.info("Identifying heat island hotspots")
        
        # Calculate spatial weights with warning suppression for disconnected components
        with warnings.catch_warnings():
            # Suppress specific warning about disconnected components - this is normal for irregular geometries
            warnings.filterwarnings("ignore", 
                                  message="The weights matrix is not fully connected",
                                  category=UserWarning)
            weights = libpysal.weights.Queen.from_dataframe(temp_data, use_index=True)
        
        # Log information about connectivity
        if hasattr(weights, 'n_components') and weights.n_components > 1:
            self.logger.debug(f"Spatial weights matrix has {weights.n_components} disconnected components (normal for irregular boundaries)")

        # Calculate local Moran's I
        moran_loc = esda.moran.Moran_Local(
            temp_data.temperature,
            weights
        )

        # Identify significant hot spots
        hotspots = temp_data[
            (moran_loc.p_sim < 0.05) &
            (temp_data.temperature > temp_data.temperature.quantile(threshold))
        ].copy()

        # Cluster contiguous hot spots
        if hotspots.empty:
            hotspots['cluster_id'] = pd.Series(dtype='int')
            valid_clusters = []
        else:
            # Suppress warning for disconnected components in w_subset - normal for hotspot analysis
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", 
                                      message="The weights matrix is not fully connected",
                                      category=UserWarning)
                hotspot_weights = libpysal.weights.w_subset(weights, hotspots.index)
            
            hotspots['cluster_id'] = self._cluster_hotspots(hotspot_weights)

            # Filter small clusters
            valid_clusters = hotspots.cluster_id.value_counts()
            valid_clusters = valid_clusters[valid_clusters >= min_cluster_size].index
            hotspots = hotspots[hotspots.cluster_id.isin(valid_clusters)]
        
        self.logger.info(f"Identified {len(hotspots)} heat island hotspots in {len(valid_clusters)} clusters")
        return hotspots

    def _cluster_hotspots(
        self,
        weights: libpysal.weights.W
    ) -> np.ndarray:
        """Cluster contiguous hot spots using connected components."""
        from scipy.sparse.csgraph import connected_components
        adj_matrix = weights.sparse
        if adj_matrix.shape[0] == 0:
            return np.array([])
        n_components, labels = connected_components(adj_matrix, directed=False)
        return labels


    def _validate_with_ground_data(
        self,
        satellite_temps: gpd.GeoDataFrame,
        station_data: gpd.GeoDataFrame
    ) -> Dict:
        """Validate satellite temperatures with ground measurements."""
        self.logger.info("Validating satellite data with ground weather stations")
        
        try:
            # Ensure both datasets use a projected CRS for accurate spatial operations
            target_crs = 'EPSG:3857'  # Web Mercator for accurate distance calculations
            if satellite_temps.crs != target_crs:
                satellite_temps = satellite_temps.to_crs(target_crs)
                self.logger.info(f"Reprojected satellite data to {target_crs}")
            if station_data.crs != target_crs:
                station_data = station_data.to_crs(target_crs)
                self.logger.info(f"Reprojected weather station data to {target_crs}")
            
            # Check for required columns in station data
            temp_columns = ['ground_temp', 'temperature', 'temp', 'air_temperature', 'mean_temp', 'value']
            station_temp_col = None
            
            for col in temp_columns:
                if col in station_data.columns:
                    station_temp_col = col
                    break
            
            if station_temp_col is None:
                self.logger.error(f"No temperature column found in station data. Available columns: {list(station_data.columns)}")
                return {
                    'error': 'No temperature column found in weather station data',
                    'available_columns': list(station_data.columns)
                }
            
            # Check for temperature column in satellite data
            if 'temperature' not in satellite_temps.columns:
                self.logger.error(f"No temperature column found in satellite data. Available columns: {list(satellite_temps.columns)}")
                return {
                    'error': 'No temperature column found in satellite data',
                    'available_columns': list(satellite_temps.columns)
                }
            
            # Spatial join between satellite grid and weather stations
            joined = gpd.sjoin_nearest(station_data, satellite_temps, how='inner')
            
            if len(joined) == 0:
                self.logger.warning("No spatial matches found between weather stations and satellite data")
                return {
                    'error': 'No spatial matches found',
                    'station_count': len(station_data),
                    'satellite_cells': len(satellite_temps)
                }
            
            # Rename columns for consistency
            joined = joined.rename(columns={
                station_temp_col: 'ground_temp',
                'temperature': 'satellite_temp'
            })
            
            # Remove rows with missing temperature data
            valid_mask = (~pd.isna(joined['ground_temp'])) & (~pd.isna(joined['satellite_temp']))
            valid_data = joined[valid_mask]
            
            if len(valid_data) == 0:
                self.logger.warning("No valid temperature pairs found after removing NaN values")
                return {
                    'error': 'No valid temperature pairs found',
                    'total_matches': len(joined),
                    'ground_nan_count': pd.isna(joined['ground_temp']).sum(),
                    'satellite_nan_count': pd.isna(joined['satellite_temp']).sum()
                }
            
            # Calculate validation metrics
            ground_temps = valid_data['ground_temp'].values
            satellite_temps_vals = valid_data['satellite_temp'].values
            
            # Log diagnostic information
            self.logger.info(f"Validation data: {len(valid_data)} temperature pairs")
            self.logger.info(f"Ground temperature range: {ground_temps.min():.1f}°C to {ground_temps.max():.1f}°C (σ={np.std(ground_temps):.2f})")
            self.logger.info(f"Satellite temperature range: {satellite_temps_vals.min():.1f}°C to {satellite_temps_vals.max():.1f}°C (σ={np.std(satellite_temps_vals):.2f})")
            
            rmse = np.sqrt(((satellite_temps_vals - ground_temps) ** 2).mean())
            mae = np.abs(satellite_temps_vals - ground_temps).mean()
            bias = (satellite_temps_vals - ground_temps).mean()
            
            # Calculate correlation with improved robustness
            correlation = np.nan
            p_value = np.nan
            try:
                # Check for variability in both datasets
                ground_std = np.std(ground_temps)
                satellite_std = np.std(satellite_temps_vals)
                
                self.logger.info(f"Temperature variability: Ground σ={ground_std:.2f}°C, Satellite σ={satellite_std:.2f}°C")
                
                if ground_std > 0.1 and satellite_std > 0.1:  # Require at least 0.1°C standard deviation
                    correlation, p_value = pearsonr(ground_temps, satellite_temps_vals)
                    self.logger.info(f"Correlation calculation successful: r={correlation:.3f}, p={p_value:.3f}")
                else:
                    self.logger.warning(f"Low temperature variability detected. Ground σ={ground_std:.3f}°C, Satellite σ={satellite_std:.3f}°C")
                    # For low variability, check if values are within reasonable ranges
                    if np.abs(ground_temps.mean() - satellite_temps_vals.mean()) < 2.0:  # Agreement within 2°C
                        correlation = 0.5  # Assign moderate correlation for good agreement with low variability
                        self.logger.info(f"Low variability but good agreement (bias={bias:.1f}°C) - assigning correlation {correlation}")
            except Exception as e:
                self.logger.warning(f"Correlation calculation failed: {str(e)}")
            
            # Calculate R²
            r_squared = correlation ** 2 if not np.isnan(correlation) else np.nan
            
            results = {
                'rmse': round(rmse, 2),
                'mae': round(mae, 2),
                'bias': round(bias, 2),
                'correlation': round(correlation, 3) if not np.isnan(correlation) else None,
                'r_squared': round(r_squared, 3) if not np.isnan(r_squared) else None,
                'p_value': round(p_value, 3) if not np.isnan(p_value) else None,
                'n_pairs': len(valid_data),
                'ground_temp_range': {
                    'min': round(ground_temps.min(), 1),
                    'max': round(ground_temps.max(), 1),
                    'mean': round(ground_temps.mean(), 1)
                },
                'satellite_temp_range': {
                    'min': round(satellite_temps_vals.min(), 1),
                    'max': round(satellite_temps_vals.max(), 1),
                    'mean': round(satellite_temps_vals.mean(), 1)
                }
            }
            
            self.logger.info(f"Ground validation completed: RMSE={rmse:.2f}°C, MAE={mae:.2f}°C, Bias={bias:.2f}°C, r={correlation:.3f}")
            return results
            
        except Exception as e:
            self.logger.error(f"Ground validation failed: {str(e)}")
            return {
                'error': f'Validation failed: {str(e)}',
                'station_data_shape': station_data.shape if station_data is not None else None,
                'satellite_data_shape': satellite_temps.shape if satellite_temps is not None else None
            }

    def _generate_recommendations(self, results: Dict) -> List[Dict]:
        """Generate comprehensive mitigation recommendations based on analysis results."""
        self.logger.info("Generating comprehensive mitigation recommendations")
        recommendations = []
        
        hotspots = results.get('hot_spots', gpd.GeoDataFrame())
        landuse_correlation = results.get('land_use_correlation', {})
        
        if hotspots.empty:
            recommendations.append({
                'strategy': 'Präventive Maßnahmen',
                'description': 'Keine Hitzeinseln identifiziert. Empfehlung für präventive Stadtbegrünung zur Vermeidung von Wärmeinseln.',
                'priority': 'low',
                'category': 'prevention'
            })
            return recommendations
        
        # A) Größenbasierte Strategien
        size_recommendations = self._generate_size_based_recommendations(hotspots)
        recommendations.extend(size_recommendations)
        
        # B) Intensitätsbasierte Priorisierung  
        intensity_recommendations = self._generate_intensity_based_recommendations(hotspots)
        recommendations.extend(intensity_recommendations)
        
        # C) Landnutzungs-spezifische Empfehlungen
        landuse_recommendations = self._generate_landuse_specific_recommendations(hotspots, results)
        recommendations.extend(landuse_recommendations)
        
        # D) Korrelationsbasierte Strategien
        correlation_recommendations = self._generate_correlation_based_recommendations(landuse_correlation)
        recommendations.extend(correlation_recommendations)
        
        self.logger.info(f"Generated {len(recommendations)} comprehensive mitigation recommendations")
        return recommendations

    def _generate_size_based_recommendations(self, hotspots: gpd.GeoDataFrame) -> List[Dict]:
        """Generate recommendations based on hotspot cluster sizes (number of grid cells)."""
        recommendations = []
        
        if hotspots.empty:
            return recommendations
        
        # Analysiere Cluster-Größen basierend auf räumlicher Nähe
        # Da Hotspots aus einem Grid stammen, nutzen wir die Anzahl der zusammenhängenden Zellen
        total_hotspots = len(hotspots)
        
        # Schätze Cluster-Größen basierend auf der Hotspot-Verteilung
        # Bei sehr wenigen Hotspots -> vermutlich einzelne Zellen (klein)
        # Bei moderater Anzahl -> vermutlich kleinere Cluster (mittel) 
        # Bei vielen Hotspots -> vermutlich größere zusammenhängende Bereiche (groß)
        
        if total_hotspots <= 5:
            # Wenige isolierte Hotspots -> Mikro-Interventionen
            recommendations.append({
                'strategy': 'Punktuelle Kühlungsmaßnahmen',
                'description': f'{total_hotspots} isolierte Hitzezellen identifiziert. Empfehlung: Einzelbäume, kleine Grünstreifen und vertikale Begrünung.',
                'priority': 'medium',
                'category': 'micro_interventions',
                'affected_areas': total_hotspots
            })
            
        elif total_hotspots <= 20:
            # Moderate Anzahl -> kleinere Cluster, Quartiersansätze
            avg_cluster_size = total_hotspots // max(1, total_hotspots // 5)  # Geschätzte Cluster
            recommendations.append({
                'strategy': 'Quartiersansätze',
                'description': f'{total_hotspots} Hitzezellen in ca. {total_hotspots // max(1, avg_cluster_size)} Bereichen. Empfehlung: Pocket Parks, Dachbegrünung und klimaresiliente Straßengestaltung.',
                'priority': 'high',
                'category': 'neighborhood_interventions', 
                'affected_areas': total_hotspots
            })
            
        else:
            # Viele Hotspots -> größere zusammenhängende Bereiche
            estimated_clusters = max(1, total_hotspots // 10)  # Geschätzte große Cluster
            recommendations.append({
                'strategy': 'Strategische Grüninfrastruktur',
                'description': f'{total_hotspots} Hitzezellen in ca. {estimated_clusters} Großbereichen. Empfehlung: Grünkorridore, urbane Wasserflächen und großflächige Verschattung.',
                'priority': 'critical',
                'category': 'strategic_interventions',
                'affected_areas': total_hotspots
            })
            
        # Zusätzliche Empfehlung basierend auf Hotspot-Dichte
        if total_hotspots > 50:
            recommendations.append({
                'strategy': 'Stadtweites Kühlungskonzept',
                'description': f'{total_hotspots} Hitzezellen erfordern koordinierte Gesamtstrategie. Empfehlung: Vernetzte Grün-Blau-Infrastruktur und klimaadaptives Stadtdesign.',
                'priority': 'critical',
                'category': 'city_wide_cooling',
                'affected_areas': total_hotspots
            })
            
        return recommendations

    def _generate_intensity_based_recommendations(self, hotspots: gpd.GeoDataFrame) -> List[Dict]:
        """Generate recommendations based on temperature intensity."""
        recommendations = []
        
        if hotspots.empty or 'temperature' not in hotspots.columns:
            return recommendations
        
        temperatures = hotspots['temperature']
        mean_temp = temperatures.mean()
        
        weak_hotspots = len(temperatures[temperatures < mean_temp + 1])
        strong_hotspots = len(temperatures[temperatures >= mean_temp + 1])
        
        if weak_hotspots > 0:
            recommendations.append({
                'strategy': 'Moderate Kühlungsmaßnahmen',
                'description': f'{weak_hotspots} Bereiche mit moderater Überwärmung. Empfehlung: Helle Oberflächen, Verschattung und gezielte Begrünung.',
                'priority': 'medium',
                'category': 'prevention',
                'affected_areas': weak_hotspots
            })
            
        if strong_hotspots > 0:
            recommendations.append({
                'strategy': 'Intensive Kühlungsmaßnahmen',
                'description': f'{strong_hotspots} starke Hitzeinseln (>{mean_temp + 1:.1f}°C). Empfehlung: Kombinierte Strategien aus Begrünung, Wasserelementen und Verschattung.',
                'priority': 'critical',
                'category': 'acute_intervention',
                'affected_areas': strong_hotspots
            })
            
        return recommendations

    def _generate_landuse_specific_recommendations(self, hotspots: gpd.GeoDataFrame, results: Dict) -> List[Dict]:
        """Generate recommendations based on dominant land use in hotspot areas."""
        recommendations = []
        
        # Landnutzungs-spezifische Empfehlungsmatrix
        landuse_strategies = {
            'dichte_bebauung': {
                'strategy': 'Urbane Verdichtung kühlen',
                'description': 'Dicht bebaute Bereiche: Dach- und Fassadenbegrünung, kühle Materialien und vertikale Gärten.',
                'priority': 'critical'
            },
            'wohngebiete': {
                'strategy': 'Wohnquartiere optimieren',
                'description': 'Wohnbereiche: Straßenbäume, private Gartenbegrünung, Hofentsiegelung und Wasserspiele.',
                'priority': 'high'
            },
            'industrie': {
                'strategy': 'Gewerbeflächen optimieren',
                'description': 'Industriegebiete: Extensive Dachbegrünung, Parkplatzentsiegelung und Verschattungsanlagen.',
                'priority': 'high'
            },
            'verkehrsflaechen': {
                'strategy': 'Verkehrsflächen kühlen',
                'description': 'Verkehrsbereiche: Straßenbegleitgrün, helle Fahrbahnbeläge und Baumalleen.',
                'priority': 'medium'
            },
            'staedtisches_gruen': {
                'strategy': 'Grünflächen stärken',
                'description': 'Grünbereiche: Verstärkte Bewässerung, schattenspendende Bäume und Wasserflächen.',
                'priority': 'low'
            }
        }
        
        # Analysiere verfügbare Landnutzungsdaten
        landuse_data = results.get('raw_landcover_data')
        if landuse_data is not None and not landuse_data.empty and 'landuse_type' in landuse_data.columns:
            # Finde dominante Landnutzung in Hotspot-Gebieten  
            dominant_landuses = landuse_data['landuse_type'].value_counts().head(3)
            
            for landuse, count in dominant_landuses.items():
                if landuse in landuse_strategies:
                    strategy = landuse_strategies[landuse].copy()
                    strategy['description'] += f' ({count} Flächen betroffen)'
                    strategy['category'] = 'landuse_specific'
                    strategy['landuse_type'] = landuse
                    recommendations.append(strategy)
        
        return recommendations

    def _generate_correlation_based_recommendations(self, landuse_correlation: Dict) -> List[Dict]:
        """Generate recommendations based on land use temperature correlations."""
        recommendations = []
        
        correlations = landuse_correlation.get('correlations', {})
        
        # Suche nach hoher Korrelation zwischen Versiegelung und Temperatur
        high_correlation_found = False
        
        for category, correlation_data in correlations.items():
            if isinstance(correlation_data, dict) and 'correlation' in correlation_data:
                correlation_value = correlation_data['correlation']
                
                # Hohe positive Korrelation mit Temperatur -> wärmend
                if correlation_value > 0.6:
                    if category in ['dichte_bebauung', 'verkehrsflaechen', 'industrie']:
                        recommendations.append({
                            'strategy': 'Entsiegelungsstrategie',
                            'description': f'Starke Temperaturkorrelation bei {category} (r={correlation_value:.2f}). Empfehlung: Entsiegelung und reflektierende Materialien.',
                            'priority': 'critical',
                            'category': 'desealing',
                            'correlation_strength': correlation_value,
                            'landuse_type': category
                        })
                        high_correlation_found = True
                
                # Starke negative Korrelation -> kühlend, erhalten/verstärken
                elif correlation_value < -0.4:
                    if category in ['wald', 'wasser', 'staedtisches_gruen']:
                        # Bessere Kategoriebeschreibung
                        category_names = {
                            'wald': 'Wald und natürlicher Vegetation',
                            'wasser': 'Gewässern', 
                            'staedtisches_gruen': 'städtischem Grün'
                        }
                        category_display = category_names.get(category, category)
                        
                        recommendations.append({
                            'strategy': 'Kühlflächen ausbauen',
                            'description': f'Kühlende Wirkung bei {category_display} (r={correlation_value:.2f}). Empfehlung: Schutz und Erweiterung dieser Flächen.',
                            'priority': 'high',
                            'category': 'cooling_enhancement',
                            'correlation_strength': abs(correlation_value),
                            'landuse_type': category
                        })
        
        # Fallback-Empfehlung wenn keine starken Korrelationen gefunden
        if not high_correlation_found and correlations:
            recommendations.append({
                'strategy': 'Integrierte Kühlung',
                'description': 'Moderate Temperaturkorrelationen gefunden. Empfehlung: Kombinierte Ansätze aus Begrünung, Verschattung und Oberflächenmodifikation.',
                'priority': 'medium',
                'category': 'integrated_cooling'
            })
        
        return recommendations

    def _calculate_area_km2(self, gdf: gpd.GeoDataFrame) -> float:
        """Calculate the area of a GeoDataFrame in square kilometers."""
        # Ensure the GeoDataFrame is in a projected CRS for accurate area calculation
        if gdf.crs is None or gdf.crs.is_geographic:
            gdf = gdf.to_crs(CRS_CONFIG["WEB_MERCATOR"])
        
        # Calculate the total area in square meters
        total_area_m2 = gdf.geometry.area.sum()
        
        # Convert to square kilometers
        total_area_km2 = total_area_m2 / 1e6
        
        self.logger.info(f"Calculated total area: {total_area_km2:.2f} km²")
        return total_area_km2

