#!/usr/bin/env python
# coding: utf-8

import os
import re
import time
import random
import argparse
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from dotenv import load_dotenv
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from google.api_core.exceptions import (DeadlineExceeded, GoogleAPIError,
                                        InternalServerError, ResourceExhausted,
                                        ServiceUnavailable)
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from supabase import Client, create_client
from tenacity import (RetryError, retry, retry_if_exception_type,
                    stop_after_attempt, wait_exponential)
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

# --- Global Variables ---
driver = None
supabase = None
use_mock_genai_direct_page = False
use_mock_genai_snippet = False
use_mock_search_engine = False
GENAI_API_KEY = None
SEARCH_API_KEY = None
SEARCH_CX = None


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
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=chrome_options
            )
            print("WebDriver setup successfully.")
        except Exception as e:
            print(f"Error setting up WebDriver: {e}")
            print(
                "Ensure Chrome is installed if not using a pre-built environment like Colab."
            )
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


def normalize_url_join(base_url, relative_url):
    """Properly joins URLs while avoiding double slashes."""
    if base_url.endswith("/") and relative_url.startswith("/"):
        base_url = base_url.rstrip("/")
    return urljoin(base_url, relative_url)


def get_surrounding_text(element, max_length=200):
    """Extracts text from the parent element of a given link, limited in length."""
    if element and element.parent:
        parent_text = element.parent.get_text(separator=" ", strip=True)
        return parent_text[:max_length] + ("..." if len(parent_text) > max_length else "")
    return ""


def find_candidate_urls(soup, base_url):
    """Scans a BeautifulSoup soup object for potential parish directory links."""
    candidate_links = []
    processed_hrefs = set()
    parish_link_keywords = [
        "Churches", "Directory of Parishes", "Parishes", "parishfinder", "Parish Finder",
        "Find a Parish", "Locations", "Our Parishes", "Parish Listings", "Find a Church",
        "Church Directory", "Faith Communities", "Find Mass Times", "Our Churches",
        "Search Parishes", "Parish Map", "Mass Schedule", "Sacraments", "Worship",
    ]
    url_patterns = [
        r"parishes", r"directory", r"locations", r"churches", r"parish-finder",
        r"findachurch", r"parishsearch", r"parishdirectory", r"find-a-church",
        r"church-directory", r"parish-listings", r"parish-map", r"mass-times",
        r"sacraments", r"search", r"worship", r"finder",
    ]
    all_links_tags = soup.find_all("a", href=True)
    for link_tag in all_links_tags:
        href = link_tag["href"]
        if not href or href.startswith("#") or href.lower().startswith("javascript:") or href.lower().startswith("mailto:"):
            continue
        abs_href = normalize_url_join(base_url, href)
        if not abs_href.startswith("http"):
            continue
        if abs_href in processed_hrefs:
            continue
        link_text = link_tag.get_text(strip=True)
        surrounding_text = get_surrounding_text(link_tag)
        parsed_href_path = urlparse(abs_href).path.lower()
        text_match = any(
            keyword.lower() in link_text.lower()
            or keyword.lower() in surrounding_text.lower()
            for keyword in parish_link_keywords
        )
        pattern_match = any(
            re.search(pattern, parsed_href_path, re.IGNORECASE) for pattern in url_patterns
        )
        if text_match or pattern_match:
            candidate_links.append(
                {
                    "text": link_text,
                    "href": abs_href,
                    "surrounding_text": surrounding_text,
                }
            )
            processed_hrefs.add(abs_href)
    return candidate_links


RETRYABLE_GENAI_EXCEPTIONS = (
    DeadlineExceeded,
    ServiceUnavailable,
    ResourceExhausted,
    InternalServerError,
    GoogleAPIError,
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RETRYABLE_GENAI_EXCEPTIONS),
    reraise=True,
)
def _invoke_genai_model_with_retry(prompt):
    """Internal helper to invoke the GenAI model with retry logic."""
    if "genai" not in globals():
        raise NameError(
            "genai module not available. Ensure User-configurable parameters cell is run."
        )
    model = genai.GenerativeModel("gemini-1.5-flash")
    return model.generate_content(prompt)


def analyze_links_with_genai(candidate_links, diocese_name=None):
    """Analyzes candidate links using GenAI (or mock) to find the best parish directory URL."""
    best_link_found = None
    highest_score = -1
    current_use_mock_direct = use_mock_genai_direct_page if GENAI_API_KEY else True
    if not current_use_mock_direct:
        print(
            f"Attempting LIVE GenAI analysis for {len(candidate_links)} direct page links for {diocese_name or 'Unknown Diocese'}."
        )
    if current_use_mock_direct:
        mock_keywords = [
            "parish", "church", "directory", "location", "finder", "search",
            "map", "listing", "sacrament", "mass", "worship",
        ]
        for link_info in candidate_links:
            current_score = 0
            text_to_check = (
                link_info["text"] + " " + link_info["href"] + " " + link_info["surrounding_text"]
            ).lower()
            for kw in mock_keywords:
                if kw in text_to_check:
                    current_score += 3
            if diocese_name and diocese_name.lower() in text_to_check:
                current_score += 1
            current_score = min(current_score, 10)
            if current_score >= 7 and current_score > highest_score:
                highest_score = current_score
                best_link_found = link_info["href"]
        return best_link_found
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
            score_match = re.search(r"Score: (\d+)", response_text, re.IGNORECASE)
            if score_match:
                score = int(score_match.group(1))
                if score >= 7 and score > highest_score:
                    highest_score = score
                    best_link_found = link_info["href"]
        except RetryError as e:
            print(
                f"    GenAI API call (Direct Link) failed after multiple retries for {link_info['href']}: {e}"
            )
        except Exception as e:
            print(
                f"    Error calling GenAI (Direct Link) for {link_info['href']}: {e}. No score assigned."
            )
    return best_link_found


def is_retryable_http_error(exception):
    """Custom retry condition for HttpError: only retry on 5xx or 429 (rate limit)."""
    if isinstance(exception, HttpError):
        return exception.resp.status >= 500 or exception.resp.status == 429
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(HttpError),
    reraise=True,
)
def _invoke_search_api_with_retry(service, query, cx_id):
    """Internal helper to invoke the Google Custom Search API with retry logic."""
    return service.cse().list(q=query, cx=cx_id, num=3).execute()


def normalize_mock_url(base_url, path):
    """Properly constructs URLs for mock data, avoiding double slashes."""
    base_clean = base_url.rstrip("/")
    path_clean = path if path.startswith("/") else "/" + path
    return base_clean + path_clean


def analyze_search_snippet_with_genai(search_results, diocese_name):
    """Analyzes search result snippets using GenAI (or mock) to find the best parish directory URL."""
    best_link_from_snippet = None
    highest_score = -1
    current_use_mock_snippet = use_mock_genai_snippet if GENAI_API_KEY else True
    if not current_use_mock_snippet:
        print(
            f"Attempting LIVE GenAI analysis for {len(search_results)} snippets for {diocese_name}."
        )
    if current_use_mock_snippet:
        mock_keywords = [
            "parish", "church", "directory", "location", "finder",
            "search", "map", "listing", "mass times",
        ]
        for result in search_results:
            current_score = 0
            text_to_check = (
                result.get("title", "")
                + " "
                + result.get("snippet", "")
                + " "
                + result.get("link", "")
            ).lower()
            for kw in mock_keywords:
                if kw in text_to_check:
                    current_score += 3
            if diocese_name and diocese_name.lower() in text_to_check:
                current_score += 1
            current_score = min(current_score, 10)
            if current_score >= 7 and current_score > highest_score:
                highest_score = current_score
                best_link_from_snippet = result.get("link")
        return best_link_from_snippet
    for result in search_results:
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        link = result.get("link", "")
        prompt = f"""Given the following search result from {diocese_name}'s website:
        Title: "{title}"
        Snippet: "{snippet}"
        URL: "{link}"
        Does this link likely lead to a parish directory, church locator, or list of churches?
        Respond with a confidence score from 0 (not likely) to 10 (very likely) and a brief justification.
        Format as: Score: [score], Justification: [text]"""
        try:
            response = _invoke_genai_model_with_retry(prompt)
            response_text = response.text
            score_match = re.search(r"Score: (\d+)", response_text, re.IGNORECASE)
            if score_match:
                score = int(score_match.group(1))
                if score >= 7 and score > highest_score:
                    highest_score = score
                    best_link_from_snippet = link
        except RetryError as e:
            print(
                f"    GenAI API call (Snippet) for {link} failed after multiple retries: {e}"
            )
        except Exception as e:
            print(f"    Error calling GenAI for snippet analysis of {link}: {e}")
    return best_link_from_snippet


def search_for_directory_link(diocese_name, diocese_website_url):
    """Uses Google Custom Search (or mock) to find potential directory links, then analyzes snippets."""
    current_use_mock_search = (
        use_mock_search_engine if (SEARCH_API_KEY and SEARCH_CX) else True
    )
    if not current_use_mock_search:
        print(f"Attempting LIVE Google Custom Search for {diocese_name}.")
    if current_use_mock_search:
        mock_results = [
            {
                "link": normalize_mock_url(diocese_website_url, "/parishes"),
                "title": f"Parishes - {diocese_name}",
                "snippet": f"List of parishes in the Diocese of {diocese_name}. Find a parish near you.",
            },
            {
                "link": normalize_mock_url(diocese_website_url, "/directory"),
                "title": f"Directory - {diocese_name}",
                "snippet": f"Official directory of churches and schools for {diocese_name}.",
            },
            {
                "link": normalize_mock_url(diocese_website_url, "/find-a-church"),
                "title": f"Find a Church - {diocese_name}",
                "snippet": f"Search for a Catholic church in {diocese_name}. Mass times and locations.",
            },
        ]
        filtered_mock_results = [
            res
            for res in mock_results
            if res["link"].startswith(diocese_website_url.rstrip("/"))
        ]
        return analyze_search_snippet_with_genai(filtered_mock_results, diocese_name)
    try:
        service = build("customsearch", "v1", developerKey=SEARCH_API_KEY)
        queries = [
            f"parish directory site:{diocese_website_url}",
            f"list of churches site:{diocese_website_url}",
            f"find a parish site:{diocese_website_url}",
            f"{diocese_name} parish directory",
        ]
        search_results_items = []
        unique_links = set()
        for q in queries:
            if len(search_results_items) >= 5:
                break
            print(f"    Executing search query: {q}")
            try:
                response = _invoke_search_api_with_retry(service, q, SEARCH_CX)
                res_items = response.get("items", [])
                for item in res_items:
                    link = item.get("link")
                    if link and link not in unique_links:
                        search_results_items.append(item)
                        unique_links.add(link)
                time.sleep(0.2)
            except RetryError as e:
                print(f"    Search API call failed after retries for query '{q}': {e}")
                continue
            except HttpError as e:
                if e.resp.status == 403:
                    print(f"    Access denied (403) for query '{q}': {e.reason}")
                    print(
                        "    Check that Custom Search API is enabled and credentials are correct."
                    )
                    break
                else:
                    print(f"    HTTP error for query '{q}': {e}")
                    continue
            except Exception as e:
                print(f"    Unexpected error for query '{q}': {e}")
                continue
        if not search_results_items:
            print(f"    Search engine returned no results for {diocese_name}.")
            return None
        formatted_results = [
            {
                "link": item.get("link"),
                "title": item.get("title"),
                "snippet": item.get("snippet"),
            }
            for item in search_results_items
        ]
        return analyze_search_snippet_with_genai(formatted_results, diocese_name)
    except Exception as e:
        print(f"    Error during search engine setup for {diocese_name}: {e}")
        return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutException, WebDriverException)),
    reraise=True,
)
def get_page_with_retry(driver_instance, url):
    """Wraps driver.get() with retry logic."""
    driver_instance.get(url)


def main():
    """Main function to run the parish directory finder."""
    global supabase, use_mock_genai_direct_page, use_mock_genai_snippet, use_mock_search_engine
    global GENAI_API_KEY, SEARCH_API_KEY, SEARCH_CX

    parser = argparse.ArgumentParser(
        description="Find parish directory URLs on diocesan websites."
    )
    parser.add_argument(
        "--max_dioceses_to_process",
        type=int,
        default=5,
        help="Maximum number of dioceses to process. Set to 0 for no limit. Defaults to 5.",
    )
    args = parser.parse_args()
    MAX_DIOCESES_TO_PROCESS = args.max_dioceses_to_process
    if MAX_DIOCESES_TO_PROCESS != 0:
        print(
            f"Processing will be limited to {MAX_DIOCESES_TO_PROCESS} randomly selected dioceses."
        )
    else:
        print(
            "Processing will include all dioceses that lack parish directory URLs (no limit)."
        )

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    if SUPABASE_URL and SUPABASE_KEY:
        print("Supabase URL and Key loaded successfully.")
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("Supabase client initialized successfully.")
        except Exception as e:
            print(f"Error initializing Supabase client: {e}")
            supabase = None
    else:
        print("Supabase URL and/or Key NOT loaded. Please check environment variables.")

    GENAI_API_KEY = os.getenv("GENAI_API_KEY_USCCB")
    if GENAI_API_KEY and GENAI_API_KEY not in ["YOUR_API_KEY_PLACEHOLDER", "SET_YOUR_KEY_HERE"]:
        try:
            genai.configure(api_key=GENAI_API_KEY)
            print("GenAI configured successfully for LIVE calls if relevant mock flags are False.")
        except Exception as e:
            print(f"Error configuring GenAI with key: {e}. GenAI features will be mocked.")
            GENAI_API_KEY = None
    else:
        print("GenAI API Key is not set. GenAI features will be mocked globally.")

    SEARCH_API_KEY = os.getenv("SEARCH_API_KEY_USCCB")
    SEARCH_CX = os.getenv("SEARCH_CX_USCCB")
    if SEARCH_API_KEY and SEARCH_API_KEY not in ["YOUR_API_KEY_PLACEHOLDER", "SET_YOUR_KEY_HERE"] and SEARCH_CX and SEARCH_CX not in ["YOUR_CX_PLACEHOLDER", "SET_YOUR_CX_HERE"]:
        print("Google Custom Search API Key and CX loaded. Ready for LIVE calls if use_mock_search_engine is False.")
    else:
        print("Google Custom Search API Key and/or CX are NOT configured or available. Search engine calls will be mocked.")

    print(
        f"Mocking settings: Direct Page GenAI={use_mock_genai_direct_page}, Snippet GenAI={use_mock_genai_snippet}, Search Engine={use_mock_search_engine}"
    )

    dioceses_to_scan = []
    if supabase:
        try:
            response_dioceses = supabase.table("Dioceses").select("Website, Name").execute()
            all_dioceses_list = (
                response_dioceses.data if response_dioceses.data is not None else []
            )
            print(f"Fetched {len(all_dioceses_list)} total records from Dioceses table.")
            
            diocese_url_to_name = {d["Website"]: d["Name"] for d in all_dioceses_list}

            response_processed_dioceses = (
                supabase.table("DiocesesParishDirectory")
                .select("diocese_url")
                .execute()
            )
            processed_diocese_urls = (
                {item["diocese_url"] for item in response_processed_dioceses.data}
                if response_processed_dioceses.data is not None
                else set()
            )
            
            unprocessed_dioceses_urls = set(diocese_url_to_name.keys()) - processed_diocese_urls
            
            dioceses_to_scan_urls = []

            if unprocessed_dioceses_urls:
                print(f"Found {len(unprocessed_dioceses_urls)} dioceses needing parish directory URLs.")
                limit = MAX_DIOCESES_TO_PROCESS if MAX_DIOCESES_TO_PROCESS != 0 else len(unprocessed_dioceses_urls)
                dioceses_to_scan_urls = random.sample(list(unprocessed_dioceses_urls), limit)
            else:
                print("All dioceses have been scanned. Rescanning the oldest entries based on 'updated_at'.")
                limit = MAX_DIOCESES_TO_PROCESS if MAX_DIOCESES_TO_PROCESS != 0 else 5
                response_oldest_scanned = (
                    supabase.table("DiocesesParishDirectory")
                    .select("diocese_url")
                    .order("updated_at", desc=False)
                    .limit(limit)
                    .execute()
                )
                if response_oldest_scanned.data:
                    dioceses_to_scan_urls = [item["diocese_url"] for item in response_oldest_scanned.data]
                    print(f"Selected {len(dioceses_to_scan_urls)} oldest dioceses for rescanning.")
                else:
                    print("Could not find any previously scanned dioceses to rescan.")

            dioceses_to_scan = [
                {"url": url, "name": diocese_url_to_name.get(url, "Unknown Diocese")}
                for url in dioceses_to_scan_urls
                if url in diocese_url_to_name
            ]

        except Exception as e:
            print(f"Error during Supabase data operations: {e}")
            dioceses_to_scan = []
    else:
        print("Supabase client not initialized. Skipping data fetch.")

    if not dioceses_to_scan:
        print(
            "No dioceses to scan."
        )
        return

    driver_instance = setup_driver()
    if not driver_instance:
        print("Selenium WebDriver not available. Skipping URL processing.")
        return

    print(f"Processing {len(dioceses_to_scan)} dioceses with Selenium...")
    for diocese_info in dioceses_to_scan:
        current_url = diocese_info["url"]
        diocese_name = diocese_info["name"]
        print(f"--- Processing: {current_url} ({diocese_name}) ---")
        parish_dir_url_found = None
        status_text = "Not Found"
        method = "not_found_all_stages"
        try:
            get_page_with_retry(driver_instance, current_url)
            time.sleep(0.5)
            page_source = driver_instance.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            candidate_links = find_candidate_urls(soup, current_url)
            if candidate_links:
                print(
                    f"    Found {len(candidate_links)} candidates from direct page. Analyzing..."
                )
                parish_dir_url_found = analyze_links_with_genai(
                    candidate_links, diocese_name
                )
                if parish_dir_url_found:
                    method = "genai_direct_page_analysis"
                    status_text = "Success"
                else:
                    print(
                        f"    GenAI (direct page) did not find a suitable URL for {current_url}."
                    )
            else:
                print(
                    f"    No candidate links found by direct page scan for {current_url}."
                )
            if not parish_dir_url_found:
                print(
                    f"    Direct page analysis failed for {current_url}. Trying search engine fallback..."
                )
                parish_dir_url_found = search_for_directory_link(
                    diocese_name, current_url
                )
                if parish_dir_url_found:
                    method = "search_engine_snippet_genai"
                    status_text = "Success"
                else:
                    print(f"    Search engine fallback also failed for {current_url}.")
            if parish_dir_url_found:
                print(
                    f"    Result: Parish Directory URL for {current_url}: {parish_dir_url_found} (Method: {method})"
                )
            else:
                print(
                    f"    Result: No Parish Directory URL definitively found for {current_url} (Final method: {method})"
                )
            if supabase:
                data_to_upsert = {
                    "diocese_url": current_url,
                    "parish_directory_url": parish_dir_url_found,
                    "found": status_text,
                    "found_method": method,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                print(f"    Attempting to upsert data: {data_to_upsert}")
                try:
                    response = (
                        supabase.table("DiocesesParishDirectory")
                        .upsert(data_to_upsert)
                        .execute()
                    )
                    if hasattr(response, "error") and response.error:
                        error_detail = (
                            response.error.message
                            if hasattr(response.error, "message")
                            else str(response.error)
                        )
                        raise Exception(f"Supabase upsert error: {error_detail}")
                    print(
                        f"    Successfully upserted data for {current_url} to Supabase."
                    )
                except Exception as supa_error:
                    print(
                        f"    Error upserting data to Supabase for {current_url}: {supa_error}"
                    )
            else:
                print(
                    f"    Supabase client not available. Skipping database write for {current_url}."
                )
        except RetryError as e:
            error_message = str(e).replace('"', "''")
            print(
                f"    Result: Page load failed after multiple retries for {current_url}: {error_message[:100]}"
            )
            status_text = f"Error: Page load failed - {error_message[:60]}"
            method = "error_page_load_failed"
            if supabase:
                data_to_upsert = {
                    "diocese_url": current_url,
                    "parish_directory_url": None,
                    "found": status_text,
                    "found_method": method,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                try:
                    response = (
                        supabase.table("DiocesesParishDirectory")
                        .upsert(data_to_upsert)
                        .execute()
                    )
                    if hasattr(response, "error") and response.error:
                        error_detail = (
                            response.error.message
                            if hasattr(response.error, "message")
                            else str(response.error)
                        )
                        raise Exception(
                            f"Supabase upsert error (on page load fail): {error_detail}"
                        )
                except Exception as supa_error:
                    print(
                        f"    Error upserting error data to Supabase for {current_url}: {supa_error}"
                    )
            else:
                print(
                    f"    Supabase client not available. Skipping database write for error on {current_url}."
                )
        except Exception as e:
            error_message = str(e).replace('"', "''")
            print(
                f"    Result: General error processing {current_url}: {error_message[:100]}"
            )
            status_text = f"Error: {error_message[:100]}"
            method = "error_processing_general"
            if supabase:
                data_to_upsert = {
                    "diocese_url": current_url,
                    "parish_directory_url": None,
                    "found": status_text,
                    "found_method": method,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                try:
                    response = (
                        supabase.table("DiocesesParishDirectory")
                        .upsert(data_to_upsert)
                        .execute()
                    )
                    if hasattr(response, "error") and response.error:
                        error_detail = (
                            response.error.message
                            if hasattr(response.error, "message")
                            else str(response.error)
                        )
                        raise Exception(
                            f"Supabase upsert error (on general error): {error_detail}"
                        )
                except Exception as supa_error:
                    print(
                        f"    Error upserting error data to Supabase for {current_url}: {supa_error}"
                    )
            else:
                print(
                    f"    Supabase client not available. Skipping database write for error on {current_url}."
                )
    close_driver()


if __name__ == "__main__":
    main()