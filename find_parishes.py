#!/usr/bin/env python
# coding: utf - 8

import argparse
import asyncio
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlparse

import google.generativeai as genai
from bs4 import BeautifulSoup
from google.api_core.exceptions import (
    DeadlineExceeded,
    GoogleAPIError,
    InternalServerError,
    ResourceExhausted,
    ServiceUnavailable,
)
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import config
from core.db import get_supabase_client
from core.db_batch_operations import get_batch_manager
from core.driver import ensure_driver_available, recover_driver
from core.logger import get_logger
from core.utils import normalize_url_join
from respectful_automation import RespectfulAutomation, create_blocking_report

logger = get_logger(__name__)

# Global batch manager for database operations
_batch_manager = None

# Global respectful automation instance
_respectful_automation = None


def get_current_batch_manager():
    """Get the current batch manager instance."""
    return _batch_manager


def get_respectful_automation():
    """Get the current respectful automation instance."""
    return _respectful_automation


def batch_upsert_parish_directory(data_to_upsert, current_url):
    """Helper function to batch upsert parish directory data."""
    batch_manager = get_current_batch_manager()
    if batch_manager:
        logger.info(f"    Adding to batch queue: {data_to_upsert}")
        success = batch_manager.add_record("DiocesesParishDirectory", data_to_upsert)
        if success:
            logger.info(f"    Batch flushed during processing of {current_url}")
        else:
            logger.info(f"    Added to batch queue for {current_url}")
    else:
        # Fallback to direct upsert if batch manager not available
        logger.warning(f"    Batch manager not available, using direct upsert for {current_url}")
        try:
            supabase = get_supabase_client()
            response = supabase.table("DiocesesParishDirectory").upsert(data_to_upsert, on_conflict="diocese_id").execute()
            if hasattr(response, "error") and response.error:
                error_detail = response.error.message if hasattr(response.error, "message") else str(response.error)
                raise Exception(f"Supabase upsert error: {error_detail}")
            logger.info(f"    Successfully upserted data for {current_url} to Supabase.")
        except Exception as e:
            logger.info(f"    Error upserting data to Supabase for {current_url}: {e}")


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
        "Churches",
        "Directory of Parishes",
        "Parishes",
        "parishfinder",
        "Parish Finder",
        "Find a Parish",
        "Locations",
        "Our Parishes",
        "Parish Listings",
        "Find a Church",
        "Church Directory",
        "Faith Communities",
        "Find Mass Times",
        "Our Churches",
        "Search Parishes",
        "Parish Map",
        "Mass Schedule",
        "Sacraments",
        "Worship",
    ]
    url_patterns = [
        r"parishes",
        r"directory",
        r"locations",
        r"churches",
        r"parish - finder",
        r"findachurch",
        r"parishsearch",
        r"parishdirectory",
        r"find - a-church",
        r"church - directory",
        r"parish - listings",
        r"parish - map",
        r"mass - times",
        r"sacraments",
        r"search",
        r"worship",
        r"finder",
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
            keyword.lower() in link_text.lower() or keyword.lower() in surrounding_text.lower()
            for keyword in parish_link_keywords
        )
        pattern_match = any(re.search(pattern, parsed_href_path, re.IGNORECASE) for pattern in url_patterns)
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
    model = genai.GenerativeModel("gemini - 1.5 - flash")
    return model.generate_content(prompt)


async def _invoke_genai_model_async(prompt):
    """Async wrapper for GenAI model invocation."""
    loop = asyncio.get_event_loop()
    try:
        # Run the sync GenAI call in a thread pool to avoid blocking the event loop
        response = await loop.run_in_executor(None, _invoke_genai_model_with_retry, prompt)
        return response
    except Exception as e:
        # Re - raise the exception to maintain the same error handling
        raise e


async def _analyze_single_link_async(link_info, diocese_name):
    """Analyze a single link asynchronously."""
    prompt = f"""Given the following information about a link from the {diocese_name or 'a diocesan'} website:
    Link Text: "{link_info['text']}"
    Link URL: "{link_info['href']}"
    Surrounding Text: "{link_info['surrounding_text']}"
    Does this link likely lead to a parish directory, a list of churches, or a way to find parishes?
    Respond with a confidence score from 0 (not likely) to 10 (very likely) and a brief justification.
    Format as: Score: [score], Justification: [text]"""

    try:
        response = await _invoke_genai_model_async(prompt)
        response_text = response.text
        score_match = re.search(r"Score: (\d+)", response_text, re.IGNORECASE)
        if score_match:
            score = int(score_match.group(1))
            return {"href": link_info["href"], "score": score}
    except RetryError as e:
        logger.info(f"    GenAI API call (Direct Link) failed after multiple retries for {link_info['href']}: {e}")
    except Exception as e:
        logger.info(f"    Error calling GenAI (Direct Link) for {link_info['href']}: {e}. No score assigned.")

    return {"href": link_info["href"], "score": 0}


async def analyze_links_with_genai_async(candidate_links, diocese_name=None):
    """Analyzes candidate links using GenAI concurrently to find the best parish directory URL."""
    current_use_mock_direct = use_mock_genai_direct_page if config.GENAI_API_KEY else True

    if not current_use_mock_direct:
        return await _analyze_links_with_live_genai(candidate_links, diocese_name)
    else:
        return _analyze_links_with_mock_scoring(candidate_links, diocese_name)


async def _analyze_links_with_live_genai(candidate_links, diocese_name):
    """Analyze links using live GenAI with concurrent processing."""
    logger.info(
        f"Attempting LIVE GenAI analysis (CONCURRENT) for {len(candidate_links)} direct page links for {diocese_name or 'Unknown Diocese'}."
    )

    tasks = [_analyze_single_link_async(link_info, diocese_name) for link_info in candidate_links]
    results = await _execute_concurrent_analysis(tasks)
    return _find_best_result_from_analysis(results)


async def _execute_concurrent_analysis(tasks):
    """Execute analysis tasks concurrently with semaphore limiting."""
    semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent GenAI calls

    async def analyze_with_semaphore(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*[analyze_with_semaphore(task) for task in tasks], return_exceptions=True)


def _find_best_result_from_analysis(results):
    """Find the best result from GenAI analysis results."""
    best_link_found = None
    highest_score = -1

    for result in results:
        if isinstance(result, dict) and result.get("score", 0) >= 7:
            if result["score"] > highest_score:
                highest_score = result["score"]
                best_link_found = result["href"]

    return best_link_found


def _analyze_links_with_mock_scoring(candidate_links, diocese_name):
    """Analyze links using mock keyword scoring."""
    mock_keywords = [
        "parish",
        "church",
        "directory",
        "location",
        "finder",
        "search",
        "map",
        "listing",
        "sacrament",
        "mass",
        "worship",
    ]

    best_link_found = None
    highest_score = -1

    for link_info in candidate_links:
        score = _calculate_mock_score(link_info, mock_keywords, diocese_name)
        if score >= 7 and score > highest_score:
            highest_score = score
            best_link_found = link_info["href"]

    return best_link_found


def _calculate_mock_score(link_info, mock_keywords, diocese_name):
    """Calculate mock score for a single link."""
    current_score = 0
    text_to_check = (link_info["text"] + " " + link_info["href"] + " " + link_info["surrounding_text"]).lower()

    for kw in mock_keywords:
        if kw in text_to_check:
            current_score += 3

    if diocese_name and diocese_name.lower() in text_to_check:
        current_score += 1

    return min(current_score, 10)


def analyze_links_with_genai(candidate_links, diocese_name=None):
    """Synchronous wrapper for backwards compatibility."""
    # If there are no candidate links or only one, use the old sequential method
    if len(candidate_links) <= 1:
        return _analyze_links_with_genai_sequential(candidate_links, diocese_name)

    # Use the async version for multiple links
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # No event loop exists, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(analyze_links_with_genai_async(candidate_links, diocese_name))


def _analyze_links_with_genai_sequential(candidate_links, diocese_name=None):
    """Original sequential implementation - kept as fallback."""
    current_use_mock_direct = _should_use_mock_genai()

    if not current_use_mock_direct:
        logger.info(
            f"Attempting LIVE GenAI analysis for {len(candidate_links)} direct page links for {diocese_name or 'Unknown Diocese'}."
        )

    if current_use_mock_direct:
        return _analyze_links_with_mock_scoring(candidate_links, diocese_name)
    else:
        return _analyze_links_with_live_genai(candidate_links, diocese_name)


def _should_use_mock_genai() -> bool:
    """Determine whether to use mock GenAI or live API"""
    return use_mock_genai_direct_page if config.GENAI_API_KEY else True


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


async def _analyze_single_snippet_async(result, diocese_name):
    """Analyze a single search result snippet asynchronously."""
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
        response = await _invoke_genai_model_async(prompt)
        response_text = response.text
        score_match = re.search(r"Score: (\d+)", response_text, re.IGNORECASE)
        if score_match:
            score = int(score_match.group(1))
            return {"link": link, "score": score}
    except RetryError as e:
        logger.info(f"    GenAI API call (Snippet) for {link} failed after multiple retries: {e}")
    except Exception as e:
        logger.info(f"    Error calling GenAI for snippet analysis of {link}: {e}")

    return {"link": link, "score": 0}


async def analyze_search_snippet_with_genai_async(search_results, diocese_name):
    """Analyzes search result snippets using GenAI concurrently to find the best parish directory URL."""
    current_use_mock_snippet = use_mock_genai_snippet if config.GENAI_API_KEY else True

    if not current_use_mock_snippet:
        return await _analyze_snippets_with_live_genai(search_results, diocese_name)
    else:
        return _analyze_snippets_with_mock_scoring(search_results, diocese_name)


async def _analyze_snippets_with_live_genai(search_results, diocese_name):
    """Analyze search snippets using live GenAI with concurrent processing."""
    logger.info(f"Attempting LIVE GenAI analysis (CONCURRENT) for {len(search_results)} snippets for {diocese_name}.")

    tasks = [_analyze_single_snippet_async(result, diocese_name) for result in search_results]
    results = await _execute_concurrent_snippet_analysis(tasks)
    return _find_best_snippet_result(results)


async def _execute_concurrent_snippet_analysis(tasks):
    """Execute snippet analysis tasks concurrently with semaphore limiting."""
    semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent GenAI calls for snippets

    async def analyze_with_semaphore(task):
        async with semaphore:
            return await task

    return await asyncio.gather(*[analyze_with_semaphore(task) for task in tasks], return_exceptions=True)


def _find_best_snippet_result(results):
    """Find the best result from snippet analysis."""
    best_link_from_snippet = None
    highest_score = -1

    for result in results:
        if isinstance(result, dict) and result.get("score", 0) >= 7:
            if result["score"] > highest_score:
                highest_score = result["score"]
                best_link_from_snippet = result["link"]

    return best_link_from_snippet


def _analyze_snippets_with_mock_scoring(search_results, diocese_name):
    """Analyze search snippets using mock keyword scoring."""
    mock_keywords = [
        "parish",
        "church",
        "directory",
        "location",
        "finder",
        "search",
        "map",
        "listing",
        "mass times",
    ]

    best_link_from_snippet = None
    highest_score = -1

    for result in search_results:
        score = _calculate_snippet_mock_score(result, mock_keywords, diocese_name)
        if score >= 7 and score > highest_score:
            highest_score = score
            best_link_from_snippet = result.get("link")

    return best_link_from_snippet


def _calculate_snippet_mock_score(result, mock_keywords, diocese_name):
    """Calculate mock score for a single search snippet."""
    current_score = 0
    text_to_check = (result.get("title", "") + " " + result.get("snippet", "") + " " + result.get("link", "")).lower()

    for kw in mock_keywords:
        if kw in text_to_check:
            current_score += 3

    if diocese_name and diocese_name.lower() in text_to_check:
        current_score += 1

    return min(current_score, 10)


def analyze_search_snippet_with_genai(search_results, diocese_name):
    """Synchronous wrapper for backwards compatibility."""
    # If there are no results or only one, use the old sequential method
    if len(search_results) <= 1:
        return _analyze_search_snippet_with_genai_sequential(search_results, diocese_name)

    # Use the async version for multiple results
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # No event loop exists, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(analyze_search_snippet_with_genai_async(search_results, diocese_name))


def _analyze_search_snippet_with_genai_sequential(search_results, diocese_name):
    """Original sequential implementation - kept as fallback."""
    current_use_mock_snippet = _should_use_mock_snippet_analysis()

    if not current_use_mock_snippet:
        logger.info(f"Attempting LIVE GenAI analysis for {len(search_results)} snippets for {diocese_name}.")

    if current_use_mock_snippet:
        return _analyze_snippets_with_mock_scoring(search_results, diocese_name)
    else:
        return _analyze_snippets_with_live_genai(search_results, diocese_name)


def _should_use_mock_snippet_analysis() -> bool:
    """Determine whether to use mock snippet analysis or live GenAI"""
    return use_mock_genai_snippet if config.GENAI_API_KEY else True


def search_and_extract_urls(search_query):
    """Performs a search and returns URLs in the expected format for GenAI analysis."""
    try:
        # Extract domain from search query if it's a site search
        if search_query.startswith("site:"):
            domain = search_query.split()[0].replace("site:", "")
            base_url = f"https://{domain}" if not domain.startswith("http") else domain.replace("site:", "")

            # Return mock search results for the domain
            mock_results = [
                {
                    "link": f"{base_url.rstrip('/')}/parishes",
                    "title": "Parishes Directory",
                    "snippet": ("Directory of parishes and churches in the diocese. Find mass times and locations."),
                },
                {
                    "link": f"{base_url.rstrip('/')}/directory",
                    "title": "Parish Directory",
                    "snippet": ("Official directory of Catholic parishes, churches, and missions."),
                },
                {
                    "link": f"{base_url.rstrip('/')}/find - a-parish",
                    "title": "Find a Parish",
                    "snippet": ("Search for a Catholic parish or church near you. Mass schedules and contact information."),
                },
                {
                    "link": f"{base_url.rstrip('/')}/our - church",
                    "title": "Our Churches",
                    "snippet": ("List of churches and parishes in our diocese with mass times and directions."),
                },
            ]
            return mock_results

        # Fallback for non - site searches
        return []

    except Exception as e:
        logger.error(f"Error in search_and_extract_urls: {e}")
        return []


def search_for_directory_link(diocese_name, diocese_website_url):
    """Uses Google Custom Search (or mock) to find potential directory links, then analyzes snippets."""
    current_use_mock_search = _should_use_mock_search()

    if not current_use_mock_search:
        logger.info(f"Attempting LIVE Google Custom Search for {diocese_name}.")

    if current_use_mock_search:
        return _handle_mock_search(diocese_name, diocese_website_url)

    return _handle_live_search(diocese_name, diocese_website_url)


def _should_use_mock_search() -> bool:
    """Determine whether to use mock search or live Google Custom Search"""
    return use_mock_search_engine if (config.SEARCH_API_KEY and config.SEARCH_CX) else True


def _handle_mock_search(diocese_name: str, diocese_website_url: str):
    """Handle mock search for testing/development"""
    mock_results = _generate_mock_search_results(diocese_name, diocese_website_url)
    filtered_mock_results = [res for res in mock_results if res["link"].startswith(diocese_website_url.rstrip("/"))]
    return analyze_search_snippet_with_genai(filtered_mock_results, diocese_name)


def _generate_mock_search_results(diocese_name: str, diocese_website_url: str) -> list:
    """Generate mock search results for testing"""
    return [
        {
            "link": normalize_url_join(diocese_website_url, "/parishes"),
            "title": f"Parishes - {diocese_name}",
            "snippet": (f"List of parishes in the Diocese of {diocese_name}. Find a parish near you."),
        },
        {
            "link": normalize_url_join(diocese_website_url, "/directory"),
            "title": f"Directory - {diocese_name}",
            "snippet": (f"Official directory of churches and schools for {diocese_name}."),
        },
        {
            "link": normalize_url_join(diocese_website_url, "/find - a-church"),
            "title": f"Find a Church - {diocese_name}",
            "snippet": (f"Search for a Catholic church in {diocese_name}. Mass times and locations."),
        },
    ]


def _handle_live_search(diocese_name: str, diocese_website_url: str):
    """Handle live Google Custom Search API calls"""
    try:
        service = build("customsearch", "v1", developerKey=config.SEARCH_API_KEY)
        search_results_items = _execute_search_queries(service, diocese_name, diocese_website_url)

        if not search_results_items:
            logger.info(f"    Search engine returned no results for {diocese_name}.")
            return None

        formatted_results = _format_search_results(search_results_items)
        return analyze_search_snippet_with_genai(formatted_results, diocese_name)

    except Exception as e:
        logger.info(f"    Error during search engine setup for {diocese_name}: {e}")
        return None


def _generate_search_queries(diocese_name: str, diocese_website_url: str) -> list:
    """Generate search queries for finding parish directories"""
    return [
        f"parish directory site:{diocese_website_url}",
        f"list of churches site:{diocese_website_url}",
        f"find a parish site:{diocese_website_url}",
        f"{diocese_name} parish directory",
    ]


def _execute_search_queries(service, diocese_name: str, diocese_website_url: str) -> list:
    """Execute search queries and collect results"""
    queries = _generate_search_queries(diocese_name, diocese_website_url)
    search_results_items = []
    unique_links = set()

    for q in queries:
        if len(search_results_items) >= 5:
            break

        logger.info(f"    Executing search query: {q}")

        try:
            response = _invoke_search_api_with_retry(service, q, config.SEARCH_CX)
            _process_search_response(response, search_results_items, unique_links)
            time.sleep(0.1)  # Brief pause between API calls to be respectful

        except RetryError as e:
            logger.info(f"    Search API call failed after retries for query '{q}': {e}")
            continue
        except HttpError as e:
            if _handle_http_error(e, q):
                break
            continue
        except Exception as e:
            logger.info(f"    Unexpected error for query '{q}': {e}")
            continue

    return search_results_items


def _process_search_response(response: dict, search_results_items: list, unique_links: set):
    """Process search API response and add unique results"""
    res_items = response.get("items", [])
    for item in res_items:
        link = item.get("link")
        if link and link not in unique_links:
            search_results_items.append(item)
            unique_links.add(link)


def _handle_http_error(error: HttpError, query: str) -> bool:
    """Handle HTTP errors from search API. Returns True if should break from query loop."""
    if error.resp.status == 403:
        logger.info(f"    Access denied (403) for query '{query}': {error.reason}")
        logger.info("    Check that Custom Search API is enabled and credentials are correct.")
        return True
    else:
        logger.info(f"    HTTP error for query '{query}': {error}")
        return False


def _format_search_results(search_results_items: list) -> list:
    """Format search results for analysis"""
    return [
        {
            "link": item.get("link"),
            "title": item.get("title"),
            "snippet": item.get("snippet"),
        }
        for item in search_results_items
    ]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutException, WebDriverException)),
    reraise=True,
)
def get_page_with_retry(driver_instance, url):
    """Wraps driver.get() with retry logic."""
    driver_instance.get(url)


def _initialize_blocking_data():
    """Initialize blocking detection data structure."""
    return {
        "is_blocked": False,
        "blocking_type": None,
        "blocking_evidence": {},
        "status_code": None,
        "robots_txt_check": {},
        "respectful_automation_used": True,
        "status_description": None,
    }


def _test_url_for_blocking(current_url, diocese_name, respectful_automation):
    """Test URL for blocking using respectful automation."""
    blocking_data = _initialize_blocking_data()

    if not respectful_automation:
        return blocking_data

    logger.info(f"  🤖 [{diocese_name}] Testing for blocking with respectful automation...")
    response, automation_info = respectful_automation.respectful_get(current_url, timeout=30)

    if response is None:
        # Request failed - could be blocking or other issue
        if automation_info.get("error") == "robots_txt_disallowed":
            logger.warning(f"  ⚠️ [{diocese_name}] Robots.txt disallows access")
            blocking_data.update(
                {
                    "is_blocked": True,
                    "blocking_type": "robots_txt_disallowed",
                    "status_description": ("Diocese website disallows automated access via robots.txt"),
                    "robots_txt_check": automation_info.get("robots_info", {}),
                    "blocking_evidence": {"robots_txt": automation_info.get("message", "Access disallowed")},
                }
            )
        else:
            logger.warning(f"  ❌ [{diocese_name}] Request failed: {automation_info.get('message', 'Unknown error')}")
            blocking_data.update(
                {
                    "status_description": (
                        f'Diocese website request failed: {automation_info.get("message", "Unknown error")}'
                    ),
                    "blocking_evidence": {"error": automation_info.get("message", "Request failed")},
                }
            )
    else:
        # Got a response - check for blocking
        block_info = automation_info.get("blocking_info", {})
        robots_info = automation_info.get("robots_info", {})

        blocking_data.update(
            {
                "is_blocked": block_info.get("is_blocked", False),
                "blocking_type": block_info.get("blocking_type"),
                "status_code": block_info.get("status_code"),
                "blocking_evidence": {
                    "evidence_list": block_info.get("evidence", []),
                    "headers": block_info.get("headers", {}),
                },
                "robots_txt_check": robots_info,
            }
        )

        if blocking_data["is_blocked"]:
            logger.warning(
                f"  🚫 [{diocese_name}] Blocking detected: {blocking_data['blocking_type']} (HTTP {blocking_data['status_code']})"
            )
            blocking_report = create_blocking_report(block_info, current_url, diocese_name)
            blocking_data["status_description"] = blocking_report.get(
                "status_description", "Diocese website blocking automated access"
            )
        else:
            logger.info(f"  ✅ [{diocese_name}] No blocking detected (HTTP {blocking_data['status_code']})")
            blocking_data["status_description"] = "Diocese website accessible to automated requests"

    return blocking_data


def _try_direct_page_analysis(worker_driver, current_url, diocese_name):
    """Try to find parish directory URL by analyzing the main diocese page."""
    parish_dir_url_found = None
    method = "not_found_all_stages"
    status_text = "Not Found"

    try:
        get_page_with_retry(worker_driver, current_url)
        # Wait for page to fully load
        WebDriverWait(worker_driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        page_source = worker_driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        candidate_links = find_candidate_urls(soup, current_url)

        if candidate_links:
            logger.info(f"🔍 [{diocese_name}] Found {len(candidate_links)} candidates from direct page. Analyzing...")
            parish_dir_url_found = analyze_links_with_genai(candidate_links, diocese_name)
            if parish_dir_url_found:
                method = "genai_direct_page_analysis"
                status_text = "Success"
            else:
                logger.info(f"⚠️ [{diocese_name}] GenAI (direct page) did not find a suitable URL.")
        else:
            logger.info(f"⚠️ [{diocese_name}] No candidate links found by direct page scan.")
    except Exception as e:
        logger.error(f"❌ [{diocese_name}] Error in direct page analysis: {e}")

    return parish_dir_url_found, method, status_text


def _try_search_engine_analysis(current_url, diocese_name):
    """Try to find parish directory URL using search engine results."""
    parish_dir_url_found = None
    method = "not_found_all_stages"
    status_text = "Not Found"

    try:
        search_query = (
            "site:" + current_url.replace("http://", "").replace("https://", "") + " parish directory churches mass times"
        )
        search_snippets = search_and_extract_urls(search_query)

        if search_snippets:
            logger.info(f"🔍 [{diocese_name}] Found {len(search_snippets)} search results. Analyzing with AI...")
            parish_dir_url_found = analyze_search_snippet_with_genai(search_snippets, diocese_name)
            if parish_dir_url_found:
                method = "search_engine_snippet_genai"
                status_text = "Success"
            else:
                logger.info(f"⚠️ [{diocese_name}] GenAI (search snippets) did not find a suitable URL.")
        else:
            logger.info(f"⚠️ [{diocese_name}] No search results found.")
    except Exception as e:
        logger.error(f"❌ [{diocese_name}] Error in search engine analysis: {e}")

    return parish_dir_url_found, method, status_text


def _create_upsert_data(
    current_diocese_id,
    current_url,
    parish_dir_url_found,
    status_text,
    method,
    blocking_data,
):
    """Create data structure for database upsert."""
    return {
        "diocese_id": current_diocese_id,
        "diocese_url": current_url,
        "parish_directory_url": parish_dir_url_found,
        "found": status_text,
        "found_method": method,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        # Blocking detection fields (will be ignored if columns don't exist yet)
        "is_blocked": blocking_data["is_blocked"],
        "blocking_type": blocking_data["blocking_type"],
        "blocking_evidence": blocking_data["blocking_evidence"],
        "status_code": blocking_data["status_code"],
        "robots_txt_check": blocking_data["robots_txt_check"],
        "respectful_automation_used": blocking_data["respectful_automation_used"],
        "status_description": blocking_data["status_description"],
    }


def _handle_retry_error(e, diocese_name, current_diocese_id, current_url, blocking_data):
    """Handle RetryError exceptions during processing."""
    error_message = str(e).replace('"', "''")
    error_msg = f"Page load failed after multiple retries: {error_message[:100]}"
    logger.error(f"❌ [{diocese_name}] {error_msg}")

    status_text = f"Error: Page load failed - {error_message[:60]}"
    method = "error_page_load_failed"
    data_to_upsert = _create_upsert_data(current_diocese_id, current_url, None, status_text, method, blocking_data)
    batch_upsert_parish_directory(data_to_upsert, current_url)
    return error_msg


def _handle_general_error(e, diocese_name, current_diocese_id, current_url, blocking_data):
    """Handle general exceptions during processing."""
    error_message = str(e).replace('"', "''")
    error_msg = f"General error processing: {error_message[:100]}"
    logger.error(f"❌ [{diocese_name}] {error_msg}")

    # Attempt WebDriver recovery if it's a connection issue
    if "HTTPConnectionPool" in error_message or "Connection refused" in error_message:
        logger.warning(f"🔄 [{diocese_name}] Attempting WebDriver recovery due to connection error...")
        try:
            recovered_driver = recover_driver()
            if recovered_driver:
                logger.info(f"✅ [{diocese_name}] WebDriver recovered successfully")
                # Update the driver for this process
            else:
                logger.error(f"❌ [{diocese_name}] WebDriver recovery failed")
        except Exception as recovery_error:
            logger.error(f"❌ [{diocese_name}] WebDriver recovery error: {recovery_error}")

    status_text = f"Error: {error_message[:100]}"
    method = "error_processing_general"
    data_to_upsert = _create_upsert_data(current_diocese_id, current_url, None, status_text, method, blocking_data)
    batch_upsert_parish_directory(data_to_upsert, current_url)
    return error_msg


def process_single_diocese(diocese_info):
    """
    Process a single diocese in isolation with its own WebDriver instance.
    This function is designed to be thread - safe for parallel processing.

    Args:
        diocese_info: Dictionary containing diocese information (id, url, name)

    Returns:
        String describing the processing result
    """
    current_url = diocese_info["url"]
    diocese_name = diocese_info["name"]
    current_diocese_id = diocese_info["id"]

    # Get respectful automation instance
    respectful_automation = get_respectful_automation()

    logger.info(f"🔄 [{diocese_name}] Starting respectful processing...")

    # First, test the URL for blocking using respectful automation
    blocking_data = _test_url_for_blocking(current_url, diocese_name, respectful_automation)

    # Each worker gets its own WebDriver instance with recovery support
    worker_driver = ensure_driver_available()
    if not worker_driver:
        error_msg = f"Failed to setup WebDriver for {diocese_name}"
        logger.error(error_msg)
        return error_msg

    try:
        # Try direct page analysis first
        parish_dir_url_found, method, status_text = _try_direct_page_analysis(worker_driver, current_url, diocese_name)

        # If direct page analysis fails, try search engine analysis
        if not parish_dir_url_found:
            parish_dir_url_found, method, status_text = _try_search_engine_analysis(current_url, diocese_name)

        # Log final result
        if parish_dir_url_found:
            result_msg = f"SUCCESS - {parish_dir_url_found} (method: {method})"
            logger.info(f"✅ [{diocese_name}] Result: {result_msg}")
        else:
            result_msg = "NOT FOUND after trying all methods"
            logger.info(f"❌ [{diocese_name}] Result: {result_msg}")

        # Prepare data for batch upsert including blocking detection
        data_to_upsert = _create_upsert_data(
            current_diocese_id,
            current_url,
            parish_dir_url_found,
            status_text,
            method,
            blocking_data,
        )
        batch_upsert_parish_directory(data_to_upsert, current_url)

        return result_msg

    except RetryError as e:
        return _handle_retry_error(e, diocese_name, current_diocese_id, current_url, blocking_data)

    except Exception as e:
        return _handle_general_error(e, diocese_name, current_diocese_id, current_url, blocking_data)

    finally:
        # Always clean up the worker's WebDriver
        if worker_driver:
            try:
                worker_driver.quit()
            except Exception as cleanup_error:
                logger.warning(f"⚠️ [{diocese_name}] WebDriver cleanup error: {str(cleanup_error)}")


def _configure_genai():
    """Configure GenAI API if available"""
    if config.GENAI_API_KEY:
        try:
            genai.configure(api_key=config.GENAI_API_KEY)
            logger.info("GenAI configured successfully.")
        except Exception as e:
            logger.info(f"Error configuring GenAI with key: {e}. GenAI features will be mocked.")
    else:
        logger.info("GenAI API Key is not set. GenAI features will be mocked globally.")


def _initialize_batch_manager(supabase):
    """Initialize global batch manager for database operations"""
    global _batch_manager
    _batch_manager = get_batch_manager(supabase, batch_size=20)
    _batch_manager.configure_table("DiocesesParishDirectory", "diocese_id")


def _initialize_respectful_automation():
    """Initialize global respectful automation instance"""
    global _respectful_automation
    _respectful_automation = RespectfulAutomation()
    logger.info("Respectful automation initialized successfully.")


def _fetch_all_dioceses(supabase, diocese_id):
    """Fetch dioceses from database with optional filtering"""
    query = supabase.table("Dioceses").select("id, Website, Name")

    if diocese_id:
        query = query.eq("id", diocese_id)

    response_dioceses = query.execute()
    all_dioceses_list = response_dioceses.data if response_dioceses.data else []
    logger.info(f"Fetched {len(all_dioceses_list)} total records from Dioceses table.")

    return all_dioceses_list


def _get_unprocessed_dioceses_urls(supabase, all_dioceses_list, max_dioceses_to_process):
    """Get URLs of unprocessed dioceses"""
    diocese_url_to_name = {d["Website"]: d["Name"] for d in all_dioceses_list}
    response_processed_dioceses = supabase.table("DiocesesParishDirectory").select("diocese_url").execute()
    processed_diocese_urls = (
        {item["diocese_url"] for item in response_processed_dioceses.data}
        if response_processed_dioceses.data is not None
        else set()
    )
    unprocessed_dioceses_urls = set(diocese_url_to_name.keys()) - processed_diocese_urls

    if unprocessed_dioceses_urls:
        logger.info(f"Found {len(unprocessed_dioceses_urls)} dioceses needing parish directory URLs.")
        limit = max_dioceses_to_process if max_dioceses_to_process != 0 else len(unprocessed_dioceses_urls)
        actual_limit = min(limit, len(unprocessed_dioceses_urls))
        return random.sample(list(unprocessed_dioceses_urls), actual_limit)

    return []


def _get_oldest_scanned_dioceses_urls(supabase, max_dioceses_to_process):
    """Get URLs of oldest scanned dioceses for rescanning"""
    logger.info("All dioceses have been scanned. Rescanning the oldest entries based on 'updated_at'.")
    limit = max_dioceses_to_process if max_dioceses_to_process != 0 else 5
    response_oldest_scanned = (
        supabase.table("DiocesesParishDirectory").select("diocese_url").order("updated_at", desc=False).limit(limit).execute()
    )

    if response_oldest_scanned.data:
        dioceses_urls = [item["diocese_url"] for item in response_oldest_scanned.data]
        logger.info(f"Selected {len(dioceses_urls)} oldest dioceses for rescanning.")
        return dioceses_urls
    else:
        logger.info("Could not find any previously scanned dioceses to rescan.")
        return []


def _determine_dioceses_to_scan_urls(supabase, all_dioceses_list, diocese_id, max_dioceses_to_process):
    """Determine which diocese URLs need to be scanned"""
    if diocese_id:
        # If a specific diocese is provided, scan it regardless of previous processing
        return [d["Website"] for d in all_dioceses_list if d.get("Website")]
    else:
        # Logic to find unprocessed or outdated dioceses
        unprocessed_urls = _get_unprocessed_dioceses_urls(supabase, all_dioceses_list, max_dioceses_to_process)
        if unprocessed_urls:
            return unprocessed_urls
        else:
            return _get_oldest_scanned_dioceses_urls(supabase, max_dioceses_to_process)


def _build_dioceses_to_scan_list(all_dioceses_list, dioceses_to_scan_urls):
    """Build final list of diocese objects to scan"""
    return [
        {"id": d["id"], "url": d["Website"], "name": d["Name"]}
        for d in all_dioceses_list
        if d.get("Website") in dioceses_to_scan_urls
    ]


def _calculate_optimal_workers(dioceses_count):
    """Calculate optimal number of workers for parallel processing"""
    return min(4, max(1, dioceses_count // 2))


def _process_dioceses_parallel(dioceses_to_scan):
    """Process dioceses in parallel using ThreadPoolExecutor"""
    num_workers = _calculate_optimal_workers(len(dioceses_to_scan))
    logger.info(f"🚀 Using {num_workers} parallel workers for diocese processing")

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Submit all diocese processing tasks
        future_to_diocese = {
            executor.submit(process_single_diocese, diocese_info): diocese_info for diocese_info in dioceses_to_scan
        }

        # Process completed tasks as they finish
        completed_count = 0
        for future in as_completed(future_to_diocese):
            diocese_info = future_to_diocese[future]
            completed_count += 1
            try:
                result = future.result()
                logger.info(
                    f"✅ [{completed_count}/{len(dioceses_to_scan)}] Completed processing {diocese_info['name']}: {result}"
                )
            except Exception as e:
                logger.error(
                    f"❌ [{completed_count}/{len(dioceses_to_scan)}] Failed processing {diocese_info['name']}: {str(e)}"
                )


def _finalize_batch_operations():
    """Flush remaining batched records and log statistics"""
    if _batch_manager:
        _batch_manager.flush_all()
        stats = _batch_manager.get_stats()
        logger.info(f"📊 Batch operations summary: {stats}")


def find_parish_directories(diocese_id=None, max_dioceses_to_process=config.DEFAULT_MAX_DIOCESES):
    """Main function to run the parish directory finder with parallel processing."""

    # Configure dependencies
    _configure_genai()

    supabase = get_supabase_client()
    if not supabase:
        return

    _initialize_batch_manager(supabase)
    _initialize_respectful_automation()

    # Determine dioceses to scan
    dioceses_to_scan = []
    try:
        all_dioceses_list = _fetch_all_dioceses(supabase, diocese_id)

        if not all_dioceses_list:
            logger.info("No dioceses found to process.")
            return

        dioceses_to_scan_urls = _determine_dioceses_to_scan_urls(
            supabase, all_dioceses_list, diocese_id, max_dioceses_to_process
        )

        dioceses_to_scan = _build_dioceses_to_scan_list(all_dioceses_list, dioceses_to_scan_urls)

    except Exception as e:
        logger.info(f"Error during Supabase data operations: {e}")
        dioceses_to_scan = []

    if not dioceses_to_scan:
        logger.info("No dioceses to scan.")
        return

    # Process dioceses in parallel
    logger.info(f"Processing {len(dioceses_to_scan)} dioceses with parallel Selenium instances...")
    _process_dioceses_parallel(dioceses_to_scan)

    # Finalize operations
    _finalize_batch_operations()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find parish directory URLs on diocesan websites.")
    parser.add_argument(
        "--diocese_id",
        type=int,
        default=None,
        help="ID of a specific diocese to process. If not provided, processes all.",
    )
    parser.add_argument(
        "--max_dioceses_to_process",
        type=int,
        default=20,
        help="Maximum number of dioceses to process. Set to 0 for no limit. Defaults to 20.",
    )
    args = parser.parse_args()

    config.validate_config()
    find_parish_directories(args.diocese_id, args.max_dioceses_to_process)
