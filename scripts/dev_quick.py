#!/usr/bin/env python3
"""
Quick development commands for the pipeline.
Shortcuts for common development tasks.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

def quick_extract_single_parish():
    """Extract data for a single parish (fastest test)"""
    print("🏃‍♂️ Quick single parish extraction...")
    cmd = [
        'python', 'run_pipeline_monitored.py',
        '--diocese_id', '1',
        '--max_parishes_per_diocese', '1',
        '--num_parishes_for_schedule', '0',
        '--skip_dioceses',
        '--skip_parish_directories',
        '--skip_schedules',
        '--skip_reporting',
        '--monitoring_url', 'http://localhost:8000'
    ]

    try:
        result = subprocess.run(cmd, timeout=120)  # 2 minute timeout
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("⏰ Quick extraction timed out")
        return False

def quick_diocese_scan():
    """Quick scan of a single diocese"""
    print("🔍 Quick diocese scan...")
    cmd = [
        'python', 'find_parishes.py',
        '--diocese_id', '1',
        '--max_dioceses_to_process', '1'
    ]

    try:
        result = subprocess.run(cmd, timeout=180)  # 3 minute timeout
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("⏰ Diocese scan timed out")
        return False

def quick_schedule_test():
    """Quick schedule extraction test"""
    print("⏰ Quick schedule extraction test...")
    cmd = [
        'python', 'extract_schedule.py',
        '--num_parishes', '1'
    ]

    try:
        result = subprocess.run(cmd, timeout=300)  # 5 minute timeout
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("⏰ Schedule extraction timed out")
        return False

def view_recent_logs():
    """View recent pipeline logs"""
    log_files = [
        'logs/pipeline.log',
        'logs/extraction.log',
        'pipeline.log'
    ]

    for log_file in log_files:
        if Path(log_file).exists():
            print(f"📋 Recent logs from {log_file}:")
            subprocess.run(['tail', '-20', log_file])
            return

    print("📋 No log files found. Checking for recent pipeline output...")
    # Try to run a quick command to see if there are any immediate issues
    subprocess.run(['python', '--version'])

def clear_chrome_cache():
    """Clear Chrome cache and temp files"""
    print("🧹 Clearing Chrome cache and temp files...")
    cache_dirs = [
        '/tmp/chrome-*',
        '/tmp/.chrome*',
        '/tmp/webdriver-cache',
        os.path.expanduser('~/.cache/google-chrome'),
        '.chrome-user-data'
    ]

    for cache_dir in cache_dirs:
        try:
            subprocess.run(['rm', '-rf', cache_dir], check=False)
        except:
            pass

    print("✅ Chrome cache cleared")

def show_db_stats():
    """Show quick database statistics"""
    print("📊 Database Statistics")
    print("=" * 25)

    try:
        from core.db import get_supabase_client
        supabase = get_supabase_client()

        # Get counts
        dioceses = supabase.table('Dioceses').select('count').execute()
        parishes = supabase.table('Parishes').select('count').execute()
        parish_data = supabase.table('ParishData').select('count').execute()

        dioceses_count = len(dioceses.data) if dioceses.data else 0
        parishes_count = len(parishes.data) if parishes.data else 0
        data_count = len(parish_data.data) if parish_data.data else 0

        print(f"Dioceses: {dioceses_count}")
        print(f"Parishes: {parishes_count}")
        print(f"Data entries: {data_count}")

        if dioceses_count > 0:
            print(f"Avg parishes/diocese: {parishes_count/dioceses_count:.1f}")

        if parishes_count > 0:
            data_coverage = (data_count / parishes_count) * 100
            print(f"Data coverage: {data_coverage:.1f}%")

        # Show recent activity
        recent_parishes = supabase.table('Parishes').select('Name, created_at').order('created_at', desc=True).limit(3).execute()
        if recent_parishes.data:
            print("\nRecent parishes:")
            for parish in recent_parishes.data:
                print(f"  • {parish['Name']}")

    except Exception as e:
        print(f"❌ Database error: {e}")

def kill_chrome_processes():
    """Kill any stuck Chrome processes"""
    print("🔪 Killing Chrome processes...")
    try:
        subprocess.run(['pkill', '-f', 'chrome'], check=False)
        subprocess.run(['pkill', '-f', 'chromedriver'], check=False)
        print("✅ Chrome processes terminated")
    except:
        print("⚠️ Could not kill Chrome processes (maybe none running)")

def check_ports():
    """Check if development ports are in use"""
    print("🔌 Checking development ports...")
    ports = [3000, 8000, 8080]

    for port in ports:
        try:
            result = subprocess.run(['lsof', '-ti', f':{port}'],
                                  capture_output=True, text=True)
            if result.stdout.strip():
                pid = result.stdout.strip()
                print(f"Port {port}: In use (PID {pid})")
            else:
                print(f"Port {port}: Available")
        except:
            print(f"Port {port}: Could not check")

def restart_services():
    """Restart development services"""
    print("🔄 Restarting development services...")

    # Kill existing processes on our ports
    ports = [3000, 8000]
    for port in ports:
        try:
            result = subprocess.run(['lsof', '-ti', f':{port}'],
                                  capture_output=True, text=True)
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    subprocess.run(['kill', pid], check=False)
                    print(f"Killed process {pid} on port {port}")
        except:
            pass

    # Start backend
    print("Starting backend...")
    subprocess.Popen(['python', 'backend/main.py'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)

    # Start frontend (if exists)
    if Path('frontend').exists():
        print("Starting frontend...")
        subprocess.Popen(['npm', 'start'],
                        cwd='frontend',
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)

    print("✅ Services restarted")
    print("📊 Backend: http://localhost:8000")
    print("🌐 Frontend: http://localhost:3000")

def main():
    parser = argparse.ArgumentParser(description="Quick Development Commands")
    parser.add_argument('command', choices=[
        'extract', 'diocese', 'schedule', 'logs', 'clear-cache',
        'stats', 'kill-chrome', 'ports', 'restart'
    ], help='Quick command to run')

    if len(sys.argv) == 1:
        print("🚀 Quick Development Commands")
        print("=" * 40)
        print("Available commands:")
        print("  extract     - Extract single parish (fastest test)")
        print("  diocese     - Quick diocese scan")
        print("  schedule    - Quick schedule extraction test")
        print("  logs        - View recent logs")
        print("  clear-cache - Clear Chrome cache")
        print("  stats       - Show database statistics")
        print("  kill-chrome - Kill stuck Chrome processes")
        print("  ports       - Check port usage")
        print("  restart     - Restart development services")
        print("\nUsage: python scripts/dev_quick.py <command>")
        return

    args = parser.parse_args()

    commands = {
        'extract': quick_extract_single_parish,
        'diocese': quick_diocese_scan,
        'schedule': quick_schedule_test,
        'logs': view_recent_logs,
        'clear-cache': clear_chrome_cache,
        'stats': show_db_stats,
        'kill-chrome': kill_chrome_processes,
        'ports': check_ports,
        'restart': restart_services
    }

    if args.command in commands:
        commands[args.command]()
    else:
        print(f"Unknown command: {args.command}")

if __name__ == '__main__':
    main()