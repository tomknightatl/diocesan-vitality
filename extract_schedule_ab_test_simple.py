#!/usr/bin/env python3
"""
Simple A/B Testing Schedule Extraction

A lightweight version that focuses purely on testing the two extraction methods
without complex infrastructure that causes timeout issues.
"""

import argparse
import random
import signal
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any

import config
from core.logger import get_logger
from core.db import get_supabase_client

# Import simpler versions of extraction functions
from core.schedule_ai_extractor import ScheduleAIExtractor, save_ai_schedule_results

logger = get_logger(__name__)


class SimpleTimeoutException(Exception):
    """Exception raised when an operation times out."""
    pass


def simple_timeout_handler(signum, frame):
    """Simple signal handler for timeouts."""
    raise SimpleTimeoutException("Operation timed out")


class SimpleABTestExtractor:
    """Simplified A/B testing controller that avoids complex infrastructure."""

    def __init__(self, supabase_client, test_ratio: float = 0.5):
        self.supabase = supabase_client
        self.test_ratio = test_ratio
        self.suppression_urls = self._get_suppression_urls()

    def _get_suppression_urls(self) -> set:
        """Get suppression URLs."""
        try:
            response = self.supabase.table('parishfactssuppressionurls').select('url').execute()
            return {item['url'] for item in response.data}
        except Exception as e:
            logger.error(f"Error fetching suppression URLs: {e}")
            return set()

    def assign_extraction_method(self, parish_id: int) -> str:
        """Assign parish to extraction method using consistent hashing."""
        random.seed(parish_id)
        method = 'ai_enhanced' if random.random() < self.test_ratio else 'keyword_based'
        random.seed()
        return method

    def get_unvisited_parishes(self, limit: int = 20) -> List[Tuple[str, int]]:
        """Get parishes that haven't been processed yet."""
        try:
            # Get parishes already processed
            processed_response = self.supabase.table('ParishData').select('parish_id').execute()
            processed_ids = {p['parish_id'] for p in processed_response.data}

            # Get all parishes with websites
            parishes_response = self.supabase.table('Parishes').select(
                'id, Name, Web'
            ).not_.is_('Web', 'null').execute()

            # Filter out processed ones and problematic URLs
            unvisited = []
            for parish in parishes_response.data:
                if (parish['id'] not in processed_ids and
                    parish['Web'] and
                    parish['Web'] not in self.suppression_urls):
                    unvisited.append((parish['Web'], parish['id']))

            logger.info(f"Found {len(unvisited)} unvisited parishes")
            return unvisited[:limit]

        except Exception as e:
            logger.error(f"Error getting unvisited parishes: {e}")
            return []

    def simple_keyword_extraction(self, url: str, parish_id: int) -> Dict:
        """Simple keyword-based extraction without complex infrastructure."""
        import requests
        from bs4 import BeautifulSoup

        try:
            # Simple request with timeout
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; Schedule Extractor)'}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text().lower()

            result = {
                'parish_id': parish_id,
                'url': url,
                'offers_reconciliation': False,
                'offers_adoration': False,
                'extraction_method': 'keyword_based_simple'
            }

            # Simple keyword detection
            if any(keyword in page_text for keyword in ['reconciliation', 'confession', 'penance']):
                result['offers_reconciliation'] = True
                result['reconciliation_info'] = 'Found reconciliation/confession keywords'

            if any(keyword in page_text for keyword in ['adoration', 'exposition', 'blessed sacrament']):
                result['offers_adoration'] = True
                result['adoration_info'] = 'Found adoration keywords'

            return result

        except Exception as e:
            logger.error(f"Simple keyword extraction failed for {parish_id}: {e}")
            return {
                'parish_id': parish_id,
                'url': url,
                'offers_reconciliation': False,
                'offers_adoration': False,
                'extraction_method': 'keyword_based_simple',
                'error': str(e)
            }

    def simple_ai_extraction(self, url: str, parish_id: int) -> List[Dict]:
        """Simple AI extraction without complex page discovery."""
        import requests
        from bs4 import BeautifulSoup

        try:
            # Simple request with timeout
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; AI Schedule Extractor)'}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            # Remove script, style, nav elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            content = soup.get_text(separator=' ', strip=True)

            # Use AI extractor
            ai_extractor = ScheduleAIExtractor()
            results = []

            # Extract reconciliation schedule
            recon_result = ai_extractor.extract_schedule_from_content(
                content, url, "reconciliation"
            )
            recon_result['parish_id'] = parish_id
            results.append(recon_result)

            # Extract adoration schedule
            ador_result = ai_extractor.extract_schedule_from_content(
                content, url, "adoration"
            )
            ador_result['parish_id'] = parish_id
            results.append(ador_result)

            return results

        except Exception as e:
            logger.error(f"Simple AI extraction failed for {parish_id}: {e}")
            return []

    def save_keyword_results(self, result: Dict):
        """Save keyword extraction results."""
        if not result.get('parish_id'):
            return

        facts_to_save = []
        parish_id = result['parish_id']

        if result.get('offers_reconciliation') and result.get('reconciliation_info'):
            facts_to_save.append({
                'parish_id': parish_id,
                'fact_type': 'ReconciliationSchedule',
                'fact_value': result['reconciliation_info'],
                'fact_source_url': result['url'],
                'extraction_method': 'keyword_based_simple'
            })

        if result.get('offers_adoration') and result.get('adoration_info'):
            facts_to_save.append({
                'parish_id': parish_id,
                'fact_type': 'AdorationSchedule',
                'fact_value': result['adoration_info'],
                'fact_source_url': result['url'],
                'extraction_method': 'keyword_based_simple'
            })

        if facts_to_save:
            try:
                self.supabase.table('ParishData').upsert(facts_to_save).execute()
                logger.info(f"Saved {len(facts_to_save)} keyword facts for parish {parish_id}")
            except Exception as e:
                logger.error(f"Error saving keyword facts: {e}")

    def run_simple_ab_test(self, num_parishes: int) -> Dict[str, Any]:
        """Run simplified A/B test."""
        parishes = self.get_unvisited_parishes(num_parishes)
        if not parishes:
            logger.info("No parishes to test")
            return {}

        # Split parishes by method
        keyword_parishes = []
        ai_parishes = []

        for url, parish_id in parishes:
            method = self.assign_extraction_method(parish_id)
            if method == 'ai_enhanced':
                ai_parishes.append((url, parish_id))
            else:
                keyword_parishes.append((url, parish_id))

        logger.info(f"🧪 Simple A/B Test: {len(keyword_parishes)} keyword, {len(ai_parishes)} AI parishes")

        results = {
            'keyword_results': 0,
            'ai_results': 0,
            'keyword_successes': 0,
            'ai_successes': 0
        }

        # Process keyword parishes
        for url, parish_id in keyword_parishes:
            logger.info(f"🔍 Simple keyword extraction: Parish {parish_id}")

            # Set timeout
            signal.signal(signal.SIGALRM, simple_timeout_handler)
            signal.alarm(60)  # 1 minute timeout

            try:
                result = self.simple_keyword_extraction(url, parish_id)
                self.save_keyword_results(result)
                results['keyword_results'] += 1

                if result.get('offers_reconciliation') or result.get('offers_adoration'):
                    results['keyword_successes'] += 1

            except SimpleTimeoutException:
                logger.warning(f"Keyword extraction timed out for parish {parish_id}")
            except Exception as e:
                logger.error(f"Keyword extraction error for parish {parish_id}: {e}")
            finally:
                signal.alarm(0)

        # Process AI parishes
        for url, parish_id in ai_parishes:
            logger.info(f"🤖 Simple AI extraction: Parish {parish_id}")

            # Set timeout
            signal.signal(signal.SIGALRM, simple_timeout_handler)
            signal.alarm(90)  # 1.5 minute timeout

            try:
                ai_results = self.simple_ai_extraction(url, parish_id)
                if ai_results:
                    save_ai_schedule_results(self.supabase, ai_results)
                    results['ai_results'] += len(ai_results)

                    # Count successes
                    successes = len([r for r in ai_results if r.get('schedule_found', False)])
                    results['ai_successes'] += successes

            except SimpleTimeoutException:
                logger.warning(f"AI extraction timed out for parish {parish_id}")
            except Exception as e:
                logger.error(f"AI extraction error for parish {parish_id}: {e}")
            finally:
                signal.alarm(0)

        # Calculate success rates
        results['keyword_success_rate'] = (results['keyword_successes'] / len(keyword_parishes)
                                         if keyword_parishes else 0)
        results['ai_success_rate'] = (results['ai_successes'] / len(ai_parishes)
                                    if ai_parishes else 0)

        logger.info(f"🧪 Simple A/B Test Results:")
        logger.info(f"   Keyword: {results['keyword_successes']}/{len(keyword_parishes)} ({results['keyword_success_rate']:.1%})")
        logger.info(f"   AI: {results['ai_successes']}/{len(ai_parishes)} ({results['ai_success_rate']:.1%})")

        return results


def main():
    parser = argparse.ArgumentParser(description="Simple A/B test for schedule extraction")
    parser.add_argument("--num_parishes", type=int, default=10, help="Number of parishes to test")
    parser.add_argument("--test_ratio", type=float, default=0.5, help="Fraction for AI method")

    args = parser.parse_args()

    supabase = get_supabase_client()
    if not supabase:
        logger.error("Could not initialize Supabase client")
        return

    tester = SimpleABTestExtractor(supabase, args.test_ratio)
    results = tester.run_simple_ab_test(args.num_parishes)

    logger.info("🎉 Simple A/B test completed!")


if __name__ == '__main__':
    main()