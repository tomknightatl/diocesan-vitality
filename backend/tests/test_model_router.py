"""
Tests for the intelligent model routing system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from ai.model_router import (
    IntelligentModelRouter,
    GenerationRequest,
    GenerationResponse,
    CostTracker,
    CostEntry,
    TaskType,
    get_router,
)
from ai.models import (
    AIRequest,
    AIResponse,
    ModelCapabilityResponse,
    ModelsListResponse,
    TaskType as APITaskType,
)


class TestCostTracker:
    """Test cases for CostTracker."""

    def test_add_cost_entry(self):
        """Test adding cost entries."""
        tracker = CostTracker()
        entry = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model_id="gemini-2.5-flash",
            task_type="text_generation",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost=0.001,
            generation_time=1.5,
        )
        tracker.add_cost_entry(entry)

        assert tracker.get_total_requests() == 1
        assert tracker.get_total_cost() == 0.001
        assert tracker.get_total_tokens() == 150

    def test_multiple_entries(self):
        """Test adding multiple cost entries."""
        tracker = CostTracker()

        for i in range(5):
            entry = CostEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                model_id="gemini-2.5-flash",
                task_type="text_generation",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost=0.001,
                generation_time=1.5,
            )
            tracker.add_cost_entry(entry)

        assert tracker.get_total_requests() == 5
        assert tracker.get_total_cost() == 0.005
        assert tracker.get_average_cost_per_request() == 0.001

    def test_cost_by_model(self):
        """Test cost breakdown by model."""
        tracker = CostTracker()

        entry1 = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model_id="gemini-2.5-pro",
            task_type="extraction",
            input_tokens=200,
            output_tokens=100,
            total_tokens=300,
            cost=0.01,
            generation_time=2.0,
        )
        entry2 = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model_id="gemini-2.5-flash",
            task_type="text_generation",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost=0.001,
            generation_time=1.0,
        )
        tracker.add_cost_entry(entry1)
        tracker.add_cost_entry(entry2)

        model_costs = tracker.get_cost_by_model()
        assert model_costs["gemini-2.5-pro"] == 0.01
        assert model_costs["gemini-2.5-flash"] == 0.001

    def test_max_entries_limit(self):
        """Test that max entries limit is respected."""
        tracker = CostTracker(max_entries=10)

        for i in range(20):
            entry = CostEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                model_id="gemini-2.5-flash",
                task_type="text_generation",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost=0.001,
                generation_time=1.5,
            )
            tracker.add_cost_entry(entry)

        # Should only keep the most recent 10 entries
        assert len(tracker.costs) == 10
        assert tracker.get_total_requests() == 20  # But still track total count


class TestIntelligentModelRouter:
    """Test cases for IntelligentModelRouter."""

    def test_initialization(self):
        """Test router initialization."""
        router = IntelligentModelRouter()
        assert len(router.models) == 3
        assert "gemini-2.5-pro" in router.models
        assert "gemini-2.5-flash" in router.models
        assert "gemini-2.5-flash-lite" in router.models

    def test_get_available_models(self):
        """Test getting available models."""
        router = IntelligentModelRouter()
        models = router.get_available_models()
        assert len(models) == 3

    def test_get_model(self):
        """Test getting a specific model."""
        router = IntelligentModelRouter()
        model = router.get_model("gemini-2.5-flash")
        assert model is not None
        assert model.model_id == "gemini-2.5-flash"
        assert model.name == "Gemini 2.5 Flash"

    def test_calculate_complexity_score_simple(self):
        """Test complexity calculation for simple task."""
        router = IntelligentModelRouter()
        request = GenerationRequest(
            prompt="Hello world",
            task_type=TaskType.TEXT_GENERATION,
        )
        score = router.calculate_complexity_score(request)
        assert 0.0 <= score <= 1.0
        assert score < 0.4  # Should be low complexity

    def test_calculate_complexity_score_complex(self):
        """Test complexity calculation for complex task."""
        router = IntelligentModelRouter()
        request = GenerationRequest(
            prompt="Extract structured data from this HTML document using advanced parsing algorithms and database schema mapping",
            task_type=TaskType.EXTRACTION,
        )
        score = router.calculate_complexity_score(request)
        assert 0.0 <= score <= 1.0
        assert score > 0.7  # Should be high complexity

    def test_calculate_complexity_score_override(self):
        """Test complexity score override."""
        router = IntelligentModelRouter()
        request = GenerationRequest(
            prompt="Simple prompt",
            task_type=TaskType.TEXT_GENERATION,
            complexity_score=0.9,  # Override
        )
        score = router.calculate_complexity_score(request)
        assert score == 0.9

    def test_select_model_high_complexity(self):
        """Test model selection for high complexity."""
        router = IntelligentModelRouter()
        request = GenerationRequest(
            prompt="Complex extraction task with database schema mapping",
            task_type=TaskType.EXTRACTION,
        )
        model_id = router.select_model(request)
        assert model_id == "gemini-2.5-pro"

    def test_select_model_medium_complexity(self):
        """Test model selection for medium complexity."""
        router = IntelligentModelRouter()
        request = GenerationRequest(
            prompt="Summarize this text about church activities",
            task_type=TaskType.SUMMARIZATION,
        )
        model_id = router.select_model(request)
        assert model_id == "gemini-2.5-flash"

    def test_select_model_low_complexity(self):
        """Test model selection for low complexity."""
        router = IntelligentModelRouter()
        request = GenerationRequest(
            prompt="Hello",
            task_type=TaskType.TEXT_GENERATION,
        )
        model_id = router.select_model(request)
        assert model_id == "gemini-2.5-flash-lite"

    def test_calculate_cost(self):
        """Test cost calculation."""
        router = IntelligentModelRouter()
        cost = router.calculate_cost("gemini-2.5-flash", 1000, 500)
        expected_cost = (1000 / 1000) * 0.000075 + (500 / 1000) * 0.0003
        assert abs(cost - expected_cost) < 0.000001

    def test_get_cost_summary(self):
        """Test getting cost summary."""
        router = IntelligentModelRouter()

        # Add some test data
        entry = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model_id="gemini-2.5-flash",
            task_type="text_generation",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost=0.001,
            generation_time=1.5,
        )
        router.cost_tracker.add_cost_entry(entry)

        summary = router.get_cost_summary()
        assert summary["total_cost"] == 0.001
        assert summary["total_tokens"] == 150
        assert summary["total_requests"] == 1

    def test_reload_config(self):
        """Test reloading configuration."""
        router = IntelligentModelRouter()
        original_config = router.config.copy()
        router.reload_config()
        # Should not raise an error
        assert router.config is not None


class TestGenerationRequest:
    """Test cases for GenerationRequest."""

    def test_creation(self):
        """Test creating a generation request."""
        request = GenerationRequest(
            prompt="Test prompt",
            task_type=TaskType.TEXT_GENERATION,
            max_tokens=100,
            temperature=0.5,
        )
        assert request.prompt == "Test prompt"
        assert request.task_type == TaskType.TEXT_GENERATION
        assert request.max_tokens == 100
        assert request.temperature == 0.5


class TestTaskTypes:
    """Test cases for TaskType enum."""

    def test_task_types(self):
        """Test all task types are defined."""
        assert TaskType.TEXT_GENERATION == "text_generation"
        assert TaskType.EXTRACTION == "extraction"
        assert TaskType.ANALYSIS == "analysis"
        assert TaskType.SUMMARIZATION == "summarization"
        assert TaskType.TRANSLATION == "translation"
        assert TaskType.CODE_GENERATION == "code_generation"
        assert TaskType.QUESTION_ANSWERING == "question_answering"


class TestSingletonRouter:
    """Test cases for singleton router pattern."""

    def test_get_router_singleton(self):
        """Test that get_router returns the same instance."""
        router1 = get_router()
        router2 = get_router()
        assert router1 is router2


class TestAPIModels:
    """Test cases for API Pydantic models."""

    def test_ai_request_validation(self):
        """Test AI request validation."""
        request = AIRequest(
            prompt="Test prompt",
            task_type=APITaskType.TEXT_GENERATION,
            temperature=0.7,
        )
        assert request.prompt == "Test prompt"
        assert request.task_type == APITaskType.TEXT_GENERATION

    def test_ai_request_invalid_temperature(self):
        """Test AI request with invalid temperature."""
        with pytest.raises(Exception):
            AIRequest(
                prompt="Test prompt",
                task_type=APITaskType.TEXT_GENERATION,
                temperature=1.5,  # Invalid: > 1.0
            )

    def test_ai_response_creation(self):
        """Test AI response creation."""
        response = AIResponse(
            content="Generated content",
            model_used="gemini-2.5-flash",
            tokens_used={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            cost=0.001,
            generation_time=1.5,
            complexity_score=0.5,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        assert response.content == "Generated content"
        assert response.model_used == "gemini-2.5-flash"
        assert response.cost == 0.001


@pytest.mark.asyncio
class TestAsyncGeneration:
    """Test cases for async generation."""

    async def test_generate_without_api_key(self):
        """Test generation fails without API key."""
        router = IntelligentModelRouter()
        router.config["api_key"] = ""

        request = GenerationRequest(
            prompt="Test prompt",
            task_type=TaskType.TEXT_GENERATION,
        )

        with pytest.raises(ValueError, match="GEMINI_API_KEY not configured"):
            await router.generate(request)

    async def test_generate_with_mock_response(self):
        """Test generation with mocked API response."""
        router = IntelligentModelRouter()
        router.config["api_key"] = "test_key"

        request = GenerationRequest(
            prompt="Test prompt",
            task_type=TaskType.TEXT_GENERATION,
        )

        # Mock the HTTP client
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Generated response"}]
                    }
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 20,
                "totalTokenCount": 30
            }
        })

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        router.http_client = mock_client

        response = await router.generate(request)

        assert response.content == "Generated response"
        assert response.tokens_used["total_tokens"] == 30
        assert response.model_used == "gemini-2.5-flash-lite"  # Low complexity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])