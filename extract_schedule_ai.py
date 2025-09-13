#!/usr/bin/env python3
"""
AI-Enhanced Schedule Extraction for Parish Websites

This script combines traditional keyword-based page discovery with AI-powered 
content analysis to accurately extract parish Adoration and Reconciliation schedules.
"""

import argparse
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

import config
from core.logger import get_logger
from core.db import get_supabase_client
from core.schedule_keywords import load_keywords_from_database
from core.schedule_ai_extractor import ScheduleAIExtractor, save_ai_schedule_results
from extract_schedule import (
    get_parishes_to_process, 
    get_suppression_urls,
    get_sitemap_urls,
    choose_best_url,
    requests_session,
    make_request_with_delay
)

logger = get_logger(__name__)


def extract_relevant_content_for_ai(url: str, suppression_urls: set) -> str:
    """
    Extract and clean content from a URL for AI processing.
    
    Args:
        url: URL to extract content from
        suppression_urls: URLs to skip
        
    Returns:
        Cleaned text content suitable for AI analysis
    """
    if url in suppression_urls:
        logger.info(f"Skipping suppressed URL: {url}")
        return ""
        
    try:
        response = make_request_with_delay(requests_session, url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove irrelevant elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
            
        # Extract text content
        text_content = soup.get_text(separator=' ', strip=True)
        
        # Basic cleaning
        lines = [line.strip() for line in text_content.split('\n')]
        cleaned_lines = [line for line in lines if line and len(line) > 10]
        
        return '\n'.join(cleaned_lines)
        
    except Exception as e:
        logger.warning(f"Could not extract content from {url}: {e}")
        return ""


def find_schedule_pages_with_ai(parish_url: str, parish_id: int, supabase, 
                               suppression_urls: set, max_pages: int = 50) -> dict:
    """
    Find and analyze potential schedule pages using keyword-based discovery + AI analysis.
    
    Args:
        parish_url: Base parish website URL
        parish_id: Parish database ID
        supabase: Database client
        suppression_urls: URLs to avoid
        max_pages: Maximum pages to analyze
        
    Returns:
        Dict with AI extraction results for both schedule types
    """
    logger.info(f"Starting AI-enhanced schedule extraction for parish {parish_id}: {parish_url}")
    
    # Load keywords from database
    recon_kw, recon_neg, ador_kw, ador_neg, mass_kw, mass_neg = load_keywords_from_database(supabase)
    
    # Discover candidate pages using existing keyword logic
    candidate_pages = {'reconciliation': [], 'adoration': []}
    
    # Get sitemap URLs for better coverage
    sitemap_urls = get_sitemap_urls(parish_url)
    urls_to_check = [parish_url] + sitemap_urls[:max_pages]
    
    logger.info(f"Checking {len(urls_to_check)} URLs for schedule content")
    
    # Find pages with relevant keywords
    pages_checked = 0
    for url in urls_to_check:
        if pages_checked >= max_pages:
            break
            
        try:
            response = make_request_with_delay(requests_session, url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Check for reconciliation keywords
            if any(kw in page_text for kw in ['reconciliation', 'confession', 'penance']):
                candidate_pages['reconciliation'].append(url)
                logger.info(f"Found reconciliation candidate: {url}")
                
            # Check for adoration keywords  
            if any(kw in page_text for kw in ['adoration', 'exposition', 'blessed sacrament']):
                candidate_pages['adoration'].append(url)
                logger.info(f"Found adoration candidate: {url}")
                
            pages_checked += 1
            
        except Exception as e:
            logger.warning(f"Could not check {url}: {e}")
            continue
    
    # Initialize AI extractor
    ai_extractor = ScheduleAIExtractor()
    results = {}
    
    # Process reconciliation pages with AI
    if candidate_pages['reconciliation']:
        best_recon_url = choose_best_url(
            candidate_pages['reconciliation'], 
            recon_kw, recon_neg, 
            urlparse(parish_url).netloc
        )
        
        logger.info(f"Analyzing reconciliation page with AI: {best_recon_url}")
        recon_content = extract_relevant_content_for_ai(best_recon_url, suppression_urls)
        
        if recon_content:
            recon_result = ai_extractor.extract_schedule_from_content(
                recon_content, best_recon_url, "reconciliation"
            )
            recon_result['parish_id'] = parish_id
            results['reconciliation'] = recon_result
        else:
            results['reconciliation'] = ai_extractor._get_empty_result("No content extracted")
    else:
        logger.info("No reconciliation candidate pages found")
        results['reconciliation'] = ai_extractor._get_empty_result("No candidate pages found")
    
    # Process adoration pages with AI
    if candidate_pages['adoration']:
        best_ador_url = choose_best_url(
            candidate_pages['adoration'],
            ador_kw, ador_neg,
            urlparse(parish_url).netloc
        )
        
        logger.info(f"Analyzing adoration page with AI: {best_ador_url}")
        ador_content = extract_relevant_content_for_ai(best_ador_url, suppression_urls)
        
        if ador_content:
            ador_result = ai_extractor.extract_schedule_from_content(
                ador_content, best_ador_url, "adoration"
            )
            ador_result['parish_id'] = parish_id
            results['adoration'] = ador_result
        else:
            results['adoration'] = ai_extractor._get_empty_result("No content extracted")
    else:
        logger.info("No adoration candidate pages found")  
        results['adoration'] = ai_extractor._get_empty_result("No candidate pages found")
    
    return results


def main(num_parishes: int, parish_id: int = None, max_pages_per_parish: int = 50):
    """Main function for AI-enhanced schedule extraction."""
    
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Could not initialize Supabase client")
        return
        
    suppression_urls = get_suppression_urls(supabase)
    parishes_to_process = get_parishes_to_process(supabase, num_parishes, parish_id)
    
    if not parishes_to_process:
        logger.info("No parishes to process")
        return
        
    logger.info(f"Processing {len(parishes_to_process)} parishes with AI-enhanced extraction")
    
    all_results = []
    
    for parish_url, p_id in parishes_to_process:
        logger.info(f"Processing parish {p_id}: {parish_url}")
        
        try:
            # Extract schedules using AI
            parish_results = find_schedule_pages_with_ai(
                parish_url, p_id, supabase, suppression_urls, max_pages_per_parish
            )
            
            # Add to results
            if parish_results.get('reconciliation'):
                all_results.append(parish_results['reconciliation'])
            if parish_results.get('adoration'):
                all_results.append(parish_results['adoration'])
                
            # Save results immediately for this parish
            parish_results_list = [r for r in parish_results.values() if r]
            save_ai_schedule_results(supabase, parish_results_list)
            
            logger.info(f"Completed AI extraction for parish {p_id}")
            
        except Exception as e:
            logger.error(f"Error processing parish {p_id}: {e}")
            continue
            
        # Respectful delay between parishes
        time.sleep(2)
    
    logger.info(f"AI-enhanced schedule extraction completed. Processed {len(all_results)} results.")
    
    # Print summary statistics
    high_confidence = len([r for r in all_results if r.get('confidence_score', 0) >= 80])
    found_schedules = len([r for r in all_results if r.get('schedule_found', False)])
    weekly_schedules = len([r for r in all_results if r.get('has_weekly_schedule', False)])
    
    logger.info(f"Summary: {found_schedules} schedules found, {weekly_schedules} weekly schedules, "
               f"{high_confidence} high-confidence results")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="AI-enhanced parish schedule extraction")
    parser.add_argument("--num_parishes", type=int, default=5, 
                       help="Number of parishes to process")
    parser.add_argument("--parish_id", type=int, 
                       help="Specific parish ID to process")
    parser.add_argument("--max_pages_per_parish", type=int, default=50,
                       help="Maximum pages to analyze per parish")
    
    args = parser.parse_args()
    
    main(args.num_parishes, args.parish_id, args.max_pages_per_parish)