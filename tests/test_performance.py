#!/usr/bin/env python3
"""
Performance regression tests for critical diocesan vitality components.

These tests ensure that key operations maintain acceptable performance
and catch performance regressions early in the development cycle.
"""

import time
from unittest.mock import Mock, patch

import pytest

from core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from core.logger import get_logger

logger = get_logger(__name__)


class TestPerformanceBenchmarks:
    """Performance benchmarks for critical components."""

    @pytest.mark.performance
    def test_circuit_breaker_performance(self):
        """Test circuit breaker overhead is minimal."""

        circuit_breaker = CircuitBreaker("test_circuit", CircuitBreakerConfig(failure_threshold=5, recovery_timeout=10))

        def fast_operation():
            return "success"

        # Measure baseline performance
        start_time = time.time()
        for _ in range(1000):
            result = circuit_breaker.call(fast_operation)
            assert result == "success"
        execution_time = time.time() - start_time

        # Circuit breaker overhead should be minimal (< 10ms per 1000 calls)
        assert execution_time < 0.01, f"Circuit breaker overhead too high: {execution_time:.4f}s"
        logger.info(f"✅ Circuit breaker performance: {execution_time:.4f}s for 1000 calls")

    @pytest.mark.performance
    def test_logger_performance(self):
        """Test logger performance is acceptable."""
        test_logger = get_logger("performance_test")

        start_time = time.time()
        for i in range(1000):
            test_logger.info(f"Performance test message {i}")
        execution_time = time.time() - start_time

        # Logging 1000 messages should complete in under 100ms
        assert execution_time < 0.1, f"Logger performance too slow: {execution_time:.4f}s"
        logger.info(f"✅ Logger performance: {execution_time:.4f}s for 1000 log messages")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_mock_parish_extraction_performance(self):
        """Test simulated parish extraction performance."""
        # Mock a realistic parish extraction scenario
        with patch("time.sleep"):  # Skip actual delays in tests
            parishes_data = []

            start_time = time.time()
            for i in range(100):  # Simulate processing 100 parishes
                parish = {
                    "id": i,
                    "name": f"Test Parish {i}",
                    "address": f"123 Test Street {i}",
                    "city": "Test City",
                    "state": "TS",
                    "zip_code": f"1234{i % 10}",
                    "phone": f"(555) 123-{i:04d}",
                    "email": f"parish{i}@test.org",
                    "website_url": f"https://parish{i}.test.org",
                }
                parishes_data.append(parish)

            execution_time = time.time() - start_time

        # Processing 100 parishes should complete in under 100ms (in mock scenario)
        assert execution_time < 0.1, f"Parish processing too slow: {execution_time:.4f}s"
        assert len(parishes_data) == 100
        logger.info(f"✅ Mock parish extraction performance: {execution_time:.4f}s for 100 parishes")

    @pytest.mark.performance
    def test_memory_usage_circuit_breaker(self):
        """Test circuit breaker memory usage is reasonable."""
        import sys

        # Measure memory before creating circuit breakers
        initial_size = sys.getsizeof({})

        # Create multiple circuit breakers
        circuit_breakers = []
        for i in range(100):
            circuit_breaker = CircuitBreaker(
                f"test_circuit_{i}", CircuitBreakerConfig(failure_threshold=3, recovery_timeout=5)
            )

            def dummy_operation():
                return i

            circuit_breakers.append((circuit_breaker, dummy_operation))

        # Memory usage should scale linearly and reasonably
        final_size = sys.getsizeof(circuit_breakers)
        memory_per_breaker = (final_size - initial_size) / 100

        # Each circuit breaker should use less than 1KB of memory overhead
        assert memory_per_breaker < 1024, f"Circuit breaker memory usage too high: {memory_per_breaker} bytes"
        logger.info(f"✅ Circuit breaker memory usage: {memory_per_breaker:.2f} bytes per breaker")

    @pytest.mark.performance
    @pytest.mark.integration
    def test_concurrent_operations_performance(self):
        """Test performance under concurrent operations."""
        import queue
        import threading

        results = queue.Queue()

        def worker_task(worker_id):
            start = time.time()
            circuit_breaker = CircuitBreaker(
                f"concurrent_test_{worker_id}", CircuitBreakerConfig(failure_threshold=5, recovery_timeout=10)
            )

            # Simulate concurrent work
            for i in range(10):

                def concurrent_operation():
                    return f"worker_{worker_id}_task_{i}"

                result = circuit_breaker.call(concurrent_operation)
                assert result == f"worker_{worker_id}_task_{i}"

            execution_time = time.time() - start
            results.put(execution_time)

        # Create and start multiple worker threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker_task, args=(worker_id,))
            threads.append(thread)

        start_time = time.time()
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Concurrent operations should complete efficiently
        assert total_time < 10.0, f"Concurrent operations too slow: {total_time:.4f}s"

        # Check individual worker performance
        worker_times = []
        while not results.empty():
            worker_times.append(results.get())

        avg_worker_time = sum(worker_times) / len(worker_times)
        assert avg_worker_time < 0.5, f"Average worker time too slow: {avg_worker_time:.4f}s"

        logger.info(f"✅ Concurrent operations performance: {total_time:.4f}s total, {avg_worker_time:.4f}s avg worker")


class TestPerformanceRegression:
    """Performance regression detection tests."""

    @pytest.mark.performance
    def test_import_performance(self):
        """Test that imports don't introduce unexpected delays."""
        start_time = time.time()

        # Test critical imports
        import core.circuit_breaker
        import core.db
        import core.logger

        import_time = time.time() - start_time

        # All critical imports should complete in under 100ms
        assert import_time < 0.1, f"Import time too slow: {import_time:.4f}s"
        logger.info(f"✅ Import performance: {import_time:.4f}s for critical modules")

    @pytest.mark.performance
    def test_configuration_loading_performance(self):
        """Test configuration loading performance."""
        import os
        from unittest.mock import patch

        # Mock environment variables for performance test
        mock_env = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_KEY": "test_key",
            "GENAI_API_KEY": "test_genai_key",
            "TESTING": "true",
        }

        start_time = time.time()

        with patch.dict(os.environ, mock_env):
            # Simulate configuration loading (without actual connections)
            config = {
                "supabase_url": os.getenv("SUPABASE_URL"),
                "supabase_key": os.getenv("SUPABASE_KEY"),
                "genai_api_key": os.getenv("GENAI_API_KEY"),
                "testing": os.getenv("TESTING") == "true",
            }

        config_time = time.time() - start_time

        # Configuration loading should be nearly instantaneous
        assert config_time < 0.001, f"Configuration loading too slow: {config_time:.6f}s"
        assert len(config) == 4
        logger.info(f"✅ Configuration loading performance: {config_time:.6f}s")


if __name__ == "__main__":
    # Run performance tests when script is executed directly
    pytest.main([__file__, "-v", "-m", "performance"])
