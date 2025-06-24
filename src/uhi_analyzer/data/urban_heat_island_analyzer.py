import ee
import numpy as np
import geopandas as gpd
import pandas as pd
import libpysal.weights
import esda
from typing import Dict, Union, List, Tuple, Optional
from datetime import datetime, date
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr
from shapely.geometry import box

from ..config.settings import (
    UHI_CLOUD_COVER_THRESHOLD,
    UHI_LANDSAT_COLLECTION,
    UHI_TEMPERATURE_BAND,
    UHI_SCALE,
    UHI_MAX_PIXELS,
    UHI_TEMP_MULTIPLIER,
    UHI_TEMP_ADDEND,
    UHI_KELVIN_OFFSET,
    UHI_GRID_CELL_SIZE,
    UHI_HOTSPOT_THRESHOLD,
    UHI_MIN_CLUSTER_SIZE,
    UHI_MORAN_SIGNIFICANCE,
    UHI_PERCENTILES,
    UHI_CORRELATION_THRESHOLD,
    UHI_VISUALIZATION_DPI,
    UHI_VISUALIZATION_FIGSIZE,
    UHI_TEMPERATURE_COLORMAP,
    UHI_LOG_LEVEL,
    CRS_CONFIG
)

class UrbanHeatIslandAnalyzer:
    """
    A class for analyzing urban heat island effects using satellite imagery and land use data.
    This analyzer processes Landsat thermal data, land use information, and other environmental
    factors to identify and analyze urban heat islands.
    """
    def __init__(self, cloud_cover_threshold: float = None, log_file: Optional[Path] = None):
        """
        Initialize the heat island analyzer.
        
        Args:
            cloud_cover_threshold: Maximum acceptable cloud cover percentage (0-100).
                                  If None, uses default from settings.
            log_file: Optional path for log file.
        """
        self.cloud_threshold = cloud_cover_threshold or UHI_CLOUD_COVER_THRESHOLD
        self.initialized = False
        self.logger = self._setup_logger(log_file)

    def _setup_logger(self, log_file: Optional[Path] = None) -> logging.Logger:
        """Set up the logger with consistent formatting."""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        logger.setLevel(getattr(logging, UHI_LOG_LEVEL))
        
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
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger

    def initialize_earth_engine(self) -> None:
        """Initialize Google Earth Engine with error handling."""
        try:
            if not ee.data._credentials:
                ee.Authenticate()
            ee.Initialize()
            self.initialized = True
            self.logger.info("Google Earth Engine successfully initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Earth Engine: {str(e)}")
            raise

    def analyze_heat_islands(
        self,
        city_boundary: Union[str, gpd.GeoDataFrame],
        date_range: Tuple[date, date],
        landuse_data: Union[str, gpd.GeoDataFrame],
        weather_stations: Optional[gpd.GeoDataFrame] = None
    ) -> Dict:
        """
        Analyze urban heat island effect using multiple data sources.
        
        Args:
            city_boundary: Path to city boundary file or GeoDataFrame.
            date_range: Tuple of start and end dates for analysis.
            landuse_data: Path to land use data or GeoDataFrame.
            weather_stations: Optional GeoDataFrame with ground temperature measurements.
        
        Returns:
            Dictionary containing comprehensive heat island analysis results.
        """
        self.logger.info("Starting urban heat island analysis")
        self.logger.info(f"Date range: {date_range[0]} to {date_range[1]}")
        self.logger.info(f"Cloud cover threshold: {self.cloud_threshold}%")
        
        if not self.initialized:
            self.initialize_earth_engine()

        # Load and validate input data
        self.logger.info("Loading and validating input data")
        city_area = self._load_geodata(city_boundary, "city boundary")
        landuse = self._load_geodata(landuse_data, "land use")

        # Get Landsat data
        self.logger.info("Fetching Landsat satellite data")
        landsat_collection = self._get_landsat_collection(
            city_area.geometry.iloc[0],
            date_range
        )

        # Calculate temperature statistics
        self.logger.info("Calculating temperature statistics")
        temp_stats = self._calculate_temperature_stats(landsat_collection, city_area)

        # Analyze patterns
        self.logger.info("Analyzing land use correlations")
        results = {
            'temperature_statistics': temp_stats,
            'land_use_correlation': self._analyze_landuse_correlation(temp_stats, landuse),
            'hot_spots': self._identify_heat_hotspots(temp_stats),
            'temporal_trends': self._analyze_temporal_trends(landsat_collection, city_area)
        }

        # Add ground validation if weather stations provided
        if weather_stations is not None:
            self.logger.info("Validating with ground weather station data")
            results['ground_validation'] = self._validate_with_ground_data(temp_stats, weather_stations)

        # Add mitigation recommendations
        self.logger.info("Generating mitigation recommendations")
        results['mitigation_recommendations'] = self._generate_recommendations(results)

        self.logger.info("Urban heat island analysis completed successfully")
        return results

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

            # Get Landsat collection
            collection = (
                ee.ImageCollection(UHI_LANDSAT_COLLECTION)
                .filterBounds(ee_geometry)
                .filterDate(date_range[0], date_range[1])
                .filter(ee.Filter.lt('CLOUD_COVER', self.cloud_threshold))
                .select([UHI_TEMPERATURE_BAND])  # Surface temperature band
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
        
        # Convert to Celsius and calculate statistics
        temp_image = (
            collection.mean()
            .multiply(UHI_TEMP_MULTIPLIER).add(UHI_TEMP_ADDEND)
            .subtract(UHI_KELVIN_OFFSET)
        )

        # Calculate various statistics
        stats = temp_image.reduceRegion(
            reducer=ee.Reducer.percentile(UHI_PERCENTILES)
            .combine(ee.Reducer.mean(), None, True)
            .combine(ee.Reducer.stdDev(), None, True),
            geometry=ee.Geometry.Rectangle(boundary.geometry.iloc[0].bounds),
            scale=UHI_SCALE,
            maxPixels=UHI_MAX_PIXELS
        ).getInfo()

        # Create spatial grid for detailed analysis
        self.logger.info("Creating analysis grid for spatial analysis")
        grid = self._create_analysis_grid(boundary)
        grid['temperature'] = self._extract_temperatures(temp_image, grid)
        
        self.logger.info(f"Temperature statistics calculated for {len(grid)} grid cells")
        return grid

    def _create_analysis_grid(
        self,
        boundary: gpd.GeoDataFrame,
        cell_size: float = None
    ) -> gpd.GeoDataFrame:
        """Create analysis grid for detailed spatial analysis."""
        if cell_size is None:
            cell_size = UHI_GRID_CELL_SIZE
            
        # Reproject to a projected CRS
        boundary = boundary.to_crs(CRS_CONFIG["WEB_MERCATOR"])

        minx, miny, maxx, maxy = boundary.total_bounds
        x_coords = np.arange(minx, maxx, cell_size)
        y_coords = np.arange(miny, maxy, cell_size)

        cells = []
        for x in x_coords:
            for y in y_coords:
                cells.append(box(x, y, x + cell_size, y + cell_size))

        grid = gpd.GeoDataFrame(geometry=cells, crs=boundary.crs)
        grid = grid.to_crs(CRS_CONFIG["OUTPUT"])
        
        self.logger.info(f"Created analysis grid with {len(grid)} cells ({cell_size}m resolution)")
        return grid

    def _extract_temperatures(self, temp_image: ee.Image, grid: gpd.GeoDataFrame) -> np.ndarray:
        """Extract temperature values for grid cells."""
        # This is a placeholder - in a real implementation, you would use Earth Engine
        # to extract temperature values for each grid cell
        # For now, we'll generate some sample data
        self.logger.info("Extracting temperature values for grid cells")
        return np.random.normal(20, 5, len(grid))  # Placeholder data

    def _analyze_landuse_correlation(
        self,
        temp_data: gpd.GeoDataFrame,
        landuse: gpd.GeoDataFrame
    ) -> Dict:
        """Analyze correlation between land use and temperature."""
        self.logger.info("Analyzing land use and temperature correlations")
        
        # Spatial join between temperature grid and land use
        joined = gpd.sjoin(temp_data, landuse)

        # Calculate statistics by land use type
        stats = joined.groupby('landuse_type').agg({
            'temperature': ['mean', 'std', 'count']
        }).reset_index()

        # Perform statistical tests
        correlations = {}
        for ltype in landuse.landuse_type.unique():
            mask = joined.landuse_type == ltype
            if mask.sum() > 1:  # Need at least 2 points for correlation
                corr, p_value = pearsonr(
                    joined[mask].temperature,
                    joined[mask].impervious_area
                )
                correlations[ltype] = {'correlation': corr, 'p_value': p_value}

        self.logger.info(f"Land use correlation analysis completed for {len(correlations)} land use types")
        return {
            'statistics': stats.to_dict(),
            'correlations': correlations
        }

    def _identify_heat_hotspots(
        self,
        temp_data: gpd.GeoDataFrame,
        threshold: float = None,
        min_cluster_size: int = None
    ) -> gpd.GeoDataFrame:
        """Identify statistically significant heat islands."""
        if threshold is None:
            threshold = UHI_HOTSPOT_THRESHOLD
        if min_cluster_size is None:
            min_cluster_size = UHI_MIN_CLUSTER_SIZE
            
        self.logger.info("Identifying heat island hotspots")
        
        # Calculate spatial weights
        weights = libpysal.weights.Queen.from_dataframe(temp_data)

        # Calculate local Moran's I
        moran_loc = esda.moran.Moran_Local(
            temp_data.temperature,
            weights
        )

        # Identify significant hot spots
        hotspots = temp_data[
            (moran_loc.p_sim < UHI_MORAN_SIGNIFICANCE) &
            (temp_data.temperature > temp_data.temperature.quantile(threshold))
        ].copy()

        # Cluster contiguous hot spots
        hotspots['cluster_id'] = self._cluster_hotspots(hotspots, weights)

        # Filter small clusters
        valid_clusters = hotspots.cluster_id.value_counts()
        valid_clusters = valid_clusters[valid_clusters >= min_cluster_size].index
        hotspots = hotspots[hotspots.cluster_id.isin(valid_clusters)]
        
        self.logger.info(f"Identified {len(hotspots)} heat island hotspots in {len(valid_clusters)} clusters")
        return hotspots

    def _cluster_hotspots(
        self,
        hotspots: gpd.GeoDataFrame,
        weights: libpysal.weights.W
    ) -> np.ndarray:
        """Cluster contiguous hot spots using connected components."""
        from scipy.sparse.csgraph import connected_components
        adj_matrix = weights.sparse
        n_components, labels = connected_components(adj_matrix, directed=False)
        return labels

    def _analyze_temporal_trends(
        self,
        collection: ee.ImageCollection,
        boundary: gpd.GeoDataFrame
    ) -> Dict:
        """Analyze temporal temperature trends."""
        self.logger.info("Analyzing temporal temperature trends")
        
        temps = []
        dates = []
        for image in collection.toList(collection.size().getInfo()).getInfo():
            date_str = image['properties']['DATE_ACQUIRED']
            temp = self._calculate_temperature_stats(
                ee.Image(image['id']),
                boundary
            )
            temps.append(temp['mean'])
            dates.append(datetime.strptime(date_str, '%Y-%m-%d').date())

        if len(temps) > 1:
            slope, intercept = np.polyfit(range(len(temps)), temps, 1)
            self.logger.info(f"Temporal trend analysis completed: slope={slope:.3f}")
            return {
                'dates': dates,
                'temperatures': temps,
                'trend_slope': slope,
                'trend_intercept': intercept
            }
        else:
            self.logger.warning("Insufficient data for temporal trend analysis")
            return None

    def _validate_with_ground_data(
        self,
        satellite_temps: gpd.GeoDataFrame,
        station_data: gpd.GeoDataFrame
    ) -> Dict:
        """Validate satellite temperatures with ground measurements."""
        self.logger.info("Validating satellite data with ground weather stations")
        
        # Spatial join between satellite grid and weather stations
        joined = gpd.sjoin_nearest(station_data, satellite_temps)

        # Calculate validation metrics
        rmse = np.sqrt(((joined.ground_temp - joined.satellite_temp) ** 2).mean())
        mae = np.abs(joined.ground_temp - joined.satellite_temp).mean()
        bias = (joined.satellite_temp - joined.ground_temp).mean()

        self.logger.info(f"Ground validation completed: RMSE={rmse:.2f}°C, MAE={mae:.2f}°C, Bias={bias:.2f}°C")
        return {
            'rmse': rmse,
            'mae': mae,
            'bias': bias,
            'correlation': joined.ground_temp.corr(joined.satellite_temp)
        }

    def _generate_recommendations(self, results: Dict) -> List[Dict]:
        """Generate mitigation recommendations based on analysis results."""
        self.logger.info("Generating mitigation recommendations")
        recommendations = []

        # Analyze hot spots
        if len(results['hot_spots']) > 0:
            recommendations.append({
                'type': 'hot_spot_mitigation',
                'description': 'Increase green coverage in identified hot spots',
                'priority': 'high',
                'locations': results['hot_spots'].geometry.to_json()
            })

        # Analyze land use correlations
        if 'impervious_surface' in results['land_use_correlation']['correlations']:
            corr = results['land_use_correlation']['correlations']['impervious_surface']
            if corr['correlation'] > UHI_CORRELATION_THRESHOLD:
                recommendations.append({
                    'type': 'surface_modification',
                    'description': 'Implement cool roofs and permeable pavements',
                    'priority': 'medium'
                })

        self.logger.info(f"Generated {len(recommendations)} mitigation recommendations")
        return recommendations

    def visualize_results(
        self,
        results: Dict,
        output_path: Optional[str] = None
    ) -> None:
        """Create visualization of heat island analysis results."""
        self.logger.info("Creating visualization of analysis results")
        
        fig, axes = plt.subplots(2, 2, figsize=UHI_VISUALIZATION_FIGSIZE)

        # Plot temperature distribution
        sns.histplot(
            data=results['temperature_statistics'],
            x='temperature',
            ax=axes[0, 0]
        )
        axes[0, 0].set_title('Temperature Distribution')

        # Plot land use correlation
        stats = pd.DataFrame(results['land_use_correlation']['statistics'])
        sns.barplot(
            data=stats,
            x='landuse_type',
            y=('temperature', 'mean'),
            ax=axes[0, 1]
        )
        axes[0, 1].set_title('Temperature by Land Use')

        # Plot hot spots
        results['hot_spots'].plot(
            column='temperature',
            cmap=UHI_TEMPERATURE_COLORMAP,
            ax=axes[1, 0]
        )
        axes[1, 0].set_title('Heat Island Hot Spots')

        # Plot temporal trends if available
        if results['temporal_trends']:
            dates = pd.to_datetime(results['temporal_trends']['dates'])
            temps = results['temporal_trends']['temperatures']
            axes[1, 1].plot(dates, temps)
            axes[1, 1].set_title('Temperature Trends')

        plt.tight_layout()
        if output_path:
            plt.savefig(output_path, dpi=UHI_VISUALIZATION_DPI, bbox_inches='tight')
            self.logger.info(f"Visualization saved to: {output_path}")
        else:
            plt.show()
            self.logger.info("Visualization displayed")

