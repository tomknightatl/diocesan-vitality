#!/usr/bin/env python3
"""
Respectful Parish Website Analysis with Blocking Detection

This script processes parish websites using respectful automation practices,
including robots.txt compliance, rate limiting, and blocking detection.
"""

import argparse
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from core.db import get_supabase_client
from core.logger import get_logger
from core.monitoring_client import MonitoringClient
from core.schedule_ai_extractor import ScheduleAIExtractor, save_ai_schedule_results
from core.schedule_keywords import load_keywords_from_database
from pipeline.respectful_automation import RespectfulAutomation

# Import helper functions from extract_schedule temporarily
# TODO: Move these functions to a shared utility module
from pipeline.extract_schedule import choose_best_url, get_parishes_to_process, get_sitemap_urls, get_suppression_urls

logger = get_logger(__name__)


def update_parish_blocking_data(supabase, parish_id: int, blocking_info: dict, robots_info: dict):
    """Update parish record with blocking detection data."""
    try:
        # Create human-readable status description
        if blocking_info.get("is_blocked"):
            if blocking_info.get("blocking_type") == "403_forbidden":
                status_description = "Parish website actively blocking automated access (403 Forbidden)"
            elif blocking_info.get("blocking_type") == "rate_limited":
                status_description = "Parish website rate limiting requests (429 Too Many Requests)"
            elif blocking_info.get("blocking_type") == "cloudflare_protection":
                status_description = "Parish website using Cloudflare bot protection"
            elif blocking_info.get("blocking_type") == "robots_txt_disallowed":
                status_description = "Parish website disallows automated access via robots.txt"
            else:
                status_description = f'Parish website blocking access ({blocking_info.get("blocking_type", "unknown")})'
        else:
            status_description = "Parish website accessible to automated requests"

        # Update parish record
        update_data = {
            "is_blocked": blocking_info.get("is_blocked", False),
            "blocking_type": blocking_info.get("blocking_type"),
            "blocking_evidence": {
                "evidence_list": blocking_info.get("evidence", []),
                "headers": blocking_info.get("headers", {}),
            },
            "status_code": blocking_info.get("status_code"),
            "robots_txt_check": robots_info,
            "respectful_automation_used": True,
            "status_description": status_description,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

        supabase.table("Parishes").update(update_data).eq("id", parish_id).execute()
        logger.info(f"✅ Updated parish {parish_id} blocking data: {status_description}")

    except Exception as e:
        logger.error(f"❌ Failed to update parish {parish_id} blocking data: {e}")


def extract_content_with_respectful_automation(url: str, automation: RespectfulAutomation, suppression_urls: set) -> tuple:
    """
    Extract content from a URL using respectful automation practices.

    Args:
        url: URL to extract content from
        automation: RespectfulAutomation instance
        suppression_urls: URLs to skip

    Returns:
        Tuple of (content_text, response_info)
    """
    if url in suppression_urls:
        logger.info(f"🚫 Skipping suppressed URL: {url}")
        return "", {"success": False, "error": "suppressed_url"}

    try:
        response, info = automation.respectful_get(url, timeout=15)

        if not response:
            logger.warning(f"⚠️ Could not fetch {url}: {info.get('error', 'Unknown error')}")
            return "", info

        if info["blocking_info"]["is_blocked"]:
            logger.warning(f"🚫 Website is blocking access: {url} - {info['blocking_info']['blocking_type']}")
            return "", info

        # Parse content
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove irrelevant elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        # Extract text content
        text_content = soup.get_text(separator=" ", strip=True)

        # Basic cleaning
        lines = [line.strip() for line in text_content.split("\n")]
        cleaned_lines = [line for line in lines if line and len(line) > 10]

        content = "\n".join(cleaned_lines)
        logger.info(f"✅ Successfully extracted {len(content)} characters from {url}")

        return content, info

    except Exception as e:
        logger.error(f"❌ Error extracting content from {url}: {e}")
        return "", {"success": False, "error": str(e)}


def process_parish_with_blocking_detection(
    parish_url: str, parish_id: int, supabase, automation: RespectfulAutomation, suppression_urls: set, max_pages: int = 10
) -> dict:
    """
    Process a parish website with respectful automation and blocking detection.

    Args:
        parish_url: Base parish website URL
        parish_id: Parish database ID
        supabase: Database client
        automation: RespectfulAutomation instance
        suppression_urls: URLs to avoid
        max_pages: Maximum pages to analyze

    Returns:
        Dict with processing results and blocking information
    """
    logger.info(f"🔄 [{parish_id}] Starting respectful processing for {parish_url}")

    # First, test the main parish URL for blocking
    logger.info(f"  🤖 [{parish_id}] Testing for blocking with respectful automation...")

    response, info = automation.respectful_get(parish_url, timeout=10)

    # Update parish blocking data regardless of success/failure
    blocking_info = info.get("blocking_info", {})
    robots_info = info.get("robots_info", {})

    update_parish_blocking_data(supabase, parish_id, blocking_info, robots_info)

    # If blocked, return early
    if blocking_info.get("is_blocked"):
        logger.warning(f"  🚫 [{parish_id}] Website is blocking access: {blocking_info.get('blocking_type')}")
        return {
            "parish_id": parish_id,
            "success": False,
            "error": "blocked",
            "blocking_info": blocking_info,
            "robots_info": robots_info,
        }

    # If request failed for other reasons
    if not response:
        logger.error(f"  ❌ [{parish_id}] Request failed: {info.get('error', 'Unknown error')}")
        return {
            "parish_id": parish_id,
            "success": False,
            "error": info.get("error", "request_failed"),
            "blocking_info": blocking_info,
            "robots_info": robots_info,
        }

    logger.info(f"  ✅ [{parish_id}] No blocking detected (HTTP {response.status_code})")

    # Continue with schedule extraction if not blocked
    try:
        # Load keywords for schedule detection
        recon_kw, recon_neg, ador_kw, ador_neg, mass_kw, mass_neg = load_keywords_from_database(supabase)

        # Get sitemap URLs for better coverage
        sitemap_urls = get_sitemap_urls(parish_url)
        urls_to_check = [parish_url] + sitemap_urls[:max_pages]

        logger.info(f"  🔍 [{parish_id}] Found {len(urls_to_check)} URLs to check for schedule content")

        # Find candidate pages
        candidate_pages = {"reconciliation": [], "adoration": []}
        pages_checked = 0

        for url in urls_to_check:
            if pages_checked >= max_pages:
                break

            try:
                content, url_info = extract_content_with_respectful_automation(url, automation, suppression_urls)

                if not content:
                    continue

                page_text = content.lower()

                # Check for reconciliation keywords
                if any(kw in page_text for kw in ["reconciliation", "confession", "penance"]):
                    candidate_pages["reconciliation"].append(url)
                    logger.info(f"  📝 [{parish_id}] Found reconciliation candidate: {url}")

                # Check for adoration keywords
                if any(kw in page_text for kw in ["adoration", "exposition", "blessed sacrament"]):
                    candidate_pages["adoration"].append(url)
                    logger.info(f"  ⛪ [{parish_id}] Found adoration candidate: {url}")

                pages_checked += 1

            except Exception as e:
                logger.warning(f"  ⚠️ [{parish_id}] Could not check {url}: {e}")
                continue

        # Process found pages with AI
        ai_extractor = ScheduleAIExtractor()
        extraction_results = {}

        # Process reconciliation pages
        if candidate_pages["reconciliation"]:
            best_recon_url = choose_best_url(
                candidate_pages["reconciliation"], recon_kw, recon_neg, urlparse(parish_url).netloc
            )

            logger.info(f"  🤖 [{parish_id}] Analyzing reconciliation page with AI: {best_recon_url}")
            recon_content, _ = extract_content_with_respectful_automation(best_recon_url, automation, suppression_urls)

            if recon_content:
                recon_result = ai_extractor.extract_schedule_from_content(recon_content, best_recon_url, "reconciliation")
                recon_result["parish_id"] = parish_id
                extraction_results["reconciliation"] = recon_result

        # Process adoration pages
        if candidate_pages["adoration"]:
            best_ador_url = choose_best_url(candidate_pages["adoration"], ador_kw, ador_neg, urlparse(parish_url).netloc)

            logger.info(f"  🤖 [{parish_id}] Analyzing adoration page with AI: {best_ador_url}")
            ador_content, _ = extract_content_with_respectful_automation(best_ador_url, automation, suppression_urls)

            if ador_content:
                ador_result = ai_extractor.extract_schedule_from_content(ador_content, best_ador_url, "adoration")
                ador_result["parish_id"] = parish_id
                extraction_results["adoration"] = ador_result

        # Save AI results if any found
        if extraction_results:
            results_list = [r for r in extraction_results.values() if r]
            save_ai_schedule_results(supabase, results_list)

        logger.info(f"  ✅ [{parish_id}] Completed processing - found {len(extraction_results)} schedule types")

        return {
            "parish_id": parish_id,
            "success": True,
            "schedules_found": len(extraction_results),
            "extraction_results": extraction_results,
            "blocking_info": blocking_info,
            "robots_info": robots_info,
        }

    except Exception as e:
        logger.error(f"  ❌ [{parish_id}] Error during schedule extraction: {e}")
        return {
            "parish_id": parish_id,
            "success": False,
            "error": str(e),
            "blocking_info": blocking_info,
            "robots_info": robots_info,
        }


def main(
    num_parishes: int = None,
    parish_id: int = None,
    max_pages_per_parish: int = 10,
    diocese_id: int = None,
    monitoring_client=None,
):
    """Main function for respectful parish processing with blocking detection."""

    logger.info("🚀 Starting respectful parish website analysis with blocking detection")
    if diocese_id:
        logger.info(f"📍 Filtering to diocese ID: {diocese_id}")

    supabase = get_supabase_client()
    if not supabase:
        logger.error("Could not initialize Supabase client")
        return

    # Initialize respectful automation
    automation = RespectfulAutomation()
    logger.info("Respectful automation initialized successfully")

    # Get parishes to process
    suppression_urls = get_suppression_urls(supabase)
    parishes_to_process = get_parishes_to_process(supabase, num_parishes, parish_id, diocese_id)

    if not parishes_to_process:
        logger.info("No parishes to process")
        return

    logger.info(f"Processing {len(parishes_to_process)} parishes with respectful automation")

    # Process statistics
    total_parishes = len(parishes_to_process)
    processed_count = 0
    blocked_count = 0
    accessible_count = 0
    schedule_found_count = 0
    start_time = time.time()

    for parish_url, p_id in parishes_to_process:
        processed_count += 1
        logger.info(f"🔄 [{processed_count}/{total_parishes}] Processing parish {p_id}: {parish_url}")

        # Fetch parish info for monitoring
        parish_info = None
        try:
            response = (
                supabase.table("Parishes")
                .select("id, name, address, Dioceses(name)")
                .eq("id", p_id)
                .execute()
            )
            if response.data:
                parish_data = response.data[0]
                parish_info = {
                    "name": parish_data.get("name", "Unknown Parish"),
                    "address": parish_data.get("address", "Unknown Address"),
                    "diocese_name": parish_data.get("Dioceses", {}).get("name", "Unknown Diocese")
                    if parish_data.get("Dioceses")
                    else "Unknown Diocese",
                }
        except Exception as e:
            logger.warning(f"Could not fetch parish info for {p_id}: {e}")
            parish_info = {
                "name": "Unknown Parish",
                "address": "Unknown Address",
                "diocese_name": "Unknown Diocese",
            }

        # Send "Visiting" message to monitoring
        if monitoring_client and parish_info:
            monitoring_client.send_log(
                f"Step 4 │ 🔍 [{processed_count}/{total_parishes}] Visiting {parish_info['name']} "
                f"→ <a href='{parish_url}' target='_blank'>{parish_url}</a>",
                "INFO",
                worker_type="schedule",
            )

        try:
            extraction_start = time.time()
            result = process_parish_with_blocking_detection(
                parish_url, p_id, supabase, automation, suppression_urls, max_pages_per_parish
            )
            extraction_duration = time.time() - extraction_start

            # Update statistics
            if result["blocking_info"].get("is_blocked"):
                blocked_count += 1
            else:
                accessible_count += 1

            schedules_found = result.get("schedules_found", 0)
            if schedules_found > 0:
                schedule_found_count += 1

            logger.info(f"✅ [{processed_count}/{total_parishes}] Completed parish {p_id}")

            # Send "Completed" message to monitoring
            if monitoring_client and parish_info:
                status_emoji = "✅" if schedules_found > 0 else "⚠️"
                monitoring_client.send_log(
                    f"Step 4 │ {status_emoji} [{processed_count}/{total_parishes}] Completed {parish_info['name']} "
                    f"({parish_info['address']}) - {schedules_found} schedule(s) found in {extraction_duration:.1f}s",
                    "INFO" if schedules_found > 0 else "WARNING",
                    worker_type="schedule",
                )

            # Send extraction_complete for Recent History
            if monitoring_client and hasattr(monitoring_client, "report_extraction_complete") and parish_info:
                # Construct mass_times from extraction results
                mass_times_parts = []
                extraction_results = result.get("extraction_results", {})
                if "reconciliation" in extraction_results:
                    recon_data = extraction_results["reconciliation"].get("extracted_data", {})
                    if recon_data.get("schedule_text"):
                        mass_times_parts.append(f"Reconciliation: {recon_data['schedule_text'][:50]}")
                if "adoration" in extraction_results:
                    ador_data = extraction_results["adoration"].get("extracted_data", {})
                    if ador_data.get("schedule_text"):
                        mass_times_parts.append(f"Adoration: {ador_data['schedule_text'][:50]}")

                mass_times = " | ".join(mass_times_parts) if mass_times_parts else "No schedules found"

                monitoring_client.report_extraction_complete(
                    diocese_name=parish_info["diocese_name"],
                    parish_name=parish_info["name"],
                    parish_url=parish_url,
                    parish_address=parish_info["address"],
                    schedules_found=schedules_found,
                    mass_times=mass_times,
                    duration=extraction_duration,
                    status="completed",
                )

        except Exception as e:
            logger.error(f"❌ [{processed_count}/{total_parishes}] Error processing parish {p_id}: {e}")
            continue

    # Send final summary to monitoring
    total_time = time.time() - start_time
    if monitoring_client:
        monitoring_client.send_log(
            f"Step 4 │ 🎉 Batch complete: {processed_count} parishes processed, "
            f"{schedule_found_count} with schedules in {total_time:.1f}s",
            "INFO",
            worker_type="schedule",
        )

    # Print final summary
    logger.info("🎉 Respectful parish analysis completed!")
    logger.info("=" * 50)
    logger.info(f"Total parishes processed: {processed_count}")
    logger.info(f"✅ Accessible: {accessible_count} ({accessible_count/processed_count*100:.1f}%)")
    logger.info(f"🚫 Blocked: {blocked_count} ({blocked_count/processed_count*100:.1f}%)")
    logger.info(f"📅 Schedules found: {schedule_found_count} ({schedule_found_count/processed_count*100:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Respectful parish website analysis with blocking detection")
    parser.add_argument("--num_parishes", type=int, help="Number of parishes to process (default: all)")
    parser.add_argument("--parish_id", type=int, help="Specific parish ID to process")
    parser.add_argument("--max_pages_per_parish", type=int, default=10, help="Maximum pages to analyze per parish")
    parser.add_argument("--diocese_id", type=int, help="Filter parishes to specific diocese ID")

    args = parser.parse_args()

    # Initialize monitoring client if MONITORING_URL is set
    import os

    monitoring_client = None
    monitoring_url = os.getenv("MONITORING_URL")
    if monitoring_url:
        monitoring_client = MonitoringClient(monitoring_url, worker_id="schedule-local")
        logger.info(f"Monitoring enabled: {monitoring_url}")

    main(
        num_parishes=args.num_parishes,
        parish_id=args.parish_id,
        max_pages_per_parish=args.max_pages_per_parish,
        diocese_id=args.diocese_id,
        monitoring_client=monitoring_client,
    )
