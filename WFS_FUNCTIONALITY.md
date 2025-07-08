# WFS-ähnliche Funktionalität für HeatSense Urban Heat Island Analyzer

## Übersicht

Die HeatSense-Anwendung bietet jetzt **WFS-ähnliche (Web Feature Service) Funktionalität** für den Download von Analyselayern. Diese ermöglicht es, die generierten räumlichen Daten in standardisierten Formaten herunterzuladen.

## Verfügbare Layer

Nach einer erfolgreichen Analyse stehen folgende Layer zum Download bereit:

### 1. **Temperatur-Layer** (`temperature`)
- **Beschreibung**: Räumliche Temperaturverteilung als Rasterzellen
- **Geometrie**: Polygon (Grid-Zellen)
- **Attribute**: Temperaturwerte in °C
- **Format**: GeoJSON

### 2. **Heat Islands** (`heat_islands`)
- **Beschreibung**: Identifizierte Wärmeinseln/Hotspots
- **Geometrie**: Polygon
- **Attribute**: Temperaturwerte, Hotspot-Intensität
- **Format**: GeoJSON

### 3. **Untersuchungsgebiet** (`boundary`)
- **Beschreibung**: Abgrenzung des analysierten Gebiets
- **Geometrie**: Polygon
- **Attribute**: Gebietsname, administrative Informationen
- **Format**: GeoJSON

## API-Endpunkte

### WFS Capabilities
```
GET /api/wfs/capabilities
```
Liefert Service-Metadaten und verfügbare Operationen.

**Beispiel Response:**
```json
{
  "service": "WFS",
  "version": "2.0.0",
  "title": "HeatSense Urban Heat Island Analysis Service",
  "feature_types": [
    {
      "name": "temperature",
      "title": "Temperatur-Layer",
      "srs": "EPSG:4326",
      "bbox": [13.0, 52.3, 13.8, 52.7]
    }
  ]
}
```

### Verfügbare Layer
```
GET /api/wfs/layers
```
Listet alle verfügbaren Layer mit Details auf.

**Beispiel Response:**
```json
{
  "layers": [
    {
      "name": "temperature",
      "title": "Temperatur-Layer",
      "description": "Räumliche Temperaturverteilung",
      "geometry_type": "Polygon",
      "srs": "EPSG:4326",
      "formats": ["geojson", "shapefile", "geopackage"]
    }
  ]
}
```

### Layer Download
```
GET /api/wfs/download/{layer_name}?format={format}&bbox={bbox}
```

**Parameter:**
- `layer_name`: Name des Layers (`temperature`, `heat_islands`, `boundary`)
- `format`: Ausgabeformat (aktuell: `geojson`)
- `bbox`: Bounding Box für räumliche Filterung (optional, Format: `minx,miny,maxx,maxy`)

**Beispiel:**
```bash
curl -X GET "http://localhost:8000/api/wfs/download/temperature?format=geojson" \
     -H "Cookie: session=your-session-cookie"
```

## Nutzung in der Web-Anwendung

### 1. Analyse durchführen
- Führe eine normale Urban Heat Island Analyse durch
- Warte auf die Fertigstellung der Analyse

### 2. WFS-Layer herunterladen
- Nach erfolgreicher Analyse erscheint der **"WFS-Layer"** Button neben dem JSON-Download
- Klicke auf den Button, um das Dropdown-Menü zu öffnen
- Wähle den gewünschten Layer aus:
  - **Temperatur-Layer** → GeoJSON
  - **Heat Islands** → GeoJSON
  - **Untersuchungsgebiet** → GeoJSON

### 3. Datei wird automatisch heruntergeladen
- Die Datei wird mit einem aussagekräftigen Namen gespeichert
- Format: `{layer_name}_{area}.{format}`
- Beispiel: `temperature_Kreuzberg.geojson`

## Verwendung der heruntergeladenen Daten

### In QGIS
1. QGIS öffnen
2. **Layer** → **Layer hinzufügen** → **Vektorlayer hinzufügen**
3. Heruntergeladene GeoJSON-Datei auswählen
4. Layer wird mit korrekten Attributen und Geometrien geladen

### In Python/GeoPandas
```python
import geopandas as gpd

# GeoJSON-Datei laden
gdf = gpd.read_file('temperature_Kreuzberg.geojson')

# Daten anzeigen
print(gdf.head())
print(f"CRS: {gdf.crs}")
print(f"Geometrie-Typ: {gdf.geometry.type.iloc[0]}")

# Schnelle Visualisierung
gdf.plot(column='temperature', cmap='coolwarm', legend=True)
```

### In ArcGIS
1. ArcGIS Pro öffnen
2. **Map** → **Add Data** → **Data**
3. GeoJSON-Datei auswählen
4. Layer wird automatisch in korrekter Projektion geladen

## Technische Details

### Datenformat
- **Koordinatensystem**: EPSG:4326 (WGS84)
- **Encoding**: UTF-8
- **Geometrie**: Valide GeoJSON-Polygone
- **Attribute**: Numerische Werte und Strings

### Session-Management
- Layer-Downloads sind an aktive Sessions gebunden
- Nach einer Analyse sind die Daten temporär verfügbar
- Automatische Cleanup-Routinen entfernen alte Dateien

### Performance
- Effiziente Speicherung als temporäre Dateien
- Direkte GeoJSON-Serialisierung ohne Zwischenschritte
- Optimierte Dateigrößen durch präzise Koordinaten

## Zukünftige Erweiterungen

### Geplante Formate
- **Shapefile** (.shp + Begleitdateien)
- **GeoPackage** (.gpkg)
- **KML/KMZ** für Google Earth
- **CSV mit WKT-Geometrien**

### Erweiterte Filterung
- Räumliche Filterung mit Bounding Box
- Attributbasierte Filterung
- Zeitbasierte Filterung für Zeitreihen

### Bulk-Downloads
- ZIP-Archive mit allen Layern
- Batch-Downloads mehrerer Formate
- Metadaten-Dateien (XML, JSON)

## Beispiel-Workflow

1. **Analyse starten**
   ```
   Gebiet: Friedrichshain-Kreuzberg
   Zeitraum: 01.06.2025 - 30.06.2025
   Modus: Standard
   ```

2. **Nach Analyse-Abschluss**
   - JSON-Download für vollständige Ergebnisse
   - WFS-Layer für einzelne Geo-Datensätze

3. **Layer-Download**
   ```
   Temperatur-Layer → temperature_Friedrichshain-Kreuzberg.geojson
   Heat Islands → heat_islands_Friedrichshain-Kreuzberg.geojson
   Boundary → boundary_Friedrichshain-Kreuzberg.geojson
   ```

4. **Weiterverarbeitung**
   - Import in GIS-Software
   - Weitere Analyse mit Python/R
   - Integration in bestehende Workflows

## Fehlerbehebung

### "No analysis results available"
- Führe zuerst eine Analyse durch
- Stelle sicher, dass die Analyse erfolgreich abgeschlossen wurde
- Verwende die gleiche Browser-Session

### Leere Downloads
- Prüfe, ob der Layer-Name korrekt ist
- Überprüfe die Analyse-Ergebnisse auf Vollständigkeit
- Schaue in die Browser-Konsole für Fehlermeldungen

### Formatierungsprobleme
- Stelle sicher, dass deine GIS-Software GeoJSON unterstützt
- Überprüfe die Koordinaten-Projektion (EPSG:4326)
- Validiere die GeoJSON-Struktur online

## Support

Bei Problemen oder Fragen zur WFS-Funktionalität:
1. Überprüfe die Browser-Konsole auf Fehlermeldungen
2. Stelle sicher, dass die neueste Version läuft
3. Teste mit dem bereitgestellten Test-Skript: `python test_wfs_functionality.py` 