#!/usr/bin/env python
# coding: utf-8

import argparse
import random
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import google.generativeai as genai
from bs4 import BeautifulSoup
from google.api_core.exceptions import (DeadlineExceeded, GoogleAPIError,
                                        InternalServerError, ResourceExhausted,
                                        ServiceUnavailable)
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from selenium.common.exceptions import TimeoutException, WebDriverException
from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

import config
from core.db import get_supabase_client
from core.driver import close_driver, setup_driver
from core.utils import normalize_url_join
from core.logger import get_logger

logger = get_logger(__name__)

# --- Global Variables ---
use_mock_genai_direct_page = False
use_mock_genai_snippet = False
use_mock_search_engine = False


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
    model = genai.GenerativeModel("gemini-1.5-flash")
    return model.generate_content(prompt)


def analyze_links_with_genai(candidate_links, diocese_name=None):
    """Analyzes candidate links using GenAI (or mock) to find the best parish directory URL."""
    best_link_found = None
    highest_score = -1
    current_use_mock_direct = use_mock_genai_direct_page if config.GENAI_API_KEY else True
    if not current_use_mock_direct:
        logger.info(
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
            logger.info(
                f"    GenAI API call (Direct Link) failed after multiple retries for {link_info['href']}: {e}"
            )
        except Exception as e:
            logger.info(
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


def analyze_search_snippet_with_genai(search_results, diocese_name):
    """Analyzes search result snippets using GenAI (or mock) to find the best parish directory URL."""
    best_link_from_snippet = None
    highest_score = -1
    current_use_mock_snippet = use_mock_genai_snippet if config.GENAI_API_KEY else True
    if not current_use_mock_snippet:
        logger.info(
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
            logger.info(
                f"    GenAI API call (Snippet) for {link} failed after multiple retries: {e}"
            )
        except Exception as e:
            logger.info(f"    Error calling GenAI for snippet analysis of {link}: {e}")
    return best_link_from_snippet


def search_for_directory_link(diocese_name, diocese_website_url):
    """Uses Google Custom Search (or mock) to find potential directory links, then analyzes snippets."""
    current_use_mock_search = (
        use_mock_search_engine if (config.SEARCH_API_KEY and config.SEARCH_CX) else True
    )
    if not current_use_mock_search:
        logger.info(f"Attempting LIVE Google Custom Search for {diocese_name}.")
    if current_use_mock_search:
        mock_results = [
            {
                "link": normalize_url_join(diocese_website_url, "/parishes"),
                "title": f"Parishes - {diocese_name}",
                "snippet": f"List of parishes in the Diocese of {diocese_name}. Find a parish near you.",
            },
            {
                "link": normalize_url_join(diocese_website_url, "/directory"),
                "title": f"Directory - {diocese_name}",
                "snippet": f"Official directory of churches and schools for {diocese_name}.",
            },
            {
                "link": normalize_url_join(diocese_website_url, "/find-a-church"),
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
        service = build("customsearch", "v1", developerKey=config.SEARCH_API_KEY)
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
            logger.info(f"    Executing search query: {q}")
            try:
                response = _invoke_search_api_with_retry(service, q, config.SEARCH_CX)
                res_items = response.get("items", [])
                for item in res_items:
                    link = item.get("link")
                    if link and link not in unique_links:
                        search_results_items.append(item)
                        unique_links.add(link)
                time.sleep(0.2)
            except RetryError as e:
                logger.info(f"    Search API call failed after retries for query '{q}': {e}")
                continue
            except HttpError as e:
                if e.resp.status == 403:
                    logger.info(f"    Access denied (403) for query '{q}': {e.reason}")
                    logger.info(
                        "    Check that Custom Search API is enabled and credentials are correct."
                    )
                    break
                else:
                    logger.info(f"    HTTP error for query '{q}': {e}")
                    continue
            except Exception as e:
                logger.info(f"    Unexpected error for query '{q}': {e}")
                continue
        if not search_results_items:
            logger.info(f"    Search engine returned no results for {diocese_name}.")
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
        logger.info(f"    Error during search engine setup for {diocese_name}: {e}")
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


def find_parish_directories(diocese_id=None, max_dioceses_to_process=config.DEFAULT_MAX_DIOCESES):
    """Main function to run the parish directory finder."""
    
    if config.GENAI_API_KEY:
        try:
            genai.configure(api_key=config.GENAI_API_KEY)
            logger.info("GenAI configured successfully.")
        except Exception as e:
            logger.info(f"Error configuring GenAI with key: {e}. GenAI features will be mocked.")
    else:
        logger.info("GenAI API Key is not set. GenAI features will be mocked globally.")

    supabase = get_supabase_client()
    if not supabase:
        return

    dioceses_to_scan = []
    try:
        # Base query for all dioceses
        query = supabase.table("Dioceses").select("id, Website, Name")

        # Filter by a single diocese if an ID is provided
        if diocese_id:
            query = query.eq('id', diocese_id)
        
        response_dioceses = query.execute()
        all_dioceses_list = response_dioceses.data if response_dioceses.data else []
        logger.info(f"Fetched {len(all_dioceses_list)} total records from Dioceses table.")
        
        if not all_dioceses_list:
            logger.info("No dioceses found to process.")
            return

        dioceses_to_scan_urls = []
        # If a specific diocese is provided, we scan it regardless of whether it was processed before.
        if diocese_id:
            dioceses_to_scan_urls = [d['Website'] for d in all_dioceses_list if d.get('Website')]
        else:
            # Logic to find unprocessed or outdated dioceses if no specific one is targeted
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
            
            if unprocessed_dioceses_urls:
                logger.info(f"Found {len(unprocessed_dioceses_urls)} dioceses needing parish directory URLs.")
                limit = max_dioceses_to_process if max_dioceses_to_process != 0 else len(unprocessed_dioceses_urls)
                dioceses_to_scan_urls = random.sample(list(unprocessed_dioceses_urls), limit)
            else:
                logger.info("All dioceses have been scanned. Rescanning the oldest entries based on 'updated_at'.")
                limit = max_dioceses_to_process if max_dioceses_to_process != 0 else 5
                response_oldest_scanned = (
                    supabase.table("DiocesesParishDirectory")
                    .select("diocese_url")
                    .order("updated_at", desc=False)
                    .limit(limit)
                    .execute()
                )
                if response_oldest_scanned.data:
                    dioceses_to_scan_urls = [item["diocese_url"] for item in response_oldest_scanned.data]
                    logger.info(f"Selected {len(dioceses_to_scan_urls)} oldest dioceses for rescanning.")
                else:
                    logger.info("Could not find any previously scanned dioceses to rescan.")

        # Construct the final list of dioceses to scan
        dioceses_to_scan = [
            {"id": d['id'], "url": d['Website'], "name": d['Name']}
            for d in all_dioceses_list
            if d.get('Website') in dioceses_to_scan_urls
        ]

    except Exception as e:
        logger.info(f"Error during Supabase data operations: {e}")
        dioceses_to_scan = []

    if not dioceses_to_scan:
        logger.info("No dioceses to scan.")
        return

    driver_instance = setup_driver()
    if not driver_instance:
        logger.info("Selenium WebDriver not available. Skipping URL processing.")
        return

    logger.info(f"Processing {len(dioceses_to_scan)} dioceses with Selenium...")
    for diocese_info in dioceses_to_scan:
        current_url = diocese_info["url"]
        diocese_name = diocese_info["name"]
        current_diocese_id = diocese_info["id"]
        logger.info(f"--- Processing: {current_url} ({diocese_name}) ---")
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
                logger.info(
                    f"    Found {len(candidate_links)} candidates from direct page. Analyzing..."
                )
                parish_dir_url_found = analyze_links_with_genai(
                    candidate_links, diocese_name
                )
                if parish_dir_url_found:
                    method = "genai_direct_page_analysis"
                    status_text = "Success"
                else:
                    logger.info(
                        f"    GenAI (direct page) did not find a suitable URL for {current_url}."
                    )
            else:
                logger.info(
                    f"    No candidate links found by direct page scan for {current_url}."
                )
            if not parish_dir_url_found:
                logger.info(
                    f"    Direct page analysis failed for {current_url}. Trying search engine fallback..."
                )
                parish_dir_url_found = search_for_directory_link(
                    diocese_name, current_url
                )
                if parish_dir_url_found:
                    method = "search_engine_snippet_genai"
                    status_text = "Success"
                else:
                    logger.info(f"    Search engine fallback also failed for {current_url}.")
            if parish_dir_url_found:
                logger.info(
                    f"    Result: Parish Directory URL for {current_url}: {parish_dir_url_found} (Method: {method})"
                )
            else:
                logger.info(
                    f"    Result: No Parish Directory URL definitively found for {current_url} (Final method: {method})"
                )
            
            data_to_upsert = {
                "diocese_id": current_diocese_id,
                "diocese_url": current_url,
                "parish_directory_url": parish_dir_url_found,
                "found": status_text,
                "found_method": method,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            logger.info(f"    Attempting to upsert data: {data_to_upsert}")
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
                logger.info(
                    f"    Successfully upserted data for {current_url} to Supabase."
                )
            except Exception as supa_error:
                logger.info(
                    f"    Error upserting data to Supabase for {current_url}: {supa_error}"
                )
        
        except RetryError as e:
            error_message = str(e).replace('"', "''")
            logger.info(
                f"    Result: Page load failed after multiple retries for {current_url}: {error_message[:100]}"
            )
            status_text = f"Error: Page load failed - {error_message[:60]}"
            method = "error_page_load_failed"
            data_to_upsert = {
                "diocese_id": current_diocese_id,
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
                logger.info(
                    f"    Error upserting error data to Supabase for {current_url}: {supa_error}"
                )
        
        except Exception as e:
            error_message = str(e).replace('"', "''")
            logger.info(
                f"    Result: General error processing {current_url}: {error_message[:100]}"
            )
            status_text = f"Error: {error_message[:100]}"
            method = "error_processing_general"
            data_to_upsert = {
                "diocese_id": current_diocese_id,
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
                logger.info(
                    f"    Error upserting error data to Supabase for {current_url}: {supa_error}"
                )
    
    close_driver()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find parish directory URLs on diocesan websites."
    )
    parser.add_argument(
        "--diocese_id",
        type=int,
        default=None,
        help="ID of a specific diocese to process. If not provided, processes all.",
    )
    parser.add_argument(
        "--max_dioceses_to_process",
        type=int,
        default=5,
        help="Maximum number of dioceses to process. Set to 0 for no limit. Defaults to 5.",
    )
    args = parser.parse_args()
    
    config.validate_config()
    find_parish_directories(args.diocese_id, args.max_dioceses_to_process)
