"""
Pydantic models for AI API requests and responses.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class TaskType(str, Enum):
    """Types of AI tasks that can be performed."""
    TEXT_GENERATION = "text_generation"
    EXTRACTION = "extraction"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CODE_GENERATION = "code_generation"
    QUESTION_ANSWERING = "question_answering"


class AIRequest(BaseModel):
    """Request model for AI generation endpoint."""
    prompt: str = Field(..., description="The prompt to generate content from", min_length=1)
    task_type: TaskType = Field(
        default=TaskType.TEXT_GENERATION,
        description="Type of task to perform"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens to generate (null for model default)",
        ge=1,
        le=8192
    )
    temperature: float = Field(
        default=0.7,
        description="Sampling temperature (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    top_p: float = Field(
        default=0.9,
        description="Nucleus sampling parameter (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional system prompt to guide generation"
    )
    complexity_score: Optional[float] = Field(
        default=None,
        description="Optional complexity score (0-1) to override automatic calculation",
        ge=0.0,
        le=1.0
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the request"
    )


class AIResponse(BaseModel):
    """Response model for AI generation endpoint."""
    content: str = Field(..., description="Generated content")
    model_used: str = Field(..., description="Model ID that was used")
    tokens_used: Dict[str, int] = Field(
        ...,
        description="Token usage breakdown"
    )
    cost: float = Field(..., description="Estimated cost in USD")
    generation_time: float = Field(..., description="Generation time in seconds")
    complexity_score: float = Field(..., description="Complexity score (0-1)")
    timestamp: str = Field(..., description="ISO timestamp of generation")


class ModelCapabilityResponse(BaseModel):
    """Response model for model capability information."""
    model_id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Human-readable model name")
    description: str = Field(..., description="Model description")
    max_tokens: int = Field(..., description="Maximum output tokens")
    context_window: int = Field(..., description="Context window size")
    supports_function_calling: bool = Field(..., description="Whether model supports function calling")
    supports_vision: bool = Field(..., description="Whether model supports vision")
    input_cost_per_1k_tokens: float = Field(..., description="Input cost per 1K tokens (USD)")
    output_cost_per_1k_tokens: float = Field(..., description="Output cost per 1K tokens (USD)")
    complexity_threshold: float = Field(..., description="Minimum complexity score to use this model")
    quality_score: float = Field(..., description="Quality score (0-1)")
    speed_score: float = Field(..., description="Speed score (0-1)")
    recommended_for: List[str] = Field(..., description="Recommended task types")


class ModelsListResponse(BaseModel):
    """Response model for listing available models."""
    models: List[ModelCapabilityResponse] = Field(..., description="List of available models")
    total_count: int = Field(..., description="Total number of models")


class AIConfigResponse(BaseModel):
    """Response model for AI configuration."""
    default_model: str = Field(..., description="Default model ID")
    max_retries: int = Field(..., description="Maximum retry attempts")
    timeout: int = Field(..., description="Request timeout in seconds")
    enable_cost_tracking: bool = Field(..., description="Whether cost tracking is enabled")
    complexity_calculation: Dict[str, Any] = Field(
        ...,
        description="Complexity calculation configuration"
    )


class CostSummaryResponse(BaseModel):
    """Response model for cost summary."""
    total_cost: float = Field(..., description="Total cost in USD")
    total_tokens: int = Field(..., description="Total tokens used")
    total_requests: int = Field(..., description="Total number of requests")
    average_cost_per_request: float = Field(..., description="Average cost per request")
    average_tokens_per_request: float = Field(..., description="Average tokens per request")
    cost_by_model: Dict[str, float] = Field(..., description="Cost breakdown by model")
    cost_by_task_type: Dict[str, float] = Field(..., description="Cost breakdown by task type")


class GenerationEntry(BaseModel):
    """Response model for a single generation entry."""
    timestamp: str = Field(..., description="ISO timestamp")
    model_id: str = Field(..., description="Model ID used")
    task_type: str = Field(..., description="Task type")
    tokens: Dict[str, int] = Field(..., description="Token usage")
    cost: float = Field(..., description="Cost in USD")
    generation_time: float = Field(..., description="Generation time in seconds")


class RecentGenerationsResponse(BaseModel):
    """Response model for recent generations."""
    generations: List[GenerationEntry] = Field(..., description="List of recent generations")
    total_count: int = Field(..., description="Total number of generations")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")