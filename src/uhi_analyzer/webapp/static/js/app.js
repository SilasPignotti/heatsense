/**
 * Urban Heat Island Analyzer - Main Application Logic
 * Handles user interactions, API calls, and UI updates
 */

// Add global error handler at the top of the file
window.addEventListener('error', function(event) {
    console.error('Global error caught:', event.error);
    console.error('Error message:', event.message);
    console.error('Error filename:', event.filename);
    console.error('Error line:', event.lineno);
    console.error('Error column:', event.colno);
    console.error('Error stack:', event.error ? event.error.stack : 'No stack available');
    
    // Check if this is the pattern matching error
    if (event.message && event.message.includes('pattern')) {
        console.error('🚨 Pattern matching error detected!');
        console.error('Full error details:', event);
    }
});

// Add unhandled promise rejection handler
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    console.error('Promise:', event.promise);
    
    // Check if this is the pattern matching error
    if (event.reason && event.reason.message && event.reason.message.includes('pattern')) {
        console.error('🚨 Pattern matching error in promise!');
        console.error('Full error details:', event);
    }
});

// Global variables
let currentAnalysis = null;
let progressInterval = null;
let availableAreas = [];
let performanceModes = {};
let currentAreaType = 'ortsteil';
let currentAnalysisController = null;
let areaData = {
    bundesland: ['Berlin'],
    bezirk: [
        'Charlottenburg-Wilmersdorf',
        'Friedrichshain-Kreuzberg',
        'Lichtenberg',
        'Marzahn-Hellersdorf',
        'Mitte',
        'Neukölln',
        'Pankow',
        'Reinickendorf',
        'Spandau',
        'Steglitz-Zehlendorf',
        'Tempelhof-Schöneberg',
        'Treptow-Köpenick'
    ],
    ortsteil: [
        'Adlershof',
        'Alt-Hohenschönhausen',
        'Alt-Treptow',
        'Biesdorf',
        'Blankenburg',
        'Blankenfelde',
        'Bohnsdorf',
        'Britz',
        'Buch',
        'Buckow',
        'Charlottenburg',
        'Charlottenburg-Nord',
        'Dahlem',
        'Falkenberg',
        'Falkenhagener Feld',
        'Fennpfuhl',
        'Französisch Buchholz',
        'Friedenau',
        'Friedrichsfelde',
        'Friedrichshagen',
        'Friedrichshain',
        'Frohnau',
        'Gatow',
        'Gesundbrunnen',
        'Gropiusstadt',
        'Grünau',
        'Grunewald',
        'Hakenfelde',
        'Haselhorst',
        'Heiligensee',
        'Hellersdorf',
        'Hermsdorf',
        'Johannisthal',
        'Karlshorst',
        'Karow',
        'Kaulsdorf',
        'Kladow',
        'Konradshöhe',
        'Köpenick',
        'Kreuzberg',
        'Lankwitz',
        'Lichtenberg',
        'Lichtenrade',
        'Lübars',
        'Malchow',
        'Mariendorf',
        'Marienfelde',
        'Märkisches Viertel',
        'Marzahn',
        'Mitte',
        'Müggelheim',
        'Neu-Hohenschönhausen',
        'Neukölln',
        'Niederschöneweide',
        'Niederschönhausen',
        'Nikolassee',
        'Oberschöneweide',
        'Pankow',
        'Plänterwald',
        'Prenzlauer Berg',
        'Rahnsdorf',
        'Reinickendorf',
        'Rosenthal',
        'Rummelsburg',
        'Rudow',
        'Schmargendorf',
        'Schmöckwitz',
        'Schöneberg',
        'Siemensstadt',
        'Spandau',
        'Staaken',
        'Steglitz',
        'Tegel',
        'Tempelhof',
        'Tiefwerder',
        'Waidmannslust',
        'Wannsee',
        'Wartenberg',
        'Wedding',
        'Weißensee',
        'Westend',
        'Wilhelmsruh',
        'Wilmersdorf',
        'Zehlendorf',
        'Zentralflughafen',
        'Zitadelle Spandau'
    ]
};

// Initialize the application
async function initializeApp() {
    console.log('🔥 Initializing Urban Heat Island Analyzer...');
    
    // Load initial data
    await loadAvailableAreas();
    await loadPerformanceModes();
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize default values
    setDefaultValues();
    
    // Initialize map
    initializeMap();
    
    console.log('✅ Application initialized successfully');
}

// Load available areas from API
async function loadAvailableAreas() {
    try {
        // Use local data instead of API call for now
        availableAreas = areaData[currentAreaType];
        populateAreaSelect(availableAreas, currentAreaType === 'bundesland' ? 'Berlin' : availableAreas[0]);
    } catch (error) {
        console.error('Error loading areas:', error);
        showError('Fehler beim Laden der verfügbaren Gebiete');
    }
}

// Load performance modes from API
async function loadPerformanceModes() {
    try {
        const response = await fetch('/api/performance-modes');
        performanceModes = await response.json();
        
        updatePerformanceModeDescriptions();
    } catch (error) {
        console.error('Error loading performance modes:', error);
        showError('Fehler beim Laden der Performance-Modi');
    }
}

// Populate area select dropdown
function populateAreaSelect(areas, defaultArea) {
    const areaSelect = document.getElementById('area-select');
    areaSelect.innerHTML = '<option value="">Gebiet auswählen...</option>';
    
    areas.forEach(area => {
        const option = document.createElement('option');
        option.value = area;
        option.textContent = area;
        if (area === defaultArea) {
            option.selected = true;
        }
        areaSelect.appendChild(option);
    });
}

// Handle area type change
function handleAreaTypeChange(event) {
    const selectedType = event.target.dataset.type;
    
    // Update active button
    document.querySelectorAll('.area-type-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Update current area type
    currentAreaType = selectedType;
    
    // Reload areas for the selected type
    loadAvailableAreas();
    
    console.log(`Area type changed to: ${selectedType}`);
}

// Update performance mode descriptions
function updatePerformanceModeDescriptions() {
    Object.keys(performanceModes).forEach(mode => {
        const modeData = performanceModes[mode];
        const label = document.querySelector(`label[for="mode-${mode}"]`);
        
        if (label) {
            const nameSpan = label.querySelector('.mode-name');
            const durationSpan = label.querySelector('.mode-duration');
            const descriptionDiv = label.querySelector('.mode-description');
            
            if (nameSpan) nameSpan.textContent = modeData.name;
            if (durationSpan) durationSpan.textContent = modeData.duration;
            if (descriptionDiv) descriptionDiv.textContent = modeData.description;
        }
    });
}

// Set default values
function setDefaultValues() {
    const today = new Date();
    const lastWeek = new Date(today);
    lastWeek.setDate(today.getDate() - 7);
    
    document.getElementById('start-date').value = lastWeek.toISOString().split('T')[0];
    document.getElementById('end-date').value = today.toISOString().split('T')[0];
    
    // Set default area type to 'ortsteil' (most commonly used)
    currentAreaType = 'ortsteil';
    document.querySelectorAll('.area-type-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.type === 'ortsteil') {
            btn.classList.add('active');
        }
    });
}

// Setup event listeners
function setupEventListeners() {
    // Form submission
    document.getElementById('analysis-form').addEventListener('submit', handleAnalysisSubmit);
    
    // Layer controls are handled in map.js setupLayerControls()
    
    // Performance mode changes
    document.querySelectorAll('input[name="performance_mode"]').forEach(radio => {
        radio.addEventListener('change', handlePerformanceModeChange);
    });
    
    // Area type buttons
    document.querySelectorAll('.area-type-btn').forEach(btn => {
        btn.addEventListener('click', handleAreaTypeChange);
    });
    
    // Modal close events
    document.addEventListener('click', handleModalClose);
    document.addEventListener('keydown', handleKeyPress);
}

// Handle analysis form submission
async function handleAnalysisSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const analysisParams = {
        area: formData.get('area'),
        start_date: formData.get('start_date'),
        end_date: formData.get('end_date'),
        performance_mode: formData.get('performance_mode')
    };
    
    // Validate form data
    if (!validateAnalysisParams(analysisParams)) {
        return;
    }
    
    // Cancel any ongoing analysis
    if (currentAnalysisController) {
        console.log('⚠️ Cancelling previous analysis...');
        currentAnalysisController.abort();
    }
    
    // Create new AbortController for this analysis
    currentAnalysisController = new AbortController();
    
    // Show loading state
    showLoading();
    
    try {
        // Start analysis
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(analysisParams),
            signal: currentAnalysisController.signal
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('Analysis result received:', result);
        console.log('Result type:', typeof result);
        console.log('Result keys:', Object.keys(result));
        
        if (result.status === 'error') {
            throw new Error(result.errors.join(', '));
        }
        
        // Check for any string validation issues in the result
        if (result.data) {
            console.log('Data keys:', Object.keys(result.data));
            // Check if any data contains invalid values
            for (const [key, value] of Object.entries(result.data)) {
                if (value && typeof value === 'object') {
                    console.log(`${key} structure:`, Object.keys(value));
                }
            }
        }
        
        // Handle successful analysis
        currentAnalysis = result;
        handleAnalysisComplete(result);
        
    } catch (error) {
        // Don't show error if request was cancelled
        if (error.name === 'AbortError') {
            console.log('🔄 Analysis cancelled by user');
            return;
        }
        
        console.error('Analysis error:', error);
        showError(`Analyse fehlgeschlagen: ${error.message}`);
    } finally {
        hideLoading();
        // Reset controller after analysis completes
        if (currentAnalysisController) {
            currentAnalysisController = null;
        }
    }
}

// Validate analysis parameters
function validateAnalysisParams(params) {
    if (!params.area) {
        showError('Bitte wählen Sie ein Gebiet aus');
        return false;
    }
    
    if (!params.start_date || !params.end_date) {
        showError('Bitte geben Sie einen vollständigen Zeitraum an');
        return false;
    }
    
    const startDate = new Date(params.start_date);
    const endDate = new Date(params.end_date);
    
    if (startDate >= endDate) {
        showError('Das Startdatum muss vor dem Enddatum liegen');
        return false;
    }
    
    const daysDiff = (endDate - startDate) / (1000 * 60 * 60 * 24);
    if (daysDiff > 365) {
        showError('Der Zeitraum darf maximal 365 Tage betragen');
        return false;
    }
    
    if (daysDiff < 0) {
        showError('Das Startdatum muss vor dem Enddatum liegen');
        return false;
    }
    
    return true;
}

// Handle analysis completion
function handleAnalysisComplete(result) {
    console.log('📊 Analysis completed:', result);
    
    // Set progress to 100%
    const progressFill = document.getElementById('progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const sidebarProgress = document.getElementById('sidebar-progress-fill');
    const sidebarPercent = document.getElementById('sidebar-progress-percent');
    
    if (progressFill) progressFill.style.width = '100%';
    if (progressPercent) progressPercent.textContent = '100%';
    if (sidebarProgress) sidebarProgress.style.width = '100%';
    if (sidebarPercent) sidebarPercent.textContent = '100%';
    
    // Clear any remaining progress interval
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
    
    try {
        // Validate result structure
        if (!result || typeof result !== 'object') {
            throw new Error('Invalid result structure');
        }
        
        if (!result.data || typeof result.data !== 'object') {
            throw new Error('Missing or invalid data in result');
        }
        
        console.log('📊 Data structure:', Object.keys(result.data));
        
        // Update statistics
        updateStatistics(result.data);
        
        // Update map (if updateMap function exists)
        if (typeof updateMap === 'function') {
            updateMap(result.data);
        } else {
            console.warn('updateMap function not found, skipping map update');
        }
        
        // Update charts
        updateCharts(result.data);
        
        // Show success message
        showSuccess(`Analyse erfolgreich abgeschlossen in ${result.execution_time}s`);
        
        // Add fade-in animation to results
        document.querySelectorAll('.summary-cards .card').forEach((card, index) => {
            setTimeout(() => {
                card.classList.add('fade-in');
            }, index * 100);
        });
        
    } catch (error) {
        console.error('Error in handleAnalysisComplete:', error);
        console.error('Result structure:', result);
        showError(`Fehler beim Verarbeiten der Ergebnisse: ${error.message}`);
    }
}

// Update statistics cards
function updateStatistics(data) {
    try {
        console.log('📊 Updating statistics with data:', data);
        
        const tempData = data.temperature_data;
        const hotspots = data.hotspots;
        const landuse = data.landuse_correlation;
        const recommendations = data.recommendations;
        
        // Temperature statistics
        if (tempData && tempData.statistics) {
            const stats = tempData.statistics;
            const avgElement = document.getElementById('avg-temperature');
            const maxElement = document.getElementById('max-temperature');
            const minElement = document.getElementById('min-temperature');
            
            if (avgElement) avgElement.textContent = stats.mean ? `${stats.mean.toFixed(1)}°C` : '--°C';
            if (maxElement) maxElement.textContent = stats.max ? `${stats.max.toFixed(1)}°C` : '--°C';
            if (minElement) minElement.textContent = stats.min ? `${stats.min.toFixed(1)}°C` : '--°C';
        } else {
            console.warn('No temperature data found');
        }
        
        // Hotspots statistics
        if (hotspots) {
            const countElement = document.getElementById('hotspots-count');
            const maxElement = document.getElementById('hotspots-max');
            const sizeElement = document.getElementById('hotspots-size');
            
            if (countElement) countElement.textContent = hotspots.count || '--';
            if (maxElement) maxElement.textContent = 
                hotspots.temperature_range?.max ? `${hotspots.temperature_range.max.toFixed(1)}°C` : '--°C';
            if (sizeElement) sizeElement.textContent = 
                hotspots.count ? `${(hotspots.count * 0.3).toFixed(1)}km²` : '--';
        } else {
            console.warn('No hotspots data found');
        }
        
        // Land use correlation
        if (landuse && landuse.correlations) {
            const correlation = landuse.correlations.overall?.correlation || 0;
            const correlationElement = document.getElementById('landuse-correlation');
            const urbanElement = document.getElementById('landuse-urban');
            const greenElement = document.getElementById('landuse-green');
            
            if (correlationElement) correlationElement.textContent = 
                correlation ? correlation.toFixed(3) : '--';
            
            // Update percentages (mock data for now)
            if (urbanElement) urbanElement.textContent = '65%';
            if (greenElement) greenElement.textContent = '20%';
        } else {
            console.warn('No land use correlation data found');
        }
        
        // Recommendations
        if (recommendations) {
            const count = recommendations.strategies ? recommendations.strategies.length : 
                         Array.isArray(recommendations) ? recommendations.length : 0;
            const recElement = document.getElementById('recommendations-count');
            if (recElement) recElement.textContent = count || '--';
        } else {
            console.warn('No recommendations data found');
        }
        
    } catch (error) {
        console.error('Error in updateStatistics:', error);
        console.error('Data received:', data);
        throw error;
    }
}

// Handle performance mode change
function handlePerformanceModeChange(event) {
    const mode = event.target.value;
    const modeData = performanceModes[mode];
    
    if (modeData) {
        // Update advanced options based on mode
        const weatherCheckbox = document.getElementById('include-weather');
        const cacheCheckbox = document.getElementById('use-cache');
        
        if (mode === 'detailed') {
            weatherCheckbox.checked = true;
            weatherCheckbox.disabled = true;
        } else {
            weatherCheckbox.disabled = false;
        }
        
        // Show performance info
        console.log(`Performance mode changed to: ${modeData.name} (${modeData.duration})`);
    }
}

// Show loading overlay
function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    overlay.classList.remove('hidden');
    
    // Start progress simulation
    startProgressSimulation();
}

// Hide loading overlay
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    overlay.classList.add('hidden');
    
    // Stop progress simulation
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

// Start progress simulation
function startProgressSimulation() {
    let progress = 0;
    let step = 0;
    let startTime = Date.now();
    
    const steps = [
        'Eingaben werden verarbeitet...',
        'Grenzdaten werden geladen...',
        'Landnutzungsdaten werden abgerufen...',
        'Wetterdaten werden gesammelt...',
        'Analysemodell wird konfiguriert...',
        'Wärmeinselanalyse wird durchgeführt...',
        'Ergebnisse werden aufbereitet...'
    ];
    
    progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        progress = Math.min(progress, 95);
        
        const currentTime = Date.now();
        const elapsedTime = (currentTime - startTime) / 1000;
        
        // Update progress bar
        const progressFill = document.getElementById('progress-fill');
        const progressPercent = document.getElementById('progress-percent');
        const progressTime = document.getElementById('progress-time');
        const loadingStep = document.getElementById('loading-step');
        
        if (progressFill) progressFill.style.width = `${progress}%`;
        if (progressPercent) progressPercent.textContent = `${Math.round(progress)}%`;
        if (progressTime) progressTime.textContent = `${elapsedTime.toFixed(1)}s`;
        
        // Update step
        const newStep = Math.min(Math.floor(progress / 15), steps.length - 1);
        if (newStep !== step && loadingStep) {
            step = newStep;
            loadingStep.textContent = steps[step];
        }
        
        // Update sidebar progress
        const sidebarProgress = document.getElementById('sidebar-progress-fill');
        const sidebarPercent = document.getElementById('sidebar-progress-percent');
        const sidebarTime = document.getElementById('sidebar-progress-time');
        const progressSection = document.getElementById('progress-section');
        
        if (sidebarProgress) sidebarProgress.style.width = `${progress}%`;
        if (sidebarPercent) sidebarPercent.textContent = `${Math.round(progress)}%`;
        if (sidebarTime) sidebarTime.textContent = `${elapsedTime.toFixed(1)}s`;
        if (progressSection) progressSection.classList.remove('hidden');
        
        // Stop at 98% to wait for actual completion
        if (progress >= 98) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
    }, 500);
}

// Show error message
function showError(message) {
    const modal = document.getElementById('error-modal');
    const messageElement = document.getElementById('error-message');
    
    messageElement.textContent = message;
    modal.classList.remove('hidden');
    
    console.error('Error:', message);
}

// Hide error message
function hideError() {
    const modal = document.getElementById('error-modal');
    modal.classList.add('hidden');
}

// Show success message
function showSuccess(message) {
    const modal = document.getElementById('success-modal');
    const messageElement = document.getElementById('success-message');
    
    messageElement.textContent = message;
    modal.classList.remove('hidden');
    
    console.log('Success:', message);
}

// Hide success message
function hideSuccess() {
    const modal = document.getElementById('success-modal');
    modal.classList.add('hidden');
}

// Show recommendations modal
function showRecommendations() {
    if (!currentAnalysis || !currentAnalysis.data.recommendations) {
        showError('Keine Empfehlungen verfügbar. Führen Sie zuerst eine Analyse durch.');
        return;
    }
    
    const modal = document.getElementById('recommendations-modal');
    const content = document.getElementById('recommendations-content');
    
    // Clear previous content
    content.innerHTML = '';
    
    // Get recommendations
    const recommendations = currentAnalysis.data.recommendations;
    const strategies = recommendations.strategies || recommendations;
    
    if (Array.isArray(strategies) && strategies.length > 0) {
        const list = document.createElement('ul');
        list.style.listStyle = 'none';
        list.style.padding = '0';
        
        strategies.forEach((strategy, index) => {
            const listItem = document.createElement('li');
            listItem.style.marginBottom = '1rem';
            listItem.style.padding = '1rem';
            listItem.style.backgroundColor = '#f9fafb';
            listItem.style.borderRadius = '8px';
            listItem.style.border = '1px solid #e5e7eb';
            
            const title = document.createElement('h4');
            title.textContent = `${index + 1}. ${strategy.title || strategy.name || 'Empfehlung'}`;
            title.style.marginBottom = '0.5rem';
            title.style.color = '#1e3a8a';
            
            const description = document.createElement('p');
            description.textContent = strategy.description || strategy.text || strategy;
            description.style.margin = '0';
            description.style.color = '#4b5563';
            
            listItem.appendChild(title);
            listItem.appendChild(description);
            list.appendChild(listItem);
        });
        
        content.appendChild(list);
    } else {
        content.innerHTML = '<p>Keine spezifischen Empfehlungen verfügbar.</p>';
    }
    
    modal.classList.remove('hidden');
}

// Hide recommendations modal
function hideRecommendations() {
    const modal = document.getElementById('recommendations-modal');
    modal.classList.add('hidden');
}

// Project Info Modal Functions
function showProjectInfo() {
    const modal = document.getElementById('project-info-modal');
    modal.classList.remove('hidden');
}

function hideProjectInfo() {
    const modal = document.getElementById('project-info-modal');
    modal.classList.add('hidden');
}

// Handle modal close events
function handleModalClose(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.add('hidden');
    }
}

// Handle keyboard events
function handleKeyPress(event) {
    if (event.key === 'Escape') {
        // Close any open modals
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.add('hidden');
        });
    }
}

// Layer toggle functions are implemented in map.js

// Export functions for global access
window.showRecommendations = showRecommendations;
window.hideRecommendations = hideRecommendations;
window.showError = showError;
window.hideError = hideError;
window.showSuccess = showSuccess;
window.hideSuccess = hideSuccess;
// Layer toggle functions are exported from map.js 