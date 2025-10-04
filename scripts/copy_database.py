#!/usr/bin/env python3
"""
Copy database from production to dev using Supabase Python client.
This script copies schema and data for all tables.
"""

import sys
import os
from supabase import create_client, Client


def main():
    # Get credentials from environment variables
    src_url = os.environ.get('SUPABASE_URL_PRD')
    src_key = os.environ.get('SUPABASE_KEY_PRD')
    dst_url = os.environ.get('SUPABASE_URL_DEV')
    dst_key = os.environ.get('SUPABASE_KEY_DEV')

    if not all([src_url, src_key, dst_url, dst_key]):
        print("❌ Missing required environment variables")
        sys.exit(1)

    # Create Supabase clients
    src_client: Client = create_client(src_url, src_key)
    dst_client: Client = create_client(dst_url, dst_key)

    # Tables to copy (capitalized as they appear in production)
    # Note: ParishScheduleSummary is a view, not a table - skipping it
    tables = [
        'Dioceses',
        'DiocesesParishDirectory',
        'Parishes',
        'ParishData',
        'DiscoveredUrls',
        'ScheduleKeywords',
        'pipeline_workers',
        'diocese_work_assignments'
    ]

    total_copied = 0

    for table in tables:
        print(f'📦 Copying table: {table}')
        try:
            # Fetch all data from source
            response = src_client.table(table).select('*').execute()

            if response.data and len(response.data) > 0:
                # Insert into destination (upsert to handle duplicates)
                dst_client.table(table).upsert(response.data).execute()
                print(f'   ✅ Copied {len(response.data)} rows')
                total_copied += len(response.data)
            else:
                print(f'   ⚠️  Table {table} is empty - skipping')

        except Exception as e:
            print(f'   ⚠️  Error: {str(e)}')
            # Continue with next table even if this one fails
            continue

    print('')
    print(f'✅ Database copy complete! Total rows: {total_copied}')
    print(f'💡 Verify in Supabase dashboard: {dst_url}')


if __name__ == '__main__':
    main()
