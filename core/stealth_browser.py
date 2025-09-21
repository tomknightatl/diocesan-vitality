#!/usr/bin/env python3
"""
Stealth Browser Module for Advanced Bot Detection Countermeasures

This module provides browser automation with stealth capabilities to bypass
advanced bot detection systems that block traditional HTTP requests.
"""

import logging
import random
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logger = logging.getLogger(__name__)


class StealthBrowser:
    """Browser automation with stealth capabilities for bot detection bypass."""

    def __init__(self):
        """Initialize stealth browser."""
        self.driver = None
        self.is_available = SELENIUM_AVAILABLE

        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium not available. Stealth browser functionality disabled.")
            return

        self._setup_driver()

    def _setup_driver(self):
        """Setup Chrome driver with stealth configuration."""
        if not SELENIUM_AVAILABLE:
            return

        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")  # Faster loading
            options.add_argument("--disable-javascript")  # Prevent detection scripts

            # Random user agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            ]
            options.add_argument(f"--user-agent={random.choice(user_agents)}")

            # Window size randomization
            window_sizes = [(1920, 1080), (1366, 768), (1440, 900), (1536, 864)]
            width, height = random.choice(window_sizes)
            options.add_argument(f"--window-size={width},{height}")

            # Experimental options to avoid detection
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            self.driver = webdriver.Chrome(options=options)

            # Execute script to hide webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Set timeouts
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)

            logger.info("Stealth browser initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize stealth browser: {e}")
            self.is_available = False

    def get_page_content(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        Get page content using stealth browser.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Page HTML content or None if failed
        """
        if not self.is_available or not self.driver:
            logger.warning("Stealth browser not available")
            return None

        try:
            # Random delay to mimic human behavior
            time.sleep(random.uniform(0.5, 2.0))

            logger.info(f"Fetching with stealth browser: {url}")
            self.driver.get(url)

            # Wait for page to load
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Random scroll to mimic human behavior
            if random.random() < 0.3:  # 30% chance
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(random.uniform(0.5, 1.5))

            return self.driver.page_source

        except TimeoutException:
            logger.warning(f"Timeout loading page: {url}")
            return None
        except WebDriverException as e:
            logger.error(f"Browser error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    def get_navigation_links(self, url: str) -> list:
        """
        Extract navigation links from a page using stealth browser.

        Args:
            url: URL to analyze

        Returns:
            List of discovered URLs
        """
        if not self.is_available or not self.driver:
            return []

        content = self.get_page_content(url)
        if not content:
            return []

        try:
            # Find navigation links
            links = self.driver.find_elements(By.CSS_SELECTOR, "nav a, .nav a, .navigation a, .menu a")

            discovered_urls = []
            base_domain = urlparse(url).netloc

            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href and base_domain in href:
                        discovered_urls.append(href)
                except:
                    continue

            return list(set(discovered_urls))

        except Exception as e:
            logger.error(f"Error extracting navigation links from {url}: {e}")
            return []

    def close(self):
        """Close the browser and cleanup resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Stealth browser closed")
            except Exception as e:
                logger.error(f"Error closing stealth browser: {e}")
            finally:
                self.driver = None


# Global stealth browser instance for reuse
_stealth_browser = None


def get_stealth_browser() -> StealthBrowser:
    """Get global stealth browser instance."""
    global _stealth_browser
    if _stealth_browser is None:
        _stealth_browser = StealthBrowser()
    return _stealth_browser


def cleanup_stealth_browser():
    """Cleanup global stealth browser instance."""
    global _stealth_browser
    if _stealth_browser:
        _stealth_browser.close()
        _stealth_browser = None


# Context manager for automatic cleanup
class StealthBrowserContext:
    """Context manager for stealth browser with automatic cleanup."""

    def __enter__(self) -> StealthBrowser:
        return get_stealth_browser()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't cleanup here, let global instance persist
        pass
