#!/usr/bin/env python3
"""
Enhanced element waiting strategies with intelligent fallback and progressive timeout handling.
Provides smart element detection with multiple selector strategies and adaptive timing.
"""

import time
from typing import List, Optional, Tuple, Union, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from core.logger import get_logger

logger = get_logger(__name__)


class ElementWaitStrategy:
    """
    Enhanced element waiting with progressive timeout and multiple selector fallbacks.
    Reduces unnecessary circuit breaker triggers by being smarter about element detection.
    """

    def __init__(self, driver, base_timeout: float = 5.0):
        self.driver = driver
        self.base_timeout = base_timeout

    def smart_element_wait(
        self,
        selectors: List[str],
        timeout: float = None,
        condition: str = "presence",
        log_attempts: bool = True
    ) -> Optional[Any]:
        """
        Try multiple selectors with progressive timeouts and different conditions.

        Args:
            selectors: List of CSS selectors to try in order
            timeout: Max timeout per selector (defaults to base_timeout)
            condition: Type of wait condition ('presence', 'visible', 'clickable')
            log_attempts: Whether to log each attempt

        Returns:
            WebElement if found, None otherwise
        """
        timeout = timeout or self.base_timeout

        # Progressive timeout strategy: start short, increase for complex selectors
        timeout_progression = self._calculate_progressive_timeouts(selectors, timeout)

        for i, (selector, selector_timeout) in enumerate(zip(selectors, timeout_progression)):
            try:
                if log_attempts:
                    logger.debug(f"🔍 Attempting selector {i+1}/{len(selectors)}: '{selector}' (timeout: {selector_timeout}s)")

                element = self._wait_for_element(selector, selector_timeout, condition)
                if element:
                    if log_attempts:
                        logger.debug(f"✅ Found element with selector: '{selector}'")
                    return element

            except TimeoutException:
                if log_attempts:
                    logger.debug(f"⏰ Timeout for selector: '{selector}'")
                continue
            except (NoSuchElementException, WebDriverException) as e:
                if log_attempts:
                    logger.debug(f"❌ Error with selector '{selector}': {str(e)[:50]}...")
                continue

        if log_attempts:
            logger.debug(f"❌ No elements found with any of {len(selectors)} selectors")
        return None

    def _calculate_progressive_timeouts(self, selectors: List[str], max_timeout: float) -> List[float]:
        """
        Calculate progressive timeouts: shorter for simple selectors, longer for complex ones.
        """
        timeouts = []
        for i, selector in enumerate(selectors):
            # Base timeout increases with complexity and position
            complexity_factor = len(selector) / 50  # Longer selectors get more time
            position_factor = i / len(selectors)    # Later selectors get more time

            # Progressive timeout: 20% to 100% of max_timeout
            progress_timeout = max_timeout * (0.2 + 0.8 * position_factor + complexity_factor * 0.1)
            progress_timeout = min(progress_timeout, max_timeout)  # Cap at max_timeout
            progress_timeout = max(progress_timeout, 1.0)         # Minimum 1 second

            timeouts.append(round(progress_timeout, 1))

        return timeouts

    def _wait_for_element(self, selector: str, timeout: float, condition: str):
        """Wait for element with specified condition"""
        wait = WebDriverWait(self.driver, timeout)

        if condition == "presence":
            return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        elif condition == "visible":
            return wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
        elif condition == "clickable":
            return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        else:
            raise ValueError(f"Unknown condition: {condition}")

    def smart_elements_wait(
        self,
        selectors: List[str],
        timeout: float = None,
        min_count: int = 1,
        log_attempts: bool = True
    ) -> List[Any]:
        """
        Find multiple elements with smart waiting and fallback strategies.

        Args:
            selectors: List of CSS selectors to try
            timeout: Max timeout per selector
            min_count: Minimum number of elements required
            log_attempts: Whether to log attempts

        Returns:
            List of elements found
        """
        timeout = timeout or self.base_timeout
        timeout_progression = self._calculate_progressive_timeouts(selectors, timeout)

        for i, (selector, selector_timeout) in enumerate(zip(selectors, timeout_progression)):
            try:
                if log_attempts:
                    logger.debug(f"🔍 Searching for elements {i+1}/{len(selectors)}: '{selector}' (timeout: {selector_timeout}s)")

                # Wait for at least one element to be present
                WebDriverWait(self.driver, selector_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )

                # Get all matching elements
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                if len(elements) >= min_count:
                    if log_attempts:
                        logger.debug(f"✅ Found {len(elements)} elements with selector: '{selector}'")
                    return elements
                elif log_attempts:
                    logger.debug(f"⚠️ Found {len(elements)} elements, need at least {min_count}")

            except TimeoutException:
                if log_attempts:
                    logger.debug(f"⏰ No elements found for selector: '{selector}'")
                continue
            except (NoSuchElementException, WebDriverException) as e:
                if log_attempts:
                    logger.debug(f"❌ Error with selector '{selector}': {str(e)[:50]}...")
                continue

        if log_attempts:
            logger.debug(f"❌ No elements found with any of {len(selectors)} selectors")
        return []

    def wait_for_page_stable(self, stability_timeout: float = 2.0, max_wait: float = 10.0):
        """
        Wait for page to become stable (no new elements appearing).
        Useful for dynamic/AJAX content.
        """
        logger.debug(f"⏳ Waiting for page stability (max {max_wait}s)...")

        start_time = time.time()
        last_count = 0
        stable_start = None

        while time.time() - start_time < max_wait:
            try:
                # Count all elements on page as a stability metric
                current_count = len(self.driver.find_elements(By.CSS_SELECTOR, "*"))

                if current_count == last_count:
                    if stable_start is None:
                        stable_start = time.time()
                    elif time.time() - stable_start >= stability_timeout:
                        logger.debug("✅ Page appears stable")
                        return True
                else:
                    stable_start = None  # Reset stability timer
                    last_count = current_count

                time.sleep(0.5)  # Check every 500ms

            except WebDriverException:
                # Page might still be loading
                time.sleep(0.5)
                continue

        logger.debug("⚠️ Page stability timeout reached")
        return False

    def smart_form_wait(self, form_selectors: List[str], timeout: float = None) -> Optional[Tuple[Any, str]]:
        """
        Wait for forms with intelligent detection of form types.
        Returns the form element and the selector that found it.
        """
        timeout = timeout or self.base_timeout

        # Enhanced form selectors with priority
        enhanced_selectors = []
        for selector in form_selectors:
            enhanced_selectors.extend([
                selector,
                f"{selector} form",
                f"form {selector}",
                f"[action*='{selector.replace('.', '').replace('#', '')}']"
            ])

        # Remove duplicates while preserving order
        unique_selectors = []
        for selector in enhanced_selectors:
            if selector not in unique_selectors:
                unique_selectors.append(selector)

        form_element = self.smart_element_wait(unique_selectors, timeout, condition="presence")
        if form_element:
            # Return both element and the working selector for future reference
            for selector in unique_selectors:
                try:
                    if self.driver.find_element(By.CSS_SELECTOR, selector) == form_element:
                        return form_element, selector
                except:
                    continue

        return None, None


def create_parish_extraction_selectors() -> List[str]:
    """
    Create comprehensive list of parish extraction selectors ordered by success probability.
    Based on common diocese website patterns observed.
    """
    return [
        # High-probability selectors (specific parish patterns)
        ".parish-card", ".parish-item", ".parish-entry",
        ".church-card", ".church-item", ".church-entry",
        ".location-card", ".location-item",

        # Medium-probability selectors (general content patterns)
        "[class*='parish']", "[class*='church']", "[class*='location']",
        ".directory-item", ".listing-item", ".result-item",

        # Navigation and link patterns
        "a[href*='parish']", "a[href*='church']", "a[href*='location']",
        "li a[href*='/']", ".menu-item a", ".nav-item a",

        # Table and list patterns
        "table tr", "ul li", "ol li",
        ".row", ".item", ".entry",

        # Low-probability selectors (very general)
        "div[class]", "article", "section",
        "a[href]"  # Last resort
    ]


def create_map_interaction_selectors() -> List[str]:
    """Create selectors for interactive map elements with progressive complexity."""
    return [
        # Specific map selectors
        "#map", ".map", ".parish-map", ".church-map",
        "[id*='map']", "[class*='map']",

        # Google Maps patterns
        ".gm-style", ".google-map", "[id*='google-map']",

        # Interactive elements within maps
        ".marker", ".pin", ".point", ".location-marker",
        "[class*='marker']", "[class*='pin']",

        # Map containers and wrappers
        ".map-container", ".map-wrapper", ".interactive-map",
        "[data-map]", "[data-location]"
    ]


def create_search_form_selectors() -> List[str]:
    """Create selectors for search forms with progressive complexity."""
    return [
        # Specific search forms
        "#search-form", ".search-form", ".parish-search", ".church-search",
        "form[action*='search']", "form[action*='parish']",

        # Input-based detection
        "input[type='search']", "input[placeholder*='search']",
        "input[name*='search']", "input[id*='search']",

        # Submit buttons
        "button[type='submit']", "input[type='submit']",
        "button:contains('Search')", "input[value*='Search']",

        # General form patterns
        "form", ".form", "[role='search']"
    ]