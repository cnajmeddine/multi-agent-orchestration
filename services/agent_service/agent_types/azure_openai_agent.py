# services/agent_service/agent_types/azure_openai_agent.py
# Azure OpenAI-powered agent implementation

import asyncio
import json
import logging
from typing import Dict, Any, List
from openai import AsyncAzureOpenAI
from ..models import AgentCapability, AgentRequest, AgentResponse
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class AzureOpenAIAgent(BaseAgent):
    def __init__(self, name: str, config: Dict[str, Any] = None):
        # Define capabilities
        capabilities = [
            AgentCapability(
                name="text_generation",
                description="Generate text using Azure OpenAI GPT models",
                input_types=["text"],
                output_types=["text"],
                max_concurrent_tasks=5
            ),
            AgentCapability(
                name="text_analysis",
                description="Analyze and extract insights from text",
                input_types=["text"],
                output_types=["json"],
                max_concurrent_tasks=3
            ),
            AgentCapability(
                name="text_summarization",
                description="Summarize long text content",
                input_types=["text"],
                output_types=["text"],
                max_concurrent_tasks=4
            ),
            AgentCapability(
                name="sentiment_analysis",
                description="Analyze sentiment and emotional tone",
                input_types=["text"],
                output_types=["json"],
                max_concurrent_tasks=5
            ),
            AgentCapability(
                name="question_answering",
                description="Answer questions based on provided context",
                input_types=["text"],
                output_types=["text"],
                max_concurrent_tasks=3
            )
        ]
        
        super().__init__(name, "azure_openai", capabilities, config)
        
        # Initialize Azure OpenAI client
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure OpenAI client with configuration."""
        try:
            # Get configuration from config or environment
            azure_endpoint = self.config.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = self.config.get("api_key") or os.getenv("AZURE_OPENAI_API_KEY")
            api_version = self.config.get("api_version", "2024-02-15-preview")
            
            if not azure_endpoint or not api_key:
                raise ValueError("Azure OpenAI endpoint and API key are required")
            
            self.client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                api_version=api_version
            )
            
            # Model configuration
            self.deployment_name = self.config.get("deployment_name", "gpt-4o-mini")
            self.max_tokens = self.config.get("max_tokens", 1000)
            self.temperature = self.config.get("temperature", 0.7)
            
            logger.info(f"Initialized Azure OpenAI client for deployment: {self.deployment_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            raise
    
    async def process_task(self, request: AgentRequest) -> AgentResponse:
        """Process tasks using Azure OpenAI."""
        input_data = request.input_data
        task_type = input_data.get("task_type", "text_generation")
        
        try:
            if task_type == "text_generation":
                result = await self._generate_text(input_data)
            elif task_type == "text_analysis":
                result = await self._analyze_text(input_data)
            elif task_type == "text_summarization":
                result = await self._summarize_text(input_data)
            elif task_type == "sentiment_analysis":
                result = await self._analyze_sentiment(input_data)
            elif task_type == "question_answering":
                result = await self._answer_question(input_data)
            else:
                raise ValueError(f"Unsupported task type: {task_type}")
            
            return AgentResponse(
                task_id=request.task_id,
                agent_id=self.name,
                success=True,
                output_data=result,
                execution_time=0.0  # Will be set by base class
            )
            
        except Exception as e:
            logger.error(f"Azure OpenAI task failed: {str(e)}")
            return AgentResponse(
                task_id=request.task_id,
                agent_id=self.name,
                success=False,
                error_message=str(e),
                execution_time=0.0
            )
    
    async def _generate_text(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate text using Azure OpenAI."""
        prompt = input_data.get("prompt") or input_data.get("text", "")
        system_message = input_data.get("system_message", "You are a helpful AI assistant.")
        
        if not prompt:
            raise ValueError("No prompt provided for text generation")
        
        try:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            generated_text = response.choices[0].message.content
            
            return {
                "task_type": "text_generation",
                "generated_text": generated_text,
                "prompt": prompt,
                "model": self.deployment_name,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            raise ValueError(f"Text generation failed: {str(e)}")
    
    async def _analyze_text(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze text for various insights."""
        text = input_data.get("text", "")
        analysis_type = input_data.get("analysis_type", "general")
        
        if not text:
            raise ValueError("No text provided for analysis")
        
        # Create analysis prompt based on type
        if analysis_type == "entities":
            system_prompt = """You are an expert at extracting entities from text. 
            Extract and categorize entities like persons, organizations, locations, dates, etc.
            Return the result as JSON with entity types and their values."""
        elif analysis_type == "themes":
            system_prompt = """You are an expert at identifying themes and topics in text.
            Identify the main themes, topics, and key points.
            Return the result as JSON with themes and their descriptions."""
        elif analysis_type == "intent":
            system_prompt = """You are an expert at understanding user intent from text.
            Identify the primary intent, secondary intents, and confidence levels.
            Return the result as JSON."""
        else:
            system_prompt = """You are an expert text analyst.
            Provide a comprehensive analysis including key topics, sentiment, entities, and insights.
            Return the result as structured JSON."""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this text:\n\n{text}"}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.3  # Lower temperature for analysis
            )
            
            analysis_result = response.choices[0].message.content
            
            # Try to parse as JSON, fallback to text
            try:
                parsed_result = json.loads(analysis_result)
            except json.JSONDecodeError:
                parsed_result = {"analysis": analysis_result}
            
            return {
                "task_type": "text_analysis",
                "analysis_type": analysis_type,
                "original_text": text,
                "analysis": parsed_result,
                "model": self.deployment_name
            }
            
        except Exception as e:
            raise ValueError(f"Text analysis failed: {str(e)}")
    
    async def _summarize_text(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize text content."""
        text = input_data.get("text", "")
        summary_length = input_data.get("length", "medium")  # short, medium, long
        summary_style = input_data.get("style", "bullet_points")  # bullet_points, paragraph, executive
        
        if not text:
            raise ValueError("No text provided for summarization")
        
        # Create summary prompt based on style
        if summary_style == "bullet_points":
            style_instruction = "Provide a bullet-point summary with key points."
        elif summary_style == "executive":
            style_instruction = "Provide an executive summary focusing on key decisions and actions."
        else:
            style_instruction = "Provide a concise paragraph summary."
        
        length_instruction = {
            "short": "Keep it very brief (2-3 sentences or points).",
            "medium": "Provide a moderate summary (4-6 sentences or points).",
            "long": "Provide a detailed summary (7-10 sentences or points)."
        }.get(summary_length, "Provide a moderate summary.")
        
        system_prompt = f"""You are an expert at summarizing text content.
        {style_instruction}
        {length_instruction}
        Focus on the most important information and maintain clarity."""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Summarize this text:\n\n{text}"}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=min(self.max_tokens, 500),  # Limit for summaries
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            
            return {
                "task_type": "text_summarization",
                "summary": summary,
                "original_length": len(text),
                "summary_length": len(summary),
                "compression_ratio": len(summary) / len(text) if text else 0,
                "style": summary_style,
                "length": summary_length,
                "model": self.deployment_name
            }
            
        except Exception as e:
            raise ValueError(f"Text summarization failed: {str(e)}")
    
    async def _analyze_sentiment(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment and emotional tone."""
        text = input_data.get("text", "")
        detailed = input_data.get("detailed", False)
        
        if not text:
            raise ValueError("No text provided for sentiment analysis")
        
        if detailed:
            system_prompt = """You are an expert at analyzing emotional sentiment in text.
            Provide detailed sentiment analysis including:
            - Overall sentiment (positive, negative, neutral)
            - Confidence score (0-1)
            - Specific emotions detected
            - Emotional intensity (low, medium, high)
            - Key phrases that indicate sentiment
            Return the result as structured JSON."""
        else:
            system_prompt = """You are an expert at analyzing sentiment in text.
            Provide sentiment analysis with overall sentiment and confidence score.
            Return the result as JSON with sentiment, confidence, and brief explanation."""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze the sentiment of this text:\n\n{text}"}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=300,
                temperature=0.2
            )
            
            sentiment_result = response.choices[0].message.content
            
            # Try to parse as JSON
            try:
                parsed_sentiment = json.loads(sentiment_result)
            except json.JSONDecodeError:
                # Fallback parsing
                parsed_sentiment = {
                    "sentiment": "neutral",
                    "confidence": 0.5,
                    "explanation": sentiment_result
                }
            
            return {
                "task_type": "sentiment_analysis",
                "original_text": text,
                "sentiment_analysis": parsed_sentiment,
                "detailed": detailed,
                "model": self.deployment_name
            }
            
        except Exception as e:
            raise ValueError(f"Sentiment analysis failed: {str(e)}")
    
    async def _answer_question(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Answer questions based on provided context."""
        question = input_data.get("question", "")
        context = input_data.get("context", "")
        answer_style = input_data.get("style", "concise")  # concise, detailed, conversational
        
        if not question:
            raise ValueError("No question provided")
        
        style_instructions = {
            "concise": "Provide a brief, direct answer.",
            "detailed": "Provide a comprehensive, detailed answer with explanations.",
            "conversational": "Provide a natural, conversational answer."
        }
        
        style_instruction = style_instructions.get(answer_style, "Provide a clear answer.")
        
        if context:
            system_prompt = f"""You are a helpful assistant that answers questions based on provided context.
            {style_instruction}
            If the context doesn't contain enough information to answer the question, say so clearly.
            Base your answer primarily on the provided context."""
            
            user_message = f"Context: {context}\n\nQuestion: {question}"
        else:
            system_prompt = f"""You are a knowledgeable assistant that answers questions accurately.
            {style_instruction}
            Provide helpful and accurate information."""
            
            user_message = question
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content
            
            return {
                "task_type": "question_answering",
                "question": question,
                "answer": answer,
                "context_provided": bool(context),
                "answer_style": answer_style,
                "model": self.deployment_name
            }
            
        except Exception as e:
            raise ValueError(f"Question answering failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of Azure OpenAI connection."""
        try:
            # Simple test call
            test_response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            return {
                "status": "healthy",
                "model": self.deployment_name,
                "test_response": test_response.choices[0].message.content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }