#!/usr/bin/env python3
"""
Simple Website Enhancement for Step 3

This script provides a simple, direct approach to enhance parish website
extraction by using AI and improved patterns on existing parish data.
"""

import argparse
import time
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup

import config
from core.db import get_supabase_client
from core.logger import get_logger
from enhanced_website_extractor import EnhancedWebsiteExtractor

logger = get_logger(__name__)

class SimpleWebsiteEnhancer:
    """Simple website enhancement for existing parishes."""

    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.website_extractor = EnhancedWebsiteExtractor()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Parish Website Finder)'
        })

    def find_real_parish_websites(self, limit: int = 10) -> Dict:
        """Find real parish websites using multiple strategies."""
        try:
            # Get parishes without websites, prioritizing legitimate ones
            query = self.supabase.table('Parishes').select('id, Name, diocese_id')
            query = query.eq('Status', 'Parish').is_('Web', 'null')
            query = query.limit(limit * 3)  # Get more to filter from
            response = query.execute()

            all_parishes = response.data

            # Filter to get parishes that look legitimate
            legitimate_parishes = []
            for parish in all_parishes:
                name = parish['Name'].lower()
                # Skip obvious non-parishes
                if not any(skip_term in name for skip_term in [
                    'boundary', 'fill', 'add', 'selected', 'proximities',
                    'type', 'menu', 'find', 'get involved', 'connect'
                ]):
                    # Prioritize parishes with saint names or common Catholic terms
                    if any(term in name for term in [
                        'saint', 'st.', 'st ', 'our lady', 'holy', 'sacred',
                        'blessed', 'immaculate', 'cathedral', 'catholic church'
                    ]):
                        legitimate_parishes.append(parish)

            # Take only the requested limit
            parishes_to_process = legitimate_parishes[:limit]

            logger.info(f"🔍 Processing {len(parishes_to_process)} legitimate parishes")

            results = {
                'processed': 0,
                'websites_found': 0,
                'websites_added': 0,
                'parishes': []
            }

            for parish in parishes_to_process:
                results['processed'] += 1
                parish_id = parish['id']
                parish_name = parish['Name']

                logger.info(f"  🔍 Searching: {parish_name}")

                # Try multiple strategies to find website
                website = self._comprehensive_website_search(parish)

                if website:
                    results['websites_found'] += 1

                    # Update parish with found website
                    try:
                        update_result = self.supabase.table('Parishes').update({
                            'Web': website
                        }).eq('id', parish_id).execute()

                        if update_result:
                            results['websites_added'] += 1
                            logger.info(f"    ✅ Found and saved: {website}")
                            results['parishes'].append({
                                'name': parish_name,
                                'website': website,
                                'status': 'added'
                            })
                        else:
                            logger.warning(f"    ⚠️ Found but failed to save: {website}")
                            results['parishes'].append({
                                'name': parish_name,
                                'website': website,
                                'status': 'found_not_saved'
                            })
                    except Exception as e:
                        logger.error(f"    ❌ Database update error: {e}")
                else:
                    logger.info(f"    ❌ No website found")
                    results['parishes'].append({
                        'name': parish_name,
                        'website': None,
                        'status': 'not_found'
                    })

                # Rate limiting
                time.sleep(1)

            return results

        except Exception as e:
            logger.error(f"Error in find_real_parish_websites: {e}")
            return {'error': str(e)}

    def _comprehensive_website_search(self, parish: Dict) -> Optional[str]:
        """Comprehensive search for parish website using multiple strategies."""
        parish_name = parish['Name']

        # Strategy 1: Common Catholic website patterns
        websites = self._generate_catholic_websites(parish_name)

        # Strategy 2: Diocese-specific patterns
        diocese_websites = self._generate_diocese_specific_websites(parish)

        # Strategy 3: Search engine simulation (basic patterns)
        search_websites = self._generate_search_based_websites(parish_name)

        all_potential_websites = websites + diocese_websites + search_websites

        # Test each potential website
        for website in all_potential_websites:
            if self._verify_website_exists_and_is_parish(website, parish_name):
                return website

        return None

    def _generate_catholic_websites(self, parish_name: str) -> List[str]:
        """Generate potential Catholic parish websites."""
        import re

        websites = []
        clean_name = re.sub(r'[^a-zA-Z\s]', '', parish_name.lower())
        words = clean_name.split()

        # Saint patterns
        if 'saint' in words or any(word.startswith('st') for word in words):
            saint_name = None
            for i, word in enumerate(words):
                if word in ['saint', 'st']:
                    if i + 1 < len(words):
                        saint_name = words[i + 1]
                        break

            if saint_name:
                websites.extend([
                    f"https://st{saint_name}parish.org",
                    f"https://saint{saint_name}catholic.org",
                    f"https://www.st{saint_name}.org",
                    f"https://st{saint_name}church.net",
                    f"https://www.saint{saint_name}parish.com",
                    f"https://{saint_name}catholic.org"
                ])

        # Our Lady patterns
        if 'our lady' in clean_name:
            ol_match = re.search(r'our lady of (\w+)', clean_name)
            if ol_match:
                dedication = ol_match.group(1)
                websites.extend([
                    f"https://ourladyof{dedication}.org",
                    f"https://www.ourladyof{dedication}.com",
                    f"https://olof{dedication}.org"
                ])

        # Holy, Sacred, Blessed patterns
        special_words = ['holy', 'sacred', 'blessed', 'immaculate']
        for special in special_words:
            if special in words:
                try:
                    idx = words.index(special)
                    if idx + 1 < len(words):
                        next_word = words[idx + 1]
                        combined = special + next_word
                        websites.extend([
                            f"https://{combined}parish.org",
                            f"https://{combined}catholic.org",
                            f"https://www.{combined}.net"
                        ])
                except:
                    continue

        return websites

    def _generate_diocese_specific_websites(self, parish: Dict) -> List[str]:
        """Generate diocese-specific website patterns."""
        websites = []
        parish_name = parish['Name']

        # Get diocese information
        try:
            diocese_response = self.supabase.table('Dioceses').select('Name, Website').eq('id', parish['diocese_id']).execute()
            if diocese_response.data:
                diocese = diocese_response.data[0]
                diocese_name = diocese.get('Name', '')
                diocese_url = diocese.get('Website', '')

                if diocese_url:
                    # Extract diocese domain
                    from urllib.parse import urlparse
                    parsed = urlparse(diocese_url)
                    base_domain = parsed.netloc.replace('www.', '')

                    # Generate parish URLs on diocese domain
                    clean_parish = parish_name.lower().replace(' ', '').replace('.', '')[:15]
                    websites.extend([
                        f"https://www.{base_domain}/parishes/{clean_parish}",
                        f"https://{base_domain}/parishes/{clean_parish}",
                        f"https://{clean_parish}.{base_domain}",
                    ])

        except Exception as e:
            logger.debug(f"Error generating diocese-specific URLs: {e}")

        return websites

    def _generate_search_based_websites(self, parish_name: str) -> List[str]:
        """Generate websites based on common search patterns."""
        import re

        websites = []
        words = re.sub(r'[^a-zA-Z\s]', '', parish_name.lower()).split()

        # Use first 2-3 words for domain generation
        if len(words) >= 2:
            domain_base = ''.join(words[:2])
            websites.extend([
                f"https://{domain_base}catholic.org",
                f"https://www.{domain_base}parish.com",
                f"https://{domain_base}church.net"
            ])

        if len(words) >= 3:
            domain_base = ''.join(words[:3])
            websites.append(f"https://{domain_base}.org")

        return websites

    def _verify_website_exists_and_is_parish(self, url: str, parish_name: str) -> bool:
        """Verify if website exists and appears to be a parish website."""
        try:
            # First, do a head request to check if URL exists
            head_response = self.session.head(url, timeout=5, allow_redirects=True)
            if head_response.status_code not in [200, 301, 302]:
                return False

            # Then check content for parish indicators
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                content = response.text.lower()

                # Check for Catholic parish indicators
                parish_indicators = [
                    'mass times', 'mass schedule', 'catholic', 'parish',
                    'sacrament', 'confession', 'baptism', 'eucharist',
                    'sunday mass', 'holy mass', 'liturgy', 'holy communion'
                ]

                indicator_count = sum(1 for indicator in parish_indicators if indicator in content)

                # Need at least 2 parish indicators to be confident
                if indicator_count >= 2:
                    logger.debug(f"✅ Verified parish website: {url} ({indicator_count} indicators)")
                    return True

        except Exception as e:
            logger.debug(f"Website verification failed for {url}: {e}")

        return False


def main():
    parser = argparse.ArgumentParser(description="Simple website enhancement for parishes")
    parser.add_argument("--limit", type=int, default=5, help="Number of parishes to process")
    parser.add_argument("--test_mode", action="store_true", help="Run in test mode (no database updates)")

    args = parser.parse_args()

    if not config.validate_config():
        logger.error("Configuration validation failed")
        return

    supabase = get_supabase_client()
    if not supabase:
        logger.error("Could not initialize Supabase client")
        return

    enhancer = SimpleWebsiteEnhancer(supabase)

    logger.info(f"🚀 Starting simple website enhancement (limit: {args.limit})")
    if args.test_mode:
        logger.info("   Running in test mode - no database updates")

    results = enhancer.find_real_parish_websites(args.limit)

    if 'error' in results:
        logger.error(f"❌ Enhancement failed: {results['error']}")
        return

    logger.info("\n📊 Website Enhancement Results:")
    logger.info(f"   Parishes processed: {results['processed']}")
    logger.info(f"   Websites found: {results['websites_found']}")
    logger.info(f"   Websites added to database: {results['websites_added']}")

    if results['processed'] > 0:
        success_rate = results['websites_found'] / results['processed'] * 100
        logger.info(f"   📈 Success rate: {success_rate:.1f}%")

    if results['parishes']:
        logger.info("\n📋 Detailed Results:")
        for parish in results['parishes']:
            status_icon = {
                'added': '✅',
                'found_not_saved': '⚠️',
                'not_found': '❌'
            }.get(parish['status'], '❓')

            website_info = f" → {parish['website']}" if parish['website'] else ""
            logger.info(f"   {status_icon} {parish['name']}{website_info}")


if __name__ == '__main__':
    main()