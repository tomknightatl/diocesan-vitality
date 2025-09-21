#!/usr/bin/env python3
"""
Controlled Parallelization Manager for Schedule Extraction

This module implements intelligent parallel processing with resource management,
rate limiting, and adaptive concurrency control to maximize extraction
throughput while respecting server limits and maintaining system stability.
"""

import asyncio
import logging
import random
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from queue import PriorityQueue, Queue
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

from core.adaptive_timeout_manager import get_adaptive_timeout_manager
from core.intelligent_cache_manager import get_cache_manager
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractionTask:
    """Represents a single extraction task."""

    task_id: str
    url: str
    parish_id: Optional[int]
    diocese_id: Optional[int]
    priority: float = 0.0
    max_retries: int = 3
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    domain: str = field(init=False)

    def __post_init__(self):
        self.domain = urlparse(self.url).netloc.lower()

    def __lt__(self, other):
        """For priority queue ordering (higher priority first)."""
        return self.priority > other.priority


@dataclass
class DomainLimits:
    """Rate limiting configuration for a domain."""

    domain: str
    max_concurrent: int = 2
    requests_per_second: float = 0.5
    burst_limit: int = 5
    cooldown_period: float = 60.0
    last_request_time: float = 0.0
    request_times: deque = field(default_factory=lambda: deque(maxlen=100))
    active_requests: int = 0
    blocked_until: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0

    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    @property
    def current_rps(self) -> float:
        """Calculate current requests per second."""
        now = time.time()
        recent_requests = [t for t in self.request_times if now - t <= 60.0]
        return len(recent_requests) / 60.0

    def can_make_request(self) -> bool:
        """Check if a new request can be made."""
        now = time.time()

        # Check if domain is in cooldown
        if now < self.blocked_until:
            return False

        # Check concurrent limit
        if self.active_requests >= self.max_concurrent:
            return False

        # Check rate limit
        if self.current_rps >= self.requests_per_second:
            return False

        return True

    def register_request(self, success: bool = True):
        """Register a request attempt."""
        now = time.time()
        self.last_request_time = now
        self.request_times.append(now)
        self.total_requests += 1

        if not success:
            self.failed_requests += 1

        # Apply cooldown if failure rate is high
        if self.failure_rate > 0.5 and self.total_requests > 5:
            self.blocked_until = now + self.cooldown_period
            logger.warning(f"⚡ Domain {self.domain} in cooldown due to high failure rate")


@dataclass
class WorkerStats:
    """Statistics for a worker thread."""

    worker_id: int
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_time: float = 0.0
    last_active: float = field(default_factory=time.time)
    current_task: Optional[str] = None

    @property
    def success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return self.tasks_completed / total

    @property
    def avg_task_time(self) -> float:
        if self.tasks_completed == 0:
            return 0.0
        return self.total_time / self.tasks_completed


class ParallelExtractionManager:
    """
    Intelligent parallel extraction manager with adaptive concurrency control.
    """

    def __init__(self, max_workers: int = 5, adaptive_scaling: bool = True):
        self.max_workers = max_workers
        self.adaptive_scaling = adaptive_scaling

        # Task management
        self.task_queue: PriorityQueue = PriorityQueue()
        self.completed_tasks: Dict[str, Any] = {}
        self.failed_tasks: Dict[str, ExtractionTask] = {}

        # Worker management
        self.executor: Optional[ThreadPoolExecutor] = None
        self.active_workers = 0
        self.worker_stats: Dict[int, WorkerStats] = {}

        # Domain rate limiting
        self.domain_limits: Dict[str, DomainLimits] = {}
        self.default_domain_config = DomainLimits(domain="default")

        # Global statistics
        self.global_stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "avg_completion_time": 0.0,
            "peak_concurrency": 0,
            "start_time": time.time(),
        }

        # Integration with other managers
        self.timeout_manager = get_adaptive_timeout_manager()
        self.cache_manager = get_cache_manager()

        # Thread safety
        self._lock = threading.RLock()
        self._shutdown = False

        logger.info(f"⚡ Parallel Extraction Manager initialized (max_workers: {max_workers})")

    def configure_domain_limits(self, domain: str, max_concurrent: int = 2, requests_per_second: float = 0.5, **kwargs):
        """Configure rate limiting for a specific domain."""
        with self._lock:
            self.domain_limits[domain] = DomainLimits(
                domain=domain, max_concurrent=max_concurrent, requests_per_second=requests_per_second, **kwargs
            )
        logger.info(f"⚡ Configured limits for {domain}: {max_concurrent} concurrent, {requests_per_second} RPS")

    def add_task(self, task: ExtractionTask) -> bool:
        """Add a task to the extraction queue."""
        try:
            with self._lock:
                if self._shutdown:
                    return False

                self.task_queue.put(task)
                self.global_stats["total_tasks"] += 1

            logger.debug(f"⚡ Added task {task.task_id} for {task.url}")
            return True

        except Exception as e:
            logger.error(f"⚡ Error adding task {task.task_id}: {e}")
            return False

    def add_batch_tasks(self, tasks: List[ExtractionTask]) -> int:
        """Add multiple tasks efficiently."""
        added_count = 0

        with self._lock:
            if self._shutdown:
                return 0

            for task in tasks:
                try:
                    self.task_queue.put(task)
                    self.global_stats["total_tasks"] += 1
                    added_count += 1
                except Exception as e:
                    logger.error(f"⚡ Error adding task {task.task_id}: {e}")

        logger.info(f"⚡ Added {added_count}/{len(tasks)} tasks to extraction queue")
        return added_count

    def extract_parallel(
        self, extraction_func: Callable, max_concurrent_domains: int = 10, timeout_per_task: float = 120.0
    ) -> Dict[str, Any]:
        """
        Execute parallel extraction with intelligent resource management.

        Args:
            extraction_func: Function to call for each task
            max_concurrent_domains: Maximum domains to process simultaneously
            timeout_per_task: Timeout for individual tasks

        Returns:
            Dictionary with extraction results and statistics
        """
        if self._shutdown:
            raise RuntimeError("Manager is shutdown")

        start_time = time.time()
        logger.info(f"⚡ Starting parallel extraction with {self.max_workers} workers")

        try:
            # Calculate optimal worker count
            optimal_workers = self._calculate_optimal_workers()
            actual_workers = min(optimal_workers, self.max_workers)

            logger.info(f"⚡ Using {actual_workers} workers (optimal: {optimal_workers})")

            # Start thread pool
            with ThreadPoolExecutor(max_workers=actual_workers, thread_name_prefix="ExtractWorker") as executor:
                self.executor = executor

                # Submit worker tasks
                futures = []
                for worker_id in range(actual_workers):
                    future = executor.submit(self._worker_loop, worker_id, extraction_func, timeout_per_task)
                    futures.append(future)

                # Monitor progress
                self._monitor_progress(futures, start_time)

                # Wait for completion with timeout
                total_timeout = timeout_per_task * 2  # Allow extra time for management
                for future in as_completed(futures, timeout=total_timeout):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"⚡ Worker thread error: {e}")

        except Exception as e:
            logger.error(f"⚡ Error in parallel extraction: {e}")
        finally:
            self.executor = None

        # Compile results
        duration = time.time() - start_time
        results = self._compile_results(duration)

        logger.info(
            f"⚡ Parallel extraction completed in {duration:.1f}s: "
            f"{results['completed']} completed, {results['failed']} failed"
        )

        return results

    def _worker_loop(self, worker_id: int, extraction_func: Callable, task_timeout: float):
        """Main worker loop for processing tasks."""
        stats = WorkerStats(worker_id)
        self.worker_stats[worker_id] = stats

        logger.info(f"⚡ Worker {worker_id} started")

        try:
            while not self._shutdown:
                try:
                    # Get next task with timeout
                    task = self.task_queue.get(timeout=5.0)
                    if task is None:  # Shutdown signal
                        break

                    stats.current_task = task.task_id
                    task_start_time = time.time()

                    # Check domain limits
                    domain_limits = self._get_domain_limits(task.domain)
                    if not domain_limits.can_make_request():
                        # Requeue task with lower priority
                        task.priority -= 0.1
                        self.task_queue.put(task)
                        time.sleep(random.uniform(1.0, 3.0))  # Backoff
                        continue

                    # Update domain tracking
                    with self._lock:
                        domain_limits.active_requests += 1
                        self.active_workers = max(
                            self.active_workers, sum(limits.active_requests for limits in self.domain_limits.values())
                        )
                        self.global_stats["peak_concurrency"] = max(self.global_stats["peak_concurrency"], self.active_workers)

                    success = False
                    try:
                        # Execute extraction with timeout
                        result = self._execute_task_with_timeout(task, extraction_func, task_timeout)

                        # Store result
                        with self._lock:
                            self.completed_tasks[task.task_id] = result
                            self.global_stats["completed_tasks"] += 1

                        success = True
                        stats.tasks_completed += 1

                        logger.debug(f"⚡ Worker {worker_id} completed task {task.task_id}")

                    except Exception as e:
                        logger.warning(f"⚡ Worker {worker_id} failed task {task.task_id}: {e}")

                        task.retry_count += 1
                        if task.retry_count <= task.max_retries:
                            # Requeue with exponential backoff
                            task.priority *= 0.8  # Lower priority for retries
                            delay = min(30.0, 2.0**task.retry_count)
                            time.sleep(delay)
                            self.task_queue.put(task)
                        else:
                            # Max retries exceeded
                            with self._lock:
                                self.failed_tasks[task.task_id] = task
                                self.global_stats["failed_tasks"] += 1
                            stats.tasks_failed += 1

                    finally:
                        # Update tracking
                        task_duration = time.time() - task_start_time
                        stats.total_time += task_duration
                        stats.last_active = time.time()
                        stats.current_task = None

                        with self._lock:
                            domain_limits.active_requests -= 1
                            domain_limits.register_request(success)

                        # Update global average
                        if success:
                            old_avg = self.global_stats["avg_completion_time"]
                            completed = self.global_stats["completed_tasks"]
                            self.global_stats["avg_completion_time"] = (
                                (old_avg * (completed - 1) + task_duration) / completed if completed > 0 else task_duration
                            )

                        self.task_queue.task_done()

                except Exception as e:
                    if "Empty" not in str(e):  # Ignore timeout from empty queue
                        logger.error(f"⚡ Worker {worker_id} error: {e}")
                    break

        except Exception as e:
            logger.error(f"⚡ Worker {worker_id} fatal error: {e}")
        finally:
            logger.info(f"⚡ Worker {worker_id} finished ({stats.tasks_completed} completed, {stats.tasks_failed} failed)")

    def _execute_task_with_timeout(self, task: ExtractionTask, extraction_func: Callable, timeout: float) -> Any:
        """Execute a single task with intelligent timeout."""
        # Use adaptive timeout if available
        adaptive_timeout = self.timeout_manager.get_optimal_timeout(
            task.url, operation_type="page_load", retry_count=task.retry_count, context=task.metadata
        )

        # Use the minimum of configured and adaptive timeout
        effective_timeout = min(timeout, adaptive_timeout)

        # Check cache first
        cache_key = f"extraction:{task.url}:{hash(str(sorted(task.metadata.items())))}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            logger.debug(f"⚡ Cache hit for task {task.task_id}")
            return cached_result

        # Record start time for timeout tracking
        start_time = time.time()

        try:
            # Execute extraction function
            result = extraction_func(task, timeout=effective_timeout)

            # Record successful response time
            response_time = time.time() - start_time
            self.timeout_manager.record_response(
                task.url,
                response_time,
                True,
                complexity_indicators=task.metadata.get("complexity_indicators"),
                timeout_occurred=False,
            )

            # Cache successful result
            if result:
                from core.intelligent_cache_manager import ContentType

                self.cache_manager.set(
                    cache_key,
                    result,
                    content_type=ContentType.SCHEDULE_DATA,
                    ttl=1800.0,  # 30 minutes for schedule data
                    metadata={"parish_id": task.parish_id, "url": task.url},
                )

            return result

        except TimeoutError:
            # Record timeout
            response_time = time.time() - start_time
            self.timeout_manager.record_response(task.url, response_time, False, timeout_occurred=True)
            raise

        except Exception as e:
            # Record failed response
            response_time = time.time() - start_time
            self.timeout_manager.record_response(task.url, response_time, False)
            raise

    def _get_domain_limits(self, domain: str) -> DomainLimits:
        """Get domain limits, creating default if not exists."""
        with self._lock:
            if domain not in self.domain_limits:
                # Create domain-specific limits based on patterns
                limits = self._create_domain_limits(domain)
                self.domain_limits[domain] = limits

            return self.domain_limits[domain]

    def _create_domain_limits(self, domain: str) -> DomainLimits:
        """Create domain limits based on domain characteristics."""
        # Known domain patterns
        if any(pattern in domain for pattern in ["archatl.com", "wordpress.com"]):
            # Fast, reliable domains
            return DomainLimits(domain=domain, max_concurrent=3, requests_per_second=1.0, burst_limit=5, cooldown_period=30.0)
        elif any(pattern in domain for pattern in ["wix.com", "weebly.com", "squarespace.com"]):
            # Platform sites with potential rate limiting
            return DomainLimits(domain=domain, max_concurrent=2, requests_per_second=0.3, burst_limit=3, cooldown_period=90.0)
        else:
            # Conservative defaults for unknown domains
            return DomainLimits(domain=domain, max_concurrent=2, requests_per_second=0.5, burst_limit=3, cooldown_period=60.0)

    def _calculate_optimal_workers(self) -> int:
        """Calculate optimal number of workers based on queue size and domain distribution."""
        if not self.adaptive_scaling:
            return self.max_workers

        # Count tasks by domain
        domain_counts = defaultdict(int)
        temp_tasks = []

        # Sample up to 100 tasks to analyze distribution
        for _ in range(min(100, self.task_queue.qsize())):
            if not self.task_queue.empty():
                task = self.task_queue.get()
                domain_counts[task.domain] += 1
                temp_tasks.append(task)

        # Put tasks back
        for task in temp_tasks:
            self.task_queue.put(task)

        # Calculate optimal workers
        unique_domains = len(domain_counts)
        total_tasks = sum(domain_counts.values())

        if total_tasks == 0:
            return 1

        # Base calculation on domain diversity and task volume
        if unique_domains <= 2:
            optimal = min(2, self.max_workers)
        elif unique_domains <= 5:
            optimal = min(3, self.max_workers)
        else:
            optimal = min(unique_domains, self.max_workers)

        # Adjust for task volume
        if total_tasks > 50:
            optimal = min(optimal + 1, self.max_workers)

        return max(1, optimal)

    def _monitor_progress(self, futures: List, start_time: float):
        """Monitor progress of parallel extraction."""
        last_report = 0

        while any(not f.done() for f in futures):
            time.sleep(5.0)

            # Report progress every 30 seconds
            if time.time() - last_report > 30:
                self._log_progress_report()
                last_report = time.time()

    def _log_progress_report(self):
        """Log current progress report."""
        with self._lock:
            queue_size = self.task_queue.qsize()
            completed = self.global_stats["completed_tasks"]
            failed = self.global_stats["failed_tasks"]
            active_domains = sum(1 for limits in self.domain_limits.values() if limits.active_requests > 0)

            logger.info(
                f"⚡ Progress: {completed} completed, {failed} failed, "
                f"{queue_size} queued, {active_domains} active domains"
            )

    def _compile_results(self, duration: float) -> Dict[str, Any]:
        """Compile final extraction results."""
        with self._lock:
            total_tasks = self.global_stats["total_tasks"]
            completed = len(self.completed_tasks)
            failed = len(self.failed_tasks)
            success_rate = completed / total_tasks if total_tasks > 0 else 0

            # Worker statistics
            worker_stats = {}
            for worker_id, stats in self.worker_stats.items():
                worker_stats[worker_id] = {
                    "tasks_completed": stats.tasks_completed,
                    "tasks_failed": stats.tasks_failed,
                    "success_rate": stats.success_rate,
                    "avg_task_time": stats.avg_task_time,
                }

            # Domain statistics
            domain_stats = {}
            for domain, limits in self.domain_limits.items():
                domain_stats[domain] = {
                    "total_requests": limits.total_requests,
                    "failed_requests": limits.failed_requests,
                    "failure_rate": limits.failure_rate,
                    "avg_rps": limits.current_rps,
                }

            return {
                "duration": duration,
                "total_tasks": total_tasks,
                "completed": completed,
                "failed": failed,
                "success_rate": success_rate,
                "avg_completion_time": self.global_stats["avg_completion_time"],
                "peak_concurrency": self.global_stats["peak_concurrency"],
                "tasks_per_second": completed / duration if duration > 0 else 0,
                "completed_tasks": dict(self.completed_tasks),
                "failed_tasks": {k: {"url": v.url, "retries": v.retry_count} for k, v in self.failed_tasks.items()},
                "worker_stats": worker_stats,
                "domain_stats": domain_stats,
            }

    def shutdown(self, wait_for_completion: bool = True, timeout: float = 60.0):
        """Gracefully shutdown the extraction manager."""
        logger.info("⚡ Shutting down Parallel Extraction Manager...")

        with self._lock:
            self._shutdown = True

            # Signal shutdown to workers
            for _ in range(self.max_workers):
                try:
                    self.task_queue.put(None, timeout=1.0)
                except:
                    pass

        if wait_for_completion and self.executor:
            try:
                # Wait for current tasks to complete
                self.executor.shutdown(wait=True, timeout=timeout)
            except Exception as e:
                logger.warning(f"⚡ Error during shutdown: {e}")

        logger.info("⚡ Parallel Extraction Manager shutdown complete")

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive extraction statistics."""
        with self._lock:
            return {
                "global_stats": dict(self.global_stats),
                "active_workers": self.active_workers,
                "queue_size": self.task_queue.qsize(),
                "domain_count": len(self.domain_limits),
                "worker_stats": {
                    worker_id: {
                        "tasks_completed": stats.tasks_completed,
                        "tasks_failed": stats.tasks_failed,
                        "success_rate": stats.success_rate,
                        "avg_task_time": stats.avg_task_time,
                        "current_task": stats.current_task,
                    }
                    for worker_id, stats in self.worker_stats.items()
                },
                "domain_stats": {
                    domain: {
                        "active_requests": limits.active_requests,
                        "total_requests": limits.total_requests,
                        "failure_rate": limits.failure_rate,
                        "blocked_until": limits.blocked_until,
                    }
                    for domain, limits in self.domain_limits.items()
                },
            }


def create_extraction_tasks(parishes: List[Dict], base_priority: float = 1.0) -> List[ExtractionTask]:
    """Create extraction tasks from parish data."""
    tasks = []

    for i, parish in enumerate(parishes):
        task = ExtractionTask(
            task_id=f"parish_{parish.get('id', i)}_{int(time.time())}",
            url=parish.get("website_url", ""),
            parish_id=parish.get("id"),
            diocese_id=parish.get("diocese_id"),
            priority=base_priority - (i * 0.01),  # Slight priority decrease for ordering
            metadata={
                "parish_name": parish.get("name", ""),
                "diocese_name": parish.get("diocese_name", ""),
                "address": parish.get("address", ""),
            },
        )
        tasks.append(task)

    return tasks


# Global parallel manager instance
_global_parallel_manager = None


def get_parallel_extraction_manager(max_workers: int = 5) -> ParallelExtractionManager:
    """Get global parallel extraction manager."""
    global _global_parallel_manager
    if _global_parallel_manager is None:
        _global_parallel_manager = ParallelExtractionManager(max_workers)
    return _global_parallel_manager
