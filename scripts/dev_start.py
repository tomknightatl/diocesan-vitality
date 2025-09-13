#!/usr/bin/env python3
"""
Development startup script for USCCB pipeline.
Helps developers quickly start the local environment.
"""

import argparse
import subprocess
import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

def check_environment():
    """Check if environment is properly configured"""
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found. Please copy .env.example to .env and configure it.")
        return False

    load_dotenv()
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_KEY',
        'GENAI_API_KEY_USCCB'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        return False

    print("✅ Environment configuration looks good")
    return True

def check_dependencies():
    """Check if Python dependencies are installed"""
    try:
        import supabase
        import selenium
        import google.generativeai
        print("✅ Core dependencies are available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def start_backend(background=True):
    """Start the FastAPI backend server"""
    backend_path = Path('backend/main.py')
    if not backend_path.exists():
        print("❌ Backend not found at backend/main.py")
        return None

    print("🚀 Starting backend server...")
    if background:
        # Start in background
        proc = subprocess.Popen(
            ['python', 'backend/main.py'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("✅ Backend started in background (PID: {})".format(proc.pid))
        return proc
    else:
        # Start in foreground
        subprocess.run(['python', 'backend/main.py'])
        return None

def start_frontend(background=True):
    """Start the React frontend server"""
    frontend_path = Path('frontend')
    if not frontend_path.exists():
        print("❌ Frontend not found at frontend/")
        return None

    print("🚀 Starting frontend server...")
    if background:
        proc = subprocess.Popen(
            ['npm', 'start'],
            cwd='frontend',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("✅ Frontend started in background (PID: {})".format(proc.pid))
        return proc
    else:
        subprocess.run(['npm', 'start'], cwd='frontend')
        return None

def run_pipeline_test():
    """Run a quick pipeline test"""
    print("🧪 Running pipeline test...")
    cmd = [
        'python', 'run_pipeline_monitored.py',
        '--diocese_id', '1',
        '--max_parishes_per_diocese', '1',
        '--skip_schedules',
        '--skip_reporting',
        '--monitoring_url', 'http://localhost:8000'
    ]

    try:
        result = subprocess.run(cmd, timeout=300)  # 5 minute timeout
        if result.returncode == 0:
            print("✅ Pipeline test completed successfully")
        else:
            print("❌ Pipeline test failed")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("⏰ Pipeline test timed out (5 minutes)")
        return False

def main():
    parser = argparse.ArgumentParser(description="USCCB Development Environment Starter")
    parser.add_argument('--check-only', action='store_true', help='Only check environment, don\'t start services')
    parser.add_argument('--backend-only', action='store_true', help='Start only the backend')
    parser.add_argument('--frontend-only', action='store_true', help='Start only the frontend')
    parser.add_argument('--test-pipeline', action='store_true', help='Run a quick pipeline test')
    parser.add_argument('--foreground', action='store_true', help='Start services in foreground')

    args = parser.parse_args()

    print("🏁 USCCB Development Environment Setup")
    print("=" * 50)

    # Always check environment first
    if not check_environment():
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)

    if args.check_only:
        print("✅ Environment check complete!")
        return

    background = not args.foreground
    processes = []

    try:
        if args.backend_only or not (args.frontend_only or args.test_pipeline):
            proc = start_backend(background)
            if proc:
                processes.append(proc)
                time.sleep(3)  # Give backend time to start

        if args.frontend_only or not (args.backend_only or args.test_pipeline):
            proc = start_frontend(background)
            if proc:
                processes.append(proc)

        if args.test_pipeline:
            if not start_backend(True):  # Ensure backend is running
                print("❌ Could not start backend for testing")
                sys.exit(1)
            time.sleep(5)  # Give backend more time to start
            run_pipeline_test()

        if background and processes:
            print("\n🎉 Services started successfully!")
            print("📊 Backend API: http://localhost:8000")
            print("🌐 Frontend: http://localhost:3000")
            print("📈 Dashboard: http://localhost:3000/dashboard")
            print("\nTo stop services, run:")
            for proc in processes:
                print(f"  kill {proc.pid}")

            # Wait for user interrupt
            print("\n Press Ctrl+C to stop all services...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping services...")
                for proc in processes:
                    proc.terminate()
                    proc.wait()
                print("✅ All services stopped")

    except Exception as e:
        print(f"❌ Error: {e}")
        # Clean up processes
        for proc in processes:
            proc.terminate()
        sys.exit(1)

if __name__ == '__main__':
    main()