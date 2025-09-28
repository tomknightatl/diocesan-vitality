#!/usr/bin/env python3
"""
Enhanced AI Fallback Extractor with JavaScript Execution and Network Analysis.

This advanced extractor combines:
1. AI-powered content analysis
2. JavaScript execution engine for dynamic content
3. Network traffic analysis for API discovery
4. Diocese-specific profiles for optimized extraction
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

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
    Enhanced AI-powered fallback extractor with advanced dynamic content capabilities.

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

    def extract(self, driver: WebDriver, diocese_name: str, url: str, max_parishes: int = None) -> List[Dict[str, Any]]:
        """
        Enhanced extraction using AI analysis, JavaScript execution, and profiles.

        This method implements a sophisticated multi-stage approach:
        1. Check for diocese-specific profiles
        2. Use JavaScript engine for dynamic content loading
        3. Apply AI analysis with network traffic monitoring
        4. Extract and validate parish data
        5. Update profiles based on results
        """
        logger.info(f"🚀 Enhanced AI Fallback Extraction starting for {diocese_name}")
        logger.info(f"    📊 Target: up to {max_parishes or 'unlimited'} parishes")
        logger.info(f"    🌐 URL: {url}")

        if not self.ai_analyzer:
            logger.error("🚀 Enhanced AI Fallback Extractor not properly initialized")
            return []

        try:
            # Step 1: Check for diocese-specific profile
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]

            profile = self.profile_manager.get_profile(url, diocese_name)
            if profile:
                logger.info(f"🎯 Using diocese profile: {profile.strategy_type} strategy")
                parishes = self._extract_with_profile(driver, diocese_name, url, profile, max_parishes)
                if parishes:
                    self.profile_manager.update_profile_success(domain, profile.strategy_type, True)
                    return parishes
                else:
                    self.profile_manager.update_profile_success(domain, profile.strategy_type, False)
                    logger.warning("🎯 Profile-based extraction failed, falling back to dynamic analysis")

            # Step 2: Dynamic content loading with JavaScript engine
            js_engine = get_dynamic_content_engine(driver)
            loading_result = js_engine.wait_for_dynamic_content(diocese_name, timeout=20)

            logger.info(f"🚀 Dynamic loading results:")
            logger.info(f"    📊 Content loaded: {loading_result['content_loaded']}")
            logger.info(f"    🔧 Method used: {loading_result['method_used']}")
            logger.info(f"    ⏱️ Loading time: {loading_result['loading_time']:.2f}s")
            logger.info(f"    🌐 API endpoints found: {len(loading_result['api_endpoints'])}")

            # Step 3: AI analysis with enhanced context
            logger.info("🤖 Running enhanced AI content analysis...")
            ai_result = self.ai_analyzer.analyze_failed_extraction(driver, diocese_name, url)

            # Merge results from dynamic loading and AI analysis
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

            # Step 4: Try API endpoints if discovered
            if loading_result["api_endpoints"]:
                logger.info(f"🌐 Attempting API extraction from {len(loading_result['api_endpoints'])} endpoints")
                api_parishes = self._extract_from_api_endpoints(loading_result["api_endpoints"], url)
                all_parish_data.extend(api_parishes)

            # Step 5: Validate and deduplicate results
            validated_parishes = self._validate_and_deduplicate(all_parish_data)

            # Step 6: Create/update profile based on results
            if not profile:  # Only create new profiles if none exists
                if validated_parishes:
                    # Successful extraction - create confidence profile
                    new_profile = self.profile_manager.create_custom_profile(domain, ai_result)
                    if new_profile:
                        logger.info(f"🎯 Created high-confidence profile for {domain} based on successful extraction")
                elif ai_result.get("confidence", 0.0) >= 0.6 and ai_result.get("extraction_strategy"):
                    # Failed extraction but high AI confidence - create learning profile
                    learning_profile = self.profile_manager.create_custom_profile(domain, ai_result)
                    if learning_profile:
                        logger.info(
                            f"🎯 Created learning profile for {domain} - Strategy: {ai_result.get('extraction_strategy')} (confidence: {ai_result.get('confidence', 0.0):.2f})"
                        )
                        logger.info(f"    💡 Profile will be used for future extractions to improve success rate")

            # Step 7: Apply max_parishes limit
            if max_parishes and len(validated_parishes) > max_parishes:
                validated_parishes = validated_parishes[:max_parishes]
                logger.info(f"🚀 Limited results to {max_parishes} parishes")

            # Step 8: Log final results
            if validated_parishes:
                logger.info(f"🚀 ✅ Enhanced AI Fallback Extraction successful!")
                logger.info(f"    📊 Final count: {len(validated_parishes)} parishes")
                logger.info(
                    f"    🎯 Success methods: JS={len(loading_result.get('parish_elements', []))}, AI={len(ai_result.get('parish_data', []))}, API={len(api_parishes) if 'api_parishes' in locals() else 0}"
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

            return validated_parishes

        except Exception as e:
            logger.error(f"🚀 Enhanced AI Fallback Extraction failed: {e}", exc_info=True)
            return []

    def _extract_with_profile(
        self, driver: WebDriver, diocese_name: str, url: str, profile, max_parishes: int
    ) -> List[Dict[str, Any]]:
        """Extract parishes using diocese-specific profile."""
        try:
            logger.info(f"🎯 Applying profile strategy: {profile.strategy_type}")

            parishes = []

            # Apply profile-specific waiting strategy
            if profile.javascript_required:
                js_engine = get_dynamic_content_engine(driver)
                loading_result = js_engine.wait_for_dynamic_content(diocese_name, profile.wait_time)

                if loading_result["content_loaded"]:
                    logger.info(f"🎯 Dynamic content loaded using profile settings")
                else:
                    logger.warning(f"🎯 Profile dynamic loading failed, continuing with static extraction")

            # Try profile custom selectors
            if profile.custom_selectors:
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

            # Try profile button clicks if specified
            if profile.button_clicks and profile.interaction_required:
                for button_selector in profile.button_clicks:
                    try:
                        buttons = driver.find_elements("css selector", button_selector)
                        for button in buttons:
                            if button.is_displayed() and button.is_enabled():
                                logger.info(f"🎯 Clicking profile button: {button_selector}")
                                button.click()
                                time.sleep(2)

                                # Re-try selectors after interaction
                                for selector in profile.custom_selectors[:3]:  # Try top 3
                                    try:
                                        elements = driver.find_elements("css selector", selector)
                                        for elem in elements:
                                            parish_data = self._extract_parish_from_element(elem, url, "profile_interaction")
                                            if parish_data and self._validate_parish_data(parish_data):
                                                parishes.append(parish_data)
                                    except:
                                        continue

                                break  # Only click first available button
                    except Exception as e:
                        logger.debug(f"🎯 Profile button click '{button_selector}' failed: {e}")
                        continue

            # Remove duplicates
            unique_parishes = self._deduplicate_parishes(parishes)

            logger.info(f"🎯 Profile extraction found {len(unique_parishes)} parishes")
            return unique_parishes

        except Exception as e:
            logger.error(f"🎯 Profile-based extraction failed: {e}")
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
                            logger.debug(f"🌐 API endpoint {endpoint} returned non-JSON data")

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
            # Look for name field
            name = None
            for name_field in ["name", "title", "parish_name", "church_name"]:
                if name_field in item:
                    name = item[name_field]
                    break

            if not name:
                return None

            parish_data = {"name": name, "extractor_used": self.extractor_name, "extraction_method": "api_endpoint"}

            # Look for URL field
            for url_field in ["url", "link", "website", "page_url"]:
                if url_field in item:
                    parish_data["url"] = urljoin(base_url, item[url_field])
                    break

            # Look for address field
            for addr_field in ["address", "location", "full_address"]:
                if addr_field in item:
                    parish_data["address"] = item[addr_field]
                    break

            # Look for phone field
            for phone_field in ["phone", "telephone", "contact_phone"]:
                if phone_field in item:
                    parish_data["phone"] = item[phone_field]
                    break

            return parish_data if self._validate_parish_data(parish_data) else None

        except Exception as e:
            logger.debug(f"🌐 Failed to extract from API item: {e}")
            return None

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

        # Exclude obvious non-parishes
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
            "description": "Enhanced AI-powered fallback with JavaScript execution and network analysis",
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
            "Diocese-specific profiles",
            "API endpoint discovery",
            "Dynamic content loading",
            "Custom selector generation",
            "Parish validation",
        ]

        return base_stats
