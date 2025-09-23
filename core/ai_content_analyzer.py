#!/usr/bin/env python3
"""
AI - Powered Content Analysis for Failed Parish Extractions.

When standard extraction methods fail, this system uses GenAI to:
1. Analyze the DOM structure of parish directory pages
2. Identify parish - related content patterns
3. Generate custom CSS selectors and XPath expressions
4. Extract parish data using AI - generated strategies
"""

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import google.generativeai as genai
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from core.circuit_breaker import circuit_breaker
from core.logger import get_logger

logger = get_logger(__name__)


class AIContentAnalyzer:
    """AI - powered content analyzer for failed parish extractions."""

    def __init__(self, genai_api_key: str):
        """Initialize the AI content analyzer."""
        self.genai_api_key = genai_api_key
        genai.configure(api_key=genai_api_key)
        self.model = genai.GenerativeModel("gemini - 1.5 - flash")

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
            - custom_selectors: AI - generated CSS selectors
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

            # Step 4: Apply AI - generated selectors
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
        """Analyze the DOM structure for parish - related patterns."""
        try:
            structure = self._get_page_structure_overview(driver)
            structure["parish_related_elements"] = self._find_parish_related_elements(driver)
            structure["cms_indicators"] = self._detect_cms_indicators(driver)
            return structure

        except Exception as e:
            logger.warning(f"🤖 DOM structure analysis failed: {e}")
            return {"error": str(e)}

    def _get_page_structure_overview(self, driver: WebDriver) -> Dict[str, Any]:
        """Get basic page structure overview."""
        return {
            "title": driver.title,
            "url": driver.current_url,
            "links_count": len(driver.find_elements(By.TAG_NAME, "a")),
            "parish_related_elements": [],
            "cms_indicators": [],
            "layout_type": "unknown",
        }

    def _find_parish_related_elements(self, driver: WebDriver) -> List[Dict[str, Any]]:
        """Find elements related to parishes and churches."""
        parish_selectors = [
            "a[href*='parish']",
            "[class*='parish']",
            "[id*='parish']",
            "a[href*='church']",
            "[class*='church']",
            "[id*='church']",
            ".content a",
            ".main a",
            "#content a",
            ".parish - list a",
        ]

        parish_elements = []
        for selector in parish_selectors:
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
            except (NoSuchElementException, WebDriverException):
                continue

        return parish_elements

    def _detect_cms_indicators(self, driver: WebDriver) -> List[str]:
        """Detect content management system indicators."""
        cms_patterns = {
            "wordpress": [".wp - content", ".wp - block", "#wp - content"],
            "drupal": [".region - content", ".field - item", "#drupal"],
            "squarespace": [".sqs - block", ".content - wrapper"],
            "custom": [".container", ".content", "#main"],
        }

        cms_indicators = []
        for cms, selectors in cms_patterns.items():
            for selector in selectors:
                try:
                    if driver.find_elements(By.CSS_SELECTOR, selector):
                        cms_indicators.append(cms)
                        break
                except (NoSuchElementException, WebDriverException):
                    continue

        return cms_indicators

    def _check_and_wait_for_dynamic_content(self, driver: WebDriver) -> None:
        """Check for dynamic loading indicators and wait for content if needed."""
        loading_indicators = [
            "loading",
            "just a moment",
            "please wait",
            "loading content",
            "spinner",
            "loader",
        ]

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        has_loading = any(indicator in page_text for indicator in loading_indicators)

        if not has_loading:
            return

        logger.info("🤖 Detected dynamic loading, waiting for content...")
        import time

        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(driver, 10)
        try:
            initial_length = len(page_text)
            time.sleep(5)  # Give JavaScript time to execute

            # Re - execute JavaScript to ensure full loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Check if content has changed
            new_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            if len(new_text) > initial_length * 1.5:  # Content significantly expanded
                logger.info("🤖 Dynamic content loaded successfully")
            else:
                logger.warning("🤖 Dynamic content may not have loaded completely")
        except (TimeoutException, WebDriverException):
            logger.warning("🤖 Dynamic loading wait timeout")

    def _get_content_selectors(self) -> List[str]:
        """Get list of CSS selectors for main content areas."""
        return [
            "main",
            ".main",
            "#main",
            ".content",
            "#content",
            ".container",
            ".wrapper",
            "article",
            ".article",
            ".parish - list",
            ".church - list",
            ".directory",
            # WordPress - specific selectors
            ".entry - content",
            ".post - content",
            ".page - content",
            # Common CMS selectors
            ".vc_column",
            ".elementor - widget",
            ".et_pb_text",
        ]

    def _extract_text_snippets_from_selectors(self, driver: WebDriver) -> List[str]:
        """Extract text snippets from content areas using CSS selectors."""
        snippets = []
        content_selectors = self._get_content_selectors()

        for selector in content_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements[:2]:  # Limit to first 2 matches
                    text = elem.text.strip()
                    if len(text) > 50 and any(indicator.lower() in text.lower() for indicator in self.parish_indicators):
                        snippets.append(text[:1000])  # Limit snippet length
            except (NoSuchElementException, WebDriverException):
                continue

        return snippets

    def _extract_html_structure_snippet(self, driver: WebDriver) -> List[str]:
        """Extract HTML structure snippet if it contains parish - related content."""
        snippets = []
        try:
            page_source = driver.page_source
            # Extract a relevant portion of HTML
            if "parish" in page_source.lower() or "church" in page_source.lower():
                # Find the most relevant section
                soup_like_content = self._extract_relevant_html_section(page_source)
                if soup_like_content:
                    snippets.append(f"HTML_STRUCTURE: {soup_like_content}")
        except Exception:
            pass
        return snippets

    def _extract_content_snippets(self, driver: WebDriver) -> List[str]:
        """Extract relevant content snippets for AI analysis."""
        try:
            # Check and wait for dynamic content
            self._check_and_wait_for_dynamic_content(driver)

            # Extract text snippets from content areas
            snippets = self._extract_text_snippets_from_selectors(driver)

            # Add HTML structure snippet if relevant
            snippets.extend(self._extract_html_structure_snippet(driver))

            return snippets[:5]  # Limit total snippets

        except Exception as e:
            logger.warning(f"🤖 Content snippet extraction failed: {e}")
            return []

    def _extract_relevant_html_section(self, html_source: str) -> str:
        """Extract the most relevant HTML section containing parish information."""
        # Simple heuristic to find parish - related HTML sections
        html_source.lower()

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
        self,
        diocese_name: str,
        url: str,
        dom_analysis: Dict,
        content_snippets: List[str],
    ) -> Dict[str, Any]:
        """Generate AI analysis of the page structure and content."""

        prompt = f"""
You are an expert web scraper analyzing a Catholic diocese's parish directory page that failed standard extraction methods.

DIOCESE: {diocese_name}
URL: {url}

DOM STRUCTURE ANALYSIS:
{json.dumps(dom_analysis, indent=2)}

CONTENT SNIPPETS:
{chr(10).join(content_snippets)}

Your task is to analyze this page and provide:

1. CUSTOM_SELECTORS: Generate 5 - 8 CSS selectors that would likely capture parish links/information
2. EXTRACTION_STRATEGY: Recommend the best approach (links, text - parsing, table - extraction, etc.)
3. CONFIDENCE: Rate your confidence (0.0 - 1.0) in the suggested approach
4. INSIGHTS: Key observations about the page structure

Focus on finding:
- Parish names (e.g., "St. Mary", "Holy Trinity Parish")
- Parish links or detail pages
- Contact information (addresses, phone numbers)
- Mass times or schedules

Return your analysis as JSON:
{{
    "selectors": [
        "a[href*='parish']",
        ".parish - name a",
        "// add more custom selectors"
    ],
    "xpath_expressions": [
        "//a[contains(text(), 'St.')]",
        "//a[contains(text(), 'Parish')]"
    ],
    "strategy": "link_extraction|text_parsing|table_extraction|navigation_based",
    "confidence": 0.8,
    "insights": [
        "Page uses WordPress structure",
        "Parishes listed in main content area",
        "Each parish has a dedicated link"
    ],
    "parish_patterns": [
        "Parish names follow 'Saint [Name] Parish' format",
        "Links contain '/parish/' in URL"
    ]
}}

Be specific and actionable. Focus on elements that actually exist on this page.
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
            return {
                "selectors": [],
                "strategy": "ai_failed",
                "confidence": 0.0,
                "error": str(e),
            }

    def _extract_parishes_with_css_selectors(self, driver: WebDriver, analysis: Dict, base_url: str) -> List[Dict[str, Any]]:
        """Extract parishes using CSS selectors from AI analysis."""
        parishes = []
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
        return parishes

    def _extract_parishes_with_xpath_expressions(
        self, driver: WebDriver, analysis: Dict, base_url: str
    ) -> List[Dict[str, Any]]:
        """Extract parishes using XPath expressions from AI analysis."""
        parishes = []
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
        return parishes

    def _remove_duplicate_parishes(self, parishes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate parishes based on name."""
        unique_parishes = []
        seen_names = set()
        for parish in parishes:
            name_key = parish.get("name", "").lower().strip()
            if name_key and name_key not in seen_names:
                seen_names.add(name_key)
                unique_parishes.append(parish)
        return unique_parishes

    def _apply_ai_selectors(self, driver: WebDriver, analysis: Dict, base_url: str) -> List[Dict[str, Any]]:
        """Apply AI - generated selectors to extract parish data."""
        try:
            parishes = []

            # Try CSS selectors first
            parishes.extend(self._extract_parishes_with_css_selectors(driver, analysis, base_url))

            # Try XPath expressions
            parishes.extend(self._extract_parishes_with_xpath_expressions(driver, analysis, base_url))

            # Remove duplicates based on name
            unique_parishes = self._remove_duplicate_parishes(parishes)

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
            except Exception:
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

        # Exclude obvious non - parishes
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
