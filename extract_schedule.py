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
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from dotenv import load_dotenv
from supabase import Client, create_client

import config
from core.logger import get_logger

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logger = get_logger(__name__)

MAX_PAGES_TO_SCAN = 100 # Limit the number of pages to scan per parish


def get_sitemap_urls(url: str) -> list[str]:
    """Fetches sitemap.xml and extracts URLs."""
    try:
        sitemap_url = urljoin(url, '/sitemap.xml')
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        return [
            loc.text
            for loc in soup.find_all('loc')
            if loc.text and loc.text.startswith(('http://', 'https://')) and 'default' not in loc.text
        ]
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch or parse sitemap for {url}: {e}")
        return []


def extract_time_info_from_soup(soup: BeautifulSoup, keyword: str) -> str:
    """Extracts schedule information from a BeautifulSoup object."""
    text = soup.get_text()
    
    time_pattern = re.compile(r'(\d+)\s*hours?\s*per\s*(week|month)', re.IGNORECASE)
    match = time_pattern.search(text)
    if match:
        hours = int(match.group(1))
        period = match.group(2).lower()
        return f"{hours} hours per {period}"

    for p in soup.find_all('p'):
        if keyword.lower() in p.text.lower():
            return p.text.strip()
            
    return "Information not found"


def extract_time_info(url: str, keyword: str) -> str:
    """Fetches a URL and extracts schedule information related to a keyword."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return extract_time_info_from_soup(soup, keyword)
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch {url} for time info extraction: {e}")
        return "Information not found"


def choose_best_url(urls: list[str], keywords: dict, negative_keywords: list[str]) -> str:
    """Chooses the best URL from a list based on a scoring system."""
    if not urls:
        return ""
    if len(urls) == 1:
        return urls[0]

    best_url = ""
    max_score = -1

    for url in urls:
        score = 0
        url_path = urlparse(url).path.lower()

        for kw, kw_score in keywords.items():
            if kw in url_path:
                score += kw_score

        for neg_kw in negative_keywords:
            if neg_kw in url_path:
                score -= 2

        if len(url_path.split('/')) > 2:
            score += 1

        if score > max_score:
            max_score = score
            best_url = url

    if not best_url:
        best_url = urls[0]

    logger.info(f"Selected best URL from {len(urls)} candidates: {best_url} with score {max_score}")
    return best_url


def calculate_priority(url: str, keywords: dict, negative_keywords: list[str]) -> int:
    """Calculates the priority of a URL based on keywords in its path."""
    score = 0
    url_path = urlparse(url).path.lower()

    for kw, kw_score in keywords.items():
        if kw in url_path:
            score += kw_score

    for neg_kw in negative_keywords:
        if neg_kw in url_path:
            score -= 2

    if len(url_path.split('/')) > 2:
        score += 1
    return score


def scrape_parish_data(url: str, parish_id: int, supabase: Client) -> dict:
    """
    Scrapes a parish website to find the best pages for Reconciliation and Adoration info.
    Uses a priority queue to visit more promising URLs first.
    """
    urls_to_visit = []
    visited_urls = set()
    candidate_pages = {'reconciliation': [], 'adoration': []}
    discovered_urls = {}

    recon_keywords = {'reconciliation': 5, 'confession': 5, 'schedule': 3, 'times': 3, 'sacrament': 1}
    recon_negative_keywords = ['adoration', 'baptism', 'donate', 'giving']
    adoration_keywords = {'adoration': 5, 'eucharist': 5, 'schedule': 3, 'times': 3}
    adoration_negative_keywords = ['reconciliation', 'confession', 'baptism', 'donate', 'giving']
    all_keywords = {**recon_keywords, **adoration_keywords}

    heapq.heappush(urls_to_visit, (0, url))

    sitemap_urls = get_sitemap_urls(url)
    if sitemap_urls:
        for s_url in sitemap_urls:
            priority = calculate_priority(s_url, all_keywords, [])
            heapq.heappush(urls_to_visit, (-priority, s_url))

    logger.info(f"Starting scan with {len(urls_to_visit)} initial URLs in priority queue.")

    while urls_to_visit and len(visited_urls) < MAX_PAGES_TO_SCAN:
        priority, current_url = heapq.heappop(urls_to_visit)
        priority = -priority

        if current_url in visited_urls:
            continue
        
        if re.search(r'\.(pdf|jpg|jpeg|png|gif|svg|zip|docx|xlsx|pptx|mp3|mp4|avi|mov)$', current_url, re.IGNORECASE):
            visited_urls.add(current_url)
            continue

        logger.debug(f"Checking {current_url} (Priority: {priority}, Visited: {len(visited_urls) + 1}/{MAX_PAGES_TO_SCAN})")
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
            response = requests.get(current_url, timeout=10)
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
                if link.startswith(('http://', 'https://')) and link not in visited_urls:
                    link_priority = calculate_priority(link, all_keywords, [])
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

    if len(visited_urls) >= MAX_PAGES_TO_SCAN:
        logger.warning(f"Reached scan limit of {MAX_PAGES_TO_SCAN} pages for {url}.")

    if discovered_urls:
        urls_to_insert = list(discovered_urls.values())
        try:
            supabase.table('DiscoveredUrls').upsert(urls_to_insert, on_conflict='url,parish_id').execute()
            logger.info(f"Saved {len(urls_to_insert)} discovered URLs to Supabase.")
        except Exception as e:
            logger.error(f"Error saving discovered URLs to Supabase: {e}")

    result = {'url': url, 'scraped_at': datetime.now(timezone.utc).isoformat()}
    
    if candidate_pages['reconciliation']:
        best_page = choose_best_url(candidate_pages['reconciliation'], recon_keywords, recon_negative_keywords)
        result['reconciliation_page'] = best_page
        result['offers_reconciliation'] = True
        result['reconciliation_info'] = extract_time_info(best_page, 'Reconciliation')
    else:
        result['offers_reconciliation'] = False
        result['reconciliation_info'] = "No relevant page found"
        result['reconciliation_page'] = ""

    if candidate_pages['adoration']:
        best_page = choose_best_url(candidate_pages['adoration'], adoration_keywords, adoration_negative_keywords)
        result['adoration_page'] = best_page
        result['offers_adoration'] = True
        result['adoration_info'] = extract_time_info(best_page, 'Adoration')
    else:
        result['offers_adoration'] = False
        result['adoration_info'] = "No relevant page found"
        result['adoration_page'] = ""
        
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

    facts_to_save = []
    for result in results:
        parish_id = result.get('parish_id')
        if not parish_id:
            continue

        if result.get('offers_reconciliation') and result.get('reconciliation_info') != "Information not found":
            facts_to_save.append({
                'parish_id': parish_id,
                'fact_type': 'ReconciliationSchedule',
                'fact_value': result.get('reconciliation_info'),
                'fact_source_url': result.get('reconciliation_page')
            })
        
        if result.get('offers_adoration') and result.get('adoration_info') != "Information not found":
            facts_to_save.append({
                'parish_id': parish_id,
                'fact_type': 'AdorationSchedule',
                'fact_value': result.get('adoration_info'),
                'fact_source_url': result.get('adoration_page')
            })

    if not facts_to_save:
        logger.info("No facts to save to Supabase.")
        return

    try:
        supabase.table('ParishData').upsert(facts_to_save, on_conflict='parish_id,fact_type').execute()
        logger.info(f"Successfully saved {len(facts_to_save)} facts to Supabase table 'ParishData'.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during Supabase upsert: {e}", exc_info=True)


def main(num_parishes: int, parish_id: int = None):
    """Main function to run the scraping pipeline."""
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set in the environment.")
        return
    supabase: Client = create_client(supabase_url, supabase_key)

    parishes_to_process = get_parishes_to_process(supabase, num_parishes, parish_id)

    if not parishes_to_process:
        logger.info("No parish URLs to process. Exiting.")
        return

    logger.info(f"Processing {len(parishes_to_process)} parishes.")

    results = []
    for url, p_id in parishes_to_process:
        logger.info(f"Scraping {url} for parish {p_id}...")
        result = scrape_parish_data(url, p_id, supabase)
        result['parish_id'] = p_id
        try:
            parish_name = urlparse(url).netloc.replace('www.','')
        except IndexError:
            parish_name = url
        result['parish_name'] = parish_name
        results.append(result)
        logger.info(f"Completed scraping {url}")

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
    args = parser.parse_args()
    main(args.num_parishes, args.parish_id)