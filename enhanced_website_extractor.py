#!/usr/bin/env python3
"""
Enhanced Website Extraction Module

Provides comprehensive website extraction patterns that can be used
across all parish extraction methods to dramatically improve success rates.
"""

import re
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup, Tag
from core.logger import get_logger

logger = get_logger(__name__)

class EnhancedWebsiteExtractor:
    """Comprehensive website extraction system for parish data."""

    def __init__(self):
        # Common social media and non-parish domains to skip
        self.skip_domains = {
            'facebook.com', 'fb.com', 'twitter.com', 'instagram.com', 'youtube.com',
            'linkedin.com', 'pinterest.com', 'tiktok.com', 'snapchat.com',
            'google.com', 'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'dioce', 'bishop', 'archdiocese', 'usccb.org', 'vatican.va'
        }

        # Parish website indicators in domain names
        self.parish_indicators = {
            'parish', 'church', 'catholic', 'saint', 'st.', 'sts.', 'ourladyof',
            'sacredheart', 'immaculate', 'holy', 'blessed', 'cathedral',
            'shrine', 'chapel', 'mission'
        }

        # Website link text patterns that suggest parish websites
        self.website_link_texts = {
            'website', 'web site', 'visit us', 'parish website', 'church website',
            'our website', 'home page', 'homepage', 'www', 'click here',
            'more info', 'learn more', 'visit', 'online'
        }

        # CSS selectors for website links (ordered by reliability)
        self.website_selectors = [
            # Most specific selectors first
            'a[class*="website"]',
            'a[class*="web"]',
            'a[id*="website"]',
            'a[id*="web"]',
            '.website a',
            '.web a',
            '.parish-website a',
            '.church-website a',
            'a[title*="website"]',
            'a[title*="web"]',
            'a[aria-label*="website"]',
            'a[aria-label*="web"]',
        ]

    def is_valid_parish_website(self, url: str, parish_name: str = None) -> bool:
        """Validate if a URL is likely a legitimate parish website."""
        if not url or len(url.strip()) < 5:
            return False

        url_lower = url.lower().strip()

        # Skip obvious non-parish URLs
        if any(domain in url_lower for domain in self.skip_domains):
            return False

        # Skip common non-website links
        skip_protocols = ['mailto:', 'tel:', 'javascript:', 'ftp://']
        if any(url_lower.startswith(proto) for proto in skip_protocols):
            return False

        # Must be HTTP/HTTPS or start with www
        if not (url_lower.startswith('http') or url_lower.startswith('www')):
            return False

        # Parish indicators in domain increase confidence
        parsed = urlparse(url_lower)
        domain = parsed.netloc.lower()

        # Look for parish indicators in domain
        has_parish_indicator = any(indicator in domain for indicator in self.parish_indicators)

        # Look for parish name in domain if provided
        has_name_match = False
        if parish_name:
            # Clean parish name for matching
            clean_name = re.sub(r'[^a-zA-Z\s]', '', parish_name.lower())
            name_words = clean_name.split()[:3]  # First 3 words
            has_name_match = any(word in domain for word in name_words if len(word) > 3)

        return has_parish_indicator or has_name_match

    def normalize_url(self, url: str, base_url: str = None) -> str:
        """Normalize and clean URL."""
        if not url:
            return None

        url = url.strip()

        # Handle relative URLs
        if url.startswith('/') and base_url:
            url = urljoin(base_url, url)
        elif url.startswith('www.') and not url.startswith('http'):
            url = f"https://{url}"
        elif not url.startswith('http') and not url.startswith('www'):
            # Might be just a domain name
            url = f"https://{url}"

        return url

    def extract_website_from_element(self, element: Tag, parish_name: str = None, base_url: str = None) -> Optional[str]:
        """Extract website from a BeautifulSoup element using multiple strategies."""
        websites_found = []

        # Strategy 1: Use CSS selectors for website-specific links
        for selector in self.website_selectors:
            try:
                links = element.select(selector)
                for link in links:
                    href = link.get('href', '').strip()
                    if href:
                        normalized_url = self.normalize_url(href, base_url)
                        if normalized_url and self.is_valid_parish_website(normalized_url, parish_name):
                            websites_found.append((normalized_url, 'css_selector', 0.9))
            except:
                continue

        # Strategy 2: Look for links with website-related text
        all_links = element.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '').strip()
            if not href:
                continue

            link_text = link.get_text().lower().strip()
            title = link.get('title', '').lower()
            aria_label = link.get('aria-label', '').lower()

            # Check if link text suggests it's a website link
            is_website_link = (
                any(pattern in link_text for pattern in self.website_link_texts) or
                any(pattern in title for pattern in self.website_link_texts) or
                any(pattern in aria_label for pattern in self.website_link_texts)
            )

            if is_website_link or href.startswith('http'):
                normalized_url = self.normalize_url(href, base_url)
                if normalized_url and self.is_valid_parish_website(normalized_url, parish_name):
                    confidence = 0.8 if is_website_link else 0.7
                    websites_found.append((normalized_url, 'link_text', confidence))

        # Strategy 3: Look for parish name in URLs
        if parish_name:
            name_words = re.sub(r'[^a-zA-Z\s]', '', parish_name.lower()).split()
            for link in all_links:
                href = link.get('href', '').strip()
                if href.startswith('http'):
                    href_lower = href.lower()
                    if any(word in href_lower for word in name_words if len(word) > 3):
                        normalized_url = self.normalize_url(href, base_url)
                        if normalized_url and self.is_valid_parish_website(normalized_url, parish_name):
                            websites_found.append((normalized_url, 'name_match', 0.6))

        # Return the highest confidence website
        if websites_found:
            # Sort by confidence, then by method preference
            websites_found.sort(key=lambda x: x[2], reverse=True)
            best_website = websites_found[0]
            logger.debug(f"Found website: {best_website[0]} (method: {best_website[1]}, confidence: {best_website[2]})")
            return best_website[0]

        return None

    def extract_website_from_text(self, text: str, parish_name: str = None) -> Optional[str]:
        """Extract website URLs from plain text using regex patterns."""
        # URL patterns
        url_patterns = [
            r'https?://[^\s<>"]+',
            r'www\.[^\s<>"]+',
            r'[a-zA-Z0-9][a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'
        ]

        potential_urls = []

        for pattern in url_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                normalized_url = self.normalize_url(match.strip())
                if normalized_url and self.is_valid_parish_website(normalized_url, parish_name):
                    potential_urls.append(normalized_url)

        return potential_urls[0] if potential_urls else None

    def extract_all_websites(self, element: Tag, parish_name: str = None, base_url: str = None) -> List[str]:
        """Extract all potential parish websites from an element."""
        # Try element-based extraction first
        website = self.extract_website_from_element(element, parish_name, base_url)
        websites = [website] if website else []

        # Try text-based extraction as backup
        text_content = element.get_text()
        text_website = self.extract_website_from_text(text_content, parish_name)
        if text_website and text_website not in websites:
            websites.append(text_website)

        return websites


def enhance_existing_extraction_method(existing_result: Dict, soup_element: Tag,
                                     base_url: str = None) -> Dict:
    """
    Enhance an existing extraction result with better website detection.
    This can be used to retrofit existing extraction methods.
    """
    if existing_result.get('website'):
        # Already has a website, return as-is
        return existing_result

    extractor = EnhancedWebsiteExtractor()
    parish_name = existing_result.get('name', '')

    # Extract website using enhanced methods
    website = extractor.extract_website_from_element(soup_element, parish_name, base_url)

    if website:
        existing_result['website'] = website
        logger.info(f"🌐 Enhanced extraction found website: {parish_name} → {website}")

    return existing_result


def test_website_extraction():
    """Test the website extraction system."""
    # Sample HTML for testing
    test_html = """
    <div class="parish-info">
        <h3>St. Mary Catholic Church</h3>
        <p>Phone: (555) 123-4567</p>
        <p>Address: 123 Main Street, Anytown, ST 12345</p>
        <div class="website">
            <a href="https://stmarycatholic.org">Visit our website</a>
        </div>
        <div class="social">
            <a href="https://facebook.com/stmary">Facebook</a>
        </div>
    </div>
    """

    soup = BeautifulSoup(test_html, 'html.parser')
    extractor = EnhancedWebsiteExtractor()

    website = extractor.extract_website_from_element(
        soup.find('div', class_='parish-info'),
        "St. Mary Catholic Church"
    )

    print(f"Test extraction result: {website}")
    return website == "https://stmarycatholic.org"


if __name__ == '__main__':
    # Run test
    success = test_website_extraction()
    print(f"Test {'PASSED' if success else 'FAILED'}")