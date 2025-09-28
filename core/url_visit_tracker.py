#!/usr/bin/env python3
"""
URL Visit Result Tracking System

This module provides comprehensive tracking of URL visits during schedule extraction,
recording detailed results for optimization, ML training, and debugging purposes.
"""

import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from core.db import get_supabase_client
from core.logger import get_logger
from supabase import Client

logger = get_logger(__name__)


class VisitStatus(Enum):
    """Visit status types."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DNS_ERROR = "dns_error"
    HTTP_ERROR = "http_error"
    PARSING_ERROR = "parsing_error"
    BLOCKED = "blocked"


class ContentQuality(Enum):
    """Content quality assessment."""

    EXCELLENT = 1.0  # Schedule data found with high confidence
    GOOD = 0.8  # Schedule keywords found, likely relevant
    FAIR = 0.6  # Some religious content, possibly relevant
    POOR = 0.4  # Generic content, low relevance
    IRRELEVANT = 0.2  # No relevant content found
    ERROR = 0.0  # Could not assess content


@dataclass
class VisitResult:
    """Comprehensive URL visit result data."""

    url: str
    parish_id: int
    visited_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # HTTP Response Data
    http_status: Optional[int] = None
    response_time_ms: Optional[int] = None
    content_type: Optional[str] = None
    content_size_bytes: Optional[int] = None

    # Extraction Results
    visit_status: VisitStatus = VisitStatus.FAILED
    extraction_success: bool = False
    schedule_data_found: bool = False
    schedule_keywords_count: int = 0

    # Error Information
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    # Content Quality Assessment
    quality_score: float = 0.0
    relevance_indicators: List[str] = field(default_factory=list)

    # Metadata
    user_agent: Optional[str] = None
    redirect_count: int = 0
    final_url: Optional[str] = None


class URLVisitTracker:
    """
    Comprehensive URL visit tracking system for schedule extraction optimization.
    """

    def __init__(self, supabase: Client = None):
        """Initialize the URL visit tracker."""
        self.supabase = supabase or get_supabase_client()
        self.logger = logger

        # Schedule-related keywords for content assessment
        self.schedule_keywords = {
            "high_value": [
                "reconciliation",
                "confession",
                "confessions",
                "penance",
                "adoration",
                "eucharistic adoration",
                "blessed sacrament",
                "mass times",
                "mass schedule",
                "service times",
                "worship times",
            ],
            "medium_value": [
                "schedule",
                "schedules",
                "times",
                "hours",
                "calendar",
                "liturgy",
                "worship",
                "service",
                "services",
                "sacraments",
                "daily mass",
                "weekend mass",
                "holy day",
                "holy days",
            ],
            "low_value": [
                "mass",
                "parish",
                "church",
                "catholic",
                "faith",
                "community",
                "ministry",
                "ministries",
                "prayer",
                "spiritual",
            ],
        }

        # Schema detection - check what columns are available
        self._detect_schema()

        logger.info("🔍 URL Visit Tracker initialized")

    def _detect_schema(self):
        """Detect available columns in DiscoveredUrls table."""
        try:
            # Try to query with new columns to see what's available
            test_result = self.supabase.table("DiscoveredUrls").select("*").limit(1).execute()
            if test_result.data:
                self.available_columns = set(test_result.data[0].keys())
            else:
                # No data, try to insert a test record to see schema
                self.available_columns = {"id", "parish_id", "url", "score", "source_url", "visited", "created_at"}

            # Check for enhanced columns
            self.has_enhanced_schema = "visited_at" in self.available_columns

            if self.has_enhanced_schema:
                logger.info("🔍 Enhanced schema detected - full visit tracking available")
            else:
                logger.info("🔍 Basic schema detected - limited visit tracking available")

        except Exception as e:
            logger.warning(f"🔍 Schema detection failed: {e}, assuming basic schema")
            self.available_columns = {"id", "parish_id", "url", "score", "source_url", "visited", "created_at"}
            self.has_enhanced_schema = False

    def record_visit(self, visit_result: VisitResult) -> bool:
        """
        Record a URL visit result in the database.

        Args:
            visit_result: Complete visit result data

        Returns:
            bool: True if recording was successful
        """
        try:
            # Calculate priority score from quality score
            priority_score = int(max(visit_result.quality_score * 100, 1))

            # Prepare data based on available schema
            if self.has_enhanced_schema:
                # Full enhanced tracking
                update_data = {
                    "visited": True,
                    "score": priority_score,  # Required field
                    "visited_at": visit_result.visited_at.isoformat(),
                    "http_status": visit_result.http_status,
                    "response_time_ms": visit_result.response_time_ms,
                    "content_type": visit_result.content_type,
                    "content_size_bytes": visit_result.content_size_bytes,
                    "extraction_success": visit_result.extraction_success,
                    "schedule_data_found": visit_result.schedule_data_found,
                    "schedule_keywords_count": visit_result.schedule_keywords_count,
                    "error_type": visit_result.error_type,
                    "error_message": visit_result.error_message,
                    "quality_score": visit_result.quality_score,
                    "visit_count": 1,  # Will be incremented if record exists
                }

                if visit_result.extraction_success:
                    update_data["last_successful_visit"] = visit_result.visited_at.isoformat()

            else:
                # Basic schema tracking
                update_data = {"visited": True, "score": priority_score}  # Required field

            # Update existing record or create if not exists
            result = (
                self.supabase.table("DiscoveredUrls")
                .upsert(
                    {"url": visit_result.url, "parish_id": visit_result.parish_id, **update_data}, on_conflict="url,parish_id"
                )
                .execute()
            )

            logger.debug(f"🔍 Recorded visit for {visit_result.url}: {visit_result.visit_status.value}")
            return True

        except Exception as e:
            logger.error(f"🔍 Error recording visit for {visit_result.url}: {e}")
            return False

    def create_visit_result(self, url: str, parish_id: int) -> VisitResult:
        """
        Create a new VisitResult object for tracking.

        Args:
            url: URL being visited
            parish_id: Parish ID for the extraction

        Returns:
            VisitResult: Initialized visit result object
        """
        return VisitResult(url=url, parish_id=parish_id)

    def record_http_response(
        self,
        visit_result: VisitResult,
        status_code: int,
        response_time: float,
        content_type: str = None,
        content_size: int = None,
        final_url: str = None,
    ):
        """Record HTTP response details."""
        visit_result.http_status = status_code
        visit_result.response_time_ms = int(response_time * 1000)
        visit_result.content_type = content_type
        visit_result.content_size_bytes = content_size
        visit_result.final_url = final_url

    def record_extraction_attempt(self, visit_result: VisitResult, success: bool, error: Exception = None):
        """Record extraction attempt results."""
        visit_result.extraction_success = success
        visit_result.visit_status = VisitStatus.SUCCESS if success else VisitStatus.FAILED

        if error:
            visit_result.error_type = type(error).__name__
            visit_result.error_message = str(error)[:500]  # Limit message length

    def assess_content_quality(self, visit_result: VisitResult, content: str, schedule_data_found: bool = False) -> float:
        """
        Assess the quality and relevance of extracted content.

        Args:
            visit_result: Visit result to update
            content: Text content to assess
            schedule_data_found: Whether schedule data was successfully extracted

        Returns:
            float: Quality score (0.0 to 1.0)
        """
        if not content:
            visit_result.quality_score = ContentQuality.ERROR.value
            return visit_result.quality_score

        content_lower = content.lower()
        total_score = 0.0
        keyword_count = 0
        found_indicators = []

        # High-value keywords (significant impact)
        for keyword in self.schedule_keywords["high_value"]:
            if keyword in content_lower:
                count = content_lower.count(keyword)
                total_score += count * 3.0
                keyword_count += count
                found_indicators.append(f"high:{keyword}({count})")

        # Medium-value keywords (moderate impact)
        for keyword in self.schedule_keywords["medium_value"]:
            if keyword in content_lower:
                count = content_lower.count(keyword)
                total_score += count * 2.0
                keyword_count += count
                found_indicators.append(f"med:{keyword}({count})")

        # Low-value keywords (minor impact)
        for keyword in self.schedule_keywords["low_value"]:
            if keyword in content_lower:
                count = content_lower.count(keyword)
                total_score += count * 1.0
                keyword_count += count
                found_indicators.append(f"low:{keyword}({count})")

        # Normalize score
        if schedule_data_found:
            quality_score = ContentQuality.EXCELLENT.value
        elif total_score >= 10:
            quality_score = ContentQuality.GOOD.value
        elif total_score >= 5:
            quality_score = ContentQuality.FAIR.value
        elif total_score >= 2:
            quality_score = ContentQuality.POOR.value
        elif keyword_count > 0:
            quality_score = ContentQuality.IRRELEVANT.value
        else:
            quality_score = ContentQuality.ERROR.value

        # Update visit result
        visit_result.schedule_data_found = schedule_data_found
        visit_result.schedule_keywords_count = keyword_count
        visit_result.quality_score = quality_score
        visit_result.relevance_indicators = found_indicators[:20]  # Limit stored indicators

        return quality_score

    def get_visit_statistics(self, parish_id: int = None) -> Dict[str, Any]:
        """
        Get visit statistics for analysis.

        Args:
            parish_id: Optional parish ID to filter statistics

        Returns:
            Dict containing visit statistics
        """
        try:
            query = self.supabase.table("DiscoveredUrls").select("*")
            if parish_id:
                query = query.eq("parish_id", parish_id)

            result = query.execute()
            urls = result.data

            stats = {
                "total_urls": len(urls),
                "visited_urls": sum(1 for u in urls if u.get("visited", False)),
                "unvisited_urls": sum(1 for u in urls if not u.get("visited", False)),
            }

            if self.has_enhanced_schema:
                successful_visits = [u for u in urls if u.get("extraction_success", False)]
                failed_visits = [u for u in urls if u.get("visited") and not u.get("extraction_success", False)]

                stats.update(
                    {
                        "successful_extractions": len(successful_visits),
                        "failed_extractions": len(failed_visits),
                        "schedule_data_found": sum(1 for u in urls if u.get("schedule_data_found", False)),
                        "avg_quality_score": sum(u.get("quality_score", 0) for u in urls) / len(urls) if urls else 0,
                        "avg_response_time": (
                            sum(u.get("response_time_ms", 0) for u in urls if u.get("response_time_ms"))
                            / len([u for u in urls if u.get("response_time_ms")])
                            if any(u.get("response_time_ms") for u in urls)
                            else 0
                        ),
                    }
                )

            return stats

        except Exception as e:
            logger.error(f"🔍 Error getting visit statistics: {e}")
            return {}

    def get_successful_urls(self, parish_id: int) -> List[Dict[str, Any]]:
        """
        Get URLs that had successful schedule data extraction.

        Args:
            parish_id: Parish ID to filter by

        Returns:
            List of successful URL records
        """
        try:
            if self.has_enhanced_schema:
                result = (
                    self.supabase.table("DiscoveredUrls")
                    .select("*")
                    .eq("parish_id", parish_id)
                    .eq("schedule_data_found", True)
                    .execute()
                )
            else:
                # Fallback: use ParishData to identify successful URLs
                result = self.supabase.table("ParishData").select("fact_source_url").eq("parish_id", parish_id).execute()

                successful_urls = []
                for record in result.data:
                    url = record.get("fact_source_url")
                    if url:
                        successful_urls.append({"url": url, "parish_id": parish_id})
                return successful_urls

            return result.data

        except Exception as e:
            logger.error(f"🔍 Error getting successful URLs for parish {parish_id}: {e}")
            return []

    def mark_url_as_visited(self, url: str, parish_id: int, visited_at: datetime = None):
        """
        Simple method to mark a URL as visited with timestamp.

        Args:
            url: URL that was visited
            parish_id: Parish ID
            visited_at: Visit timestamp (defaults to now)
        """
        if visited_at is None:
            visited_at = datetime.now(timezone.utc)

        visit_result = VisitResult(
            url=url, parish_id=parish_id, visited_at=visited_at, visit_status=VisitStatus.SUCCESS, extraction_success=True
        )

        self.record_visit(visit_result)


def get_url_visit_tracker(supabase: Client = None) -> URLVisitTracker:
    """Factory function to create URL visit tracker."""
    return URLVisitTracker(supabase)


# Context manager for automatic visit tracking
class VisitTracker:
    """Context manager for automatic URL visit tracking."""

    def __init__(self, url: str, parish_id: int, tracker: URLVisitTracker = None):
        self.url = url
        self.parish_id = parish_id
        self.tracker = tracker or get_url_visit_tracker()
        self.visit_result = None
        self.start_time = None

    def __enter__(self) -> VisitResult:
        """Start visit tracking."""
        self.start_time = time.time()
        self.visit_result = self.tracker.create_visit_result(self.url, self.parish_id)
        return self.visit_result

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End visit tracking and record results."""
        if self.visit_result:
            # Record any exception that occurred
            if exc_type:
                self.visit_result.error_type = exc_type.__name__
                self.visit_result.error_message = str(exc_val)[:500] if exc_val else None
                self.visit_result.visit_status = VisitStatus.FAILED

            # Calculate total time if not already set
            if self.visit_result.response_time_ms is None and self.start_time:
                elapsed_ms = int((time.time() - self.start_time) * 1000)
                self.visit_result.response_time_ms = elapsed_ms

            # Record the visit
            self.tracker.record_visit(self.visit_result)
