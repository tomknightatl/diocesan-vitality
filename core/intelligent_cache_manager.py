#!/usr/bin/env python3
"""
Intelligent Cache Manager with TTL Management

This module implements a sophisticated caching system with Time-To-Live (TTL)
management, content-aware expiration, and intelligent invalidation to
dramatically reduce redundant requests and improve extraction performance.
"""

import time
import hashlib
import pickle
import threading
import gzip
import json
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
from enum import Enum
import os
from urllib.parse import urlparse

from core.logger import get_logger

logger = get_logger(__name__)


class CacheStrategy(Enum):
    """Cache invalidation strategies."""
    TIME_BASED = "time_based"
    CONTENT_AWARE = "content_aware"
    PROBABILISTIC = "probabilistic"
    ADAPTIVE = "adaptive"


class ContentType(Enum):
    """Content types for cache optimization."""
    HTML_PAGE = "html_page"
    API_RESPONSE = "api_response"
    SCHEDULE_DATA = "schedule_data"
    PARISH_DATA = "parish_data"
    IMAGE_DATA = "image_data"
    STATIC_CONTENT = "static_content"
    DATABASE_QUERY = "database_query"
    DNS_RESULT = "dns_result"
    URL_VERIFICATION = "url_verification"


@dataclass
class CacheEntry:
    """Represents a cached item with metadata."""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: float = 3600.0  # Default 1 hour
    content_type: ContentType = ContentType.HTML_PAGE
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    compression: bool = False
    size_bytes: int = 0

    @property
    def age(self) -> float:
        """Age of the cache entry in seconds."""
        return time.time() - self.created_at

    @property
    def expires_at(self) -> float:
        """Timestamp when the entry expires."""
        return self.created_at + self.ttl

    @property
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        return time.time() > self.expires_at

    @property
    def time_until_expiry(self) -> float:
        """Time in seconds until expiry."""
        return max(0, self.expires_at - time.time())


@dataclass
class CacheStatistics:
    """Cache performance statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    invalidations: int = 0
    total_size_bytes: int = 0
    avg_lookup_time: float = 0.0
    hit_rate_by_type: Dict[str, float] = field(default_factory=dict)


class IntelligentCacheManager:
    """
    Advanced caching system with intelligent TTL management and content-aware strategies.
    """

    def __init__(self, max_size: int = 1000, max_memory_mb: int = 500,
                 default_ttl: float = 3600.0, cache_dir: str = None):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cache_dir = cache_dir or "/tmp/usccb_cache"

        # Cache storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # Statistics
        self.stats = CacheStatistics()

        # TTL configurations by content type
        self.ttl_configs = {
            ContentType.HTML_PAGE: 1800.0,      # 30 minutes
            ContentType.API_RESPONSE: 300.0,     # 5 minutes
            ContentType.SCHEDULE_DATA: 7200.0,   # 2 hours
            ContentType.PARISH_DATA: 3600.0,     # 1 hour
            ContentType.IMAGE_DATA: 86400.0,     # 24 hours
            ContentType.STATIC_CONTENT: 86400.0, # 24 hours
            ContentType.DATABASE_QUERY: 600.0,   # 10 minutes
            ContentType.DNS_RESULT: 3600.0,      # 1 hour
            ContentType.URL_VERIFICATION: 1800.0 # 30 minutes
        }

        # Probabilistic refresh thresholds
        self.refresh_probability_configs = {
            ContentType.HTML_PAGE: 0.1,
            ContentType.SCHEDULE_DATA: 0.2,
            ContentType.PARISH_DATA: 0.15,
            ContentType.API_RESPONSE: 0.3
        }

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

        logger.info(f"💾 Intelligent Cache Manager initialized (max_size: {max_size}, max_memory: {max_memory_mb}MB)")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve value from cache with intelligent refresh logic.
        """
        start_time = time.time()

        with self._lock:
            self.stats.total_requests += 1

            if key not in self._cache:
                self.stats.cache_misses += 1
                return default

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired:
                self._remove_entry(key)
                self.stats.cache_misses += 1
                return default

            # Update access metadata
            entry.last_accessed = time.time()
            entry.access_count += 1

            # Move to end (most recently used)
            self._cache.move_to_end(key)

            # Probabilistic refresh for soon-to-expire items
            if self._should_probabilistic_refresh(entry):
                logger.debug(f"💾 Marking {key} for probabilistic refresh")
                entry.metadata['needs_refresh'] = True

            self.stats.cache_hits += 1
            self.stats.avg_lookup_time = self._update_avg_lookup_time(time.time() - start_time)

            logger.debug(f"💾 Cache hit for {key} (age: {entry.age:.0f}s, TTL: {entry.ttl:.0f}s)")

            # Decompress if needed
            if entry.compression and hasattr(entry.value, 'decode'):
                try:
                    return pickle.loads(gzip.decompress(entry.value))
                except:
                    return entry.value
            else:
                return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None,
            content_type: ContentType = ContentType.HTML_PAGE,
            metadata: Dict[str, Any] = None, compress: bool = None) -> bool:
        """
        Store value in cache with intelligent TTL and compression.
        """
        try:
            with self._lock:
                # Determine TTL
                effective_ttl = ttl or self._calculate_intelligent_ttl(key, content_type, value)

                # Determine compression
                if compress is None:
                    compress = self._should_compress(value, content_type)

                # Prepare value for storage
                stored_value = value
                if compress and not isinstance(value, bytes):
                    try:
                        serialized = pickle.dumps(value)
                        stored_value = gzip.compress(serialized)
                    except Exception as e:
                        logger.debug(f"💾 Compression failed for {key}: {e}")
                        compress = False

                # Calculate content hash for change detection
                content_hash = self._calculate_content_hash(value)

                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=stored_value,
                    created_at=time.time(),
                    last_accessed=time.time(),
                    ttl=effective_ttl,
                    content_type=content_type,
                    content_hash=content_hash,
                    metadata=metadata or {},
                    compression=compress,
                    size_bytes=self._calculate_size(stored_value)
                )

                # Check for content changes if updating existing entry
                if key in self._cache:
                    old_entry = self._cache[key]
                    if old_entry.content_hash == content_hash:
                        # Content unchanged, just update TTL and metadata
                        old_entry.ttl = effective_ttl
                        old_entry.last_accessed = time.time()
                        old_entry.metadata.update(metadata or {})
                        logger.debug(f"💾 Refreshed TTL for unchanged content: {key}")
                        return True

                # Add/update entry
                self._cache[key] = entry

                # Update statistics
                self.stats.total_size_bytes += entry.size_bytes

                # Maintain cache size limits
                self._enforce_size_limits()

                logger.debug(f"💾 Cached {key} (TTL: {effective_ttl:.0f}s, compressed: {compress})")
                return True

        except Exception as e:
            logger.error(f"💾 Error caching {key}: {e}")
            return False

    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry."""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                self.stats.invalidations += 1
                logger.debug(f"💾 Invalidated cache entry: {key}")
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all entries matching a pattern."""
        import re
        count = 0

        with self._lock:
            regex = re.compile(pattern)
            keys_to_remove = [key for key in self._cache.keys() if regex.search(key)]

            for key in keys_to_remove:
                self._remove_entry(key)
                count += 1

            self.stats.invalidations += count

        logger.info(f"💾 Invalidated {count} cache entries matching pattern: {pattern}")
        return count

    def invalidate_by_content_type(self, content_type: ContentType) -> int:
        """Invalidate all entries of a specific content type."""
        count = 0

        with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if entry.content_type == content_type
            ]

            for key in keys_to_remove:
                self._remove_entry(key)
                count += 1

            self.stats.invalidations += count

        logger.info(f"💾 Invalidated {count} entries of type: {content_type.value}")
        return count

    def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        count = 0
        current_time = time.time()

        with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if current_time > entry.expires_at
            ]

            for key in keys_to_remove:
                self._remove_entry(key)
                count += 1

        if count > 0:
            logger.info(f"💾 Cleaned up {count} expired cache entries")

        return count

    def get_cache_info(self, key: str) -> Optional[Dict]:
        """Get cache metadata for a specific key."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                return {
                    'key': key,
                    'created_at': entry.created_at,
                    'last_accessed': entry.last_accessed,
                    'access_count': entry.access_count,
                    'ttl': entry.ttl,
                    'age': entry.age,
                    'expires_in': entry.time_until_expiry,
                    'content_type': entry.content_type.value,
                    'size_bytes': entry.size_bytes,
                    'compressed': entry.compression,
                    'metadata': entry.metadata
                }
            return None

    def get_statistics(self) -> Dict:
        """Get comprehensive cache statistics."""
        with self._lock:
            hit_rate = 0
            if self.stats.total_requests > 0:
                hit_rate = self.stats.cache_hits / self.stats.total_requests

            # Calculate hit rates by content type
            type_stats = defaultdict(lambda: {'hits': 0, 'requests': 0})
            for entry in self._cache.values():
                type_name = entry.content_type.value
                if entry.access_count > 0:
                    type_stats[type_name]['requests'] += entry.access_count
                    # Estimate hits based on access pattern
                    type_stats[type_name]['hits'] += max(1, entry.access_count - 1)

            hit_rate_by_type = {}
            for type_name, stats in type_stats.items():
                if stats['requests'] > 0:
                    hit_rate_by_type[type_name] = stats['hits'] / stats['requests']

            return {
                'total_entries': len(self._cache),
                'total_requests': self.stats.total_requests,
                'cache_hits': self.stats.cache_hits,
                'cache_misses': self.stats.cache_misses,
                'hit_rate': hit_rate,
                'evictions': self.stats.evictions,
                'invalidations': self.stats.invalidations,
                'total_size_bytes': self.stats.total_size_bytes,
                'total_size_mb': self.stats.total_size_bytes / (1024 * 1024),
                'avg_lookup_time_ms': self.stats.avg_lookup_time * 1000,
                'hit_rate_by_type': hit_rate_by_type,
                'memory_usage_percent': (self.stats.total_size_bytes / self.max_memory_bytes) * 100
            }

    def _calculate_intelligent_ttl(self, key: str, content_type: ContentType, value: Any) -> float:
        """Calculate intelligent TTL based on content analysis."""
        base_ttl = self.ttl_configs.get(content_type, self.default_ttl)

        # Adjust TTL based on content characteristics
        multiplier = 1.0

        if content_type == ContentType.HTML_PAGE:
            # Analyze page content for schedule indicators
            if isinstance(value, str):
                content_lower = value.lower()

                # Pages with schedule data should be cached longer
                schedule_indicators = ['schedule', 'times', 'mass', 'confession', 'adoration']
                if any(indicator in content_lower for indicator in schedule_indicators):
                    multiplier = 2.0

                # Static pages can be cached longer
                if 'last-modified' in content_lower or 'static' in key:
                    multiplier = 3.0

                # Dynamic pages should expire faster
                elif any(indicator in content_lower for indicator in ['javascript', 'ajax', 'dynamic']):
                    multiplier = 0.5

        elif content_type == ContentType.SCHEDULE_DATA:
            # Schedule data from reliable sources can be cached longer
            if isinstance(value, dict) and value.get('confidence', 0) > 0.8:
                multiplier = 1.5

        elif content_type == ContentType.API_RESPONSE:
            # API responses vary by endpoint
            if 'parishes' in key or 'dioceses' in key:
                multiplier = 2.0  # Parish/diocese data is relatively stable

        # Domain-based adjustments
        parsed_key = urlparse(key) if key.startswith('http') else None
        if parsed_key:
            domain = parsed_key.netloc.lower()

            # Reliable domains can have longer TTLs
            reliable_domains = ['archatl.com', 'wordpress.com', 'squarespace.com']
            if any(reliable in domain for reliable in reliable_domains):
                multiplier *= 1.3

            # Dynamic domains should have shorter TTLs
            elif any(dynamic in domain for dynamic in ['wix.com', 'weebly.com']):
                multiplier *= 0.7

        return base_ttl * multiplier

    def _should_compress(self, value: Any, content_type: ContentType) -> bool:
        """Determine if value should be compressed."""
        # Don't compress small values
        size = self._calculate_size(value)
        if size < 1024:  # Less than 1KB
            return False

        # Compress text-heavy content
        if content_type in [ContentType.HTML_PAGE, ContentType.API_RESPONSE]:
            return True

        # Don't compress already compressed data
        if isinstance(value, bytes) and len(value) > 0:
            # Check for gzip magic bytes
            if value[:2] == b'\x1f\x8b':
                return False

        return size > 5120  # Compress if larger than 5KB

    def _should_probabilistic_refresh(self, entry: CacheEntry) -> bool:
        """Determine if entry should be probabilistically refreshed."""
        # Only consider entries that are close to expiring
        time_until_expiry = entry.time_until_expiry
        if time_until_expiry > entry.ttl * 0.3:  # More than 30% of TTL remaining
            return False

        # Calculate probability based on how close to expiry
        expiry_factor = 1 - (time_until_expiry / entry.ttl)
        base_probability = self.refresh_probability_configs.get(entry.content_type, 0.1)

        # Increase probability for frequently accessed items
        access_factor = min(entry.access_count / 10.0, 2.0)  # Max 2x multiplier

        final_probability = base_probability * expiry_factor * access_factor

        import random
        return random.random() < final_probability

    def _calculate_content_hash(self, value: Any) -> str:
        """Calculate hash for content change detection."""
        try:
            if isinstance(value, str):
                content = value.encode('utf-8')
            elif isinstance(value, bytes):
                content = value
            else:
                content = json.dumps(value, sort_keys=True, default=str).encode('utf-8')

            return hashlib.md5(content).hexdigest()
        except Exception:
            return str(hash(str(value)))

    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes."""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, bytes):
                return len(value)
            else:
                return len(pickle.dumps(value))
        except Exception:
            return len(str(value)) * 4  # Rough estimate

    def _enforce_size_limits(self):
        """Enforce cache size and memory limits."""
        # Memory limit check
        while (self.stats.total_size_bytes > self.max_memory_bytes or
               len(self._cache) > self.max_size):

            if not self._cache:
                break

            # Remove least recently used entry
            lru_key = next(iter(self._cache))
            self._remove_entry(lru_key)
            self.stats.evictions += 1

    def _remove_entry(self, key: str):
        """Remove entry and update statistics."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self.stats.total_size_bytes -= entry.size_bytes

    def _update_avg_lookup_time(self, lookup_time: float) -> float:
        """Update average lookup time with exponential moving average."""
        alpha = 0.1  # Smoothing factor
        if self.stats.avg_lookup_time == 0:
            return lookup_time
        else:
            return alpha * lookup_time + (1 - alpha) * self.stats.avg_lookup_time

    def create_url_cache_key(self, url: str, method: str = 'GET',
                           headers: Dict[str, str] = None, params: Dict = None) -> str:
        """Create consistent cache key for URL requests."""
        key_parts = [method.upper(), url]

        if params:
            sorted_params = sorted(params.items())
            key_parts.append(json.dumps(sorted_params, sort_keys=True))

        if headers:
            # Only include cache-relevant headers
            cache_headers = {k.lower(): v for k, v in headers.items()
                           if k.lower() in ['accept', 'accept-language', 'user-agent']}
            if cache_headers:
                key_parts.append(json.dumps(cache_headers, sort_keys=True))

        key = '|'.join(key_parts)
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    def cached_request(self, url: str, fetch_func: Callable, ttl: float = None,
                      content_type: ContentType = ContentType.HTML_PAGE, **kwargs) -> Any:
        """
        Cached wrapper for HTTP requests.

        Args:
            url: URL to fetch
            fetch_func: Function to fetch data if not cached
            ttl: Custom TTL for this request
            content_type: Content type for cache optimization
            **kwargs: Additional arguments for fetch_func

        Returns:
            Cached or freshly fetched data
        """
        cache_key = self.create_url_cache_key(url, kwargs.get('method', 'GET'))

        # Try cache first
        cached_result = self.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Fetch fresh data
        try:
            result = fetch_func(url, **kwargs)

            # Cache the result
            self.set(cache_key, result, ttl=ttl, content_type=content_type,
                    metadata={'url': url, 'method': kwargs.get('method', 'GET')})

            return result

        except Exception as e:
            logger.error(f"💾 Error fetching {url}: {e}")
            raise

    def save_to_disk(self, filepath: str = None) -> bool:
        """Save cache to disk for persistence."""
        try:
            if not filepath:
                filepath = os.path.join(self.cache_dir, 'cache_snapshot.pkl')

            with self._lock:
                cache_data = {
                    'entries': dict(self._cache),
                    'statistics': self.stats,
                    'timestamp': time.time()
                }

                with open(filepath, 'wb') as f:
                    pickle.dump(cache_data, f)

            logger.info(f"💾 Cache saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"💾 Error saving cache to disk: {e}")
            return False

    def load_from_disk(self, filepath: str = None) -> bool:
        """Load cache from disk."""
        try:
            if not filepath:
                filepath = os.path.join(self.cache_dir, 'cache_snapshot.pkl')

            if not os.path.exists(filepath):
                logger.info(f"💾 No cache file found at {filepath}")
                return False

            with open(filepath, 'rb') as f:
                cache_data = pickle.load(f)

            with self._lock:
                loaded_entries = cache_data.get('entries', {})
                current_time = time.time()

                # Filter out expired entries
                valid_entries = 0
                for key, entry in loaded_entries.items():
                    if current_time <= entry.expires_at:
                        self._cache[key] = entry
                        self.stats.total_size_bytes += entry.size_bytes
                        valid_entries += 1

                # Update statistics (but don't overwrite current stats completely)
                if 'statistics' in cache_data:
                    old_stats = cache_data['statistics']
                    # Only restore some statistics that make sense
                    self.stats.evictions += getattr(old_stats, 'evictions', 0)
                    self.stats.invalidations += getattr(old_stats, 'invalidations', 0)

            logger.info(f"💾 Loaded {valid_entries} cache entries from {filepath}")
            return True

        except Exception as e:
            logger.error(f"💾 Error loading cache from disk: {e}")
            return False


# Global cache manager instance
_global_cache_manager = None

def get_cache_manager(max_size: int = 1000, max_memory_mb: int = 500) -> IntelligentCacheManager:
    """Get global cache manager instance."""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = IntelligentCacheManager(max_size, max_memory_mb)
    return _global_cache_manager

def cached(ttl: float = None, content_type: ContentType = ContentType.HTML_PAGE,
          key_func: Callable = None):
    """Decorator for caching function results."""
    def decorator(func: Callable) -> Callable:
        cache = get_cache_manager()

        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5('|'.join(key_parts).encode()).hexdigest()

            # Try cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(cache_key, result, ttl=ttl, content_type=content_type)

            return result

        return wrapper
    return decorator