#!/usr/bin/env python
# coding: utf-8

import argparse
import time
from datetime import datetime, timezone
import re # Added this line

import pandas as pd
import requests
from bs4 import BeautifulSoup

import config
from core.db import get_supabase_client
from core.logger import get_logger

logger = get_logger(__name__)

def get_soup(url, retries=3, backoff_factor=1.0):
    """
    Fetches the content at the given URL and returns a BeautifulSoup object.
    Implements retries with exponential backoff in case of request failures.
    """
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/58.0.3029.110 Safari/537.3'),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    }

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Attempt {attempt}: Fetching URL: {url}")
            response = requests.get(url, headers=headers, timeout=20)
            logger.info(f"Received status code: {response.status_code}")
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt} failed with error: {e}")
            if attempt == retries:
                logger.error(f"All {retries} attempts failed for URL: {url}")
                return None
            sleep_time = backoff_factor * (2 ** (attempt - 1))
            logger.info(f"Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)

def extract_dioceses_data(soup):
    """
    Extracts dioceses information from the parsed HTML.
    Returns a list of dictionaries with diocese details.
    """
    dioceses = []
    diocese_containers = soup.find_all('div', class_='views-row')

    logger.info(f"Found {len(diocese_containers)} potential diocese containers")

    for i, container in enumerate(diocese_containers):
        logger.info(f"Processing container {i+1}")

        da_wrap = container.find('div', class_='da-wrap')
        if not da_wrap:
            logger.warning(f"No da-wrap found in container {i+1}")
            continue

        name_div = da_wrap.find('div', class_='da-title')
        diocese_name = name_div.get_text(strip=True) if name_div else "N/A"
        logger.info(f"Diocese name: {diocese_name}")

        website_div = da_wrap.find('div', class_='site')
        website_url = website_div.find('a')['href'] if website_div and website_div.find('a') else "N/A"
        logger.info(f"Website: {website_url}")

        address_div = da_wrap.find('div', class_='da-address')
        address = ""
        if address_div:
            full_address_text = address_div.get_text(separator=" ", strip=True)
            # Remove website URL from the address text if it's present
            if website_url != "N/A" and website_url in full_address_text:
                full_address_text = full_address_text.replace(website_url, "").strip()
            
            # Clean up multiple spaces and newlines
            address = re.sub(r'\s+', ' ', full_address_text).strip()
            address = re.sub(r' ,', ',', address).strip() # Add this line
            # Further refinement: remove common address separators if they appear at start/end
            address = address.strip(',').strip()
        logger.info(f"Address: {address}")

        dioceses.append({
            'Name': diocese_name,
            'Address': address,
            'Website': website_url,
            'extracted_at': datetime.now(timezone.utc).isoformat()
        })

    return dioceses

def main(max_dioceses=config.DEFAULT_MAX_DIOCESES):
    """Main function to extract and store dioceses information."""
    url = "https://www.usccb.org/about/bishops-and-dioceses/all-dioceses"
    soup = get_soup(url)

    if not soup:
        logger.error("Failed to fetch the dioceses page. Exiting.")
        return

    logger.info("Successfully fetched and parsed the dioceses page.")
    
    dioceses = extract_dioceses_data(soup)
    logger.info(f"Extracted information for {len(dioceses)} dioceses.")

    if not dioceses:
        logger.warning("No dioceses were extracted.")
        return

    if max_dioceses > 0:
        dioceses = dioceses[:max_dioceses]
        logger.info(f"Limiting extraction to {len(dioceses)} dioceses.")

    dioceses_df = pd.DataFrame(dioceses)
    logger.info(dioceses_df.head())

    supabase = get_supabase_client()
    if not supabase:
        logger.error("Could not initialize Supabase client. Exiting.")
        return

    try:
        data_to_insert = dioceses_df.to_dict('records')
        logger.info(f"\nAttempting to upsert {len(data_to_insert)} rows...")
        
        result = supabase.table('Dioceses').upsert(data_to_insert, on_conflict='Name').execute()

        if result.data:
            logger.info(f"✅ Successfully upserted {len(result.data)} rows!")
        else:
            logger.error("❌ Upsert returned no data")

    except Exception as e:
        logger.error(f"❌ Bulk upsert failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract dioceses information from the USCCB website.")
    parser.add_argument(
        "--max_dioceses",
        type=int,
        default=5,
        help="Maximum number of dioceses to extract. Set to 0 or None for no limit."
    )
    args = parser.parse_args()
    
    config.validate_config()
    main(args.max_dioceses)
