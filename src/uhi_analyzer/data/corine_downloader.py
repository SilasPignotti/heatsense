"""
CorineDownloader: Allgemeiner Downloader für Corine Land Cover Daten.
"""

import json
from pathlib import Path
from typing import List, Tuple, Union
from urllib.parse import urlencode
import logging
import requests
from pyproj import Transformer
import geopandas as gpd
from shapely.geometry import shape

from uhi_analyzer.config import (
    CORINE_BASE_URLS,
    CORINE_BASE_URL,
    DEFAULT_RECORD_COUNT,
    DEFAULT_TIMEOUT,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_OUTPUT_CRS,
    DEFAULT_INPUT_CRS,
    get_closest_corine_year
)

class CorineDownloader:
    """
    Allgemeiner Downloader für Corine Land Cover Daten.
    Unterstützt verschiedene Jahre (1990, 2000, 2006, 2012, 2018).
    """
    def __init__(self, target_year: int = 2018, logger: logging.Logger = None):
        """
        Initialisiert den CorineDownloader.
        
        Args:
            target_year: Gewünschtes Jahr für die Corine-Daten. 
                        Wird automatisch auf das nächstgelegene verfügbare Jahr gerundet.
            logger: Logger-Instanz (optional)
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Bestimme das nächstgelegene verfügbare Jahr
        self.selected_year = get_closest_corine_year(target_year)
        self.base_url = CORINE_BASE_URLS[self.selected_year]
        
        if self.selected_year != target_year:
            self.logger.info(f"Gewünschtes Jahr {target_year} nicht verfügbar. "
                           f"Verwende nächstgelegenes Jahr: {self.selected_year}")
        else:
            self.logger.info(f"Verwende Corine-Daten für Jahr: {self.selected_year}")
            
        self.logger.info(f"Base URL: {self.base_url}")

    @property
    def year(self) -> int:
        """Gibt das tatsächlich verwendete Jahr zurück."""
        return self.selected_year

    def get_bbox_from_geojson(self, geojson_path: Union[str, Path]) -> Tuple[float, float, float, float]:
        """
        Extrahiert die Bounding Box aus einer GeoJSON-Datei und transformiert sie in EPSG:3857.
        
        Args:
            geojson_path: Pfad zur GeoJSON-Datei
            
        Returns:
            Bounding Box als (xmin, ymin, xmax, ymax) in EPSG:3857
        """
        try:
            gdf = gpd.read_file(geojson_path)
            bbox_wgs84 = gdf.total_bounds  # (xmin, ymin, xmax, ymax)
            
            # Transformiere von WGS84 (EPSG:4326) zu Web Mercator (EPSG:3857)
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
            
            xmin, ymin = transformer.transform(bbox_wgs84[0], bbox_wgs84[1])
            xmax, ymax = transformer.transform(bbox_wgs84[2], bbox_wgs84[3])
            
            self.logger.info(f"Bounding Box extrahiert: {bbox_wgs84} (WGS84) -> ({xmin}, {ymin}, {xmax}, {ymax}) (EPSG:3857)")
            return (xmin, ymin, xmax, ymax)
            
        except Exception as e:
            self.logger.error(f"Fehler beim Lesen der GeoJSON-Datei: {e}")
            raise

    def build_query_url(self, bbox: Tuple[float, float, float, float], offset: int = 0) -> str:
        """
        Baut die Query-URL für die ArcGIS REST API.
        
        Args:
            bbox: Bounding Box als (xmin, ymin, xmax, ymax) in EPSG:3857
            offset: Offset für Paginierung
            
        Returns:
            Vollständige Query-URL
        """
        xmin, ymin, xmax, ymax = bbox
        params = {
            'f': DEFAULT_OUTPUT_FORMAT,
            'where': '1=1',
            'geometryType': 'esriGeometryEnvelope',
            'geometry': f'{xmin},{ymin},{xmax},{ymax}',
            'inSR': DEFAULT_INPUT_CRS,
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'true',
            'outSR': DEFAULT_OUTPUT_CRS,
            'resultRecordCount': DEFAULT_RECORD_COUNT,
            'resultOffset': offset
        }
        query_string = urlencode(params)
        return f"{self.base_url}/query?{query_string}"

    def download_for_area(self, geojson_path: Union[str, Path]) -> List[dict]:
        """
        Lädt Corine Land Cover Daten für ein bestimmtes Gebiet herunter.
        Verwendet Paginierung um alle verfügbaren Daten abzurufen.
        
        Args:
            geojson_path: Pfad zur GeoJSON-Datei des Gebiets
            
        Returns:
            Liste aller Features aus der API
        """
        bbox = self.get_bbox_from_geojson(geojson_path)
        all_features = []
        offset = 0
        total_requests = 0
        
        self.logger.info(f"Starte Download der Corine Land Cover Daten ({self.year}) für Gebiet: {geojson_path}")
        
        while True:
            url = self.build_query_url(bbox, offset)
            total_requests += 1
            self.logger.info(f"Request {total_requests}: Requesting data with offset {offset}...")
            
            try:
                response = requests.get(url, timeout=DEFAULT_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                
                if 'features' not in data:
                    self.logger.error(f"Unerwartetes Antwortformat: {data}")
                    break
                    
                features = data['features']
                self.logger.info(f"  {len(features)} Features geladen")
                all_features.extend(features)
                
                # Prüfe ob wir alle Daten haben
                if len(features) < DEFAULT_RECORD_COUNT:
                    self.logger.info(f"  Letzte Seite erreicht - alle Features abgerufen")
                    break
                
                # Prüfe auf exceededTransferLimit Flag
                if data.get('exceededTransferLimit', False):
                    self.logger.info(f"  exceededTransferLimit=True - weitere Daten verfügbar")
                    offset += DEFAULT_RECORD_COUNT
                else:
                    self.logger.info(f"  exceededTransferLimit=False - alle Daten abgerufen")
                    break
                    
            except Exception as e:
                self.logger.error(f"Fehler beim Download: {e}")
                break
        
        self.logger.info(f"Download abgeschlossen: {len(all_features)} Features in {total_requests} Requests")
        return all_features

    def download_and_save(self, geojson_path: Union[str, Path], output_path: Union[str, Path] = None) -> Path:
        """
        Lädt Corine Land Cover Daten für ein Gebiet herunter und speichert sie.
        Nach dem Download werden die Features exakt auf das Polygon geclippt.
        
        Args:
            geojson_path: Pfad zur GeoJSON-Datei des Gebiets
            output_path: Pfad für die Ausgabedatei (optional)
            
        Returns:
            Pfad zur gespeicherten Datei
        """
        if output_path is None:
            # Generiere Standard-Ausgabepfad
            input_path = Path(geojson_path)
            output_path = Path("data/raw/landcover") / f"{input_path.stem}_corine_landcover_{self.year}.geojson"
        output_path = Path(output_path)

        # Download der Daten (Bounding Box)
        features = self.download_for_area(geojson_path)

        # In GeoDataFrame umwandeln
        gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
        # Lade das Ziel-Polygon (z.B. Berlin)
        clip_poly = gpd.read_file(geojson_path)
        if clip_poly.crs != gdf.crs:
            clip_poly = clip_poly.to_crs(gdf.crs)
        # Clip auf Polygon
        gdf_clipped = gpd.overlay(gdf, clip_poly, how="intersection")
        self.logger.info(f"Features nach Polygon-Clip: {len(gdf_clipped)} (vorher: {len(gdf)})")

        # Speichern
        gdf_clipped.to_file(output_path, driver="GeoJSON")
        self.logger.info(f"GeoJSON gespeichert: {output_path}")
        self.logger.info(f"Download und Clipping erfolgreich abgeschlossen!")
        self.logger.info(f"Ausgabedatei: {output_path}")
        self.logger.info(f"Anzahl Features: {len(gdf_clipped)}")
        self.logger.info(f"Corine-Jahr: {self.year}")
        return output_path 