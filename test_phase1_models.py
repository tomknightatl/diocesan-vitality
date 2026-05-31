#!/usr/bin/env python3
"""
Test script for Phase 1 Model Upgrades.

This script validates that the new models are accessible and working correctly.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.ai_config import get_ai_config, reset_ai_config
from core.ai_model_factory import get_ai_model_factory, reset_ai_model_factory
from core.logger import get_logger

logger = get_logger(__name__)


def test_configuration():
    """Test that configuration is loaded correctly."""
    logger.info("=" * 60)
    logger.info("Testing Configuration Loading")
    logger.info("=" * 60)

    try:
        config = get_ai_config()

        # Test component models
        logger.info("\nComponent Model Assignments:")
        component_models = config.get_all_component_models()
        for component, model in component_models.items():
            logger.info(f"  {component}: {model}")

        # Test component parameters
        logger.info("\nComponent-Specific Parameters:")
        for component in ["content_analyzer", "schedule_extractor", "fallback_extractor", "url_filter", "parish_prioritizer"]:
            params = config.get_component_parameters(component)
            logger.info(f"  {component}:")
            for key, value in params.items():
                logger.info(f"    {key}: {value}")

        # Test cost optimization settings
        logger.info("\nCost Optimization Settings:")
        logger.info(f"  Enabled: {config.cost_optimization_enabled}")
        logger.info(f"  Budget Limit: ${config.budget_limit_usd}")
        logger.info(f"  Daily Quota: {config.daily_quota_tokens} tokens")
        logger.info(f"  Prefer Cheaper Models: {config.prefer_cheaper_models}")
        logger.info(f"  Smart Routing: {config.enable_smart_routing}")

        logger.info("\n✓ Configuration loaded successfully")
        return True

    except Exception as e:
        logger.error(f"✗ Configuration test failed: {e}")
        return False


def test_model_availability():
    """Test that all configured models are available."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Model Availability")
    logger.info("=" * 60)

    try:
        factory = get_ai_model_factory()

        # Get all configured models
        config = get_ai_config()
        component_models = config.get_all_component_models()
        unique_models = set(component_models.values())

        logger.info(f"\nTesting {len(unique_models)} unique models...")

        results = {}
        for model_name in unique_models:
            logger.info(f"\nTesting model: {model_name}")
            success, message = factory.test_model(model_name)
            results[model_name] = (success, message)

            if success:
                logger.info(f"  ✓ {message}")
            else:
                logger.error(f"  ✗ {message}")

        # Summary
        logger.info("\n" + "-" * 60)
        logger.info("Model Availability Summary:")
        successful = sum(1 for success, _ in results.values() if success)
        total = len(results)
        logger.info(f"  {successful}/{total} models available")

        for model_name, (success, message) in results.items():
            status = "✓" if success else "✗"
            logger.info(f"  {status} {model_name}: {message}")

        return all(success for success, _ in results.values())

    except Exception as e:
        logger.error(f"✗ Model availability test failed: {e}")
        return False


def test_model_creation():
    """Test that models can be created for each component."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Model Creation for Components")
    logger.info("=" * 60)

    try:
        factory = get_ai_model_factory()
        config = get_ai_config()

        components = ["content_analyzer", "schedule_extractor", "fallback_extractor", "url_filter", "parish_prioritizer"]

        results = {}
        for component in components:
            logger.info(f"\nCreating model for: {component}")
            try:
                model = factory.get_model(component)
                model_name = config.get_model_for_component(component)
                params = config.get_component_parameters(component)

                logger.info(f"  ✓ Model created: {model_name}")
                logger.info(f"    Parameters: {params}")
                results[component] = True

            except Exception as e:
                logger.error(f"  ✗ Failed to create model: {e}")
                results[component] = False

        # Summary
        logger.info("\n" + "-" * 60)
        logger.info("Model Creation Summary:")
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        logger.info(f"  {successful}/{total} components successful")

        for component, success in results.items():
            status = "✓" if success else "✗"
            logger.info(f"  {status} {component}")

        return all(results.values())

    except Exception as e:
        logger.error(f"✗ Model creation test failed: {e}")
        return False


def test_model_capabilities():
    """Test model capabilities metadata."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Model Capabilities")
    logger.info("=" * 60)

    try:
        factory = get_ai_model_factory()
        config = get_ai_config()

        component_models = config.get_all_component_models()
        unique_models = set(component_models.values())

        logger.info(f"\nRetrieving capabilities for {len(unique_models)} models...")

        for model_name in unique_models:
            logger.info(f"\n{model_name}:")
            capabilities = factory.get_model_capabilities(model_name)
            for key, value in capabilities.items():
                logger.info(f"  {key}: {value}")

        logger.info("\n✓ Model capabilities retrieved successfully")
        return True

    except Exception as e:
        logger.error(f"✗ Model capabilities test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("Phase 1 Model Upgrades - Test Suite")
    logger.info("=" * 60)

    # Reset to ensure fresh configuration
    reset_ai_config()
    reset_ai_model_factory()

    # Run tests
    tests = [
        ("Configuration Loading", test_configuration),
        ("Model Availability", test_model_availability),
        ("Model Creation", test_model_creation),
        ("Model Capabilities", test_model_capabilities),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results[test_name] = False

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("Final Test Summary")
    logger.info("=" * 60)

    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status}: {test_name}")

    overall_success = all(results.values())
    if overall_success:
        logger.info("\n🎉 All tests passed! Phase 1 model upgrades are working correctly.")
        return 0
    else:
        logger.error("\n❌ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())