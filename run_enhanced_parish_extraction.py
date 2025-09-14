#!/usr/bin/env python3
"""
Enhanced Parish Extraction Runner

This script runs Step 3 (parish extraction) with enhanced website detection
by post-processing existing extraction results to find missing parish websites.
"""

import argparse
import time
from typing import Dict, List, Optional

import config
from core.db import get_supabase_client
from core.logger import get_logger
from enhanced_website_extractor import EnhancedWebsiteExtractor

logger = get_logger(__name__)

class EnhancedParishExtraction:
    """Enhanced parish extraction that improves website detection on existing parishes."""

    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.website_extractor = EnhancedWebsiteExtractor()

    def enhance_parishes_without_websites(self, limit: int = 20, extraction_method: str = None) -> Dict:
        """Enhance existing parishes that don't have websites by finding them."""
        try:
            # Get parishes without websites
            query = self.supabase.table('Parishes').select('id, Name, "extraction_method", diocese_id')
            query = query.eq('Status', 'Parish').is_('Web', 'null')

            if extraction_method:
                query = query.eq('extraction_method', extraction_method)

            query = query.limit(limit)
            response = query.execute()

            parishes = response.data
            logger.info(f"🔍 Enhancing {len(parishes)} parishes without websites")

            results = {
                'processed': 0,
                'websites_found': 0,
                'websites_added': 0,
                'by_method': {}
            }

            for parish in parishes:
                results['processed'] += 1
                parish_id = parish['id']
                parish_name = parish['Name']
                method = parish.get('extraction_method', 'unknown')

                logger.info(f"  🔍 Enhancing: {parish_name} ({method})")

                # Try to find website for this parish
                website = self._find_parish_website(parish)

                if website:
                    results['websites_found'] += 1

                    # Update parish with found website
                    update_result = self.supabase.table('Parishes').update({
                        'Web': website
                    }).eq('id', parish_id).execute()

                    if update_result:
                        results['websites_added'] += 1
                        logger.info(f"    ✅ Found website: {website}")

                        # Track by method
                        if method not in results['by_method']:
                            results['by_method'][method] = {'processed': 0, 'found': 0}
                        results['by_method'][method]['found'] += 1
                    else:
                        logger.warning(f"    ⚠️ Failed to update database for {parish_name}")
                else:
                    logger.info(f"    ❌ No website found")

                # Track processing by method
                if method not in results['by_method']:
                    results['by_method'][method] = {'processed': 0, 'found': 0}
                results['by_method'][method]['processed'] += 1

                # Rate limiting
                time.sleep(0.5)

            return results

        except Exception as e:
            logger.error(f"Error in enhance_parishes_without_websites: {e}")
            return {'error': str(e)}

    def _find_parish_website(self, parish_info: Dict) -> Optional[str]:
        """Find website for a specific parish using multiple strategies."""
        parish_name = parish_info['Name']

        # Strategy 1: Generate plausible parish websites based on name patterns
        potential_websites = self._generate_potential_websites(parish_name)

        # Strategy 2: Check each potential website
        for website in potential_websites:
            if self._validate_website(website, parish_name):
                return website

        return None

    def _generate_potential_websites(self, parish_name: str) -> List[str]:
        """Generate potential parish websites based on naming patterns."""
        import re

        potential_sites = []

        # Clean parish name
        clean_name = re.sub(r'[^a-zA-Z\s]', '', parish_name.lower())
        words = clean_name.split()

        # Saint/St. patterns
        if any(word in clean_name for word in ['saint', 'st.']):
            saint_name = None
            for i, word in enumerate(words):
                if word in ['saint', 'st', 'sts']:
                    if i + 1 < len(words):
                        saint_name = words[i + 1]
                        break

            if saint_name:
                potential_sites.extend([
                    f"https://st{saint_name}parish.org",
                    f"https://saint{saint_name}catholic.org",
                    f"https://www.st{saint_name}.org",
                    f"https://st{saint_name}church.com",
                    f"https://saint{saint_name}.net",
                    f"https://{saint_name}parish.org"
                ])

        # Our Lady patterns
        if 'our lady' in clean_name:
            lady_match = re.search(r'our lady of (\w+)', clean_name)
            if lady_match:
                dedication = lady_match.group(1)
                potential_sites.extend([
                    f"https://ourladyof{dedication}.org",
                    f"https://olof{dedication}.org",
                    f"https://www.ourladyof{dedication}.com"
                ])

        # Generic patterns for any parish
        if len(words) >= 2:
            first_words = ''.join(words[:2])
            potential_sites.extend([
                f"https://{first_words}catholic.org",
                f"https://www.{first_words}parish.com",
                f"https://{first_words}church.net",
                f"https://{first_words}.org"
            ])

        # Holy/Sacred/Blessed patterns
        special_names = ['holy', 'sacred', 'blessed', 'immaculate']
        for special in special_names:
            if special in words:
                try:
                    idx = words.index(special)
                    if idx + 1 < len(words):
                        combined = special + words[idx + 1]
                        potential_sites.extend([
                            f"https://{combined}parish.org",
                            f"https://{combined}catholic.org",
                            f"https://www.{combined}.org"
                        ])
                except:
                    continue

        return list(set(potential_sites))  # Remove duplicates

    def _validate_website(self, url: str, parish_name: str) -> bool:
        """Validate if a website exists and appears to be a parish website."""
        try:
            import requests

            # Quick check if URL is accessible
            response = requests.head(url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                # Do a basic content check
                content_response = requests.get(url, timeout=10)
                if content_response.status_code == 200:
                    content = content_response.text.lower()

                    # Check for parish indicators
                    parish_indicators = [
                        'mass times', 'mass schedule', 'catholic', 'parish',
                        'sacrament', 'confession', 'baptism', 'eucharist',
                        'sunday mass', 'holy mass', 'liturgy'
                    ]

                    if any(indicator in content for indicator in parish_indicators):
                        logger.debug(f"Validated website: {url}")
                        return True

        except Exception as e:
            logger.debug(f"Website validation failed for {url}: {e}")

        return False

    def get_enhancement_statistics(self) -> Dict:
        """Get current statistics about parish website coverage."""
        try:
            # Get total legitimate parishes
            total_response = self.supabase.table('Parishes').select('id').eq('Status', 'Parish').execute()
            total_parishes = len(total_response.data)

            # Get parishes with websites
            with_websites_response = self.supabase.table('Parishes').select('id').eq('Status', 'Parish').not_.is_('Web', 'null').execute()
            with_websites = len(with_websites_response.data)

            # Get breakdown by extraction method
            method_response = self.supabase.table('Parishes').select('extraction_method, Web').eq('Status', 'Parish').execute()

            from collections import defaultdict
            method_stats = defaultdict(lambda: {'total': 0, 'with_website': 0})

            for parish in method_response.data:
                method = parish.get('extraction_method', 'unknown')
                has_website = bool(parish.get('Web'))

                method_stats[method]['total'] += 1
                if has_website:
                    method_stats[method]['with_website'] += 1

            return {
                'total_parishes': total_parishes,
                'with_websites': with_websites,
                'coverage_rate': (with_websites / total_parishes * 100) if total_parishes > 0 else 0,
                'by_method': dict(method_stats)
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description="Run enhanced parish website extraction")
    parser.add_argument("--limit", type=int, default=10, help="Number of parishes to enhance")
    parser.add_argument("--method", type=str, help="Specific extraction method to enhance")
    parser.add_argument("--stats", action="store_true", help="Show current statistics only")

    args = parser.parse_args()

    if not config.validate_config():
        logger.error("Configuration validation failed")
        return

    supabase = get_supabase_client()
    if not supabase:
        logger.error("Could not initialize Supabase client")
        return

    enhancer = EnhancedParishExtraction(supabase)

    if args.stats:
        logger.info("📊 Getting current parish website statistics...")
        stats = enhancer.get_enhancement_statistics()

        if 'error' in stats:
            logger.error(f"❌ Failed to get statistics: {stats['error']}")
            return

        logger.info(f"\n📈 Current Parish Website Coverage:")
        logger.info(f"   Total legitimate parishes: {stats['total_parishes']}")
        logger.info(f"   Parishes with websites: {stats['with_websites']}")
        logger.info(f"   Coverage rate: {stats['coverage_rate']:.1f}%")

        logger.info(f"\n📋 By Extraction Method:")
        for method, data in sorted(stats['by_method'].items(), key=lambda x: x[1]['total'], reverse=True):
            total = data['total']
            with_web = data['with_website']
            rate = (with_web / total * 100) if total > 0 else 0
            logger.info(f"   {method:35} │ {with_web:3}/{total:3} parishes │ {rate:5.1f}% coverage")

        return

    logger.info(f"🚀 Starting enhanced parish website extraction (limit: {args.limit})")
    if args.method:
        logger.info(f"   Targeting method: {args.method}")

    results = enhancer.enhance_parishes_without_websites(args.limit, args.method)

    if 'error' in results:
        logger.error(f"❌ Enhancement failed: {results['error']}")
        return

    logger.info("📊 Enhancement Results:")
    logger.info(f"   Processed: {results['processed']} parishes")
    logger.info(f"   Websites found: {results['websites_found']}")
    logger.info(f"   Websites added: {results['websites_added']}")

    if results['processed'] > 0:
        success_rate = results['websites_found'] / results['processed'] * 100
        logger.info(f"   📈 Success rate: {success_rate:.1f}%")

    if results['by_method']:
        logger.info("\n📋 Results by Method:")
        for method, stats in results['by_method'].items():
            processed = stats['processed']
            found = stats['found']
            rate = (found / processed * 100) if processed > 0 else 0
            logger.info(f"   {method:30} │ {found:2}/{processed:2} parishes │ {rate:5.1f}% success")


if __name__ == '__main__':
    main()