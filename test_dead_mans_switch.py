#!/usr/bin/env python3
"""
Test script for the dead man's switch functionality.
This script simulates an extraction that starts but never finishes to test the staleness detection.
"""

import requests
import time
import json

def test_dead_mans_switch():
    backend_url = "http://localhost:8000"

    print("🧪 Testing Dead Man's Switch functionality...")

    # Step 1: Set extraction status to "running"
    print("\n1. Setting extraction status to 'running'...")

    running_status = {
        "status": "running",
        "current_diocese": "Test Diocese",
        "parishes_processed": 5,
        "total_parishes": 20,
        "success_rate": 75.0,
        "progress_percentage": 25.0,
        "estimated_completion": None
    }

    response = requests.post(f"{backend_url}/api/monitoring/extraction_status", json=running_status)
    if response.status_code == 200:
        print("✅ Extraction status set to RUNNING")
    else:
        print(f"❌ Failed to set extraction status: {response.status_code}")
        return False

    # Step 2: Set some circuit breaker data
    print("\n2. Setting circuit breaker data...")

    circuit_data = {
        "test_breaker": {
            "state": "CLOSED",
            "total_requests": 100,
            "total_successes": 95,
            "total_failures": 5,
            "total_blocked": 0,
            "success_rate": 95.0
        }
    }

    response = requests.post(f"{backend_url}/api/monitoring/circuit_breakers", json=circuit_data)
    if response.status_code == 200:
        print("✅ Circuit breaker data set")
    else:
        print(f"❌ Failed to set circuit breaker data: {response.status_code}")

    # Step 3: Check initial status
    print("\n3. Checking initial status...")
    response = requests.get(f"{backend_url}/api/monitoring/status")
    if response.status_code == 200:
        status = response.json()
        print(f"   Extraction Status: {status['extraction_status']['status']}")
        print(f"   Circuit Breakers: {len(status['circuit_breakers'])} active")

    # Step 4: Wait for dead man's switch to trigger (5+ minutes for extraction, 10+ minutes for circuit breakers)
    print(f"\n4. Waiting for dead man's switch to trigger...")
    print("   ⏳ This test will take about 6 minutes to complete...")
    print("   📊 You can monitor the dashboard at http://localhost:5173/dashboard")
    print("   🔄 The system checks for stale data every 10 seconds")

    # We'll check every 30 seconds for changes
    for i in range(15):  # 15 * 30 seconds = 7.5 minutes total
        time.sleep(30)

        response = requests.get(f"{backend_url}/api/monitoring/status")
        if response.status_code == 200:
            status = response.json()
            extraction_status = status['extraction_status']['status']
            circuit_breaker_count = len(status['circuit_breakers'])

            print(f"   Check {i+1}/15: Extraction={extraction_status}, CircuitBreakers={circuit_breaker_count}")

            # Check if extraction status became stale (should happen around 5 minutes)
            if extraction_status == 'stale' and i >= 8:  # After 4+ minutes
                print("✅ Dead man's switch triggered for extraction status!")

                if 'stale_reason' in status['extraction_status']:
                    print(f"   Reason: {status['extraction_status']['stale_reason']}")

                break
        else:
            print(f"   ❌ Failed to check status: {response.status_code}")

    print(f"\n🎉 Dead man's switch test completed!")
    print(f"   Visit http://localhost:5173/dashboard to see the 'STALE' status")

    return True

if __name__ == "__main__":
    try:
        test_dead_mans_switch()
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")