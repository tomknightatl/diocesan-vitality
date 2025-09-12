#!/usr/bin/env python
# coding: utf-8

import argparse
import heapq
import os
import re
import warnings
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from bs4.element import Tag
from dotenv import load_dotenv
from supabase import Client, create_client

import config
from core.logger import get_logger
from core.db import get_supabase_client # Import the get_supabase_client function
from core.utils import normalize_url # Import normalize_url

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logger = get_logger(__name__)

_sitemap_cache = {}

# Configure requests to retry on common transient errors
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
requests_session = requests.Session()
requests_session.mount("https://", adapter)
requests_session.mount("http://", adapter)

def get_suppression_urls(supabase: Client) -> set[str]:
    """Fetches all URLs from the ParishFactsSuppressionURLs table."""
    try:
        response = supabase.table('parishfactssuppressionurls').select('url').execute()
        if response.data:
            return {normalize_url(item['url']) for item in response.data}
        return set()
    except Exception as e:
        logger.error(f"Error fetching suppression URLs: {e}")
        return set()


def get_sitemap_urls(url: str) -> list[str]:
    """Fetches sitemap.xml and extracts URLs."""
    normalized_url = normalize_url(url) # Normalize URL for consistent caching key
    if normalized_url in _sitemap_cache:
        logger.debug(f"Returning sitemap from cache for {url}")
        return _sitemap_cache[normalized_url]

    try:
        sitemap_url = urljoin(url, '/sitemap.xml')
        response = requests_session.get(sitemap_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        sitemap_links = [
            loc.text
            for loc in soup.find_all('loc')
            if loc.text and loc.text.startswith(('http://', 'https://')) and 'default' not in loc.text
        ]
        _sitemap_cache[normalized_url] = sitemap_links # Cache the result
        return sitemap_links
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch or parse sitemap for {url}: {e}")
        _sitemap_cache[normalized_url] = [] # Cache empty list on failure to avoid repeated attempts
        return []


def extract_time_info_from_soup(soup: BeautifulSoup, keyword: str) -> tuple[str, str | None]:
    """Extracts schedule information from a BeautifulSoup object."""
    
    # Find all elements that contain the keyword
    elements_with_keyword = soup.find_all(string=re.compile(keyword, re.IGNORECASE))

    best_snippet = None
    best_snippet_score = -1

    for element in elements_with_keyword:
        # Get the parent element that is likely to contain the relevant text
        # This is a heuristic, might need tuning
        parent = element.find_parent(['p', 'li', 'div', 'span', 'td', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        if parent:
            current_snippet_parts = [parent.get_text(separator='\n', strip=True)]
            
            # Look at next siblings for more schedule information
            for sibling in parent.next_siblings:
                if isinstance(sibling, Tag): # Only process Tag objects
                    # Limit the number of siblings to check to avoid grabbing too much
                    if len(current_snippet_parts) > 5: # Heuristic: check up to 5 siblings
                        break
                    current_snippet_parts.append(sibling.get_text(separator='\n', strip=True))
            
            snippet = '\n'.join(current_snippet_parts).strip()
            
            # Score the snippet based on length and presence of schedule-like words
            score = len(snippet)
            if "schedule" in snippet.lower() or "hours" in snippet.lower() or "am" in snippet.lower() or "pm" in snippet.lower() or "confessionals" in snippet.lower() or "by appointment" in snippet.lower():
                score += 100 # Boost score for schedule-like words

            if score > best_snippet_score:
                best_snippet_score = score
                best_snippet = snippet

    if best_snippet:
        # Now, try to extract the time pattern from the best snippet
        time_pattern = re.compile(r'(\d+)\s*hours?\s*per\s*(week|month)', re.IGNORECASE)
        match = time_pattern.search(best_snippet)
        if match:
            hours = int(match.group(1))
            period = match.group(2).lower()
            return f"{hours} hours per {period}", match.group(0)
        else:
            return best_snippet, best_snippet # If no specific time pattern, return the snippet as is
            
    return "Information not found", None


def extract_time_info(url: str, keyword: str, suppression_urls: set[str]) -> tuple[str, str | None]:
    """Fetches a URL and extracts schedule information related to a keyword."""
    if url in suppression_urls:
        logger.info(f"Skipping extraction for {url} as it is in the suppression list.")
        return "Information not found", None
    try:
        response = requests_session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
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
    url_domain = urlparse(url).netloc.lower().replace('www.', '')

    for kw, kw_score in keywords.items():
        if kw in url_path:
            score += kw_score

    for neg_kw in negative_keywords:
        if neg_kw in url_path:
            score -= 2

    if len(url_path.split('/')) > 2:
        score += 1

    # Boost score if the URL is from the same base domain as the parish website
    if base_domain and url_domain == base_domain:
        score += 10 # Significant boost for local relevance

    return score


def scrape_parish_data(url: str, parish_id: int, supabase: Client, suppression_urls: set[str], max_pages_to_scan: int = config.DEFAULT_MAX_PAGES_TO_SCAN) -> dict:
    """
    Scrapes a parish website to find the best pages for Reconciliation and Adoration info.
    Uses a priority queue to visit more promising URLs first.
    """
    # Initial check for the starting URL
    if normalize_url(url) in suppression_urls:
        logger.info(f"Skipping initial URL {url} as it is in the suppression list.")
        return {'url': url, 'scraped_at': datetime.now(timezone.utc).isoformat(), 'offers_reconciliation': False, 'offers_adoration': False}

    # Temporary workaround for saintbrigid.org network issues
    if url == "http://www.saintbrigid.org/":
        logger.warning(f"Temporarily skipping {url} due to persistent network issues.")
        return {'url': url, 'scraped_at': datetime.now(timezone.utc).isoformat(), 'offers_reconciliation': False, 'offers_adoration': False}

    urls_to_visit = []
    visited_urls = set()
    candidate_pages = {'reconciliation': [], 'adoration': []}
    discovered_urls = {}

    recon_keywords = {'reconciliation': 5, 'confession': 5, 'schedule': 8, 'times': 3, 'sacrament': 1}
    recon_negative_keywords = ['adoration', 'baptism', 'donate', 'giving']
    adoration_keywords = {'adoration': 5, 'eucharist': 5, 'schedule': 3, 'times': 3}
    adoration_negative_keywords = ['reconciliation', 'confession', 'baptism', 'donate', 'giving']
    all_keywords = {**recon_keywords, **adoration_keywords}

    base_domain = urlparse(url).netloc.lower().replace('www.', '')

    heapq.heappush(urls_to_visit, (0, url))

    sitemap_urls = get_sitemap_urls(url)
    if sitemap_urls:
        for s_url in sitemap_urls:
            if normalize_url(s_url) in suppression_urls:
                logger.info(f"Skipping sitemap URL {s_url} as it is in the suppression list.")
                continue
            priority = calculate_priority(s_url, all_keywords, [], base_domain)
            heapq.heappush(urls_to_visit, (-priority, s_url))

    logger.info(f"Starting scan with {len(urls_to_visit)} initial URLs in priority queue.")

    while urls_to_visit and len(visited_urls) < max_pages_to_scan:
        priority, current_url = heapq.heappop(urls_to_visit)
        priority = -priority

        if current_url in visited_urls:
            continue
        
        if normalize_url(current_url) in suppression_urls:
            logger.info(f"Skipping {current_url} as it is in the suppression list.")
            visited_urls.add(current_url) # Mark as visited to avoid re-processing
            continue

        if re.search(r'\.(pdf|jpg|jpeg|png|gif|svg|zip|docx|xlsx|pptx|mp3|mp4|avi|mov)$', current_url, re.IGNORECASE):
            visited_urls.add(current_url)
            continue

        logger.debug(f"Checking {current_url} (Priority: {priority}, Visited: {len(visited_urls) + 1}/{max_pages_to_scan})")
        visited_urls.add(current_url)

        key = (current_url, parish_id)
        if key in discovered_urls:
            discovered_urls[key]['visited'] = True
        else:
            discovered_urls[key] = {
                'parish_id': parish_id,
                'url': current_url,
                'score': priority,
                'visited': True,
                'created_at': datetime.now(timezone.utc).isoformat()
            }

        try:
            response = requests_session.get(current_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            page_text_lower = soup.get_text().lower()

            if any(kw in page_text_lower for kw in ['reconciliation', 'confession']):
                logger.info(f"Found 'Reconciliation' keywords on {current_url}")
                candidate_pages['reconciliation'].append(current_url)

            if 'adoration' in page_text_lower:
                logger.info(f"Found 'Adoration' keyword on {current_url}")
                candidate_pages['adoration'].append(current_url)

            for a in soup.find_all('a', href=True):
                link = urljoin(current_url, a['href']).split('#')[0]
                # Check if the link is a valid HTTP/HTTPS URL and does not contain an email pattern
                if link.startswith(('http://', 'https://')) and link not in visited_urls and not re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', link):
                    if normalize_url(link) in suppression_urls:
                        logger.debug(f"Skipping discovered link {link} as it is in the suppression list.")
                        continue
                    link_priority = calculate_priority(link, all_keywords, [], base_domain)
                    heapq.heappush(urls_to_visit, (-link_priority, link))
                    key = (link, parish_id)
                    if key not in discovered_urls:
                        discovered_urls[key] = {
                            'parish_id': parish_id,
                            'url': link,
                            'score': link_priority,
                            'source_url': current_url,
                            'visited': False,
                            'created_at': datetime.now(timezone.utc).isoformat()
                        }

        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch or process {current_url}: {e}")

    if len(visited_urls) >= max_pages_to_scan:
        logger.warning(f"Reached scan limit of {max_pages_to_scan} pages for {url}.")

    if discovered_urls:
        urls_to_insert = list(discovered_urls.values())
        try:
            supabase.table('DiscoveredUrls').upsert(urls_to_insert, on_conflict='url,parish_id').execute()
            logger.info(f"Saved {len(urls_to_insert)} discovered URLs to Supabase.")
        except Exception as e:
            logger.error(f"Error saving discovered URLs to Supabase: {e}")

    result = {'url': url, 'scraped_at': datetime.now(timezone.utc).isoformat()}
    
    if candidate_pages['reconciliation']:
        best_page = choose_best_url(candidate_pages['reconciliation'], recon_keywords, recon_negative_keywords, base_domain)
        result['reconciliation_page'] = best_page
        result['offers_reconciliation'] = True
        result['reconciliation_info'], result['reconciliation_fact_string'] = extract_time_info(best_page, 'Reconciliation', suppression_urls)
        logger.info(f"Reconciliation extraction result: '{result['reconciliation_info']}'")
    else:
        result['offers_reconciliation'] = False
        result['reconciliation_info'] = "No relevant page found"
        result['reconciliation_page'] = ""
        result['reconciliation_fact_string'] = None

    if candidate_pages['adoration']:
        best_page = choose_best_url(candidate_pages['adoration'], adoration_keywords, adoration_negative_keywords, base_domain)
        result['adoration_page'] = best_page
        result['offers_adoration'] = True
        result['adoration_info'], result['adoration_fact_string'] = extract_time_info(best_page, 'Adoration', suppression_urls)
        logger.info(f"Adoration extraction result: '{result['adoration_info']}'")
    else:
        result['offers_adoration'] = False
        result['adoration_info'] = "No relevant page found"
        result['adoration_page'] = ""
        result['adoration_fact_string'] = None
        
    return result


def get_parishes_to_process(supabase: Client, num_parishes: int, parish_id: int = None) -> list[tuple[str, int]]:
    """Fetches parish URLs and IDs to process."""
    if parish_id:
        try:
            response = supabase.table('Parishes').select('id, Web').eq('id', parish_id).execute()
            if response.data:
                parish = response.data[0]
                if parish.get('Web'):
                    return [(parish['Web'], parish['id'])]
            return []
        except Exception as e:
            logger.error(f"Error fetching parish for ID {parish_id}: {e}")
            return []

    try:
        response = supabase.table('Parishes').select('id, Web').not_.is_('Web', 'null').execute()
        all_parishes = [(p['Web'], p['id']) for p in response.data if p['Web']]
        
        if num_parishes > 0:
            return all_parishes[:num_parishes]
        return all_parishes
    except Exception as e:
        logger.error(f"Error fetching parishes: {e}")
        return []


def save_facts_to_supabase(supabase: Client, results: list):
    """Saves the scraping results to the new ParishData table."""
    if not results:
        logger.info("No results to save to Supabase.")
        return

    logger.info(f"Processing {len(results)} results for database saving")
    facts_to_save = []
    for result in results:
        parish_id = result.get('parish_id')
        if not parish_id:
            logger.warning(f"Skipping result with no parish_id: {result}")
            continue

        logger.info(f"Parish {parish_id}: Reconciliation offers={result.get('offers_reconciliation')}, info='{result.get('reconciliation_info')}'")
        logger.info(f"Parish {parish_id}: Adoration offers={result.get('offers_adoration')}, info='{result.get('adoration_info')}'")

        if result.get('offers_reconciliation') and result.get('reconciliation_info') != "Information not found":
            facts_to_save.append({
                'parish_id': parish_id,
                'fact_type': 'ReconciliationSchedule',
                'fact_value': result.get('reconciliation_info'),
                'fact_source_url': result.get('reconciliation_page'),
                'fact_string': result.get('reconciliation_fact_string')
            })
            logger.info(f"Added reconciliation fact for parish {parish_id}")
        
        if result.get('offers_adoration') and result.get('adoration_info') != "Information not found":
            facts_to_save.append({
                'parish_id': parish_id,
                'fact_type': 'AdorationSchedule',
                'fact_value': result.get('adoration_info'),
                'fact_source_url': result.get('adoration_page'),
                'fact_string': result.get('adoration_fact_string')
            })
            logger.info(f"Added adoration fact for parish {parish_id}")

    logger.info(f"Prepared {len(facts_to_save)} facts to save to database")
    if not facts_to_save:
        logger.info("No facts to save to Supabase.")
        return

    try:
        supabase.table('ParishData').upsert(facts_to_save, on_conflict='parish_id,fact_type').execute()
        logger.info(f"Successfully saved {len(facts_to_save)} facts to Supabase table 'ParishData'.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during Supabase upsert: {e}", exc_info=True)


def main(num_parishes: int, parish_id: int = None, max_pages_to_scan: int = config.DEFAULT_MAX_PAGES_TO_SCAN):
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

    results = []
    for url, p_id in parishes_to_process:
        logger.info(f"Scraping {url} for parish {p_id}...")
        result = scrape_parish_data(url, p_id, supabase, suppression_urls, max_pages_to_scan=max_pages_to_scan)
        result['parish_id'] = p_id
        try:
            parish_name = urlparse(url).netloc.replace('www.','')
        except IndexError:
            parish_name = url
        result['parish_name'] = parish_name
        results.append(result)
        logger.info(f"Completed scraping {url}")
        
        # Save results after each parish to avoid data loss if script is interrupted
        logger.info(f"Saving results for parish {p_id} immediately...")
        save_facts_to_supabase(supabase, [result])

    # Also save all results at the end (in case any individual saves failed)
    logger.info("Final batch save of all results...")
    save_facts_to_supabase(supabase, results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extract adoration and reconciliation schedules from parish websites.")
    parser.add_argument(
        "--num_parishes",
        type=int,
        default=config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE,
        help=f"Maximum number of parishes to extract from. Set to 0 for no limit. Defaults to {config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE}."
    )
    parser.add_argument(
        "--parish_id",
        type=int,
        default=None,
        help="ID of a specific parish to process. Overrides --num_parishes."
    )
    parser.add_argument(
        "--max_pages_to_scan",
        type=int,
        default=config.DEFAULT_MAX_PAGES_TO_SCAN, # Use the existing constant as default
        help=f"Maximum number of pages to scan per parish. Defaults to {config.DEFAULT_MAX_PAGES_TO_SCAN}."
    )
    args = parser.parse_args()
    main(args.num_parishes, args.parish_id, args.max_pages_to_scan)