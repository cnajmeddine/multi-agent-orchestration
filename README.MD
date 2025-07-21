# Multi-Agent Orchestration Platform

Building a scalable, production-ready platform for orchestrating multiple AI agents into complex, multi-step workflows. Built with modern microservices architecture, this system ains to enable businesses to chain AI capabilities together with automatic error handling, monitoring, and state management.

## Problem Statement

Organizations are adopting multiple AI tools (ChatGPT, Claude, specialized models) but face challenges:
- **Isolation**: Agents can't communicate or share context
- **No Coordination**: Manual handoffs between AI outputs
- **Unreliability**: No error handling when agents fail
- **Complex Integration**: Expensive custom development for each workflow

## Solution

An orchestration platform that coordinates multiple AI agents to work together on complex tasks, providing:
- **Workflow Automation**: Define multi-step processes with different AI agents
- **Automatic Coordination**: Seamless data passing between agents
- **Reliability**: Built-in error handling, retries, and monitoring
- **Scalability**: Horizontal scaling with Redis-based state management

## Architecture

### Complete System Architecture
```
                           ┌─────────────────────┐
                           │   React Dashboard   │
                           │    (Port 3000)     │
                           └──────────┬──────────┘
                                      │
                           ┌──────────▼──────────┐
                           │   API Gateway       │
                           │    (Port 8000)     │
                           │  Auth, Rate Limit   │
                           └──────────┬──────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
┌───────▼─────────┐        ┌──────────▼──────────┐        ┌─────────▼──────────┐
│  Agent Service  │        │ Workflow Service    │        │ Monitoring Service │
│   (Port 8001)  │        │   (Port 8002)      │        │    (Port 8003)     │
│                 │        │                     │        │                    │
│ • Agent Registry│◄──────►│ • Workflow Engine  │◄──────►│ • Metrics Collection│
│ • Load Balancer │        │ • DAG Execution    │        │ • Alerting         │
│ • Health Monitor│        │ • State Management │        │ • Performance Data │
└─────────┬───────┘        └──────────┬──────────┘        └─────────┬──────────┘
          │                           │                             │
          │                ┌──────────▼──────────┐                  │
          │                │ Communication Bus   │                  │
          │                │    (Redis Streams)  │                  │
          │                │  • Event Pub/Sub    │                  │
          │                │  • Message Queuing  │                  │
          │                └──────────┬──────────┘                  │
          │                           │                             │
          └───────────────────────────┼─────────────────────────────┘
                                      │
                           ┌──────────▼──────────┐
                           │     Redis Cluster   │
                           │                     │
                           │ • Agent Metadata    │
                           │ • Workflow State    │
                           │ • Execution Logs    │
                           │ • Performance Cache │
                           │ • Session Store     │
                           └─────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        External Integrations                        │
├─────────────────┬─────────────────┬─────────────────┬──────────────┤
│   LLM Providers │   Tool Plugins  │  Data Sources   │   Webhooks   │
│                 │                 │                 │              │
│ • OpenAI GPT    │ • Slack API     │ • Databases     │ • Zapier     │
│ • Anthropic     │ • Email SMTP    │ • File Storage  │ • Custom     │
│ • Custom Models │ • Web Scraping  │ • APIs          │ • Callbacks  │
└─────────────────┴─────────────────┴─────────────────┴──────────────┘
```

### Service Responsibilities

#### API Gateway (Port 8000)
- **Authentication**: JWT token validation and user session management
- **Rate Limiting**: Per-user and per-endpoint throttling
- **Request Routing**: Intelligent routing to appropriate services
- **CORS Handling**: Cross-origin request management
- **API Versioning**: Backward compatibility management

#### Agent Service (Port 8001)
- **Agent Registry**: Service discovery with Redis-based metadata storage
- **Load Balancing**: SORTED SET-based agent selection by current load
- **Health Monitoring**: Real-time agent status and performance tracking
- **Agent Lifecycle**: Registration, heartbeat management, and cleanup
- **Task Execution**: Direct agent invocation with timeout and retry logic

#### Workflow Service (Port 8002)
- **Workflow Engine**: DAG-based execution with topological sorting
- **State Management**: Persistent workflow execution state in Redis
- **Dependency Resolution**: Complex step dependency management
- **Conditional Logic**: Dynamic workflow branching and parallel execution
- **Context Sharing**: Seamless data flow between workflow steps

#### Communication Service (Port 8004)
- **Message Bus**: Redis Streams for reliable message delivery
- **Event System**: Pub/Sub for real-time workflow events
- **Inter-Service Communication**: Async message passing between services
- **External Webhooks**: Outbound notifications and integrations

#### Monitoring Service (Port 8003)
- **Metrics Collection**: Performance data aggregation from all services
- **Alerting**: Real-time alerts for failures and performance issues
- **Dashboard APIs**: Data endpoints for React dashboard
- **Log Aggregation**: Centralized logging with search capabilities

### Core Components

#### 1. Agent Service
- **Agent Registry**: Redis-based service discovery and load balancing
- **Agent Types**: Pluggable agent implementations (text processing, data analysis)
- **Health Monitoring**: Real-time agent status and performance tracking
- **Dynamic Scaling**: Automatic agent lifecycle management

#### 2. Workflow Service  
- **Workflow Engine**: DAG-based execution with dependency resolution
- **State Management**: Persistent workflow execution state
- **Context Sharing**: Seamless data flow between workflow steps
- **Conditional Logic**: Support for branching and parallel execution

#### 3. Redis Storage Layer
- **Agent Metadata**: HASH structures for agent information
- **Load Balancing**: SORTED SETs for intelligent agent selection
- **Workflow State**: JSON-serialized execution context
- **Real-time Monitoring**: Health checks and performance metrics

## 🛠️ Technology Stack

- **Backend**: Python 3.11+ with FastAPI for high-performance async APIs
- **Storage**: Redis for caching, state management, and real-time operations
- **Orchestration**: Custom workflow engine with topological sort for DAG execution
- **Communication**: HTTP/REST with httpx async client for inter-service communication
- **Deployment**: Docker containerization with docker-compose orchestration
- **Monitoring**: Structured logging with health check endpoints

## 🚦 Getting Started

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-agent-orchestration
   ```

2. **Start Redis**
   ```bash
   docker-compose up redis -d
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Agent Service**
   ```bash
   python run_agent_service.py
   ```

5. **Start Workflow Service** (in new terminal)
   ```bash
   python run_workflow_service.py
   ```

6. **Verify services**
   - Agent Service: http://localhost:8001/docs
   - Workflow Service: http://localhost:8002/docs
   - Health checks: `/health` endpoints

## 📋 Demo Scenarios

### 1. Content Processing Pipeline
```json
{
  "name": "Content Analysis Workflow",
  "steps": [
    {
      "name": "sentiment_analysis",
      "agent_type": "text_processor",
      "input_mapping": {"text": "input_text"},
      "output_mapping": {"sentiment": "content_sentiment"}
    },
    {
      "name": "text_summary", 
      "agent_type": "text_processor",
      "input_mapping": {"text": "input_text"},
      "output_mapping": {"summary": "content_summary"},
      "depends_on": ["sentiment_analysis"],
      "condition": "content_sentiment == positive"
    }
  ]
}
```

### 2. Data Analysis Pipeline
```json
{
  "name": "Data Processing Workflow",
  "steps": [
    {
      "name": "data_validation",
      "agent_type": "data_analyzer",
      "input_mapping": {"data": "raw_data"},
      "output_mapping": {"clean_data": "validated_data"}
    },
    {
      "name": "statistical_analysis",
      "agent_type": "data_analyzer", 
      "input_mapping": {"data": "validated_data"},
      "output_mapping": {"stats": "analysis_results"},
      "depends_on": ["data_validation"]
    }
  ]
}
```

## 🔧 API Reference

### Agent Service Endpoints

#### Register Agent
```http
POST /agents/register
Content-Type: application/json

{
  "name": "text-processor-1",
  "agent_type": "text_processor",
  "capabilities": [
    {
      "name": "sentiment_analysis",
      "input_types": ["text"],
      "output_types": ["json"]
    }
  ]
}
```

#### Execute Task
```http
POST /agents/execute
Content-Type: application/json

{
  "agent_type": "text_processor",
  "input_data": {
    "task_type": "sentiment_analysis",
    "text": "Sample text to analyze"
  }
}
```

### Workflow Service Endpoints

#### Create Workflow
```http
POST /workflows/
Content-Type: application/json

{
  "name": "Sample Workflow",
  "steps": [/* workflow steps */]
}
```

#### Execute Workflow
```http
POST /workflows/{workflow_id}/execute
Content-Type: application/json

{
  "input_data": {
    "input_text": "Text to process"
  }
}
```

#### Monitor Execution
```http
GET /executions/{execution_id}/status
GET /executions/{execution_id}/logs
```

## 🏢 Production Considerations

### Scalability
- **Horizontal Scaling**: Add more agent instances for increased throughput
- **Load Balancing**: Redis SORTED SETs automatically distribute load
- **Database Separation**: Agent and workflow services use separate Redis databases

### Reliability
- **Error Handling**: Comprehensive exception handling with detailed logging
- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Health Monitoring**: Real-time health checks and automatic cleanup
- **State Persistence**: Workflow state survives service restarts

### Security
- **Input Validation**: Pydantic models ensure type safety
- **Error Isolation**: Service failures don't cascade
- **Audit Logging**: Complete execution history for compliance

### Monitoring
- **Structured Logging**: JSON logs for observability platforms
- **Performance Metrics**: Execution times and success rates
- **Real-time Status**: Live workflow execution monitoring

## 🔮 Future Enhancements

### Phase 2: Advanced Features
- **Web Dashboard**: React-based UI for workflow management
- **Advanced Scheduling**: Cron-based workflow triggers
- **Plugin System**: Custom agent development framework
- **Performance Analytics**: Detailed metrics and optimization insights

### Phase 3: Enterprise Features
- **Multi-tenancy**: Organization and user isolation
- **Role-based Access**: Fine-grained permission system
- **API Gateway**: Centralized authentication and rate limiting
- **Kubernetes Deployment**: Production-ready container orchestration


## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes with tests
4. Submit pull request

### Code Standards
- **Type Hints**: Full type annotations required
- **Testing**: Unit tests for all business logic
- **Documentation**: Comprehensive docstrings
- **Linting**: Black + isort + flake8 compliance

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for the future of AI orchestration**