"""
Intelligent Model Router for AI generation with automatic model selection based on task complexity.
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import Lock

import httpx
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Types of AI tasks that can be performed."""
    TEXT_GENERATION = "text_generation"
    EXTRACTION = "extraction"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CODE_GENERATION = "code_generation"
    QUESTION_ANSWERING = "question_answering"


@dataclass
class ModelCapability:
    """Represents the capabilities and pricing of an AI model."""
    model_id: str
    name: str
    description: str
    max_tokens: int
    context_window: int
    supports_function_calling: bool
    supports_vision: bool
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    complexity_threshold: float  # Minimum complexity score to use this model
    quality_score: float  # 0-1, higher is better quality
    speed_score: float  # 0-1, higher is faster
    recommended_for: List[TaskType] = field(default_factory=list)


@dataclass
class GenerationRequest:
    """Represents an AI generation request."""
    prompt: str
    task_type: TaskType
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 0.9
    system_prompt: Optional[str] = None
    complexity_score: Optional[float] = None  # If None, will be calculated
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResponse:
    """Represents an AI generation response."""
    content: str
    model_used: str
    tokens_used: Dict[str, int]  # input_tokens, output_tokens, total_tokens
    cost: float
    generation_time: float
    complexity_score: float
    timestamp: str


@dataclass
class CostEntry:
    """Represents a cost tracking entry."""
    timestamp: str
    model_id: str
    task_type: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    generation_time: float


class CostTracker:
    """Tracks AI generation costs and token usage."""

    def __init__(self, max_entries: int = 1000):
        self.costs: List[CostEntry] = []
        self.max_entries = max_entries
        self.lock = Lock()
        self.total_cost: float = 0.0
        self.total_tokens: int = 0
        self.total_requests: int = 0

    def add_cost_entry(self, entry: CostEntry):
        """Add a cost entry to the tracker."""
        with self.lock:
            self.costs.append(entry)
            self.total_cost += entry.cost
            self.total_tokens += entry.total_tokens
            self.total_requests += 1

            # Keep only the most recent entries
            if len(self.costs) > self.max_entries:
                self.costs = self.costs[-self.max_entries:]

    def get_total_cost(self) -> float:
        """Get total cost across all generations."""
        with self.lock:
            return self.total_cost

    def get_total_tokens(self) -> int:
        """Get total tokens used across all generations."""
        with self.lock:
            return self.total_tokens

    def get_total_requests(self) -> int:
        """Get total number of requests."""
        with self.lock:
            return self.total_requests

    def get_recent_costs(self, limit: int = 100) -> List[CostEntry]:
        """Get recent cost entries."""
        with self.lock:
            return self.costs[-limit:]

    def get_cost_by_model(self) -> Dict[str, float]:
        """Get total cost broken down by model."""
        with self.lock:
            model_costs: Dict[str, float] = {}
            for entry in self.costs:
                model_costs[entry.model_id] = model_costs.get(entry.model_id, 0.0) + entry.cost
            return model_costs

    def get_cost_by_task_type(self) -> Dict[str, float]:
        """Get total cost broken down by task type."""
        with self.lock:
            task_costs: Dict[str, float] = {}
            for entry in self.costs:
                task_costs[entry.task_type] = task_costs.get(entry.task_type, 0.0) + entry.cost
            return task_costs

    def get_average_cost_per_request(self) -> float:
        """Get average cost per request."""
        with self.lock:
            return self.total_cost / max(self.total_requests, 1)

    def get_average_tokens_per_request(self) -> float:
        """Get average tokens per request."""
        with self.lock:
            return self.total_tokens / max(self.total_requests, 1)


class IntelligentModelRouter:
    """
    Intelligent router that selects the optimal AI model based on task complexity,
    cost constraints, and quality requirements.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            Path(__file__).parent.parent, "config", "ai_config.json"
        )
        self.models: Dict[str, ModelCapability] = {}
        self.cost_tracker = CostTracker()
        self.http_client: Optional[httpx.AsyncClient] = None
        self.config: Dict[str, Any] = {}
        self._load_models()
        self._load_config()

    def _load_models(self):
        """Load model capabilities from configuration."""
        # Define available models with their capabilities
        self.models = {
            "gemini-2.5-pro": ModelCapability(
                model_id="gemini-2.5-pro",
                name="Gemini 2.5 Pro",
                description="Highest quality model for complex tasks requiring deep reasoning",
                max_tokens=8192,
                context_window=1000000,
                supports_function_calling=True,
                supports_vision=True,
                input_cost_per_1k_tokens=0.00125,
                output_cost_per_1k_tokens=0.005,
                complexity_threshold=0.7,
                quality_score=1.0,
                speed_score=0.6,
                recommended_for=[
                    TaskType.EXTRACTION,
                    TaskType.ANALYSIS,
                    TaskType.CODE_GENERATION,
                ],
            ),
            "gemini-2.5-flash": ModelCapability(
                model_id="gemini-2.5-flash",
                name="Gemini 2.5 Flash",
                description="Balanced model for most tasks with good quality and speed",
                max_tokens=8192,
                context_window=1000000,
                supports_function_calling=True,
                supports_vision=True,
                input_cost_per_1k_tokens=0.000075,
                output_cost_per_1k_tokens=0.0003,
                complexity_threshold=0.4,
                quality_score=0.8,
                speed_score=0.9,
                recommended_for=[
                    TaskType.TEXT_GENERATION,
                    TaskType.SUMMARIZATION,
                    TaskType.QUESTION_ANSWERING,
                ],
            ),
            "gemini-2.5-flash-lite": ModelCapability(
                model_id="gemini-2.5-flash-lite",
                name="Gemini 2.5 Flash Lite",
                description="Fast, cost-effective model for simple tasks",
                max_tokens=8192,
                context_window=1000000,
                supports_function_calling=False,
                supports_vision=False,
                input_cost_per_1k_tokens=0.0000375,
                output_cost_per_1k_tokens=0.00015,
                complexity_threshold=0.0,
                quality_score=0.6,
                speed_score=1.0,
                recommended_for=[
                    TaskType.TRANSLATION,
                    TaskType.TEXT_GENERATION,
                ],
            ),
        }

    def _load_config(self):
        """Load AI configuration from file."""
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load AI config: {e}")
                self.config = self._get_default_config()
        else:
            self.config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default AI configuration."""
        return {
            "api_key": os.getenv("GEMINI_API_KEY", ""),
            "default_model": "gemini-2.5-flash",
            "max_retries": 3,
            "timeout": 60,
            "enable_cost_tracking": True,
            "complexity_calculation": {
                "enabled": True,
                "factors": {
                    "prompt_length": 0.2,
                    "task_complexity": 0.5,
                    "domain_specificity": 0.3,
                }
            }
        }

    def reload_config(self):
        """Reload AI configuration from file."""
        self._load_config()
        self._load_models()

    def get_available_models(self) -> List[ModelCapability]:
        """Get list of all available models."""
        return list(self.models.values())

    def get_model(self, model_id: str) -> Optional[ModelCapability]:
        """Get a specific model by ID."""
        return self.models.get(model_id)

    def calculate_complexity_score(self, request: GenerationRequest) -> float:
        """
        Calculate complexity score for a request (0-1 scale).

        Factors considered:
        - Prompt length (longer prompts = more complex)
        - Task type (some tasks are inherently more complex)
        - Domain specificity (technical terms, specific knowledge)
        """
        if request.complexity_score is not None:
            return request.complexity_score

        if not self.config.get("complexity_calculation", {}).get("enabled", True):
            return 0.5  # Default to medium complexity

        factors = self.config.get("complexity_calculation", {}).get("factors", {})

        # Factor 1: Prompt length (normalized 0-1)
        prompt_length_score = min(len(request.prompt) / 2000, 1.0)

        # Factor 2: Task complexity based on type
        task_complexity_scores = {
            TaskType.EXTRACTION: 0.8,
            TaskType.ANALYSIS: 0.9,
            TaskType.CODE_GENERATION: 0.85,
            TaskType.SUMMARIZATION: 0.6,
            TaskType.QUESTION_ANSWERING: 0.5,
            TaskType.TRANSLATION: 0.4,
            TaskType.TEXT_GENERATION: 0.5,
        }
        task_complexity_score = task_complexity_scores.get(request.task_type, 0.5)

        # Factor 3: Domain specificity (simple heuristic based on technical terms)
        technical_terms = [
            "algorithm", "database", "api", "function", "method", "class",
            "sql", "python", "javascript", "react", "fastapi", "supabase",
            "extraction", "parsing", "schema", "query", "endpoint"
        ]
        domain_specificity_score = min(
            sum(1 for term in technical_terms if term.lower() in request.prompt.lower()) / 10,
            1.0
        )

        # Weighted combination
        complexity_score = (
            factors.get("prompt_length", 0.2) * prompt_length_score +
            factors.get("task_complexity", 0.5) * task_complexity_score +
            factors.get("domain_specificity", 0.3) * domain_specificity_score
        )

        return round(complexity_score, 3)

    def select_model(self, request: GenerationRequest) -> str:
        """
        Select the optimal model for the given request.

        Selection logic:
        - High complexity (>0.7) → gemini-2.5-pro (best quality)
        - Medium complexity (0.4-0.7) → gemini-2.5-flash (balanced)
        - Low complexity (<0.4) → gemini-2.5-flash-lite (lowest cost)
        """
        complexity_score = self.calculate_complexity_score(request)

        if complexity_score > 0.7:
            return "gemini-2.5-pro"
        elif complexity_score > 0.4:
            return "gemini-2.5-flash"
        else:
            return "gemini-2.5-flash-lite"

    def calculate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost for a generation request."""
        model = self.models.get(model_id)
        if not model:
            return 0.0

        input_cost = (input_tokens / 1000) * model.input_cost_per_1k_tokens
        output_cost = (output_tokens / 1000) * model.output_cost_per_1k_tokens
        return input_cost + output_cost

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate content using the optimal model for the request.

        Args:
            request: Generation request with prompt and parameters

        Returns:
            GenerationResponse with content, model used, tokens, and cost

        Raises:
            ValueError: If API key is not configured
            httpx.HTTPError: If API request fails
        """
        api_key = self.config.get("api_key") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        # Select optimal model
        model_id = self.select_model(request)
        model = self.models[model_id]

        # Initialize HTTP client if needed
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=self.config.get("timeout", 60))

        # Prepare request payload
        payload = {
            "contents": [
                {
                    "parts": [{"text": request.prompt}]
                }
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "topP": request.top_p,
                "maxOutputTokens": request.max_tokens or model.max_tokens,
            }
        }

        # Add system prompt if provided
        if request.system_prompt:
            payload["contents"].insert(0, {
                "parts": [{"text": request.system_prompt}]
            })

        # Make API request
        start_time = time.time()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"

        max_retries = self.config.get("max_retries", 3)
        last_error = None

        for attempt in range(max_retries):
            try:
                response = await self.http_client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                # Extract generated content
                content = ""
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        content = "".join(
                            part.get("text", "") for part in candidate["content"]["parts"]
                        )

                # Extract token usage
                usage_metadata = data.get("usageMetadata", {})
                input_tokens = usage_metadata.get("promptTokenCount", 0)
                output_tokens = usage_metadata.get("candidatesTokenCount", 0)
                total_tokens = usage_metadata.get("totalTokenCount", input_tokens + output_tokens)

                # Calculate cost
                cost = self.calculate_cost(model_id, input_tokens, output_tokens)

                # Calculate generation time
                generation_time = time.time() - start_time

                # Track cost if enabled
                if self.config.get("enable_cost_tracking", True):
                    cost_entry = CostEntry(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        model_id=model_id,
                        task_type=request.task_type.value,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=total_tokens,
                        cost=cost,
                        generation_time=generation_time,
                    )
                    self.cost_tracker.add_cost_entry(cost_entry)

                # Calculate final complexity score
                complexity_score = self.calculate_complexity_score(request)

                return GenerationResponse(
                    content=content,
                    model_used=model_id,
                    tokens_used={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                    },
                    cost=cost,
                    generation_time=round(generation_time, 3),
                    complexity_score=complexity_score,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            except httpx.HTTPError as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise

        raise last_error or Exception("Unknown error occurred during generation")

    async def close(self):
        """Close the HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get a summary of costs and usage."""
        return {
            "total_cost": round(self.cost_tracker.get_total_cost(), 6),
            "total_tokens": self.cost_tracker.get_total_tokens(),
            "total_requests": self.cost_tracker.get_total_requests(),
            "average_cost_per_request": round(self.cost_tracker.get_average_cost_per_request(), 6),
            "average_tokens_per_request": round(self.cost_tracker.get_average_tokens_per_request(), 1),
            "cost_by_model": {
                model: round(cost, 6)
                for model, cost in self.cost_tracker.get_cost_by_model().items()
            },
            "cost_by_task_type": {
                task: round(cost, 6)
                for task, cost in self.cost_tracker.get_cost_by_task_type().items()
            },
        }

    def get_recent_generations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent generation entries."""
        recent_costs = self.cost_tracker.get_recent_costs(limit)
        return [
            {
                "timestamp": entry.timestamp,
                "model_id": entry.model_id,
                "task_type": entry.task_type,
                "tokens": {
                    "input": entry.input_tokens,
                    "output": entry.output_tokens,
                    "total": entry.total_tokens,
                },
                "cost": round(entry.cost, 6),
                "generation_time": entry.generation_time,
            }
            for entry in recent_costs
        ]


# Global router instance
_router_instance: Optional[IntelligentModelRouter] = None
_router_lock = Lock()


def get_router() -> IntelligentModelRouter:
    """Get the global router instance (singleton pattern)."""
    global _router_instance
    if _router_instance is None:
        with _router_lock:
            if _router_instance is None:
                _router_instance = IntelligentModelRouter()
    return _router_instance