#!/usr/bin/env python3
"""
Utility script to reset the monitoring dashboard status when extraction processes
get stuck or crash without properly updating their status.

Usage:
    python reset_monitoring_status.py [--backend-url http://localhost:8000]
"""

import requests
import argparse
import sys
from datetime import datetime

def reset_extraction_status(backend_url):
    """Reset extraction status to idle"""
    url = f"{backend_url}/api/monitoring/extraction_status"

    idle_status = {
        "status": "idle",
        "current_diocese": None,
        "parishes_processed": 0,
        "total_parishes": 0,
        "success_rate": 0,
        "started_at": None,
        "progress_percentage": 0,
        "estimated_completion": None
    }

    try:
        response = requests.post(url, json=idle_status)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to reset extraction status: {e}")

def get_current_status(backend_url):
    """Get current monitoring status"""
    url = f"{backend_url}/api/monitoring/status"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get current status: {e}")

def main():
    parser = argparse.ArgumentParser(description="Reset monitoring dashboard status")
    parser.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="Backend URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check current status, don't reset"
    )

    args = parser.parse_args()

    try:
        print(f"Connecting to backend at {args.backend_url}...")

        # Get current status
        current_status = get_current_status(args.backend_url)
        extraction_status = current_status.get("extraction_status", {})

        print(f"\nCurrent extraction status:")
        print(f"  Status: {extraction_status.get('status', 'unknown')}")
        print(f"  Diocese: {extraction_status.get('current_diocese', 'None')}")
        print(f"  Parishes processed: {extraction_status.get('parishes_processed', 0)}")
        print(f"  Started at: {extraction_status.get('started_at', 'None')}")

        if args.check_only:
            return

        if extraction_status.get('status') == 'idle':
            print("\n✅ Status is already idle, no reset needed.")
            return

        # Reset status
        print(f"\n🔄 Resetting extraction status to idle...")
        result = reset_extraction_status(args.backend_url)

        if result.get("status") == "success":
            print("✅ Successfully reset extraction status to idle")
        else:
            print(f"❌ Reset failed: {result}")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()