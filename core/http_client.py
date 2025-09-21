#!/usr/bin/env python3
"""
HTTP Client with connection pooling for improved performance.
Provides reusable session management for all web scraping operations.
"""

import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from core.logger import get_logger

logger = get_logger(__name__)


class HTTPClientPool:
    """
    HTTP client with connection pooling and retry logic.
    Optimized for web scraping operations with proper resource management.
    """

    def __init__(
        self,
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        timeout: int = 20,
    ):
        """
        Initialize HTTP client with connection pooling.

        Args:
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections to save in pool
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for retries
            timeout: Default request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        # Configure connection pooling
        adapter = HTTPAdapter(pool_connections=pool_connections, pool_maxsize=pool_maxsize, max_retries=retry_strategy)

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers for web scraping
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/58.0.3029.110 Safari/537.3"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
        )

        logger.info(f"🔗 HTTP client initialized with pool_size={pool_maxsize}, max_retries={max_retries}")

    def get(
        self, url: str, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None, **kwargs
    ) -> requests.Response:
        """
        GET request with connection pooling and retry logic.

        Args:
            url: URL to fetch
            headers: Optional additional headers
            timeout: Optional timeout override
            **kwargs: Additional requests arguments

        Returns:
            requests.Response object

        Raises:
            requests.RequestException: On request failure after retries
        """
        request_timeout = timeout or self.timeout
        request_headers = self.session.headers.copy()

        if headers:
            request_headers.update(headers)

        try:
            logger.debug(f"🌐 GET request: {url}")
            response = self.session.get(url, headers=request_headers, timeout=request_timeout, **kwargs)
            response.raise_for_status()
            logger.debug(f"✅ GET success: {url} (status: {response.status_code})")
            return response

        except requests.RequestException as e:
            logger.error(f"❌ GET failed: {url} - {str(e)}")
            raise

    def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> requests.Response:
        """
        POST request with connection pooling.

        Args:
            url: URL to post to
            data: Form data
            json: JSON data
            headers: Optional additional headers
            timeout: Optional timeout override
            **kwargs: Additional requests arguments

        Returns:
            requests.Response object
        """
        request_timeout = timeout or self.timeout
        request_headers = self.session.headers.copy()

        if headers:
            request_headers.update(headers)

        try:
            logger.debug(f"📤 POST request: {url}")
            response = self.session.post(url, data=data, json=json, headers=request_headers, timeout=request_timeout, **kwargs)
            response.raise_for_status()
            logger.debug(f"✅ POST success: {url} (status: {response.status_code})")
            return response

        except requests.RequestException as e:
            logger.error(f"❌ POST failed: {url} - {str(e)}")
            raise

    def close(self):
        """Close the session and cleanup resources."""
        if self.session:
            self.session.close()
            logger.debug("🔒 HTTP session closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global HTTP client instance
_http_client = None


def get_http_client() -> HTTPClientPool:
    """
    Get or create the global HTTP client instance.
    Provides connection pooling for all HTTP operations.

    Returns:
        HTTPClientPool: Configured HTTP client with connection pooling
    """
    global _http_client

    if _http_client is None:
        _http_client = HTTPClientPool()

    return _http_client


def cleanup_http_client():
    """Clean up the global HTTP client."""
    global _http_client

    if _http_client is not None:
        _http_client.close()
        _http_client = None
        logger.debug("🧹 Global HTTP client cleaned up")
