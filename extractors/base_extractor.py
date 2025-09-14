#!/usr/bin/env python3
"""
Base Extractor Interface for AI-powered extractors.

This module provides a simple base class that extractors can inherit from.
It's separate from the more complex BaseExtractor in parish_extraction_core.py
to avoid circular dependencies.
"""

from typing import List, Dict, Any
from abc import ABC, abstractmethod
from selenium.webdriver.remote.webdriver import WebDriver


class BaseExtractor(ABC):
    """Base class for parish extractors."""

    def __init__(self):
        """Initialize the base extractor."""
        self.extractor_name = self.__class__.__name__

    @abstractmethod
    def can_extract(self, driver: WebDriver, url: str) -> bool:
        """
        Determine if this extractor can handle the given page.

        Args:
            driver: Selenium WebDriver instance
            url: The URL being processed

        Returns:
            True if this extractor can handle the page
        """
        pass

    @abstractmethod
    def extract(self, driver: WebDriver, diocese_name: str, url: str,
               max_parishes: int = None) -> List[Dict[str, Any]]:
        """
        Extract parish data from the page.

        Args:
            driver: Selenium WebDriver instance
            diocese_name: Name of the diocese
            url: The URL being processed
            max_parishes: Optional limit on number of parishes to extract

        Returns:
            List of parish data dictionaries
        """
        pass

    def get_extraction_stats(self) -> Dict[str, Any]:
        """
        Get statistics and metadata about this extractor.

        Returns:
            Dictionary with extractor information
        """
        return {
            'extractor_name': self.extractor_name,
            'type': 'base_extractor'
        }