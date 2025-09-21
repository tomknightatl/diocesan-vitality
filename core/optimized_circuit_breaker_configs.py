#!/usr/bin/env python3
"""
Optimized circuit breaker configurations based on observed diocese extraction patterns.
Provides intelligent thresholds and recovery strategies for different types of operations.
"""

from core.circuit_breaker import CircuitBreakerConfig
from core.logger import get_logger

logger = get_logger(__name__)


class OptimizedCircuitBreakerConfigs:
    """
    Optimized circuit breaker configurations for different extraction scenarios.
    Based on analysis of Diocese of Honolulu and other complex sites.
    """

    @staticmethod
    def get_element_interaction_config() -> CircuitBreakerConfig:
        """
        Optimized config for element interaction operations.

        Key optimizations:
        - Higher failure threshold (30) since element not found is expected during selector testing
        - Shorter recovery timeout (10s) since element issues resolve quickly
        - Reduced max retries (1) to prevent excessive DOM queries
        - Shorter retry delay to speed up fallback attempts
        """
        return CircuitBreakerConfig(
            failure_threshold=15,  # Optimized from 30 - fail-fast on problematic dioceses
            recovery_timeout=10,  # Decreased from 15 - DOM issues resolve quickly
            success_threshold=2,  # Only need 2 successes to confirm recovery
            request_timeout=10,  # Shorter timeout for element operations
            max_retries=1,  # Reduced from 2 - DOM queries should be fast
            retry_delay=0.5,  # Faster retries for element operations
        )

    @staticmethod
    def get_page_load_config() -> CircuitBreakerConfig:
        """
        Optimized config for page loading operations.

        Key optimizations:
        - Lower failure threshold (5) since page load failures are more serious
        - Longer recovery timeout (30s) since network/server issues take time to resolve
        - Higher request timeout (45s) for slow diocesan websites
        """
        return CircuitBreakerConfig(
            failure_threshold=5,  # Page load failures are serious
            recovery_timeout=30,  # Network issues need time to resolve
            success_threshold=3,  # Need 3 successful loads to confirm recovery
            request_timeout=45,  # Some diocese sites are very slow
            max_retries=2,  # Reasonable retries for network operations
            retry_delay=2.0,  # Longer delay for network retries
        )

    @staticmethod
    def get_javascript_execution_config() -> CircuitBreakerConfig:
        """
        Optimized config for JavaScript execution operations.

        Key optimizations:
        - Moderate failure threshold (10) since JS failures can be temporary
        - Quick recovery timeout (15s) since JS engine issues resolve fast
        - Shorter timeout for individual JS operations
        """
        return CircuitBreakerConfig(
            failure_threshold=10,  # JS failures often temporary
            recovery_timeout=15,  # JS engine recovers quickly
            success_threshold=2,  # Quick recovery confirmation
            request_timeout=20,  # JS operations should be fast
            max_retries=2,  # Reasonable JS retries
            retry_delay=1.0,  # Standard retry delay
        )

    @staticmethod
    def get_search_interaction_config() -> CircuitBreakerConfig:
        """
        Specialized config for search form interactions.

        Key optimizations:
        - Higher failure threshold since search forms vary greatly
        - Longer timeout for search processing
        - More retries for complex search interfaces
        """
        return CircuitBreakerConfig(
            failure_threshold=15,  # Search forms have many variations
            recovery_timeout=20,  # Search backends need time
            success_threshold=2,  # Quick confirmation of working search
            request_timeout=30,  # Search processing can be slow
            max_retries=3,  # More retries for search complexity
            retry_delay=2.0,  # Longer delay for search operations
        )

    @staticmethod
    def get_map_interaction_config() -> CircuitBreakerConfig:
        """
        Specialized config for interactive map operations.

        Key optimizations:
        - Very high failure threshold since maps load dynamically
        - Longer timeouts for map tile loading
        - More retries for map marker interactions
        """
        return CircuitBreakerConfig(
            failure_threshold=25,  # Maps have complex loading patterns
            recovery_timeout=25,  # Map services need recovery time
            success_threshold=3,  # Need multiple successes for map stability
            request_timeout=35,  # Maps can be slow to load
            max_retries=3,  # Maps often need multiple attempts
            retry_delay=3.0,  # Longer delays for map loading
        )

    @staticmethod
    def get_url_verification_config() -> CircuitBreakerConfig:
        """
        Optimized config for URL verification operations.

        Key optimizations:
        - Low failure threshold (3) since URL verification should be fast
        - Short recovery timeout (5s) since DNS/connectivity issues resolve quickly
        - Quick timeout for individual URL checks
        - Minimal retries to avoid wasted time
        """
        return CircuitBreakerConfig(
            failure_threshold=3,  # URL verification should succeed quickly or fail fast
            recovery_timeout=5,  # DNS/connectivity recovers fast
            success_threshold=1,  # Single success confirms URL works
            request_timeout=8,  # Quick URL verification timeout
            max_retries=1,  # Minimal retries for URL checks
            retry_delay=0.3,  # Very fast retries
        )

    @staticmethod
    def get_ai_content_analysis_config() -> CircuitBreakerConfig:
        """
        Optimized config for AI content analysis operations.

        Key optimizations:
        - Higher failure threshold (5) since AI processing can be variable
        - Extended recovery timeout (120s) for AI service recovery
        - Longer timeout for large content processing (up to 2 minutes)
        - Minimal retries since AI operations are expensive
        """
        return CircuitBreakerConfig(
            failure_threshold=5,  # AI processing can have occasional failures
            recovery_timeout=120,  # AI services need time to recover from overload
            success_threshold=2,  # Need consistent AI responses
            request_timeout=120,  # Allow up to 2 minutes for large content processing
            max_retries=1,  # Minimal retries for expensive AI operations
            retry_delay=5.0,  # Longer delay for AI retry attempts
        )

    @staticmethod
    def get_adaptive_config(operation_type: str) -> CircuitBreakerConfig:
        """
        Get adaptive circuit breaker config based on operation type.

        Args:
            operation_type: Type of operation ('element', 'page_load', 'javascript',
                          'search', 'map', 'ai_content_analysis', or 'default')

        Returns:
            Optimized CircuitBreakerConfig for the operation type
        """
        configs = {
            "element": OptimizedCircuitBreakerConfigs.get_element_interaction_config(),
            "page_load": OptimizedCircuitBreakerConfigs.get_page_load_config(),
            "javascript": OptimizedCircuitBreakerConfigs.get_javascript_execution_config(),
            "search": OptimizedCircuitBreakerConfigs.get_search_interaction_config(),
            "map": OptimizedCircuitBreakerConfigs.get_map_interaction_config(),
            "url_verification": OptimizedCircuitBreakerConfigs.get_url_verification_config(),
            "ai_content_analysis": OptimizedCircuitBreakerConfigs.get_ai_content_analysis_config(),
        }

        config = configs.get(operation_type)
        if config:
            logger.debug(f"🔧 Using optimized circuit breaker config for '{operation_type}' operations")
            return config

        # Default configuration for unknown operation types
        logger.debug(f"🔧 Using default circuit breaker config for '{operation_type}' operations")
        return CircuitBreakerConfig(
            failure_threshold=10, recovery_timeout=30, success_threshold=3, request_timeout=30, max_retries=2, retry_delay=1.5
        )


class ErrorRecoveryStrategies:
    """
    Enhanced error recovery strategies for common diocese extraction failures.
    """

    @staticmethod
    def should_skip_extractor(extractor_name: str, failure_count: int, error_type: str) -> bool:
        """
        Determine if an extractor should be skipped based on failure patterns.

        Args:
            extractor_name: Name of the extractor
            failure_count: Number of consecutive failures
            error_type: Type of error encountered

        Returns:
            True if extractor should be skipped
        """
        # Skip extractors that consistently fail on element detection
        if error_type == "NoSuchElementException":
            skip_thresholds = {
                "ImprovedInteractiveMapExtractor": 3,  # Skip quickly if no map elements
                "TableExtractor": 2,  # Skip quickly if no tables
                "ParishFinderExtractor": 4,  # Give more chances to parish finder
                "NavigationExtractor": 2,  # Skip quickly if no navigation
                "SearchBasedExtractor": 5,  # Give search more chances
            }

            threshold = skip_thresholds.get(extractor_name, 3)
            if failure_count >= threshold:
                logger.info(f"🚫 Skipping {extractor_name} after {failure_count} {error_type} failures")
                return True

        # Skip extractors with timeout issues
        elif error_type in ["TimeoutException", "TimeoutError"]:
            if failure_count >= 2:
                logger.info(f"🚫 Skipping {extractor_name} after {failure_count} timeout failures")
                return True

        return False

    @staticmethod
    def get_recovery_delay(attempt_number: int, error_type: str) -> float:
        """
        Calculate adaptive recovery delay based on attempt number and error type.

        Args:
            attempt_number: Current attempt number
            error_type: Type of error encountered

        Returns:
            Delay in seconds before next attempt
        """
        base_delays = {
            "NoSuchElementException": 0.5,  # Fast retry for element issues
            "TimeoutException": 2.0,  # Longer delay for timeouts
            "TimeoutError": 2.0,
            "WebDriverException": 1.0,  # Medium delay for driver issues
            "SessionNotCreatedException": 5.0,  # Long delay for session issues
        }

        base_delay = base_delays.get(error_type, 1.0)

        # Exponential backoff with jitter
        import random

        delay = base_delay * (1.5**attempt_number)
        jitter = delay * 0.1 * random.random()  # Add up to 10% jitter

        final_delay = min(delay + jitter, 10.0)  # Cap at 10 seconds

        logger.debug(f"🔄 Recovery delay for {error_type} (attempt {attempt_number}): {final_delay:.2f}s")
        return final_delay

    @staticmethod
    def should_fallback_to_simpler_method(failure_count: int, error_pattern: str) -> bool:
        """
        Determine if extraction should fallback to simpler methods.

        Args:
            failure_count: Number of consecutive failures
            error_pattern: Pattern of errors observed

        Returns:
            True if should fallback to simpler extraction methods
        """
        # Fallback patterns
        if failure_count >= 5 and "NoSuchElementException" in error_pattern:
            logger.info("🔄 Too many element detection failures - suggesting fallback to HTML parsing")
            return True

        if failure_count >= 3 and "TimeoutException" in error_pattern:
            logger.info("🔄 Too many timeout failures - suggesting fallback to static content extraction")
            return True

        return False

    @staticmethod
    def analyze_failure_pattern(errors: list) -> dict:
        """
        Analyze pattern of failures to suggest recovery strategies.

        Args:
            errors: List of recent error messages

        Returns:
            Dictionary with failure analysis and recommendations
        """
        from collections import Counter

        # Count error types
        error_types = [error.split(":")[0] if ":" in error else error for error in errors]
        error_counts = Counter(error_types)

        # Analyze patterns
        analysis = {
            "total_errors": len(errors),
            "error_types": dict(error_counts),
            "dominant_error": error_counts.most_common(1)[0] if error_counts else None,
            "recommendations": [],
        }

        # Generate recommendations based on patterns
        if error_counts.get("NoSuchElementException", 0) > 5:
            analysis["recommendations"].append("Consider simpler CSS selectors or XPath alternatives")
            analysis["recommendations"].append("Check if page uses dynamic content loading")

        if error_counts.get("TimeoutException", 0) > 3:
            analysis["recommendations"].append("Increase timeout values or check network connectivity")
            analysis["recommendations"].append("Consider if page requires user interaction to load content")

        if error_counts.get("SessionNotCreatedException", 0) > 0:
            analysis["recommendations"].append("Check WebDriver installation and browser compatibility")
            analysis["recommendations"].append("Consider using different browser or clearing browser cache")

        return analysis
