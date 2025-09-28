#!/usr/bin/env python3
"""
Enhanced base extractor with optimized circuit breaker usage and smart error recovery.
Demonstrates best practices for using the new optimization features.
"""

import time
from typing import Any, Dict, List, Optional

from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

from core.enhanced_element_wait import (
    create_map_interaction_selectors,
    create_parish_extraction_selectors,
    create_search_form_selectors,
)
from core.logger import get_logger
from core.optimized_circuit_breaker_configs import ErrorRecoveryStrategies, OptimizedCircuitBreakerConfigs
from core.parish_validation import filter_valid_parishes

logger = get_logger(__name__)


class EnhancedBaseExtractor:
    """
    Base extractor class demonstrating optimized circuit breaker usage and error recovery.
    Provides template for extractors that need to handle complex diocese websites.
    """

    def __init__(self, name: str = "EnhancedBaseExtractor"):
        self.name = name
        self.failure_count = 0
        self.error_history = []
        self.last_successful_selectors = {}

    def extract_parishes_with_recovery(self, driver, url: str, operation_type: str = "element") -> List[Dict[str, Any]]:
        """
        Extract parishes with intelligent error recovery and optimized circuit breaker usage.

        Args:
            driver: ProtectedWebDriver instance
            url: URL to extract from
            operation_type: Type of operation for circuit breaker optimization

        Returns:
            List of parish dictionaries
        """
        parishes = []
        start_time = time.time()

        try:
            logger.info(f"🔍 {self.name}: Starting extraction from {url}")

            # Step 1: Load page with optimized waiting
            self._load_page_with_recovery(driver, url)

            # Step 2: Wait for page stability (important for AJAX sites)
            if not driver.wait_for_page_stable(stability_timeout=2.0, max_wait=8.0):
                logger.warning(f"⚠️ Page may not be fully stable, proceeding anyway")

            # Step 3: Attempt extraction with progressive selector complexity
            parishes = self._extract_with_progressive_selectors(driver, operation_type)

            # Step 4: Apply parish validation to filter out diocesan departments
            parishes = self._apply_parish_validation(parishes)

            # Step 5: Validate and clean results
            parishes = self._validate_and_clean_results(parishes)

            extraction_time = time.time() - start_time
            logger.info(f"✅ {self.name}: Extracted {len(parishes)} parishes in {extraction_time:.2f}s")

        except Exception as e:
            self._handle_extraction_error(e, url)
            extraction_time = time.time() - start_time
            logger.error(f"❌ {self.name}: Extraction failed after {extraction_time:.2f}s: {str(e)}")

        return parishes

    def _load_page_with_recovery(self, driver, url: str):
        """Load page with intelligent retry and fallback strategies."""
        for attempt in range(3):
            try:
                # Use optimized page loading
                driver.get(url, timeout=45)
                logger.debug(f"✅ Page loaded successfully on attempt {attempt + 1}")
                return

            except TimeoutException as e:
                delay = ErrorRecoveryStrategies.get_recovery_delay(attempt, "TimeoutException")
                logger.warning(f"⏰ Page load timeout (attempt {attempt + 1}/3), retrying in {delay:.1f}s")

                if attempt < 2:  # Don't sleep on last attempt
                    time.sleep(delay)
                else:
                    raise

            except Exception as e:
                delay = ErrorRecoveryStrategies.get_recovery_delay(attempt, type(e).__name__)
                logger.warning(f"❌ Page load error (attempt {attempt + 1}/3): {str(e)[:100]}...")

                if attempt < 2:
                    time.sleep(delay)
                else:
                    raise

    def _extract_with_progressive_selectors(self, driver, operation_type: str) -> List[Dict[str, Any]]:
        """Extract using progressive selector complexity with smart recovery."""
        parishes = []

        # Get appropriate selectors based on operation type
        if operation_type == "map":
            selectors = create_map_interaction_selectors()
            logger.debug("🗺️ Using map interaction selectors")
        elif operation_type == "search":
            selectors = create_search_form_selectors()
            logger.debug("🔍 Using search form selectors")
        else:
            selectors = create_parish_extraction_selectors()
            logger.debug("⛪ Using parish extraction selectors")

        # Try extraction with progressive complexity
        for selector_group in self._group_selectors_by_complexity(selectors):
            try:
                elements = driver.smart_find_elements(selector_group, timeout=10.0, min_count=1)

                if elements:
                    logger.debug(f"✅ Found {len(elements)} elements with selector group")
                    parishes = self._process_elements(elements, driver)

                    if parishes:
                        # Remember successful selectors for future use
                        self.last_successful_selectors[operation_type] = selector_group[0]
                        break

            except Exception as e:
                error_type = type(e).__name__
                logger.debug(f"❌ Selector group failed: {error_type}")

                # Check if we should skip this extraction method
                if ErrorRecoveryStrategies.should_skip_extractor(self.name, self.failure_count, error_type):
                    logger.info(f"🚫 Skipping {self.name} due to repeated {error_type} failures")
                    break

                continue

        return parishes

    def _group_selectors_by_complexity(self, selectors: List[str]) -> List[List[str]]:
        """Group selectors by complexity for progressive extraction."""
        # Simple selectors (class-based, high probability)
        simple = [s for s in selectors if s.startswith(".") and len(s.split()) == 1]

        # Medium selectors (id-based, multi-class, attribute-based)
        medium = [
            s
            for s in selectors
            if (s.startswith("#") or ("[" in s and "]" in s) or (s.startswith(".") and len(s.split()) > 1))
        ]

        # Complex selectors (descendant, multiple conditions)
        complex_selectors = [s for s in selectors if s not in simple and s not in medium]

        # Return in order of increasing complexity
        groups = []
        if simple:
            groups.append(simple[:5])  # Top 5 simple selectors
        if medium:
            groups.append(medium[:5])  # Top 5 medium selectors
        if complex_selectors:
            groups.append(complex_selectors[:3])  # Top 3 complex selectors

        return groups

    def _process_elements(self, elements: List[Any], driver) -> List[Dict[str, Any]]:
        """Process found elements into parish data structures."""
        parishes = []

        for i, element in enumerate(elements[:50]):  # Limit processing to 50 elements
            try:
                parish_data = self._extract_parish_from_element(element, driver)
                if parish_data:
                    parishes.append(parish_data)

            except Exception as e:
                logger.debug(f"❌ Error processing element {i + 1}: {str(e)[:50]}...")
                continue

        return parishes

    def _extract_parish_from_element(self, element: Any, driver) -> Optional[Dict[str, Any]]:
        """Extract parish information from a single element."""
        try:
            # Basic extraction - override in specific extractors
            name = element.text.strip() if element.text else "Unknown Parish"
            href = element.get_attribute("href") if element.tag_name == "a" else None

            if name and len(name) > 3:  # Basic validation
                return {"name": name, "url": href, "extraction_method": self.name, "element_tag": element.tag_name}

        except Exception as e:
            logger.debug(f"❌ Error extracting from element: {str(e)}")
            return None

        return None

    def _apply_parish_validation(self, parishes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply parish validation to filter out diocesan departments."""
        if not parishes:
            return parishes

        logger.debug(f"🔍 Applying parish validation to {len(parishes)} extracted entities")

        try:
            # Apply validation filter
            validated_parishes = filter_valid_parishes(parishes)

            logger.info(
                f"✅ Parish validation: {len(validated_parishes)}/{len(parishes)} entities validated as actual parishes"
            )

            return validated_parishes

        except Exception as e:
            logger.warning(f"❌ Parish validation failed: {str(e)}. Proceeding with unfiltered results.")
            return parishes

    def _validate_and_clean_results(self, parishes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean parish results."""
        valid_parishes = []

        for parish in parishes:
            # Basic validation
            if (
                parish.get("name")
                and len(parish["name"].strip()) > 3
                and not parish["name"].strip().lower() in ["home", "contact", "about"]
            ):

                # Clean data
                parish["name"] = parish["name"].strip()
                if parish.get("url"):
                    parish["url"] = parish["url"].strip()

                valid_parishes.append(parish)

        return valid_parishes

    def _handle_extraction_error(self, error: Exception, url: str):
        """Handle extraction errors with intelligent recovery strategies."""
        self.failure_count += 1
        error_type = type(error).__name__
        error_msg = str(error)[:200]

        # Track error history for pattern analysis
        self.error_history.append({"type": error_type, "message": error_msg, "timestamp": time.time(), "url": url})

        # Keep only recent errors (last 20)
        if len(self.error_history) > 20:
            self.error_history = self.error_history[-20:]

        # Analyze failure patterns if we have enough data
        if len(self.error_history) >= 5:
            analysis = ErrorRecoveryStrategies.analyze_failure_pattern([e["message"] for e in self.error_history[-5:]])

            if analysis["recommendations"]:
                logger.info(f"📊 Failure pattern analysis for {self.name}:")
                for rec in analysis["recommendations"]:
                    logger.info(f"   • {rec}")

    def get_extractor_stats(self) -> Dict[str, Any]:
        """Get statistics about this extractor's performance."""
        recent_errors = [e for e in self.error_history if time.time() - e["timestamp"] < 3600]

        return {
            "name": self.name,
            "total_failures": self.failure_count,
            "recent_failures": len(recent_errors),
            "successful_selectors": dict(self.last_successful_selectors),
            "dominant_error": (
                max(
                    {e["type"] for e in recent_errors},
                    key=lambda x: sum(1 for e in recent_errors if e["type"] == x),
                    default="None",
                )
                if recent_errors
                else "None"
            ),
        }
