// API utility functions for dashboard 
class ApiService {
    constructor() {
        this.baseUrls = {
            agent: 'http://localhost:8001',
            workflow: 'http://localhost:8002',
            monitoring: 'http://localhost:8003',
            communication: 'http://localhost:8004'
        };
    }

    async request(service, endpoint, options = {}) {
        try {
            const url = `${this.baseUrls[service]}${endpoint}`;
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${service}${endpoint}]:`, error);
            throw error;
        }
    }

    // Agent Service
    async getAgents() {
        return this.request('agent', '/agents/');
    }

    async getAgentHealth() {
        return this.request('agent', '/health/detailed');
    }

    async registerAgent(agentData) {
        return this.request('agent', '/agents/register', {
            method: 'POST',
            body: JSON.stringify(agentData)
        });
    }

    // Workflow Service
    async getWorkflows() {
        return this.request('workflow', '/workflows/');
    }

    async createWorkflow(workflowData) {
        return this.request('workflow', '/workflows/', {
            method: 'POST',
            body: JSON.stringify(workflowData)
        });
    }

    async executeWorkflow(workflowId, inputData) {
        return this.request('workflow', `/workflows/${workflowId}/execute`, {
            method: 'POST',
            body: JSON.stringify({ input_data: inputData })
        });
    }

    async getExecutions(status = null) {
        const params = status ? `?status=${status}` : '';
        return this.request('workflow', `/executions/${params}`);
    }

    async getExecutionStatus(executionId) {
        return this.request('workflow', `/executions/${executionId}/status`);
    }

    // Monitoring Service
    async getCounters() {
        return this.request('monitoring', '/counters');
    }

    async getDashboardOverview() {
        return this.request('monitoring', '/dashboard/overview');
    }

    async getMetrics(metricName, hours = 1) {
        return this.request('monitoring', `/metrics/${metricName}?hours=${hours}`);
    }

    // Communication Service
    async getEventStats() {
        return this.request('communication', '/events/stats');
    }

    async getServiceStats() {
        return this.request('communication', '/stats');
    }

    // Health checks for all services
    async checkServiceHealth(service, port) {
        try {
            const response = await fetch(`http://localhost:${port}/`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            return data.status || 'unknown';
        } catch (error) {
            return 'unreachable';
        }
    }
}

// Global API instance
window.api = new ApiService();