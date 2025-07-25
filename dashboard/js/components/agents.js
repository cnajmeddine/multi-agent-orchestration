// Agents component logic 
class Agents {
    constructor() {
        this.agents = [];
        this.init();
    }

    init() {
        router.register('agents', () => this.loadData());
    }

    async loadData() {
        try {
            this.agents = await api.getAgents();
            this.render();
        } catch (error) {
            console.error('Failed to load agents:', error);
        }
    }

    render() {
        const container = document.getElementById('agentsGrid');
        if (!container) return;

        if (this.agents.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-title">No agents found</div>
                    <div class="empty-state-description">Agents will appear here when they register with the system</div>
                </div>
            `;
            return;
        }

        container.innerHTML = this.agents.map(agent => `
            <div class="agent-card">
                <div class="agent-header">
                    <div>
                        <div class="agent-name">${agent.name}</div>
                        <div class="agent-type">${agent.agent_type}</div>
                    </div>
                    <div class="agent-status-badge ${agent.status}">
                        ${agent.status}
                    </div>
                </div>
                
                <div class="agent-capabilities">
                    <div class="agent-capabilities-title">Capabilities</div>
                    <div>
                        ${agent.capabilities.map(cap => `
                            <span class="capability-tag">${cap.name}</span>
                        `).join('')}
                    </div>
                </div>
                
                <div class="agent-metrics">
                    <div class="agent-load">
                        Load: ${agent.current_load}/${agent.max_concurrent_tasks}
                    </div>
                </div>
            </div>
        `).join('');
    }
}

window.agents = new Agents();