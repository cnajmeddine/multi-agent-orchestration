# text_agent.py - Text processing agent implementation
# This file implements an agent for processing text data.

import asyncio
from typing import Dict, Any, List
from ..models import AgentCapability, AgentRequest, AgentResponse
from .base_agent import BaseAgent

class TextProcessingAgent(BaseAgent):
    def __init__(self, name: str, config: Dict[str, Any] = None):
        capabilities = [
            AgentCapability(
                name="text_summarization",
                description="Summarize text content",
                input_types=["text"],
                output_types=["text"],
                max_concurrent_tasks=3
            ),
            AgentCapability(
                name="sentiment_analysis", 
                description="Analyze sentiment of text",
                input_types=["text"],
                output_types=["json"],
                max_concurrent_tasks=5
            )
        ]
        super().__init__(name, "text_processor", capabilities, config)
    
    async def process_task(self, request: AgentRequest) -> AgentResponse:
        """Process text-related tasks."""
        input_data = request.input_data
        task_type = input_data.get("task_type", "sentiment_analysis")  # Default to sentiment
        text_content = input_data.get("text", "")
        
        if not text_content:
            raise ValueError("No text content provided")
            
        if task_type == "summarization":
            result = await self._summarize_text(text_content)
        elif task_type == "sentiment_analysis":
            result = await self._analyze_sentiment(text_content)
        else:
            # Default to sentiment analysis for unknown types
            result = await self._analyze_sentiment(text_content)
            
        return AgentResponse(
            task_id=request.task_id,
            agent_id=self.name,
            success=True,
            output_data=result,
            execution_time=0.0
        )
    
    async def _summarize_text(self, text: str) -> Dict[str, Any]:
        """Mock text summarization - replace with actual LLM call."""
        await asyncio.sleep(0.5)  # Simulate processing time
        word_count = len(text.split())
        summary = f"Summary of {word_count} words: {text[:100]}..."
        
        return {
            "task_type": "summarization",
            "original_length": word_count,
            "summary": summary,
            "compression_ratio": min(100 / word_count, 1.0) if word_count > 0 else 0
        }
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Mock sentiment analysis - replace with actual ML model."""
        await asyncio.sleep(0.3)  # Simulate processing time
        
        # Simple mock sentiment based on word count and content
        positive_words = ["good", "great", "excellent", "amazing", "wonderful"]
        negative_words = ["bad", "terrible", "awful", "horrible", "disappointing"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            confidence = min(0.7 + (positive_count * 0.1), 0.95)
        elif negative_count > positive_count:
            sentiment = "negative" 
            confidence = min(0.7 + (negative_count * 0.1), 0.95)
        else:
            sentiment = "neutral"
            confidence = 0.6
            
        return {
            "task_type": "sentiment_analysis",
            "sentiment": sentiment,
            "confidence": confidence,
            "word_count": len(text.split())
        }