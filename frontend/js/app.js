// Global state to hold all dashboard data
let dashboardData = {};
let allCharts = {};
let map;
let geojsonLayer;
let mapLegend;

// --- Chart.js Global Config ---
Chart.defaults.color = '#9ca3af';
Chart.defaults.borderColor = '#374151';
Chart.defaults.font.family = 'Inter';
Chart.defaults.plugins.legend.position = 'bottom';

// --- 1. Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    // Set current date
    document.getElementById('current-date').textContent = `Dashboard loaded on: ${new Date().toLocaleString()}`;
    
    // Initialize all charts and map
    initializeCharts();
    initializeMap();
    
    // Add event listeners
    setupEventListeners();
    
    // Load initial data from server
    loadInitialData();
});

function setupEventListeners() {
    // File upload logic
    const fileInputs = document.querySelectorAll('.file-input');
    const runModelBtn = document.getElementById('runModelBtn');
    
    let uploadedFiles = {};
    
    fileInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            const parentDiv = e.target.parentElement;
            const statusText = parentDiv.querySelector('p');
            
            if (file) {
                statusText.textContent = file.name;
                statusText.classList.remove('text-gray-500');
                statusText.classList.add('text-green-400');
                uploadedFiles[e.target.id] = file;
            } else {
                statusText.textContent = 'Not Uploaded';
                statusText.classList.add('text-gray-500');
                statusText.classList.remove('text-green-400');
                delete uploadedFiles[e.target.id];
            }
            
            // Enable button only if all 6 files are uploaded
            runModelBtn.disabled = Object.keys(uploadedFiles).length !== 6;
        });
    });

    // Run Analysis Button
    runModelBtn.addEventListener('click', handleRunAnalysis);
    
    // Dropdown listeners
    document.getElementById('districtForecastSelect').addEventListener('change', updateForecastChart);
    document.getElementById('districtProfileSelect').addEventListener('change', updateProfileChart);
    document.getElementById('factorSelect').addEventListener('change', updateCorrelationChart);

    // NLP Button
    document.getElementById('runNlpBtn').addEventListener('click', handleNlpAnalysis);
}

// --- 2. Data Fetching ---

async function loadInitialData() {
    const statusEl = document.getElementById('status');
    statusEl.textContent = 'Loading initial data from server...';
    try {
        // Fetch all data in one go
        const response = await fetch('/api/all-data');
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || `Server error: ${response.statusText}`);
        }
        dashboardData = await response.json();
        
        // Fetch map data
        const mapResponse = await fetch('/api/map-geojson');
        if (!mapResponse.ok) {
            const err = await mapResponse.json();
            throw new Error(err.detail || `Server error: ${mapResponse.statusText}`);
        }
        dashboardData.geojson = await mapResponse.json();

        // Populate all components
        populateAll();
        statusEl.textContent = 'Dashboard is ready.';
        statusEl.classList.remove('text-red-400');
        statusEl.classList.add('text-green-400');
        document.getElementById('summary-section').classList.remove('hidden');

    } catch (error) {
        console.error('Error loading initial data:', error);
        statusEl.textContent = `Error: ${error.message}. Please upload 6 CSV files.`;
        statusEl.classList.add('text-red-400');
    }
}

async function handleRunAnalysis() {
    const runModelBtn = document.getElementById('runModelBtn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');
    const statusEl = document.getElementById('status');
    
    // Show loading state
    runModelBtn.disabled = true;
    btnText.textContent = 'Analyzing...';
    btnSpinner.classList.remove('hidden');
    statusEl.textContent = 'Uploading files to server...';
    
    const formData = new FormData();
    for (let i = 1; i <= 6; i++) {
        formData.append('files', document.getElementById(`file${i}`).files[0]);
    }
    
    try {
        const response = await fetch('/api/upload-and-analyze', {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Analysis failed');
        }
        
        await response.json(); // Wait for success message
        statusEl.textContent = 'Analysis complete. Reloading dashboard...';
        
        // Reload all data
        await loadInitialData();
        
    } catch (error) {
        console.error('Error running analysis:', error);
        statusEl.textContent = `Error: ${error.message}`;
        statusEl.classList.add('text-red-400');
    } finally {
        // Hide loading state
        runModelBtn.disabled = false;
        btnText.textContent = 'Run Full Analysis';
        btnSpinner.classList.add('hidden');
    }
}

async function handleNlpAnalysis() {
    const text = document.getElementById('nlp-input').value;
    if (!text) {
        alert('Please paste some text to analyze.');
        return;
    }

    const btn = document.getElementById('runNlpBtn');
    const btnText = document.getElementById('nlp-btn-text');
    const spinner = document.getElementById('nlp-spinner');
    const resultsEl = document.getElementById('nlp-results');
    
    // Show loading state
    btn.disabled = true;
    btnText.textContent = 'Analyzing...';
    spinner.classList.remove('hidden');
    resultsEl.classList.add('hidden');

    try {
        const formData = new FormData();
        formData.append('text', text);

        const response = await fetch('/api/analyze-text', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'NLP analysis failed');
        }

        const results = await response.json();
        
        // Populate results
        document.getElementById('nlp-summary').textContent = results.summary;
        
        const entitiesContainer = document.getElementById('nlp-entities');
        entitiesContainer.innerHTML = ''; // Clear old entities
        
        const tagMap = {
            'PERSON': 'nlp-tag-PERSON',
            'ORG': 'nlp-tag-ORG',
            'GPE': 'nlp-tag-GPE',
            'LOC': 'nlp-tag-LOC',
            'DATE': 'nlp-tag-DATE',
            'TIME': 'nlp-tag-TIME',
            'CARDINAL': 'nlp-tag-CARDINAL',
        };
        
        if (results.entities.length === 0) {
            entitiesContainer.innerHTML = '<p class="text-gray-400">No entities found.</p>';
        } else {
            results.entities.forEach(ent => {
                const tag = document.createElement('span');
                const tagClass = tagMap[ent.label] || 'nlp-tag-DEFAULT';
                tag.className = `nlp-tag ${tagClass}`;
                tag.innerHTML = `${ent.text} <strong class="opacity-75">(${ent.label})</strong>`;
                entitiesContainer.appendChild(tag);
            });
        }
        
        resultsEl.classList.remove('hidden');

    } catch (error) {
        console.error('NLP Error:', error);
        alert(`Error during analysis: ${error.message}`);
    } finally {
        // Hide loading state
        btn.disabled = false;
        btnText.textContent = 'Analyze Text';
        spinner.classList.add('hidden');
    }
}


// --- 3. UI Population ---

function populateAll() {
    populateSummaryCards();
    populateDropdowns();
    updateAllCharts();
    updateMap();
}

function populateSummaryCards() {
    const { summary_stats } = dashboardData;
    if (!summary_stats) return;

    document.getElementById('highest-crime-district').textContent = summary_stats.highest_crime_district;
    document.getElementById('highest-crime-rate').textContent = `Rate: ${summary_stats.highest_crime_rate}`;
    document.getElementById('average-crime-rate').textContent = summary_stats.average_crime_rate;
    document.getElementById('highest-severity-district').textContent = summary_stats.highest_severity_district;
    document.getElementById('highest-severity-score').textContent = `Score: ${summary_stats.highest_severity_score}`;
    document.getElementById('total-population').textContent = summary_stats.total_population;
}

function populateDropdowns() {
    const { districts_list } = dashboardData;
    if (!districts_list) return;

    const forecastSelect = document.getElementById('districtForecastSelect');
    const profileSelect = document.getElementById('districtProfileSelect');
    
    forecastSelect.innerHTML = '';
    profileSelect.innerHTML = '';

    districts_list.forEach(district => {
        const option1 = new Option(district, district);
        const option2 = new Option(district, district);
        forecastSelect.add(option1);
        profileSelect.add(option2);
    });

    // Set to first district by default
    forecastSelect.selectedIndex = 0;
    profileSelect.selectedIndex = 0;
}

function updateAllCharts() {
    updateImportanceChart();
    updateDistrictChart();
    updateSeverityChart();
    updateRiskAnalysisChart();
    updateCorrelationChart();
    updateClusterChart();
    
    // Update charts that depend on dropdowns
    updateForecastChart(); // Will fetch data for the first district
    updateProfileChart();
}

// --- 4. Map Initialization & Update ---

function initializeMap() {
    map = L.map('map').setView([10.79, 78.70], 7); // Centered on Tamil Nadu
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    // Add legend
    mapLegend = L.control({ position: 'bottomright' });
    mapLegend.onAdd = function (map) {
        const div = L.DomUtil.create('div', 'legend');
        const grades = [0, 100, 200, 300, 400, 500];
        const colors = getMapColors();
        
        div.innerHTML = '<h4>Crime Rate (per 1L)</h4>';
        for (let i = 0; i < grades.length; i++) {
            div.innerHTML +=
                '<i style="background:' + colors[i] + '"></i> ' +
                grades[i] + (grades[i + 1] ? '&ndash;' + grades[i + 1] + '<br>' : '+');
        }
        return div;
    };
    mapLegend.addTo(map);
}

function getMapColor(rate) {
    const colors = getMapColors();
    return rate > 500 ? colors[5] :
           rate > 400 ? colors[4] :
           rate > 300 ? colors[3] :
           rate > 200 ? colors[2] :
           rate > 100 ? colors[1] :
                        colors[0];
}
function getMapColors() {
    return ['#3b82f6', '#2563eb', '#facc15', '#f59e0b', '#dc2626', '#b91c1c'];
}

function updateMap() {
    const geojsonData = dashboardData.geojson;
    if (!geojsonData) {
        console.warn("No GeoJSON data to update map.");
        return;
    }

    if (geojsonLayer) {
        map.removeLayer(geojsonLayer);
    }

    geojsonLayer = L.geoJson(geojsonData, {
        style: function(feature) {
            return {
                fillColor: getMapColor(feature.properties.Crime_Rate_2022),
                weight: 2,
                opacity: 1,
                color: '#4b5563',
                fillOpacity: 0.7
            };
        },
        onEachFeature: function(feature, layer) {
            layer.on({
                mouseover: (e) => e.target.setStyle({ weight: 4, color: '#f3f4f6', fillOpacity: 0.9 }),
                mouseout: (e) => geojsonLayer.resetStyle(e.target),
                click: (e) => map.fitBounds(e.target.getBounds())
            });
            
            // Popup content
            const props = feature.properties;
            const popupContent = `
                <h4>${props.DISTRICT}</h4>
                <p><strong>Crime Rate:</strong> ${props.Crime_Rate_2022?.toFixed(2) || 'N/A'}</p>
                <p><strong>Total Crimes:</strong> ${props.Total_Crimes?.toLocaleString() || 'N/A'}</p>
                <p><strong>Severity Score:</strong> ${props.Severity_Score?.toFixed(2) || 'N/A'}</p>
                <p><strong>Population:</strong> ${props.Population?.toLocaleString() || 'N/A'}</p>
            `;
            layer.bindPopup(popupContent);
        }
    }).addTo(map);
}

// --- 5. Chart Initialization & Updates ---

function initializeCharts() {
    const chartContexts = [
        'importanceChart', 'districtChart', 'forecastChart', 'profileChart',
        'severityChart', 'riskAnalysisChart', 'correlationChart', 'clusterChart'
    ];
    chartContexts.forEach(id => {
        const ctx = document.getElementById(id);
        if (ctx) {
            allCharts[id] = new Chart(ctx.getContext('2d'), {
                type: 'bar', // Default type
                data: { labels: [], datasets: [] },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                }
            });
        }
    });
}

// --- Specific Chart Update Functions ---

function updateImportanceChart() {
    const { rf_importance } = dashboardData;
    if (!rf_importance || !allCharts.importanceChart) return;

    allCharts.importanceChart.config.type = 'bar';
    allCharts.importanceChart.data = {
        labels: rf_importance.features,
        datasets: [{
            label: 'Feature Importance Score',
            data: rf_importance.importance,
            backgroundColor: '#22c55e',
        }]
    };
    allCharts.importanceChart.options = {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { title: { display: true, text: 'Importance Score' } }
        },
        plugins: {
            legend: { display: false }
        }
    };
    allCharts.importanceChart.update();
}

function updateDistrictChart() {
    const { district_crime_rates } = dashboardData;
    if (!district_crime_rates || !allCharts.districtChart) return;

    allCharts.districtChart.config.type = 'bar';
    allCharts.districtChart.data = {
        labels: district_crime_rates.map(d => d.District),
        datasets: [{
            label: 'Crime Rate 2022',
            data: district_crime_rates.map(d => d.Crime_Rate_2022),
            backgroundColor: '#f59e0b',
        }]
    };
    allCharts.districtChart.options = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: { title: { display: true, text: 'Crime Rate per 1 Lakh' } }
        },
        plugins: {
            legend: { display: false }
        }
    };
    allCharts.districtChart.update();
}

function updateSeverityChart() {
    const { district_severity_scores } = dashboardData;
    if (!district_severity_scores || !allCharts.severityChart) return;

    allCharts.severityChart.config.type = 'bar';
    allCharts.severityChart.data = {
        labels: district_severity_scores.map(d => d.District),
        datasets: [{
            label: 'Severity Score',
            data: district_severity_scores.map(d => d.Severity_Score),
            backgroundColor: '#ef4444',
        }]
    };
    allCharts.severityChart.options = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: { title: { display: true, text: 'Severity Score' } }
        },
        plugins: {
            legend: { display: false }
        }
    };
    allCharts.severityChart.update();
}

function updateRiskAnalysisChart() {
    const { risk_analysis_data } = dashboardData;
    if (!risk_analysis_data || !allCharts.riskAnalysisChart) return;

    allCharts.riskAnalysisChart.config.type = 'bubble';
    allCharts.riskAnalysisChart.data = {
        datasets: [{
            label: 'District Risk Profile',
            data: risk_analysis_data.map(d => ({
                x: d.Suicide_Rate,
                y: d.Road_Accident_Rate,
                r: d.Crime_Rate_2022 / 20, // Scale bubble size
                label: d.District
            })),
            backgroundColor: 'rgba(20, 184, 166, 0.6)',
            borderColor: '#0d9488',
        }]
    };
    allCharts.riskAnalysisChart.options = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { title: { display: true, text: 'Suicide Rate' } },
            y: { title: { display: true, text: 'Road Accident Rate' } }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const d = context.raw;
                        return `${d.label}: (Suicide: ${d.x.toFixed(2)}, Accident: ${d.y.toFixed(2)}, Crime Rate: ${(d.r * 20).toFixed(2)})`;
                    }
                }
            }
        }
    };
    allCharts.riskAnalysisChart.update();
}

function updateCorrelationChart() {
    const { correlation_data } = dashboardData;
    const factor = document.getElementById('factorSelect').value;
    if (!correlation_data || !allCharts.correlationChart) return;

    allCharts.correlationChart.config.type = 'scatter';
    allCharts.correlationChart.data = {
        datasets: [{
            label: `Crime Rate vs ${factor}`,
            data: correlation_data.map(d => ({
                x: d[factor],
                y: d.Crime_Rate_2022,
                label: d.District
            })),
            backgroundColor: 'rgba(236, 72, 153, 0.6)',
            borderColor: '#db2777',
        }]
    };
    allCharts.correlationChart.options = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { title: { display: true, text: factor } },
            y: { title: { display: true, text: 'Crime Rate 2022' } }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const d = context.raw;
                        return `${d.label}: (${d.x.toFixed(2)}, ${d.y.toFixed(2)})`;
                    }
                }
            }
        }
    };
    allCharts.correlationChart.update();
}

function updateClusterChart() {
    const { kmeans_clusters } = dashboardData;
    if (!kmeans_clusters || !allCharts.clusterChart) return;

    allCharts.clusterChart.config.type = 'doughnut';
    allCharts.clusterChart.data = {
        labels: kmeans_clusters.labels,
        datasets: [{
            label: 'District Clusters',
            data: kmeans_clusters.counts,
            backgroundColor: ['#f97316', '#a855f7', '#10b981', '#3b82f6'],
        }]
    };
    allCharts.clusterChart.options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: true, position: 'right' }
        }
    };
    allCharts.clusterChart.update();
}

// --- DYNAMIC CHARTS (require fetching) ---

async function updateForecastChart() {
    const district = document.getElementById('districtForecastSelect').value;
    if (!district || !allCharts.forecastChart) return;

    try {
        const response = await fetch(`/api/forecast/${district}`);
        if (!response.ok) throw new Error('Forecast data not found');
        const data = await response.json();

        allCharts.forecastChart.config.type = 'line';
        allCharts.forecastChart.data = {
            labels: data.forecast_dates,
            datasets: [
                {
                    label: 'Historical Count',
                    data: data.history_values,
                    borderColor: '#a855f7',
                    backgroundColor: '#a855f7',
                    fill: false,
                    stepped: true,
                },
                {
                    label: 'Forecast (2023)',
                    data: data.forecast_values.slice(-1), // Only the last (future) point
                    borderColor: '#f43f5e',
                    backgroundColor: '#f43f5e',
                    pointRadius: 6,
                },
                {
                    label: 'Confidence Interval',
                    data: [data.history_values[data.history_values.length - 1], ...data.forecast_values.slice(-1)], // Connect history to forecast
                    borderColor: 'rgba(244, 63, 94, 0.2)',
                    backgroundColor: 'rgba(244, 63, 94, 0.2)',
                    fill: '+1', // Fill to next dataset
                },
                {
                    label: 'Confidence Upper',
                    data: [data.history_values[data.history_values.length - 1], ...data.forecast_upper.slice(-1)],
                    borderColor: 'transparent',
                    fill: false,
                }
            ]
        };
        allCharts.forecastChart.options = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { title: { display: true, text: 'Total Crime Count' } }
            },
            plugins: {
                legend: { display: true }
            }
        };
        allCharts.forecastChart.update();

    } catch (error) {
        console.error('Error fetching forecast:', error);
    }
}

function updateProfileChart() {
    const { profile_data } = dashboardData;
    const district = document.getElementById('districtProfileSelect').value;
    if (!profile_data || !allCharts.profileChart) return;

    const data = profile_data.find(d => d.District === district);
    if (!data) return;

    const profileLabels = ['Harassment', 'Road_Accidents', 'Murder', 'Rape', 'Suicides', 'Deaths'];
    const profileValues = [
        data.Harassment, data.Road_Accidents, data.Murder, 
        data.Rape, data.Suicides, data.Deaths
    ];

    allCharts.profileChart.config.type = 'pie';
    allCharts.profileChart.data = {
        labels: profileLabels,
        datasets: [{
            label: `Crime Profile for ${district}`,
            data: profileValues,
            backgroundColor: [
                '#f59e0b', '#0ea5e9', '#ef4444', 
                '#db2777', '#14b8a6', '#6b7280'
            ],
        }]
    };
    allCharts.profileChart.options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: true, position: 'right' }
        }
    };
    allCharts.profileChart.update();
}