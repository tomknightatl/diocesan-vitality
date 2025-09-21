"""
Core module for Diocesan Vitality.

This module contains essential utilities including database operations,
WebDriver management, circuit breakers, and AI analysis components.
"""

# Import key utilities for easy access
from .logger import get_logger
from .db import get_db_connection
from .circuit_breaker import CircuitBreaker
from .utils import *

__all__ = [
    "get_logger",
    "get_db_connection",
    "CircuitBreaker"
]