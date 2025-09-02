from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

driver = None

def setup_driver():
    """Initializes and returns the Selenium WebDriver instance."""
    global driver
    if driver is None:
        try:
            print("Setting up Chrome WebDriver...")
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
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=chrome_options
            )
            print("WebDriver setup successfully.")
        except Exception as e:
            print(f"Error setting up WebDriver: {e}")
            driver = None
    return driver

def close_driver():
    """Closes the Selenium WebDriver instance if it's active."""
    global driver
    if driver:
        print("Closing WebDriver...")
        driver.quit()
        driver = None
        print("WebDriver closed.")
