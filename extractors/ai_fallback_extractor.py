#!/usr/bin/env python3
"""
AI Fallback Extractor - The Last Resort for Failed Parish Extractions.

This extractor is called when all standard extraction methods fail.
It uses AI-powered content analysis to understand page structure and extract parishes.
"""

from typing import List, Dict, Optional, Any
from urllib.parse import urljoin
from selenium.webdriver.remote.webdriver import WebDriver

from core.logger import get_logger
from core.ai_content_analyzer import get_ai_content_analyzer
from extractors.base_extractor import BaseExtractor
from config import get_genai_api_key

logger = get_logger(__name__)


class AIFallbackExtractor(BaseExtractor):
    """AI-powered fallback extractor for when all other methods fail."""

    def __init__(self):
        """Initialize the AI fallback extractor."""
        super().__init__()
        self.extractor_name = "AIFallbackExtractor"

        # Initialize AI content analyzer
        genai_api_key = get_genai_api_key()
        if genai_api_key:
            self.ai_analyzer = get_ai_content_analyzer(genai_api_key)
            logger.info("🤖 AI Fallback Extractor initialized with GenAI")
        else:
            self.ai_analyzer = None
            logger.warning("🤖 AI Fallback Extractor initialized without GenAI (API key missing)")

    def can_extract(self, driver: WebDriver, url: str) -> bool:
        """
        This extractor can always attempt extraction as a fallback.
        However, it requires GenAI API to be configured.
        """
        if not self.ai_analyzer:
            logger.warning("🤖 AI Fallback Extractor disabled - missing GenAI API key")
            return False

        # Always return True - this is the fallback of last resort
        logger.info("🤖 AI Fallback Extractor: Ready to analyze failed extraction page")
        return True

    def extract(self, driver: WebDriver, diocese_name: str, url: str,
               max_parishes: int = None) -> List[Dict[str, Any]]:
        """
        Extract parishes using AI-powered content analysis.

        This method:
        1. Analyzes the page structure using AI
        2. Generates custom selectors based on content
        3. Applies those selectors to extract parish data
        4. Validates and returns results
        """
        logger.info(f"🤖 AI Fallback Extraction starting for {diocese_name}")
        logger.info(f"    📊 Target: up to {max_parishes or 'unlimited'} parishes")
        logger.info(f"    🌐 URL: {url}")

        if not self.ai_analyzer:
            logger.error("🤖 AI Fallback Extractor not properly initialized")
            return []

        try:
            # Step 1: AI-powered content analysis
            logger.info("🤖 Step 1: Analyzing page content with AI...")
            analysis_result = self.ai_analyzer.analyze_failed_extraction(
                driver, diocese_name, url
            )

            confidence = analysis_result.get('confidence', 0.0)
            strategy = analysis_result.get('extraction_strategy', 'unknown')
            parishes = analysis_result.get('parish_data', [])
            insights = analysis_result.get('ai_insights', [])

            logger.info(f"🤖 AI Analysis Results:")
            logger.info(f"    📊 Confidence: {confidence:.2f}")
            logger.info(f"    🔧 Strategy: {strategy}")
            logger.info(f"    ⛪ Parishes found: {len(parishes)}")

            if insights:
                logger.info(f"    💡 AI Insights:")
                for insight in insights[:3]:  # Log top 3 insights
                    logger.info(f"      • {insight}")

            # Step 2: Validate and enrich parish data
            validated_parishes = []
            for parish in parishes:
                if self._validate_ai_parish(parish):
                    enriched_parish = self._enrich_parish_data(parish, driver, url)
                    validated_parishes.append(enriched_parish)

            # Step 3: Apply max_parishes limit
            if max_parishes and len(validated_parishes) > max_parishes:
                validated_parishes = validated_parishes[:max_parishes]
                logger.info(f"🤖 Limited results to {max_parishes} parishes")

            # Step 4: Log extraction results
            if validated_parishes:
                logger.info(f"🤖 ✅ AI Fallback Extraction successful!")
                logger.info(f"    📊 Final count: {len(validated_parishes)} parishes")
                logger.info(f"    🎯 Success rate: {len(validated_parishes)/len(parishes)*100:.1f}%" if parishes else "N/A")

                # Log sample results
                for i, parish in enumerate(validated_parishes[:3], 1):
                    logger.info(f"    {i}. {parish.get('name', 'N/A')}")
                    if parish.get('url'):
                        logger.info(f"       🔗 {parish['url']}")
            else:
                logger.warning("🤖 ❌ AI Fallback Extraction found no valid parishes")
                logger.warning(f"    💭 AI suggested strategy: {strategy}")
                logger.warning(f"    📊 AI confidence was: {confidence:.2f}")

            return validated_parishes

        except Exception as e:
            logger.error(f"🤖 AI Fallback Extraction failed: {e}", exc_info=True)
            return []

    def _validate_ai_parish(self, parish: Dict[str, Any]) -> bool:
        """Validate an AI-extracted parish data structure."""
        # Must have a name
        name = parish.get('name', '').strip()
        if not name or len(name) < 3:
            return False

        # Should look like a parish name
        name_lower = name.lower()
        parish_indicators = [
            'parish', 'church', 'cathedral', 'chapel', 'mission',
            'saint', 'st.', 'holy', 'blessed', 'our lady', 'sacred'
        ]

        has_indicator = any(indicator in name_lower for indicator in parish_indicators)

        # Exclude administrative entities
        exclusion_terms = [
            'office', 'department', 'ministry', 'bishop', 'chancellor',
            'tribunal', 'education', 'finance', 'human resources',
            'development', 'communications', 'vocations', 'youth director',
            'home', 'about us', 'contact us', 'news', 'events', 'calendar',
            'directions', 'staff', 'history'
        ]

        has_exclusion = any(term in name_lower for term in exclusion_terms)

        is_valid = has_indicator and not has_exclusion

        if not is_valid:
            logger.debug(f"🤖 Rejected parish candidate: '{name}' (indicator: {has_indicator}, exclusion: {has_exclusion})")

        return is_valid

    def _enrich_parish_data(self, parish: Dict[str, Any], driver: WebDriver, base_url: str) -> Dict[str, Any]:
        """Enrich AI-extracted parish data with additional information."""
        enriched = parish.copy()

        # Ensure URL is absolute
        if 'url' in enriched and enriched['url']:
            enriched['url'] = urljoin(base_url, enriched['url'])

        # Add extraction metadata
        enriched.update({
            'extractor_used': self.extractor_name,
            'extraction_method': 'ai_content_analysis',
            'ai_extracted': True,
            'validation_passed': True
        })

        # Try to get additional data if we have a parish URL
        if enriched.get('url') and not enriched.get('address'):
            try:
                # Navigate to parish page to get more details
                original_url = driver.current_url
                driver.get(enriched['url'])

                # Quick extraction of common elements
                self._extract_contact_info(driver, enriched)

                # Return to original page
                driver.get(original_url)

            except Exception as e:
                logger.debug(f"🤖 Failed to enrich parish data: {e}")

        return enriched

    def _extract_contact_info(self, driver: WebDriver, parish: Dict[str, Any]):
        """Extract contact information from parish page."""
        try:
            page_text = driver.find_element("tag name", "body").text.lower()

            # Extract address if not already present
            if not parish.get('address'):
                import re
                address_patterns = [
                    r'\d+[^,\n]*(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|circle|cir)[^,\n]*',
                    r'\d+[^\n]*(?:suite|ste|unit|apt)[^\n]*'
                ]

                for pattern in address_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        parish['address'] = match.group().strip()
                        break

            # Extract phone if not already present
            if not parish.get('phone'):
                phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
                phone_match = re.search(phone_pattern, page_text)
                if phone_match:
                    parish['phone'] = phone_match.group().strip()

        except Exception as e:
            logger.debug(f"🤖 Contact info extraction failed: {e}")

    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about AI fallback extractions."""
        return {
            'extractor_name': self.extractor_name,
            'type': 'ai_fallback',
            'ai_enabled': self.ai_analyzer is not None,
            'description': 'AI-powered fallback extractor for failed standard extractions',
            'capabilities': [
                'DOM structure analysis',
                'Custom selector generation',
                'XPath expression creation',
                'Content pattern recognition',
                'Parish validation'
            ]
        }