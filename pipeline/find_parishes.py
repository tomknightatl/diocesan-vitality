#!/usr/bin/env python
# coding: utf-8

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
from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from pipeline import config
from core.db import get_supabase_client
from core.db_batch_operations import get_batch_manager
from core.driver import close_driver, ensure_driver_available, recover_driver, setup_driver
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
    global _batch_manager
    return _batch_manager


def get_respectful_automation():
    """Get the current respectful automation instance."""
    global _respectful_automation
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
        r"parish-finder",
        r"findachurch",
        r"parishsearch",
        r"parishdirectory",
        r"find-a-church",
        r"church-directory",
        r"parish-listings",
        r"parish-map",
        r"mass-times",
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
    model = genai.GenerativeModel("gemini-1.5-flash")
    return model.generate_content(prompt)


async def _invoke_genai_model_async(prompt):
    """Async wrapper for GenAI model invocation."""
    loop = asyncio.get_event_loop()
    try:
        # Run the sync GenAI call in a thread pool to avoid blocking the event loop
        response = await loop.run_in_executor(None, _invoke_genai_model_with_retry, prompt)
        return response
    except Exception as e:
        # Re-raise the exception to maintain the same error handling
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
    best_link_found = None
    highest_score = -1
    current_use_mock_direct = use_mock_genai_direct_page if config.GENAI_API_KEY else True

    if not current_use_mock_direct:
        logger.info(
            f"Attempting LIVE GenAI analysis (CONCURRENT) for {len(candidate_links)} direct page links for {diocese_name or 'Unknown Diocese'}."
        )

        # Create concurrent tasks for all links
        tasks = [_analyze_single_link_async(link_info, diocese_name) for link_info in candidate_links]

        # Execute all tasks concurrently with a reasonable semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent GenAI calls

        async def analyze_with_semaphore(task):
            async with semaphore:
                return await task

        # Wait for all tasks to complete
        results = await asyncio.gather(*[analyze_with_semaphore(task) for task in tasks], return_exceptions=True)

        # Find the best result
        for result in results:
            if isinstance(result, dict) and result.get("score", 0) >= 7:
                if result["score"] > highest_score:
                    highest_score = result["score"]
                    best_link_found = result["href"]

        return best_link_found

    # Mock implementation (unchanged)
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
    for link_info in candidate_links:
        current_score = 0
        text_to_check = (link_info["text"] + " " + link_info["href"] + " " + link_info["surrounding_text"]).lower()
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
    best_link_found = None
    highest_score = -1
    current_use_mock_direct = use_mock_genai_direct_page if config.GENAI_API_KEY else True
    if not current_use_mock_direct:
        logger.info(
            f"Attempting LIVE GenAI analysis for {len(candidate_links)} direct page links for {diocese_name or 'Unknown Diocese'}."
        )
    if current_use_mock_direct:
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
        for link_info in candidate_links:
            current_score = 0
            text_to_check = (link_info["text"] + " " + link_info["href"] + " " + link_info["surrounding_text"]).lower()
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
            logger.info(f"    GenAI API call (Direct Link) failed after multiple retries for {link_info['href']}: {e}")
        except Exception as e:
            logger.info(f"    Error calling GenAI (Direct Link) for {link_info['href']}: {e}. No score assigned.")
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
    best_link_from_snippet = None
    highest_score = -1
    current_use_mock_snippet = use_mock_genai_snippet if config.GENAI_API_KEY else True

    if not current_use_mock_snippet:
        logger.info(f"Attempting LIVE GenAI analysis (CONCURRENT) for {len(search_results)} snippets for {diocese_name}.")

        # Create concurrent tasks for all search results
        tasks = [_analyze_single_snippet_async(result, diocese_name) for result in search_results]

        # Execute all tasks concurrently with a semaphore
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent GenAI calls for snippets

        async def analyze_with_semaphore(task):
            async with semaphore:
                return await task

        # Wait for all tasks to complete
        results = await asyncio.gather(*[analyze_with_semaphore(task) for task in tasks], return_exceptions=True)

        # Find the best result
        for result in results:
            if isinstance(result, dict) and result.get("score", 0) >= 7:
                if result["score"] > highest_score:
                    highest_score = result["score"]
                    best_link_from_snippet = result["link"]

        return best_link_from_snippet

    # Mock implementation (unchanged)
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
    for result in search_results:
        current_score = 0
        text_to_check = (result.get("title", "") + " " + result.get("snippet", "") + " " + result.get("link", "")).lower()
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
    best_link_from_snippet = None
    highest_score = -1
    current_use_mock_snippet = use_mock_genai_snippet if config.GENAI_API_KEY else True
    if not current_use_mock_snippet:
        logger.info(f"Attempting LIVE GenAI analysis for {len(search_results)} snippets for {diocese_name}.")
    if current_use_mock_snippet:
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
        for result in search_results:
            current_score = 0
            text_to_check = (result.get("title", "") + " " + result.get("snippet", "") + " " + result.get("link", "")).lower()
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
            logger.info(f"    GenAI API call (Snippet) for {link} failed after multiple retries: {e}")
        except Exception as e:
            logger.info(f"    Error calling GenAI for snippet analysis of {link}: {e}")
    return best_link_from_snippet


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
                    "snippet": "Directory of parishes and churches in the diocese. Find mass times and locations.",
                },
                {
                    "link": f"{base_url.rstrip('/')}/directory",
                    "title": "Parish Directory",
                    "snippet": "Official directory of Catholic parishes, churches, and missions.",
                },
                {
                    "link": f"{base_url.rstrip('/')}/find-a-parish",
                    "title": "Find a Parish",
                    "snippet": "Search for a Catholic parish or church near you. Mass schedules and contact information.",
                },
                {
                    "link": f"{base_url.rstrip('/')}/our-church",
                    "title": "Our Churches",
                    "snippet": "List of churches and parishes in our diocese with mass times and directions.",
                },
            ]
            return mock_results

        # Fallback for non-site searches
        return []

    except Exception as e:
        logger.error(f"Error in search_and_extract_urls: {e}")
        return []


def search_for_directory_link(diocese_name, diocese_website_url):
    """Uses Google Custom Search (or mock) to find potential directory links, then analyzes snippets."""
    current_use_mock_search = use_mock_search_engine if (config.SEARCH_API_KEY and config.SEARCH_CX) else True
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
        filtered_mock_results = [res for res in mock_results if res["link"].startswith(diocese_website_url.rstrip("/"))]
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
                # Brief pause between API calls to be respectful
                time.sleep(0.1)  # Reduced from 0.2 to 0.1
            except RetryError as e:
                logger.info(f"    Search API call failed after retries for query '{q}': {e}")
                continue
            except HttpError as e:
                if e.resp.status == 403:
                    logger.info(f"    Access denied (403) for query '{q}': {e.reason}")
                    logger.info("    Check that Custom Search API is enabled and credentials are correct.")
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


def process_single_diocese(diocese_info):
    """
    Process a single diocese in isolation with its own WebDriver instance.
    This function is designed to be thread-safe for parallel processing.

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

    # Initialize blocking detection data
    blocking_data = {
        "is_blocked": False,
        "blocking_type": None,
        "blocking_evidence": {},
        "status_code": None,
        "robots_txt_check": {},
        "respectful_automation_used": True,
        "status_description": None,
    }

    logger.info(f"🔄 [{diocese_name}] Starting respectful processing...")

    # First, test the URL for blocking using respectful automation
    if respectful_automation:
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
                        "status_description": "Diocese website disallows automated access via robots.txt",
                        "robots_txt_check": automation_info.get("robots_info", {}),
                        "blocking_evidence": {"robots_txt": automation_info.get("message", "Access disallowed")},
                    }
                )
            else:
                logger.warning(f"  ❌ [{diocese_name}] Request failed: {automation_info.get('message', 'Unknown error')}")
                blocking_data.update(
                    {
                        "status_description": f'Diocese website request failed: {automation_info.get("message", "Unknown error")}',
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

    # Each worker gets its own WebDriver instance with recovery support
    worker_driver = ensure_driver_available()
    if not worker_driver:
        error_msg = f"Failed to setup WebDriver for {diocese_name}"
        logger.error(error_msg)
        return error_msg

    try:
        parish_dir_url_found = None
        status_text = "Not Found"
        method = "not_found_all_stages"

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

            if not parish_dir_url_found:
                search_query = (
                    "site:"
                    + current_url.replace("http://", "").replace("https://", "")
                    + " parish directory churches mass times"
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

            # Log final result
            if parish_dir_url_found:
                result_msg = f"SUCCESS - {parish_dir_url_found} (method: {method})"
                logger.info(f"✅ [{diocese_name}] Result: {result_msg}")
            else:
                result_msg = f"NOT FOUND after trying all methods"
                logger.info(f"❌ [{diocese_name}] Result: {result_msg}")

            # Prepare data for batch upsert including blocking detection
            data_to_upsert = {
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
            batch_upsert_parish_directory(data_to_upsert, current_url)

            return result_msg

        except RetryError as e:
            error_message = str(e).replace('"', "''")
            error_msg = f"Page load failed after multiple retries: {error_message[:100]}"
            logger.error(f"❌ [{diocese_name}] {error_msg}")

            status_text = f"Error: Page load failed - {error_message[:60]}"
            method = "error_page_load_failed"
            data_to_upsert = {
                "diocese_id": current_diocese_id,
                "diocese_url": current_url,
                "parish_directory_url": None,
                "found": status_text,
                "found_method": method,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                # Blocking detection fields
                "is_blocked": blocking_data["is_blocked"],
                "blocking_type": blocking_data["blocking_type"],
                "blocking_evidence": blocking_data["blocking_evidence"],
                "status_code": blocking_data["status_code"],
                "robots_txt_check": blocking_data["robots_txt_check"],
                "respectful_automation_used": blocking_data["respectful_automation_used"],
                "status_description": blocking_data["status_description"],
            }
            batch_upsert_parish_directory(data_to_upsert, current_url)
            return error_msg

        except Exception as e:
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
                        driver = recovered_driver
                    else:
                        logger.error(f"❌ [{diocese_name}] WebDriver recovery failed")
                except Exception as recovery_error:
                    logger.error(f"❌ [{diocese_name}] WebDriver recovery error: {recovery_error}")

            status_text = f"Error: {error_message[:100]}"
            method = "error_processing_general"
            data_to_upsert = {
                "diocese_id": current_diocese_id,
                "diocese_url": current_url,
                "parish_directory_url": None,
                "found": status_text,
                "found_method": method,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                # Blocking detection fields
                "is_blocked": blocking_data["is_blocked"],
                "blocking_type": blocking_data["blocking_type"],
                "blocking_evidence": blocking_data["blocking_evidence"],
                "status_code": blocking_data["status_code"],
                "robots_txt_check": blocking_data["robots_txt_check"],
                "respectful_automation_used": blocking_data["respectful_automation_used"],
                "status_description": blocking_data["status_description"],
            }
            batch_upsert_parish_directory(data_to_upsert, current_url)
            return error_msg

    finally:
        # Always clean up the worker's WebDriver
        if worker_driver:
            try:
                worker_driver.quit()
            except Exception as cleanup_error:
                logger.warning(f"⚠️ [{diocese_name}] WebDriver cleanup error: {str(cleanup_error)}")


def find_parish_directories(diocese_id=None, max_dioceses_to_process=config.DEFAULT_MAX_DIOCESES):
    """Main function to run the parish directory finder with parallel processing."""

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

    # Initialize batch manager for efficient database operations
    global _batch_manager
    _batch_manager = get_batch_manager(supabase, batch_size=20)
    _batch_manager.configure_table("DiocesesParishDirectory", "diocese_id")

    # Initialize respectful automation
    global _respectful_automation
    _respectful_automation = RespectfulAutomation()
    logger.info("Respectful automation initialized successfully.")

    dioceses_to_scan = []
    try:
        # Base query for all dioceses
        query = supabase.table("Dioceses").select("id, Website, Name")

        # Filter by a single diocese if an ID is provided
        if diocese_id:
            query = query.eq("id", diocese_id)

        response_dioceses = query.execute()
        all_dioceses_list = response_dioceses.data if response_dioceses.data else []
        logger.info(f"Fetched {len(all_dioceses_list)} total records from Dioceses table.")

        if not all_dioceses_list:
            logger.info("No dioceses found to process.")
            return

        dioceses_to_scan_urls = []
        # If a specific diocese is provided, we scan it regardless of whether it was processed before.
        if diocese_id:
            dioceses_to_scan_urls = [d["Website"] for d in all_dioceses_list if d.get("Website")]
        else:
            # Logic to find unprocessed or outdated dioceses if no specific one is targeted
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
                # Fix: Ensure limit doesn't exceed available dioceses
                actual_limit = min(limit, len(unprocessed_dioceses_urls))
                dioceses_to_scan_urls = random.sample(list(unprocessed_dioceses_urls), actual_limit)
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
            {"id": d["id"], "url": d["Website"], "name": d["Name"]}
            for d in all_dioceses_list
            if d.get("Website") in dioceses_to_scan_urls
        ]

    except Exception as e:
        logger.info(f"Error during Supabase data operations: {e}")
        dioceses_to_scan = []

    if not dioceses_to_scan:
        logger.info("No dioceses to scan.")
        return

    # Skip the global driver setup since each worker will have its own
    logger.info(f"Processing {len(dioceses_to_scan)} dioceses with parallel Selenium instances...")

    # Determine optimal number of workers (max 4 to avoid resource exhaustion)
    num_workers = min(4, max(1, len(dioceses_to_scan) // 2))
    logger.info(f"🚀 Using {num_workers} parallel workers for diocese processing")

    # Process dioceses in parallel using ThreadPoolExecutor
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

    # All processing is now handled by parallel workers above

    # Flush any remaining batched records
    if _batch_manager:
        _batch_manager.flush_all()
        stats = _batch_manager.get_stats()
        logger.info(f"📊 Batch operations summary: {stats}")

    # No need to close a global driver since each worker manages its own WebDriver


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
