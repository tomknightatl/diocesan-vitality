#!/usr/bin/env python3
"""
Development testing script for USCCB pipeline.
Quick tests and diagnostics for local development.
"""

import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

def test_database_connection():
    """Test Supabase database connection"""
    print("🔌 Testing database connection...")
    try:
        from core.db import get_supabase_client
        supabase = get_supabase_client()

        # Test basic connectivity
        response = supabase.table('Dioceses').select('count').execute()
        count = len(response.data) if response.data else 0
        print(f"✅ Database connected - {count} dioceses found")

        # Test specific query
        if count > 0:
            sample = supabase.table('Dioceses').select('id, Name, State').limit(1).execute()
            if sample.data:
                diocese = sample.data[0]
                print(f"   Sample: {diocese['Name']}, {diocese['State']} (ID: {diocese['id']})")

        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_ai_connection():
    """Test Google AI API connection"""
    print("🤖 Testing AI API connection...")
    try:
        from core.ai_client import get_genai_client
        client = get_genai_client()

        response = client.generate_content("Hello, respond with just 'AI Connected'")
        response_text = response.text.strip()

        if "AI Connected" in response_text or "connected" in response_text.lower():
            print("✅ AI API connected and responding")
            return True
        else:
            print(f"⚠️ AI API connected but unexpected response: {response_text[:50]}...")
            return True
    except Exception as e:
        print(f"❌ AI API connection failed: {e}")
        return False

def test_webdriver():
    """Test Chrome WebDriver setup"""
    print("🌐 Testing Chrome WebDriver...")
    try:
        from core.driver import get_driver

        # Test driver creation
        driver = get_driver()

        # Test basic navigation
        driver.get("https://www.google.com")
        title = driver.title

        if "Google" in title:
            print("✅ Chrome WebDriver working")
            driver.quit()
            return True
        else:
            print(f"⚠️ WebDriver working but unexpected page: {title}")
            driver.quit()
            return True

    except Exception as e:
        print(f"❌ Chrome WebDriver failed: {e}")
        return False

def test_individual_script(script_name):
    """Test individual extraction script"""
    print(f"🧪 Testing {script_name}...")

    scripts_map = {
        'dioceses': 'extract_dioceses.py',
        'parishes': 'find_parishes.py',
        'extract': 'extract_parishes.py',
        'schedules': 'extract_schedule.py'
    }

    if script_name not in scripts_map:
        print(f"❌ Unknown script: {script_name}")
        print(f"Available scripts: {', '.join(scripts_map.keys())}")
        return False

    script_file = scripts_map[script_name]
    if not Path(script_file).exists():
        print(f"❌ Script not found: {script_file}")
        return False

    try:
        import subprocess

        if script_name == 'dioceses':
            cmd = ['python', script_file, '--max_dioceses', '1']
        elif script_name == 'parishes':
            cmd = ['python', script_file, '--diocese_id', '1', '--max_dioceses_to_process', '1']
        elif script_name == 'extract':
            cmd = ['python', script_file, '--diocese_id', '1', '--max_parishes', '1']
        elif script_name == 'schedules':
            cmd = ['python', script_file, '--num_parishes', '1']

        result = subprocess.run(cmd, timeout=120, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ {script_name} script test passed")
            if result.stdout:
                print(f"   Output: {result.stdout[-100:]}...")  # Last 100 chars
            return True
        else:
            print(f"❌ {script_name} script test failed")
            if result.stderr:
                print(f"   Error: {result.stderr[-200:]}...")  # Last 200 chars
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ {script_name} script test timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing {script_name}: {e}")
        return False

def test_monitoring_integration():
    """Test monitoring system integration"""
    print("📊 Testing monitoring integration...")
    try:
        from core.monitoring_client import get_monitoring_client

        # Test monitoring client creation
        client = get_monitoring_client("http://localhost:8000")

        # Test basic functionality
        client.send_log("Test log message", "INFO")
        client.update_extraction_status(status="testing")

        print("✅ Monitoring integration working")
        return True
    except Exception as e:
        print(f"❌ Monitoring integration failed: {e}")
        return False

def quick_data_check():
    """Quick check of current data in database"""
    print("📈 Quick data overview...")
    try:
        from core.db import get_supabase_client
        supabase = get_supabase_client()

        # Count dioceses
        dioceses_resp = supabase.table('Dioceses').select('count').execute()
        dioceses_count = len(dioceses_resp.data) if dioceses_resp.data else 0

        # Count parishes
        parishes_resp = supabase.table('Parishes').select('count').execute()
        parishes_count = len(parishes_resp.data) if parishes_resp.data else 0

        # Count parish data entries
        data_resp = supabase.table('ParishData').select('count').execute()
        data_count = len(data_resp.data) if data_resp.data else 0

        print(f"📊 Current database contents:")
        print(f"   Dioceses: {dioceses_count}")
        print(f"   Parishes: {parishes_count}")
        print(f"   Parish Data Entries: {data_count}")

        if dioceses_count > 0 and parishes_count > 0:
            avg_parishes = parishes_count / dioceses_count
            print(f"   Average parishes per diocese: {avg_parishes:.1f}")

        return True
    except Exception as e:
        print(f"❌ Data overview failed: {e}")
        return False

def run_environment_check():
    """Run comprehensive environment check"""
    print("🔍 Environment Check")
    print("=" * 30)

    # Check .env file
    env_file = Path('.env')
    if env_file.exists():
        print("✅ .env file found")
        load_dotenv()

        required_vars = [
            'SUPABASE_URL',
            'SUPABASE_KEY',
            'GENAI_API_KEY_USCCB',
            'SEARCH_API_KEY_USCCB',
            'SEARCH_CX_USCCB'
        ]

        for var in required_vars:
            if os.getenv(var):
                print(f"✅ {var} configured")
            else:
                print(f"⚠️ {var} not set")
    else:
        print("❌ .env file not found")

    # Check virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment active")
    else:
        print("⚠️ Virtual environment not detected")

    # Check Python version
    if sys.version_info >= (3, 8):
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} (compatible)")
    else:
        print(f"⚠️ Python {sys.version_info.major}.{sys.version_info.minor} (may have issues)")

def main():
    parser = argparse.ArgumentParser(description="USCCB Development Testing Suite")
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--db', action='store_true', help='Test database connection')
    parser.add_argument('--ai', action='store_true', help='Test AI API connection')
    parser.add_argument('--webdriver', action='store_true', help='Test Chrome WebDriver')
    parser.add_argument('--monitoring', action='store_true', help='Test monitoring integration')
    parser.add_argument('--data', action='store_true', help='Show current data overview')
    parser.add_argument('--env', action='store_true', help='Check environment configuration')
    parser.add_argument('--script', type=str, help='Test specific script (dioceses/parishes/extract/schedules)')

    args = parser.parse_args()

    if not any(vars(args).values()):
        # No arguments provided, show help
        parser.print_help()
        return

    print("🧪 USCCB Development Testing Suite")
    print("=" * 40)

    success_count = 0
    total_tests = 0

    tests_to_run = []

    if args.all or args.env:
        tests_to_run.append(('Environment Check', run_environment_check))

    if args.all or args.db:
        tests_to_run.append(('Database Connection', test_database_connection))

    if args.all or args.ai:
        tests_to_run.append(('AI API Connection', test_ai_connection))

    if args.all or args.webdriver:
        tests_to_run.append(('Chrome WebDriver', test_webdriver))

    if args.all or args.monitoring:
        tests_to_run.append(('Monitoring Integration', test_monitoring_integration))

    if args.all or args.data:
        tests_to_run.append(('Data Overview', quick_data_check))

    if args.script:
        tests_to_run.append((f'Script Test ({args.script})', lambda: test_individual_script(args.script)))

    # Run tests
    for test_name, test_func in tests_to_run:
        print(f"\n--- {test_name} ---")
        try:
            success = test_func()
            total_tests += 1
            if success:
                success_count += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            total_tests += 1

    # Summary
    if total_tests > 0:
        print(f"\n📋 Test Summary: {success_count}/{total_tests} passed")
        if success_count == total_tests:
            print("🎉 All tests passed!")
        else:
            print("⚠️ Some tests failed - check configuration and dependencies")

if __name__ == '__main__':
    main()