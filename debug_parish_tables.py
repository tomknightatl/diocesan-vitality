#!/usr/bin/env python3
"""
Debug script to examine parish data in both tables
"""

from core.db import get_supabase_client

def debug_parish_tables():
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Failed to initialize Supabase client")
        return

    # Get all parishes from both tables for diocese 2024
    print("🔍 Checking Parishes table for diocese 2024...")
    parishes_response = supabase.table('Parishes').select('Name, Web, created_at').eq('diocese_id', 2024).order('created_at', desc=True).execute()

    print("🔍 Checking ParishesTestSet table for diocese 2024...")
    testset_response = supabase.table('ParishesTestSet').select('Name, Web, created_at').eq('diocese_id', 2024).order('created_at', desc=True).execute()

    print(f"\n📊 Parishes table: {len(parishes_response.data)} records")
    print("Recent parishes:")
    for i, parish in enumerate(parishes_response.data[:10]):
        print(f"  {i+1}. {parish['Name']} | {parish.get('Web', 'No URL')} | {parish.get('created_at', 'No date')}")
    if len(parishes_response.data) > 10:
        print(f"  ... and {len(parishes_response.data) - 10} more")

    print(f"\n📊 ParishesTestSet table: {len(testset_response.data)} records")
    print("Recent test parishes:")
    for i, parish in enumerate(testset_response.data[:10]):
        print(f"  {i+1}. {parish['Name']} | {parish.get('Web', 'No URL')} | {parish.get('created_at', 'No date')}")
    if len(testset_response.data) > 10:
        print(f"  ... and {len(testset_response.data) - 10} more")

    # Check for specific parishes that should match
    test_names = {p['Name'] for p in testset_response.data}
    parish_names = {p['Name'] for p in parishes_response.data}

    common = test_names.intersection(parish_names)
    only_test = test_names - parish_names
    only_parishes = parish_names - test_names

    print(f"\n🔗 Common parish names: {len(common)}")
    for name in sorted(list(common))[:5]:
        print(f"  • {name}")
    if len(common) > 5:
        print(f"  ... and {len(common) - 5} more")

    print(f"\n📤 Only in TestSet: {len(only_test)}")
    for name in sorted(list(only_test))[:5]:
        print(f"  • {name}")
    if len(only_test) > 5:
        print(f"  ... and {len(only_test) - 5} more")

    print(f"\n📥 Only in Parishes: {len(only_parishes)}")
    for name in sorted(list(only_parishes))[:5]:
        print(f"  • {name}")
    if len(only_parishes) > 5:
        print(f"  ... and {len(only_parishes) - 5} more")

if __name__ == "__main__":
    debug_parish_tables()