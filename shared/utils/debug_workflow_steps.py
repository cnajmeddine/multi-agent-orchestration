# debug_workflow_steps.py - Debug specific step failures
import asyncio
import httpx
import json

async def debug_latest_failure():
    """Get detailed logs for the most recent failure."""
    
    async with httpx.AsyncClient() as client:
        try:
            # Get the most recent failed execution
            response = await client.get("http://localhost:8002/executions/?status=failed")
            
            if response.status_code == 200:
                executions = response.json()
                
                if executions:
                    latest = executions[0]
                    execution_id = latest['execution_id']
                    
                    print(f"🔍 DEBUGGING LATEST FAILURE: {execution_id}")
                    
                    # Get detailed logs
                    logs_response = await client.get(f"http://localhost:8002/executions/{execution_id}/logs")
                    
                    if logs_response.status_code == 200:
                        logs = logs_response.json()
                        
                        print(f"Workflow: {logs['workflow_id']}")
                        print(f"Status: {logs['status']}")
                        
                        # Find the failing step
                        for i, step_log in enumerate(logs['step_logs']):
                            print(f"\n--- Step {i+1}: {step_log['step_id']} ---")
                            print(f"Status: {step_log['status']}")
                            
                            if step_log['status'] == 'failed':
                                print(f"❌ FAILED STEP FOUND!")
                                print(f"Input: {json.dumps(step_log['input_data'], indent=2)}")
                                print(f"Error: {step_log['error_message']}")
                                print(f"Agent: {step_log['agent_id']}")
                                
                                # Try to reproduce the failure
                                await test_failed_step(step_log)
                                
                            elif step_log['status'] == 'pending':
                                print(f"⏳ PENDING STEP - This is where it stopped")
                                print(f"Expected input: {json.dumps(step_log['input_data'], indent=2)}")
                                
                                # Check why it's pending
                                await debug_pending_step(logs, step_log)
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")

async def test_failed_step(step_log):
    """Test the failed step directly."""
    
    if not step_log['input_data']:
        print("⚠️  No input data to test")
        return
    
    async with httpx.AsyncClient() as client:
        try:
            print("\n🧪 Testing failed step directly...")
            
            # Extract agent type from error or try both
            for agent_type in ['text_processor', 'data_analyzer']:
                print(f"\nTrying {agent_type}...")
                
                response = await client.post(
                    "http://localhost:8001/agents/execute",
                    json={
                        "agent_type": agent_type,
                        "input_data": step_log['input_data']
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result['success']:
                        print(f"✅ {agent_type} works with this input!")
                        print(f"Output: {json.dumps(result['output_data'], indent=2)}")
                        return
                    else:
                        print(f"❌ {agent_type} failed: {result['error_message']}")
                else:
                    print(f"❌ {agent_type} HTTP error: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")

async def debug_pending_step(logs, pending_step):
    """Debug why a step is pending."""
    
    print("\n🔍 Debugging pending step...")
    
    # Check if it's a condition issue
    context = logs['context']
    print(f"Current context: {json.dumps(context, indent=2)}")
    
    # Get the workflow definition to see the step details
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"http://localhost:8002/workflows/{logs['workflow_id']}")
            
            if response.status_code == 200:
                workflow = response.json()
                
                # Find the matching step
                matching_step = None
                for step in workflow['steps']:
                    if step['step_id'] == pending_step['step_id']:
                        matching_step = step
                        break
                
                if matching_step:
                    print(f"\nStep definition: {json.dumps(matching_step, indent=2)}")
                    
                    # Check dependencies
                    if matching_step.get('depends_on'):
                        print(f"Dependencies: {matching_step['depends_on']}")
                        
                        # Check if dependencies are completed
                        completed_steps = [s['step_id'] for s in logs['step_logs'] if s['status'] == 'completed']
                        print(f"Completed steps: {completed_steps}")
                        
                        missing_deps = [dep for dep in matching_step['depends_on'] if dep not in completed_steps]
                        if missing_deps:
                            print(f"❌ Missing dependencies: {missing_deps}")
                        else:
                            print(f"✅ All dependencies satisfied")
                    
                    # Check condition
                    if matching_step.get('condition'):
                        condition = matching_step['condition']
                        print(f"Condition: {condition}")
                        
                        # Try to evaluate condition manually
                        await test_condition(condition, context)
                    
                    # Check input mapping
                    input_mapping = matching_step.get('input_mapping', {})
                    print(f"Input mapping: {json.dumps(input_mapping, indent=2)}")
                    
                    # Try to resolve the mapping
                    resolved_input = await test_input_mapping(input_mapping, context)
                    print(f"Resolved input: {json.dumps(resolved_input, indent=2)}")
        
        except Exception as e:
            print(f"❌ Error getting workflow: {str(e)}")

async def test_condition(condition, context):
    """Test condition evaluation."""
    
    print(f"\n🧪 Testing condition: '{condition}'")
    
    # Simple condition testing
    try:
        # Replace ${var} with actual values
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            if var_name in context:
                value = context[var_name]
                return f'"{value}"' if isinstance(value, str) else str(value)
            return f"None"
        
        resolved_condition = re.sub(r'\$\{([^}]+)\}', replace_var, condition)
        print(f"Resolved condition: {resolved_condition}")
        
        # Try to evaluate (simplified)
        if '!=' in resolved_condition:
            left, right = resolved_condition.split('!=')
            left = left.strip().strip('"')
            right = right.strip().strip('"')
            result = left != right
            print(f"Evaluation: '{left}' != '{right}' = {result}")
        
    except Exception as e:
        print(f"❌ Condition test failed: {str(e)}")

async def test_input_mapping(input_mapping, context):
    """Test input mapping resolution."""
    
    resolved = {}
    
    for key, value in input_mapping.items():
        if isinstance(value, str):
            if value in context:
                resolved[key] = context[value]
            elif value.startswith('${') and value.endswith('}'):
                var_name = value[2:-1]
                resolved[key] = context.get(var_name, f"MISSING:{var_name}")
            else:
                resolved[key] = value  # Literal value
        else:
            resolved[key] = value
    
    return resolved

async def test_simple_cases():
    """Test the failing patterns with simple cases."""
    
    print("\n🧪 TESTING SIMPLE CASES...")
    
    # Test condition evaluation
    test_contexts = [
        {
            "message_sentiment": "neutral",
            "sentiment_confidence": 0.6
        },
        {
            "message_sentiment": "positive", 
            "sentiment_confidence": 0.8
        },
        {
            "message_sentiment": "negative",
            "sentiment_confidence": 0.9
        }
    ]
    
    for i, context in enumerate(test_contexts):
        print(f"\nTest {i+1}: {context}")
        await test_condition("${message_sentiment} != negative", context)

if __name__ == "__main__":
    async def main():
        await debug_latest_failure()
        await test_simple_cases()
    
    asyncio.run(main())