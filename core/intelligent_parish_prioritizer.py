#!/usr/bin/env python3
"""
Intelligent Parish Prioritization System for Schedule Extraction.

This module implements advanced parish selection strategies for Step 4 (Schedule Extraction)
to maximize success rates and optimize extraction efficiency through:

1. Priority by Schedule Likelihood - Website pattern analysis
2. Freshness-based Selection - Recency-based prioritization
3. Diocese Clustering - Batch similar extraction patterns
4. Success Rate Learning - Track and leverage historical performance
"""

import re
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urlparse
from dataclasses import dataclass, field
from collections import defaultdict

from supabase import Client

from core.logger import get_logger
from core.db import get_supabase_client

logger = get_logger(__name__)

# Known problematic domains that should be skipped
PROBLEMATIC_DOMAINS = {
    'stmarkrcc.org',  # DNS resolution fails
    'sthelenacc-clayton.org',  # Connection issues
    'stpaulcleveland.com',  # Timeout issues
    'qofathomson.org',  # Connection problems
    'stmarystoccoa.org'  # DNS/connectivity issues
}


@dataclass
class ParishPriorityScore:
    """Comprehensive priority scoring for parish selection."""
    parish_id: int
    parish_name: str
    parish_url: str
    diocese_id: int
    diocese_name: str

    # Scoring components
    schedule_likelihood_score: float = 0.0
    freshness_score: float = 0.0
    diocese_success_score: float = 0.0
    website_quality_score: float = 0.0

    # Metadata
    last_extraction_attempt: Optional[str] = None
    successful_extractions: int = 0
    total_extractions: int = 0

    @property
    def total_score(self) -> float:
        """Calculate weighted total priority score - PRIORITIZING COMPREHENSIVE COVERAGE."""
        return (
            self.freshness_score * 0.6 +           # 60% weight - UNVISITED PARISHES FIRST
            self.schedule_likelihood_score * 0.2 + # 20% weight - reduced importance
            self.diocese_success_score * 0.1 +     # 10% weight - reduced importance
            self.website_quality_score * 0.1       # 10% weight - reduced importance
        )

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this parish."""
        if self.total_extractions == 0:
            return 0.5  # Neutral score for untried parishes
        return self.successful_extractions / self.total_extractions


class IntelligentParishPrioritizer:
    """
    Advanced parish prioritization system for optimized schedule extraction.
    """

    def __init__(self, supabase: Client = None):
        """Initialize the parish prioritizer."""
        self.supabase = supabase or get_supabase_client()
        self.logger = logger

        # Caches for performance
        self._parish_cache: Dict[int, ParishPriorityScore] = {}
        self._diocese_stats_cache: Dict[int, Dict] = {}
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes

        logger.info("🎯 Intelligent Parish Prioritizer initialized")

    def get_prioritized_parishes(self, num_parishes: int, parish_id: int = None) -> List[Tuple[str, int]]:
        """
        Get intelligently prioritized parishes for schedule extraction.

        Args:
            num_parishes: Number of parishes to return
            parish_id: Specific parish ID to process (overrides prioritization)

        Returns:
            List of (parish_url, parish_id) tuples in priority order
        """
        logger.info(f"🎯 Starting intelligent parish prioritization for {num_parishes} parishes")

        # Handle specific parish request
        if parish_id:
            return self._get_specific_parish(parish_id)

        # Get all candidate parishes
        candidates = self._get_candidate_parishes()
        if not candidates:
            logger.warning("🎯 No candidate parishes found")
            return []

        # Score and prioritize all candidates
        prioritized_parishes = self._prioritize_parishes(candidates)

        # Apply clustering and final selection
        selected_parishes = self._apply_diocese_clustering(prioritized_parishes, num_parishes)

        logger.info(f"🎯 Selected {len(selected_parishes)} parishes with intelligent prioritization")
        self._log_prioritization_summary(selected_parishes)

        return [(p.parish_url, p.parish_id) for p in selected_parishes]

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

    def _get_candidate_parishes(self) -> List[Dict]:
        """Fetch candidate parishes with preference for unvisited ones."""
        try:
            # Get parishes that haven't been processed yet (no ParishData records)
            processed_parishes_response = self.supabase.table('ParishData').select('parish_id').execute()
            processed_parish_ids = {p['parish_id'] for p in processed_parishes_response.data}

            # Get all parishes with web URLs
            parishes_response = self.supabase.table('Parishes').select(
                'id, Name, Web, diocese_id'
            ).not_.is_('Web', 'null').execute()

            # Get dioceses mapping
            dioceses_response = self.supabase.table('Dioceses').select(
                'id, Name'
            ).execute()

            dioceses_map = {d['id']: d['Name'] for d in dioceses_response.data}

            # Split parishes into unvisited and visited
            unvisited_candidates = []
            visited_candidates = []

            for parish in parishes_response.data:
                if parish.get('Web') and parish.get('diocese_id'):
                    # Clean and validate the URL
                    parish_url = parish['Web'].strip()
                    if parish_url and (parish_url.startswith('http://') or parish_url.startswith('https://')):
                        diocese_name = dioceses_map.get(parish['diocese_id'], 'Unknown Diocese')
                        candidate = {
                            'parish_id': parish['id'],
                            'parish_name': parish.get('Name', 'Unknown'),
                            'parish_url': parish_url,
                            'diocese_id': parish['diocese_id'],
                            'diocese_name': diocese_name
                        }

                        # Prioritize unvisited parishes
                        if parish['id'] not in processed_parish_ids:
                            unvisited_candidates.append(candidate)
                        else:
                            visited_candidates.append(candidate)

            # Return unvisited first, then visited as fallback
            all_candidates = unvisited_candidates + visited_candidates

            logger.info(f"🎯 Found {len(unvisited_candidates)} unvisited parishes, {len(visited_candidates)} visited parishes")
            logger.info(f"🎯 Total candidate pool: {len(all_candidates)} parishes")

            return all_candidates

        except Exception as e:
            logger.error(f"🎯 Error fetching candidate parishes: {e}")
            return []

    def _prioritize_parishes(self, candidates: List[Dict]) -> List[ParishPriorityScore]:
        """Simple prioritization favoring unvisited parishes."""
        logger.info(f"🎯 Simplified prioritization for {len(candidates)} parishes (unvisited first)")

        prioritized = []

        for i, candidate in enumerate(candidates):
            try:
                # Simple scoring: unvisited parishes get higher score
                base_score = 1.0 if i < len(candidates) // 2 else 0.5  # Assumes unvisited are first half

                score = ParishPriorityScore(
                    parish_id=candidate['parish_id'],
                    parish_name=candidate['parish_name'],
                    parish_url=candidate['parish_url'],
                    diocese_id=candidate['diocese_id'],
                    diocese_name=candidate['diocese_name']
                )

                # Simplified scoring - just set base scores
                score.schedule_likelihood_score = base_score
                score.freshness_score = base_score
                score.diocese_success_score = base_score
                score.website_quality_score = base_score

                # No historical data needed for simplified version
                score.last_extraction_attempt = None
                score.successful_extractions = 0
                score.total_extractions = 0

                prioritized.append(score)

            except Exception as e:
                logger.warning(f"🎯 Error scoring parish {candidate['parish_id']}: {e}")
                continue

        # Sort by total score (highest first)
        prioritized.sort(key=lambda p: p.total_score, reverse=True)

        logger.info(f"🎯 Prioritization complete - Top score: {prioritized[0].total_score:.2f}")
        return prioritized

    def _calculate_schedule_likelihood(self, candidate: Dict) -> float:
        """
        Calculate likelihood that a parish website contains schedule information.
        Based on URL patterns, domain characteristics, and website structure indicators.
        """
        url = candidate['parish_url'].lower()
        domain = urlparse(url).netloc.lower()

        score = 0.5  # Base score

        # Domain pattern analysis
        if 'parish' in domain:
            score += 0.2
        if 'church' in domain or 'catholic' in domain:
            score += 0.15
        if 'saint' in domain or 'st' in domain:
            score += 0.1

        # URL structure analysis
        if len(domain.split('.')) <= 3:  # Simple domain structure
            score += 0.1
        if not any(pattern in domain for pattern in ['blogspot', 'wordpress.com', 'wix', 'squarespace']):
            score += 0.1  # Custom domains often have better structure

        # Diocese-based patterns (some dioceses have better website standardization)
        diocese_name = candidate.get('diocese_name', '').lower()
        if 'archdiocese' in diocese_name:
            score += 0.05  # Archdioceses often have better resources

        return min(score, 1.0)

    def _calculate_freshness_score(self, candidate: Dict, extraction_history: Dict) -> float:
        """
        Calculate freshness score based on how recently the parish was last attempted.
        Higher scores for parishes not recently attempted.
        """
        parish_id = candidate['parish_id']
        history = extraction_history.get(parish_id, {})

        if not history.get('last_attempt'):
            return 1.0  # Maximum score for never-attempted parishes

        try:
            last_attempt = datetime.fromisoformat(history['last_attempt'].replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            days_since = (now - last_attempt).days

            # Fresher score for longer time since last attempt
            if days_since >= 30:
                return 1.0
            elif days_since >= 14:
                return 0.8
            elif days_since >= 7:
                return 0.6
            elif days_since >= 3:
                return 0.4
            elif days_since >= 1:
                return 0.2
            else:
                return 0.0  # Recently attempted

        except Exception as e:
            logger.debug(f"🎯 Error parsing last attempt date for parish {parish_id}: {e}")
            return 0.5

    def _calculate_diocese_success_rates(self, extraction_history: Dict) -> Dict[int, float]:
        """Calculate success rates by diocese for scoring."""
        diocese_stats = defaultdict(lambda: {'successful': 0, 'total': 0})

        # Get parish-diocese mapping
        try:
            response = self.supabase.table('Parishes').select('id, diocese_id').execute()
            parish_diocese_map = {p['id']: p['diocese_id'] for p in response.data}
        except Exception as e:
            logger.warning(f"🎯 Error fetching parish-diocese mapping: {e}")
            return {}

        # Aggregate stats by diocese
        for parish_id, history in extraction_history.items():
            diocese_id = parish_diocese_map.get(parish_id)
            if diocese_id:
                stats = diocese_stats[diocese_id]
                stats['successful'] += history.get('successful', 0)
                stats['total'] += history.get('total', 0)

        # Calculate success rates
        success_rates = {}
        for diocese_id, stats in diocese_stats.items():
            if stats['total'] > 0:
                success_rates[diocese_id] = stats['successful'] / stats['total']
            else:
                success_rates[diocese_id] = 0.5  # Neutral score for no data

        logger.info(f"🎯 Calculated success rates for {len(success_rates)} dioceses")
        return success_rates

    def _calculate_website_quality(self, url: str) -> float:
        """
        Estimate website quality based on URL characteristics.
        Better websites are more likely to have organized schedule information.
        """
        domain = urlparse(url).netloc.lower()
        score = 0.5  # Base score

        # HTTPS bonus
        if url.startswith('https://'):
            score += 0.1

        # Custom domain bonus
        if not any(platform in domain for platform in [
            'blogspot', 'wordpress.com', 'wix', 'squarespace', 'weebly'
        ]):
            score += 0.15

        # Professional domain patterns
        if any(pattern in domain for pattern in ['parish', 'church', 'catholic']):
            score += 0.1

        # Avoid problematic patterns
        if any(pattern in domain for pattern in ['geocities', 'angelfire', '~']):
            score -= 0.2

        # Simple, clean domain structure
        if len(domain.split('.')) == 2:  # e.g., stmarys.org
            score += 0.1

        return max(0.0, min(score, 1.0))

    def _get_extraction_history(self) -> Dict[int, Dict]:
        """Get historical extraction data for parishes."""
        try:
            # Get ParishData extraction history
            response = self.supabase.table('ParishData').select(
                'parish_id, fact_type, created_at'
            ).execute()

            history = defaultdict(lambda: {'successful': 0, 'total': 0, 'last_attempt': None})

            for record in response.data:
                parish_id = record['parish_id']
                created_at = record['created_at']

                history[parish_id]['total'] += 1
                if record['fact_type'] in ['ReconciliationSchedule', 'AdorationSchedule']:
                    history[parish_id]['successful'] += 1

                # Track most recent attempt
                if (not history[parish_id]['last_attempt'] or
                    created_at > history[parish_id]['last_attempt']):
                    history[parish_id]['last_attempt'] = created_at

            logger.info(f"🎯 Loaded extraction history for {len(history)} parishes")
            return dict(history)

        except Exception as e:
            logger.warning(f"🎯 Error loading extraction history: {e}")
            return {}

    def _apply_diocese_clustering(self, prioritized_parishes: List[ParishPriorityScore],
                                num_parishes: int) -> List[ParishPriorityScore]:
        """
        Apply COMPREHENSIVE COVERAGE diocese distribution - prioritize unvisited parishes across ALL dioceses.
        """
        if not prioritized_parishes:
            return []

        # Group by diocese and sort each group by score
        diocese_groups = defaultdict(list)
        for parish in prioritized_parishes:
            diocese_groups[parish.diocese_id].append(parish)

        # Sort each diocese group by score (unvisited parishes will score highest)
        for diocese_id in diocese_groups:
            diocese_groups[diocese_id].sort(key=lambda p: p.total_score, reverse=True)

        selected = []
        remaining_slots = num_parishes

        # Strategy: Round-robin across ALL dioceses to ensure comprehensive coverage
        max_parishes_per_diocese = max(1, num_parishes // len(diocese_groups)) + 1

        # Round-robin selection to maximize diocese diversity
        round_num = 0
        max_rounds = max_parishes_per_diocese

        while remaining_slots > 0 and round_num < max_rounds:
            parishes_added_this_round = 0

            for diocese_id, diocese_parishes in diocese_groups.items():
                if remaining_slots <= 0:
                    break

                # Take the next best parish from this diocese (if available)
                if round_num < len(diocese_parishes):
                    parish = diocese_parishes[round_num]
                    if parish not in selected:  # Avoid duplicates
                        selected.append(parish)
                        remaining_slots -= 1
                        parishes_added_this_round += 1

            if parishes_added_this_round == 0:  # No more parishes available
                break

            round_num += 1

        # Final sort by total score (unvisited parishes first due to high freshness score)
        selected.sort(key=lambda p: p.total_score, reverse=True)

        diocese_distribution = defaultdict(int)
        for parish in selected:
            diocese_distribution[parish.diocese_name] += 1

        logger.info(f"🎯 Comprehensive coverage applied - {len(diocese_distribution)} dioceses")
        logger.info(f"🎯 Diocese distribution: {dict(list(diocese_distribution.items())[:10])}{'...' if len(diocese_distribution) > 10 else ''}")
        return selected[:num_parishes]

    def _log_prioritization_summary(self, selected_parishes: List[ParishPriorityScore]):
        """Log summary of prioritization results."""
        if not selected_parishes:
            return

        top_parish = selected_parishes[0]
        avg_score = sum(p.total_score for p in selected_parishes) / len(selected_parishes)

        fresh_parishes = sum(1 for p in selected_parishes if not p.last_extraction_attempt)
        high_likelihood = sum(1 for p in selected_parishes if p.schedule_likelihood_score > 0.7)

        logger.info(f"🎯 Prioritization Summary:")
        logger.info(f"    🥇 Top parish: {top_parish.parish_name} (score: {top_parish.total_score:.2f})")
        logger.info(f"    📊 Average score: {avg_score:.2f}")
        logger.info(f"    🆕 Fresh parishes: {fresh_parishes}/{len(selected_parishes)}")
        logger.info(f"    🎯 High likelihood: {high_likelihood}/{len(selected_parishes)}")

        # Log top 3 parishes for debugging
        for i, parish in enumerate(selected_parishes[:3], 1):
            logger.info(f"    {i}. {parish.parish_name} | Score: {parish.total_score:.2f} | "
                       f"Likelihood: {parish.schedule_likelihood_score:.2f} | "
                       f"Fresh: {parish.freshness_score:.2f} | "
                       f"Diocese: {parish.diocese_name}")

    def update_extraction_result(self, parish_id: int, success: bool):
        """Update tracking for a completed extraction."""
        try:
            # This would be called after extraction completion
            # For now, we rely on the ParishData table to track success
            logger.debug(f"🎯 Extraction result for parish {parish_id}: {'success' if success else 'failure'}")

            # Clear cache to refresh data
            self._parish_cache.clear()
            self._diocese_stats_cache.clear()

        except Exception as e:
            logger.warning(f"🎯 Error updating extraction result for parish {parish_id}: {e}")


def get_intelligent_parish_prioritizer(supabase: Client = None) -> IntelligentParishPrioritizer:
    """Factory function to create intelligent parish prioritizer."""
    return IntelligentParishPrioritizer(supabase)