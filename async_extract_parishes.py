#!/usr/bin/env python3
"""
Async Parish Extraction Script with concurrent processing capabilities.
Dramatically improves extraction performance through intelligent batching and parallel processing.
"""

import asyncio
import argparse
import gc
import psutil
import os
import time
from typing import List, Dict, Any
from datetime import datetime

import config
from core.db import get_supabase_client
from core.logger import get_logger
from core.async_driver import get_async_driver_pool, shutdown_async_driver_pool
from core.async_parish_extractor import get_async_parish_extractor
from parish_extraction_core import enhanced_safe_upsert_to_supabase, PatternDetector
from parish_extractors import ensure_chrome_installed

logger = get_logger(__name__)


def get_parish_directory_url_with_override(supabase, diocese_id: int, diocese_url: str) -> tuple:
    """
    Get parish directory URL with override support.

    Args:
        supabase: Supabase client
        diocese_id: Diocese ID
        diocese_url: Diocese website URL

    Returns:
        Tuple of (parish_directory_url, source) where source is 'override' or 'original'
    """
    try:
        # First, check for override
        override_response = supabase.table('DioceseParishDirectoryOverride').select(
            'parish_directory_url, found_method'
        ).eq('diocese_id', diocese_id).execute()

        if override_response.data:
            override_url = override_response.data[0]['parish_directory_url']
            found_method = override_response.data[0].get('found_method', 'override')
            logger.info(f"🔄 Using override parish directory URL for diocese {diocese_id}: {override_url} (method: {found_method})")
            return override_url, 'override'

        # Fallback to original table
        original_response = supabase.table('DiocesesParishDirectory').select(
            'parish_directory_url'
        ).eq('diocese_url', diocese_url).execute()

        if original_response.data:
            original_url = original_response.data[0]['parish_directory_url']
            logger.debug(f"📋 Using original parish directory URL for diocese {diocese_id}: {original_url}")
            return original_url, 'original'

        logger.warning(f"⚠️ No parish directory URL found for diocese {diocese_id} (URL: {diocese_url})")
        return None, None

    except Exception as e:
        logger.error(f"❌ Error fetching parish directory URL for diocese {diocese_id}: {e}")
        return None, None


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


class AsyncDioceseProcessor:
    """
    Async diocese processor with intelligent batching and parallel processing.
    Provides significant performance improvements over sequential processing.
    """
    
    def __init__(self, pool_size: int = 4, batch_size: int = 8, max_concurrent_dioceses: int = 2):
        self.pool_size = pool_size
        self.batch_size = batch_size
        self.max_concurrent_dioceses = max_concurrent_dioceses
        self.driver_pool = None
        self.parish_extractor = None
        self.processing_stats = {
            'total_dioceses': 0,
            'successful_dioceses': 0,
            'failed_dioceses': 0,
            'total_parishes_found': 0,
            'total_parishes_enhanced': 0,
            'total_processing_time': 0,
            'average_time_per_diocese': 0
        }
        
        logger.info(f"🚀 Async Diocese Processor initialized")
        logger.info(f"   • Pool size: {pool_size} drivers")
        logger.info(f"   • Batch size: {batch_size} requests")
        logger.info(f"   • Max concurrent dioceses: {max_concurrent_dioceses}")
    
    async def initialize(self):
        """Initialize async components"""
        logger.info("🔧 Initializing async diocese processor...")
        
        # Initialize driver pool
        self.driver_pool = await get_async_driver_pool(self.pool_size)
        
        # Initialize parish extractor
        self.parish_extractor = await get_async_parish_extractor(self.pool_size, self.batch_size)
        
        logger.info("✅ Async diocese processor ready")
    
    async def process_dioceses_concurrent(self, 
                                        dioceses_to_process: List[Dict],
                                        num_parishes_per_diocese: int = 5) -> Dict[str, Any]:
        """
        Process multiple dioceses concurrently with intelligent batching.
        
        Args:
            dioceses_to_process: List of diocese information dictionaries
            num_parishes_per_diocese: Maximum parishes to extract per diocese
            
        Returns:
            Dictionary with processing results and statistics
        """
        if not dioceses_to_process:
            return {'success': False, 'error': 'No dioceses to process'}
        
        if not self.driver_pool:
            await self.initialize()
        
        start_time = time.time()
        initial_memory = get_memory_usage()
        
        logger.info(f"🚀 Starting concurrent diocese processing")
        logger.info(f"   • Dioceses to process: {len(dioceses_to_process)}")
        logger.info(f"   • Max parishes per diocese: {num_parishes_per_diocese}")
        logger.info(f"   • Initial memory: {initial_memory:.1f} MB")
        
        results = {
            'successful_dioceses': [],
            'failed_dioceses': [],
            'total_parishes_extracted': 0,
            'processing_summary': {}
        }
        
        # Process dioceses in controlled batches
        diocese_batches = [
            dioceses_to_process[i:i + self.max_concurrent_dioceses]
            for i in range(0, len(dioceses_to_process), self.max_concurrent_dioceses)
        ]
        
        for batch_num, diocese_batch in enumerate(diocese_batches, 1):
            logger.info(f"📦 Processing diocese batch {batch_num}/{len(diocese_batches)} "
                       f"({len(diocese_batch)} dioceses)")
            
            # Create concurrent tasks for this batch
            batch_tasks = []
            for diocese_info in diocese_batch:
                task = asyncio.create_task(
                    self._process_single_diocese_async(diocese_info, num_parishes_per_diocese)
                )
                batch_tasks.append(task)
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process batch results
            for diocese_info, result in zip(diocese_batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Diocese {diocese_info['name']} failed: {result}")
                    results['failed_dioceses'].append({
                        'diocese_info': diocese_info,
                        'error': str(result)
                    })
                    self.processing_stats['failed_dioceses'] += 1
                else:
                    logger.info(f"✅ Diocese {diocese_info['name']} completed: "
                               f"{result['parishes_count']} parishes extracted")
                    results['successful_dioceses'].append(result)
                    results['total_parishes_extracted'] += result['parishes_count']
                    self.processing_stats['successful_dioceses'] += 1
                    self.processing_stats['total_parishes_found'] += result['parishes_count']
            
            # Memory management between batches
            if batch_num < len(diocese_batches):
                logger.info(f"  🧹 Inter-batch cleanup...")
                current_memory = force_garbage_collection()
                
                # Small delay between batches
                await asyncio.sleep(2.0)
        
        # Final statistics
        total_time = time.time() - start_time
        final_memory = get_memory_usage()
        
        self.processing_stats.update({
            'total_dioceses': len(dioceses_to_process),
            'total_processing_time': total_time,
            'average_time_per_diocese': total_time / max(len(dioceses_to_process), 1)
        })
        
        results['processing_summary'] = {
            'total_time': total_time,
            'average_time_per_diocese': self.processing_stats['average_time_per_diocese'],
            'memory_usage': {
                'initial': initial_memory,
                'final': final_memory,
                'peak_growth': final_memory - initial_memory
            },
            'performance_metrics': {
                'dioceses_per_minute': (len(dioceses_to_process) / (total_time / 60)),
                'parishes_per_minute': (results['total_parishes_extracted'] / (total_time / 60)),
                'success_rate': (self.processing_stats['successful_dioceses'] / 
                               max(len(dioceses_to_process), 1)) * 100
            }
        }
        
        # Log comprehensive results
        self._log_final_results(results)
        
        return results
    
    async def _process_single_diocese_async(self, diocese_info: Dict, max_parishes: int) -> Dict[str, Any]:
        """Process a single diocese with async parish detail extraction"""
        diocese_name = diocese_info['name']
        diocese_id = diocese_info['id']
        parish_directory_url = diocese_info['parish_directory_url']
        
        logger.info(f"🔍 Processing {diocese_name} (async mode)")
        
        result = {
            'diocese_id': diocese_id,
            'diocese_name': diocese_name,
            'diocese_url': diocese_info['url'],
            'parish_directory_url': parish_directory_url,
            'parishes_count': 0,
            'enhanced_parishes': 0,
            'extraction_time': 0,
            'success': False
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Load main parish directory page
            def load_parish_directory(driver):
                """Load parish directory and return parsed content"""
                driver.get(parish_directory_url)
                return driver.page_source
            
            html_content = await self.driver_pool.submit_request(
                url=parish_directory_url,
                callback=load_parish_directory,
                priority=1
            )
            
            # Step 2: Extract basic parish information (synchronous for now)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Detect pattern and extract parishes
            detector = PatternDetector()
            pattern = detector.detect_pattern(html_content, parish_directory_url)
            
            # Use existing synchronous extraction logic for basic parish info
            # This could be further optimized in future iterations
            parishes_found = await self._extract_basic_parish_info_async(
                soup, pattern, diocese_info, max_parishes
            )
            
            if not parishes_found:
                result['success'] = False
                result['error'] = 'No parishes found'
                return result
            
            logger.info(f"   📋 Found {len(parishes_found)} parishes for {diocese_name}")
            
            # Step 3: Enhanced concurrent parish detail extraction
            if parishes_found:
                enhanced_parishes = await self.parish_extractor.extract_parish_details_concurrent(
                    parishes_found, diocese_name, max_concurrent=self.batch_size
                )
                
                result['parishes_count'] = len(enhanced_parishes)
                result['enhanced_parishes'] = sum(1 for p in enhanced_parishes 
                                                 if getattr(p, 'enhanced_extraction', False))
                
                # Step 4: Save to database
                if enhanced_parishes:
                    supabase = get_supabase_client()
                    enhanced_safe_upsert_to_supabase(
                        enhanced_parishes,
                        diocese_id,
                        diocese_name,
                        diocese_info['url'],
                        parish_directory_url,
                        supabase
                    )
            
            result['success'] = True
            
        except Exception as e:
            logger.error(f"❌ Error processing {diocese_name}: {e}")
            result['error'] = str(e)
        
        finally:
            result['extraction_time'] = time.time() - start_time
        
        return result
    
    async def _extract_basic_parish_info_async(self, soup, pattern, diocese_info, max_parishes):
        """Extract basic parish information (placeholder for now - could be optimized further)"""
        # For now, use existing synchronous logic
        # This is a good candidate for future async optimization
        try:
            from parish_extractors import process_diocese_with_detailed_extraction
            from core.driver import get_protected_driver
            
            # This is a temporary bridge - ideally we'd make this fully async
            driver = get_protected_driver()
            if not driver:
                return []
            
            result = process_diocese_with_detailed_extraction(diocese_info, driver, max_parishes)
            driver.quit()
            
            return result.get('parishes_found', [])
            
        except Exception as e:
            logger.error(f"Error in basic parish extraction: {e}")
            return []
    
    def _log_final_results(self, results: Dict[str, Any]):
        """Log comprehensive final results"""
        summary = results['processing_summary']
        metrics = summary['performance_metrics']
        
        logger.info("🎯 Async Diocese Processing Results:")
        logger.info("=" * 50)
        logger.info(f"✅ Successful dioceses: {len(results['successful_dioceses'])}")
        logger.info(f"❌ Failed dioceses: {len(results['failed_dioceses'])}")
        logger.info(f"📊 Total parishes extracted: {results['total_parishes_extracted']}")
        logger.info(f"⏱️ Total processing time: {summary['total_time']:.2f}s")
        logger.info(f"⚡ Performance:")
        logger.info(f"   • {metrics['dioceses_per_minute']:.1f} dioceses/minute")
        logger.info(f"   • {metrics['parishes_per_minute']:.1f} parishes/minute")
        logger.info(f"   • {metrics['success_rate']:.1f}% success rate")
        logger.info(f"💾 Memory:")
        logger.info(f"   • Initial: {summary['memory_usage']['initial']:.1f} MB")
        logger.info(f"   • Final: {summary['memory_usage']['final']:.1f} MB")
        logger.info(f"   • Growth: {summary['memory_usage']['peak_growth']:.1f} MB")
    
    async def shutdown(self):
        """Shutdown async components"""
        logger.info("🛑 Shutting down async diocese processor...")
        
        if self.parish_extractor:
            self.parish_extractor.log_stats()
        
        await shutdown_async_driver_pool()
        logger.info("✅ Async diocese processor shutdown complete")


async def main_async(diocese_id=None, num_parishes_per_diocese=config.DEFAULT_MAX_PARISHES_PER_DIOCESE,
                    pool_size=4, batch_size=8, max_concurrent_dioceses=2):
    """
    Main async function for parish extraction with concurrent processing.
    """
    if not ensure_chrome_installed():
        logger.error("Chrome installation failed. Please install Chrome manually.")
        return

    supabase = get_supabase_client()
    if not supabase:
        logger.error("Failed to initialize Supabase client.")
        return

    # Get dioceses to process (same logic as sync version)
    dioceses_to_process = []
    if diocese_id:
        response = supabase.table('Dioceses').select('id, Name, Website').eq('id', diocese_id).execute()
        if response.data:
            d = response.data[0]
            parish_directory_url, source = get_parish_directory_url_with_override(
                supabase, d['id'], d['Website']
            )
            if parish_directory_url:
                dioceses_to_process.append({
                    'id': d['id'],
                    'name': d['Name'],
                    'url': d['Website'],
                    'parish_directory_url': parish_directory_url,
                    'url_source': source  # Track whether this came from override or original
                })
                logger.info(f"✅ Found parish directory URL for {d['Name']} (source: {source})")
            else:
                logger.warning(f"No parish directory URL found for diocese {d['Name']}.")
    else:
        # Get all dioceses and check for both override and original URLs
        all_dioceses_response = supabase.table('Dioceses').select('id, Name, Website').execute()
        if all_dioceses_response.data:
            for diocese in all_dioceses_response.data:
                diocese_id = diocese['id']
                diocese_name = diocese['Name']
                diocese_url = diocese['Website']

                parish_directory_url, source = get_parish_directory_url_with_override(
                    supabase, diocese_id, diocese_url
                )

                if parish_directory_url:
                    dioceses_to_process.append({
                        'id': diocese_id,
                        'name': diocese_name,
                        'url': diocese_url,
                        'parish_directory_url': parish_directory_url,
                        'url_source': source
                    })
                    logger.debug(f"📋 Added {diocese_name} to processing queue (source: {source})")
                else:
                    logger.debug(f"⏭️ Skipping {diocese_name} - no parish directory URL found")

        logger.info(f"🎯 Found {len(dioceses_to_process)} dioceses with parish directory URLs")

    if not dioceses_to_process:
        logger.info("No dioceses to process.")
        return

    # Process dioceses with async processor
    processor = AsyncDioceseProcessor(pool_size, batch_size, max_concurrent_dioceses)
    
    try:
        results = await processor.process_dioceses_concurrent(
            dioceses_to_process, 
            num_parishes_per_diocese
        )
        
        # Final cleanup
        logger.info("  🧹 Final memory cleanup...")
        force_garbage_collection()
        
        return results
        
    finally:
        await processor.shutdown()


def main(diocese_id=None, num_parishes_per_diocese=config.DEFAULT_MAX_PARISHES_PER_DIOCESE,
         pool_size=4, batch_size=8, max_concurrent_dioceses=2):
    """
    Synchronous wrapper for the async main function.
    """
    return asyncio.run(main_async(
        diocese_id, num_parishes_per_diocese, 
        pool_size, batch_size, max_concurrent_dioceses
    ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract parish information with async concurrent processing.")
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
        "--pool_size",
        type=int,
        default=4,
        help="WebDriver pool size for concurrent requests. Defaults to 4.",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=8,
        help="Batch size for concurrent parish detail requests. Defaults to 8.",
    )
    parser.add_argument(
        "--max_concurrent_dioceses",
        type=int,
        default=2,
        help="Maximum dioceses to process concurrently. Defaults to 2.",
    )
    
    args = parser.parse_args()

    config.validate_config()
    main(
        args.diocese_id, 
        args.num_parishes_per_diocese,
        args.pool_size,
        args.batch_size,
        args.max_concurrent_dioceses
    )