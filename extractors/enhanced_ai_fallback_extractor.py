#!/usr/bin/env python3
"""
Enhanced AI Fallback Extractor with JavaScript Execution and Network Analysis.

This advanced extractor combines:
1. AI - powered content analysis
2. JavaScript execution engine for dynamic content
3. Network traffic analysis for API discovery
4. Diocese - specific profiles for optimized extraction
"""

import json
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from config import get_genai_api_key
from core.ai_content_analyzer import get_ai_content_analyzer
from core.diocese_profiles import get_diocese_profile_manager
from core.dynamic_content_engine import get_dynamic_content_engine
from core.logger import get_logger
from extractors.base_extractor import BaseExtractor

logger = get_logger(__name__)


class EnhancedAIFallbackExtractor(BaseExtractor):
    """
    Enhanced AI - powered fallback extractor with advanced dynamic content capabilities.

    This extractor is the ultimate fallback when all standard methods fail.
    It uses AI analysis combined with JavaScript execution and network traffic
    monitoring to extract parishes from the most challenging diocese websites.
    """

    def __init__(self):
        """Initialize the enhanced AI fallback extractor."""
        super().__init__()
        self.extractor_name = "EnhancedAIFallbackExtractor"

        # Initialize components
        genai_api_key = get_genai_api_key()
        if genai_api_key:
            self.ai_analyzer = get_ai_content_analyzer(genai_api_key)
            self.profile_manager = get_diocese_profile_manager()
            logger.info("🚀 Enhanced AI Fallback Extractor initialized with full capabilities")
        else:
            self.ai_analyzer = None
            self.profile_manager = None
            logger.warning("🚀 Enhanced AI Fallback Extractor disabled - missing GenAI API key")

    def can_extract(self, driver: WebDriver, url: str) -> bool:
        """
        This enhanced extractor can attempt extraction if AI and profiles are available.
        """
        if not self.ai_analyzer or not self.profile_manager:
            logger.warning("🚀 Enhanced AI Fallback Extractor disabled - missing components")
            return False

        logger.info("🚀 Enhanced AI Fallback Extractor: Ready for advanced extraction")
        return True

    def _initialize_extraction(self, diocese_name: str, url: str, max_parishes: int) -> bool:
        """Initialize extraction and validate prerequisites."""
        logger.info(f"🚀 Enhanced AI Fallback Extraction starting for {diocese_name}")
        logger.info(f"    📊 Target: up to {max_parishes or 'unlimited'} parishes")
        logger.info(f"    🌐 URL: {url}")

        if not self.ai_analyzer:
            logger.error("🚀 Enhanced AI Fallback Extractor not properly initialized")
            return False
        return True

    def _try_profile_extraction(
        self, driver: WebDriver, diocese_name: str, url: str, max_parishes: int
    ) -> tuple[List[Dict[str, Any]], str]:
        """Try profile - based extraction first."""
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        profile = self.profile_manager.get_profile(url, diocese_name)
        if profile:
            logger.info(f"🎯 Using diocese profile: {profile.strategy_type} strategy")
            parishes = self._extract_with_profile(driver, diocese_name, url, profile, max_parishes)
            if parishes:
                self.profile_manager.update_profile_success(domain, profile.strategy_type, True)
                return parishes, domain
            else:
                self.profile_manager.update_profile_success(domain, profile.strategy_type, False)
                logger.warning("🎯 Profile - based extraction failed, falling back to dynamic analysis")
        return [], domain

    def _perform_dynamic_loading_and_ai_analysis(self, driver: WebDriver, diocese_name: str, url: str) -> tuple[dict, dict]:
        """Perform dynamic content loading and AI analysis."""
        # Dynamic content loading with JavaScript engine
        js_engine = get_dynamic_content_engine(driver)
        loading_result = js_engine.wait_for_dynamic_content(diocese_name, timeout=20)

        logger.info("🚀 Dynamic loading results:")
        logger.info(f"    📊 Content loaded: {loading_result['content_loaded']}")
        logger.info(f"    🔧 Method used: {loading_result['method_used']}")
        logger.info(f"    ⏱️ Loading time: {loading_result['loading_time']:.2f}s")
        logger.info(f"    🌐 API endpoints found: {len(loading_result['api_endpoints'])}")

        # AI analysis with enhanced context
        logger.info("🤖 Running enhanced AI content analysis...")
        ai_result = self.ai_analyzer.analyze_failed_extraction(driver, diocese_name, url)

        return loading_result, ai_result

    def _merge_extraction_results(self, loading_result: dict, ai_result: dict, url: str) -> List[Dict[str, Any]]:
        """Merge results from different extraction methods."""
        all_parish_data = []

        # Add parishes found by JavaScript engine
        if loading_result["parish_elements"]:
            logger.info(f"🚀 Adding {len(loading_result['parish_elements'])} parishes from dynamic loading")
            for elem in loading_result["parish_elements"]:
                parish_data = {
                    "name": elem["name"],
                    "url": urljoin(url, elem["url"]),
                    "extractor_used": self.extractor_name,
                    "extraction_method": "javascript_dynamic_loading",
                    "js_method": loading_result["method_used"],
                    "loading_time": loading_result["loading_time"],
                }
                all_parish_data.append(parish_data)

        # Add parishes found by AI analysis
        if ai_result.get("parish_data"):
            logger.info(f"🤖 Adding {len(ai_result['parish_data'])} parishes from AI analysis")
            for parish in ai_result["parish_data"]:
                parish["extractor_used"] = self.extractor_name
                parish["extraction_method"] = "ai_content_analysis"
                parish["ai_strategy"] = ai_result.get("extraction_strategy")
                parish["ai_confidence"] = ai_result.get("confidence", 0.0)
                all_parish_data.append(parish)

        # Try API endpoints if discovered
        if loading_result["api_endpoints"]:
            logger.info(f"🌐 Attempting API extraction from {len(loading_result['api_endpoints'])} endpoints")
            api_parishes = self._extract_from_api_endpoints(loading_result["api_endpoints"], url)
            all_parish_data.extend(api_parishes)

        return all_parish_data

    def _manage_profiles_based_on_results(
        self,
        profile,
        domain: str,
        validated_parishes: List[Dict[str, Any]],
        ai_result: dict,
    ) -> None:
        """Create or update profiles based on extraction results."""
        if profile:  # Profile already exists
            return

        if validated_parishes:
            # Successful extraction - create confidence profile
            new_profile = self.profile_manager.create_custom_profile(domain, ai_result)
            if new_profile:
                logger.info(f"🎯 Created high - confidence profile for {domain} based on successful extraction")
        elif ai_result.get("confidence", 0.0) >= 0.6 and ai_result.get("extraction_strategy"):
            # Failed extraction but high AI confidence - create learning profile
            learning_profile = self.profile_manager.create_custom_profile(domain, ai_result)
            if learning_profile:
                logger.info(
                    f"🎯 Created learning profile for {domain} - Strategy: {ai_result.get('extraction_strategy')} (confidence: {ai_result.get('confidence', 0.0):.2f})"
                )
                logger.info("    💡 Profile will be used for future extractions to improve success rate")

    def _log_final_results(
        self,
        validated_parishes: List[Dict[str, Any]],
        loading_result: dict,
        ai_result: dict,
    ) -> None:
        """Log final extraction results."""
        if validated_parishes:
            logger.info("🚀 ✅ Enhanced AI Fallback Extraction successful!")
            logger.info(f"    📊 Final count: {len(validated_parishes)} parishes")
            api_count = (
                len(self._extract_from_api_endpoints(loading_result.get("api_endpoints", []), ""))
                if loading_result.get("api_endpoints")
                else 0
            )
            logger.info(
                f"    🎯 Success methods: JS={len(loading_result.get('parish_elements', []))}, AI={len(ai_result.get('parish_data', []))}, API={api_count}"
            )

            # Log sample results
            for i, parish in enumerate(validated_parishes[:3], 1):
                logger.info(f"    {i}. {parish.get('name', 'N/A')} ({parish.get('extraction_method', 'unknown')})")
                if parish.get("url"):
                    logger.info(f"       🔗 {parish['url']}")
        else:
            logger.warning("🚀 ❌ Enhanced AI Fallback Extraction found no valid parishes")
            logger.warning(f"    💭 AI suggested strategy: {ai_result.get('extraction_strategy', 'unknown')}")
            logger.warning(f"    📊 AI confidence: {ai_result.get('confidence', 0.0):.2f}")
            logger.warning(f"    🚀 JS content loaded: {loading_result['content_loaded']}")

    def extract(self, driver: WebDriver, diocese_name: str, url: str, max_parishes: int = None) -> List[Dict[str, Any]]:
        """
        Enhanced extraction using AI analysis, JavaScript execution, and profiles.

        This method implements a sophisticated multi - stage approach:
        1. Check for diocese - specific profiles
        2. Use JavaScript engine for dynamic content loading
        3. Apply AI analysis with network traffic monitoring
        4. Extract and validate parish data
        5. Update profiles based on results
        """
        # Step 1: Initialize extraction
        if not self._initialize_extraction(diocese_name, url, max_parishes):
            return []

        try:
            # Step 2: Try profile - based extraction first
            parishes, domain = self._try_profile_extraction(driver, diocese_name, url, max_parishes)
            if parishes:
                return parishes

            # Step 3: Perform dynamic loading and AI analysis
            loading_result, ai_result = self._perform_dynamic_loading_and_ai_analysis(driver, diocese_name, url)

            # Step 4: Merge results from different extraction methods
            all_parish_data = self._merge_extraction_results(loading_result, ai_result, url)

            # Step 5: Validate and deduplicate results
            validated_parishes = self._validate_and_deduplicate(all_parish_data)

            # Step 6: Manage profiles based on results
            profile = self.profile_manager.get_profile(url, diocese_name)
            self._manage_profiles_based_on_results(profile, domain, validated_parishes, ai_result)

            # Step 7: Apply max_parishes limit
            if max_parishes and len(validated_parishes) > max_parishes:
                validated_parishes = validated_parishes[:max_parishes]
                logger.info(f"🚀 Limited results to {max_parishes} parishes")

            # Step 8: Log final results
            self._log_final_results(validated_parishes, loading_result, ai_result)

            return validated_parishes

        except Exception as e:
            logger.error(f"🚀 Enhanced AI Fallback Extraction failed: {e}", exc_info=True)
            return []

    def _wait_for_dynamic_content_if_needed(self, driver: WebDriver, diocese_name: str, profile):
        """Wait for dynamic content loading if required by profile."""
        if not profile.javascript_required:
            return

        js_engine = get_dynamic_content_engine(driver)
        loading_result = js_engine.wait_for_dynamic_content(diocese_name, profile.wait_time)

        if loading_result["content_loaded"]:
            logger.info("🎯 Dynamic content loaded using profile settings")
        else:
            logger.warning("🎯 Profile dynamic loading failed, continuing with static extraction")

    def _extract_with_custom_selectors(self, driver: WebDriver, url: str, profile, max_parishes: int) -> List[Dict[str, Any]]:
        """Extract parishes using profile's custom selectors."""
        parishes = []
        if not profile.custom_selectors:
            return parishes

        for selector in profile.custom_selectors:
            try:
                elements = driver.find_elements("css selector", selector)
                for elem in elements:
                    parish_data = self._extract_parish_from_element(elem, url, "profile_selector")
                    if parish_data and self._validate_parish_data(parish_data):
                        parishes.append(parish_data)

                if len(parishes) >= (max_parishes or 20):
                    break

            except Exception as e:
                logger.debug(f"🎯 Profile selector '{selector}' failed: {e}")
                continue

        return parishes

    def _extract_with_button_interactions(self, driver: WebDriver, url: str, profile) -> List[Dict[str, Any]]:
        """Extract parishes using profile's button click interactions."""
        if not self._should_perform_button_interactions(profile):
            return []

        parishes = []
        for button_selector in profile.button_clicks:
            interaction_parishes = self._try_button_interaction(driver, url, button_selector, profile)
            parishes.extend(interaction_parishes)
            if interaction_parishes:  # Only click first successful button
                break

        return parishes

    def _should_perform_button_interactions(self, profile) -> bool:
        """Check if button interactions should be performed."""
        return bool(profile.button_clicks and profile.interaction_required)

    def _try_button_interaction(self, driver: WebDriver, url: str, button_selector: str, profile) -> List[Dict[str, Any]]:
        """Try clicking a button and extracting parishes after interaction."""
        try:
            buttons = driver.find_elements("css selector", button_selector)
            for button in buttons:
                if self._is_button_clickable(button):
                    return self._perform_button_click_extraction(driver, url, button, button_selector, profile)
        except Exception as e:
            logger.debug(f"🎯 Profile button click '{button_selector}' failed: {e}")

        return []

    def _is_button_clickable(self, button) -> bool:
        """Check if button is clickable."""
        return button.is_displayed() and button.is_enabled()

    def _perform_button_click_extraction(
        self, driver: WebDriver, url: str, button, button_selector: str, profile
    ) -> List[Dict[str, Any]]:
        """Perform button click and extract parishes from resulting content."""
        logger.info(f"🎯 Clicking profile button: {button_selector}")
        button.click()
        time.sleep(2)

        parishes = []
        # Re-try selectors after interaction
        for selector in profile.custom_selectors[:3]:  # Try top 3
            selector_parishes = self._extract_after_interaction(driver, url, selector)
            parishes.extend(selector_parishes)

        return parishes

    def _extract_after_interaction(self, driver: WebDriver, url: str, selector: str) -> List[Dict[str, Any]]:
        """Extract parishes using selector after button interaction."""
        parishes = []
        try:
            elements = driver.find_elements("css selector", selector)
            for elem in elements:
                parish_data = self._extract_parish_from_element(elem, url, "profile_interaction")
                if parish_data and self._validate_parish_data(parish_data):
                    parishes.append(parish_data)
        except (NoSuchElementException, WebDriverException):
            pass

        return parishes

    def _extract_with_profile(
        self,
        driver: WebDriver,
        diocese_name: str,
        url: str,
        profile,
        max_parishes: int,
    ) -> List[Dict[str, Any]]:
        """Extract parishes using diocese - specific profile."""
        try:
            logger.info(f"🎯 Applying profile strategy: {profile.strategy_type}")

            parishes = []

            # Apply profile - specific waiting strategy
            self._wait_for_dynamic_content_if_needed(driver, diocese_name, profile)

            # Try profile custom selectors
            parishes.extend(self._extract_with_custom_selectors(driver, url, profile, max_parishes))

            # Try profile button clicks if specified
            parishes.extend(self._extract_with_button_interactions(driver, url, profile))

            # Remove duplicates
            unique_parishes = self._deduplicate_parishes(parishes)

            logger.info(f"🎯 Profile extraction found {len(unique_parishes)} parishes")
            return unique_parishes

        except Exception as e:
            logger.error(f"🎯 Profile - based extraction failed: {e}")
            return []

    def _extract_from_api_endpoints(self, api_endpoints: set, base_url: str) -> List[Dict[str, Any]]:
        """Extract parish data from discovered API endpoints."""
        parishes = []

        try:
            import requests

            for endpoint in list(api_endpoints)[:5]:  # Try up to 5 endpoints
                try:
                    logger.info(f"🌐 Trying API endpoint: {endpoint}")

                    # Make API request
                    response = requests.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            api_parishes = self._parse_api_response(data, base_url)
                            parishes.extend(api_parishes)

                            if api_parishes:
                                logger.info(f"🌐 API endpoint {endpoint} returned {len(api_parishes)} parishes")

                        except json.JSONDecodeError:
                            logger.debug(f"🌐 API endpoint {endpoint} returned non - JSON data")

                except Exception as e:
                    logger.debug(f"🌐 API endpoint {endpoint} failed: {e}")
                    continue

        except ImportError:
            logger.warning("🌐 Requests library not available for API extraction")

        return parishes

    def _parse_api_response(self, data: Any, base_url: str) -> List[Dict[str, Any]]:
        """Parse API response data for parish information."""
        parishes = []

        try:
            # Handle different response formats
            if isinstance(data, dict):
                # Check for common parish data structures
                for key in ["parishes", "churches", "locations", "data", "results"]:
                    if key in data and isinstance(data[key], list):
                        data = data[key]
                        break

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        parish_data = self._extract_parish_from_api_item(item, base_url)
                        if parish_data:
                            parishes.append(parish_data)

        except Exception as e:
            logger.error(f"🌐 API response parsing failed: {e}")

        return parishes

    def _extract_parish_from_api_item(self, item: Dict, base_url: str) -> Optional[Dict[str, Any]]:
        """Extract parish data from API response item."""
        try:
            name = self._extract_name_from_api_item(item)
            if not name:
                return None

            parish_data = self._create_base_parish_data(name)
            self._add_url_data_from_api_item(parish_data, item, base_url)
            self._add_contact_data_from_api_item(parish_data, item)

            return parish_data if self._validate_parish_data(parish_data) else None

        except Exception as e:
            logger.debug(f"🌐 Failed to extract from API item: {e}")
            return None

    def _extract_name_from_api_item(self, item: Dict) -> Optional[str]:
        """Extract parish name from API item."""
        name_fields = ["name", "title", "parish_name", "church_name"]
        for name_field in name_fields:
            if name_field in item:
                return item[name_field]
        return None

    def _create_base_parish_data(self, name: str) -> Dict[str, Any]:
        """Create base parish data structure."""
        return {
            "name": name,
            "extractor_used": self.extractor_name,
            "extraction_method": "api_endpoint",
        }

    def _add_url_data_from_api_item(self, parish_data: Dict[str, Any], item: Dict, base_url: str):
        """Add URL data from API item."""
        url_fields = ["url", "link", "website", "page_url"]
        for url_field in url_fields:
            if url_field in item:
                parish_data["url"] = urljoin(base_url, item[url_field])
                break

    def _add_contact_data_from_api_item(self, parish_data: Dict[str, Any], item: Dict):
        """Add contact information from API item."""
        # Add address
        address_fields = ["address", "location", "full_address"]
        for addr_field in address_fields:
            if addr_field in item:
                parish_data["address"] = item[addr_field]
                break

        # Add phone
        phone_fields = ["phone", "telephone", "contact_phone"]
        for phone_field in phone_fields:
            if phone_field in item:
                parish_data["phone"] = item[phone_field]
                break

    def _extract_parish_from_element(self, element, base_url: str, method: str) -> Optional[Dict[str, Any]]:
        """Extract parish data from a web element."""
        try:
            parish_data = {}

            # Get text content
            text = element.text.strip()
            if not text:
                return None

            parish_data["name"] = text

            # Get URL if it's a link
            if element.tag_name.lower() == "a":
                href = element.get_attribute("href")
                if href:
                    parish_data["url"] = urljoin(base_url, href)

            # Add extraction metadata
            parish_data.update(
                {
                    "extractor_used": self.extractor_name,
                    "extraction_method": method,
                    "element_tag": element.tag_name,
                    "element_classes": element.get_attribute("class"),
                }
            )

            return parish_data

        except Exception as e:
            logger.debug(f"🚀 Element extraction failed: {e}")
            return None

    def _validate_parish_data(self, parish_data: Dict[str, Any]) -> bool:
        """Validate that extracted data represents a real parish."""
        name = parish_data.get("name", "").lower()

        # Must have a name
        if not name or len(name.strip()) < 3:
            return False

        # Should contain parish indicators
        parish_indicators = [
            "parish",
            "church",
            "cathedral",
            "chapel",
            "mission",
            "saint",
            "st.",
            "holy",
            "blessed",
            "our lady",
            "sacred",
        ]

        has_indicator = any(indicator in name for indicator in parish_indicators)

        # Exclude obvious non - parishes
        exclusions = [
            "office",
            "department",
            "ministry",
            "bishop",
            "chancellor",
            "tribunal",
            "education",
            "finance",
            "human resources",
            "development",
            "communications",
            "vocations",
            "youth director",
            "home",
            "about us",
            "contact us",
            "news",
            "events",
            "calendar",
            "directions",
            "staff",
            "history",
            "donate",
            "volunteer",
        ]

        has_exclusion = any(term in name for term in exclusions)

        return has_indicator and not has_exclusion

    def _validate_and_deduplicate(self, parishes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and remove duplicate parishes."""
        validated = []
        seen = set()

        for parish in parishes:
            if self._validate_parish_data(parish):
                # Create unique key
                name_key = parish.get("name", "").lower().strip()
                url_key = parish.get("url", "")
                unique_key = f"{name_key}|{url_key}"

                if unique_key not in seen:
                    seen.add(unique_key)
                    validated.append(parish)

        return validated

    def _deduplicate_parishes(self, parishes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate parishes based on name and URL."""
        seen = set()
        unique = []

        for parish in parishes:
            name = parish.get("name", "").lower().strip()
            url = parish.get("url", "")
            key = f"{name}|{url}"

            if key not in seen:
                seen.add(key)
                unique.append(parish)

        return unique

    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about enhanced AI fallback extractions."""
        base_stats = {
            "extractor_name": self.extractor_name,
            "type": "enhanced_ai_fallback",
            "ai_enabled": self.ai_analyzer is not None,
            "profiles_enabled": self.profile_manager is not None,
            "description": ("Enhanced AI - powered fallback with JavaScript execution and network analysis"),
        }

        if self.profile_manager:
            profile_stats = self.profile_manager.get_profile_stats()
            base_stats.update(
                {
                    "available_profiles": profile_stats["total_profiles"],
                    "profile_strategies": profile_stats["strategy_distribution"],
                }
            )

        base_stats["capabilities"] = [
            "AI content analysis",
            "JavaScript execution engine",
            "Network traffic monitoring",
            "Diocese - specific profiles",
            "API endpoint discovery",
            "Dynamic content loading",
            "Custom selector generation",
            "Parish validation",
        ]

        return base_stats
