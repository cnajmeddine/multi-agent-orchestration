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
        """Process data analysis tasks."""
        input_data = request.input_data
        task_type = input_data.get("task_type", "data_summary")  # Default task
        data = input_data.get("data")
        
        if data is None:
            raise ValueError("No data provided for analysis")
            
        if task_type == "statistical_analysis":
            result = await self._perform_statistical_analysis(data)
        elif task_type == "data_summary":
            result = await self._generate_data_summary(data)
        else:
            # Default to data summary for unknown types
            result = await self._generate_data_summary(data)
            
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
            # Handle different data formats
            if isinstance(data, str):
                # Try to parse as JSON
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    raise ValueError("String data is not valid JSON")
            
            # Convert data to DataFrame if it's a list of dicts
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # Single record
                df = pd.DataFrame([data])
            else:
                raise ValueError(f"Data format not supported: {type(data)}")
            
            # Perform basic statistical analysis
            numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
            
            if not numeric_columns:
                return {
                    "task_type": "statistical_analysis",
                    "error": "No numeric columns found for statistical analysis",
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": df.columns.tolist(),
                    "data_types": df.dtypes.astype(str).to_dict()
                }
            
            stats = {}
            for col in numeric_columns:
                col_data = df[col].dropna()  # Remove null values
                if len(col_data) > 0:
                    stats[col] = {
                        "mean": float(col_data.mean()),
                        "median": float(col_data.median()),
                        "std": float(col_data.std()) if len(col_data) > 1 else 0.0,
                        "min": float(col_data.min()),
                        "max": float(col_data.max()),
                        "count": int(col_data.count()),
                        "null_count": int(df[col].isnull().sum())
                    }
            
            return {
                "task_type": "statistical_analysis",
                "row_count": len(df),
                "column_count": len(df.columns),
                "numeric_columns": numeric_columns,
                "statistics": stats,
                "success": True
            }
            
        except Exception as e:
            raise ValueError(f"Statistical analysis failed: {str(e)}")
    
    async def _generate_data_summary(self, data: Any) -> Dict[str, Any]:
        """Generate a summary of the dataset."""
        await asyncio.sleep(0.5)  # Simulate processing time
        
        try:
            # Handle different data formats
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    return {
                        "task_type": "data_summary",
                        "summary": f"Text data with {len(data)} characters",
                        "data_preview": data[:200],
                        "data_type": "string"
                    }
            
            if isinstance(data, list):
                if len(data) == 0:
                    return {
                        "task_type": "data_summary", 
                        "summary": "Empty dataset",
                        "row_count": 0,
                        "data_type": "empty_list"
                    }
                
                # Analyze structure
                sample_item = data[0]
                if isinstance(sample_item, dict):
                    df = pd.DataFrame(data)
                    
                    # Get data types info
                    type_info = {}
                    for col in df.columns:
                        col_type = str(df[col].dtype)
                        unique_count = df[col].nunique()
                        null_count = df[col].isnull().sum()
                        
                        type_info[col] = {
                            "dtype": col_type,
                            "unique_values": int(unique_count),
                            "null_values": int(null_count),
                            "sample_values": df[col].dropna().head(3).tolist()
                        }
                    
                    return {
                        "task_type": "data_summary",
                        "summary": f"Structured dataset with {len(df)} rows and {len(df.columns)} columns",
                        "row_count": len(df),
                        "column_count": len(df.columns),
                        "columns": df.columns.tolist(),
                        "column_info": type_info,
                        "data_type": "dataframe"
                    }
                else:
                    # List of non-dict items
                    item_types = {}
                    for item in data[:10]:  # Sample first 10 items
                        item_type = type(item).__name__
                        item_types[item_type] = item_types.get(item_type, 0) + 1
                    
                    return {
                        "task_type": "data_summary",
                        "summary": f"List of {len(data)} items",
                        "row_count": len(data),
                        "item_types": item_types,
                        "sample_items": data[:5],
                        "data_type": "list"
                    }
            
            elif isinstance(data, dict):
                # Single dictionary object
                value_types = {}
                for key, value in data.items():
                    value_type = type(value).__name__
                    value_types[value_type] = value_types.get(value_type, 0) + 1
                
                return {
                    "task_type": "data_summary",
                    "summary": f"Dictionary object with {len(data)} keys",
                    "key_count": len(data),
                    "keys": list(data.keys()),
                    "value_types": value_types,
                    "data_type": "dict"
                }
            
            else:
                # Other data types
                return {
                    "task_type": "data_summary",
                    "summary": f"Data type: {type(data).__name__}",
                    "data_preview": str(data)[:200],
                    "data_type": type(data).__name__
                }
                
        except Exception as e:
            raise ValueError(f"Data summary generation failed: {str(e)}")