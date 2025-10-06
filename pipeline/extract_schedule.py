#!/usr/bin/env python
# coding: utf-8

import argparse
import heapq
import random
import re
import time
import warnings
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from bs4.element import Tag
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pipeline import config
from core.db import get_supabase_client  # Import the get_supabase_client function
from core.enhanced_url_manager import get_enhanced_url_manager
from core.intelligent_parish_prioritizer import get_intelligent_parish_prioritizer
from core.logger import get_logger
from core.monitoring_client import MonitoringClient
from core.schedule_ai_extractor import ScheduleAIExtractor, save_ai_schedule_results
from core.schedule_keywords import get_all_keywords_for_priority_calculation, load_keywords_from_database
from core.stealth_browser import get_stealth_browser
from core.url_visit_tracker import VisitTracker, get_url_visit_tracker
from core.utils import normalize_url  # Import normalize_url
from supabase import Client

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logger = get_logger(__name__)

_sitemap_cache = {}

# List of realistic user agents to rotate between
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
]


def get_resilient_session() -> requests.Session:
    """Create a resilient HTTP session with bot detection avoidance."""
    # Configure retry strategy with more aggressive settings for blocked requests
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,  # Increased backoff
        status_forcelist=[403, 429, 500, 502, 503, 504],  # Added 403 for bot detection
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Set a random user agent
    session.headers.update(
        {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
    )

    return session


def make_request_with_delay(session: requests.Session, url: str, **kwargs) -> requests.Response:
    """Make a request with random delay and stealth browser fallback for blocked requests."""
    # Add random delay between requests (0.5 to 2 seconds)
    delay = random.uniform(0.5, 2.0)
    time.sleep(delay)

    # Rotate user agent for this request
    session.headers.update({"User-Agent": random.choice(USER_AGENTS)})

    try:
        response = session.get(url, **kwargs)

        # Check for severe bot detection (persistent 403s despite retries)
        if response.status_code == 403:
            # Check if this might be a site-wide bot block
            domain = urlparse(url).netloc
            if "too many 403 error responses" in str(kwargs.get("_last_error", "")):
                logger.warning(f"Detected severe bot blocking for {domain}, attempting stealth browser fallback")

                # Try stealth browser as fallback
                stealth_browser = get_stealth_browser()
                if stealth_browser.is_available:
                    content = stealth_browser.get_page_content(url, timeout=30)
                    if content:
                        # Create mock response object for compatibility
                        mock_response = type(
                            "MockResponse",
                            (),
                            {
                                "status_code": 200,
                                "content": content.encode(),
                                "text": content,
                                "headers": {"content-type": "text/html"},
                                "raise_for_status": lambda self: None,
                                "url": url,
                            },
                        )()
                        logger.info(f"Successfully retrieved {url} using stealth browser")
                        return mock_response

        return response

    except requests.exceptions.RequestException as e:
        # Check if this is a persistent bot detection issue
        if "403" in str(e) and "too many" in str(e).lower():
            logger.warning(f"Persistent 403 errors for {url}, attempting stealth browser fallback")

            # Try stealth browser as fallback
            stealth_browser = get_stealth_browser()
            if stealth_browser.is_available:
                content = stealth_browser.get_page_content(url, timeout=30)
                if content:
                    # Create mock response object for compatibility
                    mock_response = type(
                        "MockResponse",
                        (),
                        {
                            "status_code": 200,
                            "content": content.encode(),
                            "text": content,
                            "headers": {"content-type": "text/html"},
                            "raise_for_status": lambda self: None,
                            "url": url,
                        },
                    )()
                    logger.info(f"Successfully retrieved {url} using stealth browser")
                    return mock_response

        # Re-raise the original exception if stealth browser can't help
        raise


# Create a global resilient session
requests_session = get_resilient_session()

# Global AI extractor instance
_ai_extractor = None


def get_ai_extractor() -> ScheduleAIExtractor:
    """Get or create the global AI extractor instance."""
    global _ai_extractor
    if _ai_extractor is None:
        _ai_extractor = ScheduleAIExtractor()
    return _ai_extractor


def get_suppression_urls(supabase: Client) -> set[str]:
    """Fetches all URLs from the ParishFactsSuppressionURLs table."""
    try:
        response = supabase.table("parishfactssuppressionurls").select("url").execute()
        if response.data:
            return {normalize_url(item["url"]) for item in response.data}
        return set()
    except Exception as e:
        logger.error(f"Error fetching suppression URLs: {e}")
        return set()


def get_common_schedule_paths(base_url: str) -> list[str]:
    """Generate common schedule page paths for a parish website."""
    common_paths = [
        "/schedules",
        "/schedule",
        "/confession",
        "/confessions",
        "/reconciliation",
        "/adoration",
        "/eucharistic-adoration",
        "/sacraments",
        "/mass-times",
        "/worship",
        "/hours",
        "/spiritual-life",
        "/prayer",
        "/devotions",
        "/holy-hour",
        "/blessed-sacrament",
        "/penance",
        "/services",
        "/liturgy",
        "/parish-life",
        "/faith-formation",
        "/ministries",
    ]

    # Generate full URLs
    schedule_urls = []
    for path in common_paths:
        full_url = urljoin(base_url.rstrip("/"), path)
        schedule_urls.append(full_url)

    return schedule_urls


def get_navigation_links(url: str) -> list[str]:
    """Extract navigation links from the main page when sitemaps fail."""
    try:
        response = make_request_with_delay(requests_session, url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Look for navigation elements
        nav_links = []

        # Find navigation menus
        nav_selectors = [
            "nav a",
            "header nav a",
            ".nav a",
            ".navigation a",
            ".menu a",
            ".main-menu a",
            "#menu a",
            "#nav a",
            "ul.menu a",
            "ul.nav a",
            ".navbar a",
            ".site-nav a",
            "footer a",  # Footer links often contain schedule pages
        ]

        for selector in nav_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get("href")
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith("/"):
                        full_url = urljoin(url, href)
                    elif href.startswith(("http://", "https://")):
                        full_url = href
                    else:
                        continue  # Skip non-URL links like mailto:, tel:, etc.

                    # Filter for potentially relevant links
                    link_text = link.get_text().lower()
                    href_lower = href.lower()

                    relevant_terms = [
                        "schedule",
                        "confession",
                        "reconciliation",
                        "adoration",
                        "sacrament",
                        "mass",
                        "worship",
                        "prayer",
                        "spiritual",
                        "devotion",
                        "penance",
                        "blessed",
                        "eucharistic",
                        "holy",
                        "service",
                        "liturgy",
                        "ministry",
                    ]

                    if any(term in link_text or term in href_lower for term in relevant_terms):
                        nav_links.append(full_url)

        # Remove duplicates while preserving order
        unique_links = []
        seen = set()
        for link in nav_links:
            if link not in seen:
                unique_links.append(link)
                seen.add(link)

        return unique_links[:20]  # Limit to prevent excessive requests

    except Exception as e:
        logger.warning(f"Could not extract navigation links from {url}: {e}")
        return []


def get_robots_txt_hints(url: str) -> list[str]:
    """Extract potential URL hints from robots.txt file."""
    robots_urls = []
    try:
        robots_url = urljoin(url, "/robots.txt")
        response = make_request_with_delay(requests_session, robots_url, timeout=5)
        response.raise_for_status()

        # Parse robots.txt for Sitemap directives and disallowed paths that might contain schedules
        content = response.text

        for line in content.splitlines():
            line = line.strip()
            if line.startswith("Sitemap:"):
                sitemap_url = line.split(":", 1)[1].strip()
                if sitemap_url.startswith(("http://", "https://")):
                    robots_urls.append(sitemap_url)
            elif line.startswith("Disallow:"):
                # Sometimes robots.txt blocks schedule pages - might give us hints
                disallow_path = line.split(":", 1)[1].strip()
                if any(term in disallow_path.lower() for term in ["schedule", "confession", "adoration", "mass"]):
                    full_url = urljoin(url, disallow_path)
                    robots_urls.append(full_url)

    except Exception as e:
        logger.debug(f"Could not parse robots.txt for {url}: {e}")

    return robots_urls


def is_relevant_url(discovered_url: str, base_url: str) -> bool:
    """Filter URLs to ensure they're relevant and from the same domain."""
    try:
        base_domain = urlparse(base_url).netloc
        discovered_domain = urlparse(discovered_url).netloc

        # Must be from same domain
        if base_domain != discovered_domain:
            return False

        url_lower = discovered_url.lower()

        # Skip non-content URLs
        exclude_patterns = [
            "/wp-content/",
            "/wp-admin/",
            "/admin/",
            "/login/",
            "/logout/",
            "/search/",
            "/feed/",
            "/rss/",
            "/api/",
            "/ajax/",
            "/json/",
            ".css",
            ".js",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".pdf",
            ".zip",
            ".doc",
            ".docx",
            ".xlsx",
            ".ppt",
            ".pptx",
            "/donate/",
            "/giving/",
            "/pledge/",
            "/payment/",
            "/shop/",
            "mailto:",
            "tel:",
            "javascript:",
            "#",
            "?",
        ]

        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        # Prefer URLs that likely contain schedule content
        include_patterns = [
            "schedule",
            "confession",
            "reconciliation",
            "adoration",
            "sacrament",
            "mass",
            "worship",
            "prayer",
            "spiritual",
            "devotion",
            "penance",
            "blessed",
            "eucharistic",
            "holy",
            "service",
            "liturgy",
            "ministry",
            "parish-life",
            "about",
        ]

        # If it matches include patterns, definitely keep it
        if any(pattern in url_lower for pattern in include_patterns):
            return True

        # For other URLs, be more conservative
        # Allow general navigation pages that might link to schedules
        if len(discovered_url.split("/")) <= 5:  # Not too deep in site structure
            return True

        return False

    except Exception:
        return False


def get_sitemap_urls(url: str) -> list[str]:
    """Fetches sitemap.xml and extracts URLs. Falls back to navigation parsing if sitemap fails."""
    normalized_url = normalize_url(url)  # Normalize URL for consistent caching key
    if normalized_url in _sitemap_cache:
        logger.debug(f"Returning sitemap from cache for {url}")
        return _sitemap_cache[normalized_url]

    # Try multiple sitemap locations and formats
    sitemap_locations = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemaps.xml",
        "/sitemap/sitemap.xml",
        "/wp-sitemap.xml",  # WordPress default
        "/site-map.xml",
        "/sitemap1.xml",
    ]

    for sitemap_path in sitemap_locations:
        try:
            sitemap_url = urljoin(url, sitemap_path)
            response = make_request_with_delay(requests_session, sitemap_url, timeout=10)
            response.raise_for_status()

            # Try XML parsing first
            soup = BeautifulSoup(response.content, "xml")
            urls_found = [
                loc.text for loc in soup.find_all("loc") if loc.text and loc.text.startswith(("http://", "https://"))
            ]

            # If XML parsing didn't work, try HTML parsing
            if not urls_found:
                soup = BeautifulSoup(response.content, "html.parser")
                urls_found = [
                    loc.text for loc in soup.find_all("loc") if loc.text and loc.text.startswith(("http://", "https://"))
                ]

            # Check for sitemap index files (contain links to other sitemaps)
            sitemap_links = [
                loc.text
                for loc in soup.find_all("loc")
                if loc.text and "sitemap" in loc.text.lower() and loc.text.startswith(("http://", "https://"))
            ]

            # If we found sitemap links, fetch those too
            for sitemap_link in sitemap_links[:5]:  # Limit to prevent infinite recursion
                try:
                    sub_response = make_request_with_delay(requests_session, sitemap_link, timeout=10)
                    sub_response.raise_for_status()
                    sub_soup = BeautifulSoup(sub_response.content, "xml")
                    sub_urls = [
                        loc.text
                        for loc in sub_soup.find_all("loc")
                        if loc.text and loc.text.startswith(("http://", "https://"))
                    ]
                    urls_found.extend(sub_urls)
                except Exception as sub_e:
                    logger.debug(f"Failed to fetch sub-sitemap {sitemap_link}: {sub_e}")
                    continue

            if urls_found:
                # Filter out unwanted URLs
                filtered_urls = [
                    u
                    for u in urls_found
                    if not any(
                        exclude in u.lower() for exclude in ["default", "template", "admin", "wp-content", "attachment"]
                    )
                ]
                logger.debug(f"Found {len(filtered_urls)} URLs in sitemap {sitemap_path} for {url}")
                _sitemap_cache[normalized_url] = filtered_urls
                return filtered_urls

        except requests.exceptions.RequestException as e:
            logger.debug(f"Could not fetch sitemap {sitemap_path} for {url}: {e}")
            continue

    # All sitemap attempts failed, try fallback methods
    logger.info(f"All sitemap attempts failed for {url}, trying fallback URL discovery methods")

    # Method 1: Common schedule paths
    common_paths = get_common_schedule_paths(url)
    logger.debug(f"Generated {len(common_paths)} common schedule paths")

    # Method 2: Navigation links
    nav_links = get_navigation_links(url)
    logger.debug(f"Found {len(nav_links)} navigation links")

    # Method 3: Stealth browser fallback for navigation discovery
    stealth_nav_links = []
    if len(nav_links) < 5:  # If we didn't find many links, try stealth browser
        logger.debug("Few navigation links found, trying stealth browser for enhanced discovery")
        try:
            from core.stealth_browser import get_stealth_browser

            stealth_browser = get_stealth_browser()
            if stealth_browser.is_available:
                stealth_nav_links = stealth_browser.get_navigation_links(url)
                logger.debug(f"Stealth browser found {len(stealth_nav_links)} additional navigation links")
        except Exception as e:
            logger.debug(f"Stealth browser navigation failed: {e}")

    # Method 4: Robots.txt parsing for additional discovery hints
    robots_urls = get_robots_txt_hints(url)
    logger.debug(f"Found {len(robots_urls)} URLs from robots.txt hints")

    # Combine all discovered URLs
    all_discovered = common_paths + nav_links + stealth_nav_links + robots_urls

    # Remove duplicates and filter
    unique_urls = []
    seen = set()
    for discovered_url in all_discovered:
        normalized_discovered = normalize_url(discovered_url)
        if normalized_discovered not in seen:
            # Additional filtering for quality
            if is_relevant_url(discovered_url, url):
                unique_urls.append(discovered_url)
                seen.add(normalized_discovered)

    logger.info(f"Discovered {len(unique_urls)} URLs using fallback methods for {url}")
    _sitemap_cache[normalized_url] = unique_urls
    return unique_urls


def extract_time_info_from_soup(soup: BeautifulSoup, keyword: str) -> tuple[str, str | None]:
    """Extracts schedule information from a BeautifulSoup object."""

    # Find all elements that contain the keyword
    elements_with_keyword = soup.find_all(string=re.compile(keyword, re.IGNORECASE))

    best_snippet = None
    best_snippet_score = -1

    for element in elements_with_keyword:
        # Get the parent element that is likely to contain the relevant text
        # This is a heuristic, might need tuning
        parent = element.find_parent(["p", "li", "div", "span", "td", "h1", "h2", "h3", "h4", "h5", "h6"])

        if parent:
            current_snippet_parts = [parent.get_text(separator="\n", strip=True)]

            # Look at next siblings for more schedule information
            for sibling in parent.next_siblings:
                if isinstance(sibling, Tag):  # Only process Tag objects
                    # Limit the number of siblings to check to avoid grabbing too much
                    if len(current_snippet_parts) > 5:  # Heuristic: check up to 5 siblings
                        break
                    current_snippet_parts.append(sibling.get_text(separator="\n", strip=True))

            snippet = "\n".join(current_snippet_parts).strip()

            # Score the snippet based on length and presence of schedule-like words
            score = len(snippet)
            if (
                "schedule" in snippet.lower()
                or "hours" in snippet.lower()
                or "am" in snippet.lower()
                or "pm" in snippet.lower()
                or "confessionals" in snippet.lower()
                or "by appointment" in snippet.lower()
            ):
                score += 100  # Boost score for schedule-like words

            if score > best_snippet_score:
                best_snippet_score = score
                best_snippet = snippet

    if best_snippet:
        # Now, try to extract the time pattern from the best snippet
        time_pattern = re.compile(r"(\d+)\s*hours?\s*per\s*(week|month)", re.IGNORECASE)
        match = time_pattern.search(best_snippet)
        if match:
            hours = int(match.group(1))
            period = match.group(2).lower()
            return f"{hours} hours per {period}", match.group(0)
        else:
            return best_snippet, best_snippet  # If no specific time pattern, return the snippet as is

    return "Information not found", None


def extract_schedule_ai_first(url: str, schedule_type: str, suppression_urls: set[str], parish_id: int) -> tuple[dict, bool]:
    """
    AI-first schedule extraction with keyword fallback.

    Returns:
        (result_dict, used_ai): Tuple of extraction result and whether AI was used
    """
    if url in suppression_urls:
        logger.info(f"Skipping AI extraction for {url} as it is in the suppression list.")
        return {"info": "Information not found", "method": "suppressed"}, False

    try:
        # Fetch page content
        response = make_request_with_delay(requests_session, url, timeout=15)
        response.raise_for_status()
        content = response.text

        # Try AI extraction first
        ai_extractor = get_ai_extractor()
        if ai_extractor.model:  # Check if AI is available
            logger.info(f"🤖 Attempting AI extraction for {schedule_type} at {url}")

            ai_result = ai_extractor.extract_schedule_from_content(content, url, schedule_type)

            # Calculate adaptive confidence threshold
            adaptive_threshold = ai_extractor.get_adaptive_confidence_threshold(url, content)
            confidence_score = ai_result.get("confidence_score", 0)

            logger.info(f"🤖 AI confidence: {confidence_score}, threshold: {adaptive_threshold}")

            # Use AI result if confidence meets adaptive threshold
            if ai_result.get("schedule_found") and confidence_score >= adaptive_threshold:
                logger.info(f"🤖 AI extraction successful for {schedule_type} at {url}")

                # Format for compatibility with existing code
                schedule_details = ai_result.get("schedule_details", "")
                if not schedule_details and ai_result.get("times"):
                    # Create readable schedule from structured data
                    times = ai_result.get("times", [])
                    days = ai_result.get("days_offered", [])
                    if days and times:
                        schedule_details = f"{', '.join(days)}: {', '.join(times)}"
                    elif times:
                        schedule_details = ", ".join(times)

                result = {
                    "info": schedule_details or "Schedule found via AI",
                    "method": "ai_gemini",
                    "confidence": confidence_score,
                    "ai_data": ai_result,
                    "fact_string": schedule_details,
                }

                # Save AI result to database immediately
                ai_result["parish_id"] = parish_id
                save_ai_schedule_results(get_supabase_client(), [ai_result])

                return result, True
            else:
                logger.info(f"🤖 AI confidence too low ({confidence_score} < {adaptive_threshold}), falling back to keywords")
        else:
            logger.warning("🤖 AI extractor not available, falling back to keywords")

        # Fallback to keyword extraction
        logger.info(f"🔍 Using keyword fallback for {schedule_type} at {url}")
        soup = BeautifulSoup(content, "html.parser")
        keyword_map = {"reconciliation": "Reconciliation", "adoration": "Adoration", "mass": "Mass"}
        keyword = keyword_map.get(schedule_type, schedule_type.title())

        info, fact_string = extract_time_info_from_soup(soup, keyword)

        result = {
            "info": info,
            "method": "keyword_extraction",
            "confidence": 50 if info != "Information not found" else 0,
            "fact_string": fact_string,
        }

        return result, False

    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch {url} for {schedule_type} extraction: {e}")
        return {"info": "Information not found", "method": "network_error", "error": str(e)}, False
    except Exception as e:
        logger.error(f"Unexpected error in AI-first extraction for {url}: {e}")
        return {"info": "Information not found", "method": "extraction_error", "error": str(e)}, False


def extract_time_info(url: str, keyword: str, suppression_urls: set[str]) -> tuple[str, str | None]:
    """Legacy function - kept for backward compatibility."""
    if url in suppression_urls:
        logger.info(f"Skipping extraction for {url} as it is in the suppression list.")
        return "Information not found", None
    try:
        response = make_request_with_delay(requests_session, url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        return extract_time_info_from_soup(soup, keyword)
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch {url} for time info extraction: {e}")
        return "Information not found", None


def choose_best_url(urls: list[str], keywords: dict, negative_keywords: list[str], base_domain: str) -> str:
    """Chooses the best URL from a list based on a scoring system."""
    if not urls:
        return ""
    if len(urls) == 1:
        return urls[0]

    best_url = ""
    max_score = -1

    for url in urls:
        score = calculate_priority(url, keywords, negative_keywords, base_domain)

        if score > max_score:
            max_score = score
            best_url = url

    if not best_url:
        best_url = urls[0]

    logger.info(f"Selected best URL from {len(urls)} candidates: {best_url} with score {max_score}")
    return best_url


def calculate_priority(url: str, keywords: dict, negative_keywords: list[str], base_domain: str = None) -> int:
    """Calculates the priority of a URL based on keywords in its path and domain relevance."""
    score = 0
    url_path = urlparse(url).path.lower()
    url_domain = urlparse(url).netloc.lower().replace("www.", "")

    for kw, kw_score in keywords.items():
        if kw in url_path:
            score += kw_score

    for neg_kw in negative_keywords:
        if neg_kw in url_path:
            score -= 2

    if len(url_path.split("/")) > 2:
        score += 1

    # Boost score if the URL is from the same base domain as the parish website
    if base_domain and url_domain == base_domain:
        score += 10  # Significant boost for local relevance

    return score


def scrape_parish_data(
    url: str,
    parish_id: int,
    supabase: Client,
    suppression_urls: set[str],
    max_pages_to_scan: int = config.DEFAULT_MAX_PAGES_TO_SCAN,
) -> dict:
    """
    Enhanced parish website scraping with intelligent URL discovery and optimization.

    Uses Enhanced URL Manager for:
    - Success-based URL memory (golden URLs)
    - Smart protocol detection and DNS resolution
    - Dynamic page limits based on success history
    - Improved timeout strategies
    """
    # Initial check for the starting URL
    if normalize_url(url) in suppression_urls:
        logger.info(f"Skipping initial URL {url} as it is in the suppression list.")
        return {
            "url": url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "offers_reconciliation": False,
            "offers_adoration": False,
        }

    # Temporary workaround for saintbrigid.org network issues
    if url == "http://www.saintbrigid.org/":
        logger.warning(f"Temporarily skipping {url} due to persistent network issues.")
        return {
            "url": url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "offers_reconciliation": False,
            "offers_adoration": False,
        }

    # Initialize Enhanced URL Manager and Visit Tracker
    url_manager = get_enhanced_url_manager(supabase)
    visit_tracker = get_url_visit_tracker(supabase)

    # Create optimized extraction context
    extraction_context = url_manager.get_extraction_context(parish_id, url)

    # Use dynamic page limit from context
    optimized_max_pages = extraction_context.page_scan_limit
    logger.info(f"🔗 Using optimized page scan limit: {optimized_max_pages}")

    urls_to_visit = []
    visited_urls = set()
    candidate_pages = {"reconciliation": [], "adoration": []}
    discovered_urls = {}

    # Load keywords from database
    (
        recon_keywords,
        recon_negative_keywords,
        adoration_keywords,
        adoration_negative_keywords,
        mass_keywords,
        mass_negative_keywords,
    ) = load_keywords_from_database(supabase)
    all_keywords = get_all_keywords_for_priority_calculation(supabase)

    base_domain = urlparse(url).netloc.lower().replace("www.", "")

    # Collect initial URLs (base + sitemap)
    initial_urls = [url]
    sitemap_urls = get_sitemap_urls(url)
    if sitemap_urls:
        initial_urls.extend(sitemap_urls)

    # Get optimized URL candidates using Enhanced URL Manager
    logger.info(f"🔗 Getting optimized URL candidates for {len(initial_urls)} initial URLs")
    optimized_candidates = url_manager.get_optimized_url_candidates(extraction_context, initial_urls)

    # Build priority queue from optimized candidates
    for candidate in optimized_candidates:
        if normalize_url(candidate.url) in suppression_urls:
            logger.info(f"Skipping optimized URL {candidate.url} as it is in suppression list.")
            continue

        # Use Enhanced URL Manager priority score (negative for max-heap)
        priority = -candidate.priority_score
        heapq.heappush(urls_to_visit, (priority, candidate.url))

    # Add any remaining initial URLs not covered by optimization
    for initial_url in initial_urls:
        if not any(candidate.url == initial_url for candidate in optimized_candidates):
            if normalize_url(initial_url) not in suppression_urls:
                priority = calculate_priority(initial_url, all_keywords, [], base_domain)
                heapq.heappush(urls_to_visit, (-priority, initial_url))

    logger.info(f"🔗 Starting enhanced scan with {len(urls_to_visit)} optimized URLs in priority queue.")

    while urls_to_visit and len(visited_urls) < optimized_max_pages:
        priority, current_url = heapq.heappop(urls_to_visit)
        priority = -priority

        if current_url in visited_urls:
            continue

        if normalize_url(current_url) in suppression_urls:
            logger.info(f"Skipping {current_url} as it is in the suppression list.")
            visited_urls.add(current_url)  # Mark as visited to avoid re-processing
            continue

        if re.search(r"\.(pdf|jpg|jpeg|png|gif|svg|zip|docx|xlsx|pptx|mp3|mp4|avi|mov)$", current_url, re.IGNORECASE):
            visited_urls.add(current_url)
            continue

        logger.debug(f"Checking {current_url} (Priority: {priority}, Visited: {len(visited_urls) + 1}/{max_pages_to_scan})")
        visited_urls.add(current_url)

        key = (current_url, parish_id)
        if key in discovered_urls:
            discovered_urls[key]["visited"] = True
        else:
            discovered_urls[key] = {
                "parish_id": parish_id,
                "url": current_url,
                "score": int(priority),
                "visited": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        # Use VisitTracker context manager for comprehensive visit tracking
        with VisitTracker(current_url, parish_id, visit_tracker) as visit_result:
            try:
                start_time = time.time()
                response = make_request_with_delay(requests_session, current_url, timeout=10)
                response_time = time.time() - start_time

                # Record HTTP response details
                visit_tracker.record_http_response(
                    visit_result,
                    response.status_code,
                    response_time,
                    response.headers.get("content-type"),
                    len(response.content) if response.content else 0,
                    response.url,
                )

                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")

                page_text = soup.get_text()
                page_text_lower = page_text.lower()

                # Track schedule data discovery
                schedule_found = False

                # AI-first approach: Try extracting schedules immediately
                ai_extraction_attempted = False

                # Check if page likely contains schedule information
                schedule_indicators = [
                    "reconciliation",
                    "confession",
                    "adoration",
                    "mass",
                    "schedule",
                    "hours",
                    "times",
                    "sacrament",
                    "worship",
                    "liturgy",
                ]

                if any(indicator in page_text_lower for indicator in schedule_indicators):
                    logger.info(f"🤖 Schedule indicators found on {current_url}, attempting AI extraction")
                    ai_extraction_attempted = True

                    # Try AI extraction for all schedule types
                    for schedule_type in ["reconciliation", "adoration", "mass"]:
                        result, used_ai = extract_schedule_ai_first(current_url, schedule_type, suppression_urls, parish_id)

                        if result.get("confidence", 0) > 0:
                            logger.info(f"🤖 AI found {schedule_type} schedule: {result.get('info', 'N/A')[:100]}")
                            candidate_pages[schedule_type].append(current_url)
                            schedule_found = True

                # Fallback to keyword detection only if AI wasn't attempted or found nothing
                if not ai_extraction_attempted or not schedule_found:
                    if any(kw in page_text_lower for kw in ["reconciliation", "confession"]):
                        logger.info(f"Found 'Reconciliation' keywords on {current_url}")
                        candidate_pages["reconciliation"].append(current_url)
                        schedule_found = True

                    if "adoration" in page_text_lower:
                        logger.info(f"Found 'Adoration' keyword on {current_url}")
                        candidate_pages["adoration"].append(current_url)
                        schedule_found = True

                # Record extraction success and assess content quality
                visit_tracker.record_extraction_attempt(visit_result, True)
                quality_score = visit_tracker.assess_content_quality(visit_result, page_text, schedule_found)

                logger.debug(
                    f"🔍 Visit tracked for {current_url}: quality={quality_score:.2f}, schedule_found={schedule_found}"
                )

                # Continue with link discovery
                for a in soup.find_all("a", href=True):
                    link = urljoin(current_url, a["href"]).split("#")[0]
                    # Check if the link is a valid HTTP/HTTPS URL and does not contain an email pattern
                    if (
                        link.startswith(("http://", "https://"))
                        and link not in visited_urls
                        and not re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", link)
                    ):
                        if normalize_url(link) in suppression_urls:
                            logger.debug(f"Skipping discovered link {link} as it is in the suppression list.")
                            continue
                        link_priority = calculate_priority(link, all_keywords, [], base_domain)
                        heapq.heappush(urls_to_visit, (-link_priority, link))
                        key = (link, parish_id)
                        if key not in discovered_urls:
                            discovered_urls[key] = {
                                "parish_id": parish_id,
                                "url": link,
                                "score": int(link_priority),
                                "source_url": current_url,
                                "visited": False,
                                "created_at": datetime.now(timezone.utc).isoformat(),
                            }

            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not fetch or process {current_url}: {e}")
                # Record extraction failure
                visit_tracker.record_extraction_attempt(visit_result, False, e)

    if len(visited_urls) >= optimized_max_pages:
        logger.warning(f"🔗 Reached optimized scan limit of {optimized_max_pages} pages for {url}.")

    if discovered_urls:
        urls_to_insert = list(discovered_urls.values())
        try:
            supabase.table("DiscoveredUrls").upsert(urls_to_insert, on_conflict="url,parish_id").execute()
            logger.info(f"Saved {len(urls_to_insert)} discovered URLs to Supabase.")
        except Exception as e:
            logger.error(f"Error saving discovered URLs to Supabase: {e}")

    result = {"url": url, "scraped_at": datetime.now(timezone.utc).isoformat()}

    # Process reconciliation results (AI-first with keyword fallback)
    if candidate_pages["reconciliation"]:
        best_page = choose_best_url(candidate_pages["reconciliation"], recon_keywords, recon_negative_keywords, base_domain)
        result["reconciliation_page"] = best_page
        result["offers_reconciliation"] = True

        # Try AI-first extraction
        recon_result, used_ai = extract_schedule_ai_first(best_page, "reconciliation", suppression_urls, parish_id)

        if recon_result.get("confidence", 0) > 0:
            result["reconciliation_info"] = recon_result.get("info", "Information not found")
            result["reconciliation_fact_string"] = recon_result.get("fact_string")
            result["reconciliation_method"] = recon_result.get("method", "unknown")
            result["reconciliation_confidence"] = recon_result.get("confidence", 0)
            logger.info(f"🤖 Reconciliation extraction ({'AI' if used_ai else 'keyword'}): '{result['reconciliation_info']}'")
        else:
            # Final fallback to legacy extraction
            result["reconciliation_info"], result["reconciliation_fact_string"] = extract_time_info(
                best_page, "Reconciliation", suppression_urls
            )
            result["reconciliation_method"] = "keyword_legacy"
            result["reconciliation_confidence"] = 25
            logger.info(f"🔍 Reconciliation legacy extraction: '{result['reconciliation_info']}'")
    else:
        result["offers_reconciliation"] = False
        result["reconciliation_info"] = "No relevant page found"
        result["reconciliation_page"] = ""
        result["reconciliation_fact_string"] = None
        result["reconciliation_method"] = "none"
        result["reconciliation_confidence"] = 0

    # Process adoration results (AI-first with keyword fallback)
    if candidate_pages["adoration"]:
        best_page = choose_best_url(candidate_pages["adoration"], adoration_keywords, adoration_negative_keywords, base_domain)
        result["adoration_page"] = best_page
        result["offers_adoration"] = True

        # Try AI-first extraction
        adoration_result, used_ai = extract_schedule_ai_first(best_page, "adoration", suppression_urls, parish_id)

        if adoration_result.get("confidence", 0) > 0:
            result["adoration_info"] = adoration_result.get("info", "Information not found")
            result["adoration_fact_string"] = adoration_result.get("fact_string")
            result["adoration_method"] = adoration_result.get("method", "unknown")
            result["adoration_confidence"] = adoration_result.get("confidence", 0)
            logger.info(f"🤖 Adoration extraction ({'AI' if used_ai else 'keyword'}): '{result['adoration_info']}'")
        else:
            # Final fallback to legacy extraction
            result["adoration_info"], result["adoration_fact_string"] = extract_time_info(
                best_page, "Adoration", suppression_urls
            )
            result["adoration_method"] = "keyword_legacy"
            result["adoration_confidence"] = 25
            logger.info(f"🔍 Adoration legacy extraction: '{result['adoration_info']}'")
    else:
        result["offers_adoration"] = False
        result["adoration_info"] = "No relevant page found"
        result["adoration_page"] = ""
        result["adoration_fact_string"] = None
        result["adoration_method"] = "none"
        result["adoration_confidence"] = 0

    return result


def get_parishes_to_process(
    supabase: Client, num_parishes: int, parish_id: int = None, diocese_id: int = None
) -> list[tuple[str, int]]:
    """
    Intelligently prioritized parish selection for schedule extraction.

    Uses advanced algorithms to select parishes based on:
    - Schedule likelihood scoring (website patterns)
    - Freshness-based selection (recency prioritization)
    - Diocese clustering (batch similar patterns)
    - Success rate learning (historical performance)
    - Diocese filtering (when diocese_id is specified)
    """
    try:
        # Use intelligent prioritization system
        prioritizer = get_intelligent_parish_prioritizer(supabase)
        prioritized_parishes = prioritizer.get_prioritized_parishes(num_parishes, parish_id, diocese_id)

        if prioritized_parishes:
            logger.info(f"🎯 Intelligent prioritization selected {len(prioritized_parishes)} parishes")
            return prioritized_parishes
        else:
            logger.warning("🎯 Intelligent prioritization returned no parishes, falling back to simple method")
            # Fallback to simple method if intelligent prioritization fails
            return _get_parishes_simple_fallback(supabase, num_parishes, parish_id, diocese_id)

    except Exception as e:
        logger.error(f"🎯 Error in intelligent parish prioritization: {e}")
        logger.info("🎯 Falling back to simple parish selection method")
        return _get_parishes_simple_fallback(supabase, num_parishes, parish_id, diocese_id)


def _get_parishes_simple_fallback(
    supabase: Client, num_parishes: int, parish_id: int = None, diocese_id: int = None
) -> list[tuple[str, int]]:
    """Simple fallback parish selection method (original implementation)."""
    if parish_id:
        try:
            response = supabase.table("Parishes").select("id, Web").eq("id", parish_id).execute()
            if response.data:
                parish = response.data[0]
                if parish.get("Web"):
                    return [(parish["Web"], parish["id"])]
            return []
        except Exception as e:
            logger.error(f"Error fetching parish for ID {parish_id}: {e}")
            return []

    try:
        # Build query with optional diocese filtering
        query = supabase.table("Parishes").select("id, Web").not_.is_("Web", "null")
        if diocese_id:
            query = query.eq("diocese_id", diocese_id)
            logger.info(f"🎯 Filtering parishes to diocese ID: {diocese_id}")

        response = query.execute()
        all_parishes = [(p["Web"], p["id"]) for p in response.data if p["Web"]]

        if num_parishes > 0:
            return all_parishes[:num_parishes]
        return all_parishes
    except Exception as e:
        logger.error(f"Error fetching parishes: {e}")
        return []


def get_parish_metadata(supabase: Client, parish_ids: list) -> dict:
    """
    Fetch complete parish metadata including name, address, and diocese information.

    Args:
        supabase: Supabase client
        parish_ids: List of parish IDs to fetch

    Returns:
        Dictionary mapping parish_id to metadata dict with keys: name, website, address, diocese_name, diocese_id
    """
    if not parish_ids:
        return {}

    try:
        # Fetch parish data (without join - works in all environments)
        # Note: Column names have spaces in the actual schema
        parish_response = (
            supabase.table("Parishes")
            .select('id, Name, Web, "Street Address", City, State, "Zip Code", full_address, diocese_id')
            .in_("id", parish_ids)
            .execute()
        )

        # Collect unique diocese IDs and fetch their names
        diocese_ids = list(set(p.get("diocese_id") for p in parish_response.data if p.get("diocese_id")))
        diocese_names = {}

        if diocese_ids:
            try:
                diocese_response = (
                    supabase.table("Dioceses")
                    .select("id, Name")
                    .in_("id", diocese_ids)
                    .execute()
                )
                diocese_names = {d["id"]: d.get("Name", "Unknown Diocese") for d in diocese_response.data}
            except Exception as e:
                logger.warning(f"Could not fetch diocese names: {e}")

        parish_metadata = {}
        for p in parish_response.data:
            # Use full_address if available, otherwise construct from components
            full_address = p.get("full_address", "")

            if not full_address:
                # Construct full address from components (with space-separated column names)
                address_parts = []
                if p.get("Street Address"):
                    address_parts.append(p["Street Address"])
                if p.get("City"):
                    city_state = p["City"]
                    if p.get("State"):
                        city_state += f", {p['State']}"
                    if p.get("Zip Code"):
                        city_state += f" {p['Zip Code']}"
                    address_parts.append(city_state)
                full_address = ", ".join(address_parts) if address_parts else ""

            # Get diocese name from lookup
            diocese_id = p.get("diocese_id")
            diocese_name = diocese_names.get(diocese_id, "Unknown Diocese") if diocese_id else "Unknown Diocese"

            parish_metadata[p["id"]] = {
                "name": p.get("Name", "Unknown Parish"),
                "website": p.get("Web", ""),
                "address": full_address,
                "diocese_name": diocese_name,
                "diocese_id": diocese_id,
            }

        logger.info(f"Fetched metadata for {len(parish_metadata)} parishes")
        return parish_metadata

    except Exception as e:
        logger.error(f"Error fetching parish metadata: {e}")
        return {}


def save_facts_to_supabase(supabase: Client, results: list, monitoring_client=None):
    """Saves the scraping results to the new ParishData table."""
    if not results:
        logger.info("No results to save to Supabase.")
        return

    logger.info(f"Processing {len(results)} results for database saving")
    facts_to_save = []
    for result in results:
        parish_id = result.get("parish_id")
        if not parish_id:
            logger.warning(f"Skipping result with no parish_id: {result}")
            continue

        logger.info(
            f"Parish {parish_id}: Reconciliation offers={result.get('offers_reconciliation')}, "
            f"info='{result.get('reconciliation_info')}'"
        )
        logger.info(
            f"Parish {parish_id}: Adoration offers={result.get('offers_adoration')}, "
            f"info='{result.get('adoration_info')}'"
        )

        if result.get("offers_reconciliation") and result.get("reconciliation_info") != "Information not found":
            facts_to_save.append(
                {
                    "parish_id": parish_id,
                    "fact_type": "ReconciliationSchedule",
                    "fact_value": result.get("reconciliation_info"),
                    "fact_source_url": result.get("reconciliation_page"),
                    "fact_string": result.get("reconciliation_fact_string"),
                    "extraction_method": "keyword_based",
                }
            )
            logger.info(f"Added reconciliation fact for parish {parish_id}")

        if result.get("offers_adoration") and result.get("adoration_info") != "Information not found":
            facts_to_save.append(
                {
                    "parish_id": parish_id,
                    "fact_type": "AdorationSchedule",
                    "fact_value": result.get("adoration_info"),
                    "fact_source_url": result.get("adoration_page"),
                    "fact_string": result.get("adoration_fact_string"),
                    "extraction_method": "keyword_based",
                }
            )
            logger.info(f"Added adoration fact for parish {parish_id}")

    logger.info(f"Prepared {len(facts_to_save)} facts to save to database")
    if not facts_to_save:
        logger.info("No facts to save to Supabase.")
        return

    try:
        # Get complete parish metadata for monitoring
        parish_metadata = {}
        if monitoring_client and facts_to_save:
            parish_ids = list(set(fact["parish_id"] for fact in facts_to_save))
            parish_metadata = get_parish_metadata(supabase, parish_ids)

        supabase.table("ParishData").upsert(facts_to_save, on_conflict="parish_id,fact_type").execute()
        logger.info(f"Successfully saved {len(facts_to_save)} facts to Supabase table 'ParishData'.")

        # Send monitoring logs for ParishData insertions with complete parish data
        if monitoring_client:
            for fact in facts_to_save:
                parish_id = fact["parish_id"]
                parish_info = parish_metadata.get(
                    parish_id, {"name": "Unknown Parish", "website": "", "address": "", "diocese_name": "Unknown Diocese"}
                )

                fact_type = fact["fact_type"].replace("Schedule", "")  # Remove 'Schedule' from type
                fact_value = fact["fact_value"]
                source_url = fact.get("fact_source_url", "")

                # Create descriptive message with links
                parish_link = (
                    f" → <a href='{parish_info['website']}' target='_blank'>{parish_info['website']}</a>"
                    if parish_info["website"]
                    else ""
                )
                source_link = f" | <a href='{source_url}' target='_blank'>Source</a>" if source_url else ""

                monitoring_client.send_log(
                    f"Step 4 │ ✅ {fact_type} saved: {parish_info['name']} ({parish_info['address']}): "
                    f"{fact_value[:80]}{'...' if len(fact_value) > 80 else ''}{parish_link}{source_link}",
                    "INFO",
                    worker_type="schedule",
                )

    except Exception as e:
        logger.error(f"An unexpected error occurred during Supabase upsert: {e}", exc_info=True)


def main(
    num_parishes: int, parish_id: int = None, max_pages_to_scan: int = config.DEFAULT_MAX_PAGES_TO_SCAN, monitoring_client=None
):
    """Main function to run the scraping pipeline."""
    load_dotenv()

    supabase: Client = get_supabase_client()
    if not supabase:
        logger.error("Supabase client could not be initialized.")
        return

    suppression_urls = get_suppression_urls(supabase)
    logger.info(f"Loaded {len(suppression_urls)} suppression URLs.")

    parishes_to_process = get_parishes_to_process(supabase, num_parishes, parish_id)

    if not parishes_to_process:
        logger.info("No parish URLs to process. Exiting.")
        return

    logger.info(f"Processing {len(parishes_to_process)} parishes.")

    # Get parish metadata for all parishes upfront for better logging
    parish_ids = [p_id for url, p_id in parishes_to_process]
    parish_metadata = get_parish_metadata(supabase, parish_ids)

    results = []
    start_time = time.time()

    for idx, (url, p_id) in enumerate(parishes_to_process, 1):
        parish_info = parish_metadata.get(
            p_id, {"name": "Unknown Parish", "website": url, "address": "", "diocese_name": "Unknown Diocese"}
        )

        logger.info(f"[{idx}/{len(parishes_to_process)}] Scraping {parish_info['name']} (ID: {p_id})...")

        # Send start message to monitoring
        if monitoring_client:
            monitoring_client.send_log(
                f"Step 4 │ 🔍 [{idx}/{len(parishes_to_process)}] Visiting {parish_info['name']} "
                f"→ <a href='{url}' target='_blank'>{url}</a>",
                "INFO",
                worker_type="schedule",
            )

        extraction_start = time.time()
        result = scrape_parish_data(url, p_id, supabase, suppression_urls, max_pages_to_scan=max_pages_to_scan)
        extraction_duration = time.time() - extraction_start

        result["parish_id"] = p_id
        result["parish_name"] = parish_info["name"]
        result["parish_address"] = parish_info["address"]
        result["diocese_name"] = parish_info["diocese_name"]
        result["duration"] = extraction_duration
        results.append(result)

        logger.info(f"[{idx}/{len(parishes_to_process)}] Completed {parish_info['name']} in {extraction_duration:.1f}s")

        # Send completion message to monitoring
        if monitoring_client:
            schedules_found = 0
            if result.get("offers_reconciliation"):
                schedules_found += 1
            if result.get("offers_adoration"):
                schedules_found += 1

            status_emoji = "✅" if schedules_found > 0 else "⚠️"
            monitoring_client.send_log(
                f"Step 4 │ {status_emoji} [{idx}/{len(parishes_to_process)}] Completed {parish_info['name']} "
                f"({parish_info['address']}) - {schedules_found} schedule(s) found in {extraction_duration:.1f}s",
                "INFO" if schedules_found > 0 else "WARNING",
                worker_type="schedule",
            )

        # Save results after each parish to avoid data loss if script is interrupted
        logger.info(f"Saving results for parish {p_id} immediately...")
        save_facts_to_supabase(supabase, [result], monitoring_client)

        # Send extraction_complete message for dashboard Recent History
        if monitoring_client and hasattr(monitoring_client, "report_extraction_complete"):
            # Construct mass_times from schedule data
            mass_times_parts = []
            if result.get("offers_reconciliation") and result.get("reconciliation_info"):
                mass_times_parts.append(f"Reconciliation: {result['reconciliation_info'][:50]}")
            if result.get("offers_adoration") and result.get("adoration_info"):
                mass_times_parts.append(f"Adoration: {result['adoration_info'][:50]}")

            mass_times = " | ".join(mass_times_parts) if mass_times_parts else "No schedules found"

            monitoring_client.report_extraction_complete(
                diocese_name=parish_info["diocese_name"],
                parish_name=parish_info["name"],
                parish_url=url,
                parish_address=parish_info["address"],
                schedules_found=schedules_found,
                mass_times=mass_times,
                duration=extraction_duration,
                status="completed",
            )

    # Also save all results at the end (in case any individual saves failed)
    logger.info("Final batch save of all results...")
    save_facts_to_supabase(supabase, results, monitoring_client)

    # Send final summary to monitoring
    total_time = time.time() - start_time
    if monitoring_client:
        total_schedules = sum(
            1 for r in results if (r.get("offers_reconciliation") or r.get("offers_adoration"))
        )
        monitoring_client.send_log(
            f"Step 4 │ 🎉 Batch complete: {len(results)} parishes processed, "
            f"{total_schedules} with schedules in {total_time:.1f}s",
            "INFO",
            worker_type="schedule",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract adoration and reconciliation schedules from parish websites."
    )
    parser.add_argument(
        "--num_parishes",
        type=int,
        default=config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE,
        help=f"Maximum number of parishes to extract from. Set to 0 for no limit. "
        f"Defaults to {config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE}.",
    )
    parser.add_argument(
        "--parish_id", type=int, default=None, help="ID of a specific parish to process. Overrides --num_parishes."
    )
    parser.add_argument(
        "--max_pages_to_scan",
        type=int,
        default=config.DEFAULT_MAX_PAGES_TO_SCAN,  # Use the existing constant as default
        help=f"Maximum number of pages to scan per parish. Defaults to {config.DEFAULT_MAX_PAGES_TO_SCAN}.",
    )
    args = parser.parse_args()

    # Initialize monitoring client if MONITORING_URL is set
    import os
    monitoring_client = None
    monitoring_url = os.getenv("MONITORING_URL")
    if monitoring_url:
        monitoring_client = MonitoringClient(monitoring_url, worker_id="schedule-local")
        logger.info(f"Monitoring enabled: {monitoring_url}")

    main(args.num_parishes, args.parish_id, args.max_pages_to_scan, monitoring_client)
