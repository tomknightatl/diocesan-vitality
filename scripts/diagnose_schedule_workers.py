#!/usr/bin/env python3
"""
Quick diagnostic for schedule worker issues - Issue #106

Run from project root:
    python3 scripts/diagnose_schedule_workers.py

This script checks:
1. Database connectivity
2. Parishes available for processing
3. Blocking statistics
4. Active workers status
5. Recent data collection
6. Parish selection logic
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.db import get_supabase_client
from core.logger import get_logger

logger = get_logger(__name__)


def diagnose_schedule_workers():
    """Run comprehensive diagnostics on schedule workers."""

    logger.info("="*80)
    logger.info("🔍 SCHEDULE WORKER DIAGNOSTIC - Issue #106")
    logger.info("="*80)

    # Test 1: Database Connection
    logger.info("\n📊 Test 1: Database Connection")
    logger.info("-" * 40)
    supabase = get_supabase_client()
    if not supabase:
        logger.error("❌ Cannot connect to database")
        logger.error("   Check SUPABASE_URL and SUPABASE_KEY in .env")
        return False

    logger.info("✅ Database connection successful")

    # Test 2: Parishes with Websites
    logger.info("\n📊 Test 2: Parishes with Websites")
    logger.info("-" * 40)
    try:
        parishes_response = (
            supabase.table("Parishes")
            .select("id", count="exact")
            .not_.is_("Web", "null")
            .execute()
        )
        total_with_websites = parishes_response.count if hasattr(parishes_response, 'count') else len(parishes_response.data)
        logger.info(f"✅ Total parishes with websites: {total_with_websites}")

        if total_with_websites == 0:
            logger.error("❌ CRITICAL: No parishes have website URLs!")
            logger.error("   This would cause 0% success rate")
            return False

    except Exception as e:
        logger.error(f"❌ Error checking parishes: {e}")
        return False

    # Test 3: Parishes Without Schedule Data
    logger.info("\n📊 Test 3: Parishes Without Schedule Data")
    logger.info("-" * 40)
    try:
        # Count parishes that have a website but no ParishData records
        all_parishes_query = (
            supabase.table("Parishes")
            .select("id")
            .not_.is_("Web", "null")
            .execute()
        )
        all_parish_ids = [p['id'] for p in all_parishes_query.data]

        parish_data_query = (
            supabase.table("ParishData")
            .select("parish_id")
            .in_("parish_id", all_parish_ids)
            .execute()
        )
        parish_ids_with_data = set(pd['parish_id'] for pd in parish_data_query.data)

        parishes_without_data = len(all_parish_ids) - len(parish_ids_with_data)

        logger.info(f"✅ Parishes WITH schedule data: {len(parish_ids_with_data)}")
        logger.info(f"⚠️  Parishes WITHOUT schedule data: {parishes_without_data}")

        if parishes_without_data == 0:
            logger.warning("⚠️  WARNING: All parishes already have schedule data")
            logger.warning("   This might explain why no new extractions are happening")

    except Exception as e:
        logger.error(f"❌ Error checking parish data: {e}")

    # Test 4: Blocking Statistics
    logger.info("\n📊 Test 4: Blocking Statistics")
    logger.info("-" * 40)
    try:
        blocking_query = (
            supabase.table("Parishes")
            .select("is_blocked, blocking_type")
            .not_.is_("Web", "null")
            .execute()
        )

        blocked_count = sum(1 for p in blocking_query.data if p.get('is_blocked'))
        total_parishes = len(blocking_query.data)
        blocked_percentage = (blocked_count / total_parishes * 100) if total_parishes > 0 else 0

        logger.info(f"📊 Blocked parishes: {blocked_count}/{total_parishes} ({blocked_percentage:.1f}%)")

        # Group by blocking type
        blocking_types = {}
        for p in blocking_query.data:
            if p.get('is_blocked'):
                block_type = p.get('blocking_type', 'unknown')
                blocking_types[block_type] = blocking_types.get(block_type, 0) + 1

        if blocking_types:
            logger.info("   Blocking types:")
            for block_type, count in sorted(blocking_types.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"     - {block_type}: {count}")

        if blocked_percentage > 50:
            logger.error(f"❌ CRITICAL: {blocked_percentage:.1f}% of parishes are blocked!")
            logger.error("   This would cause low success rate")

    except Exception as e:
        logger.error(f"❌ Error checking blocking stats: {e}")

    # Test 5: Active Workers
    logger.info("\n📊 Test 5: Active Workers")
    logger.info("-" * 40)
    try:
        workers = (
            supabase.table("pipeline_workers")
            .select("*")
            .eq("status", "active")
            .execute()
        )

        logger.info(f"📊 Active workers: {len(workers.data)}")

        if len(workers.data) == 0:
            logger.warning("⚠️  WARNING: No active workers found")
            logger.warning("   Pipeline may not be running")
        else:
            for worker in workers.data:
                worker_type = worker.get('worker_type', 'unknown')
                logger.info(f"   - {worker['worker_id']} ({worker_type})")
                logger.info(f"     Last heartbeat: {worker.get('last_heartbeat', 'N/A')}")

                # Check for schedule workers
                if worker_type == 'schedule' or worker_type == 'all':
                    logger.info(f"     ✅ Schedule-capable worker found")

    except Exception as e:
        logger.error(f"❌ Error checking workers: {e}")

    # Test 6: Recent ParishData Records
    logger.info("\n📊 Test 6: Recent Parish Data Collection")
    logger.info("-" * 40)
    try:
        recent_data = (
            supabase.table("ParishData")
            .select("*", count="exact")
            .gte("created_at", "2025-09-01T00:00:00")
            .execute()
        )

        recent_count = recent_data.count if hasattr(recent_data, 'count') else len(recent_data.data)
        logger.info(f"📊 Parish data records since Sept 1, 2025: {recent_count}")

        if recent_count == 0:
            logger.error("❌ CRITICAL: No parish data collected since Sept 1!")
            logger.error("   This confirms 0% success rate")
        else:
            # Get most recent record
            latest = max(recent_data.data, key=lambda x: x.get('created_at', ''))
            logger.info(f"✅ Most recent: {latest.get('created_at', 'N/A')}")
            logger.info(f"   Fact type: {latest.get('fact_type', 'N/A')}")
            logger.info(f"   Parish ID: {latest.get('parish_id', 'N/A')}")

    except Exception as e:
        logger.error(f"❌ Error checking recent data: {e}")

    # Test 7: Parish Selection Logic
    logger.info("\n📊 Test 7: Parish Selection Logic")
    logger.info("-" * 40)
    try:
        from pipeline.extract_schedule import get_parishes_to_process

        test_parishes = get_parishes_to_process(supabase, num_parishes=10, parish_id=None, diocese_id=None)

        logger.info(f"📊 Test parish selection returned: {len(test_parishes)} parishes")

        if len(test_parishes) == 0:
            logger.error("❌ CRITICAL: Parish selection returned 0 parishes!")
            logger.error("   This would cause 0% success rate")
            logger.error("   Check intelligent_parish_prioritizer logic")
        else:
            logger.info(f"✅ Parish selection working")
            logger.info(f"   Sample parishes:")
            for i, (url, parish_id) in enumerate(test_parishes[:3], 1):
                logger.info(f"     {i}. ID={parish_id}, URL={url[:50]}...")

    except Exception as e:
        logger.error(f"❌ Error testing parish selection: {e}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")

    # Test 8: Work Assignments
    logger.info("\n📊 Test 8: Work Assignments")
    logger.info("-" * 40)
    try:
        assignments = (
            supabase.table("diocese_work_assignments")
            .select("*")
            .order("assigned_at", desc=True)
            .limit(10)
            .execute()
        )

        logger.info(f"📊 Recent work assignments: {len(assignments.data)}")

        if assignments.data:
            processing_count = sum(1 for a in assignments.data if a.get('status') == 'processing')
            completed_count = sum(1 for a in assignments.data if a.get('status') == 'completed')
            failed_count = sum(1 for a in assignments.data if a.get('status') == 'failed')

            logger.info(f"   Status breakdown:")
            logger.info(f"     - Processing: {processing_count}")
            logger.info(f"     - Completed: {completed_count}")
            logger.info(f"     - Failed: {failed_count}")

            # Check for stuck assignments
            from datetime import datetime, timezone
            import dateutil.parser

            stuck_assignments = []
            for assignment in assignments.data:
                if assignment.get('status') == 'processing':
                    assigned_at = dateutil.parser.parse(assignment['assigned_at'])
                    duration = datetime.now(timezone.utc) - assigned_at
                    if duration.total_seconds() > 7200:  # 2 hours
                        stuck_assignments.append(assignment)

            if stuck_assignments:
                logger.error(f"❌ Found {len(stuck_assignments)} stuck assignments (processing > 2 hours)")
                logger.error("   This could block new work from being assigned")
                logger.error("   Consider resetting these assignments")

    except Exception as e:
        logger.error(f"❌ Error checking work assignments: {e}")

    # Summary
    logger.info("\n" + "="*80)
    logger.info("📋 DIAGNOSTIC SUMMARY")
    logger.info("="*80)
    logger.info("\n✅ Completed diagnostic checks")
    logger.info("\nReview the output above for:")
    logger.info("  - ❌ CRITICAL errors (immediate attention required)")
    logger.info("  - ⚠️  WARNINGS (may contribute to low success rate)")
    logger.info("  - ✅ Successful checks")
    logger.info("\nNext steps:")
    logger.info("  1. Address any CRITICAL errors found")
    logger.info("  2. Review warnings for potential issues")
    logger.info("  3. Check production logs for detailed error messages")
    logger.info("  4. Test schedule extraction locally with single parish")
    logger.info("\nSee docs/TROUBLESHOOTING_106.md for detailed troubleshooting guide")
    logger.info("="*80)

    return True


if __name__ == "__main__":
    try:
        success = diagnose_schedule_workers()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Diagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n❌ Diagnostic failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
