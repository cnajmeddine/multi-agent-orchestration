const API_BASE_URLS = {
    agent: 'http://localhost:8001',
    workflow: 'http://localhost:8002',
    monitoring: 'http://localhost:8003',
    communication: 'http://localhost:8004'
  };
  
  class ApiService {
    async get(service, endpoint) {
      try {
        const response = await fetch(`${API_BASE_URLS[service]}${endpoint}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
      } catch (error) {
        console.error(`API Error [${service}${endpoint}]:`, error);
        throw error;
      }
    }
  
    // Agent Service
    async getAgents() {
      return this.get('agent', '/agents/');
    }
  
    async getAgentHealth() {
      return this.get('agent', '/health/detailed');
    }
  
    // Workflow Service  
    async getWorkflows() {
      return this.get('workflow', '/workflows/');
    }
  
    async getExecutions(status = null) {
      const params = status ? `?status=${status}` : '';
      return this.get('workflow', `/executions/${params}`);
    }
  
    // Monitoring Service
    async getCounters() {
      return this.get('monitoring', '/counters');
    }
  
    async getDashboardOverview() {
      return this.get('monitoring', '/dashboard/overview');
    }
  
    // Communication Service
    async getEventStats() {
      return this.get('communication', '/events/stats');
    }
  }
  
  export default new ApiService();