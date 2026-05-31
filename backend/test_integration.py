#!/usr/bin/env python3
"""
Simple integration test for the intelligent model routing system.
This script verifies basic functionality without requiring pytest.
"""

import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from ai.model_router import (
            IntelligentModelRouter,
            GenerationRequest,
            GenerationResponse,
            CostTracker,
            CostEntry,
            TaskType,
            get_router,
        )
        print("✅ Successfully imported model_router module")
        return True
    except Exception as e:
        print(f"❌ Failed to import model_router: {e}")
        return False


def test_router_initialization():
    """Test router initialization."""
    print("\nTesting router initialization...")
    try:
        from ai.model_router import IntelligentModelRouter
        router = IntelligentModelRouter()
        assert len(router.models) == 3, f"Expected 3 models, got {len(router.models)}"
        assert "gemini-2.5-pro" in router.models
        assert "gemini-2.5-flash" in router.models
        assert "gemini-2.5-flash-lite" in router.models
        print("✅ Router initialized successfully with 3 models")
        return True
    except Exception as e:
        print(f"❌ Router initialization failed: {e}")
        return False


def test_model_selection():
    """Test model selection logic."""
    print("\nTesting model selection...")
    try:
        from ai.model_router import IntelligentModelRouter, GenerationRequest, TaskType
        router = IntelligentModelRouter()

        # Test high complexity
        request_high = GenerationRequest(
            prompt="Extract structured data from complex HTML with database schema mapping",
            task_type=TaskType.EXTRACTION,
        )
        model_high = router.select_model(request_high)
        assert model_high == "gemini-2.5-pro", f"Expected gemini-2.5-pro, got {model_high}"
        print(f"✅ High complexity task routed to {model_high}")

        # Test medium complexity
        request_medium = GenerationRequest(
            prompt="Summarize this text about church activities",
            task_type=TaskType.SUMMARIZATION,
        )
        model_medium = router.select_model(request_medium)
        assert model_medium == "gemini-2.5-flash", f"Expected gemini-2.5-flash, got {model_medium}"
        print(f"✅ Medium complexity task routed to {model_medium}")

        # Test low complexity
        request_low = GenerationRequest(
            prompt="Hello",
            task_type=TaskType.TEXT_GENERATION,
        )
        model_low = router.select_model(request_low)
        assert model_low == "gemini-2.5-flash-lite", f"Expected gemini-2.5-flash-lite, got {model_low}"
        print(f"✅ Low complexity task routed to {model_low}")

        return True
    except Exception as e:
        print(f"❌ Model selection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complexity_calculation():
    """Test complexity score calculation."""
    print("\nTesting complexity calculation...")
    try:
        from ai.model_router import IntelligentModelRouter, GenerationRequest, TaskType
        router = IntelligentModelRouter()

        # Test simple task
        request_simple = GenerationRequest(
            prompt="Hello world",
            task_type=TaskType.TEXT_GENERATION,
        )
        score_simple = router.calculate_complexity_score(request_simple)
        assert 0.0 <= score_simple <= 1.0, f"Invalid score: {score_simple}"
        assert score_simple < 0.4, f"Simple task should have low complexity, got {score_simple}"
        print(f"✅ Simple task complexity: {score_simple:.3f}")

        # Test complex task
        request_complex = GenerationRequest(
            prompt="Extract structured data from this HTML document using advanced parsing algorithms and database schema mapping",
            task_type=TaskType.EXTRACTION,
        )
        score_complex = router.calculate_complexity_score(request_complex)
        assert 0.0 <= score_complex <= 1.0, f"Invalid score: {score_complex}"
        assert score_complex > 0.7, f"Complex task should have high complexity, got {score_complex}"
        print(f"✅ Complex task complexity: {score_complex:.3f}")

        # Test override
        request_override = GenerationRequest(
            prompt="Simple",
            task_type=TaskType.TEXT_GENERATION,
            complexity_score=0.9,
        )
        score_override = router.calculate_complexity_score(request_override)
        assert score_override == 0.9, f"Override failed, got {score_override}"
        print(f"✅ Complexity override works: {score_override:.3f}")

        return True
    except Exception as e:
        print(f"❌ Complexity calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cost_tracking():
    """Test cost tracking functionality."""
    print("\nTesting cost tracking...")
    try:
        from ai.model_router import CostTracker, CostEntry
        from datetime import datetime, timezone

        tracker = CostTracker()

        # Add some test entries
        entry1 = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model_id="gemini-2.5-flash",
            task_type="text_generation",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost=0.001,
            generation_time=1.5,
        )
        tracker.add_cost_entry(entry1)

        entry2 = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model_id="gemini-2.5-pro",
            task_type="extraction",
            input_tokens=200,
            output_tokens=100,
            total_tokens=300,
            cost=0.01,
            generation_time=2.0,
        )
        tracker.add_cost_entry(entry2)

        # Verify tracking
        assert tracker.get_total_requests() == 2, f"Expected 2 requests, got {tracker.get_total_requests()}"
        assert tracker.get_total_cost() == 0.011, f"Expected 0.011 cost, got {tracker.get_total_cost()}"
        assert tracker.get_total_tokens() == 450, f"Expected 450 tokens, got {tracker.get_total_tokens()}"

        # Verify breakdown
        model_costs = tracker.get_cost_by_model()
        assert model_costs["gemini-2.5-flash"] == 0.001
        assert model_costs["gemini-2.5-pro"] == 0.01

        print(f"✅ Cost tracking works correctly")
        print(f"   - Total requests: {tracker.get_total_requests()}")
        print(f"   - Total cost: ${tracker.get_total_cost():.6f}")
        print(f"   - Total tokens: {tracker.get_total_tokens()}")
        print(f"   - Average cost per request: ${tracker.get_average_cost_per_request():.6f}")

        return True
    except Exception as e:
        print(f"❌ Cost tracking failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cost_calculation():
    """Test cost calculation."""
    print("\nTesting cost calculation...")
    try:
        from ai.model_router import IntelligentModelRouter
        router = IntelligentModelRouter()

        # Test gemini-2.5-flash
        cost_flash = router.calculate_cost("gemini-2.5-flash", 1000, 500)
        expected_flash = (1000 / 1000) * 0.000075 + (500 / 1000) * 0.0003
        assert abs(cost_flash - expected_flash) < 0.000001, f"Cost calculation error: {cost_flash} vs {expected_flash}"
        print(f"✅ gemini-2.5-flash cost: ${cost_flash:.6f}")

        # Test gemini-2.5-pro
        cost_pro = router.calculate_cost("gemini-2.5-pro", 1000, 500)
        expected_pro = (1000 / 1000) * 0.00125 + (500 / 1000) * 0.005
        assert abs(cost_pro - expected_pro) < 0.000001, f"Cost calculation error: {cost_pro} vs {expected_pro}"
        print(f"✅ gemini-2.5-pro cost: ${cost_pro:.6f}")

        # Test gemini-2.5-flash-lite
        cost_lite = router.calculate_cost("gemini-2.5-flash-lite", 1000, 500)
        expected_lite = (1000 / 1000) * 0.0000375 + (500 / 1000) * 0.00015
        assert abs(cost_lite - expected_lite) < 0.000001, f"Cost calculation error: {cost_lite} vs {expected_lite}"
        print(f"✅ gemini-2.5-flash-lite cost: ${cost_lite:.6f}")

        return True
    except Exception as e:
        print(f"❌ Cost calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_singleton_pattern():
    """Test singleton pattern for router."""
    print("\nTesting singleton pattern...")
    try:
        from ai.model_router import get_router

        router1 = get_router()
        router2 = get_router()

        assert router1 is router2, "Singleton pattern failed - different instances returned"
        print("✅ Singleton pattern works correctly")

        return True
    except Exception as e:
        print(f"❌ Singleton pattern test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_models():
    """Test API Pydantic models."""
    print("\nTesting API models...")
    try:
        from ai.models import AIRequest, AIResponse, TaskType as APITaskType

        # Test AIRequest
        request = AIRequest(
            prompt="Test prompt",
            task_type=APITaskType.TEXT_GENERATION,
            temperature=0.7,
        )
        assert request.prompt == "Test prompt"
        assert request.task_type == APITaskType.TEXT_GENERATION
        print("✅ AIRequest model works")

        # Test AIResponse
        response = AIResponse(
            content="Generated content",
            model_used="gemini-2.5-flash",
            tokens_used={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            cost=0.001,
            generation_time=1.5,
            complexity_score=0.5,
            timestamp="2024-01-01T12:00:00Z",
        )
        assert response.content == "Generated content"
        assert response.model_used == "gemini-2.5-flash"
        print("✅ AIResponse model works")

        return True
    except Exception as e:
        print(f"❌ API models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Intelligent Model Routing System - Integration Tests")
    print("=" * 60)

    tests = [
        test_imports,
        test_router_initialization,
        test_model_selection,
        test_complexity_calculation,
        test_cost_tracking,
        test_cost_calculation,
        test_singleton_pattern,
        test_api_models,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())