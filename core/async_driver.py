#!/usr/bin/env python3
"""
Async WebDriver Manager with concurrent request handling and intelligent rate limiting.
Provides high-performance parish extraction with connection pooling and queue management.
"""

import asyncio
import time
import threading
from collections import defaultdict, deque
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass
from urllib.parse import urlparse
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException
from core.logger import get_logger
from core.circuit_breaker import circuit_breaker, CircuitBreakerConfig, CircuitBreakerOpenError
import subprocess
import shutil

logger = get_logger(__name__)
_system_chromedriver_warning_logged = False


def _find_chrome_binary():
    """Find the Chrome binary path dynamically based on what's available."""
    # List of possible Chrome binary locations in order of preference
    chrome_binaries = [
        '/usr/bin/google-chrome',       # Standard Google Chrome on Linux
        '/usr/bin/chromium-browser',    # Chromium on Raspberry Pi/ARM64
        '/usr/bin/chromium',            # Alternative Chromium path
        '/opt/google/chrome/chrome',    # Alternative Google Chrome path
        'google-chrome',                # System PATH fallback
        'chromium-browser',             # System PATH fallback
        'chromium'                      # System PATH fallback
    ]

    for binary_path in chrome_binaries:
        try:
            if binary_path.startswith('/'):
                # Absolute path - check if file exists
                if shutil.which(binary_path) or subprocess.run(['test', '-f', binary_path],
                                                             capture_output=True).returncode == 0:
                    logger.debug(f"🔍 Found Chrome binary at: {binary_path}")
                    return binary_path
            else:
                # Check in system PATH
                found_path = shutil.which(binary_path)
                if found_path:
                    logger.debug(f"🔍 Found Chrome binary in PATH: {found_path}")
                    return found_path
        except Exception as e:
            logger.debug(f"Could not check {binary_path}: {e}")
            continue

    logger.warning("⚠️ No Chrome binary found, WebDriver will use default")
    return None


@dataclass
class RequestTask:
    """Represents an async request task"""
    url: str
    callback: Callable
    args: tuple = ()
    kwargs: dict = None
    priority: int = 1  # Lower number = higher priority
    retry_count: int = 0
    max_retries: int = 2
    domain: str = ""

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
        self.domain = urlparse(self.url).netloc


@dataclass
class RateLimitConfig:
    """Rate limiting configuration per domain"""
    requests_per_second: float = 2.0
    max_concurrent: int = 3
    burst_limit: int = 5
    cooldown_period: float = 1.0


class DomainRateLimiter:
    """Rate limiter for managing requests per domain"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.request_times = deque()
        self.active_requests = 0
        self.last_request_time = 0
        self.in_cooldown = False
        self._lock = threading.Lock()

    async def acquire(self) -> bool:
        """Acquire permission to make a request"""
        with self._lock:
            current_time = time.time()

            # Remove old request times (outside the 1-second window)
            while self.request_times and current_time - self.request_times[0] > 1.0:
                self.request_times.popleft()

            # Check if we're in cooldown
            if self.in_cooldown and current_time - self.last_request_time < self.config.cooldown_period:
                return False

            # Check concurrent limit
            if self.active_requests >= self.config.max_concurrent:
                return False

            # Check rate limit
            if len(self.request_times) >= self.config.requests_per_second:
                return False

            # Acquire the request
            self.request_times.append(current_time)
            self.active_requests += 1
            self.last_request_time = current_time
            self.in_cooldown = False

            return True

    def release(self, success: bool = True):
        """Release a request slot"""
        with self._lock:
            self.active_requests = max(0, self.active_requests - 1)
            if not success:
                self.in_cooldown = True

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        with self._lock:
            return {
                'active_requests': self.active_requests,
                'recent_requests': len(self.request_times),
                'in_cooldown': self.in_cooldown,
                'last_request_time': self.last_request_time
            }


class AsyncWebDriverPool:
    """
    Pool of WebDriver instances for concurrent request handling.
    Manages driver lifecycle, connection pooling, and intelligent rate limiting.
    """

    def __init__(self, pool_size: int = 4, default_timeout: int = 30):
        self.pool_size = pool_size
        self.default_timeout = default_timeout
        self.driver_pool = asyncio.Queue()
        self.domain_rate_limiters: Dict[str, DomainRateLimiter] = {}
        self.request_queue = asyncio.PriorityQueue()
        self.active_domains: Set[str] = set()
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'concurrent_requests': 0,
            'queue_size': 0,
            'pool_utilization': 0.0
        }
        self._initialized = False
        self._shutdown = False
        logger.info(f"🚀 Async WebDriver Pool initialized with {pool_size} drivers")

    async def initialize(self):
        """Initialize the driver pool"""
        if self._initialized:
            return

        logger.info("🔧 Initializing WebDriver pool...")

        # Create driver pool
        for i in range(self.pool_size):
            try:
                driver = await self._create_driver()
                await self.driver_pool.put(driver)
                logger.debug(f"✅ Driver {i+1}/{self.pool_size} created")
            except Exception as e:
                logger.error(f"❌ Failed to create driver {i+1}: {e}")

        self._initialized = True
        logger.info(f"🎯 WebDriver pool initialized with {self.driver_pool.qsize()} drivers")

        # Start background task processor
        asyncio.create_task(self._process_queue())

    async def _create_driver(self) -> webdriver.Chrome:
        """Create a new WebDriver instance"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")  # Disable JS for faster loading
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-extensions")

        # Run driver creation in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            driver = await loop.run_in_executor(
                executor,
                lambda: self._create_chrome_driver(chrome_options)
            )

        driver.set_page_load_timeout(self.default_timeout)
        return driver

    def _create_chrome_driver(self, chrome_options):
        """Create Chrome driver with ARM64 compatibility"""
        # Try system ChromeDriver first (for ARM64 compatibility)
        try:
            chrome_service = Service('/usr/bin/chromedriver')
            # Set Chrome binary path dynamically
            chrome_binary = _find_chrome_binary()
            if chrome_binary:
                chrome_options.binary_location = chrome_binary
            return webdriver.Chrome(service=chrome_service, options=chrome_options)
        except Exception as e:
            global _system_chromedriver_warning_logged
            if not _system_chromedriver_warning_logged:
                logger.warning(f"System ChromeDriver failed: {e}, falling back to ChromeDriverManager")
                _system_chromedriver_warning_logged = True
            return webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )

    def get_rate_limiter(self, domain: str) -> DomainRateLimiter:
        """Get or create rate limiter for domain"""
        if domain not in self.domain_rate_limiters:
            # Different rate limits for different types of sites
            if 'ecatholic' in domain.lower():
                config = RateLimitConfig(requests_per_second=1.5, max_concurrent=2)
            elif 'diocese' in domain.lower() or 'archdiocese' in domain.lower():
                config = RateLimitConfig(requests_per_second=2.0, max_concurrent=3)
            else:
                config = RateLimitConfig(requests_per_second=3.0, max_concurrent=4)

            self.domain_rate_limiters[domain] = DomainRateLimiter(config)
            logger.debug(f"📊 Created rate limiter for {domain}: {config.requests_per_second} req/s")

        return self.domain_rate_limiters[domain]

    async def submit_request(self, url: str, callback: Callable, *args,
                           priority: int = 1, max_retries: int = 2, **kwargs) -> Any:
        """Submit a request to the async queue"""
        task = RequestTask(
            url=url,
            callback=callback,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries
        )

        # Create future for result
        future = asyncio.get_event_loop().create_future()
        task.future = future

        await self.request_queue.put((priority, time.time(), task))
        self.stats['queue_size'] = self.request_queue.qsize()

        logger.debug(f"📝 Queued request: {url} (priority: {priority}, queue size: {self.stats['queue_size']})")
        # Directly await the result instead of returning a Task
        return await self._wait_for_result(future)

    async def _wait_for_result(self, future: asyncio.Future) -> Any:
        """Wait for a request result"""
        return await future

    async def _process_queue(self):
        """Background task processor"""
        while not self._shutdown:
            try:
                # Get next task from queue
                try:
                    priority, timestamp, task = await asyncio.wait_for(
                        self.request_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                self.stats['queue_size'] = self.request_queue.qsize()

                # Check rate limiting for this domain
                rate_limiter = self.get_rate_limiter(task.domain)

                # Wait for rate limit permission
                while not await asyncio.to_thread(rate_limiter.acquire):
                    await asyncio.sleep(0.1)

                # Process the request
                asyncio.create_task(self._execute_request(task, rate_limiter))

            except Exception as e:
                logger.error(f"❌ Error in queue processor: {e}")
                await asyncio.sleep(1)

    async def _execute_request(self, task: RequestTask, rate_limiter: DomainRateLimiter):
        """Execute a single request with circuit breaker protection"""
        driver = None
        success = False

        try:
            # Get driver from pool
            driver = await self.driver_pool.get()
            self.stats['concurrent_requests'] += 1
            self.stats['total_requests'] += 1

            logger.debug(f"🔄 Executing request: {task.url}")

            # Execute the callback with circuit breaker protection
            result = await self._protected_execute(driver, task)

            # Set result
            if hasattr(task, 'future'):
                task.future.set_result(result)

            success = True
            self.stats['successful_requests'] += 1

        except CircuitBreakerOpenError as e:
            logger.warning(f"🚫 Circuit breaker blocked request: {task.url}")
            if hasattr(task, 'future'):
                task.future.set_exception(e)

        except Exception as e:
            logger.error(f"❌ Request failed: {task.url} - {str(e)}")

            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                logger.info(f"🔄 Retrying request {task.retry_count}/{task.max_retries}: {task.url}")
                await self.request_queue.put((task.priority + 1, time.time(), task))
            else:
                self.stats['failed_requests'] += 1
                if hasattr(task, 'future'):
                    task.future.set_exception(e)

        finally:
            # Release rate limiter
            rate_limiter.release(success)

            # Return driver to pool
            if driver:
                await self.driver_pool.put(driver)
                self.stats['concurrent_requests'] -= 1

            # Update pool utilization
            if self.pool_size > 0:
                self.stats['pool_utilization'] = (
                    (self.pool_size - self.driver_pool.qsize()) / self.pool_size * 100
                )

    @circuit_breaker('async_webdriver_request', CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30,
        request_timeout=45,
        max_retries=1,
        retry_delay=2.0
    ))
    async def _protected_execute(self, driver, task: RequestTask):
        """Execute request with circuit breaker protection"""
        loop = asyncio.get_event_loop()

        # Execute callback in thread pool to avoid blocking
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                lambda: task.callback(driver, *task.args, **task.kwargs)
            )

        return result

    async def batch_requests(self, requests: List[Dict[str, Any]],
                           batch_size: int = 10) -> List[Any]:
        """Submit multiple requests as a batch"""
        logger.info(f"📦 Processing batch of {len(requests)} requests (batch size: {batch_size})")

        tasks = []
        for request in requests:
            task = await self.submit_request(
                url=request['url'],
                callback=request['callback'],
                *request.get('args', []),
                priority=request.get('priority', 1),
                max_retries=request.get('max_retries', 2),
                **request.get('kwargs', {})
            )
            tasks.append(task)

            # Batch processing - wait after each batch_size requests
            if len(tasks) % batch_size == 0:
                await asyncio.sleep(0.5)  # Small delay between batches

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"✅ Batch completed: {len([r for r in results if not isinstance(r, Exception)])} successful, "
                   f"{len([r for r in results if isinstance(r, Exception)])} failed")

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        rate_limiter_stats = {}
        for domain, limiter in self.domain_rate_limiters.items():
            rate_limiter_stats[domain] = limiter.get_stats()

        return {
            **self.stats,
            'pool_size': self.pool_size,
            'available_drivers': self.driver_pool.qsize(),
            'active_domains': len(self.active_domains),
            'rate_limiters': rate_limiter_stats
        }

    def log_stats(self):
        """Log comprehensive statistics"""
        stats = self.get_stats()
        success_rate = (stats['successful_requests'] / max(stats['total_requests'], 1)) * 100

        logger.info("📊 Async WebDriver Pool Statistics:")
        logger.info(f"  • Total Requests: {stats['total_requests']}")
        logger.info(f"  • Success Rate: {success_rate:.1f}%")
        logger.info(f"  • Queue Size: {stats['queue_size']}")
        logger.info(f"  • Pool Utilization: {stats['pool_utilization']:.1f}%")
        logger.info(f"  • Active Domains: {stats['active_domains']}")

        if stats['rate_limiters']:
            logger.info("  • Rate Limiters:")
            for domain, rl_stats in stats['rate_limiters'].items():
                logger.info(f"    - {domain}: {rl_stats['active_requests']} active, "
                           f"cooldown: {rl_stats['in_cooldown']}")

    async def shutdown(self):
        """Shutdown the driver pool"""
        logger.info("🛑 Shutting down Async WebDriver Pool...")
        self._shutdown = True

        # Close all drivers
        while not self.driver_pool.empty():
            driver = await self.driver_pool.get()
            try:
                driver.quit()
            except Exception as e:
                logger.warning(f"⚠️ Error closing driver: {e}")

        # Log final statistics
        self.log_stats()
        logger.info("✅ Async WebDriver Pool shutdown complete")


# Global async driver pool instance
_async_driver_pool = None


async def get_async_driver_pool(pool_size: int = 4) -> AsyncWebDriverPool:
    """Get or create the global async driver pool"""
    global _async_driver_pool

    if _async_driver_pool is None:
        _async_driver_pool = AsyncWebDriverPool(pool_size)
        await _async_driver_pool.initialize()

    return _async_driver_pool


async def shutdown_async_driver_pool():
    """Shutdown the global async driver pool"""
    global _async_driver_pool

    if _async_driver_pool:
        await _async_driver_pool.shutdown()
        _async_driver_pool = None
