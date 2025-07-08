/**
 * HeatSense - Urban Heat Island Analyzer
 * Main JavaScript Application
 */

// Global variables
let map = null;
let temperatureLayer = null;
let hotspotsLayer = null;
let weatherStationsLayer = null;
let boundaryLayer = null;
let currentAnalysisData = null;

// Application state
const appState = {
    isAnalyzing: false,
    currentPerformanceMode: 'standard',
    selectedArea: null,
    selectedAreaType: 'bezirk'
};

/**
 * Initialize the application when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});



/**
 * Main application initialization
 */
function initializeApp() {
    console.log('🔥 Initializing HeatSense...');
    
    // Initialize date pickers
    initializeDatePickers();
    
    // Load performance modes
    loadPerformanceModes();
    
    // Initialize map
    initializeMap();
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize area dropdown with default selection
    updateAreaDropdown();
    
    console.log('✅ HeatSense initialized successfully');
}

/**
 * Initialize date picker inputs
 */
function initializeDatePickers() {
    const config = {
        dateFormat: "d.m.Y",
        locale: "de",
        allowInput: true,
        defaultDate: "01.06.2025"
    };
    
    flatpickr("#start-date", {
        ...config,
        defaultDate: "01.06.2025"
    });
    
    flatpickr("#end-date", {
        ...config,
        defaultDate: "30.06.2025"
    });
}

/**
 * Load available performance modes from API
 */
async function loadPerformanceModes() {
    try {
        const response = await fetch('/api/performance-modes');
        const modes = await response.json();
        
        const container = document.getElementById('performance-modes');
        container.innerHTML = '';
        
        // Order modes as: preview, fast, standard, detailed
        const orderedModes = ['preview', 'fast', 'standard', 'detailed'];
        orderedModes.forEach((modeKey, index) => {
            if (modes[modeKey]) {
                const modeElement = createPerformanceModeElement(modeKey, modes[modeKey], modeKey === 'fast'); // Default to 'fast'
                container.appendChild(modeElement);
            }
        });
        
        // Set default selection
        appState.currentPerformanceMode = 'fast';
        
    } catch (error) {
        console.error('Error loading performance modes:', error);
        showErrorMessage('Fehler beim Laden der Leistungsmodi');
    }
}

/**
 * Create performance mode UI element
 */
function createPerformanceModeElement(modeKey, modeData, isDefault = false) {
    const div = document.createElement('div');
    div.className = `performance-mode ${isDefault ? 'selected' : ''}`;
    div.onclick = () => selectPerformanceMode(modeKey, div);
    div.setAttribute('data-mode', modeKey);
    
    const modeName = modeData.name || modeKey;
    const modeIcon = modeData.icon || 'fas fa-cog';
    
    div.innerHTML = `
        <input type="radio" name="performance_mode" value="${modeKey}" ${isDefault ? 'checked' : ''}>
        <div class="mode-header">
            <div class="mode-title-group">
                <i class="${modeIcon}"></i>
                <span class="mode-title">${modeName}</span>
            </div>
            <span class="mode-time">${modeData.estimated_time}</span>
        </div>
        <div class="mode-description">${modeData.description}</div>
    `;
    
    return div;
}

/**
 * Select performance mode
 */
function selectPerformanceMode(modeKey, element) {
    // Remove previous selection
    document.querySelectorAll('.performance-mode').forEach(el => el.classList.remove('selected'));
    
    // Select new mode
    element.classList.add('selected');
    element.querySelector('input[type="radio"]').checked = true;
    appState.currentPerformanceMode = modeKey;
    
    console.log(`Selected performance mode: ${modeKey}`);
}

/**
 * Initialize Leaflet map
 */
function initializeMap() {
    // Berlin coordinates
    const berlinCenter = [52.5200, 13.4050];
    
    // Create map
    map = L.map('map', {
        center: berlinCenter,
        zoom: 10,
        zoomControl: true,
        attributionControl: true
    });
    
    // Add base layer (CartoDB Positron - clean and modern)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '© CARTO',
        maxZoom: 19,
        subdomains: 'abcd'
    }).addTo(map);
    
    // Add custom attribution
    map.attributionControl.addAttribution('HeatSense Urban Heat Island Analyzer');
    
    // Ensure map renders correctly after layout is established
    setTimeout(() => {
        map.invalidateSize();
    }, 100);
    
    // Also invalidate size on window resize
    window.addEventListener('resize', () => {
        map.invalidateSize();
    });
    
    console.log('🗺️ Map initialized');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Area selection dropdown
    document.getElementById('area-select').addEventListener('change', function(e) {
        appState.selectedArea = e.target.value;
    });
}

/**
 * Select area type and update dropdown
 */
function selectAreaType(areaType) {
    // Remove active class from all buttons
    document.querySelectorAll('.area-type-btn').forEach(btn => btn.classList.remove('active'));
    
    // Add active class to clicked button
    document.querySelector(`[data-type="${areaType}"]`).classList.add('active');
    
    // Update app state
    appState.selectedAreaType = areaType;
    
    // Update dropdown
    updateAreaDropdown();
}

/**
 * Update area dropdown based on selected type
 */
async function updateAreaDropdown() {
    const selectedType = appState.selectedAreaType;
    
    try {
        const response = await fetch(`/api/areas?type=${selectedType}`);
        const areas = await response.json();
        
        const select = document.getElementById('area-select');
        select.innerHTML = '';
        
        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        
        let placeholderText = 'Auswählen...';
        switch (selectedType) {
            case 'stadt':
                placeholderText = 'Stadt auswählen...';
                break;
            case 'bezirk':
                placeholderText = 'Bezirk auswählen...';
                break;
            case 'ortsteil':
                placeholderText = 'Ortsteil auswählen...';
                break;
        }
        
        defaultOption.textContent = placeholderText;
        select.appendChild(defaultOption);
        
        // Add areas
        areas.forEach(area => {
            const option = document.createElement('option');
            option.value = area;
            option.textContent = area;
            select.appendChild(option);
        });
        
        // Reset selection
        appState.selectedArea = null;
        
    } catch (error) {
        console.error('Error updating area dropdown:', error);
        showErrorMessage('Fehler beim Laden der Gebiete');
    }
}

/**
 * Start analysis
 */
async function startAnalysis() {
    if (appState.isAnalyzing) {
        return;
    }
    
    // Validate inputs
    const validation = validateInputs();
    if (!validation.valid) {
        showErrorMessage(validation.message);
        return;
    }
    
    // Set analyzing state
    appState.isAnalyzing = true;
    updateAnalyzeButton(true);
    showLoadingModal();
    hideDownloadButton();
    
    // Prepare analysis data
    const analysisData = {
        area_type: appState.selectedAreaType,
        area: appState.selectedArea,
        start_date: document.getElementById('start-date').value,
        end_date: document.getElementById('end-date').value,
        performance_mode: appState.currentPerformanceMode
    };
    
    console.log('🚀 Starting analysis with data:', analysisData);
    
    try {
        // Start analysis
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(analysisData)
        });
        
        const result = await response.json();
        
        if (result.status === 'error') {
            throw new Error(result.errors?.join(', ') || 'Analysis failed');
        }
        
        // Store results
        currentAnalysisData = result;
        
        // Display results
        displayAnalysisResults(result);
        
        // Show download button
        showDownloadButton();
        
        console.log('✅ Analysis completed successfully');
        
    } catch (error) {
        console.error('❌ Analysis failed:', error);
        showErrorMessage(`Analyse fehlgeschlagen: ${error.message}`);
    } finally {
        // Reset state
        appState.isAnalyzing = false;
        updateAnalyzeButton(false);
        hideLoadingModal();
    }
}

/**
 * Validate user inputs
 */
function validateInputs() {
    if (!appState.selectedArea) {
        return { valid: false, message: 'Bitte wählen Sie ein Gebiet aus.' };
    }
    
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    
    if (!startDate || !endDate) {
        return { valid: false, message: 'Bitte geben Sie Start- und Enddatum an.' };
    }
    
    // Parse dates for validation
    const start = new Date(startDate.split('.').reverse().join('-'));
    const end = new Date(endDate.split('.').reverse().join('-'));
    
    if (start >= end) {
        return { valid: false, message: 'Das Startdatum muss vor dem Enddatum liegen.' };
    }
    
    return { valid: true };
}

/**
 * Display analysis results
 */
function displayAnalysisResults(result) {
    console.log('Displaying analysis results:', result);
    
    const data = result.data;
    if (!data) {
        console.warn('No data in analysis results');
        showErrorMessage('Keine Analysedaten erhalten');
        return;
    }
    
    console.log('Analysis data structure:', data);
    
    // Show results container
    const resultsContainer = document.getElementById('results-container');
    if (resultsContainer) {
        resultsContainer.style.display = 'block';
    }
    
    try {
        // Update KPIs
        console.log('Updating KPIs...');
        updateKPIs(data);
    } catch (error) {
        console.error('Error updating KPIs:', error);
    }
    
    try {
        // Update map layers
        console.log('Updating map layers...');
        updateMapLayers(data);
    } catch (error) {
        console.error('Error updating map layers:', error);
    }
    
    try {
        // Display recommendations
        console.log('Displaying recommendations...');
        displayRecommendations(data);
    } catch (error) {
        console.error('Error displaying recommendations:', error);
    }
    
    try {
        // Fit map to data bounds if available
        console.log('Fitting map to bounds...');
        fitMapToBounds(data);
    } catch (error) {
        console.error('Error fitting map to bounds:', error);
    }
    
    console.log('Analysis results display completed');
}

/**
 * Update KPI cards
 */
function updateKPIs(data) {
    console.log('Updating KPIs with data:', data);
    
    const summary = data.summary || {};
    const temperatureOverview = summary.temperature_overview || {};
    
    // Update KPI values with proper formatting and validation
    const hotspotsCount = summary.hotspots_count || 0;
    document.getElementById('kpi-hotspots').textContent = hotspotsCount;
    
    const avgTemp = temperatureOverview.mean;
    document.getElementById('kpi-temp-avg').textContent = 
        (avgTemp !== undefined && avgTemp !== null) ? `${parseFloat(avgTemp).toFixed(1)}°C` : '-';
    
    const maxTemp = temperatureOverview.max;
    document.getElementById('kpi-temp-max').textContent = 
        (maxTemp !== undefined && maxTemp !== null) ? `${parseFloat(maxTemp).toFixed(1)}°C` : '-';
    
    const recommendationsCount = summary.recommendations_count || 0;
    document.getElementById('kpi-recommendations').textContent = recommendationsCount;
    
    console.log('KPIs updated:', {
        hotspots: hotspotsCount,
        avgTemp: avgTemp,
        maxTemp: maxTemp,
        recommendations: recommendationsCount
    });
}

/**
 * Update map layers with analysis data
 */
function updateMapLayers(data) {
    // Clear existing layers
    clearMapLayers();
    
    // Add boundary layer
    if (data.boundary) {
        boundaryLayer = L.geoJSON(data.boundary, {
            style: {
                color: '#6c757d',        // Gray color instead of red
                weight: 2,
                opacity: 0.8,
                fillColor: '#6c757d',
                fillOpacity: 0.05
            }
        }).addTo(map);
    }
    
    // Add temperature layer
    if (data.temperature_data?.geojson) {
        temperatureLayer = L.geoJSON(data.temperature_data.geojson, {
            style: function(feature) {
                const temp = feature.properties.temperature;
                return {
                    color: getTemperatureColor(temp),
                    weight: 1,
                    opacity: 0.8,
                    fillOpacity: 0.6
                };
            },
            onEachFeature: function(feature, layer) {
                if (feature.properties.temperature) {
                    layer.bindPopup(`Temperatur: ${feature.properties.temperature.toFixed(1)}°C`);
                }
            }
        }).addTo(map);
    }
    
    // Add hotspots layer
    if (data.hotspots?.geojson) {
        hotspotsLayer = L.geoJSON(data.hotspots.geojson, {
            style: {
                color: '#ff0000',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.7
            },
            onEachFeature: function(feature, layer) {
                if (feature.properties.temperature) {
                    layer.bindPopup(`🔥 Hotspot: ${feature.properties.temperature.toFixed(1)}°C`);
                }
            }
        });
        // Don't add to map by default - user can toggle
    }
    
    // Add weather stations layer (if available)
    if (data.weather_stations?.geojson) {
        weatherStationsLayer = L.geoJSON(data.weather_stations.geojson, {
            pointToLayer: function(feature, latlng) {
                return L.circleMarker(latlng, {
                    radius: 6,
                    fillColor: '#3498db',
                    color: '#2980b9',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                });
            },
            onEachFeature: function(feature, layer) {
                const temp = feature.properties.ground_temp;
                if (temp) {
                    layer.bindPopup(`🌤️ Wetterstation: ${temp.toFixed(1)}°C`);
                }
            }
        });
        // Don't add to map by default - user can toggle
    }
    
    // Update map control button states
    updateMapControlButtons();
    updateLegend(); // Update legend after layers are added
}

/**
 * Get temperature color for visualization
 */
function getTemperatureColor(temperature) {
    if (temperature < 15) return '#0066cc';
    if (temperature < 20) return '#00cc66';
    if (temperature < 25) return '#cccc00';
    if (temperature < 30) return '#ff6600';
    if (temperature < 35) return '#ff3300';
    return '#cc0000';
}

/**
 * Clear existing map layers
 */
function clearMapLayers() {
    if (temperatureLayer) {
        map.removeLayer(temperatureLayer);
        temperatureLayer = null;
    }
    if (hotspotsLayer) {
        map.removeLayer(hotspotsLayer);
        hotspotsLayer = null;
    }
    if (weatherStationsLayer) {
        map.removeLayer(weatherStationsLayer);
        weatherStationsLayer = null;
    }
    if (boundaryLayer) {
        map.removeLayer(boundaryLayer);
        boundaryLayer = null;
    }
    updateLegend(); // Update legend when all layers are cleared
}

/**
 * Fit map to data bounds
 */
function fitMapToBounds(data) {
    if (boundaryLayer) {
        map.fitBounds(boundaryLayer.getBounds(), { padding: [20, 20] });
    } else if (temperatureLayer) {
        map.fitBounds(temperatureLayer.getBounds(), { padding: [20, 20] });
    }
}

/**
 * Update map control button states
 */
function updateMapControlButtons() {
    // Boundary button - always active when available
    const boundaryBtn = document.getElementById('toggle-boundary');
    if (boundaryLayer) {
        boundaryBtn.classList.add('active');
        boundaryBtn.disabled = false;
    } else {
        boundaryBtn.classList.remove('active');
        boundaryBtn.disabled = true;
    }
    
    // Temperature button - always active when available
    const tempBtn = document.getElementById('toggle-temperature');
    if (temperatureLayer) {
        tempBtn.classList.add('active');
        tempBtn.disabled = false;
    } else {
        tempBtn.classList.remove('active');
        tempBtn.disabled = true;
    }
    
    // Hotspots button
    const hotspotsBtn = document.getElementById('toggle-hotspots');
    if (hotspotsLayer) {
        hotspotsBtn.disabled = false;
    } else {
        hotspotsBtn.disabled = true;
    }
    
    // Weather stations button
    const weatherBtn = document.getElementById('toggle-weather');
    if (weatherStationsLayer) {
        weatherBtn.disabled = false;
    } else {
        weatherBtn.disabled = true;
    }
}

/**
 * Toggle boundary layer
 */
function toggleBoundaryLayer() {
    const btn = document.getElementById('toggle-boundary');
    if (boundaryLayer) {
        if (map.hasLayer(boundaryLayer)) {
            map.removeLayer(boundaryLayer);
            btn.classList.remove('active');
        } else {
            map.addLayer(boundaryLayer);
            btn.classList.add('active');
        }
    }
}

/**
 * Toggle temperature layer
 */
function toggleTemperatureLayer() {
    const btn = document.getElementById('toggle-temperature');
    if (temperatureLayer) {
        if (map.hasLayer(temperatureLayer)) {
            map.removeLayer(temperatureLayer);
            btn.classList.remove('active');
        } else {
            map.addLayer(temperatureLayer);
            btn.classList.add('active');
        }
        updateLegend(); // Update legend when temperature layer is toggled
    }
}

/**
 * Toggle hotspots layer
 */
function toggleHotspotsLayer() {
    const btn = document.getElementById('toggle-hotspots');
    if (hotspotsLayer) {
        if (map.hasLayer(hotspotsLayer)) {
            map.removeLayer(hotspotsLayer);
            btn.classList.remove('active');
        } else {
            map.addLayer(hotspotsLayer);
            btn.classList.add('active');
        }
        updateLegend(); // Update legend when hotspots layer is toggled
    }
}

/**
 * Toggle weather stations layer
 */
function toggleWeatherStations() {
    const btn = document.getElementById('toggle-weather');
    if (weatherStationsLayer) {
        if (map.hasLayer(weatherStationsLayer)) {
            map.removeLayer(weatherStationsLayer);
            btn.classList.remove('active');
        } else {
            map.addLayer(weatherStationsLayer);
            btn.classList.add('active');
        }
    }
}

/**
 * Display recommendations
 */
function displayRecommendations(data) {
    console.log('Displaying recommendations with data:', data);
    
    const container = document.getElementById('recommendations-list');
    if (!container) {
        console.warn('Recommendations container not found');
        return;
    }
    
    container.innerHTML = '';
    
    const recommendations = data.recommendations;
    console.log('Recommendations object:', recommendations);
    
    if (!recommendations) {
        console.warn('No recommendations data available');
        container.innerHTML = '<p>Keine Empfehlungen verfügbar.</p>';
        return;
    }
    
    let strategies = [];
    
    // Handle different recommendation data structures
    if (Array.isArray(recommendations)) {
        strategies = recommendations;
    } else if (recommendations.strategies) {
        strategies = Array.isArray(recommendations.strategies) ? 
            recommendations.strategies : [recommendations.strategies];
    } else if (typeof recommendations === 'object') {
        // If it's an object, try to extract meaningful content
        strategies = Object.values(recommendations).filter(item => 
            typeof item === 'string' || (typeof item === 'object' && (item.title || item.description))
        );
    }
    
    console.log('Processed strategies:', strategies);
    
    if (!strategies || strategies.length === 0) {
        console.warn('No strategies found in recommendations');
        container.innerHTML = '<p>Keine Empfehlungen verfügbar.</p>';
        return;
    }
    
    strategies.forEach((recommendation, index) => {
        const item = document.createElement('div');
        item.className = 'recommendation-item';
        
        if (typeof recommendation === 'string') {
            item.innerHTML = `<div class="recommendation-description">${recommendation}</div>`;
        } else if (typeof recommendation === 'object') {
            const title = recommendation.title || recommendation.strategy || `Empfehlung ${index + 1}`;
            const description = recommendation.description || recommendation.text || recommendation.content || 'Keine Beschreibung verfügbar';
            
            item.innerHTML = `
                <div class="recommendation-title">${title}</div>
                <div class="recommendation-description">${description}</div>
            `;
        } else {
            item.innerHTML = `<div class="recommendation-description">Empfehlung ${index + 1}: ${String(recommendation)}</div>`;
        }
        
        container.appendChild(item);
    });
    
    console.log(`Displayed ${strategies.length} recommendations`);
}

/**
 * Update analyze button state
 */
function updateAnalyzeButton(isAnalyzing) {
    const button = document.getElementById('analyze-button');
    const icon = button.querySelector('i');
    
    if (isAnalyzing) {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyse läuft...';
    } else {
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-play"></i> Analyse starten';
    }
}

/**
 * Show loading modal
 */
function showLoadingModal() {
    const modal = document.getElementById('loading-modal');
    const text = document.getElementById('loading-text');
    
    modal.style.display = 'block';
    text.textContent = 'Daten werden heruntergeladen...';
    
    // Simulate loading stages
    let stage = 0;
    const loadingTexts = [
        'Daten werden heruntergeladen...',
        'Analyse wird durchgeführt...',
        'Ergebnisse werden verarbeitet...'
    ];
    
    const interval = setInterval(() => {
        if (appState.isAnalyzing) {
            stage = (stage + 1) % loadingTexts.length;
            text.textContent = loadingTexts[stage];
        } else {
            clearInterval(interval);
        }
    }, 2000);
}

/**
 * Hide loading modal
 */
function hideLoadingModal() {
    const modal = document.getElementById('loading-modal');
    modal.style.display = 'none';
}

/**
 * Show info modal
 */
function showInfo() {
    document.getElementById('info-modal').style.display = 'block';
}

/**
 * Show privacy modal (placeholder)
 */
function showPrivacy() {
    alert('Datenschutz-Information würde hier angezeigt werden.');
}

/**
 * Close modal
 */
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

/**
 * Close modal when clicking outside
 */
window.onclick = function(event) {
    const modal = document.getElementById('info-modal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
};

/**
 * Show error message
 */
function showErrorMessage(message) {
    // Simple alert for now - could be enhanced with toast notifications
    alert(`❌ Fehler: ${message}`);
}

/**
 * Update legend display based on active layers
 */
function updateLegend() {
    const legendContainer = document.getElementById('map-legend');
    const temperatureLegend = document.getElementById('temperature-legend');
    const hotspotsLegend = document.getElementById('hotspots-legend');
    
    // Check which layers are active
    const isTemperatureActive = temperatureLayer && map.hasLayer(temperatureLayer);
    const isHotspotsActive = hotspotsLayer && map.hasLayer(hotspotsLayer);
    
    // Show/hide individual legend sections
    if (isTemperatureActive) {
        temperatureLegend.style.display = 'block';
    } else {
        temperatureLegend.style.display = 'none';
    }
    
    if (isHotspotsActive) {
        hotspotsLegend.style.display = 'block';
    } else {
        hotspotsLegend.style.display = 'none';
    }
    
    // Show/hide entire legend container
    if (isTemperatureActive || isHotspotsActive) {
        legendContainer.style.display = 'block';
    } else {
        legendContainer.style.display = 'none';
    }
}

/**
 * Show success message to user
 */
function showSuccessMessage(message) {
    console.log('Success:', message);
    // You can extend this to show a toast notification
}

/**
 * Show download button when analysis results are available
 */
function showDownloadButton() {
    const downloadButton = document.getElementById('download-button');
    if (downloadButton) {
        downloadButton.style.display = 'flex';
    }
    
    const wfsDropdown = document.getElementById('wfs-dropdown');
    if (wfsDropdown) {
        wfsDropdown.style.display = 'block';
    }
}

/**
 * Hide download button
 */
function hideDownloadButton() {
    const downloadButton = document.getElementById('download-button');
    if (downloadButton) {
        downloadButton.style.display = 'none';
    }
    
    const wfsDropdown = document.getElementById('wfs-dropdown');
    if (wfsDropdown) {
        wfsDropdown.style.display = 'none';
    }
}

/**
 * Download analysis results as JSON file
 */
function downloadResults() {
    if (!currentAnalysisData) {
        showErrorMessage('Keine Analyseergebnisse zum Download verfügbar');
        return;
    }
    
    try {
        // Create filename with timestamp and area info
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        const area = currentAnalysisData.metadata?.area || 'unbekannt';
        const filename = `uhi_analysis_${area}_${timestamp}.json`;
        
        // Create download data
        const downloadData = {
            ...currentAnalysisData,
            download_info: {
                downloaded_at: new Date().toISOString(),
                filename: filename,
                application: 'HeatSense Urban Heat Island Analyzer',
                version: '1.0'
            }
        };
        
        // Create blob and download
        const blob = new Blob([JSON.stringify(downloadData, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showSuccessMessage('Analyseergebnisse erfolgreich heruntergeladen');
        
    } catch (error) {
        console.error('Download failed:', error);
        showErrorMessage('Fehler beim Download: ' + error.message);
    }
}

/**
 * Toggle WFS dropdown menu
 */
function toggleWfsDropdown() {
    const dropdownContent = document.getElementById('wfs-dropdown-content');
    if (dropdownContent) {
        dropdownContent.classList.toggle('show');
    }
}

/**
 * Download WFS layer
 */
async function downloadWfsLayer(layerName, format) {
    try {
        // Build download URL
        const url = `/api/wfs/download/${layerName}?format=${format}`;
        
        // Create a temporary link and click it to trigger download
        const link = document.createElement('a');
        link.href = url;
        link.download = `${layerName}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Close dropdown
        const dropdownContent = document.getElementById('wfs-dropdown-content');
        if (dropdownContent) {
            dropdownContent.classList.remove('show');
        }
        
        showSuccessMessage(`${layerName} Layer erfolgreich heruntergeladen`);
        
    } catch (error) {
        console.error('WFS download failed:', error);
        showErrorMessage('Fehler beim WFS-Download: ' + error.message);
    }
}

/**
 * Close WFS dropdown when clicking outside
 */
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('wfs-dropdown');
    const dropdownContent = document.getElementById('wfs-dropdown-content');
    
    if (dropdown && dropdownContent && !dropdown.contains(event.target)) {
        dropdownContent.classList.remove('show');
    }
});

// Export functions for global access
window.updateAreaDropdown = updateAreaDropdown;
window.startAnalysis = startAnalysis;
window.toggleTemperatureLayer = toggleTemperatureLayer;
window.toggleHotspotsLayer = toggleHotspotsLayer;
window.toggleWeatherStations = toggleWeatherStations;
window.showInfo = showInfo;
window.showPrivacy = showPrivacy;
window.closeModal = closeModal;
window.downloadResults = downloadResults;
window.toggleWfsDropdown = toggleWfsDropdown;
window.downloadWfsLayer = downloadWfsLayer; 