#!/usr/bin/env python3
"""
Test script for Circuit Breaker Pattern implementation.
Validates circuit breaker functionality with different failure scenarios.
"""

import random
import time

from core.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    circuit_breaker,
    circuit_manager,
)
from core.logger import get_logger

logger = get_logger(__name__)


# Test functions with different failure patterns
@circuit_breaker(
    "test_service_unreliable",
    CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=5,
        request_timeout=2,
        max_retries=1,
        retry_delay=0.5,
    ),
)
def unreliable_service(fail_probability=0.7):
    """Simulates an unreliable service that fails randomly"""
    if random.random() < fail_probability:
        raise Exception("Service temporarily unavailable")
    return "Success"


@circuit_breaker(
    "test_service_timeout",
    CircuitBreakerConfig(failure_threshold=2, recovery_timeout=3, request_timeout=1, max_retries=0),
)
def timeout_service(delay=2):
    """Simulates a service that times out"""
    time.sleep(delay)
    return "Success after delay"


@circuit_breaker(
    "test_service_reliable",
    CircuitBreakerConfig(failure_threshold=5, recovery_timeout=10, request_timeout=5, max_retries=2),
)
def reliable_service():
    """Simulates a reliable service"""
    return "Reliable success"


def _test_normal_operation():
    """Test 1: Normal operation scenario"""
    logger.info("\n📋 Test 1: Normal Operation")
    try:
        for i in range(3):
            result = reliable_service()
            logger.info(f"✅ Call {i + 1}: {result}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")


def _test_unreliable_service():
    """Test 2: Service with failures (should trigger circuit breaker)"""
    logger.info("\n📋 Test 2: Unreliable Service (Circuit Breaker Should Open)")
    failure_count = 0
    success_count = 0
    blocked_count = 0

    for i in range(10):
        try:
            result = unreliable_service(fail_probability=0.8)
            success_count += 1
            logger.info(f"✅ Call {i + 1}: {result}")
        except CircuitBreakerOpenError:
            blocked_count += 1
            logger.warning(f"🚫 Call {i + 1}: Blocked by circuit breaker")
        except Exception as e:
            failure_count += 1
            logger.warning(f"❌ Call {i + 1}: {str(e)}")

        time.sleep(0.1)  # Small delay between calls

    logger.info(f"📊 Test 2 Results: {success_count} successes, {failure_count} failures, {blocked_count} blocked")


def _test_timeout_service():
    """Test 3: Timeout scenario"""
    logger.info("\n📋 Test 3: Timeout Service")
    for i in range(3):
        try:
            result = timeout_service(delay=1.5)  # Should timeout
            logger.info(f"✅ Call {i + 1}: {result}")
        except CircuitBreakerOpenError:
            logger.warning(f"🚫 Call {i + 1}: Blocked by circuit breaker")
        except Exception as e:
            logger.warning(f"⏰ Call {i + 1}: Timeout - {str(e)}")


def _test_circuit_recovery():
    """Test 4: Recovery after circuit opens"""
    logger.info("\n📋 Test 4: Circuit Recovery Test")
    logger.info("⏳ Waiting for recovery timeout...")
    time.sleep(6)  # Wait for recovery timeout

    # Try the unreliable service again with better odds
    logger.info("🔄 Testing recovery with improved service reliability...")
    for i in range(5):
        try:
            result = unreliable_service(fail_probability=0.2)  # Much more reliable
            logger.info(f"✅ Recovery call {i + 1}: {result}")
        except CircuitBreakerOpenError:
            logger.warning(f"🚫 Recovery call {i + 1}: Still blocked")
        except Exception as e:
            logger.warning(f"❌ Recovery call {i + 1}: {str(e)}")

        time.sleep(0.2)


def _log_final_statistics():
    """Log final circuit breaker statistics"""
    logger.info("\n📊 Final Circuit Breaker Statistics:")
    circuit_manager.log_summary()


def test_circuit_breaker_functionality():
    """Test various circuit breaker scenarios"""

    logger.info("🧪 Starting Circuit Breaker Tests")
    logger.info("=" * 50)

    # Execute test scenarios
    _test_normal_operation()
    _test_unreliable_service()
    _test_timeout_service()
    _test_circuit_recovery()
    _log_final_statistics()


def test_protected_driver():
    """Test the protected WebDriver functionality"""
    from core.driver import get_protected_driver

    logger.info("\n🚗 Testing Protected WebDriver")
    logger.info("=" * 30)

    driver = get_protected_driver(timeout=10)
    if not driver:
        logger.error("❌ Failed to create protected driver")
        return

    # Test loading a real webpage
    test_urls = [
        "https://www.google.com",
        "https://httpstat.us/500",  # Should fail
        "https://httpstat.us/200?sleep=5000",  # Should timeout
        "https://www.example.com",
    ]

    for url in test_urls:
        try:
            logger.info(f"🌐 Testing URL: {url}")
            driver.get(url, timeout=3)
            logger.info(f"✅ Successfully loaded: {url}")
        except Exception as e:
            logger.warning(f"❌ Failed to load {url}: {str(e)}")

        time.sleep(1)

    # Close driver
    driver.quit()
    logger.info("🏁 Driver testing completed")


if __name__ == "__main__":
    # Run circuit breaker tests
    test_circuit_breaker_functionality()

    # Uncomment to test protected driver (requires Chrome)
    # test_protected_driver()

    logger.info("\n🎉 All tests completed!")
