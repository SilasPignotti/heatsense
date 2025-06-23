"""
WFS-Downloader Klasse für verschiedene Geodatendienste.

Diese Klasse ermöglicht das einfache Herunterladen von Geodaten über WFS-Services
mit konfigurierbaren Endpunkten und verschiedenen Ausgabeformaten.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from urllib.parse import urlencode
import requests
import geopandas as gpd
from datetime import datetime


class WFSDownloader:
    """
    Klasse zum Download von Geodaten über WFS-Services.
    
    Attributes:
        config: WFS-Konfiguration mit Endpunkten
        headers: HTTP-Headers für Requests
        timeout: Timeout für HTTP-Requests
        logger: Logger-Instanz
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        log_file: Optional[Path] = None
    ):
        """
        Initialisiert den WFS-Downloader.
        
        Args:
            config: WFS-Konfiguration (aus wfs_config.py)
            headers: Optionale HTTP-Headers
            timeout: Timeout in Sekunden
            log_file: Optionaler Pfad für Log-Datei
        """
        self.config = config
        self.timeout = timeout
        self.logger = self._setup_logger(log_file)
        
        # Standard-Headers falls keine angegeben
        self.headers = headers or {
            "User-Agent": "Urban-Heat-Island-Analyzer/1.0",
            "Accept": "application/json,application/geojson"
        }
    
    def _setup_logger(self, log_file: Optional[Path] = None) -> logging.Logger:
        """Richtet den Logger ein."""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        logger.setLevel(logging.INFO)
        
        # Handler für Konsole
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Handler für Datei (falls angegeben)
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
    
    def build_wfs_url(self, endpoint_name: str, **kwargs) -> str:
        """
        Baut die WFS-URL mit den entsprechenden Parametern.
        
        Args:
            endpoint_name: Name des Endpunkts aus der Konfiguration
            **kwargs: Zusätzliche Parameter für die URL
            
        Returns:
            Vollständige WFS-URL
            
        Raises:
            KeyError: Wenn Endpunkt nicht in Konfiguration gefunden
        """
        if endpoint_name not in self.config:
            raise KeyError(f"Endpunkt '{endpoint_name}' nicht in Konfiguration gefunden")
        
        endpoint_config = self.config[endpoint_name]
        
        # Basis-Parameter
        params = {
            'service': endpoint_config['service'],
            'version': endpoint_config['version'],
            'request': endpoint_config['request'],
            'typeNames': endpoint_config['typeName'],
            'outputFormat': endpoint_config['outputFormat'],
            'srsName': endpoint_config['srsName']
        }
        
        # Zusätzliche Parameter hinzufügen
        params.update(kwargs)
        
        return f"{endpoint_config['url']}?{urlencode(params)}"
    
    def download_data(
        self,
        endpoint_name: str,
        output_path: Union[str, Path],
        **kwargs
    ) -> bool:
        """
        Lädt Daten vom WFS-Service herunter und speichert sie.
        
        Args:
            endpoint_name: Name des Endpunkts aus der Konfiguration
            output_path: Pfad für die Ausgabedatei
            **kwargs: Zusätzliche Parameter für die WFS-URL
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # WFS-URL bauen
            wfs_url = self.build_wfs_url(endpoint_name, **kwargs)
            self.logger.info(f"Lade Daten von: {wfs_url}")
            
            # Daten herunterladen
            response = requests.get(
                wfs_url,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Prüfe Content-Type
            content_type = response.headers.get('content-type', '')
            if 'json' in content_type or 'geojson' in content_type:
                # Als GeoJSON speichern
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                self.logger.info(f"Daten erfolgreich gespeichert: {output_path}")
                return True
            else:
                self.logger.error(f"Unerwartetes Antwortformat: {content_type}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Fehler beim Download: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler: {e}")
            return False
    
    def validate_geojson(self, file_path: Union[str, Path]) -> bool:
        """
        Validiert eine GeoJSON-Datei.
        
        Args:
            file_path: Pfad zur GeoJSON-Datei
            
        Returns:
            True wenn gültig, False sonst
        """
        try:
            gdf = gpd.read_file(file_path)
            self.logger.info(f"GeoJSON validiert: {len(gdf)} Features gefunden")
            self.logger.info(f"CRS: {gdf.crs}")
            return True
        except Exception as e:
            self.logger.error(f"GeoJSON-Validierung fehlgeschlagen: {e}")
            return False
    
    def download_and_validate(
        self,
        endpoint_name: str,
        output_path: Union[str, Path],
        validate: bool = True,
        **kwargs
    ) -> bool:
        """
        Lädt Daten herunter und validiert sie optional.
        
        Args:
            endpoint_name: Name des Endpunkts aus der Konfiguration
            output_path: Pfad für die Ausgabedatei
            validate: Ob GeoJSON validiert werden soll
            **kwargs: Zusätzliche Parameter für die WFS-URL
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        # Daten herunterladen
        if not self.download_data(endpoint_name, output_path, **kwargs):
            return False
        
        # Optional validieren
        if validate:
            if not self.validate_geojson(output_path):
                return False
        
        return True
    
    def get_available_endpoints(self) -> list:
        """
        Gibt alle verfügbaren Endpunkte zurück.
        
        Returns:
            Liste der Endpunkt-Namen
        """
        return list(self.config.keys())
    
    def get_endpoint_info(self, endpoint_name: str) -> Dict[str, Any]:
        """
        Gibt Informationen zu einem Endpunkt zurück.
        
        Args:
            endpoint_name: Name des Endpunkts
            
        Returns:
            Endpunkt-Konfiguration
            
        Raises:
            KeyError: Wenn Endpunkt nicht gefunden
        """
        if endpoint_name not in self.config:
            raise KeyError(f"Endpunkt '{endpoint_name}' nicht gefunden")
        
        return self.config[endpoint_name].copy() 