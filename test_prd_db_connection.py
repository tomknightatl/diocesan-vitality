#!/usr/bin/env python3
"""
Test script to verify PRD Supabase database connection.
This script reads credentials from .env file and attempts to connect.
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2 import OperationalError

def test_prd_supabase_connection():
    """Test connection to PRD Supabase database using credentials from .env"""

    # Load environment variables from .env file
    load_dotenv()

    # Get PRD Supabase database credentials
    db_host = os.getenv('SUPABASE_DB_HOST_PRD')
    db_port = os.getenv('SUPABASE_DB_PORT_PRD')
    db_password = os.getenv('SUPABASE_DB_PASSWORD_PRD')
    db_user = 'postgres'  # Supabase default user
    db_name = 'postgres'  # Supabase default database

    # Validate required credentials
    missing_creds = []
    if not db_host:
        missing_creds.append('SUPABASE_DB_HOST_PRD')
    if not db_port:
        missing_creds.append('SUPABASE_DB_PORT_PRD')
    if not db_password:
        missing_creds.append('SUPABASE_DB_PASSWORD_PRD')

    if missing_creds:
        print(f"❌ ERROR: Missing required credentials: {', '.join(missing_creds)}")
        return False

    # Mask password for display
    masked_password = db_password[:4] + '...' + db_password[-4:] if len(db_password) > 8 else '***'

    print("=" * 60)
    print("Testing PRD Supabase Database Connection")
    print("=" * 60)
    print(f"Host: {db_host}")
    print(f"Port: {db_port}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print(f"Password: {masked_password}")
    print("=" * 60)

    # Attempt connection
    try:
        print("\n🔄 Attempting to connect to database...")

        connection = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10  # 10 second timeout
        )

        print("✅ SUCCESS: Database connection established!")

        # Test basic query
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()

        print(f"\n📊 Database Information:")
        print(f"   PostgreSQL Version: {version[0]}")

        # Get current database and user
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        print(f"   Current Database: {db_info[0]}")
        print(f"   Current User: {db_info[1]}")

        # Close connection
        cursor.close()
        connection.close()
        print("\n✅ Connection test completed successfully!")
        print("=" * 60)
        return True

    except OperationalError as e:
        print(f"\n❌ ERROR: Failed to connect to database")
        print(f"\n🔍 Error Details:")
        print(f"   {type(e).__name__}: {e}")

        # Provide troubleshooting suggestions based on error
        error_str = str(e).lower()

        if "connection refused" in error_str:
            print("\n💡 Troubleshooting Suggestions:")
            print("   - Check if the database host and port are correct")
            print("   - Verify network connectivity to the database")
            print("   - Check if firewall rules allow connections")

        elif "authentication failed" in error_str or "password" in error_str:
            print("\n💡 Troubleshooting Suggestions:")
            print("   - Verify the database password is correct")
            print("   - Check if the user account exists and is active")

        elif "timeout" in error_str:
            print("\n💡 Troubleshooting Suggestions:")
            print("   - Check network connectivity")
            print("   - Verify the database host is reachable")
            print("   - Try increasing the connection timeout")

        elif "host" in error_str or "could not translate host name" in error_str:
            print("\n💡 Troubleshooting Suggestions:")
            print("   - Verify the database hostname is correct")
            print("   - Check DNS resolution")
            print("   - Ensure you have internet connectivity")

        print("\n" + "=" * 60)
        return False

    except Exception as e:
        print(f"\n❌ ERROR: Unexpected error occurred")
        print(f"\n🔍 Error Details:")
        print(f"   {type(e).__name__}: {e}")
        print("\n" + "=" * 60)
        return False

if __name__ == "__main__":
    success = test_prd_supabase_connection()
    sys.exit(0 if success else 1)