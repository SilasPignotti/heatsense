#!/usr/bin/env python3
"""
Berlin Weather Data Downloader - Lädt und interpoliert Temperaturdaten für Berlin.
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
import sys
import matplotlib.pyplot as plt

# Projekt-Pfad hinzufügen
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from uhi_analyzer.data.dwd_downloader import BerlinWeatherService
from uhi_analyzer.config.settings import (
    DWD_BUFFER_DISTANCE, DWD_INTERPOLATION_RESOLUTION, 
    DWD_INTERPOLATE_BY_DEFAULT
)

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_berlin_geometry() -> dict:
    """
    Lädt die Berlin-Geometrie aus der GeoJSON-Datei und gibt das Geometrie-Objekt zurück.
    
    Returns:
        dict: Die Geometrie von Berlin als GeoJSON-Objekt
    """
    import json
    berlin_geojson_path = Path("data/raw/boundaries/berlin_admin_boundaries.geojson")
    
    if not berlin_geojson_path.exists():
        raise FileNotFoundError(f"Berlin-Geometrie nicht gefunden: {berlin_geojson_path}")
    
    with open(berlin_geojson_path, 'r', encoding='utf-8') as f:
        geojson = json.load(f)
        # FeatureCollection: nehme die Geometrie des ersten Features
        if geojson.get("type") == "FeatureCollection":
            return geojson['features'][0]['geometry']
        # Direkte Geometrie
        elif geojson.get("type") in ["Polygon", "MultiPolygon"]:
            return geojson
        else:
            raise ValueError(f"Unerwarteter GeoJSON-Typ: {geojson.get('type')}")


def download_berlin_weather_data(
    date: datetime, 
    output_dir: str = "data/processed/weather",
    buffer_distance: float = None,
    resolution: float = None,
    interpolate: bool = None
) -> None:
    """
    Lädt und interpoliert Temperaturdaten für Berlin für einen ganzen Tag.
    
    Args:
        date: Datum für die Datenabfrage
        output_dir: Ausgabeverzeichnis für die Daten
        buffer_distance: Buffer-Distanz in Metern um Berlin zu erweitern (Standard aus Config)
        resolution: Auflösung des Interpolationsrasters in Metern (Standard aus Config)
        interpolate: Ob die Daten interpoliert werden sollen (Standard aus Config)
    """
    # Config-Werte als Standard verwenden
    if buffer_distance is None:
        buffer_distance = DWD_BUFFER_DISTANCE
    if resolution is None:
        resolution = DWD_INTERPOLATION_RESOLUTION
    if interpolate is None:
        interpolate = DWD_INTERPOLATE_BY_DEFAULT
        
    logger.info(f"Starte Download der Berlin-Temperaturdaten für {date.date()}")
    logger.info(f"Buffer: {buffer_distance}m, Auflösung: {resolution}m, Interpolation: {interpolate}")
    
    # Ausgabeverzeichnis erstellen
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Berlin-Geometrie laden
    try:
        berlin_geometry = load_berlin_geometry()
        logger.info("Berlin-Geometrie erfolgreich geladen")
    except Exception as e:
        logger.error(f"Fehler beim Laden der Berlin-Geometrie: {e}")
        return
    
    # Weather Service initialisieren
    try:
        weather_service = BerlinWeatherService(buffer_distance=buffer_distance)
        logger.info("Weather Service erfolgreich initialisiert")
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung des Weather Service: {e}")
        return
    
    # Wetterdaten abrufen
    try:
        weather_data = weather_service.get_weather_data(
            geometry=berlin_geometry,
            date=date,
            interpolate=interpolate,
            resolution=resolution
        )
        
        if weather_data.empty:
            logger.error("Keine Wetterdaten erhalten!")
            return
        
        logger.info(f"Wetterdaten erfolgreich abgerufen: {len(weather_data)} Datensätze")
        
        # Ausgabedatei erstellen
        date_str = date.strftime("%Y%m%d")
        if interpolate:
            filename = f"berlin_temperature_interpolated_{date_str}.geojson"
        else:
            filename = f"berlin_temperature_stations_{date_str}.geojson"
        
        output_file = output_path / filename
        
        # Als GeoJSON speichern
        weather_data.to_file(output_file, driver="GeoJSON")
        
        logger.info(f"Wetterdaten erfolgreich gespeichert: {output_file}")
        
        # Statistiken ausgeben
        if interpolate:
            logger.info(f"Interpolierte Daten: {len(weather_data)} Punkte")
            logger.info(f"Temperaturbereich: {weather_data['ground_temp'].min():.1f}°C - {weather_data['ground_temp'].max():.1f}°C")
            logger.info(f"Verwendete Stationen: {weather_data['n_stations'].iloc[0]}")
            logger.info(f"Auflösung: {weather_data['resolution_m'].iloc[0]}m")
        else:
            logger.info(f"Stationsdaten: {len(weather_data)} Messungen")
            logger.info(f"Stationen: {weather_data['station_id'].nunique()}")
            logger.info(f"Temperaturbereich: {weather_data['value'].min():.1f}°C - {weather_data['value'].max():.1f}°C")
        
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Wetterdaten: {e}")
        import traceback
        logger.error(traceback.format_exc())


def download_berlin_weather_data_for_timestamp(
    timestamp: datetime,
    output_dir: str = "data/processed/weather",
    buffer_distance: float = None,
    resolution: float = None,
    interpolate: bool = None
) -> None:
    """
    Lädt und interpoliert Temperaturdaten für Berlin für einen spezifischen Zeitpunkt.
    
    Args:
        timestamp: Spezifischer Zeitpunkt für die Interpolation
        output_dir: Ausgabeverzeichnis für die Daten
        buffer_distance: Buffer-Distanz in Metern um Berlin zu erweitern (Standard aus Config)
        resolution: Auflösung des Interpolationsrasters in Metern (Standard aus Config)
        interpolate: Ob die Daten interpoliert werden sollen (Standard aus Config)
    """
    # Config-Werte als Standard verwenden
    if buffer_distance is None:
        buffer_distance = DWD_BUFFER_DISTANCE
    if resolution is None:
        resolution = DWD_INTERPOLATION_RESOLUTION
    if interpolate is None:
        interpolate = DWD_INTERPOLATE_BY_DEFAULT
        
    logger.info(f"Starte Download der Berlin-Temperaturdaten für Zeitpunkt {timestamp}")
    logger.info(f"Buffer: {buffer_distance}m, Auflösung: {resolution}m, Interpolation: {interpolate}")
    
    # Ausgabeverzeichnis erstellen
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Berlin-Geometrie laden
    try:
        berlin_geometry = load_berlin_geometry()
        logger.info("Berlin-Geometrie erfolgreich geladen")
    except Exception as e:
        logger.error(f"Fehler beim Laden der Berlin-Geometrie: {e}")
        return
    
    # Weather Service initialisieren
    try:
        weather_service = BerlinWeatherService(buffer_distance=buffer_distance)
        logger.info("Weather Service erfolgreich initialisiert")
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung des Weather Service: {e}")
        return
    
    # Wetterdaten abrufen
    try:
        weather_data = weather_service.get_weather_data(
            geometry=berlin_geometry,
            timestamp=timestamp,
            interpolate=interpolate,
            resolution=resolution
        )
        
        if weather_data.empty:
            logger.error("Keine Wetterdaten erhalten!")
            return
        
        logger.info(f"Wetterdaten erfolgreich abgerufen: {len(weather_data)} Datensätze")
        
        # Ausgabedatei erstellen
        date_str = timestamp.strftime("%Y%m%d")
        time_str = timestamp.strftime("%H%M")
        
        if interpolate:
            filename = f"berlin_temperature_interpolated_{date_str}_{time_str}.geojson"
        else:
            filename = f"berlin_temperature_stations_{date_str}_{time_str}.geojson"
        
        output_file = output_path / filename
        
        # Als GeoJSON speichern
        weather_data.to_file(output_file, driver="GeoJSON")
        
        logger.info(f"Wetterdaten erfolgreich gespeichert: {output_file}")
        
        # Statistiken ausgeben
        if interpolate:
            logger.info(f"Interpolierte Daten: {len(weather_data)} Punkte")
            logger.info(f"Temperaturbereich: {weather_data['ground_temp'].min():.1f}°C - {weather_data['ground_temp'].max():.1f}°C")
            logger.info(f"Verwendete Stationen: {weather_data['n_stations'].iloc[0]}")
            logger.info(f"Auflösung: {weather_data['resolution_m'].iloc[0]}m")
            logger.info(f"Zielzeitpunkt: {weather_data['target_timestamp'].iloc[0]}")
        else:
            logger.info(f"Stationsdaten: {len(weather_data)} Messungen")
            logger.info(f"Stationen: {weather_data['station_id'].nunique()}")
            logger.info(f"Temperaturbereich: {weather_data['value'].min():.1f}°C - {weather_data['value'].max():.1f}°C")
            logger.info(f"Messzeitpunkte: {weather_data['date'].unique()}")
        
        # Visualisierung
        try:
            fig, ax = plt.subplots(figsize=(8, 8))
            if interpolate:
                weather_data.plot(ax=ax, column='ground_temp', cmap='coolwarm', legend=True, markersize=30)
            else:
                weather_data.plot(ax=ax, column='value', cmap='coolwarm', legend=True, markersize=60, edgecolor='k')
            ax.set_title(f"Berlin Temperatur {timestamp.strftime('%Y-%m-%d %H:%M')}")
            ax.set_axis_off()
            plt.tight_layout()
            png_file = output_path / f"berlin_temperature_{date_str}_{time_str}.png"
            plt.savefig(png_file, dpi=150)
            plt.close(fig)
            logger.info(f"Visualisierung gespeichert: {png_file}")
        except Exception as e:
            logger.error(f"Fehler bei der Visualisierung: {e}")
        
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Wetterdaten: {e}")
        import traceback
        logger.error(traceback.format_exc())


def main():
    """Hauptfunktion für die Kommandozeile."""
    parser = argparse.ArgumentParser(
        description="Lädt und interpoliert Temperaturdaten für Berlin zu einem bestimmten Zeitpunkt"
    )
    parser.add_argument(
        "--timestamp",
        type=str,
        required=True,
        help="Spezifischer Zeitpunkt im Format YYYY-MM-DD HH:MM (z.B. 2024-01-15 12:00)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed/weather",
        help="Ausgabeverzeichnis (Standard: data/processed/weather)"
    )
    parser.add_argument(
        "--buffer",
        type=float,
        default=None,
        help=f"Buffer-Distanz in Metern (Standard aus Config: {DWD_BUFFER_DISTANCE}m)"
    )
    parser.add_argument(
        "--resolution",
        type=float,
        default=None,
        help=f"Auflösung des Interpolationsrasters in Metern (Standard aus Config: {DWD_INTERPOLATION_RESOLUTION}m)"
    )
    parser.add_argument(
        "--no-interpolate",
        action="store_true",
        help="Keine Interpolation durchführen, nur Stationsdaten"
    )
    
    args = parser.parse_args()
    
    # Zeitpunkt parsen
    try:
        timestamp = datetime.strptime(args.timestamp, "%Y-%m-%d %H:%M")
    except ValueError:
        logger.error("Ungültiges Zeitstempel-Format. Verwende YYYY-MM-DD HH:MM (z.B. 2024-01-15 12:00)")
        return
    
    # Download durchführen
    download_berlin_weather_data_for_timestamp(
        timestamp=timestamp,
        output_dir=args.output_dir,
        buffer_distance=args.buffer,
        resolution=args.resolution,
        interpolate=not args.no_interpolate
    )


if __name__ == "__main__":
    main() 