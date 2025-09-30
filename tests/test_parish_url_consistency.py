#!/usr/bin/env python3
"""
Test Parish URL Consistency Between ParishesTestSet and Parishes Tables

This test validates that the Web URLs in ParishesTestSet match the URLs
in the Parishes table for diocese 2024 (Archdiocese of Atlanta).

This test can be run as part of CI/CD pipeline to ensure data consistency.
"""

import sys
from typing import Dict, List, Set, Tuple

from core.db import get_supabase_client
from supabase import Client


def get_parishes_testset_urls(supabase: Client, diocese_id: int) -> Dict[str, str]:
    """Get Web URLs from ParishesTestSet table for given diocese"""
    try:
        response = supabase.table("ParishesTestSet").select("Name, Web").eq("diocese_id", diocese_id).execute()

        if not response.data:
            print(f"⚠️  No records found in ParishesTestSet for diocese_id {diocese_id}")
            return {}

        # Create mapping of parish name to URL (handle None URLs)
        url_map = {}
        for parish in response.data:
            name = parish.get("Name", "").strip()
            url = parish.get("Web")
            if name:  # Only include parishes with names
                url_map[name] = url if url else None

        return url_map

    except Exception as e:
        print(f"❌ Error fetching ParishesTestSet data: {e}")
        return {}


def get_parishes_urls(supabase: Client, diocese_id: int) -> Dict[str, str]:
    """Get Web URLs from Parishes table for given diocese"""
    try:
        response = supabase.table("Parishes").select("Name, Web").eq("diocese_id", diocese_id).execute()

        if not response.data:
            print(f"⚠️  No records found in Parishes for diocese_id {diocese_id}")
            return {}

        # Create mapping of parish name to URL (handle None URLs)
        url_map = {}
        for parish in response.data:
            name = parish.get("Name", "").strip()
            url = parish.get("Web")
            if name:  # Only include parishes with names
                url_map[name] = url if url else None

        return url_map

    except Exception as e:
        print(f"❌ Error fetching Parishes data: {e}")
        return {}


def normalize_url(url: str) -> str:
    """Normalize URL for comparison (handle common variations)"""
    if not url:
        return ""

    url = url.strip().lower()

    # Remove trailing slash
    if url.endswith("/"):
        url = url[:-1]

    # Ensure protocol
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Convert http to https for comparison
    if url.startswith("http://"):
        url = url.replace("http://", "https://", 1)

    return url


def compare_parish_urls(testset_urls: Dict[str, str], parishes_urls: Dict[str, str]) -> Tuple[List, List, List, List]:
    """Compare URLs between testset and parishes tables"""

    # Normalize URLs for comparison
    testset_normalized = {name: normalize_url(url) for name, url in testset_urls.items()}
    parishes_normalized = {name: normalize_url(url) for name, url in parishes_urls.items()}

    testset_names = set(testset_normalized.keys())
    parishes_names = set(parishes_normalized.keys())

    # Find parishes in both tables
    common_parishes = testset_names.intersection(parishes_names)

    # Find mismatches
    url_mismatches = []
    url_matches = []

    for parish_name in common_parishes:
        testset_url = testset_normalized[parish_name]
        parishes_url = parishes_normalized[parish_name]

        if testset_url == parishes_url:
            url_matches.append({"parish": parish_name, "url": testset_urls[parish_name]})  # Use original URL for display
        else:
            url_mismatches.append(
                {
                    "parish": parish_name,
                    "testset_url": testset_urls[parish_name],
                    "parishes_url": parishes_urls[parish_name],
                    "testset_normalized": testset_url,
                    "parishes_normalized": parishes_url,
                }
            )

    # Find parishes only in one table
    only_in_testset = [{"parish": name, "url": testset_urls[name]} for name in testset_names - parishes_names]
    only_in_parishes = [{"parish": name, "url": parishes_urls[name]} for name in parishes_names - testset_names]

    return url_matches, url_mismatches, only_in_testset, only_in_parishes


def run_url_consistency_test(diocese_id: int = 2024) -> bool:
    """Run the URL consistency test and return True if all URLs match"""

    print(f"🔍 Testing URL consistency for diocese {diocese_id} (Archdiocese of Atlanta)")
    print("=" * 70)

    # Initialize Supabase client
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Failed to initialize Supabase client")
        return False
    print("✅ Supabase client initialized")

    # Get URLs from both tables
    print("\n📊 Fetching data from tables...")
    testset_urls = get_parishes_testset_urls(supabase, diocese_id)
    parishes_urls = get_parishes_urls(supabase, diocese_id)

    if not testset_urls and not parishes_urls:
        print("❌ No data found in either table")
        return False

    print(f"   • ParishesTestSet: {len(testset_urls)} parishes")
    print(f"   • Parishes: {len(parishes_urls)} parishes")

    # Compare URLs
    print("\n🔗 Comparing URLs...")
    url_matches, url_mismatches, only_in_testset, only_in_parishes = compare_parish_urls(testset_urls, parishes_urls)

    # Report results
    print("\n📋 RESULTS:")
    print("=" * 40)

    print(f"✅ URL Matches: {len(url_matches)}")
    if url_matches:
        print("   Parishes with matching URLs:")
        for match in url_matches[:5]:  # Show first 5
            url_display = match["url"] if match["url"] else "(No URL)"
            print(f"     • {match['parish']}: {url_display}")
        if len(url_matches) > 5:
            print(f"     ... and {len(url_matches) - 5} more")

    print(f"\n❌ URL Mismatches: {len(url_mismatches)}")
    if url_mismatches:
        print("   Parishes with different URLs:")
        for mismatch in url_mismatches:
            print(f"     • {mismatch['parish']}:")
            print(f"       TestSet: {mismatch['testset_url']}")
            print(f"       Parishes: {mismatch['parishes_url']}")

    print(f"\n📤 Only in ParishesTestSet: {len(only_in_testset)}")
    if only_in_testset:
        for parish in only_in_testset[:3]:  # Show first 3
            url_display = parish["url"] if parish["url"] else "(No URL)"
            print(f"     • {parish['parish']}: {url_display}")
        if len(only_in_testset) > 3:
            print(f"     ... and {len(only_in_testset) - 3} more")

    print(f"\n📥 Only in Parishes: {len(only_in_parishes)}")
    if only_in_parishes:
        for parish in only_in_parishes[:3]:  # Show first 3
            url_display = parish["url"] if parish["url"] else "(No URL)"
            print(f"     • {parish['parish']}: {url_display}")
        if len(only_in_parishes) > 3:
            print(f"     ... and {len(only_in_parishes) - 3} more")

    # Calculate success metrics
    total_common = len(url_matches) + len(url_mismatches)
    match_percentage = (len(url_matches) / total_common * 100) if total_common > 0 else 0

    print(f"\n📊 SUMMARY:")
    print(f"   • Common parishes: {total_common}")
    print(f"   • URL match rate: {match_percentage:.1f}%")
    print(f"   • Data coverage: TestSet={len(testset_urls)}, Parishes={len(parishes_urls)}")

    # Determine test result
    test_passed = len(url_mismatches) == 0 and total_common > 0

    if test_passed:
        print(f"\n🎉 TEST PASSED: All URLs are consistent!")
    else:
        print(f"\n❌ TEST FAILED: Found {len(url_mismatches)} URL mismatches")

    return test_passed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test parish URL consistency between tables")
    parser.add_argument(
        "--diocese-id", type=int, default=2024, help="Diocese ID to test (default: 2024 for Archdiocese of Atlanta)"
    )

    args = parser.parse_args()

    success = run_url_consistency_test(args.diocese_id)
    sys.exit(0 if success else 1)
