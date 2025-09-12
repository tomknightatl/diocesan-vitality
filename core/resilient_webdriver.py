"""
Resilient WebDriver wrapper with enhanced circuit breaker integration, retry logic, and rate limiting.
Provides automatic recovery from WebDriver failures and connection issues.
"""

import time
import random
from typing import Optional, Callable, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException, TimeoutException, NoSuchElementException,
    ElementNotInteractableException, StaleElementReferenceException
)

from core.logger import get_logger
from core.circuit_breaker import circuit_breaker, CircuitBreakerConfig, CircuitBreakerOpenError

logger = get_logger(__name__)

class ResilientWebDriver:
    """
    Resilient WebDriver wrapper that handles failures gracefully and implements
    retry logic with exponential backoff and jitter.
    """
    
    def __init__(self, driver_factory: Callable = None, max_retries: int = 3, 
                 base_delay: float = 1.0, max_delay: float = 30.0):
        """
        Initialize resilient WebDriver wrapper.
        
        Args:
            driver_factory: Function that creates a new WebDriver instance
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
        """
        self.driver_factory = driver_factory
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._driver = None
        
        # Configure circuit breaker for WebDriver operations
        self.circuit_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=2,
            request_timeout=30,
            max_retries=max_retries,
            retry_delay=base_delay
        )
        
    @property
    def driver(self):
        """Get the current WebDriver instance, creating one if needed."""
        if self._driver is None:
            self._create_new_driver()
        return self._driver
    
    def _create_new_driver(self) -> bool:
        """Create a new WebDriver instance."""
        try:
            if self.driver_factory:
                self._driver = self.driver_factory()
                logger.info("✅ Created new WebDriver instance")
                return True
            else:
                logger.error("❌ No driver factory provided")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to create WebDriver: {e}")
            self._driver = None
            return False
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        # Add jitter (±20% of delay)
        jitter = delay * 0.2 * (random.random() * 2 - 1)
        return max(0.1, delay + jitter)
    
    def _is_recoverable_error(self, error: Exception) -> bool:
        """Check if an error is recoverable through retry."""
        recoverable_errors = (
            WebDriverException,
            TimeoutException,
            StaleElementReferenceException,
            ConnectionError,
            ConnectionRefusedError
        )
        return isinstance(error, recoverable_errors)
    
    def _recover_driver(self) -> bool:
        """Attempt to recover the WebDriver by creating a new instance."""
        logger.info("🔄 Attempting WebDriver recovery...")
        
        # Close existing driver if it exists
        if self._driver:
            try:
                self._driver.quit()
            except:
                pass
            self._driver = None
        
        # Create new driver
        return self._create_new_driver()
    
    def robust_execute(self, operation: Callable, *args, **kwargs) -> Any:
        """
        Execute a WebDriver operation with retry logic and error recovery.
        
        Args:
            operation: Function to execute (should take driver as first argument)
            *args, **kwargs: Arguments to pass to the operation
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: After all retry attempts are exhausted
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Use circuit breaker for the operation
                @circuit_breaker("webdriver_operation", self.circuit_config)
                def protected_operation():
                    return operation(self.driver, *args, **kwargs)
                
                result = protected_operation()
                
                # Success - reset any failure counters
                if attempt > 0:
                    logger.info(f"✅ Operation succeeded after {attempt} retries")
                
                return result
                
            except CircuitBreakerOpenError:
                # Circuit breaker is open - don't retry immediately
                logger.warning("🚫 Circuit breaker is open - operation blocked")
                raise
                
            except Exception as error:
                last_error = error
                
                # Check if this is the last attempt
                if attempt == self.max_retries:
                    logger.error(f"❌ Operation failed after {self.max_retries + 1} attempts: {error}")
                    break
                
                # Check if error is recoverable
                if not self._is_recoverable_error(error):
                    logger.error(f"❌ Non-recoverable error: {error}")
                    break
                
                logger.warning(f"⚠️ Attempt {attempt + 1} failed: {error}")
                
                # Attempt driver recovery if needed
                if "connection" in str(error).lower() or "session" in str(error).lower():
                    if not self._recover_driver():
                        logger.error("❌ Driver recovery failed")
                        break
                
                # Wait before retry with exponential backoff
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"⏳ Waiting {delay:.1f}s before retry {attempt + 2}")
                    time.sleep(delay)
        
        # All attempts failed
        raise last_error
    
    def get(self, url: str, timeout: int = 30) -> bool:
        """Navigate to URL with retry logic."""
        def _get_operation(driver, url, timeout):
            driver.set_page_load_timeout(timeout)
            driver.get(url)
            return True
        
        return self.robust_execute(_get_operation, url, timeout)
    
    def find_element(self, by: By, value: str, timeout: int = 10):
        """Find element with retry logic."""
        def _find_element_operation(driver, by, value, timeout):
            wait = WebDriverWait(driver, timeout)
            return wait.until(EC.presence_of_element_located((by, value)))
        
        return self.robust_execute(_find_element_operation, by, value, timeout)
    
    def find_elements(self, by: By, value: str, timeout: int = 10):
        """Find elements with retry logic."""
        def _find_elements_operation(driver, by, value, timeout):
            wait = WebDriverWait(driver, timeout)
            # Wait for at least one element to be present
            wait.until(EC.presence_of_element_located((by, value)))
            return driver.find_elements(by, value)
        
        return self.robust_execute(_find_elements_operation, by, value, timeout)
    
    def click_element(self, element):
        """Click element with retry logic."""
        def _click_operation(driver, element):
            wait = WebDriverWait(driver, 10)
            wait.until(EC.element_to_be_clickable(element))
            element.click()
            return True
        
        return self.robust_execute(_click_operation, element)
    
    def execute_script(self, script: str, *args):
        """Execute JavaScript with retry logic."""
        def _execute_script_operation(driver, script, *args):
            return driver.execute_script(script, *args)
        
        return self.robust_execute(_execute_script_operation, script, *args)
    
    def get_page_source(self) -> str:
        """Get page source with retry logic."""
        def _get_page_source_operation(driver):
            return driver.page_source
        
        return self.robust_execute(_get_page_source_operation)
    
    def get_current_url(self) -> str:
        """Get current URL with retry logic."""
        def _get_current_url_operation(driver):
            return driver.current_url
        
        return self.robust_execute(_get_current_url_operation)
    
    def wait_for_page_load(self, timeout: int = 30) -> bool:
        """Wait for page to fully load."""
        def _wait_for_load_operation(driver, timeout):
            wait = WebDriverWait(driver, timeout)
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            return True
        
        return self.robust_execute(_wait_for_load_operation, timeout)
    
    def quit(self):
        """Quit the WebDriver."""
        if self._driver:
            try:
                self._driver.quit()
                logger.info("✅ WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"⚠️ Error closing WebDriver: {e}")
            finally:
                self._driver = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.quit()


def create_resilient_webdriver(driver_factory: Callable, **kwargs) -> ResilientWebDriver:
    """
    Factory function to create a resilient WebDriver wrapper.
    
    Args:
        driver_factory: Function that creates a WebDriver instance
        **kwargs: Additional arguments for ResilientWebDriver
        
    Returns:
        ResilientWebDriver instance
    """
    return ResilientWebDriver(driver_factory, **kwargs)


# Rate limiting decorator for WebDriver operations
def rate_limited(calls_per_second: float = 1.0):
    """
    Decorator to rate limit function calls.
    
    Args:
        calls_per_second: Maximum calls allowed per second
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            last_called[0] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator