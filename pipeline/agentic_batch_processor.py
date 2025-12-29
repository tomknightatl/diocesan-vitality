#!/usr/bin/env python3
"""
Agentic Batch Processor for Schedule Extraction

This module provides batch processing capabilities for the agentic workflow,
allowing integration with the existing pipeline infrastructure.
"""

import logging
from typing import Optional
from core.db import get_supabase_client
from core.intelligent_parish_prioritizer import IntelligentParishPrioritizer
from pipeline.agentic_schedule_extractor import scrape_parish_data_agentic

logger = logging.getLogger(__name__)


def extract_schedule_agentic_main(
    num_parishes: int = 100,
    parish_id: Optional[int] = None,
    max_pages_per_parish: int = 10,
    monitoring_client=None,
    max_iterations: int = 15,
):
    """
    Main function for agentic schedule extraction (replaces extract_schedule_main)

    Args:
        num_parishes: Number of parishes to process
        parish_id: Specific parish ID (optional)
        max_pages_per_parish: Maximum pages to check per parish
        monitoring_client: Monitoring client for logging
        max_iterations: Maximum workflow iterations per parish
    """
    supabase = get_supabase_client()

    # Use intelligent prioritization to select parishes
    prioritizer = IntelligentParishPrioritizer()
    if parish_id:
        parish_tuples = prioritizer.get_prioritized_parishes(
            num_parishes=num_parishes, parish_id=parish_id
        )
    else:
        parish_tuples = prioritizer.get_prioritized_parishes(num_parishes=num_parishes)

    # Convert to list of dicts for consistency
    parishes = [{"parish_id": pid, "parish_website": url} for url, pid in parish_tuples]

    logger.info(f"🤖 Starting agentic schedule extraction for {len(parishes)} parishes")

    for i, parish in enumerate(parishes, 1):
        try:
            logger.info(
                f"🤖 [{i}/{len(parishes)}] Processing parish {parish['parish_id']}: {parish['parish_website']}"
            )

            # Call agentic extraction
            result = scrape_parish_data_agentic(
                url=parish["parish_website"],
                parish_id=parish["parish_id"],
                supabase=supabase,
                max_iterations=max_iterations,
            )

            logger.info(
                f"🤖 [{i}/{len(parishes)}] Completed parish {parish['parish_id']}: {result['reconciliation_info']}"
            )

            # Log to monitoring if available
            if monitoring_client:
                monitoring_client.send_log(
                    f"Agentic extraction for parish {parish['parish_id']}: {result['reconciliation_info']}",
                    "INFO",
                    worker_type="schedule",
                )

        except Exception as e:
            logger.error(
                f"🤖 [{i}/{len(parishes)}] Failed parish {parish['parish_id']}: {e}"
            )
            if monitoring_client:
                monitoring_client.report_error(
                    error_type="AgenticExtractionError",
                    message=f"Agentic extraction failed for parish {parish['parish_id']}: {str(e)}",
                )

    logger.info(
        f"✅ Completed agentic schedule extraction for {len(parishes)} parishes"
    )
