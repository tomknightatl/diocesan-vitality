#!/usr/bin/env python3
"""
Simplified Parish Prioritization System for Schedule Extraction.

This module implements straightforward parish selection for Step 4 (Schedule Extraction)
based on simple, clear prioritization rules:

1. First Priority: Never-tested parishes (respectful_automation_used = false/null)
   - Newer parishes (higher id) visited first
2. Second Priority: Previously tested parishes
   - Most recently tested parishes visited last (older extracted_at first)
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from supabase import Client

from core.logger import get_logger
from core.db import get_supabase_client

logger = get_logger(__name__)


class IntelligentParishPrioritizer:
    """
    Simplified parish prioritization system for schedule extraction.
    """

    def __init__(self, supabase: Client = None):
        """Initialize the parish prioritizer."""
        self.supabase = supabase or get_supabase_client()
        self.logger = logger
        logger.info("🎯 Intelligent Parish Prioritizer initialized")

    def get_prioritized_parishes(self, num_parishes: int, parish_id: int = None) -> List[Tuple[str, int]]:
        """
        Get prioritized parishes for schedule extraction using simplified logic.

        Args:
            num_parishes: Number of parishes to return
            parish_id: Specific parish ID to process (overrides prioritization)

        Returns:
            List of (parish_url, parish_id) tuples in priority order
        """
        logger.info(f"🎯 Starting simplified parish prioritization for {num_parishes} parishes")

        # Handle specific parish request
        if parish_id:
            return self._get_specific_parish(parish_id)

        # Get prioritized parishes using simplified logic
        prioritized_parishes = self._get_simple_prioritized_parishes(num_parishes)

        logger.info(f"🎯 Selected {len(prioritized_parishes)} parishes with simplified prioritization")
        self._log_prioritization_summary(prioritized_parishes)

        return [(p['Web'], p['id']) for p in prioritized_parishes]

    def _get_specific_parish(self, parish_id: int) -> List[Tuple[str, int]]:
        """Handle specific parish ID request."""
        try:
            response = self.supabase.table('Parishes').select('id, Web').eq('id', parish_id).execute()
            if response.data and response.data[0].get('Web'):
                parish = response.data[0]
                logger.info(f"🎯 Specific parish requested: {parish_id}")
                return [(parish['Web'], parish['id'])]
            return []
        except Exception as e:
            logger.error(f"🎯 Error fetching specific parish {parish_id}: {e}")
            return []

    def _get_simple_prioritized_parishes(self, num_parishes: int) -> List[Dict]:
        """
        Get prioritized parishes using simplified logic:
        1. Never-tested parishes first (newer parishes first by ID)
        2. Previously tested parishes second (older tests first by extracted_at)
        """
        try:
            # Get all parishes with websites
            parishes_response = self.supabase.table('Parishes').select(
                'id, Name, Web, respectful_automation_used, extracted_at'
            ).not_.is_('Web', 'null').execute()

            if not parishes_response.data:
                logger.warning("🎯 No parishes with websites found")
                return []

            parishes = parishes_response.data

            # Split into never-tested and previously-tested
            never_tested = []
            previously_tested = []

            for parish in parishes:
                if not parish.get('Web'):  # Skip parishes without websites
                    continue

                # Check if parish has been tested for blocking
                is_tested = parish.get('respectful_automation_used') is True

                if is_tested:
                    previously_tested.append(parish)
                else:
                    never_tested.append(parish)

            # Sort never-tested parishes: Newer parishes first (higher ID = more recently created)
            never_tested.sort(key=lambda p: p['id'], reverse=True)

            # Sort previously-tested parishes: Older tests first (earlier extracted_at = test longer ago)
            previously_tested.sort(key=lambda p: p.get('extracted_at') or '1900-01-01T00:00:00', reverse=False)

            # Combine: never-tested first, then previously-tested
            all_prioritized = never_tested + previously_tested

            logger.info(f"🎯 Found {len(never_tested)} never-tested parishes, {len(previously_tested)} previously-tested parishes")
            logger.info(f"🎯 Total candidate pool: {len(all_prioritized)} parishes")

            # Return requested number
            selected = all_prioritized[:num_parishes]

            logger.info(f"🎯 Prioritization complete - returning {len(selected)} parishes")
            return selected

        except Exception as e:
            logger.error(f"🎯 Error in simplified prioritization: {e}")
            return []

    def _log_prioritization_summary(self, selected_parishes: List[Dict]):
        """Log summary of prioritization results."""
        if not selected_parishes:
            logger.warning("🎯 No parishes selected")
            return

        # Count never-tested vs previously-tested
        never_tested_count = sum(1 for p in selected_parishes if not p.get('respectful_automation_used'))
        previously_tested_count = len(selected_parishes) - never_tested_count

        logger.info("🎯 Prioritization Summary:")
        logger.info(f"    📊 Total selected: {len(selected_parishes)}")
        logger.info(f"    🆕 Never-tested: {never_tested_count}")
        logger.info(f"    🔄 Previously-tested: {previously_tested_count}")

        # Log top parish details
        if selected_parishes:
            top_parish = selected_parishes[0]
            is_tested = "Previously-tested" if top_parish.get('respectful_automation_used') else "Never-tested"
            logger.info(f"    🥇 Top parish: {top_parish.get('Name', 'Unknown')} (ID: {top_parish['id']}) - {is_tested}")

        # Log first few parishes for debugging
        for i, parish in enumerate(selected_parishes[:3], 1):
            status = "Previously-tested" if parish.get('respectful_automation_used') else "Never-tested"
            extracted_at = parish.get('extracted_at', 'Never')
            logger.info(f"    {i}. {parish.get('Name', 'Unknown')} | ID: {parish['id']} | "
                       f"Status: {status} | Last Test: {extracted_at}")

    def update_extraction_result(self, parish_id: int, success: bool):
        """Update tracking for a completed extraction."""
        try:
            logger.debug(f"🎯 Extraction result for parish {parish_id}: {'success' if success else 'failure'}")
        except Exception as e:
            logger.warning(f"🎯 Error updating extraction result for parish {parish_id}: {e}")


def get_intelligent_parish_prioritizer(supabase: Client = None) -> IntelligentParishPrioritizer:
    """Factory function to create intelligent parish prioritizer."""
    return IntelligentParishPrioritizer(supabase)