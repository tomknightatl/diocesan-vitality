#!/usr/bin/env python3
"""
Diocese-Specific Extraction Profiles.

This module contains specialized extraction strategies for dioceses that require
custom handling due to unique website architectures, dynamic loading patterns,
or specific content management systems.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DiocesesExtractionProfile:
    """Profile for diocese-specific extraction strategies."""

    diocese_domain: str
    strategy_type: str  # 'dynamic_loading', 'api_extraction', 'navigation_based', 'custom_selectors'
    wait_time: int = 10
    custom_selectors: List[str] = None
    api_endpoints: List[str] = None
    interaction_required: bool = False
    loading_indicators: List[str] = None
    content_selectors: List[str] = None
    javascript_required: bool = False
    scroll_trigger: bool = False
    button_clicks: List[str] = None
    special_instructions: str = ""

    def __post_init__(self):
        if self.custom_selectors is None:
            self.custom_selectors = []
        if self.api_endpoints is None:
            self.api_endpoints = []
        if self.loading_indicators is None:
            self.loading_indicators = []
        if self.content_selectors is None:
            self.content_selectors = []
        if self.button_clicks is None:
            self.button_clicks = []


class DiocesesProfileManager:
    """Manages diocese-specific extraction profiles."""

    def __init__(self):
        """Initialize the profile manager with known diocese profiles."""
        self.profiles = self._initialize_profiles()
        logger.info(f"🎯 Loaded {len(self.profiles)} diocese extraction profiles")

    def _initialize_profiles(self) -> Dict[str, DiocesesExtractionProfile]:
        """Initialize known diocese profiles based on analysis results."""
        profiles = {}

        # Diocese of Houma-Thibodaux - Dynamic loading with "Just a moment..."
        profiles["htdiocese.org"] = DiocesesExtractionProfile(
            diocese_domain="htdiocese.org",
            strategy_type="dynamic_loading",
            wait_time=15,
            javascript_required=True,
            loading_indicators=["just a moment", "loading", "please wait"],
            custom_selectors=[
                ".entry-title a",
                '.entry-content a[href*="parish"]',
                ".wp-block-column a",
                "article .entry-title a",
                ".parish-link a",
            ],
            scroll_trigger=True,
            special_instructions="WordPress site with Cloudflare protection and dynamic loading",
        )

        # Diocese of Marquette - Dynamic loading detected
        profiles["dioceseofmarquette.org"] = DiocesesExtractionProfile(
            diocese_domain="dioceseofmarquette.org",
            strategy_type="dynamic_loading",
            wait_time=12,
            javascript_required=True,
            loading_indicators=["just a moment", "loading"],
            custom_selectors=[
                ".parish-listing a",
                ".directory-item a",
                ".church-list a",
                "article h2 a",
                '.entry-title a[href*="parish"]',
            ],
            interaction_required=True,
            button_clicks=[".load-more", ".show-all", "#expand-parishes"],
            special_instructions="CMS-based with navigation-heavy structure",
        )

        # Diocese of Santa Rosa - From previous analysis
        profiles["srdiocese.org"] = DiocesesExtractionProfile(
            diocese_domain="srdiocese.org",
            strategy_type="navigation_based",
            wait_time=8,
            custom_selectors=[
                ".parish-directory a",
                ".parish-list .parish-item a",
                ".location-list a",
                "nav .parish-link",
                ".directory-entry a",
            ],
            content_selectors=[".parish-content", ".main-content"],
            special_instructions="Navigation-based extraction with hover menus",
        )

        # Common WordPress dioceses pattern
        profiles["wordpress_pattern"] = DiocesesExtractionProfile(
            diocese_domain="*wordpress*",
            strategy_type="dynamic_loading",
            wait_time=10,
            javascript_required=True,
            custom_selectors=[
                '.wp-block-group a[href*="parish"]',
                ".entry-content a",
                ".wp-block-column a",
                "article .entry-title a",
                '.post-content a[href*="church"]',
            ],
            loading_indicators=["loading", "just a moment"],
            scroll_trigger=True,
            special_instructions="Generic WordPress diocese site pattern",
        )

        # eCatholic platform pattern
        profiles["ecatholic_pattern"] = DiocesesExtractionProfile(
            diocese_domain="*ecatholic*",
            strategy_type="api_extraction",
            wait_time=5,
            api_endpoints=["/api/parishes", "/data/parishes.json", "/parishes/list"],
            custom_selectors=[".parish-finder .result a", ".location-result a", ".parish-search-result a"],
            special_instructions="eCatholic platform with API endpoints",
        )

        # Drupal-based dioceses
        profiles["drupal_pattern"] = DiocesesExtractionProfile(
            diocese_domain="*drupal*",
            strategy_type="custom_selectors",
            wait_time=7,
            custom_selectors=[
                ".view-parish-directory .field-content a",
                ".node-parish .field-name-title a",
                ".region-content .field-item a",
                ".view-content .views-row a",
            ],
            content_selectors=[".region-content", ".main-container"],
            special_instructions="Drupal CMS with field-based structure",
        )

        return profiles

    def get_profile(self, url: str, diocese_name: str = None) -> Optional[DiocesesExtractionProfile]:
        """Get the most appropriate profile for a diocese URL."""
        try:
            domain = urlparse(url).netloc.lower()

            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]

            # Direct domain match
            if domain in self.profiles:
                logger.info(f"🎯 Found specific profile for {domain}")
                return self.profiles[domain]

            # Pattern matching for common platforms
            if "wordpress" in url.lower() or self._is_wordpress_site(url):
                logger.info(f"🎯 Using WordPress pattern for {domain}")
                return self.profiles["wordpress_pattern"]

            if "ecatholic" in domain:
                logger.info(f"🎯 Using eCatholic pattern for {domain}")
                return self.profiles["ecatholic_pattern"]

            # Content-based detection (would require page analysis)
            # This could be enhanced with actual content detection

            logger.info(f"🎯 No specific profile found for {domain}")
            return None

        except Exception as e:
            logger.error(f"🎯 Error getting profile for {url}: {e}")
            return None

    def _is_wordpress_site(self, url: str) -> bool:
        """Detect if a site is likely WordPress-based."""
        # This could be enhanced with actual WordPress detection
        wordpress_indicators = ["wp-content", "wp-includes", "wp-admin"]
        return any(indicator in url.lower() for indicator in wordpress_indicators)

    def create_custom_profile(self, domain: str, analysis_results: Dict) -> DiocesesExtractionProfile:
        """Create a custom profile based on AI analysis results."""
        try:
            # Extract strategy from AI analysis
            strategy = analysis_results.get("extraction_strategy", "custom_selectors")
            confidence = analysis_results.get("confidence", 0.5)
            selectors = analysis_results.get("custom_selectors", [])
            insights = analysis_results.get("ai_insights", [])

            # Determine if JavaScript is required
            javascript_required = any("javascript" in insight.lower() or "dynamic" in insight.lower() for insight in insights)

            # Determine loading indicators
            loading_indicators = []
            if javascript_required:
                loading_indicators = ["loading", "just a moment", "please wait"]

            profile = DiocesesExtractionProfile(
                diocese_domain=domain,
                strategy_type=strategy,
                wait_time=int(10 + (confidence * 10)),  # More confident = longer wait
                custom_selectors=selectors[:10],  # Limit to top 10 selectors
                javascript_required=javascript_required,
                loading_indicators=loading_indicators,
                scroll_trigger=javascript_required,
                special_instructions=f"Auto-generated from AI analysis (confidence: {confidence:.2f})",
            )

            # Cache the profile for future use
            self.profiles[domain] = profile
            logger.info(f"🎯 Created custom profile for {domain} with strategy {strategy}")

            return profile

        except Exception as e:
            logger.error(f"🎯 Failed to create custom profile for {domain}: {e}")
            return None

    def update_profile_success(self, domain: str, method_used: str, success: bool):
        """Update profile based on extraction success/failure."""
        try:
            if domain in self.profiles:
                profile = self.profiles[domain]

                # Track success/failure (could be enhanced with persistent storage)
                if success:
                    logger.info(f"🎯 Profile for {domain} succeeded with {method_used}")
                    # Could reduce wait time or mark strategy as preferred
                else:
                    logger.warning(f"🎯 Profile for {domain} failed with {method_used}")
                    # Could increase wait time or try alternative strategy

        except Exception as e:
            logger.error(f"🎯 Failed to update profile for {domain}: {e}")

    def get_all_profiles(self) -> Dict[str, DiocesesExtractionProfile]:
        """Get all available profiles."""
        return self.profiles.copy()

    def get_profile_stats(self) -> Dict[str, Any]:
        """Get statistics about available profiles."""
        stats = {
            "total_profiles": len(self.profiles),
            "strategy_distribution": {},
            "javascript_required": 0,
            "api_based": 0,
            "custom_selectors": 0,
        }

        for profile in self.profiles.values():
            strategy = profile.strategy_type
            stats["strategy_distribution"][strategy] = stats["strategy_distribution"].get(strategy, 0) + 1

            if profile.javascript_required:
                stats["javascript_required"] += 1

            if profile.api_endpoints:
                stats["api_based"] += 1

            if profile.custom_selectors:
                stats["custom_selectors"] += 1

        return stats


# Global instance
_profile_manager = None


def get_diocese_profile_manager() -> DiocesesProfileManager:
    """Get the global diocese profile manager."""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = DiocesesProfileManager()
    return _profile_manager
