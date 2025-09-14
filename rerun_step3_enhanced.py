#!/usr/bin/env python3
"""
Re-run Step 3 with Enhanced Extraction

This script re-runs parish extraction (Step 3) on specific dioceses
with enhanced website detection to improve coverage.
"""

import argparse
import subprocess
import sys

import config
from core.db import get_supabase_client
from core.logger import get_logger

logger = get_logger(__name__)

class EnhancedStep3Runner:
    """Re-run Step 3 with enhanced capabilities."""

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def get_dioceses_with_low_website_coverage(self, limit: int = 5) -> list:
        """Find dioceses with parishes but low website coverage."""
        try:
            # Get all dioceses with their parish counts and website counts
            dioceses_response = self.supabase.table('Dioceses').select('id, Name, Website').execute()
            dioceses = dioceses_response.data

            diocese_stats = []

            for diocese in dioceses:
                diocese_id = diocese['id']
                diocese_name = diocese['Name']
                diocese_url = diocese['Website']

                # Get parish count for this diocese
                parishes_response = self.supabase.table('Parishes').select('id, Web').eq('diocese_id', diocese_id).execute()
                total_parishes = len(parishes_response.data)

                if total_parishes == 0:
                    continue  # Skip dioceses with no parishes

                # Count parishes with websites
                parishes_with_websites = len([p for p in parishes_response.data if p.get('Web')])

                coverage_rate = (parishes_with_websites / total_parishes * 100) if total_parishes > 0 else 0

                diocese_stats.append({
                    'id': diocese_id,
                    'name': diocese_name,
                    'url': diocese_url,
                    'total_parishes': total_parishes,
                    'with_websites': parishes_with_websites,
                    'coverage_rate': coverage_rate
                })

            # Sort by total parishes (prioritize dioceses with more parishes but low coverage)
            diocese_stats.sort(key=lambda x: (x['total_parishes'], -x['coverage_rate']), reverse=True)

            return diocese_stats[:limit]

        except Exception as e:
            logger.error(f"Error getting diocese statistics: {e}")
            return []

    def run_step3_for_diocese(self, diocese_id: int, max_parishes: int = 20) -> bool:
        """Run Step 3 (parish extraction) for a specific diocese."""
        try:
            logger.info(f"🔄 Running Step 3 for diocese {diocese_id} (max {max_parishes} parishes)")

            # Run extract_parishes.py with specific diocese
            cmd = [
                sys.executable, 'extract_parishes.py',
                '--diocese_id', str(diocese_id),
                '--num_parishes_per_diocese', str(max_parishes)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                logger.info(f"✅ Step 3 completed successfully for diocese {diocese_id}")
                return True
            else:
                logger.error(f"❌ Step 3 failed for diocese {diocese_id}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"❌ Step 3 timed out for diocese {diocese_id}")
            return False
        except Exception as e:
            logger.error(f"❌ Error running Step 3 for diocese {diocese_id}: {e}")
            return False

    def enhance_existing_parishes(self, diocese_id: int) -> int:
        """Enhance existing parishes in a diocese by finding missing websites."""
        try:
            from run_enhanced_parish_extraction import EnhancedParishExtraction

            enhancer = EnhancedParishExtraction(self.supabase)

            # Get parishes without websites for this diocese
            parishes_response = self.supabase.table('Parishes').select('id, Name, extraction_method').eq('diocese_id', diocese_id).is_('Web', 'null').execute()
            parishes_without_websites = parishes_response.data

            if not parishes_without_websites:
                logger.info(f"  All parishes in diocese {diocese_id} already have websites")
                return 0

            logger.info(f"  🔍 Enhancing {len(parishes_without_websites)} parishes without websites")

            websites_found = 0
            for parish in parishes_without_websites[:10]:  # Limit to 10 to avoid timeout
                website = enhancer._find_parish_website(parish)
                if website:
                    # Update parish with found website
                    self.supabase.table('Parishes').update({'Web': website}).eq('id', parish['id']).execute()
                    websites_found += 1
                    logger.info(f"    ✅ Found website for {parish['Name']}: {website}")

            return websites_found

        except Exception as e:
            logger.error(f"Error enhancing parishes: {e}")
            return 0

    def comprehensive_enhancement(self, limit: int = 3) -> dict:
        """Run comprehensive enhancement on dioceses with low website coverage."""
        dioceses = self.get_dioceses_with_low_website_coverage(limit)

        if not dioceses:
            logger.info("No dioceses found for enhancement")
            return {}

        results = {
            'dioceses_processed': 0,
            'total_parishes_extracted': 0,
            'total_websites_found': 0,
            'dioceses': []
        }

        logger.info(f"🚀 Starting comprehensive enhancement on {len(dioceses)} dioceses")

        for diocese in dioceses:
            diocese_id = diocese['id']
            diocese_name = diocese['name']

            logger.info(f"\n📍 Processing: {diocese_name} (ID: {diocese_id})")
            logger.info(f"   Current: {diocese['with_websites']}/{diocese['total_parishes']} parishes with websites ({diocese['coverage_rate']:.1f}%)")

            diocese_result = {
                'id': diocese_id,
                'name': diocese_name,
                'initial_coverage': diocese['coverage_rate'],
                'parishes_extracted': 0,
                'websites_found': 0,
                'final_coverage': diocese['coverage_rate']
            }

            # Step 1: Try to extract more parishes (if there are unextracted ones)
            if diocese['total_parishes'] < 10:  # If diocese has very few parishes, try to extract more
                success = self.run_step3_for_diocese(diocese_id, 30)
                if success:
                    # Check how many new parishes were found
                    new_count_response = self.supabase.table('Parishes').select('id').eq('diocese_id', diocese_id).execute()
                    new_total = len(new_count_response.data)
                    new_parishes = new_total - diocese['total_parishes']
                    diocese_result['parishes_extracted'] = new_parishes
                    results['total_parishes_extracted'] += new_parishes
                    logger.info(f"   ✅ Extracted {new_parishes} new parishes")

            # Step 2: Enhance existing parishes without websites
            websites_found = self.enhance_existing_parishes(diocese_id)
            diocese_result['websites_found'] = websites_found
            results['total_websites_found'] += websites_found

            # Step 3: Calculate final coverage
            final_response = self.supabase.table('Parishes').select('id, Web').eq('diocese_id', diocese_id).execute()
            final_total = len(final_response.data)
            final_with_websites = len([p for p in final_response.data if p.get('Web')])
            final_coverage = (final_with_websites / final_total * 100) if final_total > 0 else 0
            diocese_result['final_coverage'] = final_coverage

            results['dioceses_processed'] += 1
            results['dioceses'].append(diocese_result)

            logger.info(f"   📈 Final coverage: {final_with_websites}/{final_total} parishes ({final_coverage:.1f}%)")
            improvement = final_coverage - diocese['coverage_rate']
            if improvement > 0:
                logger.info(f"   🎉 Improvement: +{improvement:.1f} percentage points")

        return results


def main():
    parser = argparse.ArgumentParser(description="Re-run Step 3 with enhanced website extraction")
    parser.add_argument("--dioceses", type=int, default=3, help="Number of dioceses to process")
    parser.add_argument("--diocese_id", type=int, help="Specific diocese ID to process")
    parser.add_argument("--list_candidates", action="store_true", help="List dioceses that could benefit from enhancement")

    args = parser.parse_args()

    if not config.validate_config():
        logger.error("Configuration validation failed")
        return

    supabase = get_supabase_client()
    if not supabase:
        logger.error("Could not initialize Supabase client")
        return

    runner = EnhancedStep3Runner(supabase)

    if args.list_candidates:
        logger.info("🔍 Finding dioceses with low website coverage...")
        dioceses = runner.get_dioceses_with_low_website_coverage(10)

        logger.info(f"\n📊 Top 10 Dioceses for Enhancement:")
        logger.info("=" * 80)
        for i, diocese in enumerate(dioceses, 1):
            logger.info(f"{i:2}. {diocese['name']}")
            logger.info(f"    Parishes: {diocese['total_parishes']} | With websites: {diocese['with_websites']} | Coverage: {diocese['coverage_rate']:.1f}%")
            logger.info(f"    Diocese ID: {diocese['id']}")
        return

    if args.diocese_id:
        logger.info(f"🔄 Processing specific diocese: {args.diocese_id}")
        success = runner.run_step3_for_diocese(args.diocese_id, 30)
        if success:
            websites_found = runner.enhance_existing_parishes(args.diocese_id)
            logger.info(f"✅ Completed! Found {websites_found} additional websites")
        return

    logger.info(f"🚀 Starting comprehensive enhancement for {args.dioceses} dioceses")
    results = runner.comprehensive_enhancement(args.dioceses)

    if results:
        logger.info("\n🎉 Comprehensive Enhancement Results:")
        logger.info(f"   Dioceses processed: {results['dioceses_processed']}")
        logger.info(f"   New parishes extracted: {results['total_parishes_extracted']}")
        logger.info(f"   New websites found: {results['total_websites_found']}")

        for diocese in results['dioceses']:
            improvement = diocese['final_coverage'] - diocese['initial_coverage']
            logger.info(f"\n   📍 {diocese['name']}:")
            logger.info(f"      Coverage: {diocese['initial_coverage']:.1f}% → {diocese['final_coverage']:.1f}% (+{improvement:.1f}pp)")
            logger.info(f"      New parishes: {diocese['parishes_extracted']}")
            logger.info(f"      New websites: {diocese['websites_found']}")


if __name__ == '__main__':
    main()