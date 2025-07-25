// Monitoring component logic 
class Monitoring {
    constructor() {
        this.counters = {};
        this.chart = null;
        this.init();
    }

    init() {
        router.register('monitoring', () => this.loadData());
    }

    async loadData() {
        try {
            this.counters = await api.getCounters();
            this.render();
            this.renderChart();
        } catch (error) {
            console.error('Failed to load monitoring data:', error);
        }
    }

    render() {
        this.renderCounters();
    }

    renderCounters() {
        const container = document.getElementById('countersView');
        if (!container) return;

        const counterEntries = Object.entries(this.counters);
        
        if (counterEntries.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-title">No data available</div>
                    <div class="empty-state-description">Counters will appear as the system processes events</div>
                </div>
            `;
            return;
        }

        container.innerHTML = counterEntries.map(([key, value]) => `
            <div class="counter-item">
                <div class="counter-label">${key.replace(/_/g, ' ')}</div>
                <div class="counter-value">${value}</div>
            </div>
        `).join('');
    }

    renderChart() {
        const canvas = document.getElementById('metricsChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        if (this.chart) {
            this.chart.destroy();
        }

        const counterEntries = Object.entries(this.counters);
        const labels = counterEntries.map(([key]) => key.replace(/_/g, ' '));
        const data = counterEntries.map(([, value]) => value);

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Count',
                    data: data,
                    backgroundColor: 'rgba(0, 212, 255, 0.2)',
                    borderColor: 'rgba(0, 212, 255, 1)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 212, 255, 0.1)'
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0, 212, 255, 0.1)'
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    }
                }
            }
        });
    }
}

window.monitoring = new Monitoring();