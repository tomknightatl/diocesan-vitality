#!/usr/bin/env python3
"""
Enhanced URL Management System for Schedule Extraction Optimization.

This module implements advanced URL discovery, prioritization, and memory systems
to dramatically improve extraction success rates by:

1. Success-Based URL Memory - Prioritizing previously successful URLs
2. Smart Protocol Detection - Handling HTTP/HTTPS and DNS issues
3. Enhanced URL Re-discovery - Leveraging known successful patterns
4. Dynamic Page Limits - Adaptive scanning based on success probability
5. Improved Timeout Strategy - Context-aware timeout management
"""

import re
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urlparse, urljoin, urlunparse
from dataclasses import dataclass, field
from collections import defaultdict

from supabase import Client

from core.logger import get_logger
from core.db import get_supabase_client
from core.ml_url_predictor import get_ml_url_predictor
from core.adaptive_timeout_manager import get_adaptive_timeout_manager
from core.intelligent_cache_manager import get_cache_manager, ContentType
from core.robust_error_handler import get_error_handler, ErrorContext

logger = get_logger(__name__)


@dataclass
class URLCandidate:
    """Enhanced URL candidate with success tracking and optimization metadata."""
    url: str
    parish_id: int
    priority_score: float = 0.0
    success_history: int = 0  # Number of successful extractions
    last_success: Optional[str] = None
    protocol_verified: bool = False
    dns_resolvable: bool = False
    content_type: str = 'unknown'
    estimated_timeout: float = 30.0


@dataclass
class ExtractionContext:
    """Context for dynamic extraction optimization."""
    parish_id: int
    parish_url: str
    previous_successes: List[str] = field(default_factory=list)
    page_scan_limit: int = 200
    timeout_strategy: str = 'adaptive'
    priority_urls: List[str] = field(default_factory=list)


class EnhancedURLManager:
    """
    Advanced URL management system with success-based learning and optimization.
    """

    def __init__(self, supabase: Client = None):
        """Initialize the enhanced URL manager with integrated optimization systems."""
        self.supabase = supabase or get_supabase_client()
        self.logger = logger

        # Integration with optimization systems
        self.ml_predictor = get_ml_url_predictor(self.supabase)
        self.timeout_manager = get_adaptive_timeout_manager()
        self.cache_manager = get_cache_manager()
        self.error_handler = get_error_handler()

        # Caches for performance (now enhanced with intelligent caching)
        self._success_cache: Dict[int, List[str]] = {}
        self._protocol_cache: Dict[str, str] = {}
        self._dns_cache: Dict[str, bool] = {}
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes

        logger.info("🔗 Enhanced URL Manager initialized with ML prediction, adaptive timeouts, intelligent caching, and error handling")

    def get_extraction_context(self, parish_id: int, base_url: str) -> ExtractionContext:
        """
        Create optimized extraction context for a parish based on historical data.

        Args:
            parish_id: Parish ID to extract for
            base_url: Base parish URL

        Returns:
            ExtractionContext with optimization parameters
        """
        logger.info(f"🔗 Creating extraction context for parish {parish_id}")

        # Get previous successful URLs
        previous_successes = self._get_successful_urls(parish_id)

        # Determine dynamic page scan limit based on success history
        page_scan_limit = self._calculate_dynamic_page_limit(parish_id, previous_successes)

        # Get priority URLs from successful extractions and smart discovery
        priority_urls = self._get_priority_urls(parish_id, base_url, previous_successes)

        # Determine timeout strategy
        timeout_strategy = self._determine_timeout_strategy(base_url, previous_successes)

        context = ExtractionContext(
            parish_id=parish_id,
            parish_url=base_url,
            previous_successes=previous_successes,
            page_scan_limit=page_scan_limit,
            timeout_strategy=timeout_strategy,
            priority_urls=priority_urls
        )

        logger.info(f"🔗 Context created: {len(priority_urls)} priority URLs, "
                   f"scan limit: {page_scan_limit}, timeout: {timeout_strategy}")

        return context

    def get_optimized_url_candidates(self, context: ExtractionContext,
                                   discovered_urls: List[str]) -> List[URLCandidate]:
        """
        Get prioritized and optimized URL candidates for extraction using ML prediction.

        Args:
            context: Extraction context with optimization parameters
            discovered_urls: URLs discovered through normal crawling

        Returns:
            List of optimized URLCandidate objects in priority order
        """
        error_context = ErrorContext(
            operation="url_prediction",
            url=context.parish_url,
            parish_id=context.parish_id
        )

        return self.error_handler.handle_with_fallback(
            "url_prediction",
            self._get_optimized_candidates_with_ml,
            error_context,
            extraction_context=context,
            discovered_urls=discovered_urls
        )

    def _get_optimized_candidates_with_ml(self, error_context: ErrorContext,
                                        extraction_context: ExtractionContext,
                                        discovered_urls: List[str]) -> List[URLCandidate]:
        """Internal method with ML-based URL optimization."""
        logger.info(f"🔗 Optimizing {len(discovered_urls)} discovered URLs with ML prediction")

        candidates = []
        processed_urls = set()

        # Get ML predictions for this domain
        domain = urlparse(extraction_context.parish_url).netloc
        try:
            ml_predictions = self.ml_predictor.predict_successful_urls(
                domain,
                base_patterns=extraction_context.priority_urls[:10]  # Use top priority URLs as patterns
            )
            logger.info(f"🧠 ML predictor generated {len(ml_predictions)} URL predictions")
        except Exception as e:
            logger.warning(f"🧠 ML prediction failed: {e}, falling back to pattern-based")
            ml_predictions = []

        # Priority 0: ML Predictions (highest priority)
        for url, confidence in ml_predictions[:20]:  # Top 20 ML predictions
            if url not in processed_urls:
                candidate = self._create_url_candidate(url, extraction_context.parish_id,
                                                     priority_boost=20.0 * confidence, is_ml_predicted=True)
                if candidate:
                    candidates.append(candidate)
                    processed_urls.add(url)

        # Priority 1: Previously successful URLs (golden URLs)
        for url in extraction_context.previous_successes:
            if url not in processed_urls:
                candidate = self._create_url_candidate(url, extraction_context.parish_id,
                                                     priority_boost=15.0, is_golden=True)
                if candidate:
                    candidates.append(candidate)
                    processed_urls.add(url)

        # Priority 2: Context priority URLs (smart discovery)
        for url in extraction_context.priority_urls:
            if url not in processed_urls:
                candidate = self._create_url_candidate(url, extraction_context.parish_id,
                                                     priority_boost=5.0)
                if candidate:
                    candidates.append(candidate)
                    processed_urls.add(url)

        # Priority 3: Standard discovered URLs with enhanced scoring
        for url in discovered_urls:
            if url not in processed_urls:
                candidate = self._create_url_candidate(url, extraction_context.parish_id)
                if candidate and candidate.priority_score > 0:
                    candidates.append(candidate)
                    processed_urls.add(url)

        # Sort by priority score (highest first)
        candidates.sort(key=lambda c: c.priority_score, reverse=True)

        # Apply protocol verification and DNS resolution
        verified_candidates = self._verify_url_candidates(candidates)

        logger.info(f"🔗 Created {len(verified_candidates)} verified URL candidates")
        return verified_candidates

    def _get_successful_urls(self, parish_id: int) -> List[str]:
        """Get URLs that previously yielded successful extractions."""
        try:
            if parish_id in self._success_cache:
                return self._success_cache[parish_id]

            # Query ParishData for successful extractions
            response = self.supabase.table('ParishData').select(
                'fact_source_url'
            ).eq('parish_id', parish_id).in_(
                'fact_type', ['ReconciliationSchedule', 'AdorationSchedule']
            ).execute()

            successful_urls = []
            for record in response.data:
                url = record.get('fact_source_url')
                if url and url not in successful_urls:
                    successful_urls.append(url)

            # Cache results
            self._success_cache[parish_id] = successful_urls

            logger.info(f"🔗 Found {len(successful_urls)} previously successful URLs for parish {parish_id}")
            return successful_urls

        except Exception as e:
            logger.error(f"🔗 Error fetching successful URLs for parish {parish_id}: {e}")
            return []

    def _calculate_dynamic_page_limit(self, parish_id: int,
                                    previous_successes: List[str]) -> int:
        """Calculate dynamic page scan limit based on success history."""
        base_limit = 50

        # If we have successful URLs, we can be more conservative
        if previous_successes:
            return min(base_limit, 30)  # Lower limit since we have golden URLs

        # For new parishes, check complexity indicators
        try:
            discovered_count = self.supabase.table('DiscoveredUrls').select(
                'url', count='exact'
            ).eq('parish_id', parish_id).execute()

            if discovered_count.count and discovered_count.count > 100:
                return min(base_limit * 2, 150)  # Complex site, higher limit

        except Exception as e:
            logger.debug(f"🔗 Could not determine site complexity: {e}")

        return base_limit

    def _get_priority_urls(self, parish_id: int, base_url: str,
                          previous_successes: List[str]) -> List[str]:
        """Generate priority URLs using smart discovery patterns."""
        priority_urls = []

        # Start with previously successful URLs
        priority_urls.extend(previous_successes)

        # Generate smart discovery URLs based on common patterns
        domain = urlparse(base_url).netloc
        base_scheme = urlparse(base_url).scheme

        # Common schedule page patterns
        patterns = [
            '/reconciliation', '/confession', '/confessions', '/penance',
            '/adoration', '/eucharistic-adoration', '/blessed-sacrament',
            '/mass-times', '/mass-schedule', '/liturgy', '/worship',
            '/schedule', '/schedules', '/hours', '/times',
            '/sacraments', '/services', '/parish-life', '/ministries'
        ]

        for pattern in patterns:
            # Generate both HTTP and HTTPS variants
            for scheme in ['https', 'http']:
                candidate_url = f"{scheme}://{domain}{pattern}"
                if candidate_url not in priority_urls:
                    priority_urls.append(candidate_url)

        # Also check previously discovered URLs for this parish
        try:
            discovered = self.supabase.table('DiscoveredUrls').select(
                'url'
            ).eq('parish_id', parish_id).execute()

            for record in discovered.data:
                url = record['url']
                if self._is_schedule_relevant_url(url) and url not in priority_urls:
                    priority_urls.append(url)

        except Exception as e:
            logger.debug(f"🔗 Could not load discovered URLs: {e}")

        return priority_urls

    def _determine_timeout_strategy(self, base_url: str,
                                  previous_successes: List[str]) -> str:
        """Determine optimal timeout strategy based on URL patterns."""
        domain = urlparse(base_url).netloc.lower()

        # Fast domains (typically load quickly)
        fast_patterns = ['archatl.com', 'wordpress.com', 'squarespace.com']
        if any(pattern in domain for pattern in fast_patterns):
            return 'fast'

        # Complex sites (may need more time)
        complex_patterns = ['wix.com', 'weebly.com', 'shopify.com']
        if any(pattern in domain for pattern in complex_patterns):
            return 'extended'

        # Sites with previous successes can use moderate timeouts
        if previous_successes:
            return 'moderate'

        return 'adaptive'

    def _create_url_candidate(self, url: str, parish_id: int,
                            priority_boost: float = 0.0,
                            is_golden: bool = False,
                            is_ml_predicted: bool = False) -> Optional[URLCandidate]:
        """Create a URL candidate with enhanced scoring."""
        try:
            # Basic URL validation
            parsed = urlparse(url)
            if not parsed.netloc or not parsed.scheme:
                return None

            # Calculate base priority score
            base_score = self._calculate_url_priority_score(url)

            # Apply boosts
            total_score = base_score + priority_boost

            # Golden URL boost
            if is_golden:
                total_score += 15.0  # Significant boost for proven URLs

            # ML prediction boost
            if is_ml_predicted:
                total_score += 10.0  # Boost for ML predicted URLs

            # Get success history
            success_count = self._get_url_success_count(url, parish_id)

            # Get estimated timeout using adaptive timeout manager
            estimated_timeout = self.timeout_manager.get_optimal_timeout(
                url,
                operation_type='page_load',
                context={'parish_id': parish_id, 'is_golden': is_golden}
            )

            candidate = URLCandidate(
                url=url,
                parish_id=parish_id,
                priority_score=total_score,
                success_history=success_count,
                estimated_timeout=estimated_timeout
            )

            return candidate

        except Exception as e:
            logger.debug(f"🔗 Error creating URL candidate for {url}: {e}")
            return None

    def _calculate_url_priority_score(self, url: str) -> float:
        """Calculate priority score based on URL patterns and keywords."""
        url_lower = url.lower()
        score = 0.0

        # High-value schedule indicators
        high_value_terms = ['reconciliation', 'confession', 'adoration', 'eucharistic']
        for term in high_value_terms:
            if term in url_lower:
                score += 5.0

        # Medium-value schedule indicators
        medium_value_terms = ['mass', 'times', 'schedule', 'hours', 'worship', 'liturgy']
        for term in medium_value_terms:
            if term in url_lower:
                score += 3.0

        # General religious indicators
        general_terms = ['parish', 'church', 'catholic', 'sacrament', 'ministry']
        for term in general_terms:
            if term in url_lower:
                score += 1.0

        # Penalize low-value pages
        low_value_terms = ['contact', 'about', 'history', 'staff', 'donate', 'news']
        for term in low_value_terms:
            if term in url_lower:
                score -= 2.0

        return max(score, 0.0)

    def _get_url_success_count(self, url: str, parish_id: int) -> int:
        """Get number of successful extractions for this URL."""
        try:
            response = self.supabase.table('ParishData').select(
                'id', count='exact'
            ).eq('parish_id', parish_id).eq('fact_source_url', url).execute()

            return response.count or 0

        except Exception as e:
            logger.debug(f"🔗 Could not get success count for {url}: {e}")
            return 0

    def _verify_url_candidates(self, candidates: List[URLCandidate]) -> List[URLCandidate]:
        """Verify URL candidates with protocol detection and DNS resolution using intelligent caching."""
        verified = []

        for candidate in candidates:
            error_context = ErrorContext(
                operation="url_verification",
                url=candidate.url,
                parish_id=candidate.parish_id
            )

            try:
                verified_candidate = self.error_handler.handle_with_fallback(
                    "url_verification",
                    self._verify_single_candidate,
                    error_context,
                    candidate=candidate
                )

                if verified_candidate and verified_candidate.dns_resolvable:
                    verified.append(verified_candidate)

            except Exception as e:
                logger.debug(f"🔗 Error verifying candidate {candidate.url}: {e}")
                continue

        logger.info(f"🔗 Verified {len(verified)}/{len(candidates)} URL candidates")
        return verified

    def _verify_single_candidate(self, error_context: ErrorContext, candidate: URLCandidate) -> URLCandidate:
        """Verify a single URL candidate with intelligent caching."""
        # Check DNS resolution using intelligent cache
        domain = urlparse(candidate.url).netloc

        # Use cache manager for DNS resolution
        cache_key = f"dns_resolution:{domain}"
        candidate.dns_resolvable = self.cache_manager.get(
            cache_key,
            default=None
        )

        if candidate.dns_resolvable is None:
            # Perform DNS resolution check
            candidate.dns_resolvable = self._check_dns_resolution(domain)
            # Cache result with 1 hour TTL
            self.cache_manager.set(
                cache_key,
                candidate.dns_resolvable,
                ttl=3600.0,
                content_type=ContentType.DNS_RESULT
            )

        # Protocol verification with intelligent caching
        if candidate.dns_resolvable:
            protocol_cache_key = f"protocol_verification:{candidate.url}"
            verified_url = self.cache_manager.get(
                protocol_cache_key,
                default=None
            )

            if verified_url is None:
                verified_url = self._verify_and_fix_protocol_with_timeout(candidate)
                # Cache result with 30 minute TTL
                self.cache_manager.set(
                    protocol_cache_key,
                    verified_url,
                    ttl=1800.0,
                    content_type=ContentType.URL_VERIFICATION
                )

            if verified_url != candidate.url:
                candidate.url = verified_url
                candidate.protocol_verified = True

        return candidate

    def _check_dns_resolution(self, domain: str) -> bool:
        """Quick DNS resolution check."""
        try:
            import socket
            socket.gethostbyname(domain)
            return True
        except socket.gaierror:
            return False

    def _verify_and_fix_protocol_with_timeout(self, candidate: URLCandidate) -> str:
        """Verify URL protocol with adaptive timeouts."""
        parsed = urlparse(candidate.url)

        # Get adaptive timeout for verification
        verification_timeout = self.timeout_manager.get_optimal_timeout(
            candidate.url,
            operation_type='head_request',
            context={'parish_id': candidate.parish_id}
        )

        # Try HTTPS first, then HTTP
        for scheme in ['https', 'http']:
            test_url = urlunparse((scheme, parsed.netloc, parsed.path,
                                 parsed.params, parsed.query, parsed.fragment))
            try:
                response = requests.head(
                    test_url,
                    timeout=min(verification_timeout, 10.0),  # Cap at 10s for verification
                    allow_redirects=True
                )
                if response.status_code < 400:
                    # Record successful response for timeout optimization
                    self.timeout_manager.record_response(
                        test_url,
                        'head_request',
                        response.elapsed.total_seconds(),
                        True
                    )
                    return test_url
            except Exception as e:
                # Record failed response for timeout optimization
                self.timeout_manager.record_response(
                    test_url,
                    'head_request',
                    verification_timeout,
                    False,
                    str(e)
                )
                continue

        # If both fail, return original
        return candidate.url

    def _verify_and_fix_protocol(self, url: str) -> str:
        """Legacy method for backward compatibility."""
        candidate = URLCandidate(url=url, parish_id=0)
        return self._verify_and_fix_protocol_with_timeout(candidate)

    def _is_schedule_relevant_url(self, url: str) -> bool:
        """Check if URL is likely to contain schedule information."""
        url_lower = url.lower()

        relevant_terms = [
            'reconciliation', 'confession', 'adoration', 'eucharistic',
            'mass', 'times', 'schedule', 'hours', 'worship', 'liturgy',
            'sacrament', 'parish', 'church'
        ]

        return any(term in url_lower for term in relevant_terms)

    def get_timeout_for_url(self, url: str, strategy: str, operation_type: str = 'page_load', context: Dict = None) -> float:
        """Get optimized timeout for URL using adaptive timeout management."""
        # Use adaptive timeout manager for intelligent timeout calculation
        return self.timeout_manager.get_optimal_timeout(
            url,
            operation_type=operation_type,
            context=context or {}
        )

    def get_timeout_for_url_legacy(self, url: str, strategy: str) -> float:
        """Legacy timeout method for backward compatibility."""
        base_timeouts = {
            'fast': 15.0,
            'moderate': 30.0,
            'extended': 60.0,
            'adaptive': 30.0
        }

        timeout = base_timeouts.get(strategy, 30.0)

        # Adjust based on URL characteristics
        domain = urlparse(url).netloc.lower()

        # Known slow patterns
        if any(pattern in domain for pattern in ['wix.com', 'weebly.com']):
            timeout *= 1.5

        # Known fast patterns
        elif any(pattern in domain for pattern in ['archatl.com', 'wordpress.com']):
            timeout *= 0.8

        return min(timeout, 90.0)  # Never exceed 90 seconds


def get_enhanced_url_manager(supabase: Client = None) -> EnhancedURLManager:
    """Factory function to create enhanced URL manager."""
    return EnhancedURLManager(supabase)