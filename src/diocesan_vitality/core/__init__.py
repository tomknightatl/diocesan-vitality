"""
Core module for Diocesan Vitality.

This module contains essential utilities including database operations,
WebDriver management, circuit breakers, and AI analysis components.
"""

from .circuit_breaker import CircuitBreaker
from .db import get_db_connection

# Import key utilities for easy access
from .logger import get_logger
from .utils import *

__all__ = ["get_logger", "get_db_connection", "CircuitBreaker"]
