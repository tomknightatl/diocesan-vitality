#!/usr/bin/env python3
"""
Main script to extract parish data from U.S. Catholic dioceses
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Import extraction modules
from parish_extraction_core import (
    setup_enhanced_driver,
    PatternDetector,
    enhanced_safe_upsert_to_supabase,
    analyze_parish_finder_quality
)
from parish_extractors import (
    ensure_chrome_installed,
    process_diocese_with_detailed_extraction
)

# Load environment variables
load_dotenv()

def main():
    import argparse

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

    # Ensure Chrome is installed
    if not ensure_chrome_installed():
        print("Chrome installation failed. Please install Chrome manually.")
        return
    
    # Initialize Supabase
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )
    
    # Get dioceses with parish directory URLs
    query = supabase.table('DiocesesParishDirectory').select(
        'diocese_url, parish_directory_url'
    ).not_.is_('parish_directory_url', 'null')
    
    if args.num_dioceses != 0:
        query = query.limit(args.num_dioceses)
    
    response = query.execute()
    
    dioceses = response.data if response.data else []
    
    # Get diocese names
    diocese_urls = [d['diocese_url'] for d in dioceses]
    names_response = supabase.table('Dioceses').select(
        'Website, Name'
    ).in_('Website', diocese_urls).execute()
    
    url_to_name = {item['Website']: item['Name'] for item in names_response.data}
    
    # Process each diocese
    driver = setup_enhanced_driver()
    
    try:
        for diocese in dioceses:
            diocese_info = {
                'name': url_to_name.get(diocese['diocese_url'], 'Unknown'),
                'url': diocese['diocese_url'],
                'parish_directory_url': diocese['parish_directory_url']
            }
            
            print(f"Processing {diocese_info['name']}...")
            result = process_diocese_with_detailed_extraction(diocese_info, driver, args.num_parishes_per_diocese)
            
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
        driver.quit()

if __name__ == "__main__":
    main()