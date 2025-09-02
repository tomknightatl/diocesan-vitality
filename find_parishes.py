#!/usr/bin/env python
# coding: utf-8

# <a href="https://colab.research.google.com/github/tomknightatl/USCCB/blob/main/Find_Parish_Directory.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# # Notebook Configuration Parameters
# 
# This notebook is designed to find parish directory URLs on diocesan websites. The first code cell below, labeled "User-configurable parameters," contains all the necessary settings to control its behavior, including API key configurations, GitHub integration, and mocking controls.
# 
# Please review and configure these parameters before running the notebook.
# 
# ## API Keys & Secrets
# 
# For features that require external services (like Generative AI or Google Search), you'll need to provide API keys. These should be stored securely using Colab Secrets.
# 
# ### `GENAI_API_KEY`
# - **Purpose**: This API key is for Google Generative AI (e.g., Gemini models). It's used to analyze web page content and search result snippets to identify potential parish directory links.
# - **Configuration**:
#     1. Obtain your GenAI API key from Google AI Studio.
#     2. In Google Colab, go to "Secrets" (key icon in the left sidebar) and add a new secret named `GENAI_API_KEY_USCCB`. Paste your API key as the value.
#     3. In the "User-configurable parameters" cell, uncomment the line `# GENAI_API_KEY = GENAI_API_KEY_FROM_USERDATA` to use the key from Colab Secrets. Alternatively, you can directly assign your key string to `GENAI_API_KEY` in the cell, but using secrets is recommended.
# - **Default**: `None`. If no key is provided, GenAI-powered analysis will be disabled, and the system will rely on mock/basic analysis.
# - **Dependencies**: Required if you want to use live GenAI analysis. You'll also need to set `use_mock_genai_direct_page = False` and/or `use_mock_genai_snippet = False`.
# 
# ### `SEARCH_API_KEY` and `SEARCH_CX`
# - **Purpose**: These are for the Google Custom Search API. This API is used as a fallback mechanism to find parish directory links if direct analysis of the diocesan website doesn't yield clear results. `SEARCH_API_KEY` is your API key, and `SEARCH_CX` is your Programmable Search Engine ID.
# - **Configuration**:
#     1. Create a Programmable Search Engine on the Google Control Panel, configured to search diocesan websites. Note the Search Engine ID (`SEARCH_CX`).
#     2. Obtain your Google Cloud API Key enabled for the Custom Search API.
#     3. In Colab Secrets, add `SEARCH_API_KEY_USCCB` (with your API key) and `SEARCH_CX_USCCB` (with your Search Engine ID).
#     4. In the "User-configurable parameters" cell, uncomment the lines that assign these secrets to `SEARCH_API_KEY` and `SEARCH_CX`.
# - **Default**: `None` for both. If not set, the Google Custom Search fallback will be disabled, and the system will rely on mock/basic search.
# - **Dependencies**: Required for the search engine fallback feature. You'll also need to set `use_mock_search_engine = False`.
# 
# ## Mocking Controls
# 
# These boolean flags allow you to run the notebook with mocked (simulated) API responses, which is useful for testing or when API keys are unavailable. Set them to `False` to use live APIs (requires corresponding API keys to be configured).
# 
# ### `use_mock_genai_direct_page`
# - **Purpose**: Controls whether GenAI analysis of links found directly on a webpage uses live API calls or mocked responses.
# - **Configuration**: Set to `True` for mock, `False` for live.
# - **Default**: `True`. GenAI analysis for direct page links will be mocked.
# - **Dependencies**: If set to `False`, a valid `GENAI_API_KEY` must be configured.
# 
# ### `use_mock_genai_snippet`
# - **Purpose**: Controls whether GenAI analysis of search result snippets (from Google Custom Search) uses live API calls or mocked responses.
# - **Configuration**: Set to `True` for mock, `False` for live.
# - **Default**: `True`. GenAI analysis for search snippets will be mocked.
# - **Dependencies**: If set to `False`, a valid `GENAI_API_KEY` must be configured.
# 
# ### `use_mock_search_engine`
# - **Purpose**: Controls whether the Google Custom Search fallback uses live API calls or mocked search results.
# - **Configuration**: Set to `True` for mock, `False` for live.
# - **Default**: `True`. Google Custom Search calls will be mocked.
# - **Dependencies**: If set to `False`, valid `SEARCH_API_KEY` and `SEARCH_CX` must be configured.
# 
# ## Advanced Settings
# 
# ### `chrome_options`
# - **Purpose**: These are advanced settings for the Selenium WebDriver (Chrome). They control browser behavior like running headless (without a visible UI).
# - **Configuration**: Modified directly in the "User-configurable parameters" cell.
# - **Default**: Pre-configured for headless operation, no-sandbox, and other common settings for server environments. It's generally not necessary to change these unless you have specific WebDriver requirements.
# - **Dependencies**: None.

# In[ ]:


# Cell 1
# Install Install necessary libraries
import os
os.system('pip install supabase selenium webdriver-manager google-generativeai google-api-python-client tenacity')


# In[ ]:


# Cell 2
# Chrome Installation for Google Colab

import os
from dotenv import load_dotenv
load_dotenv()
import subprocess

def ensure_chrome_installed():
    """Ensures Chrome is installed in the Colab environment."""
    try:
        # Check if Chrome is already available
        result = subprocess.run(['which', 'google-chrome'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Chrome is already installed and available.")
            return True

        print("🔧 Chrome not found. Installing Chrome for Selenium...")

        # Install Chrome
        os.system('apt-get update > /dev/null 2>&1')
        os.system('wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - > /dev/null 2>&1')
        os.system('echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list')
        os.system('apt-get update > /dev/null 2>&1')
        os.system('apt-get install -y google-chrome-stable > /dev/null 2>&1')

        # Verify installation
        result = subprocess.run(['google-chrome', '--version'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Chrome installed successfully: {result.stdout.strip()}")
            return True
        else:
            print("❌ Chrome installation may have failed.")
            return False

    except Exception as e:
        print(f"❌ Error during Chrome installation: {e}")
        return False

# Run the installation check
# Run the installation check
# chrome_ready = ensure_chrome_installed()
# if chrome_ready:
#     print("🚀 Ready to proceed with Selenium operations!")
# else:
#     print("⚠️  You may need to restart the runtime if Chrome installation failed.")
print("NOTE: Chrome installation is skipped. Please ensure Chrome is installed and accessible on your system PATH.")


# In[ ]:


# Cell 3
# Setup API Keys

# Standard library imports
import sqlite3
import re
import os
import time

# Third-party library imports
import requests # For simple HTTP requests (though less used now with Selenium)
from bs4 import BeautifulSoup # For parsing HTML
# from google.colab import userdata # Moved to User-configurable parameters cell

# Selenium imports for web automation and dynamic content loading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("window-size=1920,1080")
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException

# Google GenAI imports (for Gemini model)
import google.generativeai as genai

# Google GenAI imports (for Gemini model)
# import google.generativeai as genai # Moved to User-configurable parameters cell
from google.api_core.exceptions import DeadlineExceeded, ServiceUnavailable, ResourceExhausted, InternalServerError, GoogleAPIError

# Google API Client imports (for Custom Search API)
from googleapiclient.errors import HttpError
# To use the live Google Custom Search API, uncomment the following import in this cell
# AND in Cell where `build` is called.
# from googleapiclient.discovery import build

# Tenacity library for robust retry mechanisms
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

# --- Selenium WebDriver Setup ---
# chrome_options is now defined in the first code cell (User-configurable parameters).
# Ensure it's available in the global scope if defined in the first cell.


driver = None # Global WebDriver instance

def setup_driver():
    """Initializes and returns the Selenium WebDriver instance."""
    global driver
    if driver is None:
        try:
            print("Setting up Chrome WebDriver...")
            # ChromeDriver is automatically managed by webdriver_manager
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            print("WebDriver setup successfully.")
        except Exception as e:
            print(f"Error setting up WebDriver: {e}")
            print("Ensure Chrome is installed if not using a pre-built environment like Colab.")
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


# In[ ]:


# Cell 4
# User-configurable-parameters
import os # For os.path.exists logic if adapted
import argparse # Import argparse

print("--- User Configurable Parameters Cell Initializing ---")

# --- Processing Limit Configuration ---
parser = argparse.ArgumentParser(description="Find parish directory URLs on diocesan websites.")
parser.add_argument(
    "--max_dioceses_to_process",
    type=int,
    default=5,
    help="Maximum number of dioceses to process. Set to 0 for no limit. Defaults to 5."
)
args = parser.parse_args()

MAX_DIOCESES_TO_PROCESS = args.max_dioceses_to_process

if MAX_DIOCESES_TO_PROCESS != 0:
    print(f"Processing will be limited to {MAX_DIOCESES_TO_PROCESS} randomly selected dioceses.")
else:
    print("Processing will include all dioceses that lack parish directory URLs (no limit).")

# --- Supabase Configuration ---
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if SUPABASE_URL and SUPABASE_KEY:
    print("Supabase URL and Key loaded successfully.")
else:
    print("Supabase URL and/or Key NOT loaded. Please check Colab Secrets.")

# --- GenAI API Key Setup ---
# To use live GenAI calls:
# 1. Ensure your GENAI_API_KEY_USCCB is stored in Colab Secrets.
# 2. EITHER: Uncomment the line below that assigns GENAI_API_KEY_FROM_USERDATA to GENAI_API_KEY
#    OR: Directly assign your key string to GENAI_API_KEY.
# 3. Set the use_mock_genai_direct_page and use_mock_genai_snippet flags (defined below) to False.
GENAI_API_KEY_FROM_USERDATA = os.getenv('GENAI_API_KEY_USCCB')
GENAI_API_KEY = None # Default: No API key, forces mock.

# UPDATED: Uncomment this line to use your API key from Colab Secrets
if GENAI_API_KEY_FROM_USERDATA and GENAI_API_KEY_FROM_USERDATA not in ["YOUR_API_KEY_PLACEHOLDER", "SET_YOUR_KEY_HERE"]:
    GENAI_API_KEY = GENAI_API_KEY_FROM_USERDATA # Now using key from Colab Secrets

if GENAI_API_KEY:
    try:
        genai.configure(api_key=GENAI_API_KEY)
        print("GenAI configured successfully for LIVE calls if relevant mock flags are False.")
    except Exception as e:
        print(f"Error configuring GenAI with key: {e}. GenAI features will be mocked.")
        GENAI_API_KEY = None # Ensure mock if configuration fails
else:
    print("GenAI API Key is not set. GenAI features will be mocked globally.")

# --- Search Engine API Key Setup ---
# To use live Google Custom Search API calls:
# 1. Ensure your SEARCH_API_KEY_USCCB and SEARCH_CX_USCCB are in Colab Secrets.
# 2. EITHER: Uncomment the lines below that assign _FROM_USERDATA to SEARCH_API_KEY and SEARCH_CX
#    OR: Directly assign your key strings.
# 3. Set the use_mock_search_engine flag (defined below) to False.
SEARCH_API_KEY_FROM_USERDATA = os.getenv('SEARCH_API_KEY_USCCB')
SEARCH_CX_FROM_USERDATA = os.getenv('SEARCH_CX_USCCB')

SEARCH_API_KEY = None # Default: No API key, forces mock.
SEARCH_CX = None      # Default: No CX, forces mock.
# UPDATED: Uncomment these lines to use your keys from Colab Secrets
if SEARCH_API_KEY_FROM_USERDATA and SEARCH_API_KEY_FROM_USERDATA not in ["YOUR_API_KEY_PLACEHOLDER", "SET_YOUR_KEY_HERE"]:
    SEARCH_API_KEY = SEARCH_API_KEY_FROM_USERDATA # Now using key from Colab Secrets
if SEARCH_CX_FROM_USERDATA and SEARCH_CX_FROM_USERDATA not in ["YOUR_CX_PLACEHOLDER", "SET_YOUR_CX_HERE"]:
    SEARCH_CX = SEARCH_CX_FROM_USERDATA            # Now using CX from Colab Secrets

if SEARCH_API_KEY and SEARCH_CX:
    print("Google Custom Search API Key and CX loaded. Ready for LIVE calls if use_mock_search_engine is False.")
else:
    print("Google Custom Search API Key and/or CX are NOT configured or available. Search engine calls will be mocked.")

# --- Mocking Controls ---
# These flags determine whether to use live API calls or mocked responses.
# UPDATED: Set these to False to attempt LIVE API calls (since your APIs are now working)
global use_mock_genai_direct_page
use_mock_genai_direct_page = False  # Changed from True to False - Use LIVE GenAI for direct page analysis
# Set to False to attempt LIVE GenAI calls for search snippet analysis (requires valid GENAI_API_KEY)
global use_mock_genai_snippet
use_mock_genai_snippet = False  # Changed from True to False - Use LIVE GenAI for snippet analysis
# UPDATED: Set to False to attempt LIVE Google Custom Search calls (since your API is now working)
global use_mock_search_engine
use_mock_search_engine = False  # Changed from True to False - Use LIVE Google Custom Search

print(f"Mocking settings: Direct Page GenAI={use_mock_genai_direct_page}, Snippet GenAI={use_mock_genai_snippet}, Search Engine={use_mock_search_engine}")

# --- Selenium WebDriver Options ---

print("--- End User Configurable Parameters Cell ---")


# In[ ]:


# Cell 5
# Fetch Dioceses Info from Supabase database

import random
from supabase import create_client, Client
import os # os is kept for MAX_DIOCESES_TO_PROCESS logic check from globals()

# Initialize Supabase Client
# These should be available from Cell 3 (User-configurable parameters)
# SUPABASE_URL, SUPABASE_KEY
if 'SUPABASE_URL' in globals() and 'SUPABASE_KEY' in globals() and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase client initialized successfully.")
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
        supabase = None
else:
    print("Error: Supabase URL or Key not found in global variables. Please ensure they are set in Cell 3.")
    supabase = None

dioceses_to_scan = []
if supabase:
    try:
        # Fetch all dioceses
        response_dioceses = supabase.table('Dioceses').select('Website, Name').execute()
        all_dioceses_list = response_dioceses.data if response_dioceses.data is not None else []
        print(f"Fetched {len(all_dioceses_list)} total records from Dioceses table.")

        # Fetch dioceses that already have a valid parish directory URL
        response_processed_dioceses = supabase.table('DiocesesParishDirectory').select('diocese_url').not_.is_('parish_directory_url', 'null').not_.eq('parish_directory_url', '').execute()

        processed_diocese_urls = {item['diocese_url'] for item in response_processed_dioceses.data} if response_processed_dioceses.data is not None else set()
        print(f"Found {len(processed_diocese_urls)} dioceses already processed with valid URLs in DiocesesParishDirectory.")

        # Filter out processed dioceses
        unprocessed_dioceses = [
            {'url': d['Website'], 'name': d['Name']}
            for d in all_dioceses_list
            if d['Website'] not in processed_diocese_urls
        ]
        print(f"Found {len(unprocessed_dioceses)} dioceses needing parish directory URLs (or not yet in DiocesesParishDirectory).")

        # Apply limit if MAX_DIOCESES_TO_PROCESS is set (ensure MAX_DIOCESES_TO_PROCESS is accessible)
        # MAX_DIOCESES_TO_PROCESS should be defined in Cell 3.
        if 'MAX_DIOCESES_TO_PROCESS' in globals() and MAX_DIOCESES_TO_PROCESS is not None:
            if len(unprocessed_dioceses) > MAX_DIOCESES_TO_PROCESS:
                dioceses_to_scan = random.sample(unprocessed_dioceses, MAX_DIOCESES_TO_PROCESS)
                print(f"Randomly selected {len(dioceses_to_scan)} dioceses for processing (limit: {MAX_DIOCESES_TO_PROCESS}).")
            else:
                dioceses_to_scan = unprocessed_dioceses
                print(f"All {len(dioceses_to_scan)} unprocessed dioceses will be processed (within limit of {MAX_DIOCESES_TO_PROCESS}).")
        else:
            dioceses_to_scan = unprocessed_dioceses
            print(f"All {len(dioceses_to_scan)} unprocessed dioceses will be processed (no limit set).")

    except Exception as e:
        print(f"Error during Supabase data operations: {e}")
        dioceses_to_scan = [] # Ensure it's empty on error
else:
    print("Supabase client not initialized. Skipping data fetch.")
    dioceses_to_scan = []

# Final check and message
if not dioceses_to_scan:
    print("No dioceses to scan based on Supabase data and MAX_DIOCESES_TO_PROCESS setting.")
else:
    print(f"Prepared {len(dioceses_to_scan)} dioceses for scanning.")


# In[ ]:


# Cell 6
# Function to find candidate parish listing URLs from page content

from urllib.parse import urljoin, urlparse # For handling relative and absolute URLs
import re # For regular expression matching in URL paths
from datetime import datetime, timezone # For adding timezone-aware timestamps

def normalize_url_join(base_url, relative_url):
    """Properly joins URLs while avoiding double slashes."""
    # Remove trailing slash from base_url if relative_url starts with slash
    if base_url.endswith('/') and relative_url.startswith('/'):
        base_url = base_url.rstrip('/')
    return urljoin(base_url, relative_url)

def get_surrounding_text(element, max_length=200):
    """Extracts text from the parent element of a given link, limited in length.
    This provides context for the link.
    """
    if element and element.parent:
        parent_text = element.parent.get_text(separator=' ', strip=True)
        # Truncate if too long to keep prompts for GenAI concise
        return parent_text[:max_length] + ('...' if len(parent_text) > max_length else '')
    return ''

def find_candidate_urls(soup, base_url):
    """Scans a BeautifulSoup soup object for potential parish directory links.
    It uses a combination of keyword matching in link text/surrounding text
    and regex patterns for URL paths.
    Returns a list of candidate link dictionaries.
    """
    candidate_links = []
    processed_hrefs = set() # To avoid adding duplicate URLs

    # Keywords likely to appear in link text or surrounding text for parish directories
    parish_link_keywords = [
        'Churches', 'Directory of Parishes', 'Parishes', 'parishfinder', 'Parish Finder',
        'Find a Parish', 'Locations', 'Our Parishes', 'Parish Listings', 'Find a Church',
        'Church Directory', 'Faith Communities', 'Find Mass Times', 'Our Churches',
        'Search Parishes', 'Parish Map', 'Mass Schedule', 'Sacraments', 'Worship'
    ]
    # Regex patterns for URL paths that often indicate a parish directory
    url_patterns = [
        r'parishes', r'directory', r'locations', r'churches',
        r'parish-finder', r'findachurch', r'parishsearch', r'parishdirectory',
        r'find-a-church', r'church-directory', r'parish-listings', r'parish-map',
        r'mass-times', r'sacraments', r'search', r'worship', r'finder'
    ]

    all_links_tags = soup.find_all('a', href=True) # Find all <a> tags with an href attribute

    for link_tag in all_links_tags:
        href = link_tag['href']
        # Skip empty, anchor, JavaScript, or mailto links
        if not href or href.startswith('#') or href.lower().startswith('javascript:') or href.lower().startswith('mailto:'):
            continue

        abs_href = normalize_url_join(base_url, href) # Resolve relative URLs to absolute with fixed joining
        if not abs_href.startswith('http'): # Ensure it's a web link
            continue
        if abs_href in processed_hrefs: # Avoid re-processing the same URL
            continue

        link_text = link_tag.get_text(strip=True)
        surrounding_text = get_surrounding_text(link_tag)
        parsed_href_path = urlparse(abs_href).path.lower() # Get the path component of the URL

        # Check for matches based on keywords in text or URL patterns
        text_match = any(keyword.lower() in link_text.lower() or keyword.lower() in surrounding_text.lower() for keyword in parish_link_keywords)
        pattern_match = any(re.search(pattern, parsed_href_path, re.IGNORECASE) for pattern in url_patterns)

        if text_match or pattern_match:
            candidate_links.append({
                'text': link_text,
                'href': abs_href,
                'surrounding_text': surrounding_text
            })
            processed_hrefs.add(abs_href)

    return candidate_links


# In[ ]:


# Cell 7
# GenAI Powered Link Analyzer (for direct page content)

# Define exceptions on which GenAI calls should be retried
RETRYABLE_GENAI_EXCEPTIONS = (
    DeadlineExceeded, ServiceUnavailable, ResourceExhausted,
    InternalServerError, GoogleAPIError
)

@retry(
    stop=stop_after_attempt(3), # Retry up to 3 times
    wait=wait_exponential(multiplier=1, min=2, max=10), # Exponential backoff: 2s, 4s, 8s...
    retry=retry_if_exception_type(RETRYABLE_GENAI_EXCEPTIONS),
    reraise=True # Reraise the last exception if all retries fail
)
def _invoke_genai_model_with_retry(prompt):
    """Internal helper to invoke the GenAI model with retry logic."""
    # print("    Attempting GenAI call...") # Uncomment for debugging retries
    # GENAI_API_KEY is configured in the first cell. If None, this will fail if not mocked.
    # Ensure genai is available if first cell wasn't run, or handle error
    if 'genai' not in globals():
        raise NameError("genai module not available. Ensure User-configurable parameters cell is run.")
    model = genai.GenerativeModel('gemini-1.5-flash') # Or your preferred model
    return model.generate_content(prompt)

def analyze_links_with_genai(candidate_links, diocese_name=None):
    """Analyzes candidate links using GenAI (or mock) to find the best parish directory URL."""
    best_link_found = None
    highest_score = -1

    # --- Mock vs. Live Control for GenAI (Direct Page Analysis) ---
    # Control for this is `use_mock_genai_direct_page` from the User-configurable parameters cell.
    # GENAI_API_KEY is also defined there.
    # Ensure mock if key is not configured, overriding user setting for safety.
    current_use_mock_direct = use_mock_genai_direct_page if ('GENAI_API_KEY' in globals() and GENAI_API_KEY) else True

    if not current_use_mock_direct:
        print(f"Attempting LIVE GenAI analysis for {len(candidate_links)} direct page links for {diocese_name or 'Unknown Diocese'}.")
    # else:
        # print(f"Using MOCKED GenAI analysis for {len(candidate_links)} direct page links for {diocese_name or 'Unknown Diocese'}.")
    # ---

    if current_use_mock_direct:
        mock_keywords = ['parish', 'church', 'directory', 'location', 'finder', 'search', 'map', 'listing', 'sacrament', 'mass', 'worship']
        for link_info in candidate_links:
            current_score = 0
            text_to_check = (link_info['text'] + ' ' + link_info['href'] + ' ' + link_info['surrounding_text']).lower()
            for kw in mock_keywords:
                if kw in text_to_check: current_score += 3
            if diocese_name and diocese_name.lower() in text_to_check: current_score +=1
            current_score = min(current_score, 10) # Cap score at 10
            if current_score >= 7 and current_score > highest_score: # Threshold of 7
                highest_score = current_score
                best_link_found = link_info['href']
        return best_link_found

    # --- Actual GenAI API Call Logic (executes if use_mock is False) ---
    for link_info in candidate_links:
        prompt = f"""Given the following information about a link from the {diocese_name or 'a diocesan'} website:
        Link Text: "{link_info['text']}"
        Link URL: "{link_info['href']}"
        Surrounding Text: "{link_info['surrounding_text']}"
        Does this link likely lead to a parish directory, a list of churches, or a way to find parishes?
        Respond with a confidence score from 0 (not likely) to 10 (very likely) and a brief justification.
        Format as: Score: [score], Justification: [text]"""
        try:
            response = _invoke_genai_model_with_retry(prompt)
            response_text = response.text
            # print(f"    GenAI Raw Response (Direct Link): {response_text}") # For debugging
            score_match = re.search(r"Score: (\d+)", response_text, re.IGNORECASE)
            if score_match:
                score = int(score_match.group(1))
                if score >= 7 and score > highest_score:
                    highest_score = score
                    best_link_found = link_info['href']
            # else: print(f"    Could not parse score from GenAI (Direct Link) for {link_info['href']}: {response_text}")
        except RetryError as e:
            print(f"    GenAI API call (Direct Link) failed after multiple retries for {link_info['href']}: {e}")
        except Exception as e:
            print(f"    Error calling GenAI (Direct Link) for {link_info['href']}: {e}. No score assigned.")
    return best_link_found


# In[ ]:


# Cell 8
# Search Engine Fallback Functions & GenAI Snippet Analysis

# Ensure 'build' is imported if using live search. It's commented in Cell 1 by default.
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def is_retryable_http_error(exception):
    """Custom retry condition for HttpError: only retry on 5xx or 429 (rate limit)."""
    if isinstance(exception, HttpError):
        return exception.resp.status >= 500 or exception.resp.status == 429
    return False

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(HttpError),
    reraise=True
)
def _invoke_search_api_with_retry(service, query, cx_id):
    """Internal helper to invoke the Google Custom Search API with retry logic."""
    # print(f"    Attempting Search API call for query: {query}") # Uncomment for debugging retries
    return service.cse().list(q=query, cx=cx_id, num=3).execute() # Fetch top 3 results per query

def normalize_mock_url(base_url, path):
    """Properly constructs URLs for mock data, avoiding double slashes."""
    # Ensure base_url doesn't end with slash and path starts with slash
    base_clean = base_url.rstrip('/')
    path_clean = path if path.startswith('/') else '/' + path
    return base_clean + path_clean

def analyze_search_snippet_with_genai(search_results, diocese_name):
    """Analyzes search result snippets using GenAI (or mock) to find the best parish directory URL."""
    best_link_from_snippet = None
    highest_score = -1

    # --- Mock vs. Live Control for GenAI (Snippet Analysis) ---
    # Control for this is `use_mock_genai_snippet` from the User-configurable parameters cell.
    # GENAI_API_KEY is also defined there.
    # Ensure mock if key is not configured, overriding user setting for safety.
    current_use_mock_snippet = use_mock_genai_snippet if ('GENAI_API_KEY' in globals() and GENAI_API_KEY) else True

    if not current_use_mock_snippet:
        print(f"Attempting LIVE GenAI analysis for {len(search_results)} snippets for {diocese_name}.")
    # else:
        # print(f"Using MOCKED GenAI analysis for {len(search_results)} snippets for {diocese_name}.")
    # ---

    if current_use_mock_snippet:
        mock_keywords = ['parish', 'church', 'directory', 'location', 'finder', 'search', 'map', 'listing', 'mass times']
        for result in search_results:
            current_score = 0
            text_to_check = (result.get('title', '') + ' ' + result.get('snippet', '') + ' ' + result.get('link', '')).lower()
            for kw in mock_keywords:
                if kw in text_to_check: current_score += 3
            if diocese_name and diocese_name.lower() in text_to_check: current_score += 1
            current_score = min(current_score, 10)
            if current_score >= 7 and current_score > highest_score: # Threshold of 7
                highest_score = current_score
                best_link_from_snippet = result.get('link')
        return best_link_from_snippet

    # --- Actual GenAI API Call Logic for Snippets (executes if use_mock_genai_for_snippet is False) ---
    for result in search_results:
        title = result.get('title', '')
        snippet = result.get('snippet', '')
        link = result.get('link', '')
        prompt = f"""Given the following search result from {diocese_name}'s website:
        Title: "{title}"
        Snippet: "{snippet}"
        URL: "{link}"
        Does this link likely lead to a parish directory, church locator, or list of churches?
        Respond with a confidence score from 0 (not likely) to 10 (very likely) and a brief justification.
        Format as: Score: [score], Justification: [text]"""
        try:
            # Uses the same _invoke_genai_model_with_retry as direct page analysis
            response = _invoke_genai_model_with_retry(prompt)
            response_text = response.text
            # print(f"    GenAI Raw Response (Snippet): {response_text}") # For debugging
            score_match = re.search(r"Score: (\d+)", response_text, re.IGNORECASE)
            if score_match:
                score = int(score_match.group(1))
                if score >= 7 and score > highest_score:
                    highest_score = score
                    best_link_from_snippet = link
            # else: print(f"    Could not parse score from GenAI (Snippet) for {link}: {response_text}")
        except RetryError as e:
            print(f"    GenAI API call (Snippet) for {link} failed after multiple retries: {e}")
        except Exception as e:
            print(f"    Error calling GenAI for snippet analysis of {link}: {e}")
    return best_link_from_snippet

def search_for_directory_link(diocese_name, diocese_website_url):
    """Uses Google Custom Search (or mock) to find potential directory links, then analyzes snippets."""
    # print(f"Executing search engine fallback for {diocese_name} ({diocese_website_url})") # Verbose

    # --- Mock vs. Live Control for Search Engine ---
    # Control for this is `use_mock_search_engine` from the User-configurable parameters cell.
    # SEARCH_API_KEY and SEARCH_CX are also defined there.
    # Ensure mock if keys are not configured, overriding user setting for safety.
    current_use_mock_search = use_mock_search_engine if ('SEARCH_API_KEY' in globals() and SEARCH_API_KEY and 'SEARCH_CX' in globals() and SEARCH_CX) else True

    if not current_use_mock_search:
        print(f"Attempting LIVE Google Custom Search for {diocese_name}.")
    # else:
        # print(f"Using MOCKED Google Custom Search for {diocese_name}.")
    # ---

    if current_use_mock_search:
        mock_results = [
            {'link': normalize_mock_url(diocese_website_url, '/parishes'), 'title': f"Parishes - {diocese_name}", 'snippet': f"List of parishes in the Diocese of {diocese_name}. Find a parish near you."},
            {'link': normalize_mock_url(diocese_website_url, '/directory'), 'title': f"Directory - {diocese_name}", 'snippet': f"Official directory of churches and schools for {diocese_name}."},
            {'link': normalize_mock_url(diocese_website_url, '/find-a-church'), 'title': f"Find a Church - {diocese_name}", 'snippet': f"Search for a Catholic church in {diocese_name}. Mass times and locations."}
        ]
        # Simulate `site:` search by filtering mock results to the diocese's website
        filtered_mock_results = [res for res in mock_results if res['link'].startswith(diocese_website_url.rstrip('/'))]
        return analyze_search_snippet_with_genai(filtered_mock_results, diocese_name)

    # --- Actual Google Custom Search API Call Logic (executes if use_mock_search is False) ---
    try:
        # `build` is imported at the top of this cell for clarity when live calls are made.
        service = build("customsearch", "v1", developerKey=SEARCH_API_KEY)
        # Construct multiple queries to increase chances of finding the directory
        queries = [
            f"parish directory site:{diocese_website_url}",
            f"list of churches site:{diocese_website_url}",
            f"find a parish site:{diocese_website_url}",
            f"{diocese_name} parish directory"  # Broader query without site restriction as a last resort
        ]
        search_results_items = []
        unique_links = set()  # To avoid duplicate results from different queries

        for q in queries:
            if len(search_results_items) >= 5: break  # Limit total API calls/results
            print(f"    Executing search query: {q}")
            try:
                # Use the retry-enabled helper for the API call
                response = _invoke_search_api_with_retry(service, q, SEARCH_CX)
                res_items = response.get('items', [])
                for item in res_items:
                    link = item.get('link')
                    if link and link not in unique_links:
                        search_results_items.append(item)
                        unique_links.add(link)
                time.sleep(0.2)  # Brief pause between queries to be polite to the API
            except RetryError as e:
                print(f"    Search API call failed after retries for query '{q}': {e}")
                continue  # Try next query
            except HttpError as e:
                if e.resp.status == 403:
                    print(f"    Access denied (403) for query '{q}': {e.reason}")
                    print("    Check that Custom Search API is enabled and credentials are correct.")
                    break  # Stop trying other queries if we have auth issues
                else:
                    print(f"    HTTP error for query '{q}': {e}")
                    continue
            except Exception as e:
                print(f"    Unexpected error for query '{q}': {e}")
                continue

        if not search_results_items:
            print(f"    Search engine returned no results for {diocese_name}.")
            return None

        # Format results for the snippet analyzer
        formatted_results = [{'link': item.get('link'), 'title': item.get('title'), 'snippet': item.get('snippet')} for item in search_results_items]
        return analyze_search_snippet_with_genai(formatted_results, diocese_name)

    except Exception as e:
        print(f"    Error during search engine setup for {diocese_name}: {e}")
        return None


# In[ ]:


# Cell 9
# Process URLs, Apply Analysis Stages, and Write Results to Supabase Database

# Imports are assumed to be handled by previous cells (esp. for TimeoutException, WebDriverException, BeautifulSoup, time, retry)
# from supabase import Client # Only if supabase client needs re-init and not global

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutException, WebDriverException)),
    reraise=True
)
def get_page_with_retry(driver_instance, url):
    """Wraps driver.get() with retry logic."""
    # print(f"    Attempting to load page: {url}") # Uncomment for debugging retries
    driver_instance.get(url)

# Check for Supabase client (initialized in Cell 5)
if 'supabase' not in globals() or not supabase:
    print("Error: Supabase client not found or not initialized. Please ensure Cell 5 (Supabase setup) ran correctly.")
    # If dioceses_to_scan was populated by Cell 5, it might still try to run, so clear it.
    dioceses_to_scan = []

# Debug: Check if user is authenticated
if supabase:
    try:
        # Test authentication by trying to get user info
        user = supabase.auth.get_user()
        if user and user.user:
            print(f"Authenticated as user: {user.user.email}")
        else:
            print("Warning: No authenticated user found. This may cause RLS policy violations.")
    except Exception as auth_error:
        print(f"Authentication check failed: {auth_error}")

if 'dioceses_to_scan' in locals() and dioceses_to_scan:
    driver_instance = setup_driver() # Initialize the WebDriver
    if driver_instance:
        print(f"Processing {len(dioceses_to_scan)} dioceses with Selenium...")
        for diocese_info in dioceses_to_scan:
            current_url = diocese_info['url']
            diocese_name = diocese_info['name']
            print(f"--- Processing: {current_url} ({diocese_name}) ---")

            parish_dir_url_found = None
            status_text = "Not Found" # Default status
            method = "not_found_all_stages" # Default method

            try:
                # Stage 1: Load page with Selenium
                get_page_with_retry(driver_instance, current_url)
                time.sleep(0.5)
                page_source = driver_instance.page_source
                soup = BeautifulSoup(page_source, 'html.parser')

                # Stage 2: Find candidate links
                candidate_links = find_candidate_urls(soup, current_url)

                if candidate_links:
                    # Stage 3: Analyze with GenAI
                    print(f"    Found {len(candidate_links)} candidates from direct page. Analyzing...")
                    parish_dir_url_found = analyze_links_with_genai(candidate_links, diocese_name)
                    if parish_dir_url_found:
                        method = "genai_direct_page_analysis"
                        status_text = "Success"
                    else:
                        print(f"    GenAI (direct page) did not find a suitable URL for {current_url}.")
                else:
                    print(f"    No candidate links found by direct page scan for {current_url}.")

                # Stage 4: Search engine fallback
                if not parish_dir_url_found:
                    print(f"    Direct page analysis failed for {current_url}. Trying search engine fallback...")
                    parish_dir_url_found = search_for_directory_link(diocese_name, current_url)
                    if parish_dir_url_found:
                        method = "search_engine_snippet_genai"
                        status_text = "Success"
                    else:
                        print(f"    Search engine fallback also failed for {current_url}.")

                # Log final result for this diocese before DB write
                if parish_dir_url_found:
                     print(f"    Result: Parish Directory URL for {current_url}: {parish_dir_url_found} (Method: {method})")
                else:
                     print(f"    Result: No Parish Directory URL definitively found for {current_url} (Final method: {method})")

                # Write to Supabase
                if supabase: # Check if client is available
                    data_to_upsert = {
                        'diocese_url': current_url,
                        'parish_directory_url': parish_dir_url_found,
                        'found': status_text,
                        'found_method': method,
                        'scanned_at': datetime.now(timezone.utc).isoformat()
                    }

                    print(f"    Attempting to upsert data: {data_to_upsert}")

                    try:
                        # First, try to check if RLS is causing issues by testing table access
                        test_response = supabase.table('DiocesesParishDirectory').select('*').limit(1).execute()
                        print(f"    Table access test successful, found {len(test_response.data)} rows")

                        # Now attempt the upsert
                        response = supabase.table('DiocesesParishDirectory').upsert(data_to_upsert).execute()

                        # Check for errors in the response object
                        if hasattr(response, 'error') and response.error:
                            error_detail = response.error.message if hasattr(response.error, 'message') else str(response.error)
                            raise Exception(f"Supabase upsert error: {error_detail}")

                        print(f"    Successfully upserted data for {current_url} to Supabase.")

                    except Exception as supa_error:
                        error_str = str(supa_error)
                        print(f"    Error upserting data to Supabase for {current_url}: {error_str}")

                        # Check if it's an RLS policy violation
                        if '42501' in error_str or 'row-level security policy' in error_str.lower():
                            print("    RLS Policy Issue Detected!")
                            print("    Solutions:")
                            print("    1. Authenticate with supabase.auth.sign_in_with_password(email, password)")
                            print("    2. Disable RLS: ALTER TABLE DiocesesParishDirectory DISABLE ROW LEVEL SECURITY;")
                            print("    3. Create a policy: CREATE POLICY ... ON DiocesesParishDirectory FOR ALL USING (true);")

                            # Try inserting without upsert as a fallback
                            try:
                                print("    Attempting regular insert as fallback...")
                                insert_response = supabase.table('DiocesesParishDirectory').insert(data_to_upsert).execute()
                                if hasattr(insert_response, 'error') and insert_response.error:
                                    print(f"    Insert also failed: {insert_response.error}")
                                else:
                                    print("    Insert succeeded!")
                            except Exception as insert_error:
                                print(f"    Insert fallback also failed: {insert_error}")
                else:
                    print(f"    Supabase client not available. Skipping database write for {current_url}.")

            except RetryError as e:
                error_message = str(e).replace('"', "''")
                print(f"    Result: Page load failed after multiple retries for {current_url}: {error_message[:100]}")
                status_text = f"Error: Page load failed - {error_message[:60]}"
                method = "error_page_load_failed"
                # Write error to Supabase
                if supabase:
                    data_to_upsert = {
                        'diocese_url': current_url,
                        'parish_directory_url': None,
                        'found': status_text,
                        'found_method': method,
                        'scanned_at': datetime.now(timezone.utc).isoformat()
                    }
                    try:
                        response = supabase.table('DiocesesParishDirectory').upsert(data_to_upsert).execute()
                        if hasattr(response, 'error') and response.error:
                            error_detail = response.error.message if hasattr(response.error, 'message') else str(response.error)
                            raise Exception(f"Supabase upsert error (on page load fail): {error_detail}")
                    except Exception as supa_error:
                        print(f"    Error upserting error data to Supabase for {current_url}: {supa_error}")
                else:
                    print(f"    Supabase client not available. Skipping database write for error on {current_url}.")
            except Exception as e:
                error_message = str(e).replace('"', "''")
                print(f"    Result: General error processing {current_url}: {error_message[:100]}")
                status_text = f"Error: {error_message[:100]}"
                method = "error_processing_general"
                # Write error to Supabase
                if supabase:
                    data_to_upsert = {
                        'diocese_url': current_url,
                        'parish_directory_url': None,
                        'found': status_text,
                        'found_method': method,
                        'scanned_at': datetime.now(timezone.utc).isoformat()
                    }
                    try:
                        response = supabase.table('DiocesesParishDirectory').upsert(data_to_upsert).execute()
                        if hasattr(response, 'error') and response.error:
                            error_detail = response.error.message if hasattr(response.error, 'message') else str(response.error)
                            raise Exception(f"Supabase upsert error (on general error): {error_detail}")
                    except Exception as supa_error:
                        print(f"    Error upserting error data to Supabase for {current_url}: {supa_error}")
                else:
                    print(f"    Supabase client not available. Skipping database write for error on {current_url}.")

        close_driver()
    else:
        print("Selenium WebDriver not available. Skipping URL processing.")
else:
    print("No dioceses to scan (dioceses_to_scan is empty or not defined). Ensure Cell 5 (Supabase data fetch) ran correctly.")

