#!/usr/bin/env python3
"""
Test Parish URL Consistency Between ParishesTestSet and Parishes Tables

This test validates that the Web URLs in ParishesTestSet match the URLs
in the Parishes table for diocese 2024 (Archdiocese of Atlanta).

This test can be run as part of CI/CD pipeline to ensure data consistency.
"""

import sys
from typing import Dict, List, Tuple

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
    _print_test_header(diocese_id)

    supabase = _initialize_test_client()
    if not supabase:
        return False

    testset_urls, parishes_urls = _fetch_url_data(supabase, diocese_id)
    if not _validate_data_exists(testset_urls, parishes_urls):
        return False

    comparison_results = _compare_and_analyze_urls(testset_urls, parishes_urls)
    _report_test_results(comparison_results, testset_urls, parishes_urls)

    return _determine_test_outcome(comparison_results)


def _print_test_header(diocese_id: int):
    """Print test header information"""
    print(f"🔍 Testing URL consistency for diocese {diocese_id} (Archdiocese of Atlanta)")
    print("=" * 70)


def _initialize_test_client():
    """Initialize Supabase client for testing"""
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Failed to initialize Supabase client")
        return None
    print("✅ Supabase client initialized")
    return supabase


def _fetch_url_data(supabase, diocese_id: int):
    """Fetch URL data from both tables"""
    print("\n📊 Fetching data from tables...")
    testset_urls = get_parishes_testset_urls(supabase, diocese_id)
    parishes_urls = get_parishes_urls(supabase, diocese_id)

    print(f"   • ParishesTestSet: {len(testset_urls)} parishes")
    print(f"   • Parishes: {len(parishes_urls)} parishes")

    return testset_urls, parishes_urls


def _validate_data_exists(testset_urls: list, parishes_urls: list) -> bool:
    """Validate that data exists in at least one table"""
    if not testset_urls and not parishes_urls:
        print("❌ No data found in either table")
        return False
    return True


def _compare_and_analyze_urls(testset_urls: list, parishes_urls: list) -> dict:
    """Compare URLs and return analysis results"""
    print("\n🔗 Comparing URLs...")
    url_matches, url_mismatches, only_in_testset, only_in_parishes = compare_parish_urls(testset_urls, parishes_urls)

    return {
        "url_matches": url_matches,
        "url_mismatches": url_mismatches,
        "only_in_testset": only_in_testset,
        "only_in_parishes": only_in_parishes,
    }


def _report_test_results(comparison_results: dict, testset_urls: list, parishes_urls: list):
    """Report detailed test results"""
    print("\n📋 RESULTS:")
    print("=" * 40)

    _report_url_matches(comparison_results["url_matches"])
    _report_url_mismatches(comparison_results["url_mismatches"])
    _report_unique_entries(comparison_results["only_in_testset"], "ParishesTestSet")
    _report_unique_entries(comparison_results["only_in_parishes"], "Parishes")
    _report_summary_statistics(comparison_results, testset_urls, parishes_urls)


def _report_url_matches(url_matches: list):
    """Report URL matches"""
    print(f"✅ URL Matches: {len(url_matches)}")
    if url_matches:
        print("   Parishes with matching URLs:")
        for match in url_matches[:5]:  # Show first 5
            url_display = match["url"] if match["url"] else "(No URL)"
            print(f"     • {match['parish']}: {url_display}")
        if len(url_matches) > 5:
            print(f"     ... and {len(url_matches) - 5} more")


def _report_url_mismatches(url_mismatches: list):
    """Report URL mismatches"""
    print(f"\n❌ URL Mismatches: {len(url_mismatches)}")
    if url_mismatches:
        print("   Parishes with different URLs:")
        for mismatch in url_mismatches:
            print(f"     • {mismatch['parish']}:")
            print(f"       TestSet: {mismatch['testset_url']}")
            print(f"       Parishes: {mismatch['parishes_url']}")


def _report_unique_entries(entries: list, table_name: str):
    """Report entries unique to one table"""
    print(f"\n📤 Only in {table_name}: {len(entries)}")
    if entries:
        for entry in entries[:3]:  # Show first 3
            url_display = entry["url"] if entry["url"] else "(No URL)"
            print(f"     • {entry['parish']}: {url_display}")
        if len(entries) > 3:
            print(f"     ... and {len(entries) - 3} more")


def _report_summary_statistics(comparison_results: dict, testset_urls: list, parishes_urls: list):
    """Report summary statistics"""
    url_matches = comparison_results["url_matches"]
    url_mismatches = comparison_results["url_mismatches"]

    total_common = len(url_matches) + len(url_mismatches)
    match_percentage = (len(url_matches) / total_common * 100) if total_common > 0 else 0

    print("\n📊 SUMMARY:")
    print(f"   • Common parishes: {total_common}")
    print(f"   • URL match rate: {match_percentage:.1f}%")
    print(f"   • Data coverage: TestSet={len(testset_urls)}, Parishes={len(parishes_urls)}")


def _determine_test_outcome(comparison_results: dict) -> bool:
    """Determine and report test outcome"""
    url_matches = comparison_results["url_matches"]
    url_mismatches = comparison_results["url_mismatches"]

    total_common = len(url_matches) + len(url_mismatches)
    test_passed = len(url_mismatches) == 0 and total_common > 0

    if test_passed:
        print("\n🎉 TEST PASSED: All URLs are consistent!")
    else:
        print(f"\n❌ TEST FAILED: Found {len(url_mismatches)} URL mismatches")

    return test_passed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test parish URL consistency between tables")
    parser.add_argument(
        "--diocese - id",
        type=int,
        default=2024,
        help="Diocese ID to test (default: 2024 for Archdiocese of Atlanta)",
    )

    args = parser.parse_args()

    success = run_url_consistency_test(args.diocese_id)
    sys.exit(0 if success else 1)
