#!/usr/bin/env python3
"""
Robust Error Handling with Graceful Degradation

This module implements comprehensive error handling with intelligent fallback
mechanisms to ensure pipeline resilience and continuous operation even when
individual components fail.
"""

import functools
import json
import re
import time
import traceback
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

from core.logger import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FallbackStrategy(Enum):
    """Available fallback strategies."""

    RETRY = "retry"
    FALLBACK_METHOD = "fallback_method"
    DEFAULT_VALUE = "default_value"
    SKIP = "skip"
    ESCALATE = "escalate"


@dataclass
class ErrorContext:
    """Context information for error handling."""

    operation: str
    url: Optional[str] = None
    parish_id: Optional[int] = None
    diocese_id: Optional[int] = None
    attempt_number: int = 1
    start_time: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""

    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    fallback_methods: List[str] = field(default_factory=list)
    default_value: Any = None
    skip_on_failure: bool = False
    severity_threshold: ErrorSeverity = ErrorSeverity.HIGH


@dataclass
class ErrorMetrics:
    """Tracking error patterns and recovery success."""

    total_errors: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors_by_operation: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=100))
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    last_error_time: Optional[float] = None


class RobustErrorHandler:
    """
    Comprehensive error handling system with intelligent fallback mechanisms.
    """

    def __init__(self):
        self.logger = logger
        self.metrics = ErrorMetrics()

        # Fallback configurations by operation type
        self.fallback_configs: Dict[str, FallbackConfig] = {
            "ai_analysis": FallbackConfig(
                max_retries=2,
                retry_delay=0.5,
                fallback_methods=["regex_analysis", "keyword_search", "structure_analysis"],
                default_value={"parishes": [], "confidence": 0.1},
                severity_threshold=ErrorSeverity.MEDIUM,
            ),
            "web_scraping": FallbackConfig(
                max_retries=3,
                retry_delay=2.0,
                retry_backoff=1.5,
                fallback_methods=["requests_fallback", "selenium_fallback", "cached_content"],
                default_value=None,
                severity_threshold=ErrorSeverity.HIGH,
            ),
            "database_operation": FallbackConfig(
                max_retries=5,
                retry_delay=0.5,
                retry_backoff=1.2,
                fallback_methods=["retry_with_exponential_backoff", "read_only_fallback"],
                severity_threshold=ErrorSeverity.CRITICAL,
            ),
            "url_prediction": FallbackConfig(
                max_retries=1,
                fallback_methods=["pattern_based_prediction", "static_patterns"],
                default_value=[],
                severity_threshold=ErrorSeverity.LOW,
            ),
            "content_parsing": FallbackConfig(
                max_retries=2,
                fallback_methods=["alternative_parser", "regex_extraction", "manual_patterns"],
                default_value={},
                severity_threshold=ErrorSeverity.MEDIUM,
            ),
        }

        # Error pattern recognition
        self.error_patterns = {
            "network_timeout": [
                r"timeout",
                r"connection.*timed out",
                r"read.*timeout",
                r"socket.*timeout",
                r"request.*timeout",
            ],
            "network_connection": [
                r"connection.*refused",
                r"connection.*reset",
                r"network.*unreachable",
                r"name.*not.*resolved",
                r"no route to host",
            ],
            "http_client_error": [r"404", r"not found", r"forbidden", r"unauthorized", r"bad request"],
            "http_server_error": [
                r"500",
                r"502",
                r"503",
                r"504",
                r"internal server error",
                r"bad gateway",
                r"service unavailable",
            ],
            "parsing_error": [r"json.*decode", r"xml.*parse", r"html.*parse", r"invalid.*syntax", r"malformed.*data"],
            "ai_service_error": [r"ai.*error", r"model.*error", r"api.*quota", r"rate.*limit", r"service.*unavailable"],
            "database_error": [
                r"database.*error",
                r"connection.*pool",
                r"sql.*error",
                r"table.*not.*exist",
                r"constraint.*violation",
            ],
            "selenium_error": [
                r"webdriver.*exception",
                r"element.*not.*found",
                r"session.*not.*created",
                r"chrome.*not.*found",
                r"browser.*crash",
            ],
        }

        logger.info("🛡️ Robust Error Handler initialized")

    def handle_with_fallback(self, operation: str, primary_func: Callable, context: ErrorContext = None, **kwargs) -> Any:
        """
        Execute function with comprehensive error handling and fallback.

        Args:
            operation: Operation identifier for fallback configuration
            primary_func: Primary function to execute
            context: Error context information
            **kwargs: Additional arguments for fallback functions

        Returns:
            Result from successful execution or fallback
        """
        if context is None:
            context = ErrorContext(operation=operation)

        config = self.fallback_configs.get(operation, FallbackConfig())
        last_exception = None

        # Try primary function with retries
        for attempt in range(1, config.max_retries + 2):  # +1 for initial attempt
            try:
                context.attempt_number = attempt

                if attempt > 1:
                    delay = config.retry_delay * (config.retry_backoff ** (attempt - 2))
                    logger.info(f"🛡️ Retrying {operation} (attempt {attempt}) after {delay:.1f}s delay")
                    time.sleep(delay)

                result = primary_func(context, **kwargs)

                if attempt > 1:
                    self.metrics.successful_recoveries += 1
                    logger.info(f"🛡️ ✅ {operation} succeeded on retry attempt {attempt}")

                return result

            except Exception as e:
                last_exception = e
                error_type = self._classify_error(str(e))

                self._record_error(operation, error_type, str(e), context)

                logger.warning(
                    f"🛡️ {operation} failed (attempt {attempt}/{config.max_retries + 1}): " f"{error_type} - {str(e)[:200]}"
                )

                # Check if we should continue retrying
                if attempt > config.max_retries or not self._should_retry(error_type, config):
                    break

        # Primary function failed, try fallback methods
        return self._execute_fallback_methods(operation, config, context, last_exception, **kwargs)

    def _execute_fallback_methods(
        self, operation: str, config: FallbackConfig, context: ErrorContext, primary_exception: Exception, **kwargs
    ) -> Any:
        """Execute fallback methods in sequence."""

        for fallback_method in config.fallback_methods:
            try:
                logger.info(f"🛡️ Trying fallback method: {fallback_method} for {operation}")

                result = self._execute_fallback_method(operation, fallback_method, context, **kwargs)

                if result is not None:
                    self.metrics.successful_recoveries += 1
                    logger.info(f"🛡️ ✅ Fallback method '{fallback_method}' succeeded for {operation}")
                    return result

            except Exception as e:
                logger.warning(f"🛡️ Fallback method '{fallback_method}' failed: {str(e)[:200]}")
                continue

        # All fallback methods failed
        self.metrics.failed_recoveries += 1

        # Return default value or re-raise exception based on configuration
        if config.default_value is not None:
            logger.warning(f"🛡️ Using default value for {operation}")
            return config.default_value
        elif config.skip_on_failure:
            logger.warning(f"🛡️ Skipping {operation} due to failure")
            return None
        else:
            severity = self._determine_error_severity(str(primary_exception), config)
            if severity == ErrorSeverity.CRITICAL:
                logger.error(f"🛡️ Critical error in {operation}, re-raising")
                raise primary_exception
            else:
                logger.warning(f"🛡️ Non-critical error in {operation}, continuing with default")
                return config.default_value

    def _execute_fallback_method(self, operation: str, method_name: str, context: ErrorContext, **kwargs) -> Any:
        """Execute a specific fallback method."""

        # AI Analysis fallbacks
        if operation == "ai_analysis":
            if method_name == "regex_analysis":
                return self._regex_analysis_fallback(context, **kwargs)
            elif method_name == "keyword_search":
                return self._keyword_search_fallback(context, **kwargs)
            elif method_name == "structure_analysis":
                return self._structure_analysis_fallback(context, **kwargs)

        # Web scraping fallbacks
        elif operation == "web_scraping":
            if method_name == "requests_fallback":
                return self._requests_fallback(context, **kwargs)
            elif method_name == "selenium_fallback":
                return self._selenium_fallback(context, **kwargs)
            elif method_name == "cached_content":
                return self._cached_content_fallback(context, **kwargs)

        # URL prediction fallbacks
        elif operation == "url_prediction":
            if method_name == "pattern_based_prediction":
                return self._pattern_based_prediction_fallback(context, **kwargs)
            elif method_name == "static_patterns":
                return self._static_patterns_fallback(context, **kwargs)

        # Content parsing fallbacks
        elif operation == "content_parsing":
            if method_name == "alternative_parser":
                return self._alternative_parser_fallback(context, **kwargs)
            elif method_name == "regex_extraction":
                return self._regex_extraction_fallback(context, **kwargs)
            elif method_name == "manual_patterns":
                return self._manual_patterns_fallback(context, **kwargs)

        # Database operation fallbacks
        elif operation == "database_operation":
            if method_name == "retry_with_exponential_backoff":
                return self._database_retry_fallback(context, **kwargs)
            elif method_name == "read_only_fallback":
                return self._read_only_database_fallback(context, **kwargs)

        raise NotImplementedError(f"Fallback method '{method_name}' not implemented for '{operation}'")

    def _regex_analysis_fallback(self, context: ErrorContext, content: str = "", **kwargs) -> Dict:
        """Fallback AI analysis using regex patterns."""
        try:
            parishes = []

            # Basic parish name extraction patterns
            name_patterns = [
                r"<h[1-6][^>]*>([^<]*(?:church|parish|cathedral|basilica)[^<]*)</h[1-6]>",
                r'class=["\'][^"\']*name[^"\']*["\'][^>]*>([^<]+)</[^>]+>',
                r"<title>([^<]*(?:church|parish|cathedral)[^<]*)</title>",
            ]

            # Basic address extraction patterns
            address_patterns = [
                r"\b\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard)\b[^<]*",
                r"\b[A-Z][a-z]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b",
            ]

            for pattern in name_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    name = match.group(1).strip()
                    if len(name) > 5 and len(name) < 100:  # Reasonable name length
                        parishes.append({"name": name, "confidence": 0.3})

            return {"parishes": parishes[:10], "confidence": 0.3, "method": "regex_analysis"}  # Limit to 10 results

        except Exception as e:
            logger.debug(f"🛡️ Regex analysis fallback failed: {e}")
            return {"parishes": [], "confidence": 0.1, "method": "regex_analysis_failed"}

    def _keyword_search_fallback(self, context: ErrorContext, content: str = "", **kwargs) -> Dict:
        """Fallback using simple keyword search."""
        try:
            content_lower = content.lower()

            # Schedule-related keywords with weights
            schedule_keywords = {
                "reconciliation": 5,
                "confession": 5,
                "adoration": 5,
                "mass times": 4,
                "mass schedule": 4,
                "worship": 3,
                "liturgy": 3,
                "sacrament": 2,
            }

            found_schedules = []
            for keyword, weight in schedule_keywords.items():
                if keyword in content_lower:
                    # Extract context around the keyword
                    start = max(0, content_lower.find(keyword) - 100)
                    end = min(len(content), content_lower.find(keyword) + 100)
                    context_text = content[start:end]

                    found_schedules.append({"type": keyword, "context": context_text.strip(), "confidence": weight / 10.0})

            return {"schedules": found_schedules, "confidence": 0.4 if found_schedules else 0.1, "method": "keyword_search"}

        except Exception as e:
            logger.debug(f"🛡️ Keyword search fallback failed: {e}")
            return {"schedules": [], "confidence": 0.1, "method": "keyword_search_failed"}

    def _structure_analysis_fallback(self, context: ErrorContext, content: str = "", **kwargs) -> Dict:
        """Fallback using HTML structure analysis."""
        try:
            # Simple HTML element counting for complexity assessment
            elements = {
                "tables": content.lower().count("<table"),
                "lists": content.lower().count("<ul") + content.lower().count("<ol"),
                "divs": content.lower().count("<div"),
                "links": content.lower().count("<a "),
                "images": content.lower().count("<img"),
            }

            # Estimate content type based on structure
            if elements["tables"] > 3:
                structure_type = "tabular_data"
                confidence = 0.6
            elif elements["lists"] > 5:
                structure_type = "list_based"
                confidence = 0.5
            elif elements["links"] > 20:
                structure_type = "navigation_heavy"
                confidence = 0.3
            else:
                structure_type = "simple_content"
                confidence = 0.4

            return {
                "structure_analysis": {
                    "type": structure_type,
                    "elements": elements,
                    "estimated_parishes": max(1, elements["links"] // 10),
                },
                "confidence": confidence,
                "method": "structure_analysis",
            }

        except Exception as e:
            logger.debug(f"🛡️ Structure analysis fallback failed: {e}")
            return {"structure_analysis": {}, "confidence": 0.1, "method": "structure_analysis_failed"}

    def _requests_fallback(self, context: ErrorContext, url: str = "", **kwargs) -> str:
        """Fallback web scraping using requests library."""
        import requests

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.debug(f"🛡️ Requests fallback failed for {url}: {e}")
            raise

    def _pattern_based_prediction_fallback(self, context: ErrorContext, domain: str = "", **kwargs) -> List:
        """Fallback URL prediction using basic patterns."""
        patterns = [
            "/reconciliation",
            "/confession",
            "/confessions",
            "/adoration",
            "/eucharistic-adoration",
            "/mass-times",
            "/mass-schedule",
            "/schedule",
            "/worship",
            "/liturgy",
            "/sacraments",
        ]

        urls = []
        for pattern in patterns:
            for scheme in ["https", "http"]:
                urls.append(f"{scheme}://{domain}{pattern}")

        return urls

    def _static_patterns_fallback(self, context: ErrorContext, **kwargs) -> List:
        """Final fallback with minimal static patterns."""
        domain = kwargs.get("domain", "example.com")
        return [f"https://{domain}/reconciliation", f"https://{domain}/adoration", f"https://{domain}/mass-times"]

    def _alternative_parser_fallback(self, context: ErrorContext, content: str = "", **kwargs) -> Dict:
        """Alternative content parsing method."""
        try:
            # Try different parsing approaches
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")

            # Extract basic information
            title = soup.find("title")
            title_text = title.get_text() if title else ""

            # Find potential schedule containers
            schedule_containers = soup.find_all(
                ["div", "section", "article"],
                class_=lambda x: x and any(term in str(x).lower() for term in ["schedule", "time", "mass", "service"]),
            )

            return {
                "title": title_text,
                "schedule_containers": len(schedule_containers),
                "content_length": len(content),
                "method": "alternative_parser",
            }

        except Exception as e:
            logger.debug(f"🛡️ Alternative parser fallback failed: {e}")
            return {"method": "alternative_parser_failed"}

    def _regex_extraction_fallback(self, context: ErrorContext, content: str = "", **kwargs) -> Dict:
        """Regex-based content extraction fallback."""
        try:
            # Time patterns for schedule extraction
            time_patterns = [
                r"\b(?:1[0-2]|[1-9]):(?:[0-5][0-9])\s*(?:AM|PM|am|pm)\b",
                r"\b(?:1[0-2]|[1-9])\s*(?:AM|PM|am|pm)\b",
                r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
            ]

            found_times = []
            for pattern in time_patterns:
                matches = re.findall(pattern, content)
                found_times.extend(matches)

            return {
                "extracted_times": found_times[:20],  # Limit results
                "time_count": len(found_times),
                "method": "regex_extraction",
            }

        except Exception as e:
            logger.debug(f"🛡️ Regex extraction fallback failed: {e}")
            return {"method": "regex_extraction_failed"}

    def _manual_patterns_fallback(self, context: ErrorContext, **kwargs) -> Dict:
        """Manual pattern-based extraction fallback."""
        return {
            "manual_patterns": [
                "Saturday evening Mass",
                "Sunday morning Mass",
                "Weekday Mass times",
                "Confession schedule",
                "Adoration hours",
            ],
            "method": "manual_patterns",
        }

    def _database_retry_fallback(self, context: ErrorContext, operation_func: Callable = None, **kwargs):
        """Database retry with exponential backoff."""
        if not operation_func:
            raise ValueError("Database operation function required")

        max_retries = 5
        base_delay = 0.5

        for attempt in range(max_retries):
            try:
                return operation_func(**kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise

                delay = base_delay * (2**attempt)
                logger.warning(f"🛡️ Database retry {attempt + 1}/{max_retries} after {delay}s: {e}")
                time.sleep(delay)

    def _cached_content_fallback(self, context: ErrorContext, url: str = "", **kwargs) -> Optional[str]:
        """Fallback to cached content if available."""
        # This would integrate with a caching system
        logger.info(f"🛡️ Attempting to retrieve cached content for {url}")
        return None  # Would return cached content if available

    def _read_only_database_fallback(self, context: ErrorContext, **kwargs):
        """Read-only database fallback for critical operations."""
        logger.warning("🛡️ Using read-only database fallback")
        return None  # Would implement read-only operations

    def _classify_error(self, error_message: str) -> str:
        """Classify error type based on message patterns."""
        error_msg_lower = error_message.lower()

        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_msg_lower):
                    return error_type

        return "unknown_error"

    def _should_retry(self, error_type: str, config: FallbackConfig) -> bool:
        """Determine if error type should be retried."""
        non_retryable_errors = [
            "http_client_error",  # 4xx errors usually don't benefit from retries
            "parsing_error",  # Data format issues won't resolve with retries
        ]

        return error_type not in non_retryable_errors

    def _determine_error_severity(self, error_message: str, config: FallbackConfig) -> ErrorSeverity:
        """Determine error severity based on message and configuration."""
        error_msg_lower = error_message.lower()

        # Critical errors
        if any(term in error_msg_lower for term in ["critical", "fatal", "database.*down"]):
            return ErrorSeverity.CRITICAL

        # High severity errors
        elif any(term in error_msg_lower for term in ["500", "server.*error", "timeout"]):
            return ErrorSeverity.HIGH

        # Medium severity errors
        elif any(term in error_msg_lower for term in ["404", "not.*found", "parsing"]):
            return ErrorSeverity.MEDIUM

        # Low severity errors
        else:
            return ErrorSeverity.LOW

    def _record_error(self, operation: str, error_type: str, error_message: str, context: ErrorContext):
        """Record error metrics for analysis."""
        self.metrics.total_errors += 1
        self.metrics.errors_by_type[error_type] += 1
        self.metrics.errors_by_operation[operation] += 1
        self.metrics.last_error_time = time.time()

        error_record = {
            "timestamp": time.time(),
            "operation": operation,
            "error_type": error_type,
            "error_message": error_message[:500],  # Truncate long messages
            "context": {"url": context.url, "parish_id": context.parish_id, "attempt_number": context.attempt_number},
        }

        self.metrics.recent_errors.append(error_record)

    def get_error_statistics(self) -> Dict:
        """Get comprehensive error handling statistics."""
        total_operations = self.metrics.successful_recoveries + self.metrics.failed_recoveries
        recovery_rate = 0
        if total_operations > 0:
            recovery_rate = self.metrics.successful_recoveries / total_operations

        return {
            "total_errors": self.metrics.total_errors,
            "successful_recoveries": self.metrics.successful_recoveries,
            "failed_recoveries": self.metrics.failed_recoveries,
            "recovery_rate": recovery_rate,
            "errors_by_type": dict(self.metrics.errors_by_type),
            "errors_by_operation": dict(self.metrics.errors_by_operation),
            "recent_error_count": len(self.metrics.recent_errors),
            "last_error_time": self.metrics.last_error_time,
        }

    def create_resilient_wrapper(self, operation: str, fallback_config: FallbackConfig = None):
        """Create a decorator for making functions resilient."""

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                context = ErrorContext(operation=operation)
                if fallback_config:
                    self.fallback_configs[operation] = fallback_config

                return self.handle_with_fallback(operation, lambda ctx, **kw: func(*args, **kwargs), context, **kwargs)

            return wrapper

        return decorator


# Global error handler instance
_global_error_handler = None


def get_error_handler() -> RobustErrorHandler:
    """Get global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = RobustErrorHandler()
    return _global_error_handler


def resilient(operation: str, **fallback_kwargs):
    """Decorator to make functions resilient with error handling."""
    config = FallbackConfig(**fallback_kwargs) if fallback_kwargs else None
    return get_error_handler().create_resilient_wrapper(operation, config)
