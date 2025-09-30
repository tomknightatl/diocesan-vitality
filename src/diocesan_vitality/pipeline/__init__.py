"""
Pipeline module for Diocesan Vitality.

This module contains the main data extraction pipeline components.
"""

from .runner import main as run_pipeline

__all__ = ["run_pipeline"]
