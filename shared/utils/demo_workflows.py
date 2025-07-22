# fixed_demo_workflows.py - Fixed workflow definitions
import asyncio
import httpx
import json

# Fixed workflow definitions with step IDs in dependencies

def create_customer_support_workflow():
    return {
        "name": "Customer Support Analysis Fixed",
        "description": "Analyze customer feedback and generate appropriate responses",
        "steps": [
            {
                "name": "sentiment_analysis",
                "agent_type": "text_processor",
                "input_mapping": {
                    "task_type": "sentiment_analysis",
                    "text": "customer_message"
                },
                "output_mapping": {
                    "sentiment": "message_sentiment",
                    "confidence": "sentiment_confidence"
                },
                "depends_on": [],
                "timeout": 60
            },
            {
                "name": "generate_summary",
                "agent_type": "text_processor", 
                "input_mapping": {
                    "task_type": "summarization",
                    "text": "customer_message"
                },
                "output_mapping": {
                    "summary": "message_summary"
                },
                "depends_on": [],  # Remove dependency for now
                "timeout": 60
            }
        ],
        "global_timeout": 300
    }

def create_data_processing_workflow():
    return {
        "name": "Data Analysis Pipeline Fixed", 
        "description": "Process and analyze customer data",
        "steps": [
            {
                "name": "data_validation",
                "agent_type": "data_analyzer",
                "input_mapping": {
                    "task_type": "data_summary",
                    "data": "raw_customer_data"
                },
                "output_mapping": {
                    "row_count": "total_records",
                    "summary": "data_validation_summary"
                },
                "depends_on": [],
                "timeout": 120
            },
            {
                "name": "statistical_analysis",
                "agent_type": "data_analyzer",
                "input_mapping": {
                    "task_type": "statistical_analysis", 
                    "data": "raw_customer_data"
                },
                "output_mapping": {
                    "statistics": "customer_stats"
                },
                "depends_on": [],  # Remove dependency to test
                "timeout": 180
            }
        ],
        "global_timeout": 600
    }

def create_simple_sequential_workflow():
    """Create a simple sequential workflow to test dependencies."""
    step1_id = "step-1-sentiment"
    step2_id = "step-2-summary"
    
    return {
        "name": "Simple Sequential Test",
        "description": "Test step dependencies",
        "steps": [
            {
                "step_id": step1_id,
                "name": "sentiment_analysis",
                "agent_type": "text_processor",
                "input_mapping": {
                    "task_type": "sentiment_analysis",
                    "text": "test_message"
                },
                "output_mapping": {
                    "sentiment": "result_sentiment"
                },
                "depends_on": [],
                "timeout": 60
            },
            {
                "step_id": step2_id,
                "name": "text_summary",
                "agent_type": "text_processor",
                "input_mapping": {
                    "task_type": "summarization",
                    "text": "test_message"  # Simple mapping, no variables
                },
                "output_mapping": {
                    "summary": "result_summary"
                },
                "depends_on": [step1_id],  # Use step ID
                "timeout": 60
            }
        ],
        "global_timeout": 300
    }

# Test data
TEST_DATA = {
    "customer_support": {
        "customer_message": "I'm really disappointed with the product quality. The item arrived damaged and doesn't work as advertised. I want a refund immediately!"
    },
    
    "data_processing": {
        "raw_customer_data": [
            {"customer_id": 1, "age": 25, "purchase_amount": 150.50, "satisfaction": 4},
            {"customer_id": 2, "age": 34, "purchase_amount": 89.99, "satisfaction": 5},
            {"customer_id": 3, "age": 45, "purchase_amount": 299.99, "satisfaction": 3}
        ]
    },
    
    "simple_test": {
        "test_message": "This product is amazing and works perfectly!"
    }
}

async def create_and_test_workflows():
    """Create and test fixed workflows."""
    
    workflows_to_test = [
        (create_customer_support_workflow(), "customer_support"),
        (create_data_processing_workflow(), "data_processing"),
        (create_simple_sequential_workflow(), "simple_test")
    ]
    
    async with httpx.AsyncClient() as client:
        for workflow_def, test_data_key in workflows_to_test:
            try:
                print(f"\n🔧 Testing: {workflow_def['name']}")
                
                # Create workflow
                response = await client.post(
                    "http://localhost:8002/workflows/",
                    json=workflow_def
                )
                
                if response.status_code == 200:
                    workflow = response.json()
                    workflow_id = workflow['workflow_id']
                    print(f"✅ Created workflow: {workflow_id}")
                    
                    # Execute workflow
                    execution_response = await client.post(
                        f"http://localhost:8002/workflows/{workflow_id}/execute",
                        json={"input_data": TEST_DATA[test_data_key]}
                    )
                    
                    if execution_response.status_code == 200:
                        execution = execution_response.json()
                        execution_id = execution['execution_id']
                        print(f"🚀 Started execution: {execution_id}")
                        
                        # Monitor execution
                        for attempt in range(10):  # 20 second timeout
                            await asyncio.sleep(2)
                            
                            status_response = await client.get(
                                f"http://localhost:8002/executions/{execution_id}/status"
                            )
                            
                            if status_response.status_code == 200:
                                status = status_response.json()
                                print(f"📊 Status: {status['status']} ({status['progress_percentage']:.1f}%)")
                                
                                if status['status'] in ['completed', 'failed']:
                                    break
                            else:
                                print(f"❌ Status check failed: {status_response.status_code}")
                                break
                        
                        # Get final result
                        result_response = await client.get(
                            f"http://localhost:8002/executions/{execution_id}"
                        )
                        
                        if result_response.status_code == 200:
                            result = result_response.json()
                            print(f"✅ Final status: {result['status']}")
                            
                            if result['status'] == 'completed':
                                print(f"📄 Context: {json.dumps(result['context'], indent=2)}")
                            else:
                                # Get error details
                                logs_response = await client.get(
                                    f"http://localhost:8002/executions/{execution_id}/logs"
                                )
                                if logs_response.status_code == 200:
                                    logs = logs_response.json()
                                    for step in logs['step_logs']:
                                        if step['error_message']:
                                            print(f"❌ Step error: {step['error_message']}")
                        else:
                            print(f"❌ Failed to get result: {result_response.status_code}")
                    
                    else:
                        print(f"❌ Failed to execute: {execution_response.status_code}")
                        print(execution_response.text)
                else:
                    print(f"❌ Failed to create: {response.status_code}")
                    print(response.text)
                    
            except Exception as e:
                print(f"❌ Error testing {workflow_def['name']}: {str(e)}")

async def test_input_mapping_directly():
    """Test input mapping resolution directly."""
    
    print("\n🧪 TESTING INPUT MAPPING...")
    
    # Test the problematic mapping
    test_context = {
        "text_sentiment": "neutral",
        "data_insights": {
            "summary": "Dataset has 3 rows and 3 columns"
        }
    }
    
    problematic_mapping = {
        "task_type": "summarization",
        "text": "Sentiment: ${text_sentiment}, Data: ${data_insights.summary}"
    }
    
    print(f"Context: {json.dumps(test_context, indent=2)}")
    print(f"Mapping: {json.dumps(problematic_mapping, indent=2)}")
    
    # Manual resolution test
    text_template = problematic_mapping["text"]
    print(f"Template: {text_template}")
    
    # Simple variable substitution
    import re
    
    def replace_var(match):
        var_path = match.group(1)
        parts = var_path.split('.')
        
        current = test_context
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return f"MISSING({var_path})"
        
        return str(current)
    
    resolved = re.sub(r'\$\{([^}]+)\}', replace_var, text_template)
    print(f"Resolved: {resolved}")

if __name__ == "__main__":
    async def main():
        await test_input_mapping_directly()
        await create_and_test_workflows()
    
    asyncio.run(main())