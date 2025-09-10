from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from core.logger import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from selenium.common.exceptions import WebDriverException, SessionNotCreatedException

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
