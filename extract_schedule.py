#!/usr/bin/env python
# coding: utf-8

import argparse
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


def choose_best_url(urls: list[str], keywords: list[str]) -> str:
    """Chooses the best URL from a list based on keyword matching in the URL path."""
    if not urls:
        return ""
    if len(urls) == 1:
        return urls[0]

    best_url = urls[0]
    max_score = -1

    for url in urls:
        score = 0
        url_path = urlparse(url).path.lower()
        for kw in keywords:
            if kw in url_path:
                score += 2 # Higher score for keyword in path
        
        # Bonus for being a more specific path
        if len(url_path.split('/')) > 2:
            score += 1

        if score > max_score:
            max_score = score
            best_url = url
            
    logger.info(f"Selected best URL from {len(urls)} candidates: {best_url}")
    return best_url


def scrape_parish_data(url: str) -> dict:
    """
    Scrapes a parish website to find the best pages for Reconciliation and Adoration info.
    """
    urls_to_visit = {url}
    visited_urls = set()
    candidate_pages = {'reconciliation': [], 'adoration': []}

    sitemap_urls = get_sitemap_urls(url)
    if sitemap_urls:
        urls_to_visit.update(sitemap_urls)

    logger.info(f"Starting scan with {len(urls_to_visit)} initial URLs.")

    while urls_to_visit and len(visited_urls) < MAX_PAGES_TO_SCAN:
        current_url = urls_to_visit.pop()
        if current_url in visited_urls:
            continue
        
        if re.search(r'\.(pdf|jpg|jpeg|png|gif|svg|zip|docx|xlsx|pptx|mp3|mp4|avi|mov)$', current_url, re.IGNORECASE):
            visited_urls.add(current_url)
            continue

        logger.debug(f"Checking {current_url} ({len(visited_urls) + 1}/{MAX_PAGES_TO_SCAN})")
        visited_urls.add(current_url)

        try:
            response = requests.get(current_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for a in soup.find_all('a', href=True):
                link = urljoin(current_url, a['href']).split('#')[0]
                if link.startswith(('http://', 'https://')) and link not in visited_urls:
                    urls_to_visit.add(link)

            page_text_lower = soup.get_text().lower()

            if any(kw in page_text_lower for kw in ['reconciliation', 'confession']):
                logger.info(f"Found 'Reconciliation' keywords on {current_url}")
                candidate_pages['reconciliation'].append(current_url)

            if 'adoration' in page_text_lower:
                logger.info(f"Found 'Adoration' keyword on {current_url}")
                candidate_pages['adoration'].append(current_url)

        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch or process {current_url}: {e}")

    if len(visited_urls) >= MAX_PAGES_TO_SCAN:
        logger.warning(f"Reached scan limit of {MAX_PAGES_TO_SCAN} pages for {url}.")

    # --- Analysis Step ---
    result = {'url': url, 'scraped_at': datetime.now(timezone.utc).isoformat()}
    
    if candidate_pages['reconciliation']:
        best_page = choose_best_url(candidate_pages['reconciliation'], ['reconciliation', 'confession', 'sacrament'])
        result['reconciliation_page'] = best_page
        result['offers_reconciliation'] = True
        result['reconciliation_info'] = extract_time_info(best_page, 'Reconciliation')
    else:
        result['offers_reconciliation'] = False
        result['reconciliation_info'] = "No relevant page found"
        result['reconciliation_page'] = ""

    if candidate_pages['adoration']:
        best_page = choose_best_url(candidate_pages['adoration'], ['adoration', 'eucharist'])
        result['adoration_page'] = best_page
        result['offers_adoration'] = True
        result['adoration_info'] = extract_time_info(best_page, 'Adoration')
    else:
        result['offers_adoration'] = False
        result['adoration_info'] = "No relevant page found"
        result['adoration_page'] = ""
        
    return result


def get_url_for_parish(supabase: Client, parish_id: int) -> list[str]:
    """Fetches the website URL for a single parish by its ID."""
    try:
        response = supabase.table('Parishes').select('Web').eq('id', parish_id).execute()
        if response.data:
            parish_url = response.data[0].get('Web')
            if parish_url:
                return [parish_url]
            else:
                logger.warning(f"Parish with ID {parish_id} found, but it has no website URL.")
        else:
            logger.warning(f"No parish found with ID {parish_id}.")
    except Exception as e:
        logger.error(f"Error fetching parish URL for ID {parish_id}: {e}")
    return []


def get_prioritized_urls(supabase: Client, num_parishes: int) -> list[str]:
    """Fetches parish URLs from Supabase and prioritizes them for scraping."""
    try:
        all_parishes_response = supabase.table('Parishes').select('Web').not_.is_('Web', 'null').execute()
        all_parish_urls = {p['Web'] for p in all_parishes_response.data if p['Web']}
        logger.info(f"Found {len(all_parish_urls)} parishes with websites in 'Parishes' table.")

        schedules_response = supabase.table('ParishSchedules').select('url, scraped_at').order('scraped_at').execute()
        parishes_with_schedules = {item['url'] for item in schedules_response.data}
        sorted_schedules = [item['url'] for item in schedules_response.data]
        logger.info(f"Found {len(parishes_with_schedules)} parishes in 'ParishSchedules' table.")

        parishes_to_scrape_new = [url for url in all_parish_urls if url not in parishes_with_schedules]
        logger.info(f"Found {len(parishes_to_scrape_new)} new parishes to scrape.")

        parishes_to_rescrape = [url for url in sorted_schedules if url in all_parish_urls]
        
        prioritized_urls = parishes_to_scrape_new + parishes_to_rescrape

        if num_parishes != 0:
            return prioritized_urls[:num_parishes]
        return prioritized_urls

    except Exception as e:
        logger.error(f"Error fetching and prioritizing parish URLs from Supabase: {e}")
        return []


def save_results_to_supabase(supabase: Client, results: list):
    """Saves the scraping results to the Supabase 'ParishSchedules' table."""
    if not results:
        logger.info("No results to save to Supabase.")
        return

    try:
        supabase.table('ParishSchedules').upsert(results, on_conflict='url').execute()
        logger.info(f"Successfully saved {len(results)} records to Supabase table 'ParishSchedules'.")
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

    if parish_id:
        parish_urls = get_url_for_parish(supabase, parish_id)
    else:
        parish_urls = get_prioritized_urls(supabase, num_parishes)

    if not parish_urls:
        logger.info("No parish URLs to process. Exiting.")
        return

    logger.info(f"Processing {len(parish_urls)} parishes.")

    results = []
    for url in parish_urls:
        logger.info(f"Scraping {url}...")
        result = scrape_parish_data(url)
        try:
            parish_name = urlparse(url).netloc.replace('www.','')
        except IndexError:
            parish_name = url
        result['parish_name'] = parish_name
        results.append(result)
        logger.info(f"Completed scraping {url}")

    save_results_to_supabase(supabase, results)


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