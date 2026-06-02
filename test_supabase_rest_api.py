#!/usr/bin/env python3
"""
Test script to verify PRD Supabase connection using the Supabase Python client.
This tests the REST API connection which works over IPv4.
"""

import os
import sys
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ ERROR: supabase Python library not installed")
    print("   Install it with: pip install supabase")
    sys.exit(1)

def test_supabase_rest_api():
    """Test connection to Supabase using REST API"""

    # Load environment variables
    load_dotenv()

    # Get credentials
    supabase_url = os.getenv('SUPABASE_URL_PRD')
    supabase_key = os.getenv('SUPABASE_KEY_PRD')

    # Validate credentials
    if not supabase_url or not supabase_key:
        print("❌ ERROR: Missing required credentials")
        if not supabase_url:
            print("   - SUPABASE_URL_PRD not found")
        if not supabase_key:
            print("   - SUPABASE_KEY_PRD not found")
        return False

    # Mask key for display
    masked_key = supabase_key[:20] + '...' + supabase_key[-20:] if len(supabase_key) > 40 else '***'

    print("=" * 70)
    print("Testing PRD Supabase REST API Connection")
    print("=" * 70)
    print(f"URL: {supabase_url}")
    print(f"Key: {masked_key}")
    print("=" * 70)

    try:
        print("\n🔄 Initializing Supabase client...")
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized successfully")

        print("\n🔄 Testing database access...")
        # Try to query the Dioceses table
        response = supabase.table('Dioceses').select('*').limit(1).execute()

        print("✅ Database query successful!")
        print(f"\n📊 Query Results:")
        print(f"   Status: {response.status_code}")
        print(f"   Data count: {len(response.data)}")

        if response.data:
            print(f"   Sample record:")
            for key, value in list(response.data[0].items())[:3]:
                print(f"      {key}: {value}")

        print("\n✅ Connection test completed successfully!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n❌ ERROR: Connection test failed")
        print(f"\n🔍 Error Details:")
        print(f"   {type(e).__name__}: {e}")

        # Provide troubleshooting suggestions
        error_str = str(e).lower()

        if "api" in error_str or "key" in error_str:
            print("\n💡 Troubleshooting Suggestions:")
            print("   - Verify the Supabase URL is correct")
            print("   - Check if the API key is valid and has proper permissions")
            print("   - Ensure the API key is not expired")

        elif "network" in error_str or "connection" in error_str:
            print("\n💡 Troubleshooting Suggestions:")
            print("   - Check internet connectivity")
            print("   - Verify the Supabase URL is reachable")
            print("   - Check firewall rules")

        elif "table" in error_str or "permission" in error_str:
            print("\n💡 Troubleshooting Suggestions:")
            print("   - Verify the table exists in the database")
            print("   - Check if the API key has proper permissions")
            print("   - Ensure Row Level Security (RLS) policies allow access")

        print("\n" + "=" * 70)
        return False

if __name__ == "__main__":
    success = test_supabase_rest_api()
    sys.exit(0 if success else 1)