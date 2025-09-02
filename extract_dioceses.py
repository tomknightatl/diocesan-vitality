#!/usr/bin/env python
# coding: utf-8

import argparse
import logging
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from bs4 import BeautifulSoup

import config
from core.db import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraping.log"),
        logging.StreamHandler()
    ]
)

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
            logging.info(f"Attempt {attempt}: Fetching URL: {url}")
            response = requests.get(url, headers=headers, timeout=20)
            logging.info(f"Received status code: {response.status_code}")
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logging.warning(f"Attempt {attempt} failed with error: {e}")
            if attempt == retries:
                logging.error(f"All {retries} attempts failed for URL: {url}")
                return None
            sleep_time = backoff_factor * (2 ** (attempt - 1))
            logging.info(f"Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)

def extract_dioceses_data(soup):
    """
    Extracts dioceses information from the parsed HTML.
    Returns a list of dictionaries with diocese details.
    """
    dioceses = []
    diocese_containers = soup.find_all('div', class_='views-row')

    logging.info(f"Found {len(diocese_containers)} potential diocese containers")

    for i, container in enumerate(diocese_containers):
        logging.info(f"Processing container {i+1}")

        da_wrap = container.find('div', class_='da-wrap')
        if not da_wrap:
            logging.warning(f"No da-wrap found in container {i+1}")
            continue

        name_div = da_wrap.find('div', class_='da-title')
        diocese_name = name_div.get_text(strip=True) if name_div else "N/A"
        logging.info(f"Diocese name: {diocese_name}")

        address_div = da_wrap.find('div', class_='da-address')
        address_parts = []
        if address_div:
            for div in address_div.find_all('div', recursive=False):
                text = div.get_text(strip=True)
                if text:
                    address_parts.append(text)

        address = ", ".join(address_parts)
        logging.info(f"Address: {address}")

        website_div = da_wrap.find('div', class_='site')
        website_url = website_div.find('a')['href'] if website_div and website_div.find('a') else "N/A"
        logging.info(f"Website: {website_url}")

        dioceses.append({
            'Name': diocese_name,
            'Address': address,
            'Website': website_url,
            'extracted_at': datetime.now(timezone.utc).isoformat()
        })

    return dioceses

def main(max_dioceses=0):
    """Main function to extract and store dioceses information."""
    url = "https://www.usccb.org/about/bishops-and-dioceses/all-dioceses"
    soup = get_soup(url)

    if not soup:
        logging.error("Failed to fetch the dioceses page. Exiting.")
        return

    logging.info("Successfully fetched and parsed the dioceses page.")
    
    dioceses = extract_dioceses_data(soup)
    logging.info(f"Extracted information for {len(dioceses)} dioceses.")

    if not dioceses:
        logging.warning("No dioceses were extracted.")
        return

    if max_dioceses > 0:
        dioceses = dioceses[:max_dioceses]
        logging.info(f"Limiting extraction to {len(dioceses)} dioceses.")

    dioceses_df = pd.DataFrame(dioceses)
    logging.info(dioceses_df.head())

    supabase = get_supabase_client()
    if not supabase:
        logging.error("Could not initialize Supabase client. Exiting.")
        return

    try:
        data_to_insert = dioceses_df.to_dict('records')
        logging.info(f"\nAttempting to upsert {len(data_to_insert)} rows...")
        
        result = supabase.table('Dioceses').upsert(data_to_insert, on_conflict='Name').execute()

        if result.data:
            logging.info(f"✅ Successfully upserted {len(result.data)} rows!")
        else:
            logging.error("❌ Upsert returned no data")

    except Exception as e:
        logging.error(f"❌ Bulk upsert failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract dioceses information from the USCCB website.")
    parser.add_argument(
        "--max_dioceses",
        type=int,
        default=0,
        help="Maximum number of dioceses to extract. Set to 0 or None for no limit."
    )
    args = parser.parse_args()
    
    config.validate_config()
    main(args.max_dioceses)