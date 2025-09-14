#!/usr/bin/env python3
"""
Enhanced Parish Website Extraction System

This script improves parish website extraction by:
1. Better filtering of non-parish entries
2. Enhanced website detection patterns
3. AI-powered validation of parish data
4. Improved website URL extraction from parish directories
"""

import re
import argparse
import time
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

import config
from core.db import get_supabase_client
from core.logger import get_logger

logger = get_logger(__name__)

# Enhanced patterns for parish website detection
WEBSITE_SELECTORS = [
    'a[href*="parish"]',
    'a[href*="church"]',
    'a[href*="catholic"]',
    'a[href*="stmary"]',
    'a[href*="saintmary"]',
    'a[href*="stjohn"]',
    'a[href*="saintjohn"]',
    'a[href*="stpatrick"]',
    'a[href*="saintpatrick"]',
    'a[href*="stmichael"]',
    'a[href*="saintmichael"]',
    'a[class*="website"]',
    'a[class*="parish"]',
    'a[title*="website"]',
    'a[title*="visit"]',
    '.parish-website a',
    '.church-website a',
    '.website-link a',
]

# Common parish name patterns
PARISH_NAME_PATTERNS = [
    r'saint?\s+\w+',
    r'st\.?\s+\w+',
    r'our\s+lady\s+of\s+\w+',
    r'holy\s+\w+',
    r'blessed\s+\w+',
    r'sacred\s+heart',
    r'immaculate\s+\w+',
    r'cathedral\s+of\s+\w+',
    r'\w+\s+catholic\s+church',
]

# Enhanced non-parish filter terms
NON_PARISH_TERMS = [
    'menu', 'navigation', 'header', 'footer', 'sidebar',
    'find a parish', 'parish finder', 'choose city', 'select',
    'get involved', 'connect with us', 'contact us', 'about us',
    'home', 'search', 'filter', 'sort', 'view all',
    'diocese', 'bishop', 'office', 'administration',
    'calendar', 'events', 'news', 'bulletins',
    'calc.', 'calculation', 'averages', 'sums',
    'school directory', 'find a school', 'ministry',
    'diocesan', 'archdiocese', 'episcopal',
]

class EnhancedParishExtractor:
    """Enhanced parish website extraction system."""

    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Parish Website Extractor)'
        })

        # Initialize AI if available
        if config.GENAI_API_KEY:
            try:
                genai.configure(api_key=config.GENAI_API_KEY)
                self.use_ai = True
                logger.info("🤖 AI-powered validation enabled")
            except Exception as e:
                logger.warning(f"AI initialization failed: {e}")
                self.use_ai = False
        else:
            self.use_ai = False
            logger.info("🔍 Using keyword-based validation only")

    def is_likely_parish(self, name: str) -> bool:
        """Enhanced parish name validation."""
        if not name or len(name.strip()) < 3:
            return False

        name_lower = name.lower().strip()

        # Immediate disqualifiers
        if any(term in name_lower for term in NON_PARISH_TERMS):
            return False

        # Length checks
        if len(name_lower) < 3 or len(name_lower) > 100:
            return False

        # Parish name pattern matching
        for pattern in PARISH_NAME_PATTERNS:
            if re.search(pattern, name_lower):
                return True

        # Generic church indicators
        church_terms = ['church', 'parish', 'chapel', 'cathedral', 'mission', 'shrine']
        if any(term in name_lower for term in church_terms):
            # But not if it's just "parish" by itself or similar
            if name_lower not in ['parish', 'church', 'chapel', 'cathedral']:
                return True

        return False

    def validate_parish_with_ai(self, name: str, address: str = None, phone: str = None) -> Dict:
        """AI-powered parish validation."""
        if not self.use_ai:
            return {'is_parish': self.is_likely_parish(name), 'confidence': 0.7, 'reason': 'keyword-based'}

        context = f"Name: {name}"
        if address:
            context += f", Address: {address}"
        if phone:
            context += f", Phone: {phone}"

        prompt = f"""
        Analyze this entry to determine if it represents a real Catholic parish or church:
        {context}

        Consider:
        1. Is this a legitimate parish/church name?
        2. Does it follow Catholic naming conventions?
        3. Is it a navigation element, menu item, or UI component?
        4. Is it a generic term or placeholder text?

        Respond with:
        Score: [0-100] (confidence it's a real parish)
        Reason: [brief explanation]
        """

        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            response_text = response.text

            score_match = re.search(r"Score: (\d+)", response_text)
            score = int(score_match.group(1)) if score_match else 50

            reason_match = re.search(r"Reason: (.+)", response_text)
            reason = reason_match.group(1).strip() if reason_match else "AI analysis"

            return {
                'is_parish': score >= 70,
                'confidence': score / 100,
                'reason': reason
            }

        except Exception as e:
            logger.warning(f"AI validation failed for {name}: {e}")
            return {'is_parish': self.is_likely_parish(name), 'confidence': 0.6, 'reason': 'fallback'}

    def extract_website_from_parish_page(self, parish_url: str) -> Optional[str]:
        """Enhanced website extraction from individual parish pages."""
        try:
            response = self.session.get(parish_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try multiple selectors for website links
            for selector in WEBSITE_SELECTORS:
                try:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get('href', '')
                        if href and self.is_valid_parish_website(href):
                            return self.normalize_url(href, parish_url)
                except:
                    continue

            # Look for any external links that might be parish websites
            external_links = soup.find_all('a', href=re.compile(r'^https?://'))
            for link in external_links:
                href = link.get('href', '')
                if self.is_valid_parish_website(href):
                    # Check if link text suggests it's a parish website
                    link_text = link.get_text().lower()
                    if any(term in link_text for term in ['website', 'visit', 'parish', 'church']):
                        return href

        except Exception as e:
            logger.warning(f"Error extracting website from {parish_url}: {e}")

        return None

    def is_valid_parish_website(self, url: str) -> bool:
        """Validate if a URL is likely a parish website."""
        if not url:
            return False

        url_lower = url.lower()

        # Skip social media and common non-parish domains
        skip_domains = [
            'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com',
            'google.com', 'yahoo.com', 'gmail.com',
            'diocese', 'archdiocese', 'bishop',
            'usccb.org', 'vatican.va'
        ]

        if any(domain in url_lower for domain in skip_domains):
            return False

        # Parish website indicators
        parish_indicators = [
            'parish', 'church', 'catholic', 'saint', 'st.',
            'ourladyof', 'sacredheart', 'immaculate', 'holy'
        ]

        return any(indicator in url_lower for indicator in parish_indicators)

    def normalize_url(self, url: str, base_url: str = None) -> str:
        """Normalize and validate URL."""
        if not url:
            return None

        # Handle relative URLs
        if url.startswith('/') and base_url:
            url = urljoin(base_url, url)
        elif not url.startswith('http'):
            if base_url:
                url = urljoin(base_url, url)
            else:
                url = f"https://{url}"

        return url.strip()

    def enhance_parish_websites(self, diocese_id: int = None, limit: int = 50) -> Dict:
        """Main function to enhance parish website extraction."""
        try:
            # Get parishes without websites
            query = self.supabase.table('Parishes').select('id, Name, diocese_id, "Street Address", "Phone Number"')
            query = query.is_('Web', 'null')

            if diocese_id:
                query = query.eq('diocese_id', diocese_id)

            query = query.limit(limit)
            response = query.execute()

            parishes_without_websites = response.data
            logger.info(f"🔍 Found {len(parishes_without_websites)} parishes without websites")

            results = {
                'processed': 0,
                'validated_parishes': 0,
                'non_parishes_filtered': 0,
                'websites_found': 0,
                'websites_added': 0
            }

            for parish in parishes_without_websites:
                results['processed'] += 1

                # Validate if this is actually a parish
                validation = self.validate_parish_with_ai(
                    parish['Name'],
                    parish.get('Street Address'),
                    parish.get('Phone Number')
                )

                if not validation['is_parish']:
                    logger.info(f"  ❌ Filtered non-parish: {parish['Name']} - {validation['reason']}")
                    results['non_parishes_filtered'] += 1

                    # Mark as non-parish in database
                    self.supabase.table('Parishes').update({
                        'Status': 'Non-Parish'
                    }).eq('id', parish['id']).execute()

                    continue

                results['validated_parishes'] += 1
                logger.info(f"  ✅ Validated parish: {parish['Name']} (confidence: {validation['confidence']:.2f})")

                # Try to find website for this parish
                website_found = self.search_for_parish_website(parish)

                if website_found:
                    results['websites_found'] += 1

                    # Update parish with website
                    update_result = self.supabase.table('Parishes').update({
                        'Web': website_found
                    }).eq('id', parish['id']).execute()

                    if update_result:
                        results['websites_added'] += 1
                        logger.info(f"  🌐 Added website: {parish['Name']} → {website_found}")

                # Brief pause to be respectful
                time.sleep(0.5)

            return results

        except Exception as e:
            logger.error(f"Error in enhance_parish_websites: {e}")
            return {'error': str(e)}

    def search_for_parish_website(self, parish_info: Dict) -> Optional[str]:
        """Search for a parish website using multiple strategies."""
        parish_name = parish_info['Name']

        # Strategy 1: Direct Google search for parish website
        search_terms = [
            f'"{parish_name}" catholic church website',
            f'{parish_name} parish website',
            f'{parish_name.replace("Saint", "St")} catholic church'
        ]

        # For now, return mock result - in production you'd implement actual search
        # This would integrate with Google Custom Search API or other search methods

        # Strategy 2: Check if parish has detail URL we can scrape
        if parish_info.get('parish_detail_url'):
            website = self.extract_website_from_parish_page(parish_info['parish_detail_url'])
            if website:
                return website

        return None


def main():
    parser = argparse.ArgumentParser(description="Enhance parish website extraction")
    parser.add_argument("--diocese_id", type=int, help="Process specific diocese only")
    parser.add_argument("--limit", type=int, default=20, help="Limit number of parishes to process")
    parser.add_argument("--validate_only", action="store_true", help="Only validate existing parishes, don't search for websites")

    args = parser.parse_args()

    # Validate configuration
    if not config.validate_config():
        logger.error("Configuration validation failed")
        return

    supabase = get_supabase_client()
    if not supabase:
        logger.error("Could not initialize Supabase client")
        return

    extractor = EnhancedParishExtractor(supabase)

    logger.info(f"🚀 Starting enhanced parish extraction (limit: {args.limit})")
    if args.diocese_id:
        logger.info(f"   Targeting diocese ID: {args.diocese_id}")

    results = extractor.enhance_parish_websites(args.diocese_id, args.limit)

    if 'error' in results:
        logger.error(f"❌ Enhancement failed: {results['error']}")
        return

    logger.info("📊 Enhancement Results:")
    logger.info(f"   Processed: {results['processed']} parishes")
    logger.info(f"   Validated parishes: {results['validated_parishes']}")
    logger.info(f"   Non-parishes filtered: {results['non_parishes_filtered']}")
    logger.info(f"   Websites found: {results['websites_found']}")
    logger.info(f"   Websites added: {results['websites_added']}")

    if results['processed'] > 0:
        validation_rate = results['validated_parishes'] / results['processed'] * 100
        website_success_rate = results['websites_found'] / results['validated_parishes'] * 100 if results['validated_parishes'] > 0 else 0
        logger.info(f"   📈 Validation rate: {validation_rate:.1f}%")
        logger.info(f"   🌐 Website discovery rate: {website_success_rate:.1f}%")


if __name__ == '__main__':
    main()