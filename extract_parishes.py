#!/usr/bin/env python3
"""
Main script to extract parish data from U.S. Catholic dioceses
"""

import argparse

import config
from core.db import get_supabase_client
from core.driver import close_driver, setup_driver
from parish_extraction_core import (PatternDetector,
                                    analyze_parish_finder_quality,
                                    enhanced_safe_upsert_to_supabase)
from parish_extractors import (ensure_chrome_installed,
                               process_diocese_with_detailed_extraction)
from core.logger import get_logger

logger = get_logger(__name__)

def main(diocese_id=None, num_parishes_per_diocese=config.DEFAULT_MAX_PARISHES_PER_DIOCESE):
    """
    Main function to extract parish information from diocese websites.
    """
    if not ensure_chrome_installed():
        logger.error("Chrome installation failed. Please install Chrome manually.")
        return

    supabase = get_supabase_client()
    if not supabase:
        logger.error("Failed to initialize Supabase client.")
        return

    dioceses_to_process = []
    if diocese_id:
        # Fetch the specific diocese by ID
        response = supabase.table('Dioceses').select('id, Name, Website').eq('id', diocese_id).execute()
        if response.data:
            d = response.data[0]
            # Now get its parish directory URL
            dir_response = supabase.table('DiocesesParishDirectory').select('parish_directory_url').eq('diocese_url', d['Website']).execute()
            if dir_response.data:
                dioceses_to_process.append({
                    'id': d['id'],
                    'name': d['Name'],
                    'url': d['Website'],
                    'parish_directory_url': dir_response.data[0]['parish_directory_url']
                })
            else:
                logger.warning(f"No parish directory URL found for diocese {d['Name']}.")
    else:
        # Fetch all dioceses with parish directory URLs (original logic)
        query = supabase.table('DiocesesParishDirectory').select(
            'diocese_url, parish_directory_url'
        ).not_.is_('parish_directory_url', 'null')
        response = query.execute()
        dioceses_with_dirs = response.data if response.data else []
        if dioceses_with_dirs:
            urls = [d['diocese_url'] for d in dioceses_with_dirs]
            names_response = supabase.table('Dioceses').select('id, Name, Website').in_('Website', urls).execute()
            url_to_details = {item['Website']: {'id': item['id'], 'name': item['Name']} for item in names_response.data}
            for d in dioceses_with_dirs:
                details = url_to_details.get(d['diocese_url'])
                if details:
                    dioceses_to_process.append({
                        'id': details['id'],
                        'name': details['name'],
                        'url': d['diocese_url'],
                        'parish_directory_url': d['parish_directory_url']
                    })

    if not dioceses_to_process:
        logger.info("No dioceses to process.")
        return

    # Process each diocese
    driver = setup_driver()
    if not driver:
        logger.error("Failed to setup WebDriver.")
        return

    try:
        for diocese_info in dioceses_to_process:
            logger.info(f"Processing {diocese_info['name']} (ID: {diocese_info['id']})...")
            result = process_diocese_with_detailed_extraction(diocese_info, driver, num_parishes_per_diocese)

            # Save parishes to database
            if result['parishes_found']:
                enhanced_safe_upsert_to_supabase(
                    result['parishes_found'],
                    diocese_info['id'],
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
        "--diocese_id",
        type=int,
        default=None,
        help="ID of a specific diocese to process. If not provided, processes all.",
    )
    parser.add_argument(
        "--num_parishes_per_diocese",
        type=int,
        default=5,
        help="Maximum number of parishes to extract from each diocese. Set to 0 for no limit. Defaults to 5.",
    )
    args = parser.parse_args()

    config.validate_config()
    main(args.diocese_id, args.num_parishes_per_diocese)
