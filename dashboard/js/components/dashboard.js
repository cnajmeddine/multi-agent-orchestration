// Dashboard component logic 
class Dashboard {
    constructor() {
        this.metrics = [
            { key: 'agents', label: 'Active Agents', value: 0 },
            { key: 'workflows', label: 'Total Workflows', value: 0 },
            { key: 'executions', label: 'Running Executions', value: 0 },
            { key: 'alerts', label: 'System Alerts', value: 0 }
        ];

        this.services = [
            { name: 'Agent Service', port: 8001 },
            { name: 'Workflow Service', port: 8002 },
            { name: 'Monitoring Service', port: 8003 },
            { name: 'Communication Service', port: 8004 }
        ];

        this.recentActivity = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadData();
        this.startPolling();
    }

    bindEvents() {
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }
    }

    async loadData() {
        try {
            await Promise.all([
                this.loadMetrics(),
                this.loadServiceStatus(),
                this.loadRecentActivity()
            ]);
            this.render();
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
        }
    }

    async loadMetrics() {
        try {
            // Get agents count
            const agents = await api.getAgents();
            const activeAgents = agents.filter(a => 
                a.status === 'idle' || a.status === 'busy'
            ).length;

            // Get workflows count
            const workflows = await api.getWorkflows();

            // Get running executions
            const runningExecutions = await api.getExecutions('running');

            // Get monitoring overview for alerts
            const overview = await api.getDashboardOverview();

            this.metrics = [
                { key: 'agents', label: 'Active Agents', value: activeAgents },
                { key: 'workflows', label: 'Total Workflows', value: workflows.length },
                { key: 'executions', label: 'Running Executions', value: runningExecutions.length },
                { key: 'alerts', label: 'System Alerts', value: overview.summary?.active_alerts || 0 }
            ];
        } catch (error) {
            console.error('Failed to load metrics:', error);
        }
    }

    async loadServiceStatus() {
        try {
            const servicePromises = this.services.map(async (service) => {
                const status = await api.checkServiceHealth(service.name, service.port);
                return { ...service, status };
            });

            this.services = await Promise.all(servicePromises);
        } catch (error) {
            console.error('Failed to load service status:', error);
        }
    }

    async loadRecentActivity() {
        try {
            const overview = await api.getDashboardOverview();
            if (overview.recent_events) {
                this.recentActivity = overview.recent_events.slice(0, 6).map(event => ({
                    text: this.formatActivityText(event),
                    time: this.formatTime(event.timestamp)
                }));
            }
        } catch (error) {
            console.error('Failed to load recent activity:', error);
            this.recentActivity = [
                { text: 'Dashboard initialized', time: 'just now' }
            ];
        }
    }

    formatActivityText(event) {
        if (event.type === 'service_event') {
            const eventType = event.data.event_type.replace('.', ' ').replace('_', ' ');
            return `${eventType} from ${event.data.source_service}`;
        }
        return `${event.type}: ${JSON.stringify(event.data).slice(0, 40)}...`;
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);

        if (diff < 60) return 'just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }

    render() {
        this.renderMetrics();
        this.renderServiceStatus();
        this.renderRecentActivity();
    }

    renderMetrics() {
        const container = document.getElementById('metricsGrid');
        if (!container) return;

        container.innerHTML = this.metrics.map(metric => `
            <div class="overview-card">
                <div class="overview-card-header">
                    <div class="overview-card-title">${metric.label}</div>
                </div>
                <div class="overview-card-value">${metric.value}</div>
            </div>
        `).join('');
    }

    renderServiceStatus() {
        const container = document.getElementById('serviceList');
        if (!container) return;

        container.innerHTML = this.services.map(service => `
            <div class="service-item">
                <div class="service-info">
                    <div class="service-status-dot ${service.status}"></div>
                    <div class="service-name">${service.name}</div>
                </div>
                <div class="service-details">
                    <div class="service-status-badge ${service.status}">
                        ${service.status}
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderRecentActivity() {
        const container = document.getElementById('activityList');
        if (!container) return;

        if (this.recentActivity.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-title">No recent activity</div>
                    <div class="empty-state-description">Activity will appear here as events occur</div>
                </div>
            `;
            return;
        }

        container.innerHTML = this.recentActivity.map(activity => `
            <div class="activity-item">
                <div class="activity-icon"></div>
                <div class="activity-text">${activity.text}</div>
                <div class="activity-time">${activity.time}</div>
            </div>
        `).join('');
    }

    startPolling() {
        // Refresh every 5 seconds
        setInterval(() => {
            if (router.currentRoute === 'dashboard') {
                this.loadData();
            }
        }, 5000);
    }
}

// Initialize dashboard when page loads
window.dashboard = new Dashboard();