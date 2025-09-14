#!/usr/bin/env python3
"""
Dynamic Timeout Optimization System

This module implements intelligent timeout management that adapts based on
site response patterns, complexity indicators, and historical performance
to optimize extraction efficiency and reduce unnecessary waiting.
"""

import time
import statistics
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from urllib.parse import urlparse
import threading
import json

from supabase import Client
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ResponseMetrics:
    """Tracks response time metrics for a domain."""
    domain: str
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    success_times: deque = field(default_factory=lambda: deque(maxlen=50))
    failure_times: deque = field(default_factory=lambda: deque(maxlen=50))
    last_updated: float = field(default_factory=time.time)
    complexity_indicators: Dict[str, float] = field(default_factory=dict)

    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 10.0
        return statistics.mean(self.response_times)

    @property
    def p95_response_time(self) -> float:
        if len(self.response_times) < 5:
            return self.avg_response_time * 1.5
        return statistics.quantiles(self.response_times, n=20)[18]  # 95th percentile

    @property
    def success_rate(self) -> float:
        total = len(self.success_times) + len(self.failure_times)
        if total == 0:
            return 0.5
        return len(self.success_times) / total

    @property
    def complexity_score(self) -> float:
        """Calculate overall complexity score from indicators."""
        if not self.complexity_indicators:
            return 1.0

        weights = {
            'js_heavy': 2.0,
            'spa_detected': 2.5,
            'ajax_requests': 1.8,
            'dynamic_content': 2.2,
            'cdn_usage': 0.8,
            'image_heavy': 1.3,
            'iframe_count': 1.5,
            'redirect_count': 1.4
        }

        weighted_score = 0
        total_weight = 0

        for indicator, value in self.complexity_indicators.items():
            if indicator in weights:
                weighted_score += value * weights[indicator]
                total_weight += weights[indicator]

        if total_weight == 0:
            return 1.0

        return weighted_score / total_weight


@dataclass
class TimeoutStrategy:
    """Defines timeout parameters for different scenarios."""
    name: str
    base_timeout: float
    max_timeout: float
    retry_multiplier: float = 1.5
    adaptive_factor: float = 1.2
    description: str = ""


class AdaptiveTimeoutManager:
    """
    Intelligent timeout manager that learns from site behavior patterns
    to optimize timeout values dynamically.
    """

    def __init__(self, supabase: Client = None):
        self.supabase = supabase
        self.logger = logger

        # Response tracking
        self.domain_metrics: Dict[str, ResponseMetrics] = {}
        self.global_stats = {
            'total_requests': 0,
            'total_timeouts': 0,
            'avg_response_time': 10.0
        }

        # Thread safety
        self._lock = threading.RLock()

        # Predefined strategies
        self.strategies = {
            'lightning': TimeoutStrategy(
                name='lightning',
                base_timeout=5.0,
                max_timeout=15.0,
                retry_multiplier=1.2,
                adaptive_factor=1.1,
                description='Ultra-fast sites with CDN/caching'
            ),
            'fast': TimeoutStrategy(
                name='fast',
                base_timeout=10.0,
                max_timeout=25.0,
                retry_multiplier=1.3,
                adaptive_factor=1.15,
                description='Standard static sites'
            ),
            'moderate': TimeoutStrategy(
                name='moderate',
                base_timeout=20.0,
                max_timeout=45.0,
                retry_multiplier=1.4,
                adaptive_factor=1.2,
                description='Dynamic sites with some JS'
            ),
            'complex': TimeoutStrategy(
                name='complex',
                base_timeout=35.0,
                max_timeout=75.0,
                retry_multiplier=1.6,
                adaptive_factor=1.3,
                description='Heavy JS/SPA applications'
            ),
            'patient': TimeoutStrategy(
                name='patient',
                base_timeout=60.0,
                max_timeout=120.0,
                retry_multiplier=1.8,
                adaptive_factor=1.4,
                description='Very slow or problematic sites'
            )
        }

        # Domain classifications
        self.domain_classifications: Dict[str, str] = {
            # Fast domains
            'wordpress.com': 'fast',
            'squarespace.com': 'fast',
            'archatl.com': 'fast',
            'cloudflare.net': 'lightning',
            'github.io': 'lightning',

            # Moderate domains
            'wix.com': 'moderate',
            'weebly.com': 'moderate',
            'godaddy.com': 'moderate',

            # Complex domains
            'shopify.com': 'complex',
            'hubspot.com': 'complex',
            'salesforce.com': 'complex'
        }

        logger.info("⏱️ Adaptive Timeout Manager initialized")

    def get_optimal_timeout(self, url: str, operation_type: str = 'page_load',
                           retry_count: int = 0, context: Dict = None) -> float:
        """
        Calculate optimal timeout for a URL based on historical data and complexity.

        Args:
            url: Target URL
            operation_type: Type of operation ('page_load', 'element_wait', 'api_request')
            retry_count: Current retry attempt (0 for first attempt)
            context: Additional context information

        Returns:
            Optimized timeout value in seconds
        """
        try:
            with self._lock:
                domain = urlparse(url).netloc.lower()

                # Get or create domain metrics
                if domain not in self.domain_metrics:
                    self.domain_metrics[domain] = ResponseMetrics(domain=domain)

                metrics = self.domain_metrics[domain]

                # Determine base strategy
                strategy = self._determine_strategy(domain, metrics, context)

                # Calculate base timeout
                base_timeout = self._calculate_base_timeout(strategy, metrics, operation_type)

                # Apply adaptive adjustments
                adapted_timeout = self._apply_adaptive_adjustments(
                    base_timeout, metrics, retry_count, strategy
                )

                # Apply operation-specific modifiers
                final_timeout = self._apply_operation_modifiers(
                    adapted_timeout, operation_type, context
                )

                # Ensure within bounds
                final_timeout = max(3.0, min(final_timeout, strategy.max_timeout))

                self.logger.debug(
                    f"⏱️ Timeout for {domain}: {final_timeout:.1f}s "
                    f"(strategy: {strategy.name}, retry: {retry_count})"
                )

                return final_timeout

        except Exception as e:
            self.logger.error(f"⏱️ Error calculating timeout for {url}: {e}")
            return 30.0  # Safe fallback

    def _determine_strategy(self, domain: str, metrics: ResponseMetrics,
                           context: Dict = None) -> TimeoutStrategy:
        """Determine the best timeout strategy for a domain."""

        # Check explicit domain classifications
        for pattern, strategy_name in self.domain_classifications.items():
            if pattern in domain:
                return self.strategies[strategy_name]

        # Use metrics-based classification
        if metrics.response_times:
            avg_time = metrics.avg_response_time
            complexity = metrics.complexity_score
            success_rate = metrics.success_rate

            # Fast sites
            if avg_time < 3.0 and complexity < 1.2 and success_rate > 0.9:
                return self.strategies['lightning']
            elif avg_time < 8.0 and complexity < 1.5:
                return self.strategies['fast']

            # Slow or complex sites
            elif avg_time > 25.0 or complexity > 2.5 or success_rate < 0.6:
                return self.strategies['patient']
            elif avg_time > 15.0 or complexity > 2.0:
                return self.strategies['complex']

        # Check context hints
        if context:
            if context.get('detected_spa', False) or context.get('js_heavy', False):
                return self.strategies['complex']
            if context.get('cdn_detected', False):
                return self.strategies['fast']

        # Default to moderate
        return self.strategies['moderate']

    def _calculate_base_timeout(self, strategy: TimeoutStrategy,
                               metrics: ResponseMetrics, operation_type: str) -> float:
        """Calculate base timeout using strategy and historical data."""

        base = strategy.base_timeout

        # Adjust based on historical performance
        if metrics.response_times:
            # Use P95 response time as baseline with safety margin
            historical_timeout = metrics.p95_response_time * 1.5

            # Weight historical data with strategy base
            weight = min(len(metrics.response_times) / 20.0, 0.7)  # Max 70% weight on history
            base = base * (1 - weight) + historical_timeout * weight

        # Operation-specific base adjustments
        operation_multipliers = {
            'page_load': 1.0,
            'element_wait': 0.7,
            'api_request': 0.8,
            'form_submit': 1.2,
            'file_download': 2.0,
            'ajax_wait': 0.6
        }

        multiplier = operation_multipliers.get(operation_type, 1.0)
        return base * multiplier

    def _apply_adaptive_adjustments(self, base_timeout: float, metrics: ResponseMetrics,
                                   retry_count: int, strategy: TimeoutStrategy) -> float:
        """Apply adaptive adjustments based on recent performance."""

        timeout = base_timeout

        # Retry escalation
        if retry_count > 0:
            timeout *= (strategy.retry_multiplier ** retry_count)

        # Recent performance adjustments
        if len(metrics.response_times) >= 5:
            recent_times = list(metrics.response_times)[-5:]
            recent_avg = statistics.mean(recent_times)

            # If recent responses are much slower/faster, adjust
            if recent_avg > metrics.avg_response_time * 1.5:
                timeout *= 1.3  # Increase for recent slowdown
            elif recent_avg < metrics.avg_response_time * 0.7:
                timeout *= 0.9  # Decrease for recent speedup

        # Success rate adjustments
        if metrics.success_rate < 0.5:
            timeout *= 1.4  # More patient with unreliable sites
        elif metrics.success_rate > 0.95:
            timeout *= 0.9  # More aggressive with reliable sites

        # Complexity adjustments
        complexity_factor = min(metrics.complexity_score, 3.0)
        timeout *= (0.8 + 0.2 * complexity_factor)  # Scale from 0.8x to 1.4x

        return timeout

    def _apply_operation_modifiers(self, timeout: float, operation_type: str,
                                  context: Dict = None) -> float:
        """Apply final operation-specific modifiers."""

        if not context:
            return timeout

        # Content-based modifiers
        if context.get('content_size_mb', 0) > 5:
            timeout *= 1.3  # Larger content needs more time

        if context.get('image_count', 0) > 20:
            timeout *= 1.2  # Image-heavy pages

        if context.get('external_resources', 0) > 10:
            timeout *= 1.15  # Many external dependencies

        # Network condition modifiers
        if context.get('network_quality') == 'poor':
            timeout *= 1.5
        elif context.get('network_quality') == 'excellent':
            timeout *= 0.8

        return timeout

    def record_response(self, url: str, response_time: float, success: bool,
                       complexity_indicators: Dict[str, float] = None,
                       timeout_occurred: bool = False):
        """Record response metrics for future timeout optimization."""
        try:
            with self._lock:
                domain = urlparse(url).netloc.lower()

                if domain not in self.domain_metrics:
                    self.domain_metrics[domain] = ResponseMetrics(domain=domain)

                metrics = self.domain_metrics[domain]

                # Record response time
                metrics.response_times.append(response_time)

                # Record success/failure timing
                if success:
                    metrics.success_times.append(response_time)
                else:
                    metrics.failure_times.append(response_time)

                # Update complexity indicators
                if complexity_indicators:
                    for key, value in complexity_indicators.items():
                        metrics.complexity_indicators[key] = value

                metrics.last_updated = time.time()

                # Update global stats
                self.global_stats['total_requests'] += 1
                if timeout_occurred:
                    self.global_stats['total_timeouts'] += 1

                # Update global average (rolling)
                old_avg = self.global_stats['avg_response_time']
                count = self.global_stats['total_requests']
                self.global_stats['avg_response_time'] = (
                    (old_avg * (count - 1) + response_time) / count
                )

        except Exception as e:
            self.logger.error(f"⏱️ Error recording response for {url}: {e}")

    def analyze_complexity_indicators(self, page_content: str = None,
                                     response_headers: Dict = None,
                                     network_logs: List = None) -> Dict[str, float]:
        """Analyze page complexity indicators for timeout optimization."""
        indicators = {}

        try:
            # Content analysis
            if page_content:
                content = page_content.lower()

                # JavaScript detection
                js_count = content.count('<script') + content.count('javascript:')
                indicators['js_heavy'] = min(js_count / 10.0, 3.0)

                # SPA detection
                spa_indicators = ['angular', 'react', 'vue', 'backbone', 'ember']
                spa_score = sum(1 for indicator in spa_indicators if indicator in content)
                indicators['spa_detected'] = min(spa_score, 1.0)

                # Dynamic content indicators
                dynamic_terms = ['ajax', 'fetch(', 'xmlhttprequest', 'async']
                dynamic_score = sum(1 for term in dynamic_terms if term in content)
                indicators['dynamic_content'] = min(dynamic_score / 3.0, 2.0)

                # Image analysis
                img_count = content.count('<img')
                indicators['image_heavy'] = min(img_count / 20.0, 2.0)

                # Iframe analysis
                iframe_count = content.count('<iframe')
                indicators['iframe_count'] = min(iframe_count / 3.0, 2.0)

            # Response header analysis
            if response_headers:
                headers = {k.lower(): v for k, v in response_headers.items()}

                # CDN detection
                cdn_headers = ['cf-ray', 'x-amz-cf-id', 'x-cache', 'x-served-by']
                if any(header in headers for header in cdn_headers):
                    indicators['cdn_usage'] = 0.5  # CDNs typically speed things up

                # Content size
                content_length = headers.get('content-length')
                if content_length and content_length.isdigit():
                    size_mb = int(content_length) / (1024 * 1024)
                    indicators['content_size'] = min(size_mb / 5.0, 2.0)

            # Network logs analysis
            if network_logs:
                ajax_requests = len([log for log in network_logs
                                   if log.get('type') == 'xhr' or log.get('type') == 'fetch'])
                indicators['ajax_requests'] = min(ajax_requests / 10.0, 2.0)

                redirect_count = len([log for log in network_logs
                                    if str(log.get('status', 0)).startswith('3')])
                indicators['redirect_count'] = min(redirect_count / 3.0, 2.0)

        except Exception as e:
            self.logger.debug(f"⏱️ Error analyzing complexity indicators: {e}")

        return indicators

    def get_domain_stats(self, domain: str) -> Dict:
        """Get performance statistics for a domain."""
        with self._lock:
            if domain not in self.domain_metrics:
                return {}

            metrics = self.domain_metrics[domain]
            return {
                'domain': domain,
                'avg_response_time': metrics.avg_response_time,
                'p95_response_time': metrics.p95_response_time,
                'success_rate': metrics.success_rate,
                'complexity_score': metrics.complexity_score,
                'total_requests': len(metrics.response_times),
                'last_updated': metrics.last_updated,
                'complexity_indicators': dict(metrics.complexity_indicators)
            }

    def get_global_stats(self) -> Dict:
        """Get global timeout management statistics."""
        with self._lock:
            timeout_rate = 0
            if self.global_stats['total_requests'] > 0:
                timeout_rate = (self.global_stats['total_timeouts'] /
                               self.global_stats['total_requests'])

            return {
                'total_requests': self.global_stats['total_requests'],
                'total_timeouts': self.global_stats['total_timeouts'],
                'timeout_rate': timeout_rate,
                'avg_response_time': self.global_stats['avg_response_time'],
                'domains_tracked': len(self.domain_metrics),
                'strategies_available': list(self.strategies.keys())
            }

    def optimize_strategy_thresholds(self):
        """Optimize strategy classification thresholds based on collected data."""
        try:
            with self._lock:
                if len(self.domain_metrics) < 10:
                    return  # Need more data

                # Analyze performance by current strategy assignments
                strategy_performance = defaultdict(list)

                for domain, metrics in self.domain_metrics.items():
                    if len(metrics.response_times) >= 5:
                        current_strategy = self._determine_strategy(domain, metrics)
                        strategy_performance[current_strategy.name].append({
                            'avg_time': metrics.avg_response_time,
                            'success_rate': metrics.success_rate,
                            'complexity': metrics.complexity_score
                        })

                # Log current performance by strategy
                for strategy_name, performances in strategy_performance.items():
                    if performances:
                        avg_time = statistics.mean([p['avg_time'] for p in performances])
                        avg_success = statistics.mean([p['success_rate'] for p in performances])

                        self.logger.info(
                            f"⏱️ Strategy '{strategy_name}': "
                            f"avg_time={avg_time:.1f}s, success_rate={avg_success:.2f}"
                        )

        except Exception as e:
            self.logger.error(f"⏱️ Error optimizing strategy thresholds: {e}")

    def save_metrics(self, filepath: str):
        """Save timeout metrics to file."""
        try:
            with self._lock:
                data = {
                    'domain_metrics': {
                        domain: {
                            'domain': metrics.domain,
                            'response_times': list(metrics.response_times),
                            'success_times': list(metrics.success_times),
                            'failure_times': list(metrics.failure_times),
                            'complexity_indicators': dict(metrics.complexity_indicators),
                            'last_updated': metrics.last_updated
                        }
                        for domain, metrics in self.domain_metrics.items()
                    },
                    'global_stats': self.global_stats,
                    'timestamp': time.time()
                }

                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)

                self.logger.info(f"⏱️ Metrics saved to {filepath}")

        except Exception as e:
            self.logger.error(f"⏱️ Error saving metrics: {e}")

    def load_metrics(self, filepath: str):
        """Load timeout metrics from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            with self._lock:
                # Restore domain metrics
                for domain, metric_data in data.get('domain_metrics', {}).items():
                    metrics = ResponseMetrics(domain=domain)
                    metrics.response_times.extend(metric_data.get('response_times', []))
                    metrics.success_times.extend(metric_data.get('success_times', []))
                    metrics.failure_times.extend(metric_data.get('failure_times', []))
                    metrics.complexity_indicators.update(
                        metric_data.get('complexity_indicators', {})
                    )
                    metrics.last_updated = metric_data.get('last_updated', time.time())

                    self.domain_metrics[domain] = metrics

                # Restore global stats
                self.global_stats.update(data.get('global_stats', {}))

            self.logger.info(f"⏱️ Metrics loaded from {filepath}")

        except Exception as e:
            self.logger.error(f"⏱️ Error loading metrics: {e}")


def get_adaptive_timeout_manager() -> AdaptiveTimeoutManager:
    """Factory function to create adaptive timeout manager."""
    return AdaptiveTimeoutManager()