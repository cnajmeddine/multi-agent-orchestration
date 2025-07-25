// Workflows component logic 
class Workflows {
    constructor() {
        this.workflows = [];
        this.executions = [];
        this.init();
    }

    init() {
        this.bindEvents();
        router.register('workflows', () => this.loadData());
    }

    bindEvents() {
        const createBtn = document.getElementById('createWorkflowBtn');
        const modal = document.getElementById('createWorkflowModal');
        const closeBtn = document.getElementById('closeModalBtn');
        const cancelBtn = document.getElementById('cancelBtn');
        const form = document.getElementById('workflowForm');

        if (createBtn) {
            createBtn.addEventListener('click', () => this.openCreateModal());
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeCreateModal());
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.closeCreateModal());
        }

        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) this.closeCreateModal();
            });
        }

        if (form) {
            form.addEventListener('submit', (e) => this.handleCreateWorkflow(e));
        }
    }

    async loadData() {
        try {
            const [workflows, executions] = await Promise.all([
                api.getWorkflows(),
                api.getExecutions()
            ]);

            this.workflows = workflows;
            this.executions = executions;
            this.render();
        } catch (error) {
            console.error('Failed to load workflows:', error);
        }
    }

    render() {
        const container = document.getElementById('workflowsGrid');
        if (!container) return;

        if (this.workflows.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-title">No workflows found</div>
                    <div class="empty-state-description">Create your first workflow to get started</div>
                </div>
            `;
            return;
        }

        container.innerHTML = this.workflows.map(workflow => {
            const executions = this.executions.filter(e => e.workflow_id === workflow.workflow_id);
            const completedCount = executions.filter(e => e.status === 'completed').length;
            const failedCount = executions.filter(e => e.status === 'failed').length;

            return `
                <div class="workflow-card">
                    <div class="workflow-card-header">
                        <div>
                            <div class="workflow-title">${workflow.name}</div>
                            <div class="workflow-description">${workflow.description || 'No description'}</div>
                        </div>
                    </div>
                    <div class="workflow-stats">
                        <div class="workflow-stat">
                            <div class="workflow-stat-value">${workflow.steps.length}</div>
                            <div class="workflow-stat-label">Steps</div>
                        </div>
                        <div class="workflow-stat">
                            <div class="workflow-stat-value">${executions.length}</div>
                            <div class="workflow-stat-label">Total Runs</div>
                        </div>
                        <div class="workflow-stat">
                            <div class="workflow-stat-value">${completedCount}</div>
                            <div class="workflow-stat-label">Completed</div>
                        </div>
                        <div class="workflow-stat">
                            <div class="workflow-stat-value">${failedCount}</div>
                            <div class="workflow-stat-label">Failed</div>
                        </div>
                    </div>
                    <div class="workflow-actions">
                        <button class="workflow-action-btn" onclick="workflows.executeWorkflow('${workflow.workflow_id}')">
                            Execute
                        </button>
                        <button class="workflow-action-btn" onclick="workflows.viewWorkflow('${workflow.workflow_id}')">
                            View Details
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    openCreateModal() {
        const modal = document.getElementById('createWorkflowModal');
        if (modal) {
            modal.classList.add('open');
            
            // Set example JSON
            const jsonTextarea = document.getElementById('workflowJson');
            if (jsonTextarea && !jsonTextarea.value) {
                jsonTextarea.value = JSON.stringify({
                    "steps": [
                        {
                            "name": "sentiment_analysis",
                            "agent_type": "text_processor",
                            "input_mapping": {
                                "task_type": "sentiment_analysis",
                                "text": "input_text"
                            },
                            "output_mapping": {
                                "sentiment": "text_sentiment"
                            },
                            "depends_on": [],
                            "timeout": 60
                        }
                    ]
                }, null, 2);
            }
        }
    }

    closeCreateModal() {
        const modal = document.getElementById('createWorkflowModal');
        if (modal) {
            modal.classList.remove('open');
        }
    }

    async handleCreateWorkflow(e) {
        e.preventDefault();
        
        const name = document.getElementById('workflowName').value;
        const description = document.getElementById('workflowDescription').value;
        const jsonData = document.getElementById('workflowJson').value;

        try {
            const workflowData = JSON.parse(jsonData);
            
            const workflow = {
                name,
                description,
                ...workflowData
            };

            await api.createWorkflow(workflow);
            this.closeCreateModal();
            this.loadData();
            
            // Clear form
            document.getElementById('workflowForm').reset();
        } catch (error) {
            alert('Failed to create workflow: ' + error.message);
        }
    }

    async executeWorkflow(workflowId) {
        try {
            const inputText = prompt('Enter input text for the workflow:');
            if (!inputText) return;

            const execution = await api.executeWorkflow(workflowId, { input_text: inputText });
            alert(`Workflow execution started: ${execution.execution_id}`);
            
            // Refresh data to show new execution
            setTimeout(() => this.loadData(), 1000);
        } catch (error) {
            alert('Failed to execute workflow: ' + error.message);
        }
    }

    viewWorkflow(workflowId) {
        const workflow = this.workflows.find(w => w.workflow_id === workflowId);
        if (workflow) {
            alert('Workflow Details:\n' + JSON.stringify(workflow, null, 2));
        }
    }
}

window.workflows = new Workflows();