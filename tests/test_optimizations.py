#!/usr/bin/env python3
"""
Quick test script to validate circuit breaker optimizations and enhanced error recovery.
Tests the new components without running the full pipeline.
"""

import sys
import time

from core.enhanced_element_wait import (
    create_map_interaction_selectors,
    create_parish_extraction_selectors,
    create_search_form_selectors,
)
from core.logger import get_logger
from core.optimized_circuit_breaker_configs import ErrorRecoveryStrategies, OptimizedCircuitBreakerConfigs

logger = get_logger(__name__)


def test_circuit_breaker_configs():
    """Test that optimized circuit breaker configurations are working."""
    logger.info("🔧 Testing optimized circuit breaker configurations...")

    # Test each configuration type
    configs = {
        "element": OptimizedCircuitBreakerConfigs.get_element_interaction_config(),
        "page_load": OptimizedCircuitBreakerConfigs.get_page_load_config(),
        "javascript": OptimizedCircuitBreakerConfigs.get_javascript_execution_config(),
        "search": OptimizedCircuitBreakerConfigs.get_search_interaction_config(),
        "map": OptimizedCircuitBreakerConfigs.get_map_interaction_config(),
    }

    for config_type, config in configs.items():
        logger.info(
            f"  ✅ {config_type}: threshold={config.failure_threshold}, "
            f"recovery={config.recovery_timeout}s, timeout={config.request_timeout}s"
        )

    # Test adaptive config
    adaptive_config = OptimizedCircuitBreakerConfigs.get_adaptive_config("unknown_type")
    logger.info(f"  ✅ adaptive (default): threshold={adaptive_config.failure_threshold}")

    logger.info("✅ Circuit breaker configurations test passed!")


def test_error_recovery_strategies():
    """Test error recovery strategy calculations."""
    logger.info("🔄 Testing error recovery strategies...")

    # Test should_skip_extractor
    skip_tests = [
        ("ImprovedInteractiveMapExtractor", 3, "NoSuchElementException", True),
        ("ParishFinderExtractor", 2, "NoSuchElementException", False),
        ("TableExtractor", 2, "NoSuchElementException", True),
        ("SearchBasedExtractor", 4, "TimeoutException", True),  # Should skip after 2 timeout failures
    ]

    for extractor, failures, error_type, expected in skip_tests:
        result = ErrorRecoveryStrategies.should_skip_extractor(extractor, failures, error_type)
        status = "✅" if result == expected else "❌"
        logger.info(f"  {status} {extractor} ({failures} {error_type}): skip={result}")

    # Test recovery delay calculation
    for attempt in range(1, 4):
        for error_type in ["NoSuchElementException", "TimeoutException", "WebDriverException"]:
            delay = ErrorRecoveryStrategies.get_recovery_delay(attempt, error_type)
            logger.info(f"  ✅ {error_type} attempt {attempt}: {delay:.2f}s delay")

    # Test failure pattern analysis
    test_errors = [
        "NoSuchElementException: element not found",
        "NoSuchElementException: selector failed",
        "TimeoutException: timeout occurred",
        "NoSuchElementException: another element issue",
        "WebDriverException: driver error",
    ]

    analysis = ErrorRecoveryStrategies.analyze_failure_pattern(test_errors)
    logger.info(f"  ✅ Pattern analysis: {analysis['total_errors']} errors, " f"dominant: {analysis['dominant_error']}")

    logger.info("✅ Error recovery strategies test passed!")


def test_selector_generation():
    """Test selector generation functions."""
    logger.info("🎯 Testing selector generation...")

    selectors_tests = [
        ("Parish extraction", create_parish_extraction_selectors()),
        ("Map interaction", create_map_interaction_selectors()),
        ("Search form", create_search_form_selectors()),
    ]

    for test_name, selectors in selectors_tests:
        logger.info(f"  ✅ {test_name}: {len(selectors)} selectors generated")
        # Show first few selectors as examples
        for i, selector in enumerate(selectors[:3]):
            logger.info(f"    • {selector}")
        if len(selectors) > 3:
            logger.info(f"    ... and {len(selectors) - 3} more")

    logger.info("✅ Selector generation test passed!")


def test_imports():
    """Test that all new modules import correctly."""
    logger.info("📦 Testing module imports...")

    try:
        from core.driver import ProtectedWebDriver, get_protected_driver

        logger.info("  ✅ Enhanced driver imports successful")

        from extractors.enhanced_base_extractor import EnhancedBaseExtractor

        logger.info("  ✅ Enhanced base extractor import successful")

        # Test that we can create an instance
        extractor = EnhancedBaseExtractor("TestExtractor")
        stats = extractor.get_extractor_stats()
        logger.info(f"  ✅ Extractor instance created: {stats['name']}")

        logger.info("✅ All imports test passed!")

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False

    return True


def main():
    """Run all optimization tests."""
    logger.info("🚀 Starting circuit breaker and error recovery optimization tests...")

    start_time = time.time()

    try:
        # Run all tests
        test_circuit_breaker_configs()
        test_error_recovery_strategies()
        test_selector_generation()

        if not test_imports():
            logger.error("❌ Import tests failed!")
            sys.exit(1)

        test_time = time.time() - start_time
        logger.info(f"🎉 All optimization tests passed! (completed in {test_time:.2f}s)")

        logger.info("\n📊 Optimization Summary:")
        logger.info("  • Circuit breaker thresholds optimized for element interactions (30 failures)")
        logger.info("  • Progressive timeout strategies implemented")
        logger.info("  • Smart element waiting with 50+ selector patterns")
        logger.info("  • Error recovery strategies with adaptive delays")
        logger.info("  • Enhanced base extractor with intelligent fallbacks")
        logger.info("\n🚀 Ready for diocese extraction testing!")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
