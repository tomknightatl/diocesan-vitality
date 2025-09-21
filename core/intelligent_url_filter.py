#!/usr/bin/env python3
"""
Intelligent URL filtering system for enhanced extraction efficiency.

This module provides pre-filtering capabilities to reduce wasted processing
on low-probability URLs before they reach the verification stage.
"""

import re
import urllib.parse
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Set, Tuple

from core.logger import get_logger

logger = get_logger(__name__)


class URLQuality(Enum):
    """URL quality levels for processing prioritization."""

    EXCELLENT = "excellent"  # Very high probability of success
    GOOD = "good"  # Good probability of success
    FAIR = "fair"  # Moderate probability of success
    POOR = "poor"  # Low probability of success
    SKIP = "skip"  # Should be skipped entirely


@dataclass
class URLAnalysis:
    """Analysis result for a single URL."""

    url: str
    quality: URLQuality
    confidence_score: float
    reasons: List[str]
    estimated_processing_time: float


class IntelligentURLFilter:
    """
    Intelligent URL filtering system to optimize processing efficiency.

    Pre-filters URLs based on:
    - URL structure patterns
    - Content type indicators
    - Blacklisted patterns
    - ML confidence scores
    - Historical success patterns
    """

    def __init__(self):
        self.logger = get_logger(__name__)

        # High-value URL patterns
        self.high_value_patterns = [
            # Schedule-related patterns
            r"(?i)(reconciliation|confession|adoration|eucharistic)",
            r"(?i)(schedule|times|hours|worship)",
            r"(?i)(mass.*times|liturgy.*schedule)",
            r"(?i)(sacrament|prayer|devotion)",
            # Common CMS schedule paths
            r"/schedule",
            r"/times",
            r"/worship",
            r"/mass",
            r"/liturgy",
            r"/sacraments",
            r"/reconciliation",
            r"/adoration",
            r"/confession",
            r"/prayer",
        ]

        # Medium-value patterns
        self.medium_value_patterns = [
            r"(?i)(parish|church|catholic)",
            r"(?i)(ministry|ministries|faith)",
            r"(?i)(events|calendar|bulletin)",
            r"/about",
            r"/ministries",
            r"/events",
        ]

        # Low-value patterns (still worth checking but lower priority)
        self.low_value_patterns = [
            r"(?i)(community|news|announcements)",
            r"(?i)(education|school|youth)",
            r"/news",
            r"/community",
            r"/education",
        ]

        # Blacklisted patterns (skip entirely)
        self.blacklisted_patterns = [
            # Administrative/technical pages
            r"(?i)(admin|wp-admin|login|register|signup)",
            r"(?i)(forgot.*password|reset.*password)",
            r"(?i)(privacy.*policy|terms.*service|legal)",
            r"(?i)(sitemap|robots\.txt|favicon\.ico)",
            # File types that won't contain schedules
            r"\.(pdf|jpg|jpeg|png|gif|svg|ico|css|js|xml|json)$",
            r"\.(doc|docx|xls|xlsx|ppt|pptx|zip|rar)$",
            # Contact/donation pages
            r"(?i)(contact|phone|email|address)",
            r"(?i)(donat|giving|tithe|contribution)",
            r"(?i)(staff|clergy|personnel|directory)",
            # Social media and external links
            r"(?i)(facebook|twitter|instagram|youtube)",
            r"(?i)(linkedin|pinterest|social)",
            # Generic CMS pages
            r"(?i)(search|404|error|not.*found)",
            r"(?i)(maintenance|coming.*soon|under.*construction)",
        ]

        # Domain-specific blacklists
        self.blacklisted_domains = {
            "facebook.com",
            "twitter.com",
            "instagram.com",
            "youtube.com",
            "linkedin.com",
            "pinterest.com",
            "google.com",
            "bing.com",
            "yahoo.com",
            "microsoft.com",
            "apple.com",
        }

        # File extension blacklist
        self.blacklisted_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".ico",
            ".webp",
            ".css",
            ".js",
            ".json",
            ".xml",
            ".txt",
            ".zip",
            ".rar",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
            ".wav",
            ".wmv",
        }

    def analyze_urls(self, urls: List[str], ml_predictions: Dict[str, float] = None) -> List[URLAnalysis]:
        """
        Analyze a list of URLs and return quality assessments.

        Args:
            urls: List of URLs to analyze
            ml_predictions: Optional ML confidence scores for URLs

        Returns:
            List of URLAnalysis objects sorted by quality/confidence
        """
        self.logger.info(f"🔍 Analyzing {len(urls)} URLs for processing efficiency")

        analyses = []
        ml_predictions = ml_predictions or {}

        for url in urls:
            analysis = self._analyze_single_url(url, ml_predictions.get(url, 0.0))
            analyses.append(analysis)

        # Sort by quality and confidence score
        analyses.sort(key=lambda x: (x.quality.value, x.confidence_score), reverse=True)

        # Log analysis summary
        quality_counts = {}
        for analysis in analyses:
            quality_counts[analysis.quality.value] = quality_counts.get(analysis.quality.value, 0) + 1

        self.logger.info(f"🔍 URL Analysis Summary: {quality_counts}")

        return analyses

    def _analyze_single_url(self, url: str, ml_confidence: float) -> URLAnalysis:
        """Analyze a single URL and determine its processing priority."""
        reasons = []
        confidence_score = 0.0
        estimated_time = 10.0  # Base processing time in seconds

        # Parse URL components
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            query = parsed.query.lower()
            fragment = parsed.fragment.lower()
            full_url_lower = url.lower()
        except Exception as e:
            self.logger.warning(f"🔍 Failed to parse URL {url}: {e}")
            return URLAnalysis(url, URLQuality.SKIP, 0.0, ["Invalid URL format"], 0.0)

        # Check blacklisted domains
        if any(blacklisted in domain for blacklisted in self.blacklisted_domains):
            return URLAnalysis(url, URLQuality.SKIP, 0.0, ["Blacklisted domain"], 0.0)

        # Check blacklisted patterns
        for pattern in self.blacklisted_patterns:
            if re.search(pattern, full_url_lower):
                return URLAnalysis(url, URLQuality.SKIP, 0.0, [f"Blacklisted pattern: {pattern}"], 0.0)

        # Check file extensions
        path_lower = path.lower()
        for ext in self.blacklisted_extensions:
            if path_lower.endswith(ext):
                return URLAnalysis(url, URLQuality.SKIP, 0.0, [f"Blacklisted extension: {ext}"], 0.0)

        # Analyze high-value patterns
        high_value_matches = 0
        for pattern in self.high_value_patterns:
            if re.search(pattern, full_url_lower):
                high_value_matches += 1
                confidence_score += 25.0
                reasons.append(f"High-value pattern: {pattern}")

        # Analyze medium-value patterns
        medium_value_matches = 0
        for pattern in self.medium_value_patterns:
            if re.search(pattern, full_url_lower):
                medium_value_matches += 1
                confidence_score += 15.0
                reasons.append(f"Medium-value pattern: {pattern}")

        # Analyze low-value patterns
        low_value_matches = 0
        for pattern in self.low_value_patterns:
            if re.search(pattern, full_url_lower):
                low_value_matches += 1
                confidence_score += 5.0
                reasons.append(f"Low-value pattern: {pattern}")

        # Apply ML confidence boost
        if ml_confidence > 0.3:
            confidence_score += ml_confidence * 50.0
            reasons.append(f"ML confidence: {ml_confidence:.3f}")
            estimated_time *= 0.8  # ML-predicted URLs process faster

        # URL structure analysis
        path_depth = len([p for p in parsed.path.split("/") if p])
        if path_depth <= 2:
            confidence_score += 10.0
            reasons.append("Simple URL structure")
        elif path_depth > 5:
            confidence_score -= 10.0
            estimated_time *= 1.3
            reasons.append("Complex URL structure")

        # Query parameters indicate dynamic content
        if parsed.query:
            confidence_score -= 5.0
            estimated_time *= 1.2
            reasons.append("Dynamic parameters present")

        # Determine quality level
        if confidence_score >= 80.0:
            quality = URLQuality.EXCELLENT
            estimated_time *= 0.7
        elif confidence_score >= 60.0:
            quality = URLQuality.GOOD
            estimated_time *= 0.8
        elif confidence_score >= 40.0:
            quality = URLQuality.FAIR
        elif confidence_score >= 20.0:
            quality = URLQuality.POOR
            estimated_time *= 1.5
        else:
            quality = URLQuality.SKIP
            estimated_time = 0.0

        return URLAnalysis(
            url=url,
            quality=quality,
            confidence_score=min(confidence_score, 100.0),
            reasons=reasons,
            estimated_processing_time=estimated_time,
        )

    def filter_urls(
        self, urls: List[str], max_urls: int = 50, ml_predictions: Dict[str, float] = None
    ) -> Tuple[List[str], Dict[str, URLAnalysis]]:
        """
        Filter URLs and return the top candidates for processing.

        Args:
            urls: List of URLs to filter
            max_urls: Maximum number of URLs to return
            ml_predictions: Optional ML confidence scores

        Returns:
            Tuple of (filtered_urls, analysis_dict)
        """
        self.logger.info(f"🔍 Filtering {len(urls)} URLs to top {max_urls} candidates")

        # Analyze all URLs
        analyses = self.analyze_urls(urls, ml_predictions)

        # Filter out URLs marked for skipping
        processable_analyses = [a for a in analyses if a.quality != URLQuality.SKIP]

        # Take top candidates up to max_urls
        top_analyses = processable_analyses[:max_urls]

        # Extract URLs and create analysis dictionary
        filtered_urls = [a.url for a in top_analyses]
        analysis_dict = {a.url: a for a in top_analyses}

        # Log filtering results
        skipped_count = len(urls) - len(processable_analyses)
        self.logger.info(f"🔍 URL Filtering Results:")
        self.logger.info(f"   📊 Total URLs: {len(urls)}")
        self.logger.info(f"   ✅ Processable: {len(processable_analyses)}")
        self.logger.info(f"   🚫 Skipped: {skipped_count}")
        self.logger.info(f"   🎯 Selected for processing: {len(filtered_urls)}")

        if top_analyses:
            avg_confidence = sum(a.confidence_score for a in top_analyses) / len(top_analyses)
            estimated_total_time = sum(a.estimated_processing_time for a in top_analyses)
            self.logger.info(f"   🎯 Average confidence: {avg_confidence:.1f}%")
            self.logger.info(f"   ⏱️ Estimated processing time: {estimated_total_time:.1f}s")

        return filtered_urls, analysis_dict

    def get_priority_batches(self, analyses: List[URLAnalysis], batch_size: int = 10) -> List[List[URLAnalysis]]:
        """
        Group URLs into priority batches for sequential processing.

        Args:
            analyses: List of URL analyses
            batch_size: Maximum URLs per batch

        Returns:
            List of batches (lists of URLAnalysis)
        """
        # Group by quality level
        quality_groups = {URLQuality.EXCELLENT: [], URLQuality.GOOD: [], URLQuality.FAIR: [], URLQuality.POOR: []}

        for analysis in analyses:
            if analysis.quality in quality_groups:
                quality_groups[analysis.quality].append(analysis)

        batches = []

        # Process each quality level
        for quality in [URLQuality.EXCELLENT, URLQuality.GOOD, URLQuality.FAIR, URLQuality.POOR]:
            group = quality_groups[quality]
            if not group:
                continue

            # Sort by confidence within quality level
            group.sort(key=lambda x: x.confidence_score, reverse=True)

            # Create batches
            for i in range(0, len(group), batch_size):
                batch = group[i : i + batch_size]
                batches.append(batch)

        self.logger.info(f"🔍 Created {len(batches)} priority batches for processing")
        return batches


# Global instance for easy access
_global_url_filter = None


def get_url_filter() -> IntelligentURLFilter:
    """Get global URL filter instance."""
    global _global_url_filter
    if _global_url_filter is None:
        _global_url_filter = IntelligentURLFilter()
    return _global_url_filter
