#!/usr/bin/env python3
"""
DWD Weather Data Downloader - Lädt Wetterdaten basierend auf Geometrie und Zeitpunkt.
"""

import logging
from datetime import datetime, timedelta
from typing import Union, Dict, Any
import geopandas as gpd
import pandas as pd
import polars as pl
from shapely.geometry import Point, Polygon, MultiPolygon, shape
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import griddata
from shapely.ops import unary_union

from wetterdienst import Settings
from wetterdienst.provider.dwd.observation import DwdObservationRequest

from ..config.settings import (
    DWD_SETTINGS, DWD_TEMPERATURE_PARAMETERS,
    DWD_BUFFER_DISTANCE, DWD_INTERPOLATION_RESOLUTION, 
    DWD_INTERPOLATION_METHOD, DWD_INTERPOLATE_BY_DEFAULT
)

# Logging konfigurieren
logger = logging.getLogger(__name__)


class BerlinWeatherService:
    """
    Service zum Abrufen von Wetterdaten basierend auf Geometrie und Zeitpunkt.
    """
    
    def __init__(self, buffer_distance: float = None, interpolation_method: str = None):
        """
        Initialisiert den Weather Service.
        
        Args:
            buffer_distance: Optionaler Buffer in Metern (Standard aus Config)
            interpolation_method: Optionaler Interpolationsmethode (Standard aus Config)
        """
        # Settings mit den Projekt-Konfigurationen erstellen
        settings_kwargs = {
            "ts_shape": DWD_SETTINGS["ts_shape"],
            "ts_humanize": DWD_SETTINGS["ts_humanize"],
            "ts_convert_units": DWD_SETTINGS["ts_convert_units"],
        }
        self.settings = Settings(**settings_kwargs)
        
        # Buffer und Interpolationsmethode setzen
        self.buffer_distance = buffer_distance or DWD_BUFFER_DISTANCE
        self.interpolation_method = interpolation_method or DWD_INTERPOLATION_METHOD
    
    def _create_geometry_from_geojson(self, geojson: Union[str, Dict[str, Any]]) -> Union[Point, Polygon, MultiPolygon]:
        """
        Erstellt eine Shapely-Geometrie aus GeoJSON.
        
        Args:
            geojson: GeoJSON als String oder Dictionary
            
        Returns:
            Shapely-Geometrie
        """
        if isinstance(geojson, str):
            geojson = json.loads(geojson)
        
        return shape(geojson)
    
    def _get_bounding_box_from_geometry(self, geometry: Union[Point, Polygon, MultiPolygon]) -> Dict[str, float]:
        """
        Erstellt eine Bounding Box aus einer Geometrie.
        
        Args:
            geometry: Shapely-Geometrie
            
        Returns:
            Dictionary mit min/max Koordinaten
        """
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
        Erstellt ein regelmäßiges Raster für die Interpolation.
        
        Args:
            geometry: Shapely-Geometrie
            resolution: Auflösung des Rasters in Metern
            
        Returns:
            GeoDataFrame mit Rasterpunkten
        """
        # Bounding Box der Geometrie
        bounds = geometry.bounds
        
        # Raster erstellen (in Grad, grobe Näherung: 1 Grad ≈ 111km)
        lat_step = resolution / 111000  # Grad pro Meter
        lon_step = resolution / (111000 * np.cos(np.radians((bounds[1] + bounds[3]) / 2)))
        
        # Rasterpunkte generieren
        lats = np.arange(bounds[1], bounds[3] + lat_step, lat_step)
        lons = np.arange(bounds[0], bounds[2] + lon_step, lon_step)
        
        # Alle Kombinationen erstellen
        grid_points = []
        for lat in lats:
            for lon in lons:
                point = Point(lon, lat)
                if geometry.contains(point):
                    grid_points.append(point)
        
        # Als GeoDataFrame
        grid_gdf = gpd.GeoDataFrame(
            geometry=grid_points,
            crs="EPSG:4326"
        )
        
        logger.info(f"Interpolationsraster erstellt: {len(grid_gdf)} Punkte mit {resolution}m Auflösung")
        return grid_gdf
    
    def _interpolate_temperature(self, stations_gdf: gpd.GeoDataFrame, 
                               target_gdf: gpd.GeoDataFrame,
                               method: str = 'linear') -> gpd.GeoDataFrame:
        """
        Interpoliert Temperaturdaten von Wetterstationen auf ein Raster.
        
        Args:
            stations_gdf: GeoDataFrame mit Stationsdaten (bereits gefiltert für Zielzeitpunkt)
            target_gdf: GeoDataFrame mit Zielpunkten
            method: Interpolationsmethode ('linear', 'nearest', 'cubic')
            
        Returns:
            GeoDataFrame mit interpolierten Temperaturen
        """
        if len(stations_gdf) < 3:
            logger.warning("Zu wenige Stationen für Interpolation. Verwende Nearest Neighbor.")
            method = 'nearest'
        
        # Koordinaten der Stationen
        station_coords = np.array([
            stations_gdf.geometry.x.values,
            stations_gdf.geometry.y.values
        ]).T
        
        # Temperaturwerte (direkt verwenden, keine Durchschnittsbildung)
        station_temps = stations_gdf['value'].values
        
        # Koordinaten der Zielpunkte
        target_coords = np.array([
            target_gdf.geometry.x.values,
            target_gdf.geometry.y.values
        ]).T
        
        # Interpolation
        interpolated_temps = griddata(
            station_coords, 
            station_temps, 
            target_coords, 
            method=method,
            fill_value=np.nan
        )
        
        # Ergebnis-GeoDataFrame
        result_gdf = target_gdf.copy()
        result_gdf['ground_temp'] = interpolated_temps
        
        # NaN-Werte mit Nearest Neighbor füllen
        if np.any(np.isnan(result_gdf['ground_temp'])):
            logger.info("Fülle NaN-Werte mit Nearest Neighbor Interpolation")
            nan_mask = np.isnan(result_gdf['ground_temp'])
            if np.any(nan_mask):
                nearest_temps = griddata(
                    station_coords, 
                    station_temps, 
                    target_coords[nan_mask], 
                    method='nearest'
                )
                result_gdf.loc[nan_mask, 'ground_temp'] = nearest_temps
        
        logger.info(f"Temperaturinterpolation abgeschlossen: {len(result_gdf)} Punkte")
        return result_gdf
    
    def _get_stations_in_area(self, geometry: Union[Point, Polygon, MultiPolygon]) -> gpd.GeoDataFrame:
        """
        Ruft alle Wetterstationen in einem Gebiet ab.
        
        Args:
            geometry: Shapely-Geometrie
            
        Returns:
            GeoDataFrame mit Stationsdaten
        """
        # Buffer um die Geometrie hinzufügen
        buffered_geometry = geometry.buffer(self.buffer_distance / 111000)  # Konvertiere Meter zu Grad
        logger.info(f"Geometrie mit {self.buffer_distance}m Buffer erweitert")
        
        # Bounding Box aus erweiterter Geometrie erstellen
        bbox = self._get_bounding_box_from_geometry(buffered_geometry)
        logger.info(f"Bounding Box: {bbox}")
        
        # Request für stündliche Temperaturdaten erstellen
        request = DwdObservationRequest(
            parameters=DWD_TEMPERATURE_PARAMETERS,
            start_date="2024-01-01",  # Kurzer Zeitraum für Stationssuche
            end_date="2024-01-02",
            settings=self.settings,
        )
        
        # Alle Stationen abrufen
        stations_df = request.all().df
        
        if stations_df.is_empty():
            logger.error("Keine Stationen verfügbar!")
            return gpd.GeoDataFrame()
        
        # Stationen innerhalb der Bounding Box filtern
        stations_in_bbox = stations_df.filter(
            (stations_df["latitude"] >= bbox['min_lat']) &
            (stations_df["latitude"] <= bbox['max_lat']) &
            (stations_df["longitude"] >= bbox['min_lon']) &
            (stations_df["longitude"] <= bbox['max_lon'])
        )
        
        if stations_in_bbox.is_empty():
            logger.error("Keine Stationen in der Bounding Box verfügbar!")
            return gpd.GeoDataFrame()
        
        # Als GeoDataFrame konvertieren
        # CRS der Geometrie ermitteln (Standard: WGS84 falls nicht definiert)
        geometry_crs = getattr(geometry, 'crs', "EPSG:4326")
        
        stations_gdf = gpd.GeoDataFrame(
            stations_in_bbox.to_pandas(),
            geometry=gpd.points_from_xy(
                stations_in_bbox["longitude"],
                stations_in_bbox["latitude"]
            ),
            crs=geometry_crs
        )
        
        # Stationen innerhalb der erweiterten Geometrie filtern
        if buffered_geometry is not None:
            # Geometrie in das gleiche CRS wie die Stationen konvertieren falls nötig
            if geometry_crs != stations_gdf.crs:
                buffered_geometry = buffered_geometry.to_crs(stations_gdf.crs)
            
            # Stationen innerhalb der Geometrie filtern
            stations_in_geometry = stations_gdf[stations_gdf.geometry.within(buffered_geometry)]
            
            if stations_in_geometry.empty:
                logger.error("Keine Stationen innerhalb der erweiterten Geometrie gefunden!")
                return gpd.GeoDataFrame()
            
            stations_gdf = stations_in_geometry
        
        return stations_gdf
    
    def _get_temperature_data(self, station_ids: list, start_time: datetime, end_time: datetime) -> gpd.GeoDataFrame:
        """
        Ruft Temperaturdaten für gegebene Stationen und Zeitraum ab.
        
        Args:
            station_ids: Liste der Stations-IDs
            start_time: Startzeitpunkt
            end_time: Endzeitpunkt
            
        Returns:
            GeoDataFrame mit Temperaturdaten
        """
        logger.info(f"Lade Temperaturdaten für {len(station_ids)} Stationen "
                   f"von {start_time} bis {end_time}")
        
        # Request für Temperaturdaten erstellen
        temp_request = DwdObservationRequest(
            parameters=DWD_TEMPERATURE_PARAMETERS,
            start_date=start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_date=end_time.strftime("%Y-%m-%d %H:%M:%S"),
            settings=self.settings,
        ).filter_by_station_id(station_id=station_ids)
        
        # Temperaturdaten abrufen
        values_df = temp_request.values.all().df
        
        if values_df.is_empty():
            logger.error("Keine Temperaturdaten verfügbar!")
            return gpd.GeoDataFrame()
        
        # Als Pandas DataFrame konvertieren
        values_pandas = values_df.to_pandas()
        
        return values_pandas
    
    def _find_closest_measurements(
        self, 
        stations_gdf: gpd.GeoDataFrame, 
        target_timestamp: datetime
    ) -> gpd.GeoDataFrame:
        """
        Findet für jede Station die Messung, die am nächsten am Zielzeitpunkt liegt.
        
        Args:
            stations_gdf: GeoDataFrame mit allen Stationsmessungen
            target_timestamp: Zielzeitpunkt
            
        Returns:
            GeoDataFrame mit einer Messung pro Station (nächste zum Zielzeitpunkt)
        """
        closest_measurements = []
        
        for station_id in stations_gdf['station_id'].unique():
            station_data = stations_gdf[stations_gdf['station_id'] == station_id]
            
            # Zeitdifferenz zu jedem Messzeitpunkt berechnen
            station_data = station_data.copy()
            
            # Datetime-Objekte konvertieren und Zeitzonen behandeln
            station_dates = pd.to_datetime(station_data['date'])
            
            # Falls station_dates Zeitzonen haben, target_timestamp auch mit Zeitzone versehen
            if station_dates.dt.tz is not None:
                # Target timestamp mit gleicher Zeitzone versehen
                target_tz_aware = target_timestamp.replace(tzinfo=station_dates.dt.tz)
            else:
                # Falls keine Zeitzonen, beide zeitzonenfrei machen
                station_dates = station_dates.dt.tz_localize(None)
                target_tz_aware = target_timestamp
            
            station_data['time_diff'] = abs(station_dates - target_tz_aware)
            
            # Messung mit minimaler Zeitdifferenz finden
            closest_idx = station_data['time_diff'].idxmin()
            closest_measurement = station_data.loc[closest_idx]
            
            # Zeitdifferenz in Minuten für Logging
            time_diff_minutes = closest_measurement['time_diff'].total_seconds() / 60
            
            logger.info(f"Station {station_id}: Nächste Messung um {closest_measurement['date']} "
                       f"(Differenz: {time_diff_minutes:.1f} Minuten)")
            
            closest_measurements.append(closest_measurement)
        
        # Als GeoDataFrame zusammenfassen
        result_gdf = gpd.GeoDataFrame(
            closest_measurements,
            crs=stations_gdf.crs
        )
        
        # Zeitdifferenz-Spalte entfernen
        if 'time_diff' in result_gdf.columns:
            result_gdf = result_gdf.drop('time_diff', axis=1)
        
        return result_gdf
    
    def get_weather_data(
        self,
        geometry: Union[Point, Polygon, MultiPolygon, str, Dict[str, Any]],
        timestamp: datetime,
        interpolate: bool = None,
        resolution: float = None
    ) -> gpd.GeoDataFrame:
        """
        Ruft Temperaturdaten für einen spezifischen Zeitpunkt ab.
        
        Args:
            geometry: Shapely-Geometrie oder GeoJSON (String/Dict)
            timestamp: Spezifischer Zeitpunkt für die Datenabfrage
            interpolate: Ob die Daten interpoliert werden sollen (Standard aus Config)
            resolution: Auflösung des Interpolationsrasters in Metern (Standard aus Config)
            
        Returns:
            GeoDataFrame mit Temperaturdaten für den spezifischen Zeitpunkt
        """
        # Config-Werte als Standard verwenden
        if interpolate is None:
            interpolate = DWD_INTERPOLATE_BY_DEFAULT
        if resolution is None:
            resolution = DWD_INTERPOLATION_RESOLUTION
            
        logger.info(f"Lade Wetterdaten für Geometrie und Zeitpunkt {timestamp}")
        logger.info(f"Buffer: {self.buffer_distance}m, Auflösung: {resolution}m, Interpolation: {interpolate}")
        
        # GeoJSON zu Shapely-Geometrie konvertieren falls nötig
        if isinstance(geometry, (str, dict)):
            geometry = self._create_geometry_from_geojson(geometry)
        
        # Stationen im Gebiet finden
        stations_gdf = self._get_stations_in_area(geometry)
        
        if stations_gdf.empty:
            return gpd.GeoDataFrame()
        
        # Stations-IDs extrahieren
        station_ids = stations_gdf["station_id"].tolist()
        
        # Tag für die DWD-Abfrage bestimmen
        date = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = date
        end_time = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Temperaturdaten abrufen
        values_pandas = self._get_temperature_data(station_ids, start_time, end_time)
        
        if values_pandas.empty:
            return gpd.GeoDataFrame()
        
        # Mit Stationsdaten zusammenführen
        result_gdf = stations_gdf.merge(
            values_pandas,
            left_on="station_id",
            right_on="station_id",
            how="inner"
        )
        
        # Spalten bereinigen und sortieren
        columns_to_keep = [
            "station_id", "name", "latitude", "longitude", "height",
            "geometry", "date", "value", "quality", "parameter"
        ]
        
        result_gdf = result_gdf[columns_to_keep]
        
        # Nach Stations-ID und Datum sortieren
        result_gdf = result_gdf.sort_values(["station_id", "date"])
        
        logger.info(f"Erfolgreich: {len(result_gdf)} Temperaturmessungen für "
                   f"{len(result_gdf['station_id'].unique())} Stationen")
        
        # Nächste Messung zum Zielzeitpunkt für jede Station finden
        logger.info(f"Suche nächste Messungen zum Zeitpunkt {timestamp}")
        timestamp_data = self._find_closest_measurements(result_gdf, timestamp)
        
        if timestamp_data.empty:
            logger.error("Keine Messungen in der Nähe des Zielzeitpunkts gefunden!")
            return gpd.GeoDataFrame()
        
        logger.info(f"Gefunden: {len(timestamp_data)} Messungen nahe {timestamp}")
        
        # Interpolation durchführen falls gewünscht
        if interpolate and len(timestamp_data) > 0:
            logger.info("Starte Temperaturinterpolation...")
            
            # Interpolationsraster erstellen
            grid_gdf = self._create_interpolation_grid(geometry, resolution)
            
            # Interpolation durchführen
            interpolated_gdf = self._interpolate_temperature(timestamp_data, grid_gdf, self.interpolation_method)
            
            # Zusätzliche Metadaten hinzufügen
            interpolated_gdf['date'] = timestamp
            interpolated_gdf['source'] = 'interpolated_ground_data'
            interpolated_gdf['n_stations'] = len(timestamp_data['station_id'].unique())
            interpolated_gdf['resolution_m'] = resolution
            interpolated_gdf['target_timestamp'] = timestamp
            
            logger.info(f"Interpolation abgeschlossen: {len(interpolated_gdf)} Punkte erstellt")
            return interpolated_gdf
        
        return timestamp_data 