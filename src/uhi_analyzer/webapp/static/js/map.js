/**
 * Urban Heat Island Analyzer - Map Module
 * Handles map initialization, layer management, and data visualization
 */

// Global map variables
let map = null;
let temperatureLayer = null;
let landuseLayer = null;
let weatherLayer = null;
let hotspotsLayer = null;

// Map configuration
const MAP_CONFIG = {
    center: [52.5200, 13.4050], // Berlin coordinates
    zoom: 11,
    minZoom: 9,
    maxZoom: 18,
    attribution: '© OpenStreetMap contributors'
};

// Temperature color scale
const TEMPERATURE_COLORS = {
    15: '#3b82f6',  // Blue
    20: '#10b981',  // Green
    25: '#f59e0b',  // Yellow
    30: '#f97316',  // Orange
    35: '#ef4444',  // Red
    40: '#dc2626',  // Dark red
    45: '#991b1b'   // Very dark red
};

// Initialize map
function initializeMap() {
    console.log('🗺️ Initializing map...');
    
    try {
        // Create map instance
        map = L.map('map', {
            center: MAP_CONFIG.center,
            zoom: MAP_CONFIG.zoom,
            minZoom: MAP_CONFIG.minZoom,
            maxZoom: MAP_CONFIG.maxZoom,
            zoomControl: true,
            attributionControl: true
        });
        
        // Add high-resolution base tile layer with better quality
        const baseLayers = {
            'OpenStreetMap': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: MAP_CONFIG.attribution,
                maxZoom: MAP_CONFIG.maxZoom,
                detectRetina: true,
                crossOrigin: true,
                updateWhenIdle: false,
                updateWhenZooming: false,
                keepBuffer: 2,
                className: 'crisp-tiles'
            }),
            'CartoDB Positron': L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                attribution: '© OpenStreetMap contributors, © CartoDB',
                maxZoom: 19,
                detectRetina: true,
                crossOrigin: true,
                updateWhenIdle: false,
                updateWhenZooming: false,
                keepBuffer: 2,
                className: 'crisp-tiles'
            }),
            'CartoDB Dark': L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '© OpenStreetMap contributors, © CartoDB',
                maxZoom: 19,
                detectRetina: true,
                crossOrigin: true,
                updateWhenIdle: false,
                updateWhenZooming: false,
                keepBuffer: 2,
                className: 'crisp-tiles'
            }),
            'Satellite': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                attribution: 'Tiles © Esri',
                maxZoom: 18,
                detectRetina: true,
                crossOrigin: true,
                updateWhenIdle: false,
                updateWhenZooming: false,
                keepBuffer: 2,
                className: 'crisp-tiles'
            })
        };
        
        // Add default base layer
        baseLayers['CartoDB Positron'].addTo(map);
        
        // Add layer control
        L.control.layers(baseLayers).addTo(map);
        
        // Initialize layer groups
        temperatureLayer = L.layerGroup().addTo(map);
        landuseLayer = L.layerGroup();
        weatherLayer = L.layerGroup();
        hotspotsLayer = L.layerGroup();
        
        // Add map event listeners
        map.on('zoomend', handleZoomChange);
        map.on('moveend', handleMapMove);
        map.on('click', handleMapClick);
        
        // Add custom controls
        addCustomControls();
        
        // Setup layer controls event listeners
        setupLayerControls();
        
        console.log('✅ Map initialized successfully');
        
    } catch (error) {
        console.error('❌ Map initialization failed:', error);
        // Don't show error immediately - map might still work
        setTimeout(() => {
            if (!map || !map.getContainer()) {
                showError('Karte konnte nicht geladen werden');
            }
        }, 1000);
    }
}

// Add custom map controls
function addCustomControls() {
    // Remove default zoom control (we'll use our custom buttons)
    map.zoomControl.remove();
    
    // Custom scale control
    L.control.scale({
        position: 'bottomleft',
        metric: true,
        imperial: false
    }).addTo(map);
}

// Setup layer controls event listeners
function setupLayerControls() {
    console.log('🎛️ Setting up layer controls...');
    
    // Wait for DOM to be fully loaded
    setTimeout(() => {
        // Temperature layer control
        const temperatureCheckbox = document.getElementById('layer-temperature');
        if (temperatureCheckbox) {
            temperatureCheckbox.addEventListener('change', toggleTemperatureLayer);
            console.log('✅ Temperature layer control connected');
        } else {
            console.warn('⚠️ Temperature checkbox not found');
        }
        
        // Landuse layer control
        const landuseCheckbox = document.getElementById('layer-landuse');
        if (landuseCheckbox) {
            landuseCheckbox.addEventListener('change', toggleLanduseLayer);
            console.log('✅ Landuse layer control connected');
        } else {
            console.warn('⚠️ Landuse checkbox not found');
        }
        
        // Weather layer control
        const weatherCheckbox = document.getElementById('layer-weather');
        if (weatherCheckbox) {
            weatherCheckbox.addEventListener('change', toggleWeatherLayer);
            console.log('✅ Weather layer control connected');
        } else {
            console.warn('⚠️ Weather checkbox not found');
        }
        
        // Hotspots layer control
        const hotspotsCheckbox = document.getElementById('layer-hotspots');
        if (hotspotsCheckbox) {
            hotspotsCheckbox.addEventListener('change', toggleHotspotsLayer);
            console.log('✅ Hotspots layer control connected');
        } else {
            console.warn('⚠️ Hotspots checkbox not found');
        }
        
        // Check if layer controls container is visible
        const layerControls = document.querySelector('.layer-controls');
        if (layerControls) {
            console.log('✅ Layer controls container found and should be visible');
            // Make sure it's visible and properly styled
            layerControls.style.display = 'block';
            layerControls.style.visibility = 'visible';
            layerControls.style.opacity = '1';
            
            // Log current styles for debugging
            const computedStyle = window.getComputedStyle(layerControls);
            console.log('Layer controls position:', computedStyle.position);
            console.log('Layer controls z-index:', computedStyle.zIndex);
            console.log('Layer controls display:', computedStyle.display);
            console.log('Layer controls visibility:', computedStyle.visibility);
            
            // Test that we can find all checkboxes
            const checkboxes = layerControls.querySelectorAll('input[type="checkbox"]');
            console.log(`Found ${checkboxes.length} layer control checkboxes`);
            checkboxes.forEach((checkbox, index) => {
                console.log(`  ${index + 1}. ${checkbox.id}: ${checkbox.checked ? 'checked' : 'unchecked'}`);
            });
        } else {
            console.error('❌ Layer controls container not found');
        }
        
        console.log('✅ Layer controls setup completed');
    }, 500);
}

// Update map with analysis data
function updateMap(data) {
    console.log('🔄 Updating map with analysis data...');
    console.log('📊 Full data structure:', data);
    console.log('📊 Data keys:', Object.keys(data));
    
    try {
        // Clear existing layers
        clearAllLayers();
        
        // Log each data type for debugging
        Object.keys(data).forEach(key => {
            console.log(`📊 ${key}:`, data[key]);
            if (data[key] && typeof data[key] === 'object') {
                console.log(`📊 ${key} keys:`, Object.keys(data[key]));
            }
        });
        
        // Add temperature data
        if (data.temperature_data) {
            console.log('🌡️ Temperature data found:', data.temperature_data);
            let tempGeoJSON = null;
            
            if (data.temperature_data.geojson) {
                tempGeoJSON = data.temperature_data.geojson;
            } else if (data.temperature_data.grid && data.temperature_data.grid.geojson) {
                tempGeoJSON = data.temperature_data.grid.geojson;
            } else if (data.temperature_data.features) {
                tempGeoJSON = data.temperature_data;
            }
            
            if (tempGeoJSON) {
                console.log('🌡️ Adding temperature layer with GeoJSON:', tempGeoJSON);
                addTemperatureLayer(tempGeoJSON);
                if (!map.hasLayer(temperatureLayer)) {
                    map.addLayer(temperatureLayer);
                }
                const tempCheckbox = document.getElementById('layer-temperature');
                if (tempCheckbox) {
                    tempCheckbox.checked = true;
                }
            } else {
                console.warn('⚠️ No valid temperature GeoJSON found');
            }
        }
        
        // Add hotspots
        if (data.hotspots) {
            console.log('🔥 Hotspots data found:', data.hotspots);
            let hotspotsGeoJSON = null;
            
            if (data.hotspots.geojson) {
                hotspotsGeoJSON = data.hotspots.geojson;
            } else if (data.hotspots.features) {
                hotspotsGeoJSON = data.hotspots;
            }
            
            if (hotspotsGeoJSON) {
                console.log('🔥 Adding hotspots layer with GeoJSON:', hotspotsGeoJSON);
                addHotspotsLayer(hotspotsGeoJSON);
                // Initially hide hotspots, let user enable them
                const hotspotsCheckbox = document.getElementById('layer-hotspots');
                if (hotspotsCheckbox) {
                    hotspotsCheckbox.checked = false;
                }
            } else {
                console.warn('⚠️ No valid hotspots GeoJSON found');
            }
        }
        
        // Add land use data (check multiple possible locations)
        let landuseGeoJSON = null;
        if (data.landuse_correlation) {
            console.log('🌱 Land use correlation data found:', data.landuse_correlation);
            if (data.landuse_correlation.geojson) {
                landuseGeoJSON = data.landuse_correlation.geojson;
            } else if (data.landuse_correlation.features) {
                landuseGeoJSON = data.landuse_correlation;
            }
        } else if (data.landuse_data) {
            console.log('🌱 Land use data found:', data.landuse_data);
            if (data.landuse_data.geojson) {
                landuseGeoJSON = data.landuse_data.geojson;
            } else if (data.landuse_data.features) {
                landuseGeoJSON = data.landuse_data;
            }
        }
        
        if (landuseGeoJSON) {
            console.log('🌱 Adding land use layer with GeoJSON:', landuseGeoJSON);
            addLanduseLayer(landuseGeoJSON);
            if (!map.hasLayer(landuseLayer)) {
                map.addLayer(landuseLayer);
            }
            const landuseCheckbox = document.getElementById('layer-landuse');
            if (landuseCheckbox) {
                landuseCheckbox.checked = true;
            }
            console.log('✅ Land use layer added and displayed');
        } else {
            console.warn('⚠️ No valid land use GeoJSON found');
        }
        
        // Add weather station data (check multiple possible locations)
        let weatherGeoJSON = null;
        if (data.weather_stations) {
            console.log('🌤️ Weather stations data found:', data.weather_stations);
            if (data.weather_stations.geojson) {
                weatherGeoJSON = data.weather_stations.geojson;
            } else if (data.weather_stations.features) {
                weatherGeoJSON = data.weather_stations;
            }
        } else if (data.weather_data) {
            console.log('🌤️ Weather data found:', data.weather_data);
            if (data.weather_data.geojson) {
                weatherGeoJSON = data.weather_data.geojson;
            } else if (data.weather_data.features) {
                weatherGeoJSON = data.weather_data;
            }
        }
        
        if (weatherGeoJSON) {
            console.log('🌤️ Adding weather layer with GeoJSON:', weatherGeoJSON);
            addWeatherLayer(weatherGeoJSON);
            if (!map.hasLayer(weatherLayer)) {
                map.addLayer(weatherLayer);
            }
            const weatherCheckbox = document.getElementById('layer-weather');
            if (weatherCheckbox) {
                weatherCheckbox.checked = true;
            }
            console.log('✅ Weather station layer added and displayed');
        } else {
            console.warn('⚠️ No valid weather station GeoJSON found');
        }
        
        // Center map on data bounds
        centerMapOnData(data);
        
        console.log('✅ Map updated successfully');
        
    } catch (error) {
        console.error('❌ Map update failed:', error);
        console.error('❌ Error details:', error.message);
        console.error('❌ Stack trace:', error.stack);
        showError('Karte konnte nicht aktualisiert werden');
    }
}

// Add temperature layer
function addTemperatureLayer(geojsonData) {
    console.log('🌡️ Adding temperature layer...');
    
    try {
        // Create heat map points
        const heatPoints = [];
        
        // Process GeoJSON features
        if (geojsonData.features) {
            geojsonData.features.forEach(feature => {
                if (feature.geometry && feature.properties) {
                    const coords = getFeatureCoordinates(feature);
                    const temp = feature.properties.temperature;
                    
                    if (coords && temp !== null && temp !== undefined) {
                        heatPoints.push([coords[1], coords[0], temp]);
                        
                        // Add individual markers for detailed view
                        const marker = L.circleMarker([coords[1], coords[0]], {
                            radius: 6,
                            fillColor: getTemperatureColor(temp),
                            color: '#fff',
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.8,
                            className: 'temperature-marker'
                        });
                        
                        // Add popup with temperature info
                        marker.bindPopup(`
                            <div class="temperature-popup">
                                <h4><i class="fas fa-thermometer-half"></i> Temperatur</h4>
                                <p><strong>${temp.toFixed(1)}°C</strong></p>
                                <p><small>Koordinaten: ${coords[1].toFixed(4)}, ${coords[0].toFixed(4)}</small></p>
                            </div>
                        `);
                        
                        temperatureLayer.addLayer(marker);
                    }
                }
            });
        }
        
        // Heatmap removed - showing only grid markers
        
        console.log(`✅ Temperature layer added with ${heatPoints.length} points`);
        
    } catch (error) {
        console.error('❌ Temperature layer creation failed:', error);
    }
}

// Add hotspots layer
function addHotspotsLayer(geojsonData) {
    console.log('🔥 Adding hotspots layer...');
    
    try {
        if (geojsonData.features) {
            geojsonData.features.forEach(feature => {
                if (feature.geometry && feature.properties) {
                    const coords = getFeatureCoordinates(feature);
                    const temp = feature.properties.temperature;
                    
                    if (coords && temp !== null && temp !== undefined) {
                        // Create hotspot marker
                        const marker = L.marker([coords[1], coords[0]], {
                            icon: L.divIcon({
                                className: 'hotspot-marker',
                                html: `
                                    <div class="hotspot-icon">
                                        <i class="fas fa-fire"></i>
                                    </div>
                                `,
                                iconSize: [30, 30],
                                iconAnchor: [15, 15]
                            })
                        });
                        
                        // Add detailed popup
                        marker.bindPopup(`
                            <div class="hotspot-popup">
                                <h4><i class="fas fa-fire"></i> Hotspot</h4>
                                <p><strong>Temperatur: ${temp.toFixed(1)}°C</strong></p>
                                <p>Intensität: ${temp > 40 ? 'Sehr hoch' : temp > 35 ? 'Hoch' : 'Mittel'}</p>
                                <p><small>Koordinaten: ${coords[1].toFixed(4)}, ${coords[0].toFixed(4)}</small></p>
                            </div>
                        `);
                        
                        hotspotsLayer.addLayer(marker);
                    }
                }
            });
        }
        
        console.log('✅ Hotspots layer added');
        
    } catch (error) {
        console.error('❌ Hotspots layer creation failed:', error);
    }
}

// Add land use layer
function addLanduseLayer(geojsonData) {
    console.log('🌱 Adding land use layer...');
    
    try {
        if (geojsonData.features) {
            // Create a single GeoJSON layer with all features
            const layer = L.geoJSON(geojsonData, {
                                        style: function(feature) {
                            const landuseType = feature.properties.landuse_type || feature.properties.CODE_18 || 'default';
                            return {
                                fillColor: getLanduseColor(landuseType),
                                weight: 1,
                                opacity: 0.8,
                                color: '#fff',
                                fillOpacity: 0.4,
                                interactive: true,
                                className: 'landuse-polygon'
                            };
                        },
                onEachFeature: function(feature, layer) {
                    if (feature.properties) {
                        const landuseType = feature.properties.landuse_type || feature.properties.CODE_18 || 'Unbekannt';
                        const area = feature.properties.area || feature.properties.Shape_Area || 'N/A';
                        const correlation = feature.properties.correlation || 'N/A';
                        
                        layer.bindPopup(`
                            <div class="landuse-popup">
                                <h4><i class="fas fa-seedling"></i> Landnutzung</h4>
                                <p><strong>Typ: ${landuseType}</strong></p>
                                <p>Fläche: ${area}</p>
                                ${correlation !== 'N/A' ? `<p>Korrelation: ${correlation}</p>` : ''}
                            </div>
                        `);
                    }
                }
            });
            
            landuseLayer.addLayer(layer);
            console.log(`✅ Land use layer added with ${geojsonData.features.length} features`);
        } else {
            console.warn('⚠️ No land use features found in GeoJSON data');
        }
        
    } catch (error) {
        console.error('❌ Land use layer creation failed:', error);
        console.error('Error details:', error.message);
    }
}

// Add weather station layer
function addWeatherLayer(geojsonData) {
    console.log('🌤️ Adding weather station layer...');
    
    try {
        if (geojsonData.features) {
            geojsonData.features.forEach(feature => {
                if (feature.geometry && feature.properties) {
                    const coords = getFeatureCoordinates(feature);
                    if (coords) {
                        const temperature = feature.properties.ground_temp || feature.properties.temperature || 0;
                        const stationName = feature.properties.station_name || feature.properties.name || 'Unbekannt';
                        
                        const marker = L.circleMarker([coords[1], coords[0]], {
                            radius: 8,
                            fillColor: '#3b82f6',
                            color: '#fff',
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.8,
                            className: 'weather-marker'
                        });
                        
                        marker.bindPopup(`
                            <div class="weather-popup">
                                <h4><i class="fas fa-thermometer-half"></i> Wetterstation</h4>
                                <p><strong>Station: ${stationName}</strong></p>
                                <p>Temperatur: ${temperature.toFixed(1)}°C</p>
                            </div>
                        `);
                        
                        weatherLayer.addLayer(marker);
                    }
                }
            });
        }
        
        console.log('✅ Weather station layer added');
        
    } catch (error) {
        console.error('❌ Weather station layer creation failed:', error);
    }
}

// Get feature coordinates
function getFeatureCoordinates(feature) {
    if (feature.geometry) {
        if (feature.geometry.type === 'Point') {
            return feature.geometry.coordinates;
        } else if (feature.geometry.type === 'Polygon') {
            // Return centroid for polygons
            const coords = feature.geometry.coordinates[0];
            let x = 0, y = 0;
            coords.forEach(coord => {
                x += coord[0];
                y += coord[1];
            });
            return [x / coords.length, y / coords.length];
        }
    }
    return null;
}

// Get temperature color
function getTemperatureColor(temperature) {
    if (temperature <= 15) return TEMPERATURE_COLORS[15];
    if (temperature <= 20) return TEMPERATURE_COLORS[20];
    if (temperature <= 25) return TEMPERATURE_COLORS[25];
    if (temperature <= 30) return TEMPERATURE_COLORS[30];
    if (temperature <= 35) return TEMPERATURE_COLORS[35];
    if (temperature <= 40) return TEMPERATURE_COLORS[40];
    return TEMPERATURE_COLORS[45];
}

// Get land use color
function getLanduseColor(landuseType) {
    const colors = {
        'urban': '#6b7280',
        'residential': '#94a3b8',
        'commercial': '#64748b',
        'industrial': '#475569',
        'forest': '#22c55e',
        'grass': '#84cc16',
        'water': '#3b82f6',
        'agriculture': '#eab308',
        'default': '#d1d5db'
    };
    
    // Handle CORINE Land Cover codes (if using raw data)
    const corineColors = {
        '111': '#e60000', // Continuous urban fabric
        '112': '#ff0000', // Discontinuous urban fabric
        '121': '#cc4df2', // Industrial or commercial units
        '122': '#cc0000', // Road and rail networks
        '123': '#e6cccc', // Port areas
        '124': '#e6cce6', // Airports
        '131': '#a600cc', // Mineral extraction sites
        '132': '#a64d00', // Dump sites
        '133': '#ff4dff', // Construction sites
        '141': '#ffa6ff', // Green urban areas
        '142': '#ffe6ff', // Sport and leisure facilities
        '211': '#ffffa8', // Non-irrigated arable land
        '212': '#ffff00', // Permanently irrigated land
        '213': '#e6e600', // Rice fields
        '221': '#e68000', // Vineyards
        '222': '#f2a64d', // Fruit trees and berry plantations
        '223': '#e6a600', // Olive groves
        '231': '#e6e64d', // Pastures
        '241': '#ffe6a6', // Annual crops
        '242': '#ffe64d', // Complex cultivation patterns
        '243': '#e6cc4d', // Agriculture with natural vegetation
        '244': '#f2cca6', // Agro-forestry areas
        '311': '#80ff00', // Broad-leaved forest
        '312': '#00a600', // Coniferous forest
        '313': '#4dff00', // Mixed forest
        '321': '#ccf24d', // Natural grasslands
        '322': '#a6ff80', // Moors and heathland
        '323': '#a6e64d', // Sclerophyllous vegetation
        '324': '#a6f200', // Transitional woodland-shrub
        '331': '#e6e6e6', // Beaches, dunes, sands
        '332': '#cccccc', // Bare rocks
        '333': '#ccffcc', // Sparsely vegetated areas
        '334': '#000000', // Burnt areas
        '335': '#a6e6cc', // Glaciers and perpetual snow
        '411': '#a6a6ff', // Inland marshes
        '412': '#4d4dff', // Peat bogs
        '421': '#ccccff', // Salt marshes
        '422': '#e6e6ff', // Salines
        '423': '#a6a6e6', // Intertidal flats
        '511': '#00ccf2', // Water courses
        '512': '#80f2e6', // Water bodies
        '521': '#00ffa6', // Coastal lagoons
        '522': '#a6ffe6', // Estuaries
        '523': '#e6f2ff'  // Sea and ocean
    };
    
    // Check for CORINE codes first
    if (landuseType && corineColors[landuseType]) {
        return corineColors[landuseType];
    }
    
    return colors[landuseType] || colors.default;
}

// Clear all layers
function clearAllLayers() {
    temperatureLayer.clearLayers();
    landuseLayer.clearLayers();
    weatherLayer.clearLayers();
    hotspotsLayer.clearLayers();
    
    // Heatmap layer removed
}

// Center map on data
function centerMapOnData(data) {
    if (data.temperature_data && data.temperature_data.geojson) {
        try {
            const geojson = data.temperature_data.geojson;
            if (geojson.features && geojson.features.length > 0) {
                const group = L.featureGroup();
                
                geojson.features.forEach(feature => {
                    const coords = getFeatureCoordinates(feature);
                    if (coords) {
                        L.marker([coords[1], coords[0]]).addTo(group);
                    }
                });
                
                if (group.getLayers().length > 0) {
                    map.fitBounds(group.getBounds(), { padding: [20, 20] });
                }
            }
        } catch (error) {
            console.error('Failed to center map on data:', error);
        }
    }
}

// Map control functions
function zoomIn() {
    if (map) {
        map.zoomIn();
    }
}

function zoomOut() {
    if (map) {
        map.zoomOut();
    }
}

function centerMap() {
    if (map) {
        map.setView(MAP_CONFIG.center, MAP_CONFIG.zoom);
    }
}

// Layer toggle functions
function toggleTemperatureLayer() {
    const checkbox = document.getElementById('layer-temperature');
    if (!checkbox || !temperatureLayer) return;
    
    const checked = checkbox.checked;
    console.log('🌡️ Temperature layer toggle:', checked ? 'ON' : 'OFF');
    
    if (checked) {
        if (!map.hasLayer(temperatureLayer)) {
            map.addLayer(temperatureLayer);
        }
    } else {
        if (map.hasLayer(temperatureLayer)) {
            map.removeLayer(temperatureLayer);
        }
    }
}

function toggleLanduseLayer() {
    const checkbox = document.getElementById('layer-landuse');
    if (!checkbox || !landuseLayer) return;
    
    const checked = checkbox.checked;
    console.log('🏞️ Landuse layer toggle:', checked ? 'ON' : 'OFF');
    
    if (checked) {
        if (!map.hasLayer(landuseLayer)) {
            map.addLayer(landuseLayer);
            console.log('✅ Land use layer shown');
        }
    } else {
        if (map.hasLayer(landuseLayer)) {
            map.removeLayer(landuseLayer);
            console.log('❌ Land use layer hidden');
        }
    }
}

function toggleWeatherLayer() {
    const checkbox = document.getElementById('layer-weather');
    if (!checkbox || !weatherLayer) return;
    
    const checked = checkbox.checked;
    console.log('🌤️ Weather layer toggle:', checked ? 'ON' : 'OFF');
    
    if (checked) {
        if (!map.hasLayer(weatherLayer)) {
            map.addLayer(weatherLayer);
            console.log('✅ Weather station layer shown');
        }
    } else {
        if (map.hasLayer(weatherLayer)) {
            map.removeLayer(weatherLayer);
            console.log('❌ Weather station layer hidden');
        }
    }
}

function toggleHotspotsLayer() {
    const checkbox = document.getElementById('layer-hotspots');
    if (!checkbox || !hotspotsLayer) return;
    
    const checked = checkbox.checked;
    console.log('🔥 Hotspots layer toggle:', checked ? 'ON' : 'OFF');
    
    if (checked) {
        if (!map.hasLayer(hotspotsLayer)) {
            map.addLayer(hotspotsLayer);
            console.log('✅ Hotspots layer shown');
        }
    } else {
        if (map.hasLayer(hotspotsLayer)) {
            map.removeLayer(hotspotsLayer);
            console.log('❌ Hotspots layer hidden');
        }
    }
}

// Map event handlers
function handleZoomChange(e) {
    const zoom = map.getZoom();
    console.log('Map zoom changed to:', zoom);
    
    // Adjust marker sizes based on zoom level
    if (temperatureLayer) {
        temperatureLayer.eachLayer(function(layer) {
            if (layer.setRadius) {
                const radius = Math.max(3, Math.min(8, zoom - 5));
                layer.setRadius(radius);
            }
        });
    }
}

function handleMapMove(e) {
    const center = map.getCenter();
    console.log('Map moved to:', center.lat.toFixed(4), center.lng.toFixed(4));
}

function handleMapClick(e) {
    const latlng = e.latlng;
    console.log('Map clicked at:', latlng.lat.toFixed(4), latlng.lng.toFixed(4));
}

// Export functions for global access
window.initializeMap = initializeMap;
window.updateMap = updateMap;
window.zoomIn = zoomIn;
window.zoomOut = zoomOut;
window.centerMap = centerMap;
window.toggleTemperatureLayer = toggleTemperatureLayer;
window.toggleLanduseLayer = toggleLanduseLayer;
window.toggleWeatherLayer = toggleWeatherLayer;
window.toggleHotspotsLayer = toggleHotspotsLayer;

// Add custom CSS for markers
const style = document.createElement('style');
style.textContent = `
    .hotspot-marker {
        background: none;
        border: none;
    }
    
    .hotspot-icon {
        background: #ef4444;
        border: 2px solid #fff;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    
    .temperature-popup,
    .hotspot-popup,
    .landuse-popup {
        min-width: 200px;
    }
    
    .temperature-popup h4,
    .hotspot-popup h4,
    .landuse-popup h4 {
        margin: 0 0 10px 0;
        color: #1e3a8a;
        font-size: 16px;
    }
    
    .temperature-popup p,
    .hotspot-popup p,
    .landuse-popup p {
        margin: 5px 0;
        font-size: 14px;
    }
`;
document.head.appendChild(style); 