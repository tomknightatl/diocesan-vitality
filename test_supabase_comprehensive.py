#!/usr/bin/env python3
"""
Comprehensive test script for both DEV and PRD Supabase environments.
Tests REST API connectivity, database access, and basic query execution.
"""

import os
import sys
import time
from datetime import datetime

# Remove current directory from sys.path to avoid conflicts with local 'supabase' directory
if '' in sys.path:
    sys.path.remove('')
if os.getcwd() in sys.path:
    sys.path.remove(os.getcwd())

# Add local package path to sys.path
sys.path.insert(0, '/home/tomk/.local/lib/python3.12/site-packages')

from dotenv import load_dotenv

try:
    from supabase import create_client, Client
except ImportError as e:
    print("❌ ERROR: supabase Python library not installed")
    print(f"   Import error: {e}")
    print("   Install it with: pip install supabase")
    sys.exit(1)

try:
    import psycopg2
    from psycopg2 import OperationalError
except ImportError as e:
    print("❌ ERROR: psycopg2 library not installed")
    print(f"   Import error: {e}")
    print("   Install it with: pip install psycopg2-binary")
    sys.exit(1)


class SupabaseTestResult:
    """Class to store test results for each environment"""

    def __init__(self, env_name):
        self.env_name = env_name
        self.rest_api_success = False
        self.rest_api_time = 0
        self.rest_api_error = None
        self.rest_api_sample_data = None

        self.db_connection_success = False
        self.db_connection_time = 0
        self.db_connection_error = None
        self.db_version = None

        self.query_success = False
        self.query_time = 0
        self.query_error = None
        self.query_sample_data = None

    def print_summary(self):
        """Print a formatted summary of test results"""
        print(f"\n{'=' * 70}")
        print(f"📊 {self.env_name.upper()} ENVIRONMENT TEST SUMMARY")
        print(f"{'=' * 70}")

        # REST API Results
        print(f"\n🌐 REST API Connection:")
        if self.rest_api_success:
            print(f"   ✅ SUCCESS ({self.rest_api_time:.3f}s)")
            if self.rest_api_sample_data:
                print(f"   📄 Sample Data Retrieved:")
                for key, value in list(self.rest_api_sample_data.items())[:3]:
                    print(f"      {key}: {value}")
        else:
            print(f"   ❌ FAILED")
            if self.rest_api_error:
                print(f"   🔍 Error: {self.rest_api_error}")

        # Database Connection Results
        print(f"\n🔌 Direct Database Connection:")
        if self.db_connection_success:
            print(f"   ✅ SUCCESS ({self.db_connection_time:.3f}s)")
            if self.db_version:
                print(f"   📋 PostgreSQL Version: {self.db_version[:50]}...")
        else:
            print(f"   ❌ FAILED")
            if self.db_connection_error:
                print(f"   🔍 Error: {self.db_connection_error}")

        # Query Results
        print(f"\n🔍 Basic Query Execution:")
        if self.query_success:
            print(f"   ✅ SUCCESS ({self.query_time:.3f}s)")
            if self.query_sample_data:
                print(f"   📄 Query Results:")
                for key, value in list(self.query_sample_data.items())[:3]:
                    print(f"      {key}: {value}")
        else:
            print(f"   ❌ FAILED")
            if self.query_error:
                print(f"   🔍 Error: {self.query_error}")

        print(f"\n{'=' * 70}")


def test_rest_api_connection(url, key, env_name):
    """Test Supabase REST API connection"""
    print(f"\n🔄 Testing {env_name} REST API connection...")

    try:
        start_time = time.time()
        supabase: Client = create_client(url, key)

        # Test basic query
        response = supabase.table('Dioceses').select('*').limit(1).execute()
        elapsed_time = time.time() - start_time

        if response.status_code == 200 and response.data:
            print(f"   ✅ REST API connection successful ({elapsed_time:.3f}s)")
            print(f"   📊 Status: {response.status_code}")
            print(f"   📊 Records: {len(response.data)}")
            return True, elapsed_time, None, response.data[0]
        else:
            error_msg = f"Unexpected response: {response.status_code}"
            print(f"   ❌ {error_msg}")
            return False, elapsed_time, error_msg, None

    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"   ❌ REST API connection failed: {error_msg}")
        return False, elapsed_time, error_msg, None


def test_database_connection(host, port, password, env_name):
    """Test direct PostgreSQL database connection"""
    print(f"\n🔄 Testing {env_name} direct database connection...")

    try:
        start_time = time.time()

        connection = psycopg2.connect(
            host=host,
            port=port,
            database='postgres',
            user='postgres',
            password=password,
            connect_timeout=10
        )

        elapsed_time = time.time() - start_time

        # Get database version
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]

        cursor.close()
        connection.close()

        print(f"   ✅ Database connection successful ({elapsed_time:.3f}s)")
        print(f"   📋 PostgreSQL: {version[:60]}...")

        return True, elapsed_time, None, version

    except OperationalError as e:
        elapsed_time = time.time() - start_time
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"   ❌ Database connection failed: {error_msg}")
        return False, elapsed_time, error_msg, None

    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"   ❌ Unexpected error: {error_msg}")
        return False, elapsed_time, error_msg, None


def test_query_execution(url, key, env_name):
    """Test basic query execution via REST API"""
    print(f"\n🔄 Testing {env_name} query execution...")

    try:
        start_time = time.time()
        supabase: Client = create_client(url, key)

        # Execute a more complex query
        response = supabase.table('Dioceses').select('id', 'Name', 'Website').limit(3).execute()
        elapsed_time = time.time() - start_time

        if response.status_code == 200 and response.data:
            print(f"   ✅ Query execution successful ({elapsed_time:.3f}s)")
            print(f"   📊 Records retrieved: {len(response.data)}")
            return True, elapsed_time, None, response.data[0]
        else:
            error_msg = f"Query returned no data or error: {response.status_code}"
            print(f"   ❌ {error_msg}")
            return False, elapsed_time, error_msg, None

    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"   ❌ Query execution failed: {error_msg}")
        return False, elapsed_time, error_msg, None


def test_environment(env_suffix, env_name):
    """Test all aspects of a Supabase environment"""
    print(f"\n{'=' * 70}")
    print(f"🧪 TESTING {env_name.upper()} ENVIRONMENT")
    print(f"{'=' * 70}")

    result = SupabaseTestResult(env_name)

    # Get credentials
    url = os.getenv(f'SUPABASE_URL_{env_suffix}')
    key = os.getenv(f'SUPABASE_KEY_{env_suffix}')
    db_host = os.getenv(f'SUPABASE_DB_HOST_{env_suffix}')
    db_port = os.getenv(f'SUPABASE_DB_PORT_{env_suffix}')
    db_password = os.getenv(f'SUPABASE_DB_PASSWORD_{env_suffix}')

    # Validate credentials
    missing = []
    if not url:
        missing.append(f'SUPABASE_URL_{env_suffix}')
    if not key:
        missing.append(f'SUPABASE_KEY_{env_suffix}')
    if not db_host:
        missing.append(f'SUPABASE_DB_HOST_{env_suffix}')
    if not db_port:
        missing.append(f'SUPABASE_DB_PORT_{env_suffix}')
    if not db_password:
        missing.append(f'SUPABASE_DB_PASSWORD_{env_suffix}')

    if missing:
        print(f"\n❌ ERROR: Missing credentials: {', '.join(missing)}")
        return result

    # Mask sensitive data for display
    masked_key = key[:20] + '...' + key[-20:] if len(key) > 40 else '***'
    masked_password = db_password[:4] + '...' + db_password[-4:] if len(db_password) > 8 else '***'

    print(f"\n📋 Configuration:")
    print(f"   URL: {url}")
    print(f"   API Key: {masked_key}")
    print(f"   DB Host: {db_host}")
    print(f"   DB Port: {db_port}")
    print(f"   DB Password: {masked_password}")

    # Test 1: REST API Connection
    success, time_taken, error, sample_data = test_rest_api_connection(url, key, env_name)
    result.rest_api_success = success
    result.rest_api_time = time_taken
    result.rest_api_error = error
    result.rest_api_sample_data = sample_data

    # Test 2: Direct Database Connection
    success, time_taken, error, version = test_database_connection(
        db_host, db_port, db_password, env_name
    )
    result.db_connection_success = success
    result.db_connection_time = time_taken
    result.db_connection_error = error
    result.db_version = version

    # Test 3: Query Execution (via REST API)
    success, time_taken, error, sample_data = test_query_execution(url, key, env_name)
    result.query_success = success
    result.query_time = time_taken
    result.query_error = error
    result.query_sample_data = sample_data

    return result


def generate_report(dev_result, prd_result):
    """Generate a comprehensive test report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""
# Supabase Database Connection Test Report
**Generated:** {timestamp}

## Executive Summary

### DEV Environment (Local)
- **REST API:** {'✅ SUCCESS' if dev_result.rest_api_success else '❌ FAILED'}
- **Direct DB Connection:** {'✅ SUCCESS' if dev_result.db_connection_success else '❌ FAILED'}
- **Query Execution:** {'✅ SUCCESS' if dev_result.query_success else '❌ FAILED'}

### PRD Environment (Production)
- **REST API:** {'✅ SUCCESS' if prd_result.rest_api_success else '❌ FAILED'}
- **Direct DB Connection:** {'✅ SUCCESS' if prd_result.db_connection_success else '❌ FAILED'}
- **Query Execution:** {'✅ SUCCESS' if prd_result.query_success else '❌ FAILED'}

---

## Detailed Results

### DEV Environment (Local Supabase)

#### REST API Connection
- **Status:** {'✅ SUCCESS' if dev_result.rest_api_success else '❌ FAILED'}
- **Response Time:** {dev_result.rest_api_time:.3f}s
"""

    if dev_result.rest_api_error:
        report += f"- **Error:** {dev_result.rest_api_error}\n"

    if dev_result.rest_api_sample_data:
        report += f"- **Sample Data:**\n"
        for key, value in list(dev_result.rest_api_sample_data.items())[:3]:
            report += f"  - {key}: {value}\n"

    report += f"""
#### Direct Database Connection
- **Status:** {'✅ SUCCESS' if dev_result.db_connection_success else '❌ FAILED'}
- **Connection Time:** {dev_result.db_connection_time:.3f}s
"""

    if dev_result.db_connection_error:
        report += f"- **Error:** {dev_result.db_connection_error}\n"

    if dev_result.db_version:
        report += f"- **PostgreSQL Version:** {dev_result.db_version}\n"

    report += f"""
#### Query Execution
- **Status:** {'✅ SUCCESS' if dev_result.query_success else '❌ FAILED'}
- **Query Time:** {dev_result.query_time:.3f}s
"""

    if dev_result.query_error:
        report += f"- **Error:** {dev_result.query_error}\n"

    if dev_result.query_sample_data:
        report += f"- **Sample Data:**\n"
        for key, value in list(dev_result.query_sample_data.items())[:3]:
            report += f"  - {key}: {value}\n"

    report += f"""
---

### PRD Environment (Production Supabase)

#### REST API Connection
- **Status:** {'✅ SUCCESS' if prd_result.rest_api_success else '❌ FAILED'}
- **Response Time:** {prd_result.rest_api_time:.3f}s
"""

    if prd_result.rest_api_error:
        report += f"- **Error:** {prd_result.rest_api_error}\n"

    if prd_result.rest_api_sample_data:
        report += f"- **Sample Data:**\n"
        for key, value in list(prd_result.rest_api_sample_data.items())[:3]:
            report += f"  - {key}: {value}\n"

    report += f"""
#### Direct Database Connection
- **Status:** {'✅ SUCCESS' if prd_result.db_connection_success else '❌ FAILED'}
- **Connection Time:** {prd_result.db_connection_time:.3f}s
"""

    if prd_result.db_connection_error:
        report += f"- **Error:** {prd_result.db_connection_error}\n"

    if prd_result.db_version:
        report += f"- **PostgreSQL Version:** {prd_result.db_version}\n"

    report += f"""
#### Query Execution
- **Status:** {'✅ SUCCESS' if prd_result.query_success else '❌ FAILED'}
- **Query Time:** {prd_result.query_time:.3f}s
"""

    if prd_result.query_error:
        report += f"- **Error:** {prd_result.query_error}\n"

    if prd_result.query_sample_data:
        report += f"- **Sample Data:**\n"
        for key, value in list(prd_result.query_sample_data.items())[:3]:
            report += f"  - {key}: {value}\n"

    report += f"""
---

## Recommendations

### For Development (DEV)
"""

    if dev_result.rest_api_success:
        report += "- ✅ REST API is working - use this for development\n"
    else:
        report += "- ❌ REST API is not working - check local Supabase instance\n"

    if dev_result.db_connection_success:
        report += "- ✅ Direct database connection is working\n"
    else:
        report += "- ⚠️ Direct database connection is not available - use REST API instead\n"

    report += f"""
### For Production (PRD)
"""

    if prd_result.rest_api_success:
        report += "- ✅ REST API is working - recommended for production use\n"
    else:
        report += "- ❌ REST API is not working - check credentials and permissions\n"

    if prd_result.db_connection_success:
        report += "- ✅ Direct database connection is working\n"
    else:
        report += "- ⚠️ Direct database connection is not available - use REST API instead\n"

    report += f"""
### General Recommendations
1. **Use REST API for most operations** - it's reliable and secure
2. **Monitor connection times** - optimize queries if response times are slow
3. **Implement proper error handling** - handle connection failures gracefully
4. **Use connection pooling** - for high-traffic applications
5. **Secure your credentials** - never commit .env files to version control

---

## Test Methodology

### Tests Performed
1. **REST API Connection Test**
   - Validates Supabase URL and API key
   - Tests basic authentication
   - Executes a simple query to verify data access

2. **Direct Database Connection Test**
   - Tests PostgreSQL connection with credentials
   - Verifies database accessibility
   - Retrieves PostgreSQL version information

3. **Query Execution Test**
   - Executes a SELECT query via REST API
   - Measures query performance
   - Validates data retrieval capabilities

### Security Notes
- All tests use read-only operations
- No data modifications were performed
- Credentials are masked in reports
- .env file is not committed to version control

---

*Report generated by comprehensive Supabase test script*
"""

    return report


def main():
    """Main test execution function"""
    print("\n" + "=" * 70)
    print("🚀 SUPABASE DATABASE CONNECTION TEST SUITE")
    print("=" * 70)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load environment variables
    load_dotenv()

    # Test DEV environment
    dev_result = test_environment('DEV', 'DEV')

    # Test PRD environment
    prd_result = test_environment('PRD', 'PRD')

    # Print summaries
    dev_result.print_summary()
    prd_result.print_summary()

    # Generate and save report
    report = generate_report(dev_result, prd_result)

    report_filename = f"supabase_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_filename, 'w') as f:
        f.write(report)

    print(f"\n📄 Detailed report saved to: {report_filename}")

    # Final summary
    print(f"\n{'=' * 70}")
    print("📊 FINAL SUMMARY")
    print(f"{'=' * 70}")

    dev_overall = dev_result.rest_api_success and dev_result.query_success
    prd_overall = prd_result.rest_api_success and prd_result.query_success

    print(f"\nDEV Environment: {'✅ OPERATIONAL' if dev_overall else '❌ ISSUES DETECTED'}")
    print(f"PRD Environment: {'✅ OPERATIONAL' if prd_overall else '❌ ISSUES DETECTED'}")

    if dev_overall and prd_overall:
        print(f"\n🎉 All critical tests passed! Both environments are operational.")
        return 0
    else:
        print(f"\n⚠️ Some tests failed. Please review the detailed report.")
        return 1


if __name__ == "__main__":
    sys.exit(main())