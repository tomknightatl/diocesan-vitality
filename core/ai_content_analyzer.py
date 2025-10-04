#!/usr/bin/env python3
"""
AI-Powered Content Analysis for Failed Parish Extractions.

When standard extraction methods fail, this system uses GenAI to:
1. Analyze the DOM structure of parish directory pages
2. Identify parish-related content patterns
3. Generate custom CSS selectors and XPath expressions
4. Extract parish data using AI-generated strategies
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import google.generativeai as genai
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from core.circuit_breaker import circuit_breaker
from core.logger import get_logger

logger = get_logger(__name__)


class AIContentAnalyzer:
    """AI-powered content analyzer for failed parish extractions."""

    def __init__(self, genai_api_key: str):
        """Initialize the AI content analyzer."""
        self.genai_api_key = genai_api_key
        genai.configure(api_key=genai_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

        # Common parish indicators for validation
        self.parish_indicators = [
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
            "sacred heart",
            "catholic church",
            "mass times",
            "contact",
            "address",
            "phone",
        ]

        logger.info("🤖 AI Content Analyzer initialized")

    @circuit_breaker("ai_content_analysis")
    def analyze_failed_extraction(self, driver: WebDriver, diocese_name: str, url: str) -> Dict[str, Any]:
        """
        Analyze a parish directory page when standard extraction fails.

        Returns:
            - custom_selectors: AI-generated CSS selectors
            - extraction_strategy: Recommended approach
            - parish_data: Any parishes found using AI analysis
            - confidence: Analysis confidence score
        """
        try:
            logger.info(f"🤖 Starting AI content analysis for {diocese_name}")

            # Step 1: Analyze page structure
            dom_analysis = self._analyze_dom_structure(driver)

            # Step 2: Extract relevant content snippets
            content_snippets = self._extract_content_snippets(driver)

            # Step 3: Generate AI analysis prompt
            analysis_result = self._generate_ai_analysis(diocese_name, url, dom_analysis, content_snippets)

            # Step 4: Apply AI-generated selectors
            parish_data = self._apply_ai_selectors(driver, analysis_result, url)

            logger.info(f"🤖 AI analysis completed: found {len(parish_data)} parishes")

            return {
                "custom_selectors": analysis_result.get("selectors", []),
                "extraction_strategy": analysis_result.get("strategy", "unknown"),
                "parish_data": parish_data,
                "confidence": analysis_result.get("confidence", 0.0),
                "ai_insights": analysis_result.get("insights", []),
            }

        except Exception as e:
            logger.error(f"🤖 AI content analysis failed: {e}")
            return {
                "custom_selectors": [],
                "extraction_strategy": "failed",
                "parish_data": [],
                "confidence": 0.0,
                "error": str(e),
            }

    def _analyze_dom_structure(self, driver: WebDriver) -> Dict[str, Any]:
        """Analyze the DOM structure for parish-related patterns."""
        try:
            # Get page structure overview
            structure = {
                "title": driver.title,
                "url": driver.current_url,
                "links_count": len(driver.find_elements(By.TAG_NAME, "a")),
                "parish_related_elements": [],
                "cms_indicators": [],
                "layout_type": "unknown",
            }

            # Look for parish-related elements
            parish_elements = []
            for selector in [
                "a[href*='parish']",
                "[class*='parish']",
                "[id*='parish']",
                "a[href*='church']",
                "[class*='church']",
                "[id*='church']",
                ".content a",
                ".main a",
                "#content a",
                ".parish-list a",
            ]:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        parish_elements.extend(
                            [
                                {
                                    "selector": selector,
                                    "count": len(elements),
                                    "sample_texts": [elem.text.strip()[:50] for elem in elements[:3] if elem.text.strip()],
                                }
                            ]
                        )
                except:
                    continue

            structure["parish_related_elements"] = parish_elements

            # Detect CMS patterns
            cms_indicators = []
            cms_patterns = {
                "wordpress": [".wp-content", ".wp-block", "#wp-content"],
                "drupal": [".region-content", ".field-item", "#drupal"],
                "squarespace": [".sqs-block", ".content-wrapper"],
                "custom": [".container", ".content", "#main"],
            }

            for cms, selectors in cms_patterns.items():
                for selector in selectors:
                    try:
                        if driver.find_elements(By.CSS_SELECTOR, selector):
                            cms_indicators.append(cms)
                            break
                    except:
                        continue

            structure["cms_indicators"] = cms_indicators

            return structure

        except Exception as e:
            logger.warning(f"🤖 DOM structure analysis failed: {e}")
            return {"error": str(e)}

    def _extract_content_snippets(self, driver: WebDriver) -> List[str]:
        """Extract relevant content snippets for AI analysis."""
        snippets = []

        try:
            # Check if page has dynamic loading indicators
            loading_indicators = ["loading", "just a moment", "please wait", "loading content", "spinner", "loader"]

            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            has_loading = any(indicator in page_text for indicator in loading_indicators)

            if has_loading:
                logger.info("🤖 Detected dynamic loading, waiting for content...")
                # Wait for dynamic content to load
                import time

                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.support.ui import WebDriverWait

                # Wait up to 10 seconds for content to appear
                wait = WebDriverWait(driver, 10)
                try:
                    # Wait for body text to change (indicating content loaded)
                    initial_length = len(page_text)
                    time.sleep(5)  # Give JavaScript time to execute

                    # Re-execute JavaScript to ensure full loading
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)

                    # Check if content has changed
                    new_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                    if len(new_text) > initial_length * 1.5:  # Content significantly expanded
                        logger.info("🤖 Dynamic content loaded successfully")
                    else:
                        logger.warning("🤖 Dynamic content may not have loaded completely")
                except:
                    logger.warning("🤖 Dynamic loading wait timeout")

            # Get main content areas
            content_selectors = [
                "main",
                ".main",
                "#main",
                ".content",
                "#content",
                ".container",
                ".wrapper",
                "article",
                ".article",
                ".parish-list",
                ".church-list",
                ".directory",
                # WordPress-specific selectors
                ".entry-content",
                ".post-content",
                ".page-content",
                # Common CMS selectors
                ".vc_column",
                ".elementor-widget",
                ".et_pb_text",
            ]

            for selector in content_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements[:2]:  # Limit to first 2 matches
                        text = elem.text.strip()
                        if len(text) > 50 and any(indicator.lower() in text.lower() for indicator in self.parish_indicators):
                            snippets.append(text[:1000])  # Limit snippet length
                except:
                    continue

            # Also get page source sample for structure analysis
            try:
                page_source = driver.page_source
                # Extract a relevant portion of HTML
                if "parish" in page_source.lower() or "church" in page_source.lower():
                    # Find the most relevant section
                    soup_like_content = self._extract_relevant_html_section(page_source)
                    if soup_like_content:
                        snippets.append(f"HTML_STRUCTURE: {soup_like_content}")
            except:
                pass

            return snippets[:5]  # Limit total snippets

        except Exception as e:
            logger.warning(f"🤖 Content snippet extraction failed: {e}")
            return []

    def _extract_relevant_html_section(self, html_source: str) -> str:
        """Extract the most relevant HTML section containing parish information."""
        # Simple heuristic to find parish-related HTML sections
        html_lower = html_source.lower()

        # Find sections with high parish keyword density
        parish_keywords = ["parish", "church", "catholic", "saint", "st."]

        # Look for div or section tags with parish content
        patterns = [
            r'<div[^>]*class="[^"]*parish[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*church[^"]*"[^>]*>.*?</div>',
            r"<main[^>]*>.*?</main>",
            r"<section[^>]*>.*?</section>",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html_source, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if len(match) < 2000:  # Reasonable size
                    keyword_count = sum(1 for keyword in parish_keywords if keyword in match.lower())
                    if keyword_count >= 2:
                        return match[:1500]  # Truncate for API limits

        return ""

    def _generate_ai_analysis(
        self, diocese_name: str, url: str, dom_analysis: Dict, content_snippets: List[str]
    ) -> Dict[str, Any]:
        """Generate AI analysis of the page structure and content."""

        prompt = f"""
You are an expert web scraper analyzing a Catholic diocese's parish directory page that has defeated 3 standard extraction methods.

DIOCESE: {diocese_name}
URL: {url}

DOM STRUCTURE ANALYSIS:
{json.dumps(dom_analysis, indent=2)}

CONTENT SNIPPETS (actual page content):
{chr(10).join(content_snippets[:3])}

CRITICAL INSTRUCTIONS:
Your job is to find ALL parishes on this page. Standard methods (navigation extraction, generic
extraction, table extraction) have ALL FAILED.

SUCCESSFUL EXTRACTION EXAMPLES:
1. Accordion/Tab Navigation: If parishes are in collapsible sections or tabs, look for:
   - Buttons with data-toggle, aria-expanded, or onclick handlers
   - Tab panels with class names like "tab-pane", "accordion-item"
   - Selectors: "button[data-toggle]", ".accordion-header", "[role='tab']"

2. Embedded Maps/JavaScript Lists: If parishes load via JavaScript:
   - Look for data attributes: data-parishes, data-locations, data-markers
   - Script tags with JSON data: <script type="application/json">
   - Selectors: "[data-parishes]", "script[type='application/json']"

3. Navigation Dropdowns: If parishes are in menu dropdowns:
   - Hover menus: .dropdown-menu, .submenu, .nav-dropdown
   - Hidden until hover: display:none, visibility:hidden
   - Selectors: ".menu-item a[href*='parish']", "nav .dropdown a"

4. Iframe Embedded: If directory is in an iframe:
   - Check for: <iframe src="...parishfinder...">
   - Strategy: "iframe_extraction" with iframe URL

5. PDF/Document Links: If directory is a downloadable file:
   - Look for: .pdf links, "Download Parish Directory"
   - Strategy: "pdf_extraction" with document URL

ANALYSIS REQUIREMENTS:
1. SELECTORS: Provide 8-12 highly specific CSS selectors that target ACTUAL elements you see
   in the DOM/content
2. XPATH: Include XPath expressions for complex cases (contains(), following-sibling, etc.)
3. STRATEGY: Choose the BEST match:
   - "link_extraction_and_navigation_based" (if parishes are in dropdowns/menus)
   - "accordion_tab_extraction" (if in collapsible sections)
   - "javascript_data_attribute_extraction" (if in data-* attributes)
   - "iframe_extraction" (if in embedded iframe)
   - "pdf_extraction" (if in downloadable PDF)
   - "table_extraction" (if in HTML tables)
   - "text_parsing_with_regex" (if plain text list)
4. CONFIDENCE: Be honest (0.0-1.0). If unsure, say 0.3-0.5
5. SPECIFIC_EXTRACTION_STEPS: Provide step-by-step instructions

Return JSON (use ACTUAL selectors from the page, not generic examples):
{{
    "selectors": [
        "ACTUAL selector from DOM",
        "ANOTHER actual selector",
        "Be SPECIFIC to THIS page"
    ],
    "xpath_expressions": [
        "//element[@actual-attribute='value']"
    ],
    "strategy": "best_matching_strategy_from_list_above",
    "confidence": 0.7,
    "insights": [
        "SPECIFIC observation about THIS page",
        "What I actually see in the DOM/content"
    ],
    "parish_patterns": [
        "Actual pattern from this page"
    ],
    "specific_extraction_steps": [
        "Step 1: Find element with selector X",
        "Step 2: Extract Y from element",
        "Step 3: Parse Z"
    ]
}}

REMEMBER: We need ACTUAL working selectors, not generic examples. Analyze the DOM STRUCTURE
and CONTENT SNIPPETS provided above.
"""

        try:
            response = self.model.generate_content(prompt)

            # Parse JSON response
            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return analysis
            else:
                logger.warning("🤖 AI response not in expected JSON format")
                return {
                    "selectors": [],
                    "strategy": "failed_parsing",
                    "confidence": 0.0,
                    "insights": ["Failed to parse AI response"],
                    "raw_response": response.text,
                }

        except Exception as e:
            logger.error(f"🤖 AI analysis generation failed: {e}")
            return {"selectors": [], "strategy": "ai_failed", "confidence": 0.0, "error": str(e)}

    def _apply_ai_selectors(self, driver: WebDriver, analysis: Dict, base_url: str) -> List[Dict[str, Any]]:
        """Apply AI-generated selectors to extract parish data."""
        parishes = []

        try:
            # Try CSS selectors first
            for selector in analysis.get("selectors", []):
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        parish_data = self._extract_parish_from_element(elem, base_url)
                        if parish_data and self._validate_parish_data(parish_data):
                            parishes.append(parish_data)
                except Exception as e:
                    logger.debug(f"🤖 Selector '{selector}' failed: {e}")
                    continue

            # Try XPath expressions
            for xpath in analysis.get("xpath_expressions", []):
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for elem in elements:
                        parish_data = self._extract_parish_from_element(elem, base_url)
                        if parish_data and self._validate_parish_data(parish_data):
                            parishes.append(parish_data)
                except Exception as e:
                    logger.debug(f"🤖 XPath '{xpath}' failed: {e}")
                    continue

            # Remove duplicates based on name
            unique_parishes = []
            seen_names = set()
            for parish in parishes:
                name_key = parish.get("name", "").lower().strip()
                if name_key and name_key not in seen_names:
                    seen_names.add(name_key)
                    unique_parishes.append(parish)

            return unique_parishes[:20]  # Limit results

        except Exception as e:
            logger.error(f"🤖 Failed to apply AI selectors: {e}")
            return []

    def _extract_parish_from_element(self, element, base_url: str) -> Optional[Dict[str, Any]]:
        """Extract parish data from a web element."""
        try:
            parish_data = {}

            # Get text content
            text = element.text.strip()
            if not text:
                return None

            # Extract name
            parish_data["name"] = text

            # Get URL if it's a link
            if element.tag_name.lower() == "a":
                href = element.get_attribute("href")
                if href:
                    parish_data["url"] = urljoin(base_url, href)

            # Look for additional data in parent/sibling elements
            try:
                parent = element.find_element(By.XPATH, "..")
                parent_text = parent.text.strip()

                # Extract address patterns
                address_pattern = (
                    r"\d+[^,\n]*(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Circle|Cir)[^,\n]*"
                )
                address_match = re.search(address_pattern, parent_text, re.IGNORECASE)
                if address_match:
                    parish_data["address"] = address_match.group().strip()

                # Extract phone patterns
                phone_pattern = r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
                phone_match = re.search(phone_pattern, parent_text)
                if phone_match:
                    parish_data["phone"] = phone_match.group().strip()
            except:
                pass

            return parish_data

        except Exception as e:
            logger.debug(f"🤖 Element extraction failed: {e}")
            return None

    def _validate_parish_data(self, parish_data: Dict[str, Any]) -> bool:
        """Validate that extracted data represents a real parish."""
        name = parish_data.get("name", "").lower()

        # Must have a name
        if not name or len(name.strip()) < 3:
            return False

        # Should contain parish indicators
        has_parish_indicator = any(
            indicator in name
            for indicator in [
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
        )

        # Exclude obvious non-parishes
        exclusion_terms = [
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
            "youth",
            "home",
            "about",
            "contact",
            "news",
            "events",
            "calendar",
        ]

        has_exclusion = any(term in name for term in exclusion_terms)

        return has_parish_indicator and not has_exclusion


def get_ai_content_analyzer(genai_api_key: str) -> AIContentAnalyzer:
    """Factory function to create AI content analyzer."""
    return AIContentAnalyzer(genai_api_key)
