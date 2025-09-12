from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from core.logger import get_logger
from core.circuit_breaker import circuit_breaker, CircuitBreakerConfig, circuit_manager
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from selenium.common.exceptions import WebDriverException, SessionNotCreatedException, TimeoutException
import time

logger = get_logger(__name__)
driver = None

# Define retryable exceptions for WebDriver setup
RETRYABLE_WEBDRIVER_EXCEPTIONS = (WebDriverException, SessionNotCreatedException)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RETRYABLE_WEBDRIVER_EXCEPTIONS),
    reraise=False, # Do not re-raise after retries, let the function return None
)
def _setup_driver_with_retry():
    """Internal helper to set up WebDriver with retry logic."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("--allow-insecure-localhost")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--unsafely-treat-insecure-origin-as-secure")
    chrome_options.add_argument("--cipher-suite-blacklist=TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )

def setup_driver():
    """Initializes and returns the Selenium WebDriver instance."""
    global driver
    if driver is None:
        logger.info("Setting up Chrome WebDriver...")
        try:
            driver = _setup_driver_with_retry()
            if driver:
                logger.info("WebDriver setup successfully.")
            else:
                logger.info("Failed to setup WebDriver after multiple retries.")
        except Exception as e: # Catch any remaining exceptions not covered by retry
            logger.info(f"Error setting up WebDriver: {e}")
            driver = None
    return driver

def close_driver():
    """Closes the Selenium WebDriver instance if it's active."""
    global driver
    if driver:
        logger.info("Closing WebDriver...")
        driver.quit()
        driver = None
        logger.info("WebDriver closed.")
        
        # Log circuit breaker summary on close
        circuit_manager.log_summary()


class ProtectedWebDriver:
    """
    WebDriver wrapper with circuit breaker protection and timeout handling.
    Provides robust protection against hanging requests and service failures.
    """
    
    def __init__(self, driver, default_timeout=30):
        self.driver = driver
        self.default_timeout = default_timeout
        
        # Configure circuit breakers for different operations
        self.page_load_cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            request_timeout=45,
            max_retries=2,
            retry_delay=2.0
        )
        
        self.element_cb_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=15,
            request_timeout=15,
            max_retries=1,
            retry_delay=1.0
        )
        
        logger.info(f"🛡️ Protected WebDriver initialized with default timeout: {default_timeout}s")
    
    @circuit_breaker('webdriver_page_load')
    def get(self, url, timeout=None):
        """Load a web page with circuit breaker protection"""
        timeout = timeout or self.default_timeout
        logger.debug(f"🌐 Loading page: {url} (timeout: {timeout}s)")
        
        # Set page load timeout
        self.driver.set_page_load_timeout(timeout)
        
        start_time = time.time()
        try:
            self.driver.get(url)
            load_time = time.time() - start_time
            logger.debug(f"✅ Page loaded in {load_time:.2f}s")
            return True
        except TimeoutException as e:
            load_time = time.time() - start_time
            logger.warning(f"⏰ Page load timeout after {load_time:.2f}s for {url}")
            raise TimeoutError(f"Page load timeout after {timeout}s") from e
        except WebDriverException as e:
            load_time = time.time() - start_time
            logger.error(f"❌ WebDriver error after {load_time:.2f}s for {url}: {str(e)}")
            raise
    
    @circuit_breaker('webdriver_element_interaction')
    def find_element(self, *args, **kwargs):
        """Find element with circuit breaker protection"""
        try:
            return self.driver.find_element(*args, **kwargs)
        except Exception as e:
            logger.debug(f"🔍 Element not found: {str(e)}")
            raise
    
    @circuit_breaker('webdriver_element_interaction')
    def find_elements(self, *args, **kwargs):
        """Find elements with circuit breaker protection"""
        try:
            return self.driver.find_elements(*args, **kwargs)
        except Exception as e:
            logger.debug(f"🔍 Elements not found: {str(e)}")
            raise
    
    @circuit_breaker('webdriver_javascript')
    def execute_script(self, script, *args, timeout=None):
        """Execute JavaScript with circuit breaker protection"""
        timeout = timeout or 15
        logger.debug(f"⚡ Executing JavaScript (timeout: {timeout}s)")
        
        # Set script timeout
        self.driver.set_script_timeout(timeout)
        
        try:
            return self.driver.execute_script(script, *args)
        except TimeoutException as e:
            logger.warning(f"⏰ JavaScript timeout after {timeout}s")
            raise TimeoutError(f"JavaScript execution timeout after {timeout}s") from e
        except Exception as e:
            logger.error(f"❌ JavaScript error: {str(e)}")
            raise
    
    def __getattr__(self, name):
        """Delegate other attributes to the underlying driver"""
        return getattr(self.driver, name)


def get_protected_driver(timeout=30):
    """Get a protected WebDriver instance with circuit breaker protection"""
    raw_driver = setup_driver()
    if raw_driver:
        return ProtectedWebDriver(raw_driver, timeout)
    return None
