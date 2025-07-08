import ee
import numpy as np
import geopandas as gpd
import pandas as pd
import libpysal.weights
import esda
import warnings
from typing import Dict, Union, List, Tuple, Optional
from datetime import datetime, date
import logging
from pathlib import Path
from scipy.stats import pearsonr
from shapely.geometry import box
from uhi_analyzer.utils.data_processor import process_corine_for_uhi, CORINE_GROUPED_DESCRIPTIONS, enhance_weather_data_for_uhi

from uhi_analyzer.config.settings import (
    UHI_EARTH_ENGINE_PROJECT,
    UHI_LOG_LEVEL,
    CRS_CONFIG,
)

class UrbanHeatIslandAnalyzer:
    """
    Specialized analyzer for Urban Heat Island (UHI) effects using satellite imagery and land use data.
    
    This analyzer processes Landsat thermal data, land use information, and weather station data
    to identify and analyze urban heat islands. It provides comprehensive UHI analysis including:
    
    - Satellite temperature analysis using Landsat thermal bands
    - Land use correlation analysis with heat patterns
    - Heat hotspot identification and clustering
    - Temporal trend analysis across seasons
    - Ground validation with weather station data
    - Mitigation strategy recommendations
    - Comprehensive visualization of results
    
    Features:
    - Google Earth Engine integration for satellite data
    - Advanced spatial analysis with clustering algorithms
    - Statistical correlation analysis
    - Configurable parameters for different study areas
    - Robust error handling and logging
    - Professional visualization capabilities
    """
    
    def __init__(
        self, 
        cloud_cover_threshold: float = 20,  # Maximum acceptable cloud cover percentage (0-100)
        grid_cell_size: float = 100,  # Analysis grid cell size in meters
        hotspot_threshold: float = 0.9,  # Percentile threshold for hotspot identification
        min_cluster_size: int = 5,  # Minimum number of cells for a valid hotspot cluster
        use_grouped_categories: bool = True,
        log_file: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
        skip_temporal_trends: bool = False,
    ):
        """
        Initialize the Urban Heat Island analyzer.
        
        Args:
            cloud_cover_threshold: Maximum acceptable cloud cover percentage (0-100)
            grid_cell_size: Analysis grid cell size in meters
            hotspot_threshold: Percentile threshold for hotspot identification (0-1)
            min_cluster_size: Minimum number of cells for a valid hotspot cluster
            use_grouped_categories: If True, use grouped categories for cleaner analysis
            log_file: Optional path for log file
            logger: Optional logger instance
            skip_temporal_trends: If True, skip temporal trends analysis
        """
        self.cloud_threshold = cloud_cover_threshold
        self.grid_cell_size = grid_cell_size
        self.hotspot_threshold = hotspot_threshold
        self.min_cluster_size = min_cluster_size
        self.use_grouped_categories = use_grouped_categories
        self.initialized = False
        self.logger = logger or self._setup_logger(log_file)
        self.skip_temporal_trends = skip_temporal_trends
        self.logger.info(f"UHI Analyzer initialized: cloud_threshold={cloud_cover_threshold}%, "
                        f"grid_size={grid_cell_size}m, hotspot_threshold={hotspot_threshold}")

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
            
            # Phase 6: Temporal analysis
            self.logger.info("Phase 6: Analyzing temporal trends")
            if not self.skip_temporal_trends:
                temporal_trends = self._analyze_temporal_trends(
                    hot_spots, landsat_collection, date_range[0].year
                )
            else:
                temporal_trends = None

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
                "temporal_trends": temporal_trends,
            }

            # Phase 7: Ground validation (optional)
            if weather_stations is not None:
                self.logger.info("Phase 7: Enhancing weather data for UHI analysis")
                weather_stations = enhance_weather_data_for_uhi(weather_stations, self.logger)
                
                self.logger.info("Phase 7: Validating with ground weather station data")
                results['ground_validation'] = self._validate_with_ground_data(temp_stats, weather_stations)

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
        Analyze correlation between land use and temperature.
        Args:
            temp_data: GeoDataFrame with temperature grid
            landuse: GeoDataFrame with land use data
            use_grouped_categories: If True, use grouped categories for cleaner analysis
        """
        if use_grouped_categories is None:
            use_grouped_categories = self.use_grouped_categories
        self.logger.info(f"Analyzing land use and temperature correlations "
                        f"({'grouped' if use_grouped_categories else 'detailed'} categories)")
        
        # Ensure both GeoDataFrames have the same CRS
        if temp_data.crs != landuse.crs:
            landuse = landuse.to_crs(temp_data.crs)
            self.logger.info(f"Reprojected land use data to {temp_data.crs}")
        
        # Always process land use data before correlation/statistics
        landuse_processed = process_corine_for_uhi(
            landuse, group_landuse=use_grouped_categories
        )
        analysis_column = 'landuse_type'
        
        # Optionally build category descriptions
        category_descriptions = {}
        if use_grouped_categories:
            for category in landuse_processed[analysis_column].unique():
                if category in CORINE_GROUPED_DESCRIPTIONS:
                    category_descriptions[category] = CORINE_GROUPED_DESCRIPTIONS[category]
                else:
                    category_descriptions[category] = f"Unknown category: {category}"
        
        # Spatial join between temperature grid and land use
        try:
            joined = gpd.sjoin(temp_data, landuse_processed, how='left')
            self.logger.info(f"Spatial join completed: {len(joined)} records")
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

        # Perform statistical tests
        correlations = {}
        unique_types = joined[analysis_column].unique()
        
        for ltype in unique_types:
            if pd.isna(ltype):
                continue
                
            mask = joined[analysis_column] == ltype
            type_data = joined[mask]
            
            if len(type_data) > 1:  # Need at least 2 points for correlation
                # Remove NaN values for correlation
                valid_mask = (~pd.isna(type_data['temperature'])) & (~pd.isna(type_data['impervious_area']))
                valid_temp = type_data[valid_mask]['temperature']
                valid_imperv = type_data[valid_mask]['impervious_area']
                
                if len(valid_temp) > 1:
                    # Check for constant arrays to avoid ConstantInputWarning
                    temp_variance = valid_temp.var()
                    imperv_variance = valid_imperv.var()
                    
                    if temp_variance > 1e-10 and imperv_variance > 1e-10:  # Non-constant arrays
                        try:
                            corr, p_value = pearsonr(valid_temp, valid_imperv)
                            correlations[ltype] = {
                                'correlation': round(corr, 3),
                                'p_value': round(p_value, 3),
                                'n_samples': len(valid_temp)
                            }
                        except Exception as e:
                            self.logger.warning(f"Correlation calculation failed for {ltype}: {str(e)}")
                    else:
                        # Handle constant arrays gracefully
                        self.logger.debug(f"Skipping correlation for {ltype}: constant values detected")
                        correlations[ltype] = {
                            'correlation': 0.0,  # No correlation for constant data
                            'p_value': 1.0,      # No significance
                            'n_samples': len(valid_temp),
                            'note': 'constant_values'
                        }
        
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
        
        return {
            'statistics': stats.to_dict(),
            'correlations': correlations,
            'category_descriptions': category_descriptions,
            'analysis_type': 'grouped' if use_grouped_categories else 'detailed',
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

    def _analyze_temporal_trends(
        self,
        hotspots: gpd.GeoDataFrame,
        image_collection: ee.ImageCollection,
        year: int,
    ) -> Optional[Dict]:
        """Analyzes temporal trends in urban heat islands."""
        if hotspots.empty:
            self.logger.warning("No hotspots provided for temporal analysis. Skipping.")
            return None
        try:
            self.logger.info("Analyzing temporal trends.")
            
            # Limit to a representative sample of hotspots for performance
            max_hotspots = 100
            if len(hotspots) > max_hotspots:
                sample_hotspots = hotspots.sample(n=max_hotspots, random_state=42)
                self.logger.info(f"Sampling {max_hotspots} hotspots from {len(hotspots)} for temporal analysis")
            else:
                sample_hotspots = hotspots
            
            hotspot_geometries = [
                ee.Geometry(geom.__geo_interface__) for geom in sample_hotspots.geometry
            ]
            hotspot_features = ee.FeatureCollection([
                ee.Feature(geom, {'hotspot_id': i}) for i, geom in enumerate(hotspot_geometries)
            ])

            # Create a function to process monthly data
            def get_monthly_mean(month):
                start_date = ee.Date.fromYMD(year, month, 1)
                end_date = start_date.advance(1, "month")

                monthly_collection = image_collection.filterDate(start_date, end_date)

                # Check if collection has images for this month
                collection_size = monthly_collection.size()
                
                def process_images():
                    monthly_mean_image = (
                        monthly_collection.mean()
                        .select('ST_B10')  # Landsat thermal band
                        .multiply(0.00341802)  # Convert to Kelvin
                        .add(149.0)  # Offset correction
                        .subtract(273.15)  # Convert Kelvin to Celsius
                    )

                    reduced_features = monthly_mean_image.reduceRegions(
                        collection=hotspot_features,
                        reducer=ee.Reducer.mean(),
                        scale=30,  # Landsat resolution in meters
                    )

                    return reduced_features.map(lambda feature: feature.set('month', month))

                def empty_collection():
                    return ee.FeatureCollection([])

                return ee.Algorithms.If(collection_size.gt(0), process_images(), empty_collection())

            # Process months 1-12
            monthly_results = []
            for month in range(1, 13):
                try:
                    monthly_fc = get_monthly_mean(month)
                    monthly_info = ee.FeatureCollection(monthly_fc).getInfo()
                    
                    if monthly_info and monthly_info.get('features'):
                        monthly_results.extend(monthly_info['features'])
                        
                except Exception as e:
                    self.logger.warning(f"Error processing month {month}: {str(e)}")
                    continue

            if monthly_results:
                self.logger.info(f"Temporal trend analysis completed with {len(monthly_results)} data points")
                return {
                    'features': monthly_results,
                    'n_hotspots': len(sample_hotspots),
                    'year': year
                }
            else:
                self.logger.warning("No temporal trend data could be extracted")
                return None

        except ee.EEException as e:
            self.logger.error(f"An Earth Engine error occurred during temporal trend analysis: {e}")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during temporal trend analysis: {e}")
            return None

    def _validate_with_ground_data(
        self,
        satellite_temps: gpd.GeoDataFrame,
        station_data: gpd.GeoDataFrame
    ) -> Dict:
        """Validate satellite temperatures with ground measurements."""
        self.logger.info("Validating satellite data with ground weather stations")
        
        try:
            # Ensure both datasets have the same CRS
            if satellite_temps.crs != station_data.crs:
                station_data = station_data.to_crs(satellite_temps.crs)
                self.logger.info(f"Reprojected weather station data to {satellite_temps.crs}")
            
            # Check for required columns in station data
            temp_columns = ['temperature', 'temp', 'air_temperature', 'mean_temp', 'value']
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
            
            rmse = np.sqrt(((satellite_temps_vals - ground_temps) ** 2).mean())
            mae = np.abs(satellite_temps_vals - ground_temps).mean()
            bias = (satellite_temps_vals - ground_temps).mean()
            
            # Calculate correlation
            try:
                # Check for constant arrays to avoid ConstantInputWarning
                ground_variance = np.var(ground_temps)
                satellite_variance = np.var(satellite_temps_vals)
                
                if ground_variance > 1e-10 and satellite_variance > 1e-10:  # Non-constant arrays
                    correlation, p_value = pearsonr(ground_temps, satellite_temps_vals)
                else:
                    # Handle constant arrays gracefully
                    self.logger.warning("Ground or satellite temperature data contains constant values. Cannot calculate correlation.")
                    correlation, p_value = np.nan, np.nan
            except Exception as e:
                self.logger.warning(f"Correlation calculation failed: {str(e)}")
                correlation, p_value = np.nan, np.nan
            
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
        """Generate mitigation recommendations based on analysis results."""
        self.logger.info("Generating mitigation recommendations")
        recommendations = []

        # Analyze hot spots
        if len(results['hot_spots']) > 0:
            recommendations.append({
                'strategy': 'Reduktion von Hitzeinseln',
                'type': 'Reduktion von Hitzeinseln', 
                'description': 'Erhöhung der Grünflächen in identifizierten Hotspots',
                'priority': 'high',
                'locations': results['hot_spots'].geometry.to_json()
            })

        # Analyze land use correlations
        if 'land_use_correlation' in results and results['land_use_correlation']:
            land_use_data = results['land_use_correlation']
            
            # Check if we have correlations data
            if 'correlations' in land_use_data and 'impervious_surface' in land_use_data['correlations']:
                corr = land_use_data['correlations']['impervious_surface']
                if corr['correlation'] > 0.5:
                    recommendations.append({
                        'strategy': 'Oberflächenmodifikation',
                        'description': 'Einführung von kühlen Dächern und wasserdurchlässigen Belägen',
                        'priority': 'medium'
                    })
            
            # Check if we have statistics data (alternative format)
            elif 'statistics' in land_use_data:
                stats = land_use_data['statistics']
                # Look for high temperature land use types
                for landuse_type, temp_data in stats.items():
                    if isinstance(temp_data, dict) and 'temperature_mean' in temp_data:
                        if temp_data['temperature_mean'] > 30.0:  # Hot areas
                            recommendations.append({
                                'strategy': 'Grüne Infrastruktur',
                                'description': f'Erhöhung der Vegetation in {landuse_type}-Gebieten',
                                'priority': 'high'
                            })

        self.logger.info(f"Generated {len(recommendations)} mitigation recommendations")
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

