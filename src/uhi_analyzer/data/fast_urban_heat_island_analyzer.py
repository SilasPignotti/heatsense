"""
Fast Urban Heat Island Analyzer with caching and performance optimizations.

This module provides an optimized version of the Urban Heat Island analyzer that leverages
caching to dramatically improve performance by avoiding redundant API calls and computations.
"""

import ee
import numpy as np
import geopandas as gpd
import libpysal.weights
from typing import Dict, Union, List, Tuple, Optional
from datetime import datetime, date
import logging
from pathlib import Path
from scipy.stats import pearsonr
from shapely.geometry import box
import concurrent.futures

from uhi_analyzer.config.settings import (
    UHI_EARTH_ENGINE_PROJECT,
    UHI_LOG_LEVEL,
    CRS_CONFIG,
    UHI_PERFORMANCE_MODES,
    UHI_CACHE_DIR,
    UHI_CACHE_MAX_AGE_DAYS
)
from uhi_analyzer.utils.cache_manager import CacheManager


class FastUrbanHeatIslandAnalyzer:
    """
    Performance-optimized Urban Heat Island analyzer with intelligent caching.
    
    This analyzer significantly improves performance through:
    - Intelligent caching of Earth Engine collections and temperature data
    - Cached boundary and land cover data
    - Parallel processing where possible
    - Memory-efficient operations
    - Reuse of computed grids and intermediate results
    
    Features same interface as UrbanHeatIslandAnalyzer but with dramatic speed improvements.
    """
    
    def __init__(
        self, 
        cloud_cover_threshold: float = 20,  # Maximum acceptable cloud cover percentage (0-100)
        grid_cell_size: float = 100,  # Analysis grid cell size in meters
        hotspot_threshold: float = 0.9,  # Percentile threshold for hotspot identification (0-1)
        min_cluster_size: int = 5,  # Minimum number of cells for a valid hotspot cluster
        cache_dir: Union[str, Path] = UHI_CACHE_DIR,
        max_cache_age_days: int = UHI_CACHE_MAX_AGE_DAYS,
        performance_mode: Optional[str] = None,
        log_file: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Fast Urban Heat Island analyzer.
        
        Args:
            cloud_cover_threshold: Maximum acceptable cloud cover percentage (0-100)
            grid_cell_size: Analysis grid cell size in meters
            hotspot_threshold: Percentile threshold for hotspot identification (0-1)
            min_cluster_size: Minimum number of cells for a valid hotspot cluster
            cache_dir: Directory for cache files
            max_cache_age_days: Maximum age for cached items
            performance_mode: Performance mode ('preview', 'fast', 'standard', 'detailed')
            log_file: Optional path for log file
            logger: Optional logger instance
        """
        # Apply performance mode settings if specified
        if performance_mode and performance_mode in UHI_PERFORMANCE_MODES:
            mode_config = UHI_PERFORMANCE_MODES[performance_mode]
            cloud_cover_threshold = mode_config.get('cloud_cover_threshold', cloud_cover_threshold)
            grid_cell_size = mode_config.get('grid_cell_size', grid_cell_size)
            hotspot_threshold = mode_config.get('hotspot_threshold', hotspot_threshold)
            min_cluster_size = mode_config.get('min_cluster_size', min_cluster_size)
            
            # Store mode-specific settings
            self.performance_mode = performance_mode
            self.batch_size = mode_config.get('batch_size', 3000)
            self.max_pixels = mode_config.get('max_pixels', 1e9)  # Maximum pixels for Earth Engine operations
            self.skip_temporal_trends = mode_config.get('skip_temporal_trends', False)
        else:
            self.performance_mode = None
            self.batch_size = 3000
            self.max_pixels = 1e9  # Maximum pixels for Earth Engine operations
            self.skip_temporal_trends = False
        
        self.cloud_threshold = cloud_cover_threshold
        self.grid_cell_size = grid_cell_size
        self.hotspot_threshold = hotspot_threshold
        self.min_cluster_size = min_cluster_size
        self.initialized = False
        self.logger = logger or self._setup_logger(log_file)
        
        # Initialize cache manager
        self.cache = CacheManager(
            cache_dir=cache_dir,
            max_age_days=max_cache_age_days,
            logger=self.logger
        )
        
        mode_info = f", mode={performance_mode}" if performance_mode else ""
        self.logger.info(f"🚀 Fast UHI Analyzer initialized: cloud_threshold={cloud_cover_threshold}%, "
                        f"grid_size={grid_cell_size}m, cache_dir={cache_dir}{mode_info}")

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
            self._file_handler = file_handler
            file_handler.flush()
        else:
            self._file_handler = None
        
        return logger

    def initialize_earth_engine(self, project: Optional[str] = None) -> None:
        """Initialize Google Earth Engine with error handling."""
        try:
            if not ee.data._credentials:
                self.logger.info("Authenticating with Google Earth Engine...")
                ee.Authenticate()
            
            project_id = project or UHI_EARTH_ENGINE_PROJECT
            ee.Initialize(project=project_id)
            self.initialized = True
            self.logger.info(f"Google Earth Engine initialized with project: {project_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Earth Engine: {str(e)}")
            raise RuntimeError(f"Earth Engine initialization failed: {str(e)}")

    def analyze_heat_islands(
        self,
        city_boundary: Union[str, gpd.GeoDataFrame],
        date_range: Tuple[date, date],
        landuse_data: Union[str, gpd.GeoDataFrame],
        weather_stations: Optional[gpd.GeoDataFrame] = None,
        save_intermediate: bool = False,
        output_dir: Optional[Path] = None
    ) -> Dict:
        """
        Perform comprehensive urban heat island analysis with caching optimizations.
        
        Same interface as UrbanHeatIslandAnalyzer.analyze_heat_islands but with performance improvements.
        """
        self.logger.info("=" * 60)
        self.logger.info("🚀 FAST URBAN HEAT ISLAND ANALYSIS STARTING")
        self.logger.info("=" * 60)
        self.logger.info(f"Analysis period: {date_range[0]} to {date_range[1]}")
        self.logger.info("Using intelligent caching for performance optimization")
        
        if not self.initialized:
            self.initialize_earth_engine()

        # Prepare output directory
        if save_intermediate and output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Phase 1: Load and validate input data with caching
            self.logger.info("Phase 1: Loading input data (checking cache...)")
            city_area = self._load_geodata_cached(city_boundary, "city boundary")
            landuse = self._load_geodata_cached(landuse_data, "land use")
            
            # Get boundary bounds for cache keys
            bounds = city_area.total_bounds
            
            if save_intermediate and output_dir:
                city_area.to_file(output_dir / "city_boundary_processed.geojson")
                landuse.to_file(output_dir / "landuse_processed.geojson")

            # Phase 2: Check for cached temperature grid first
            self.logger.info("Phase 2: Checking for cached temperature data...")
            temp_stats = self.cache.get_temperature_grid(
                geometry_bounds=tuple(bounds),
                date_range=date_range,
                grid_size=self.grid_cell_size,
                cloud_threshold=self.cloud_threshold
            )
            
            if temp_stats is None:
                # No cache hit - perform satellite analysis
                self.logger.info("No cached data found. Acquiring satellite data...")
                landsat_collection = self._get_landsat_collection_cached(
                    city_area.geometry.iloc[0], date_range, bounds
                )
                
                self.logger.info("Computing temperature statistics...")
                temp_stats = self._calculate_temperature_stats_optimized(
                    landsat_collection, city_area, bounds, date_range
                )
                
                if temp_stats.empty:
                    raise ValueError("No temperature data could be extracted")
            else:
                self.logger.info("✅ Using cached temperature data - significant time saved!")
            
            if save_intermediate and output_dir:
                temp_stats.to_file(output_dir / "temperature_stats.geojson")

            # Phase 3: Parallel processing of analysis components
            self.logger.info("Phase 3: Performing analysis (using parallel processing...)")
            
            # Use ThreadPoolExecutor for I/O bound operations
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all analysis tasks in parallel
                landuse_future = executor.submit(
                    self._analyze_landuse_correlation_optimized, temp_stats, landuse
                )
                hotspots_future = executor.submit(
                    self._identify_heat_hotspots_optimized, temp_stats
                )
                # Only analyze temporal trends if not skipped
                if not self.skip_temporal_trends:
                    temporal_future = executor.submit(
                        self._analyze_temporal_trends_cached, 
                        temp_stats, bounds, date_range
                    )
                else:
                    temporal_future = None
                
                # Collect results
                landuse_correlation = landuse_future.result()
                hot_spots = hotspots_future.result()
                temporal_trends = temporal_future.result() if temporal_future else None
            
            if save_intermediate and output_dir and not hot_spots.empty:
                hot_spots.to_file(output_dir / "heat_hotspots.geojson")

            # Compile results
            results = {
                "metadata": {
                    "analysis_date": datetime.now().isoformat(),
                    "study_period": f"{date_range[0]} to {date_range[1]}",
                    "cloud_threshold": self.cloud_threshold,
                    "grid_cell_size": self.grid_cell_size,
                    "city_area_km2": city_area.geometry.area.sum() / 1e6,
                    "performance_mode": "fast_cached",
                    "cache_stats": self.cache.get_cache_stats()
                },
                "temperature_statistics": temp_stats,
                "land_use_correlation": landuse_correlation,
                "hot_spots": hot_spots,
                "temporal_trends": temporal_trends,
            }

            # Optional ground validation
            if weather_stations is not None:
                self.logger.info("Phase 4: Ground validation")
                results['ground_validation'] = self._validate_with_ground_data_optimized(
                    temp_stats, weather_stations
                )

            # Generate recommendations
            self.logger.info("Phase 5: Generating recommendations")
            results['mitigation_recommendations'] = self._generate_recommendations_optimized(results)

            self._log_analysis_summary(results)
            
            self.logger.info("=" * 60)
            self.logger.info("🚀 FAST ANALYSIS COMPLETED SUCCESSFULLY")
            self.logger.info("=" * 60)
            
            return results

        except Exception as e:
            self.logger.error(f"Fast analysis failed: {str(e)}")
            raise

    def _load_geodata_cached(
        self,
        data: Union[str, gpd.GeoDataFrame],
        data_type: str
    ) -> gpd.GeoDataFrame:
        """Load geospatial data with caching for file-based inputs."""
        if isinstance(data, str):
            # Check if it's a boundary file we can cache
            if data_type == "city boundary" and "boundary" in data.lower():
                # Try to extract suburb name for caching
                suburb_name = Path(data).stem
                cached_boundary = self.cache.get_boundary_data(suburb_name)
                if cached_boundary is not None:
                    return cached_boundary
                
                # Load and cache
                self.logger.info(f"Loading {data_type} from file: {data}")
                gdf = gpd.read_file(data)
                if gdf.crs is None:
                    gdf.set_crs(CRS_CONFIG["OUTPUT"], inplace=True)
                
                self.cache.cache_boundary_data(suburb_name, gdf)
                return gdf
            else:
                # Standard loading for other data types
                return self._load_geodata_standard(data, data_type)
        else:
            self.logger.info(f"Using provided {data_type} GeoDataFrame")
            gdf = data.copy()
            if gdf.crs is None:
                gdf.set_crs(CRS_CONFIG["OUTPUT"], inplace=True)
            return gdf

    def _load_geodata_standard(
        self,
        data: Union[str, gpd.GeoDataFrame],
        data_type: str
    ) -> gpd.GeoDataFrame:
        """Standard geodata loading without caching."""
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

    def _get_landsat_collection_cached(
        self,
        geometry: gpd.GeoSeries,
        date_range: Tuple[date, date],
        bounds: Tuple[float, float, float, float]
    ) -> ee.ImageCollection:
        """Get Landsat collection with caching support."""
        # Check cache first
        cached_collection = self.cache.get_earth_engine_collection(
            geometry_bounds=bounds,
            date_range=date_range,
            cloud_threshold=self.cloud_threshold
        )
        
        if cached_collection is not None:
            # Convert cached data back to EE collection if needed
            return self._reconstruct_ee_collection(cached_collection)
        
        # No cache - get fresh data
        return self._get_landsat_collection_fresh(geometry, date_range, bounds)

    def _get_landsat_collection_fresh(
        self,
        geometry: gpd.GeoSeries,
        date_range: Tuple[date, date],
        bounds: Tuple[float, float, float, float]
    ) -> ee.ImageCollection:
        """Get fresh Landsat collection and cache it."""
        try:
            ee_geometry = ee.Geometry.Rectangle(geometry.bounds)
            start_date_str = date_range[0].isoformat()
            end_date_str = date_range[1].isoformat()
            
            collection = (ee.ImageCollection(UHI_LANDSAT_COLLECTION)
                         .filterBounds(ee_geometry)
                         .filterDate(start_date_str, end_date_str)
                         .filter(ee.Filter.lt('CLOUD_COVER', self.cloud_threshold)))
            
            # Cache the collection metadata
            collection_info = {
                'count': collection.size().getInfo(),
                'date_range': date_range,
                'bounds': bounds,
                'cloud_threshold': self.cloud_threshold
            }
            
            self.cache.cache_earth_engine_collection(
                geometry_bounds=bounds,
                date_range=date_range,
                cloud_threshold=self.cloud_threshold,
                data=collection_info
            )
            
            return collection
            
        except Exception as e:
            self.logger.error(f"Error acquiring Landsat data: {str(e)}")
            raise

    def _reconstruct_ee_collection(self, cached_data: Dict) -> ee.ImageCollection:
        """Reconstruct EE collection from cached metadata."""
        # For this implementation, we'll create a fresh collection
        # In a more advanced implementation, you might cache actual image data
        ee_geometry = ee.Geometry.Rectangle(cached_data['bounds'])
        start_date = cached_data['date_range'][0].isoformat()
        end_date = cached_data['date_range'][1].isoformat()
        
        return (ee.ImageCollection(UHI_LANDSAT_COLLECTION)
                .filterBounds(ee_geometry)
                .filterDate(start_date, end_date)
                .filter(ee.Filter.lt('CLOUD_COVER', cached_data['cloud_threshold'])))

    def _calculate_temperature_stats_optimized(
        self,
        collection: ee.ImageCollection,
        boundary: gpd.GeoDataFrame,
        bounds: Tuple[float, float, float, float],
        date_range: Tuple[date, date]
    ) -> gpd.GeoDataFrame:
        """Optimized temperature calculation with caching."""
        try:
            # Check for cached analysis grid first
            grid = self.cache.get_analysis_grid(
                geometry_bounds=bounds,
                grid_size=self.grid_cell_size
            )
            
            if grid is None:
                # Create and cache new grid
                self.logger.info("Creating analysis grid...")
                grid = self._create_analysis_grid_optimized(boundary, bounds)
                self.cache.cache_analysis_grid(
                    geometry_bounds=bounds,
                    grid_size=self.grid_cell_size,
                    grid_data=grid
                )
            else:
                self.logger.info("✅ Using cached analysis grid")

            # Calculate mean temperature from collection
            self.logger.info("Processing satellite imagery...")
            temp_image = (collection
                         .select(UHI_TEMPERATURE_BAND)
                         .median()
                         .multiply(UHI_TEMP_MULTIPLIER)
                         .add(UHI_TEMP_ADDEND)
                         .subtract(UHI_KELVIN_OFFSET))

            # Extract temperatures more efficiently
            temperatures = self._extract_temperatures_optimized(temp_image, grid)
            
            # Create result GeoDataFrame
            result = grid.copy()
            result['temperature'] = temperatures
            result = result.dropna(subset=['temperature'])
            
            # Cache the result
            self.cache.cache_temperature_grid(
                geometry_bounds=bounds,
                date_range=date_range,
                grid_size=self.grid_cell_size,
                cloud_threshold=self.cloud_threshold,
                temperature_grid=result
            )
            
            self.logger.info(f"Temperature analysis completed: {len(result)} grid cells")
            return result
            
        except Exception as e:
            self.logger.error(f"Temperature calculation failed: {str(e)}")
            raise

    def _create_analysis_grid_optimized(
        self,
        boundary: gpd.GeoDataFrame,
        bounds: Tuple[float, float, float, float],
        cell_size: float = None
    ) -> gpd.GeoDataFrame:
        """Create optimized analysis grid using boundary bounds."""
        if cell_size is None:
            cell_size = self.grid_cell_size
            
        # Use bounds directly for efficiency
        xmin, ymin, xmax, ymax = bounds
        
        # Create grid coordinates
        x_coords = np.arange(xmin, xmax + cell_size, cell_size)
        y_coords = np.arange(ymin, ymax + cell_size, cell_size)
        
        # Create grid cells more efficiently
        cells = []
        for i, x in enumerate(x_coords[:-1]):
            for j, y in enumerate(y_coords[:-1]):
                cell_bounds = [x, y, x + cell_size, y + cell_size]
                cells.append({
                    'grid_id': i * len(y_coords) + j,
                    'geometry': box(*cell_bounds)
                })
        
        grid = gpd.GeoDataFrame(cells, crs=boundary.crs)
        
        # Filter to boundary more efficiently using spatial index
        grid = grid[grid.geometry.intersects(boundary.unary_union)]
        
        self.logger.info(f"Created optimized grid: {len(grid)} cells of {cell_size}m")
        return grid.reset_index(drop=True)

    def _extract_temperatures_optimized(
        self,
        temp_image: ee.Image,
        grid: gpd.GeoDataFrame
    ) -> np.ndarray:
        """Optimized temperature extraction using batch processing."""
        try:
            # Convert grid to EE FeatureCollection more efficiently
            grid_features = []
            for idx, row in grid.iterrows():
                geom = row.geometry
                coords = [[list(coord) for coord in geom.exterior.coords]]
                ee_geom = ee.Geometry.Polygon(coords)
                feature = ee.Feature(ee_geom, {'grid_id': int(idx)})
                grid_features.append(feature)
            
            # Process in batches to avoid memory issues
            batch_size = min(self.batch_size, len(grid_features))
            temperatures = np.full(len(grid), np.nan)
            
            for i in range(0, len(grid_features), batch_size):
                batch_features = grid_features[i:i + batch_size]
                batch_collection = ee.FeatureCollection(batch_features)
                
                # Sample temperature values
                sampled = temp_image.sampleRegions(
                    collection=batch_collection,
                    scale=UHI_SCALE,
                    tileScale=4,
                    geometries=False
                )
                
                # Extract values
                batch_data = sampled.getInfo()
                for feature in batch_data['features']:
                    props = feature['properties']
                    grid_id = props['grid_id']
                    temp_value = props.get(UHI_TEMPERATURE_BAND)
                    if temp_value is not None:
                        temperatures[grid_id] = temp_value
            
            return temperatures
            
        except Exception as e:
            self.logger.error(f"Temperature extraction failed: {str(e)}")
            raise

    def _analyze_landuse_correlation_optimized(
        self,
        temp_data: gpd.GeoDataFrame,
        landuse: gpd.GeoDataFrame,
        use_grouped_categories: bool = True
    ) -> Dict:
        """Optimized land use correlation analysis."""
        self.logger.info("Analyzing land use correlations...")
        
        try:
            # Use spatial join with optimized parameters
            overlay = gpd.overlay(
                temp_data[['geometry', 'temperature']],
                landuse[['geometry', 'landuse_code']],
                how='intersection',
                keep_geom_type=False
            )
            
            if overlay.empty:
                return {"error": "No intersection between temperature and land use data"}

            # Calculate area-weighted averages more efficiently
            overlay['area'] = overlay.geometry.area
            overlay = overlay[overlay['area'] > 0]  # Remove zero-area intersections
            
            # Group and calculate statistics using pandas groupby
            if use_grouped_categories:
                overlay['grouped_code'] = overlay['landuse_code'].map(
                    CORINE_DETAILED_TO_GROUPED
                ).fillna(overlay['landuse_code'])
                group_col = 'grouped_code'
                mapping = CORINE_GROUPED_DESCRIPTIONS
                impervious_coeffs = CORINE_GROUPED_IMPERVIOUS_COEFFICIENTS
            else:
                group_col = 'landuse_code'
                mapping = CORINE_LANDUSE_MAPPING
                impervious_coeffs = CORINE_IMPERVIOUS_COEFFICIENTS

            # Efficient aggregation using weighted averages
            def weighted_avg(group):
                return (group['temperature'] * group['area']).sum() / group['area'].sum()
            
            stats = overlay.groupby(group_col).agg({
                'temperature': ['count', 'mean', weighted_avg, 'std'],
                'area': 'sum'
            }).round(2)
            
            # Flatten column names
            stats.columns = ['count', 'mean_temp', 'weighted_mean_temp', 'std_temp', 'total_area']
            stats = stats.reset_index()
            
            # Add descriptions and impervious surface data
            stats['description'] = stats[group_col].map(mapping)
            stats['impervious_surface_pct'] = stats[group_col].map(impervious_coeffs)
            
            # Calculate correlations more efficiently
            correlation_data = stats.dropna(subset=['weighted_mean_temp', 'impervious_surface_pct'])
            
            correlations = {}
            if len(correlation_data) > 2:
                # Temperature vs impervious surface correlation
                temp_imperv_corr, temp_imperv_p = pearsonr(
                    correlation_data['weighted_mean_temp'],
                    correlation_data['impervious_surface_pct']
                )
                correlations['temperature_vs_impervious'] = {
                    'correlation': round(temp_imperv_corr, 3),
                    'p_value': round(temp_imperv_p, 4),
                    'significant': temp_imperv_p < 0.05
                }

            return {
                'statistics': stats.to_dict('records'),
                'correlations': correlations,
                'summary': {
                    'land_use_types': len(stats),
                    'total_area_km2': round(stats['total_area'].sum() / 1e6, 2),
                    'temperature_range': {
                        'min': float(stats['weighted_mean_temp'].min()),
                        'max': float(stats['weighted_mean_temp'].max())
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Land use correlation analysis failed: {str(e)}")
            return {"error": str(e)}

    def _identify_heat_hotspots_optimized(
        self,
        temp_data: gpd.GeoDataFrame,
        threshold: float = None,
        min_cluster_size: int = None
    ) -> gpd.GeoDataFrame:
        """Optimized heat hotspot identification."""
        if threshold is None:
            threshold = self.hotspot_threshold
        if min_cluster_size is None:
            min_cluster_size = self.min_cluster_size
            
        try:
            if temp_data.empty or 'temperature' not in temp_data.columns:
                return gpd.GeoDataFrame()

            # Calculate threshold temperature more efficiently
            temp_threshold = temp_data['temperature'].quantile(threshold)
            hotspots = temp_data[temp_data['temperature'] >= temp_threshold].copy()
            
            if len(hotspots) < min_cluster_size:
                self.logger.warning(f"Insufficient hotspots found: {len(hotspots)} < {min_cluster_size}")
                return gpd.GeoDataFrame()

            # Use spatial weights for clustering with optimized parameters
            weights = libpysal.weights.Queen.from_dataframe(
                hotspots,
                use_index=False,
                silence_warnings=True
            )
            
            if weights.n == 0:
                return hotspots
            
            # Perform clustering
            clusters = self._cluster_hotspots_optimized(weights)
            hotspots['cluster_id'] = clusters
            
            # Filter by minimum cluster size
            cluster_sizes = hotspots['cluster_id'].value_counts()
            valid_clusters = cluster_sizes[cluster_sizes >= min_cluster_size].index
            
            result = hotspots[hotspots['cluster_id'].isin(valid_clusters)].copy()
            
            self.logger.info(f"Identified {len(result)} hotspot cells in {len(valid_clusters)} clusters")
            return result
            
        except Exception as e:
            self.logger.error(f"Hotspot identification failed: {str(e)}")
            return gpd.GeoDataFrame()

    def _cluster_hotspots_optimized(self, weights: libpysal.weights.W) -> np.ndarray:
        """Optimized hotspot clustering using connected components."""
        try:
            # Use networkx for efficient connected components if available
            try:
                import networkx as nx
                G = weights.to_networkx()
                components = list(nx.connected_components(G))
                clusters = np.zeros(weights.n, dtype=int)
                for i, component in enumerate(components):
                    for node in component:
                        clusters[node] = i
                return clusters
            except ImportError:
                # Fallback to manual clustering
                clusters = np.full(weights.n, -1, dtype=int)
                cluster_id = 0
                
                for i in range(weights.n):
                    if clusters[i] == -1:
                        self._flood_fill(i, cluster_id, clusters, weights)
                        cluster_id += 1
                
                return clusters
                
        except Exception as e:
            self.logger.warning(f"Clustering failed, using individual hotspots: {str(e)}")
            return np.arange(weights.n)

    def _flood_fill(self, start: int, cluster_id: int, clusters: np.ndarray, weights: libpysal.weights.W):
        """Flood fill algorithm for clustering."""
        stack = [start]
        while stack:
            node = stack.pop()
            if clusters[node] == -1:
                clusters[node] = cluster_id
                for neighbor in weights.neighbors[node]:
                    if clusters[neighbor] == -1:
                        stack.append(neighbor)

    def _analyze_temporal_trends_cached(
        self,
        temp_data: gpd.GeoDataFrame,
        bounds: Tuple[float, float, float, float],
        date_range: Tuple[date, date]
    ) -> Optional[Dict]:
        """Analyze temporal trends with caching optimizations."""
        # For this implementation, we'll use a simplified approach
        # In practice, you might want to cache monthly temperature data
        
        try:
            if temp_data.empty:
                return None
                
            # Basic temporal analysis based on available data
            return {
                'analysis_period': f"{date_range[0]} to {date_range[1]}",
                'mean_temperature': float(temp_data['temperature'].mean()),
                'temperature_std': float(temp_data['temperature'].std()),
                'hotspot_count': len(temp_data[temp_data['temperature'] > temp_data['temperature'].quantile(0.8)]),
                'data_points': len(temp_data)
            }
            
        except Exception as e:
            self.logger.warning(f"Temporal analysis failed: {str(e)}")
            return None

    def _validate_with_ground_data_optimized(
        self,
        satellite_temps: gpd.GeoDataFrame,
        station_data: gpd.GeoDataFrame
    ) -> Dict:
        """Optimized ground data validation."""
        try:
            # Use spatial join with optimized buffer
            stations_buffered = station_data.copy()
            stations_buffered['geometry'] = stations_buffered.geometry.buffer(1000)  # 1km buffer
            
            # Spatial join
            joined = gpd.sjoin(satellite_temps, stations_buffered, how='inner', predicate='intersects')
            
            if joined.empty:
                return {"error": "No spatial overlap between satellite and ground data"}
            
            # Calculate validation statistics
            correlation, p_value = pearsonr(joined['temperature'], joined['ground_temp'])
            
            return {
                'validation_points': len(joined),
                'correlation': round(correlation, 3),
                'p_value': round(p_value, 4),
                'rmse': round(np.sqrt(np.mean((joined['temperature'] - joined['ground_temp'])**2)), 2),
                'mean_difference': round((joined['temperature'] - joined['ground_temp']).mean(), 2)
            }
            
        except Exception as e:
            self.logger.error(f"Ground validation failed: {str(e)}")
            return {"error": str(e)}

    def _generate_recommendations_optimized(self, results: Dict) -> List[Dict]:
        """Generate optimized mitigation recommendations."""
        recommendations = []
        
        try:
            temp_stats = results.get('temperature_statistics', gpd.GeoDataFrame())
            landuse_data = results.get('land_use_correlation', {})
            
            if not temp_stats.empty:
                # High temperature areas recommendation
                high_temp_threshold = temp_stats['temperature'].quantile(0.9)
                high_temp_count = len(temp_stats[temp_stats['temperature'] > high_temp_threshold])
                
                if high_temp_count > 0:
                    recommendations.append({
                        'category': 'Urban Cooling',
                        'priority': 'High',
                        'title': 'Implement cooling strategies in high-temperature zones',
                        'description': f'Focus on {high_temp_count} grid cells with temperatures above {high_temp_threshold:.1f}°C',
                        'strategies': [
                            'Increase urban tree canopy coverage',
                            'Install cool roofing materials',
                            'Create green infrastructure corridors',
                            'Implement water features for evapotranspiration cooling'
                        ]
                    })
            
            # Land use specific recommendations
            stats = landuse_data.get('statistics', [])
            for stat in stats:
                if stat.get('weighted_mean_temp', 0) > temp_stats['temperature'].quantile(0.8):
                    land_type = stat.get('description', 'Unknown')
                    recommendations.append({
                        'category': 'Land Use Optimization',
                        'priority': 'Medium',
                        'title': f'Mitigate heat in {land_type} areas',
                        'description': f'Average temperature: {stat.get("weighted_mean_temp", 0):.1f}°C',
                        'strategies': [
                            'Increase green space integration',
                            'Improve building energy efficiency',
                            'Implement sustainable urban drainage'
                        ]
                    })
            
            return recommendations[:10]  # Limit to top 10 recommendations
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {str(e)}")
            return []

    def _log_analysis_summary(self, results: Dict) -> None:
        """Log analysis summary with performance metrics."""
        try:
            temp_stats = results.get('temperature_statistics', gpd.GeoDataFrame())
            hot_spots = results.get('hot_spots', gpd.GeoDataFrame())
            cache_stats = results.get('metadata', {}).get('cache_stats', {})
            
            self.logger.info("=" * 40)
            self.logger.info("ANALYSIS SUMMARY")
            self.logger.info("=" * 40)
            
            if not temp_stats.empty and 'temperature' in temp_stats.columns:
                valid_temps = temp_stats['temperature'].dropna()
                if len(valid_temps) > 0:
                    self.logger.info(f"📊 Temperature analysis: {len(temp_stats)} grid cells")
                    self.logger.info(f"🌡️  Temperature range: {valid_temps.min():.1f}°C to {valid_temps.max():.1f}°C")
                    self.logger.info(f"📈 Mean temperature: {valid_temps.mean():.1f}°C")
            
            if not hot_spots.empty:
                self.logger.info(f"🔥 Heat hotspots: {len(hot_spots)} cells")
            
            # Cache performance info
            if cache_stats:
                self.logger.info(f"💾 Cache usage: {cache_stats.get('total_files', 0)} files, "
                              f"{cache_stats.get('total_size_mb', 0):.1f} MB")
                
        except Exception as e:
            self.logger.warning(f"Error logging summary: {str(e)}")

    # Include other methods from original analyzer (save_results, visualize_results, etc.)
    def save_results(
        self, 
        results: Dict, 
        output_dir: Path, 
        prefix: str = "fast_uhi_analysis"
    ) -> Dict[str, Path]:
        """Save analysis results to files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        try:
            # Save temperature statistics
            if 'temperature_statistics' in results and not results['temperature_statistics'].empty:
                temp_path = output_dir / f"{prefix}_temperature_stats.geojson"
                results['temperature_statistics'].to_file(temp_path)
                saved_files['temperature_statistics'] = temp_path
                
            # Save hotspots
            if 'hot_spots' in results and not results['hot_spots'].empty:
                hotspots_path = output_dir / f"{prefix}_hotspots.geojson"
                results['hot_spots'].to_file(hotspots_path)
                saved_files['hot_spots'] = hotspots_path
                
            # Save other results as JSON
            for key in ['land_use_correlation', 'mitigation_recommendations', 'metadata']:
                if key in results:
                    import json
                    file_path = output_dir / f"{prefix}_{key}.json"
                    with open(file_path, 'w') as f:
                        json.dump(results[key], f, indent=2, default=str)
                    saved_files[key] = file_path
            
            self.logger.info(f"✅ Results saved to {output_dir}")
            return saved_files
            
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
            raise

    @staticmethod
    def get_default_parameters() -> Dict[str, any]:
        """Get default configuration parameters for Fast UHI analysis."""
        from .urban_heat_island_analyzer import UrbanHeatIslandAnalyzer
        params = UrbanHeatIslandAnalyzer.get_default_parameters()
        params['performance_mode'] = 'fast_cached'
        params['cache_enabled'] = True
        return params

    def get_cache_stats(self) -> Dict[str, any]:
        """Get current cache statistics."""
        return self.cache.get_cache_stats()

    def clear_cache(self, cache_type: Optional[str] = None):
        """Clear cache files."""
        self.cache.clear_cache(cache_type)
        self.logger.info(f"🗑️  Cache cleared: {cache_type or 'all'}")

    @staticmethod
    def get_available_performance_modes() -> List[str]:
        """Get list of available performance modes."""
        return list(UHI_PERFORMANCE_MODES.keys())

    @staticmethod
    def get_performance_mode_config(mode: str) -> Dict[str, any]:
        """Get configuration for a specific performance mode."""
        if mode not in UHI_PERFORMANCE_MODES:
            raise ValueError(f"Unknown performance mode: {mode}. Available modes: {list(UHI_PERFORMANCE_MODES.keys())}")
        return UHI_PERFORMANCE_MODES[mode].copy()

    @classmethod
    def create_with_performance_mode(
        cls,
        performance_mode: str,
        cache_dir: Union[str, Path] = UHI_CACHE_DIR,
        max_cache_age_days: int = UHI_CACHE_MAX_AGE_DAYS,
        **kwargs
    ) -> 'FastUrbanHeatIslandAnalyzer':
        """
        Create FastUrbanHeatIslandAnalyzer with specific performance mode.
        
        Args:
            performance_mode: Performance mode ('preview', 'fast', 'standard', 'detailed')
            cache_dir: Directory for cache files
            max_cache_age_days: Maximum age for cached items
            **kwargs: Additional arguments to override mode defaults
            
        Returns:
            Configured FastUrbanHeatIslandAnalyzer instance
        """
        return cls(
            performance_mode=performance_mode,
            cache_dir=cache_dir,
            max_cache_age_days=max_cache_age_days,
            **kwargs
        ) 