#!/usr/bin/env python3
"""
Main script to extract parish data from U.S. Catholic dioceses
"""

import argparse
import gc
import psutil
import os
from datetime import datetime, timezone

import config
from core.db import get_supabase_client
from core.driver import close_driver, setup_driver, get_protected_driver
from core.circuit_breaker import circuit_manager
from parish_extraction_core import (PatternDetector,
                                    analyze_parish_finder_quality,
                                    enhanced_safe_upsert_to_supabase)
from parish_extractors import (ensure_chrome_installed,
                               process_diocese_with_detailed_extraction)
from core.logger import get_logger

logger = get_logger(__name__)

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def force_garbage_collection():
    """Force garbage collection and log memory usage"""
    initial_memory = get_memory_usage()
    
    # Force garbage collection
    collected = gc.collect()
    
    final_memory = get_memory_usage()
    memory_freed = initial_memory - final_memory
    
    if memory_freed > 0:
        logger.info(f"  🧹 Memory cleanup: Freed {memory_freed:.1f} MB (collected {collected} objects)")
        logger.info(f"  💾 Current memory usage: {final_memory:.1f} MB")
    else:
        logger.debug(f"  💾 Current memory usage: {final_memory:.1f} MB (collected {collected} objects)")
    
    return final_memory

def main(diocese_id=None, num_parishes_per_diocese=config.DEFAULT_MAX_PARISHES_PER_DIOCESE, max_dioceses=config.DEFAULT_MAX_DIOCESES, monitoring_client=None):
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

            # Build initial list of dioceses
            for d in dioceses_with_dirs:
                details = url_to_details.get(d['diocese_url'])
                if details:
                    dioceses_to_process.append({
                        'id': details['id'],
                        'name': details['name'],
                        'url': d['diocese_url'],
                        'parish_directory_url': d['parish_directory_url']
                    })

            # Prioritize dioceses by last extraction attempt date (least recently attempted first)
            logger.info(f"  📅 Prioritizing {len(dioceses_to_process)} dioceses by extraction attempt recency...")

            # Get the last extraction attempt date for each diocese from DiocesesParishDirectory
            diocese_urls = [d['url'] for d in dioceses_to_process]
            extraction_attempts = supabase.table('DiocesesParishDirectory').select('diocese_url, last_extraction_attempt_at').in_('diocese_url', diocese_urls).execute()

            # Create mapping of diocese_url to last_extraction_attempt_at
            url_to_last_attempt = {}
            if extraction_attempts.data:
                for attempt in extraction_attempts.data:
                    url = attempt['diocese_url']
                    last_attempt = attempt['last_extraction_attempt_at']
                    # Handle None/null values - treat as never attempted (highest priority)
                    url_to_last_attempt[url] = last_attempt if last_attempt else ""

            # Add last attempt timestamp to each diocese for sorting
            diocese_last_extraction = {}
            for diocese in dioceses_to_process:
                diocese_url = diocese['url']
                last_attempt = url_to_last_attempt.get(diocese_url, "")
                diocese_last_extraction[diocese['id']] = last_attempt

                if last_attempt == "":
                    logger.debug(f"    {diocese['name']}: never attempted (highest priority)")
                else:
                    logger.debug(f"    {diocese['name']}: last attempted {last_attempt}")

            # Sort dioceses by last extraction attempt date (empty string sorts first, then oldest dates)
            dioceses_to_process.sort(key=lambda d: diocese_last_extraction.get(d['id'], ""))

            # Log the prioritization results
            never_attempted = [d['name'] for d in dioceses_to_process if diocese_last_extraction.get(d['id']) == ""]
            if never_attempted:
                logger.info(f"  🆕 {len(never_attempted)} dioceses never attempted (highest priority): {', '.join(never_attempted[:5])}{'...' if len(never_attempted) > 5 else ''}")

            previously_attempted = [d for d in dioceses_to_process if diocese_last_extraction.get(d['id']) != ""]
            if previously_attempted:
                oldest_name = previously_attempted[0]['name'] if previously_attempted else None
                newest_name = previously_attempted[-1]['name'] if previously_attempted else None
                oldest_date = diocese_last_extraction.get(previously_attempted[0]['id']) if previously_attempted else None
                newest_date = diocese_last_extraction.get(previously_attempted[-1]['id']) if previously_attempted else None
                logger.info(f"  📅 Extraction attempt priority: {oldest_name} ({oldest_date}) → {newest_name} ({newest_date})")

            # Log the first few dioceses to be processed for debugging
            first_five = dioceses_to_process[:5]
            logger.info(f"  🎯 Processing order (first 5): {[f'{d['name']} ({diocese_last_extraction.get(d['id'], 'never')})' for d in first_five]}")

            logger.info(f"  ✅ Diocese prioritization complete: processing from least to most recently attempted")

            # Apply diocese limit after prioritization
            if max_dioceses > 0 and len(dioceses_to_process) > max_dioceses:
                original_count = len(dioceses_to_process)
                dioceses_to_process = dioceses_to_process[:max_dioceses]
                logger.info(f"  📊 Applied diocese limit: processing {max_dioceses} of {original_count} dioceses")

    if not dioceses_to_process:
        logger.info("No dioceses to process.")
        return

    # Process each diocese with protected driver
    driver = get_protected_driver(timeout=45)
    if not driver:
        logger.error("Failed to setup Protected WebDriver.")
        return

    try:
        initial_memory = get_memory_usage()
        logger.info(f"  🚀 Starting parish extraction with {initial_memory:.1f} MB memory usage")
        logger.info(f"  🛡️ Circuit breaker protection enabled for all external requests")
        
        for i, diocese_info in enumerate(dioceses_to_process):
            logger.info(f"Processing {diocese_info['name']} (ID: {diocese_info['id']})...")

            # Update last extraction attempt timestamp for this diocese
            try:
                current_timestamp = datetime.now(timezone.utc)
                supabase.table('DiocesesParishDirectory').update({
                    'last_extraction_attempt_at': current_timestamp.isoformat()
                }).eq('diocese_url', diocese_info['url']).execute()
                logger.debug(f"  📅 Updated last_extraction_attempt_at for {diocese_info['name']}")
            except Exception as e:
                logger.warning(f"  ⚠️ Failed to update last_extraction_attempt_at for {diocese_info['name']}: {e}")

            # Process the diocese
            result = process_diocese_with_detailed_extraction(diocese_info, driver, num_parishes_per_diocese)

            # Save parishes to database
            if result['parishes_found']:
                enhanced_safe_upsert_to_supabase(
                    result['parishes_found'],
                    diocese_info['id'],
                    diocese_info['name'],
                    diocese_info['url'],
                    diocese_info['parish_directory_url'],
                    supabase,
                    monitoring_client
                )
            
            # Strategic garbage collection after each diocese
            if len(dioceses_to_process) > 1:  # Only log for multi-diocese runs
                logger.info(f"  📊 Completed diocese {i+1}/{len(dioceses_to_process)}")

                # Send diocese progress to monitoring dashboard
                if monitoring_client:
                    current_diocese_name = diocese_info['name']
                    progress_percentage = ((i + 1) / len(dioceses_to_process)) * 100

                    # Determine next diocese name for the log message
                    next_diocese_name = None
                    if i + 1 < len(dioceses_to_process):
                        next_diocese_name = dioceses_to_process[i + 1]['name']

                    # Send completion log for current diocese
                    monitoring_client.send_log(
                        f"Step 3 │ ✅ Finished Diocese {current_diocese_name}",
                        "INFO"
                    )

                    # Send starting log for next diocese (if exists)
                    if next_diocese_name:
                        monitoring_client.send_log(
                            f"Step 3 │ ▶️ Starting Diocese {next_diocese_name}",
                            "INFO"
                        )

                    # Update progress bar percentage
                    monitoring_client.update_extraction_status(
                        status="running",
                        current_diocese=next_diocese_name or "Extraction Complete",
                        progress_percentage=progress_percentage,
                        parishes_processed=i + 1,
                        total_parishes=len(dioceses_to_process)
                    )

                force_garbage_collection()
                
                # Additional cleanup for large runs
                if (i + 1) % 5 == 0:  # Every 5 dioceses
                    logger.info(f"  🔄 Deep cleanup after {i+1} dioceses...")
                    # Force more aggressive cleanup
                    for generation in range(3):
                        gc.collect(generation)
                    
                    current_memory = get_memory_usage()
                    memory_growth = current_memory - initial_memory
                    if memory_growth > 100:  # More than 100MB growth
                        logger.warning(f"  ⚠️ Memory usage has grown by {memory_growth:.1f} MB - consider restarting")
                        
    finally:
        # Final cleanup and circuit breaker reporting
        logger.info("  🧹 Final memory cleanup...")
        force_garbage_collection()
        
        # Log circuit breaker statistics
        logger.info("  📊 Circuit Breaker Final Report:")
        circuit_manager.log_summary()
        
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
    parser.add_argument(
        "--max_dioceses",
        type=int,
        default=config.DEFAULT_MAX_DIOCESES,
        help="Maximum number of dioceses to process. Set to 0 for no limit. Defaults to 5.",
    )
    args = parser.parse_args()

    config.validate_config()
    main(args.diocese_id, args.num_parishes_per_diocese, args.max_dioceses)
