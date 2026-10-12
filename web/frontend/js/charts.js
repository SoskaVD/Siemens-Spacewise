/**
 * Chart.js visualizations for Siemens Spacewise Simulator
 * Handles all chart rendering and updates
 */

// Chart instances
let hourlyChart = null;
let categoryChart = null;
let topMachinesChart = null;

/**
 * Render hourly consumption line chart (8760 points)
 * @param {Array} data - Array of hourly data points
 */
function renderHourlyChart(data) {
    const ctx = document.getElementById('hourly-chart').getContext('2d');
    
    // Destroy existing chart if present
    if (hourlyChart) {
        hourlyChart.destroy();
    }

    // Prepare data
    const labels = data.map(d => d.ts);
    const totalPower = data.map(d => d.total_power_kw);
    const hvac = data.map(d => d.hvac_power_kw || 0);
    const compressors = data.map(d => d.compressors_power_kw || 0);
    const motors = data.map(d => d.motors_power_kw || 0);

    hourlyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Potencia Total (kW)',
                    data: totalPower,
                    borderColor: 'rgb(0, 150, 136)',
                    backgroundColor: 'rgba(0, 150, 136, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0, // Hide points for performance with 8760 points
                    pointHoverRadius: 3
                },
                {
                    label: 'HVAC (kW)',
                    data: hvac,
                    borderColor: 'rgb(33, 150, 243)',
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    borderWidth: 1,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 2,
                    hidden: true
                },
                {
                    label: 'Compresores (kW)',
                    data: compressors,
                    borderColor: 'rgb(255, 152, 0)',
                    backgroundColor: 'rgba(255, 152, 0, 0.1)',
                    borderWidth: 1,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 2,
                    hidden: true
                },
                {
                    label: 'Motores (kW)',
                    data: motors,
                    borderColor: 'rgb(156, 39, 176)',
                    backgroundColor: 'rgba(156, 39, 176, 0.1)',
                    borderWidth: 1,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 2,
                    hidden: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 3,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        title: function(context) {
                            return context[0].label;
                        },
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)} kW`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Fecha y Hora'
                    },
                    ticks: {
                        maxTicksLimit: 12, // Show only 12 ticks to avoid crowding
                        maxRotation: 45,
                        minRotation: 0
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Potencia (kW)'
                    },
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString('es-ES') + ' kW';
                        }
                    }
                }
            }
        }
    });
}

/**
 * Render consumption by category pie/doughnut chart
 * @param {object} categoryData - Object with category names as keys and energy values
 */
function renderCategoryChart(categoryData) {
    const ctx = document.getElementById('category-chart').getContext('2d');
    
    // Destroy existing chart if present
    if (categoryChart) {
        categoryChart.destroy();
    }

    // Prepare data
    const labels = Object.keys(categoryData);
    const values = Object.values(categoryData);
    
    // Color palette (accessible, high contrast)
    const colors = [
        'rgb(0, 150, 136)',   // Teal
        'rgb(33, 150, 243)',  // Blue
        'rgb(255, 152, 0)',   // Orange
        'rgb(156, 39, 176)',  // Purple
        'rgb(244, 67, 54)',   // Red
        'rgb(76, 175, 80)',   // Green
        'rgb(121, 85, 72)',   // Brown
        'rgb(63, 81, 181)',   // Indigo
        'rgb(255, 87, 34)'    // Deep Orange
    ];

    categoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.2,
            plugins: {
                legend: {
                    display: true,
                    position: 'right',
                    labels: {
                        usePointStyle: true,
                        padding: 10,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value.toLocaleString('es-ES')} kWh (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Render top 10 machines bar chart
 * @param {Array} topMachines - Array of {code, energy} objects
 */
function renderTopMachinesChart(topMachines) {
    const ctx = document.getElementById('top-machines-chart').getContext('2d');
    
    // Destroy existing chart if present
    if (topMachinesChart) {
        topMachinesChart.destroy();
    }

    // Prepare data (take top 10)
    const top10 = topMachines.slice(0, 10);
    const labels = top10.map(m => m.code);
    const values = top10.map(m => m.energy);

    topMachinesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Energía Consumida (kWh)',
                data: values,
                backgroundColor: 'rgba(0, 150, 136, 0.8)',
                borderColor: 'rgb(0, 150, 136)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.2,
            indexAxis: 'y', // Horizontal bars
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.x.toLocaleString('es-ES')} kWh`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Energía (kWh)'
                    },
                    ticks: {
                        callback: function(value) {
                            if (value >= 1000000) {
                                return (value / 1000000).toFixed(1) + 'M';
                            } else if (value >= 1000) {
                                return (value / 1000).toFixed(0) + 'K';
                            }
                            return value;
                        }
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 10
                        }
                    }
                }
            }
        }
    });
}

// Make functions globally available
window.renderHourlyChart = renderHourlyChart;
window.renderCategoryChart = renderCategoryChart;
window.renderTopMachinesChart = renderTopMachinesChart;
