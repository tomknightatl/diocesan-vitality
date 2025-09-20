from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from core.logger import get_logger
from core.circuit_breaker import circuit_breaker, CircuitBreakerConfig, circuit_manager
from core.optimized_circuit_breaker_configs import OptimizedCircuitBreakerConfigs
from core.enhanced_element_wait import ElementWaitStrategy
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from selenium.common.exceptions import WebDriverException, SessionNotCreatedException, TimeoutException
import time
import subprocess
import shutil

logger = get_logger(__name__)
driver = None

def _find_chrome_binary():
    """Find the Chrome binary path dynamically based on what's available."""
    # List of possible Chrome binary locations in order of preference
    chrome_binaries = [
        '/usr/bin/google-chrome',       # Standard Google Chrome on Linux
        '/usr/bin/chromium-browser',    # Chromium on Raspberry Pi/ARM64
        '/usr/bin/chromium',            # Alternative Chromium path
        '/opt/google/chrome/chrome',    # Alternative Google Chrome path
        'google-chrome',                # System PATH fallback
        'chromium-browser',             # System PATH fallback
        'chromium'                      # System PATH fallback
    ]

    for binary_path in chrome_binaries:
        try:
            if binary_path.startswith('/'):
                # Absolute path - check if file exists
                if shutil.which(binary_path) or subprocess.run(['test', '-f', binary_path],
                                                             capture_output=True).returncode == 0:
                    logger.info(f"🔍 Found Chrome binary at: {binary_path}")
                    return binary_path
            else:
                # Check in system PATH
                found_path = shutil.which(binary_path)
                if found_path:
                    logger.info(f"🔍 Found Chrome binary in PATH: {found_path}")
                    return found_path
        except Exception as e:
            logger.debug(f"Could not check {binary_path}: {e}")
            continue

    logger.warning("⚠️ No Chrome binary found, WebDriver will use default")
    return None

# Define retryable exceptions for WebDriver setup
RETRYABLE_WEBDRIVER_EXCEPTIONS = (WebDriverException, SessionNotCreatedException)

def _setup_chrome_driver():
    """Set up Chrome WebDriver with enhanced compatibility."""
    import os
    import tempfile
    import uuid

    chrome_options = ChromeOptions()

    # Essential headless options
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # Enhanced stability options
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-sync")

    # Use unique session ID to avoid conflicts
    session_id = str(uuid.uuid4())[:8]

    # Create unique temp directories for this session
    temp_base = tempfile.gettempdir()
    user_data_dir = os.path.join(temp_base, f'chrome-user-data-{session_id}')
    cache_dir = os.path.join(temp_base, f'chrome-cache-{session_id}')
    webdriver_cache = os.path.join(temp_base, f'webdriver-cache-{session_id}')

    # Create directories
    for tmp_dir in [user_data_dir, cache_dir, webdriver_cache]:
        os.makedirs(tmp_dir, mode=0o777, exist_ok=True)

    # Use unique directories to avoid conflicts
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument(f"--disk-cache-dir={cache_dir}")
    chrome_options.add_argument("--disable-background-networking")

    # Use cache directory that webdriver-manager can access
    os.environ['WDM_LOCAL_CACHE'] = webdriver_cache

    logger.info(f"🔧 Creating Chrome session with ID: {session_id}")

    # Try system ChromeDriver first (for ARM64 compatibility)
    try:
        chrome_service = ChromeService('/usr/bin/chromedriver')
        # Set Chrome binary path dynamically
        chrome_binary = _find_chrome_binary()
        if chrome_binary:
            chrome_options.binary_location = chrome_binary
        return webdriver.Chrome(service=chrome_service, options=chrome_options)
    except Exception as e:
        logger.warning(f"System ChromeDriver failed: {e}, falling back to ChromeDriverManager")
        return webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()), options=chrome_options
        )

def _setup_firefox_driver():
    """Set up Firefox WebDriver as fallback."""
    firefox_options = FirefoxOptions()
    firefox_options.add_argument("--headless")
    firefox_options.add_argument("--width=1920")
    firefox_options.add_argument("--height=1080")

    # Set Firefox preferences for better compatibility
    firefox_options.set_preference("dom.webdriver.enabled", False)
    firefox_options.set_preference("useAutomationExtension", False)
    firefox_options.set_preference("general.useragent.override",
                                  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # Use cache directory that webdriver-manager can access
    import os
    os.environ['WDM_LOCAL_CACHE'] = '/tmp/webdriver-cache'

    return webdriver.Firefox(
        service=FirefoxService(GeckoDriverManager().install()), options=firefox_options
    )

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RETRYABLE_WEBDRIVER_EXCEPTIONS),
    reraise=False, # Do not re-raise after retries, let the function return None
)
def _setup_driver_with_retry():
    """Internal helper to set up WebDriver with retry logic and fallback support."""
    # Try Chrome first
    try:
        logger.info("🔧 Attempting Chrome WebDriver setup...")
        driver = _setup_chrome_driver()
        logger.info("✅ Chrome WebDriver setup successful")
        return driver
    except Exception as chrome_error:
        logger.warning(f"⚠️ Chrome WebDriver failed: {chrome_error}")

        # Fallback to Firefox if available
        try:
            # Check if Firefox is available
            import shutil
            if shutil.which('firefox') or shutil.which('firefox-esr'):
                logger.info("🔧 Falling back to Firefox WebDriver...")
                driver = _setup_firefox_driver()
                logger.info("✅ Firefox WebDriver setup successful")
                return driver
            else:
                logger.warning("⚠️ Firefox not available for fallback")
                return None
        except Exception as firefox_error:
            logger.error(f"❌ Firefox WebDriver also failed: {firefox_error}")
            logger.error("❌ All WebDriver options exhausted")
            return None

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
        try:
            driver.quit()
        except Exception as e:
            logger.warning(f"Error during WebDriver cleanup: {e}")
        driver = None
        logger.info("WebDriver closed.")

        # Log circuit breaker summary on close
        circuit_manager.log_summary()


def recover_driver():
    """Recovers WebDriver by closing current instance and creating a new one."""
    global driver
    logger.info("🔄 Attempting WebDriver recovery...")

    try:
        # Force close existing driver
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.warning(f"Error closing driver during recovery: {e}")
            driver = None

        # Create new driver instance
        driver = _setup_driver_with_retry()
        if driver:
            logger.info("✅ WebDriver recovery successful")
            return driver
        else:
            logger.error("❌ WebDriver recovery failed")
            return None

    except Exception as e:
        logger.error(f"❌ WebDriver recovery failed with error: {e}")
        driver = None
        return None


def ensure_driver_available():
    """Ensures WebDriver is available, recovers if necessary."""
    global driver

    if driver is None:
        logger.info("Driver is None, setting up new driver...")
        return setup_driver()

    # Test if driver is responsive
    try:
        _ = driver.current_url
        return driver
    except Exception as e:
        logger.warning(f"Driver not responsive ({e}), attempting recovery...")
        return recover_driver()


class ProtectedWebDriver:
    """
    WebDriver wrapper with circuit breaker protection and timeout handling.
    Provides robust protection against hanging requests and service failures.
    """

    def __init__(self, driver, default_timeout=30):
        self.driver = driver
        self.default_timeout = default_timeout

        # Use optimized circuit breaker configurations
        self.page_load_cb_config = OptimizedCircuitBreakerConfigs.get_page_load_config()
        self.element_cb_config = OptimizedCircuitBreakerConfigs.get_element_interaction_config()
        self.javascript_cb_config = OptimizedCircuitBreakerConfigs.get_javascript_execution_config()

        # Initialize enhanced element wait strategy
        self.element_wait_strategy = ElementWaitStrategy(driver, base_timeout=5.0)

        logger.info(f"🛡️ Protected WebDriver initialized with optimized configs (timeout: {default_timeout}s)")
        logger.debug(f"   • Element interaction threshold: {self.element_cb_config.failure_threshold}")
        logger.debug(f"   • Page load threshold: {self.page_load_cb_config.failure_threshold}")
        logger.debug(f"   • JavaScript threshold: {self.javascript_cb_config.failure_threshold}")

    def get(self, url, timeout=None):
        """Load a web page with circuit breaker protection"""
        timeout = timeout or self.default_timeout
        logger.debug(f"🌐 Loading page: {url} (timeout: {timeout}s)")

        cb = circuit_manager.get_circuit_breaker('webdriver_page_load', self.page_load_cb_config)

        def _load_page():
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

        return cb.call(_load_page)

    def find_element(self, *args, **kwargs):
        """Find element with circuit breaker protection"""
        cb = circuit_manager.get_circuit_breaker('webdriver_element_interaction', self.element_cb_config)
        return cb.call(self.driver.find_element, *args, **kwargs)

    def find_elements(self, *args, **kwargs):
        """Find elements with circuit breaker protection"""
        cb = circuit_manager.get_circuit_breaker('webdriver_element_interaction', self.element_cb_config)
        return cb.call(self.driver.find_elements, *args, **kwargs)

    def execute_script(self, script, *args, timeout=None):
        """Execute JavaScript with optimized circuit breaker protection"""
        timeout = timeout or 15
        logger.debug(f"⚡ Executing JavaScript (timeout: {timeout}s)")

        cb = circuit_manager.get_circuit_breaker('webdriver_javascript', self.javascript_cb_config)

        def _execute_js():
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

        return cb.call(_execute_js)

    # Enhanced element finding methods using smart waiting strategies

    def smart_find_element(self, selectors, timeout=None, condition="presence"):
        """Find element using enhanced waiting strategy with multiple selectors"""
        timeout = timeout or self.default_timeout
        return self.element_wait_strategy.smart_element_wait(
            selectors if isinstance(selectors, list) else [selectors],
            timeout=timeout,
            condition=condition
        )

    def smart_find_elements(self, selectors, timeout=None, min_count=1):
        """Find multiple elements using enhanced waiting strategy"""
        timeout = timeout or self.default_timeout
        return self.element_wait_strategy.smart_elements_wait(
            selectors if isinstance(selectors, list) else [selectors],
            timeout=timeout,
            min_count=min_count
        )

    def wait_for_page_stable(self, stability_timeout=2.0, max_wait=10.0):
        """Wait for page to stabilize (useful for AJAX content)"""
        return self.element_wait_strategy.wait_for_page_stable(stability_timeout, max_wait)

    def smart_find_form(self, form_selectors, timeout=None):
        """Find form using intelligent form detection"""
        timeout = timeout or self.default_timeout
        return self.element_wait_strategy.smart_form_wait(
            form_selectors if isinstance(form_selectors, list) else [form_selectors],
            timeout=timeout
        )

    def close(self):
        """Close the underlying WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ ProtectedWebDriver closed successfully")
            except Exception as e:
                logger.warning(f"⚠️ Error closing ProtectedWebDriver: {e}")
            finally:
                self.driver = None

    def __getattr__(self, name):
        """Delegate other attributes to the underlying driver"""
        return getattr(self.driver, name)


def get_protected_driver(timeout=30):
    """Get a protected WebDriver instance with circuit breaker protection"""
    # Always create a fresh WebDriver instance to avoid stale sessions
    raw_driver = _setup_driver_with_retry()
    if raw_driver:
        return ProtectedWebDriver(raw_driver, timeout)
    return None
