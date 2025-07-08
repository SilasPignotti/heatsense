# Upgrade-Plan: Von WFS-ähnlich zu vollständigem OGC WFS

## Aktueller Stand vs. OGC WFS 2.0

### ✅ Was bereits implementiert ist:
- REST-basierte Endpunkte
- Service-Metadaten (capabilities)
- Layer-Listing
- Feature-Downloads
- Räumliche Daten (GeoJSON)
- Session-Management

### ❌ Was für vollständigen OGC WFS fehlt:

## 1. XML-basierte Requests/Responses

### Aktuell:
```json
GET /api/wfs/capabilities
{
  "service": "WFS",
  "version": "2.0.0"
}
```

### OGC WFS Standard:
```xml
GET /wfs?service=WFS&request=GetCapabilities&version=2.0.0

<?xml version="1.0" encoding="UTF-8"?>
<wfs:WFS_Capabilities version="2.0.0">
  <ows:ServiceIdentification>
    <ows:Title>HeatSense WFS</ows:Title>
  </ows:ServiceIdentification>
</wfs:WFS_Capabilities>
```

## 2. GML-Ausgabeformat

### Aktuell (GeoJSON):
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Polygon", "coordinates": [...] },
      "properties": { "temperature": 25.3 }
    }
  ]
}
```

### OGC Standard (GML):
```xml
<wfs:FeatureCollection>
  <gml:featureMember>
    <uhi:Temperature gml:id="temp.1">
      <uhi:geometry>
        <gml:Polygon>
          <gml:exterior>
            <gml:LinearRing>
              <gml:posList>13.404 52.520 13.405 52.520</gml:posList>
            </gml:LinearRing>
          </gml:exterior>
        </gml:Polygon>
      </uhi:geometry>
      <uhi:temperature>25.3</uhi:temperature>
    </uhi:Temperature>
  </gml:featureMember>
</wfs:FeatureCollection>
```

## 3. OGC Filter Encoding

### Erweiterte Abfragen:
```xml
<fes:Filter>
  <fes:PropertyIsGreaterThan>
    <fes:ValueReference>temperature</fes:ValueReference>
    <fes:Literal>30</fes:Literal>
  </fes:PropertyIsGreaterThan>
</fes:Filter>
```

## Implementation Plan

### Phase 1: XML-Support hinzufügen
```python
from lxml import etree
from owslib.wfs import WebFeatureService

@app.route('/wfs')
def wfs_endpoint():
    service = request.args.get('service', '').upper()
    request_type = request.args.get('request', '').lower()
    version = request.args.get('version', '2.0.0')
    
    if service == 'WFS' and request_type == 'getcapabilities':
        return generate_capabilities_xml()
    elif service == 'WFS' and request_type == 'getfeature':
        return handle_getfeature_request()
```

### Phase 2: GML-Serialisierung
```python
def geojson_to_gml(geojson_data, feature_type):
    """Convert GeoJSON to GML format."""
    root = etree.Element("{http://www.opengis.net/wfs/2.0}FeatureCollection")
    # GML conversion logic
    return etree.tostring(root, pretty_print=True)
```

### Phase 3: Schema-Definitionen
```xml
<!-- temperature.xsd -->
<xs:schema targetNamespace="http://heatsense.example.com/uhi">
  <xs:complexType name="TemperatureType">
    <xs:complexContent>
      <xs:extension base="gml:AbstractFeatureType">
        <xs:sequence>
          <xs:element name="geometry" type="gml:PolygonPropertyType"/>
          <xs:element name="temperature" type="xs:double"/>
        </xs:sequence>
      </xs:extension>
    </xs:complexContent>
  </xs:complexType>
</xs:schema>
```

## Warum aktuell "WFS-ähnlich"?

### Vorteile der aktuellen Lösung:
1. **Einfacher zu implementieren** - JSON ist leichter als XML/GML
2. **Moderne Web-Standards** - REST + JSON ist zeitgemäß
3. **Direkt verwendbar** - GeoJSON funktioniert in allen modernen GIS-Tools
4. **Bessere Performance** - Weniger Overhead als XML
5. **Entwicklerfreundlich** - Einfacher zu debuggen und zu testen

### Wann vollständiger OGC WFS sinnvoll wäre:
- **Enterprise-Integration** mit bestehenden GIS-Systemen
- **Standardkonformität** für behördliche Anforderungen
- **Interoperabilität** mit OGC-kompatiblen Clients
- **Komplexe Abfragen** mit Filter Encoding

## Empfehlung

Für deine Anwendung ist die **aktuelle WFS-ähnliche Lösung optimal**, weil:

1. ✅ **Funktional vollständig** - Alle wichtigen Features verfügbar
2. ✅ **Modern und zugänglich** - JSON ist universell unterstützt
3. ✅ **Einfach erweiterbar** - Neue Formate leicht hinzufügbar
4. ✅ **Performance** - Schnelle Downloads und Verarbeitung

**Wenn vollständiger OGC WFS gewünscht ist**, können wir eine **Hybrid-Lösung** implementieren:
- `/api/wfs/*` = JSON-basiert (wie jetzt)
- `/wfs?service=WFS` = OGC-konform mit XML/GML

## Nächste Schritte

### Sofort umsetzbar:
1. **Shapefile-Export** hinzufügen
2. **Räumliche Filter** (Bounding Box) implementieren
3. **Bulk-Downloads** als ZIP

### Mittel-/langfristig:
1. **OGC WFS 2.0 Endpunkt** parallel implementieren
2. **GML-Ausgabeformat** hinzufügen
3. **CSW (Catalog Service)** für Metadaten-Discovery

Die aktuelle Lösung ist professionell und praxistauglich! 