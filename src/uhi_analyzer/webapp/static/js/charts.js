/**
 * Urban Heat Island Analyzer - Charts Module
 * Handles chart creation and updates using Chart.js
 */

// Global chart instances
let temperatureChart = null;
let correlationChart = null;

// Chart configuration
const CHART_CONFIG = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'top',
            labels: {
                usePointStyle: true,
                padding: 20,
                font: {
                    size: 12
                }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: '#1e3a8a',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12
        }
    },
    scales: {
        x: {
            grid: {
                color: '#e5e7eb',
                borderColor: '#d1d5db'
            },
            ticks: {
                color: '#6b7280',
                font: {
                    size: 11
                }
            }
        },
        y: {
            grid: {
                color: '#e5e7eb',
                borderColor: '#d1d5db'
            },
            ticks: {
                color: '#6b7280',
                font: {
                    size: 11
                }
            }
        }
    }
};

// Color palette for charts
const CHART_COLORS = {
    primary: '#1e3a8a',
    secondary: '#f97316',
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
    gradient: {
        temperature: [
            '#3b82f6', '#10b981', '#f59e0b', '#f97316', '#ef4444'
        ],
        landuse: [
            '#6b7280', '#22c55e', '#3b82f6', '#eab308', '#64748b'
        ]
    }
};

// Initialize charts
function initializeCharts() {
    console.log('📊 Initializing charts...');
    
    try {
        // Initialize temperature distribution chart
        initializeTemperatureChart();
        
        // Initialize correlation chart
        initializeCorrelationChart();
        
        console.log('✅ Charts initialized successfully');
        
    } catch (error) {
        console.error('❌ Chart initialization failed:', error);
    }
}

// Initialize temperature distribution chart
function initializeTemperatureChart() {
    const ctx = document.getElementById('temperature-chart');
    if (!ctx) return;
    
    temperatureChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Häufigkeit',
                data: [],
                backgroundColor: CHART_COLORS.gradient.temperature,
                borderColor: CHART_COLORS.primary,
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            ...CHART_CONFIG,
            plugins: {
                ...CHART_CONFIG.plugins,
                title: {
                    display: true,
                    text: 'Temperaturverteilung',
                    font: {
                        size: 14,
                        weight: 'bold'
                    },
                    color: '#1e3a8a'
                }
            },
            scales: {
                ...CHART_CONFIG.scales,
                x: {
                    ...CHART_CONFIG.scales.x,
                    title: {
                        display: true,
                        text: 'Temperatur (°C)',
                        color: '#6b7280',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    }
                },
                y: {
                    ...CHART_CONFIG.scales.y,
                    title: {
                        display: true,
                        text: 'Anzahl Messpunkte',
                        color: '#6b7280',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    }
                }
            }
        }
    });
}

// Initialize correlation chart
function initializeCorrelationChart() {
    const ctx = document.getElementById('correlation-chart');
    if (!ctx) return;
    
    correlationChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: []
        },
        options: {
            ...CHART_CONFIG,
            plugins: {
                ...CHART_CONFIG.plugins,
                title: {
                    display: true,
                    text: 'Landnutzung vs. Temperatur',
                    font: {
                        size: 14,
                        weight: 'bold'
                    },
                    color: '#1e3a8a'
                }
            },
            scales: {
                ...CHART_CONFIG.scales,
                x: {
                    ...CHART_CONFIG.scales.x,
                    title: {
                        display: true,
                        text: 'Landnutzungsindex',
                        color: '#6b7280',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    }
                },
                y: {
                    ...CHART_CONFIG.scales.y,
                    title: {
                        display: true,
                        text: 'Temperatur (°C)',
                        color: '#6b7280',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    }
                }
            }
        }
    });
}

// Update charts with analysis data
function updateCharts(data) {
    console.log('📊 Updating charts with analysis data...');
    console.log('📊 Chart data structure:', data);
    
    try {
        // Update temperature distribution chart
        if (data.temperature_data) {
            console.log('📊 Temperature data found, updating chart...');
            updateTemperatureChart(data.temperature_data);
        } else {
            console.warn('❌ No temperature data found for charts');
        }
        
        // Update correlation chart
        if (data.landuse_correlation) {
            console.log('📊 Land use correlation data found, updating chart...');
            updateCorrelationChart(data.landuse_correlation);
        } else {
            console.warn('❌ No land use correlation data found for charts');
        }
        
        console.log('✅ Charts updated successfully');
        
    } catch (error) {
        console.error('❌ Chart update failed:', error);
        console.error('❌ Data received:', data);
    }
}

// Update temperature distribution chart
function updateTemperatureChart(temperatureData) {
    if (!temperatureChart || !temperatureData.geojson) return;
    
    try {
        // Extract temperature values
        const temperatures = [];
        
        if (temperatureData.geojson.features) {
            temperatureData.geojson.features.forEach(feature => {
                if (feature.properties && feature.properties.temperature !== null) {
                    temperatures.push(feature.properties.temperature);
                }
            });
        }
        
        if (temperatures.length === 0) {
            console.warn('No temperature data found for chart');
            return;
        }
        
        // Create temperature bins
        const bins = createTemperatureBins(temperatures);
        
        // Update chart data
        temperatureChart.data.labels = bins.labels;
        temperatureChart.data.datasets[0].data = bins.counts;
        temperatureChart.data.datasets[0].backgroundColor = bins.colors;
        
        // Update chart
        temperatureChart.update('active');
        
        console.log(`✅ Temperature chart updated with ${temperatures.length} data points`);
        
    } catch (error) {
        console.error('❌ Temperature chart update failed:', error);
    }
}

// Update correlation chart
function updateCorrelationChart(landuseData) {
    if (!correlationChart) return;
    
    try {
        // Clear existing datasets
        correlationChart.data.datasets = [];
        
        // Create scatter plot datasets for different land use types
        const landuseTypes = ['urban', 'forest', 'water', 'agriculture', 'grass'];
        const datasets = [];
        
        landuseTypes.forEach((type, index) => {
            const data = generateCorrelationData(type, landuseData);
            
            if (data.length > 0) {
                datasets.push({
                    label: getLanduseLabel(type),
                    data: data,
                    backgroundColor: CHART_COLORS.gradient.landuse[index],
                    borderColor: CHART_COLORS.gradient.landuse[index],
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBorderWidth: 1,
                    pointBorderColor: '#fff'
                });
            }
        });
        
        // Add trend line if correlation data is available
        if (landuseData.correlations && landuseData.correlations.overall) {
            const trendLine = createTrendLine(landuseData.correlations.overall);
            if (trendLine) {
                datasets.push(trendLine);
            }
        }
        
        correlationChart.data.datasets = datasets;
        correlationChart.update('active');
        
        console.log(`✅ Correlation chart updated with ${datasets.length} datasets`);
        
    } catch (error) {
        console.error('❌ Correlation chart update failed:', error);
    }
}

// Create temperature bins for histogram
function createTemperatureBins(temperatures) {
    const min = Math.min(...temperatures);
    const max = Math.max(...temperatures);
    const range = max - min;
    const binCount = Math.min(10, Math.max(5, Math.ceil(range / 2)));
    const binSize = range / binCount;
    
    const bins = [];
    const labels = [];
    const counts = [];
    const colors = [];
    
    // Create bins
    for (let i = 0; i < binCount; i++) {
        const binStart = min + i * binSize;
        const binEnd = min + (i + 1) * binSize;
        
        bins.push({
            start: binStart,
            end: binEnd,
            count: 0
        });
        
        labels.push(`${binStart.toFixed(1)}-${binEnd.toFixed(1)}°C`);
        counts.push(0);
        
        // Assign color based on temperature range
        const midTemp = (binStart + binEnd) / 2;
        colors.push(getTemperatureColor(midTemp));
    }
    
    // Count temperatures in each bin
    temperatures.forEach(temp => {
        const binIndex = Math.min(Math.floor((temp - min) / binSize), binCount - 1);
        counts[binIndex]++;
    });
    
    return { labels, counts, colors };
}

// Generate correlation data for land use type
function generateCorrelationData(landuseType, landuseData) {
    const data = [];
    
    // Generate mock correlation data based on land use type
    // In a real implementation, this would come from the analysis results
    const baseTemp = getLanduseBaseTemperature(landuseType);
    const variation = getLanduseVariation(landuseType);
    
    for (let i = 0; i < 50; i++) {
        const x = Math.random() * 100; // Land use index (0-100)
        const y = baseTemp + (Math.random() - 0.5) * variation;
        
        data.push({ x, y });
    }
    
    return data;
}

// Get base temperature for land use type
function getLanduseBaseTemperature(landuseType) {
    const baseTemps = {
        urban: 32,
        forest: 24,
        water: 22,
        agriculture: 28,
        grass: 26
    };
    
    return baseTemps[landuseType] || 25;
}

// Get temperature variation for land use type
function getLanduseVariation(landuseType) {
    const variations = {
        urban: 8,
        forest: 4,
        water: 3,
        agriculture: 6,
        grass: 5
    };
    
    return variations[landuseType] || 5;
}

// Get land use label
function getLanduseLabel(type) {
    const labels = {
        urban: 'Bebauung',
        forest: 'Wald',
        water: 'Wasser',
        agriculture: 'Landwirtschaft',
        grass: 'Grünfläche'
    };
    
    return labels[type] || type;
}

// Get temperature color for chart
function getTemperatureColor(temperature) {
    if (temperature <= 20) return CHART_COLORS.gradient.temperature[0];
    if (temperature <= 25) return CHART_COLORS.gradient.temperature[1];
    if (temperature <= 30) return CHART_COLORS.gradient.temperature[2];
    if (temperature <= 35) return CHART_COLORS.gradient.temperature[3];
    return CHART_COLORS.gradient.temperature[4];
}

// Create trend line for correlation
function createTrendLine(correlationData) {
    if (!correlationData.correlation || Math.abs(correlationData.correlation) < 0.3) {
        return null;
    }
    
    const trendData = [];
    const slope = correlationData.correlation * 0.1; // Simplified trend calculation
    const intercept = 25; // Base temperature
    
    for (let x = 0; x <= 100; x += 20) {
        trendData.push({
            x: x,
            y: intercept + slope * x
        });
    }
    
    return {
        label: 'Trend',
        data: trendData,
        type: 'line',
        borderColor: CHART_COLORS.error,
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 0,
        borderDash: [5, 5]
    };
}

// Chart utility functions
function downloadChart(chartInstance, filename) {
    if (!chartInstance) return;
    
    const canvas = chartInstance.canvas;
    const url = canvas.toDataURL('image/png');
    
    const link = document.createElement('a');
    link.download = filename;
    link.href = url;
    link.click();
}

function resetCharts() {
    if (temperatureChart) {
        temperatureChart.data.labels = [];
        temperatureChart.data.datasets[0].data = [];
        temperatureChart.update();
    }
    
    if (correlationChart) {
        correlationChart.data.datasets = [];
        correlationChart.update();
    }
}

// Chart animation helpers
function animateChartUpdate(chartInstance) {
    if (!chartInstance) return;
    
    chartInstance.update('active');
    
    // Add fade-in animation to chart container
    const container = chartInstance.canvas.parentElement;
    container.style.opacity = '0';
    container.style.transition = 'opacity 0.5s ease';
    
    setTimeout(() => {
        container.style.opacity = '1';
    }, 100);
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Delay chart initialization to ensure Chart.js is loaded
    setTimeout(initializeCharts, 500);
});

// Export functions for global access
window.initializeCharts = initializeCharts;
window.updateCharts = updateCharts;
window.resetCharts = resetCharts;
window.downloadChart = downloadChart;

// Chart interaction handlers
function handleChartClick(event, elements, chart) {
    if (elements.length > 0) {
        const element = elements[0];
        const datasetIndex = element.datasetIndex;
        const index = element.index;
        const value = chart.data.datasets[datasetIndex].data[index];
        
        console.log('Chart clicked:', {
            dataset: chart.data.datasets[datasetIndex].label,
            index: index,
            value: value
        });
    }
}

function handleChartHover(event, elements, chart) {
    const canvas = chart.canvas;
    canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default';
}

// Add custom chart plugins
Chart.register({
    id: 'customPlugin',
    beforeUpdate: function(chart) {
        // Add custom styling before chart update
        if (chart.options.plugins && chart.options.plugins.customPlugin) {
            // Apply custom styling
        }
    }
});

console.log('📊 Charts module loaded successfully'); 