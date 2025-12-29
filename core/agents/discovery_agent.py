#!/usr/bin/env python3
"""
Discovery Agent for Agentic Schedule Extraction

This agent is responsible for finding potential schedule sources on parish websites
using multiple discovery strategies with adaptive prioritization.

Phase 1 Implementation: Basic discovery with sitemap and navigation analysis
"""

from typing import List, Dict, Optional
from urllib.parse import urlparse
import logging

# Setup logging
logger = logging.getLogger(__name__)


class DiscoveryAgent:
    """Finds potential schedule sources using multiple strategies"""

    def __init__(self):
        """Initialize discovery strategies with success rates and costs"""
        self.strategies = {
            "sitemap_analysis": {
                "function": self._analyze_sitemap,
                "success_rate": 0.8,
                "cost": 1,  # Budget units
            },
            "navigation_following": {
                "function": self._follow_navigation,
                "success_rate": 0.6,
                "cost": 2,
            },
            "pdf_bulletin_check": {
                "function": self._check_pdf_bulletins,
                "success_rate": 0.4,
                "cost": 3,
            },
            "site_search": {
                "function": self._search_within_site,
                "success_rate": 0.3,
                "cost": 4,
            },
        }

    def discover_sources(self, state: Dict) -> Dict:
        """
        Execute discovery strategies in priority order

        Args:
            state: Current workflow state

        Returns:
            Updated state with discovered sources
        """
        logger.info(f"🔍 Starting discovery for {state['parish_url']}")

        # Sort strategies by success_rate/cost ratio (value per budget)
        sorted_strategies = sorted(
            self.strategies.items(),
            key=lambda x: x[1]["success_rate"] / x[1]["cost"],
            reverse=True,
        )

        for strategy_name, strategy_config in sorted_strategies:
            if state["budget_remaining"] < strategy_config["cost"]:
                logger.debug(f"💰 Not enough budget for {strategy_name}")
                continue

            logger.info(
                f"🔍 Trying {strategy_name} (success: {strategy_config['success_rate']}, cost: {strategy_config['cost']})"
            )

            # Execute strategy
            sources = strategy_config["function"](state["parish_url"])

            # Update state
            state["sources_checked"].extend(sources)
            state["strategies_tried"].append(strategy_name)
            state["budget_remaining"] -= strategy_config["cost"]
            state["knowledge_graph"]["discovery"] = {
                "strategy": strategy_name,
                "sources": sources,
                "timestamp": self._get_current_timestamp(),
            }

            if sources:  # Early exit on success
                logger.info(f"🎯 Found {len(sources)} sources using {strategy_name}")
                return state

        logger.info("🔍 No sources found with any strategy")
        return state

    def _analyze_sitemap(self, url: str) -> List[str]:
        """
        Use existing sitemap parser with enhancements

        Args:
            url: Parish website URL

        Returns:
            List of schedule-related URLs
        """
        try:
            from pipeline.extract_schedule import get_sitemap_urls

            logger.debug(f"🗺️  Analyzing sitemap for {url}")
            urls = get_sitemap_urls(url)

            # Filter for schedule-related URLs
            schedule_urls = [
                u
                for u in urls
                if any(
                    keyword in u.lower()
                    for keyword in [
                        "schedule",
                        "reconciliation",
                        "confession",
                        "adoration",
                        "sacrament",
                        "hours",
                    ]
                )
            ]

            logger.debug(
                f"🗺️  Found {len(schedule_urls)} schedule-related URLs in sitemap"
            )
            return schedule_urls[:10]  # Limit to top 10

        except Exception as e:
            logger.error(f"🗺️  Sitemap analysis failed: {e}")
            return []

    def _follow_navigation(self, url: str) -> List[str]:
        """
        Extract navigation links and follow relevant ones

        Args:
            url: Parish website URL

        Returns:
            List of navigation URLs
        """
        try:
            from pipeline.extract_schedule import get_navigation_links

            logger.debug(f"🧭 Following navigation for {url}")
            nav_links = get_navigation_links(url)

            logger.debug(f"🧭 Found {len(nav_links)} navigation links")
            return nav_links[:15]  # Limit to top 15

        except Exception as e:
            logger.error(f"🧭 Navigation following failed: {e}")
            return []

    def _check_pdf_bulletins(self, url: str) -> List[str]:
        """
        Find and analyze PDF bulletins (Phase 2 placeholder)

        Args:
            url: Parish website URL

        Returns:
            List of PDF URLs
        """
        logger.debug(f"📄 Checking for PDF bulletins at {url}")
        # Phase 2 implementation will go here
        return []

    def _search_within_site(self, url: str) -> List[str]:
        """
        Use site-specific search (Phase 2 placeholder)

        Args:
            url: Parish website URL

        Returns:
            List of search result URLs
        """
        logger.debug(f"🔎 Searching within site {url}")
        # Phase 2 implementation will go here
        return []

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime

        return datetime.now().isoformat()
