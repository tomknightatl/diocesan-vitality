#!/usr/bin/env python3
"""
Circuit Breaker Pattern implementation for external service protection.
Prevents cascade failures and provides intelligent retry mechanisms.
"""

import time
import threading
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union
from dataclasses import dataclass
from core.logger import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation - requests pass through
    OPEN = "open"          # Failure state - requests are blocked
    HALF_OPEN = "half_open"  # Testing state - limited requests allowed


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5          # Failures before opening circuit
    recovery_timeout: int = 60          # Seconds before trying half-open
    success_threshold: int = 3          # Successes needed to close from half-open
    request_timeout: int = 30           # Seconds before timing out requests
    max_retries: int = 3               # Maximum retry attempts
    retry_delay: float = 1.0           # Base delay between retries (exponential backoff)
    
    
class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and blocks requests"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation with failure tracking and automatic recovery.
    
    Features:
    - Automatic failure detection and circuit opening
    - Exponential backoff for retries
    - Half-open state for gradual recovery
    - Thread-safe operation
    - Detailed logging and monitoring
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.next_attempt_time = time.time()
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.total_timeouts = 0
        self.total_blocked = 0
        
        logger.info(f"🔌 Circuit breaker '{name}' initialized with config: "
                   f"failure_threshold={self.config.failure_threshold}, "
                   f"recovery_timeout={self.config.recovery_timeout}s")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker with protection.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result of the function call
            
        Raises:
            CircuitBreakerOpenError: When circuit is open and blocking requests
            TimeoutError: When request times out
            Exception: Original exception from the protected function
        """
        with self._lock:
            self.total_requests += 1
            
            # Check if circuit should remain open
            if self.state == CircuitState.OPEN:
                if time.time() < self.next_attempt_time:
                    self.total_blocked += 1
                    logger.warning(f"🚫 Circuit breaker '{self.name}' OPEN - blocking request")
                    raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is OPEN")
                else:
                    # Time to try half-open
                    logger.info(f"🔄 Circuit breaker '{self.name}' transitioning to HALF-OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
            
            # In HALF_OPEN state, limit concurrent requests
            if self.state == CircuitState.HALF_OPEN:
                logger.debug(f"🟡 Circuit breaker '{self.name}' in HALF-OPEN state - testing request")
        
        # Execute the function with retry logic
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Add timeout wrapper if not already present
                if hasattr(func, '__timeout_wrapped__'):
                    result = func(*args, **kwargs)
                else:
                    result = self._execute_with_timeout(func, *args, **kwargs)
                
                # Success - update circuit state
                self._on_success()
                return result
                
            except TimeoutError as e:
                last_exception = e
                self.total_timeouts += 1
                logger.warning(f"⏰ Timeout in circuit breaker '{self.name}' (attempt {attempt + 1}/{self.config.max_retries + 1})")
                
            except Exception as e:
                last_exception = e
                logger.warning(f"❌ Error in circuit breaker '{self.name}' (attempt {attempt + 1}/{self.config.max_retries + 1}): {str(e)}")
            
            # Don't retry on the last attempt
            if attempt < self.config.max_retries:
                retry_delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.debug(f"🔄 Retrying in {retry_delay:.1f}s...")
                time.sleep(retry_delay)
        
        # All retries failed
        self._on_failure()
        raise last_exception
    
    def _execute_with_timeout(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with timeout protection"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Function call timed out after {self.config.request_timeout} seconds")
        
        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.config.request_timeout)
        
        try:
            result = func(*args, **kwargs)
            signal.alarm(0)  # Cancel timeout
            return result
        finally:
            signal.signal(signal.SIGALRM, old_handler)
    
    def _on_success(self):
        """Handle successful request"""
        with self._lock:
            self.total_successes += 1
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                logger.debug(f"✅ Success in HALF-OPEN state ({self.success_count}/{self.config.success_threshold})")
                
                if self.success_count >= self.config.success_threshold:
                    logger.info(f"🟢 Circuit breaker '{self.name}' CLOSED - service recovered")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                if self.failure_count > 0:
                    logger.debug(f"✅ Resetting failure count for '{self.name}'")
                    self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed request"""
        with self._lock:
            self.total_failures += 1
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    logger.error(f"🔴 Circuit breaker '{self.name}' OPEN - failure threshold exceeded "
                               f"({self.failure_count}/{self.config.failure_threshold})")
                    self.state = CircuitState.OPEN
                    self.next_attempt_time = time.time() + self.config.recovery_timeout
                else:
                    logger.debug(f"⚠️ Failure #{self.failure_count} for '{self.name}' "
                                f"({self.config.failure_threshold - self.failure_count} until circuit opens)")
            
            elif self.state == CircuitState.HALF_OPEN:
                logger.warning(f"🔴 Circuit breaker '{self.name}' back to OPEN - test request failed")
                self.state = CircuitState.OPEN
                self.next_attempt_time = time.time() + self.config.recovery_timeout
                self.success_count = 0
    
    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        """Get circuit breaker statistics"""
        with self._lock:
            success_rate = (self.total_successes / max(self.total_requests, 1)) * 100
            
            return {
                'name': self.name,
                'state': self.state.value,
                'total_requests': self.total_requests,
                'total_successes': self.total_successes,
                'total_failures': self.total_failures,
                'total_timeouts': self.total_timeouts,
                'total_blocked': self.total_blocked,
                'success_rate': f"{success_rate:.1f}%",
                'current_failures': self.failure_count,
                'failure_threshold': self.config.failure_threshold,
                'last_failure_time': self.last_failure_time
            }
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        with self._lock:
            logger.info(f"🔄 Resetting circuit breaker '{self.name}'")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.next_attempt_time = time.time()
    
    def force_open(self):
        """Manually open the circuit breaker"""
        with self._lock:
            logger.warning(f"🔴 Manually opening circuit breaker '{self.name}'")
            self.state = CircuitState.OPEN
            self.next_attempt_time = time.time() + self.config.recovery_timeout
    
    def force_close(self):
        """Manually close the circuit breaker"""
        with self._lock:
            logger.info(f"🟢 Manually closing circuit breaker '{self.name}'")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0


class CircuitBreakerManager:
    """
    Global manager for circuit breakers to avoid creating duplicates
    and provide centralized monitoring.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.circuit_breakers: Dict[str, CircuitBreaker] = {}
            self.initialized = True
            logger.info("🔌 Circuit Breaker Manager initialized")
    
    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker by name"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all circuit breakers"""
        return {name: cb.get_stats() for name, cb in self.circuit_breakers.items()}
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for cb in self.circuit_breakers.values():
            cb.reset()
    
    def log_summary(self):
        """Log a summary of all circuit breaker statistics"""
        if not self.circuit_breakers:
            logger.info("📊 No circuit breakers active")
            return
            
        logger.info("📊 Circuit Breaker Summary:")
        for name, cb in self.circuit_breakers.items():
            stats = cb.get_stats()
            logger.info(f"  • {name}: {stats['state'].upper()} | "
                       f"Requests: {stats['total_requests']} | "
                       f"Success Rate: {stats['success_rate']} | "
                       f"Failures: {stats['total_failures']} | "
                       f"Timeouts: {stats['total_timeouts']} | "
                       f"Blocked: {stats['total_blocked']}")


# Global circuit breaker manager instance
circuit_manager = CircuitBreakerManager()


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator to wrap functions with circuit breaker protection.
    
    Usage:
        @circuit_breaker('diocese_website')
        def fetch_diocese_page(url):
            return requests.get(url)
    """
    def decorator(func):
        cb = circuit_manager.get_circuit_breaker(name, config)
        
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__timeout_wrapped__ = True
        return wrapper
    
    return decorator