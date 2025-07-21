# analysis_agent.py - Data analysis agent implementation
# This file implements an agent for performing data analysis tasks.

import asyncio
import json
import pandas as pd
from typing import Dict, Any, List
from ..models import AgentCapability, AgentRequest, AgentResponse
from .base_agent import BaseAgent

class DataAnalysisAgent(BaseAgent):
    def __init__(self, name: str, config: Dict[str, Any] = None):
        capabilities = [
            AgentCapability(
                name="statistical_analysis",
                description="Perform statistical analysis on datasets",
                input_types=["json", "csv"],
                output_types=["json"],
                max_concurrent_tasks=2
            ),
            AgentCapability(
                name="data_summary",
                description="Generate summary statistics for datasets", 
                input_types=["json", "csv"],
                output_types=["json"],
                max_concurrent_tasks=3
            )
        ]
        super().__init__(name, "data_analyzer", capabilities, config)
    
    async def process_task(self, request: AgentRequest) -> AgentResponse:
        """Process text-related tasks."""
        input_data = request.input_data
        task_type = input_data.get("task_type")
        text_content = input_data.get("text", "")
        
        if not text_content:
            raise ValueError("No text content provided")
            
        if task_type == "summarization":
            result = await self._summarize_text(text_content)
        elif task_type == "sentiment_analysis":
            result = await self._analyze_sentiment(text_content)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
            
        return AgentResponse(
            task_id=request.task_id,
            agent_id=self.name,
            success=True,
            output_data=result,
            execution_time=0.0  # Will be overwritten by base_agent.py
        )
    
    async def _perform_statistical_analysis(self, data: Any) -> Dict[str, Any]:
        """Perform statistical analysis on the provided data."""
        await asyncio.sleep(1.0)  # Simulate processing time
        
        try:
            # Convert data to DataFrame if it's a list of dicts
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                raise ValueError("Data format not supported")
            
            # Perform basic statistical analysis
            numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
            
            if not numeric_columns:
                return {
                    "task_type": "statistical_analysis",
                    "error": "No numeric columns found for statistical analysis",
                    "row_count": len(df),
                    "column_count": len(df.columns)
                }
            
            stats = {}
            for col in numeric_columns:
                stats[col] = {
                    "mean": float(df[col].mean()),
                    "median": float(df[col].median()),
                    "std": float(df[col].std()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "count": int(df[col].count())
                }
            
            return {
                "task_type": "statistical_analysis",
                "row_count": len(df),
                "column_count": len(df.columns),
                "numeric_columns": numeric_columns,
                "statistics": stats
            }
            
        except Exception as e:
            raise ValueError(f"Statistical analysis failed: {str(e)}")
    
    async def _generate_data_summary(self, data: Any) -> Dict[str, Any]:
        """Generate a summary of the dataset."""
        await asyncio.sleep(0.5)  # Simulate processing time
        
        try:
            if isinstance(data, list):
                if len(data) == 0:
                    return {
                        "task_type": "data_summary", 
                        "summary": "Empty dataset",
                        "row_count": 0
                    }
                
                # Analyze structure
                sample_item = data[0]
                if isinstance(sample_item, dict):
                    df = pd.DataFrame(data)
                    
                    return {
                        "task_type": "data_summary",
                        "row_count": len(df),
                        "column_count": len(df.columns),
                        "columns": df.columns.tolist(),
                        "data_types": df.dtypes.astype(str).to_dict(),
                        "null_counts": df.isnull().sum().to_dict(),
                        "sample_data": data[:3]  # First 3 rows as sample
                    }
                else:
                    return {
                        "task_type": "data_summary",
                        "summary": f"List of {len(data)} items",
                        "sample_items": data[:5],
                        "item_types": [type(item).__name__ for item in data[:5]]
                    }
            
            elif isinstance(data, dict):
                return {
                    "task_type": "data_summary",
                    "summary": "Single dictionary object",
                    "keys": list(data.keys()),
                    "key_count": len(data),
                    "sample_data": data
                }
            
            else:
                return {
                    "task_type": "data_summary",
                    "summary": f"Data type: {type(data).__name__}",
                    "data": str(data)[:200]  # First 200 characters
                }
                
        except Exception as e:
            raise ValueError(f"Data summary generation failed: {str(e)}")