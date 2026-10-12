/**
 * API client for Siemens Spacewise Simulator
 * Handles all HTTP requests with proper error handling and loading states
 */

const API = {
    /**
     * Get base URL for API requests
     */
    getBaseUrl() {
        // If running from file:// or different port, use localhost:5000
        if (window.location.protocol === 'file:' || 
            window.location.port === '5500' || 
            window.location.port === '8000' ||
            window.location.port === '8080') {
            return 'http://localhost:5000/api';
        }
        // Otherwise use relative path (same origin)
        return '/api';
    },

    /**
     * Make HTTP request with error handling
     * @param {string} endpoint - API endpoint
     * @param {object} options - Fetch options
     * @returns {Promise<object>} Parsed JSON response
     */
    async request(endpoint, options = {}) {
        const url = `${this.getBaseUrl()}${endpoint}`;
        
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMessage = errorData.error || `HTTP ${response.status}: ${response.statusText}`;
                throw new Error(errorMessage);
            }

            // Handle CSV downloads
            if (response.headers.get('content-type')?.includes('text/csv')) {
                return await response.text();
            }

            return await response.json();
        } catch (error) {
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('No se pudo conectar al servidor. Verifique que Flask esté corriendo en puerto 5000.');
            }
            throw error;
        }
    },

    /**
     * Get all active machines
     * @returns {Promise<{machines: Array, count: number}>}
     */
    async getMachines() {
        return this.request('/machines');
    },

    /**
     * Get machine details by code
     * @param {string} code - Machine code (e.g., 'HVAC-001')
     * @returns {Promise<object>} Machine details
     */
    async getMachine(code) {
        return this.request(`/machines/${encodeURIComponent(code)}`);
    },

    /**
     * Get all simulations
     * @returns {Promise<{simulations: Array, count: number}>}
     */
    async getSimulations() {
        return this.request('/simulations');
    },

    /**
     * Get simulation summary with KPIs
     * @param {number} simulationId - Simulation ID
     * @returns {Promise<object>} Summary with total_energy_kwh, peak_power_kw, etc.
     */
    async getSimulationSummary(simulationId) {
        return this.request(`/simulations/${simulationId}/summary`);
    },

    /**
     * Get hourly totals for a simulation (8760 data points)
     * @param {number} simulationId - Simulation ID
     * @returns {Promise<{data: Array, points: number}>}
     */
    async getHourlyTotals(simulationId) {
        return this.request(`/simulations/${simulationId}/hourly`);
    },

    /**
     * Get measurements for a specific machine in a simulation
     * @param {number} simulationId - Simulation ID
     * @param {string} machineCode - Machine code (e.g., 'HVAC-001')
     * @returns {Promise<{data: Array, points: number}>}
     */
    async getMachineMeasurements(simulationId, machineCode) {
        return this.request(`/simulations/${simulationId}/machines/${encodeURIComponent(machineCode)}`);
    },

    /**
     * Export simulation data as CSV
     * @param {number} simulationId - Simulation ID
     * @param {string} [startDate] - Start date (YYYY-MM-DD)
     * @param {string} [endDate] - End date (YYYY-MM-DD)
     * @returns {Promise<string>} CSV content
     */
    async exportData(simulationId, startDate, endDate) {
        let endpoint = `/simulations/${simulationId}/export?format=csv`;
        if (startDate) endpoint += `&start=${encodeURIComponent(startDate)}`;
        if (endDate) endpoint += `&end=${encodeURIComponent(endDate)}`;
        return this.request(endpoint);
    },

    /**
     * Download CSV file
     * @param {number} simulationId - Simulation ID
     * @param {string} [startDate] - Start date
     * @param {string} [endDate] - End date
     */
    async downloadCSV(simulationId, startDate, endDate) {
        const csv = await this.exportData(simulationId, startDate, endDate);
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `simulation_${simulationId}_export.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
};

// Make API globally available
window.API = API;
