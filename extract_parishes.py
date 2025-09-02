#!/usr/bin/env python3
"""
Main script to extract parish data from U.S. Catholic dioceses
"""

import argparse
import logging

import config
from core.db import get_supabase_client
from core.driver import close_driver, setup_driver
from parish_extraction_core import (PatternDetector,
                                    analyze_parish_finder_quality,
                                    enhanced_safe_upsert_to_supabase)
from parish_extractors import (ensure_chrome_installed,
                               process_diocese_with_detailed_extraction)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main(num_dioceses=config.DEFAULT_MAX_DIOCESES, num_parishes_per_diocese=config.DEFAULT_MAX_PARISHES_PER_DIOCESE):
    """
    Main function to extract parish information from diocese websites.
    """
    if not ensure_chrome_installed():
        logging.error("Chrome installation failed. Please install Chrome manually.")
        return

    supabase = get_supabase_client()
    if not supabase:
        logging.error("Failed to initialize Supabase client.")
        return

    # Get dioceses with parish directory URLs
    query = supabase.table('DiocesesParishDirectory').select(
        'diocese_url, parish_directory_url'
    ).not_.is_('parish_directory_url', 'null')

    if num_dioceses != 0:
        query = query.limit(num_dioceses)

    response = query.execute()
    dioceses = response.data if response.data else []

    if not dioceses:
        logging.info("No dioceses with parish directory URLs found to process.")
        return

    # Get diocese names
    diocese_urls = [d['diocese_url'] for d in dioceses]
    names_response = supabase.table('Dioceses').select(
        'Website, Name'
    ).in_('Website', diocese_urls).execute()

    url_to_name = {item['Website']: item['Name'] for item in names_response.data}

    # Process each diocese
    driver = setup_driver()
    if not driver:
        logging.error("Failed to setup WebDriver.")
        return

    try:
        for diocese in dioceses:
            diocese_info = {
                'name': url_to_name.get(diocese['diocese_url'], 'Unknown'),
                'url': diocese['diocese_url'],
                'parish_directory_url': diocese['parish_directory_url']
            }

            logging.info(f"Processing {diocese_info['name']}...")
            result = process_diocese_with_detailed_extraction(diocese_info, driver, num_parishes_per_diocese)

            # Save parishes to database
            if result['parishes_found']:
                enhanced_safe_upsert_to_supabase(
                    result['parishes_found'],
                    diocese_info['name'],
                    diocese_info['url'],
                    diocese_info['parish_directory_url'],
                    supabase
                )
    finally:
        close_driver()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract parish information from diocese websites.")
    parser.add_argument(
        "--num_dioceses",
        type=int,
        default=5,
        help="Maximum number of dioceses to extract from. Set to 0 for no limit. Defaults to 5.",
    )
    parser.add_argument(
        "--num_parishes_per_diocese",
        type=int,
        default=5,
        help="Maximum number of parishes to extract from each diocese. Set to 0 for no limit. Defaults to 5.",
    )
    args = parser.parse_args()

    config.validate_config()
    main(args.num_dioceses, args.num_parishes_per_diocese)
