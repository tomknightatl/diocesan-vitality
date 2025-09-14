#!/usr/bin/env python3
"""
Dynamic Content Engine - Advanced JavaScript Execution and Network Traffic Analysis.

This module provides sophisticated capabilities to handle dynamic diocese websites:
1. JavaScript execution engine with DOM monitoring
2. Network traffic interception and API discovery
3. Content polling and lazy loading triggers
4. AJAX/API endpoint extraction
"""

import json
import time
import re
from typing import List, Dict, Optional, Any, Set
from urllib.parse import urljoin, urlparse
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException

from core.logger import get_logger
from core.circuit_breaker import circuit_breaker

logger = get_logger(__name__)


class NetworkTrafficAnalyzer:
    """Analyzes network traffic to discover API endpoints and data sources."""

    def __init__(self, driver: WebDriver):
        """Initialize the network traffic analyzer."""
        self.driver = driver
        self.captured_requests = []
        self.api_endpoints = set()
        self.parish_data_urls = set()

    def enable_logging(self):
        """Enable browser logging to capture network requests."""
        try:
            # Enable performance logging
            caps = self.driver.capabilities
            if 'goog:loggingPrefs' not in caps:
                logger.info("🌐 Performance logging not available, using JS injection method")
                return self._inject_xhr_monitor()

            # Get performance logs
            logs = self.driver.get_log('performance')
            for log in logs:
                self._process_performance_log(log)

            logger.info(f"🌐 Captured {len(self.captured_requests)} network requests")
            return True

        except Exception as e:
            logger.warning(f"🌐 Network logging failed, falling back to JS monitoring: {e}")
            return self._inject_xhr_monitor()

    def _inject_xhr_monitor(self):
        """Inject JavaScript to monitor XHR/fetch requests."""
        monitor_script = """
        window.capturedRequests = [];

        // Monitor XMLHttpRequest
        const originalXHROpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
            this._method = method;
            this._url = url;
            return originalXHROpen.apply(this, arguments);
        };

        const originalXHRSend = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.send = function(data) {
            this.addEventListener('readystatechange', function() {
                if (this.readyState === 4) {
                    window.capturedRequests.push({
                        method: this._method,
                        url: this._url,
                        status: this.status,
                        response: this.responseText.substring(0, 1000),
                        timestamp: Date.now()
                    });
                }
            });
            return originalXHRSend.apply(this, arguments);
        };

        // Monitor fetch API
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            const method = options.method || 'GET';
            return originalFetch.apply(this, arguments).then(response => {
                response.clone().text().then(text => {
                    window.capturedRequests.push({
                        method: method,
                        url: url,
                        status: response.status,
                        response: text.substring(0, 1000),
                        timestamp: Date.now()
                    });
                });
                return response;
            });
        };

        return true;
        """

        try:
            self.driver.execute_script(monitor_script)
            logger.info("🌐 XHR/Fetch monitoring injected successfully")
            return True
        except Exception as e:
            logger.error(f"🌐 Failed to inject XHR monitor: {e}")
            return False

    def collect_requests(self, wait_time: int = 5) -> List[Dict]:
        """Collect captured network requests."""
        try:
            # Wait for requests to be captured
            time.sleep(wait_time)

            # Get captured requests from JavaScript
            requests = self.driver.execute_script("return window.capturedRequests || [];")
            self.captured_requests.extend(requests)

            logger.info(f"🌐 Collected {len(requests)} new network requests")
            return requests

        except Exception as e:
            logger.error(f"🌐 Failed to collect requests: {e}")
            return []

    def analyze_parish_endpoints(self) -> Set[str]:
        """Analyze requests to identify potential parish data endpoints."""
        parish_keywords = ['parish', 'church', 'location', 'directory', 'api', 'data']

        for request in self.captured_requests:
            url = request.get('url', '')
            response = request.get('response', '')

            # Check URL for parish-related keywords
            if any(keyword in url.lower() for keyword in parish_keywords):
                self.api_endpoints.add(url)

            # Check response content for parish data
            if self._contains_parish_data(response):
                self.parish_data_urls.add(url)

        logger.info(f"🌐 Found {len(self.api_endpoints)} potential API endpoints")
        logger.info(f"🌐 Found {len(self.parish_data_urls)} parish data URLs")

        return self.parish_data_urls

    def _contains_parish_data(self, response: str) -> bool:
        """Check if response contains parish-like data."""
        if not response or len(response) < 50:
            return False

        parish_indicators = [
            'parish', 'church', 'cathedral', 'saint', 'st.', 'holy',
            'address', 'phone', 'mass', 'schedule', 'pastor'
        ]

        # Look for JSON-like structures with parish data
        try:
            if response.startswith('{') or response.startswith('['):
                # Likely JSON response
                response_lower = response.lower()
                match_count = sum(1 for indicator in parish_indicators
                                if indicator in response_lower)
                return match_count >= 3
        except:
            pass

        return False

    def _process_performance_log(self, log_entry: Dict):
        """Process a performance log entry."""
        message = json.loads(log_entry['message'])
        if message['message']['method'] in ['Network.responseReceived', 'Network.requestWillBeSent']:
            self.captured_requests.append(message['message'])


class JavaScriptExecutionEngine:
    """Advanced JavaScript execution engine for dynamic content handling."""

    def __init__(self, driver: WebDriver):
        """Initialize the JavaScript execution engine."""
        self.driver = driver
        self.network_analyzer = NetworkTrafficAnalyzer(driver)

    @circuit_breaker('javascript_execution')
    def wait_for_dynamic_content(self, diocese_name: str, timeout: int = 20) -> Dict[str, Any]:
        """
        Advanced waiting strategy for JavaScript-heavy diocese sites.

        Returns:
            - content_loaded: Whether dynamic content was successfully loaded
            - method_used: Which method successfully loaded the content
            - parish_elements: Any parish elements found after loading
            - api_endpoints: Discovered API endpoints
        """
        result = {
            'content_loaded': False,
            'method_used': None,
            'parish_elements': [],
            'api_endpoints': set(),
            'loading_time': 0
        }

        start_time = time.time()
        logger.info(f"🚀 Starting dynamic content loading for {diocese_name}")

        try:
            # Step 1: Enable network monitoring
            self.network_analyzer.enable_logging()

            # Step 2: Try multiple loading strategies
            strategies = [
                self._wait_for_content_change,
                self._trigger_scroll_loading,
                self._simulate_user_interaction,
                self._wait_for_ajax_completion,
                self._poll_for_content_appearance
            ]

            for i, strategy in enumerate(strategies, 1):
                logger.info(f"🔄 Trying loading strategy {i}: {strategy.__name__}")

                try:
                    if strategy(timeout // len(strategies)):
                        result['content_loaded'] = True
                        result['method_used'] = strategy.__name__
                        logger.info(f"✅ Content loaded using {strategy.__name__}")
                        break
                except Exception as e:
                    logger.debug(f"⚠️ Strategy {strategy.__name__} failed: {e}")
                    continue

            # Step 3: Collect network requests
            requests = self.network_analyzer.collect_requests(3)
            result['api_endpoints'] = self.network_analyzer.analyze_parish_endpoints()

            # Step 4: Extract any parish elements found
            result['parish_elements'] = self._extract_loaded_parish_elements()

            result['loading_time'] = time.time() - start_time
            logger.info(f"🎯 Dynamic content loading completed in {result['loading_time']:.2f}s")

            return result

        except Exception as e:
            logger.error(f"🚀 Dynamic content loading failed: {e}")
            result['loading_time'] = time.time() - start_time
            return result

    def _wait_for_content_change(self, timeout: int = 10) -> bool:
        """Wait for significant content changes in the DOM."""
        try:
            initial_content = self.driver.find_element(By.TAG_NAME, 'body').text
            initial_length = len(initial_content)

            wait = WebDriverWait(self.driver, timeout)

            def content_has_changed(driver):
                current_content = driver.find_element(By.TAG_NAME, 'body').text
                current_length = len(current_content)
                # Content should increase by at least 50%
                return current_length > initial_length * 1.5

            wait.until(content_has_changed)
            logger.info("✅ Content change detected")
            return True

        except TimeoutException:
            logger.debug("⚠️ No significant content change detected")
            return False

    def _trigger_scroll_loading(self, timeout: int = 10) -> bool:
        """Trigger lazy loading by scrolling through the page."""
        try:
            initial_elements = len(self.driver.find_elements(By.CSS_SELECTOR, 'a, div, article'))

            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Scroll to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            # Scroll incrementally
            for i in range(5):
                scroll_position = (i + 1) * 20  # 20%, 40%, 60%, 80%, 100%
                script = f"window.scrollTo(0, document.body.scrollHeight * {scroll_position / 100});"
                self.driver.execute_script(script)
                time.sleep(1)

            # Check if new elements appeared
            final_elements = len(self.driver.find_elements(By.CSS_SELECTOR, 'a, div, article'))

            if final_elements > initial_elements * 1.2:
                logger.info(f"✅ Scroll loading triggered new content ({final_elements - initial_elements} new elements)")
                return True

            return False

        except Exception as e:
            logger.debug(f"⚠️ Scroll loading failed: {e}")
            return False

    def _simulate_user_interaction(self, timeout: int = 10) -> bool:
        """Simulate user interactions that might trigger content loading."""
        try:
            actions = ActionChains(self.driver)

            # Look for common interactive elements
            selectors = [
                'button[onclick]', '.load-more', '.show-all', '#load-parishes',
                '[data-load]', '.expand', '.toggle', 'input[type="search"]'
            ]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements[:3]:  # Try first 3 elements
                        if element.is_displayed() and element.is_enabled():
                            logger.info(f"🖱️ Clicking interactive element: {selector}")
                            actions.click(element).perform()
                            time.sleep(2)  # Wait for potential AJAX

                            # Check if content changed
                            if self._has_new_parish_content():
                                logger.info("✅ User interaction triggered new content")
                                return True

                except Exception as e:
                    logger.debug(f"⚠️ Failed to interact with {selector}: {e}")
                    continue

            return False

        except Exception as e:
            logger.debug(f"⚠️ User interaction simulation failed: {e}")
            return False

    def _wait_for_ajax_completion(self, timeout: int = 10) -> bool:
        """Wait for AJAX requests to complete."""
        try:
            # Wait for jQuery if available
            jquery_script = """
            return (typeof jQuery !== 'undefined') ? jQuery.active === 0 : true;
            """

            wait = WebDriverWait(self.driver, timeout)
            wait.until(lambda driver: driver.execute_script(jquery_script))

            # Also wait for any pending fetch/XHR requests
            xhr_script = """
            return (typeof window.capturedRequests !== 'undefined') &&
                   window.capturedRequests.length > 0;
            """

            # Give AJAX time to complete
            time.sleep(3)

            has_requests = self.driver.execute_script(xhr_script)
            if has_requests:
                logger.info("✅ AJAX requests detected and completed")
                return True

            return False

        except Exception as e:
            logger.debug(f"⚠️ AJAX waiting failed: {e}")
            return False

    def _poll_for_content_appearance(self, timeout: int = 15) -> bool:
        """Poll for specific parish-related content to appear."""
        try:
            parish_selectors = [
                '[class*="parish"]', '[id*="parish"]',
                '[class*="church"]', '[id*="church"]',
                '.directory a', '.location-list a',
                'article a', '.entry-title a'
            ]

            end_time = time.time() + timeout

            while time.time() < end_time:
                for selector in parish_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) > 0:
                        # Verify elements contain parish-like content
                        valid_elements = []
                        for elem in elements[:10]:  # Check first 10
                            text = elem.text.strip().lower()
                            if any(keyword in text for keyword in ['parish', 'church', 'saint', 'st.', 'holy']):
                                valid_elements.append(elem)

                        if len(valid_elements) >= 2:
                            logger.info(f"✅ Parish content appeared: {len(valid_elements)} elements via {selector}")
                            return True

                time.sleep(1)  # Poll every second

            return False

        except Exception as e:
            logger.debug(f"⚠️ Content polling failed: {e}")
            return False

    def _has_new_parish_content(self) -> bool:
        """Quick check if new parish content has appeared."""
        try:
            parish_keywords = ['parish', 'church', 'saint', 'cathedral', 'holy']
            body_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()

            keyword_count = sum(body_text.count(keyword) for keyword in parish_keywords)
            return keyword_count > 5  # Arbitrary threshold

        except Exception as e:
            logger.debug(f"⚠️ Parish content check failed: {e}")
            return False

    def _extract_loaded_parish_elements(self) -> List[Dict[str, str]]:
        """Extract parish elements that were loaded dynamically."""
        parish_elements = []

        try:
            # Look for links with parish-related content
            selectors = [
                'a[href*="parish"]', 'a[href*="church"]',
                '.parish a', '.church a', '.location a',
                'article a', '.entry-title a', '.directory a'
            ]

            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    try:
                        text = elem.text.strip()
                        href = elem.get_attribute('href')

                        if text and href and self._is_parish_like(text):
                            parish_elements.append({
                                'name': text,
                                'url': href,
                                'selector': selector
                            })
                    except:
                        continue

            # Remove duplicates
            seen = set()
            unique_elements = []
            for elem in parish_elements:
                key = (elem['name'].lower(), elem['url'])
                if key not in seen:
                    seen.add(key)
                    unique_elements.append(elem)

            logger.info(f"🔍 Extracted {len(unique_elements)} parish elements from dynamic content")
            return unique_elements

        except Exception as e:
            logger.error(f"🔍 Failed to extract parish elements: {e}")
            return []

    def _is_parish_like(self, text: str) -> bool:
        """Check if text looks like a parish name."""
        text_lower = text.lower()
        parish_indicators = ['parish', 'church', 'cathedral', 'saint', 'st.', 'holy', 'blessed', 'our lady']
        exclusions = ['home', 'about', 'contact', 'news', 'events', 'calendar', 'office', 'staff']

        has_indicator = any(indicator in text_lower for indicator in parish_indicators)
        has_exclusion = any(exclusion in text_lower for exclusion in exclusions)

        return has_indicator and not has_exclusion and len(text.strip()) > 3


def get_dynamic_content_engine(driver: WebDriver) -> JavaScriptExecutionEngine:
    """Factory function to create JavaScript execution engine."""
    return JavaScriptExecutionEngine(driver)