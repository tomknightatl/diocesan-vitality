#!/usr/bin/env python3
"""
Development startup script for the pipeline.
Helps developers quickly start the local environment.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


def check_environment():
    """Check if environment is properly configured"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found. Please copy .env.example to .env and configure it.")
        return False

    load_dotenv()
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "GENAI_API_KEY"]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        return False

    print("✅ Environment configuration looks good")
    return True


def check_dependencies():
    """Check if Python dependencies are installed"""
    try:
        pass

        print("✅ Core dependencies are available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Run: pip install -r requirements.txt")
        return False


def start_backend(background=True):
    """Start the FastAPI backend server"""
    backend_path = Path("backend/main.py")
    if not backend_path.exists():
        print("❌ Backend not found at backend/main.py")
        return None

    print("🚀 Starting backend server...")
    if background:
        # Start in background
        proc = subprocess.Popen(
            ["python", "backend/main.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("✅ Backend started in background (PID: {})".format(proc.pid))
        return proc
    else:
        # Start in foreground
        subprocess.run(["python", "backend/main.py"])
        return None


def start_frontend(background=True):
    """Start the React frontend server"""
    frontend_path = Path("frontend")
    if not frontend_path.exists():
        print("❌ Frontend not found at frontend/")
        return None

    print("🚀 Starting frontend server...")
    if background:
        proc = subprocess.Popen(
            ["npm", "start"],
            cwd="frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("✅ Frontend started in background (PID: {})".format(proc.pid))
        return proc
    else:
        subprocess.run(["npm", "start"], cwd="frontend")
        return None


def run_pipeline_test():
    """Run a quick pipeline test"""
    print("🧪 Running pipeline test...")
    cmd = [
        "python",
        "run_pipeline_monitored.py",
        "--diocese_id",
        "1",
        "--max_parishes_per_diocese",
        "1",
        "--skip_schedules",
        "--skip_reporting",
        "--monitoring_url",
        "http://localhost:8000",
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


def _create_argument_parser():
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(description="Development Environment Starter")
    parser.add_argument(
        "--check - only",
        action="store_true",
        help="Only check environment, don't start services",
    )
    parser.add_argument("--backend - only", action="store_true", help="Start only the backend")
    parser.add_argument("--frontend - only", action="store_true", help="Start only the frontend")
    parser.add_argument("--test - pipeline", action="store_true", help="Run a quick pipeline test")
    parser.add_argument("--foreground", action="store_true", help="Start services in foreground")
    return parser


def _validate_environment():
    """Validate environment and dependencies"""
    print("🏁 Development Environment Setup")
    print("=" * 50)

    # Always check environment first
    if not check_environment():
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)


def _should_start_backend(args):
    """Determine if backend should be started based on arguments"""
    return args.backend_only or not (args.frontend_only or args.test_pipeline)


def _should_start_frontend(args):
    """Determine if frontend should be started based on arguments"""
    return args.frontend_only or not (args.backend_only or args.test_pipeline)


def _start_backend_service(background, processes):
    """Start backend service and add to process list"""
    proc = start_backend(background)
    if proc:
        processes.append(proc)
        time.sleep(3)  # Give backend time to start


def _start_frontend_service(background, processes):
    """Start frontend service and add to process list"""
    proc = start_frontend(background)
    if proc:
        processes.append(proc)


def _run_pipeline_test_service():
    """Run pipeline test with backend dependency"""
    if not start_backend(True):  # Ensure backend is running
        print("❌ Could not start backend for testing")
        sys.exit(1)
    time.sleep(5)  # Give backend more time to start
    run_pipeline_test()


def _display_service_info(processes):
    """Display information about started services"""
    print("\n🎉 Services started successfully!")
    print("📊 Backend API: http://localhost:8000")
    print("🌐 Frontend: http://localhost:3000")
    print("📈 Dashboard: http://localhost:3000/dashboard")
    print("\nTo stop services, run:")
    for proc in processes:
        print(f"  kill {proc.pid}")


def _wait_for_interrupt(processes):
    """Wait for user interrupt and handle graceful shutdown"""
    print("\n Press Ctrl + C to stop all services...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        for proc in processes:
            proc.terminate()
            proc.wait()
        print("✅ All services stopped")


def _cleanup_processes(processes):
    """Clean up processes on error"""
    for proc in processes:
        proc.terminate()


def main():
    parser = _create_argument_parser()
    args = parser.parse_args()

    _validate_environment()

    if args.check_only:
        print("✅ Environment check complete!")
        return

    background = not args.foreground
    processes = []

    try:
        # Start backend if needed
        if _should_start_backend(args):
            _start_backend_service(background, processes)

        # Start frontend if needed
        if _should_start_frontend(args):
            _start_frontend_service(background, processes)

        # Run pipeline test if requested
        if args.test_pipeline:
            _run_pipeline_test_service()

        # Handle background services
        if background and processes:
            _display_service_info(processes)
            _wait_for_interrupt(processes)

    except Exception as e:
        print(f"❌ Error: {e}")
        _cleanup_processes(processes)
        sys.exit(1)


if __name__ == "__main__":
    main()
