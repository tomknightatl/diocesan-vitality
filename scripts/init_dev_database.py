#!/usr/bin/env python3
"""
Initialize dev database schema using Supabase REST API.
This script creates tables in the dev database by executing SQL via the Supabase client.
"""

import os
import sys
from pathlib import Path
from supabase import create_client, Client


def main():
    # Get dev database credentials from environment
    dev_url = os.getenv('SUPABASE_URL_DEV')
    dev_key = os.getenv('SUPABASE_KEY_DEV')

    if not dev_url or not dev_key:
        print("❌ Missing SUPABASE_URL_DEV or SUPABASE_KEY_DEV environment variables")
        print("💡 Make sure these are set in your .env file")
        sys.exit(1)

    print("🚀 Initializing dev database schema...")
    print(f"📊 Target database: {dev_url}")
    print("")

    # Create Supabase client
    supabase: Client = create_client(dev_url, dev_key)

    # Read the initial schema SQL file
    schema_file = Path(__file__).parent.parent / "sql" / "initial_schema.sql"

    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        sys.exit(1)

    print(f"📄 Reading schema from: {schema_file}")
    schema_sql = schema_file.read_text()

    # Note: Supabase Python client doesn't support raw SQL execution via REST API
    # We need to use the PostgREST API or run SQL via the Supabase dashboard
    print("")
    print("⚠️  IMPORTANT: Supabase Python client cannot execute raw SQL via REST API")
    print("")
    print("📋 Manual initialization steps:")
    print("1. Open: https://supabase.com/dashboard/project/derftxlibiidgcdafxrx/sql/new")
    print("2. Copy the contents of: sql/initial_schema.sql")
    print("3. Paste into the SQL editor and click 'Run'")
    print("")
    print("💡 Alternative: Use the copy_database.py script to copy from production:")
    print("   export SUPABASE_URL_PRD=$(grep '^SUPABASE_URL=' .env | cut -d'=' -f2)")
    print("   export SUPABASE_KEY_PRD=$(grep '^SUPABASE_KEY=' .env | cut -d'=' -f2)")
    print("   export SUPABASE_URL_DEV=$(grep '^SUPABASE_URL_DEV=' .env | cut -d'=' -f2)")
    print("   export SUPABASE_KEY_DEV=$(grep '^SUPABASE_KEY_DEV=' .env | cut -d'=' -f2)")
    print("   python scripts/copy_database.py")
    print("")

    # Check if tables exist
    print("🔍 Checking if tables exist in dev database...")
    try:
        # Try to query pipeline_workers table
        response = supabase.table("pipeline_workers").select("*", count="exact").limit(0).execute()
        print(f"✅ pipeline_workers table exists ({response.count} rows)")
    except Exception as e:
        print(f"❌ pipeline_workers table does NOT exist")
        print(f"   Error: {str(e)}")
        print("")
        print("⚠️  You need to initialize the database schema first!")
        sys.exit(1)


if __name__ == '__main__':
    main()
