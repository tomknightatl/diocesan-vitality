#!/usr/bin/env python3
"""
Test script to verify monitoring API integration
"""
import requests
import time
import json
from datetime import datetime, timezone

class MonitoringClient:
    """Client for sending updates to the monitoring API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 5  # Quick timeout for monitoring calls

    def send_log(self, message: str, level: str = "INFO", parish_id: int = None):
        """Send a log entry to the monitoring API."""
        try:
            data = {
                "message": message,
                "level": level,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "parish_id": parish_id
            }
            response = self.session.post(f"{self.base_url}/api/monitoring/log", json=data)
            print(f"✅ Sent log: {message} (Status: {response.status_code})")
            return True
        except Exception as e:
            print(f"❌ Failed to send log: {e}")
            return False

    def update_extraction_status(self, status: str, current_diocese: str = None,
                                parishes_processed: int = 0, total_parishes: int = 0,
                                success_rate: float = 0.0, progress_percentage: float = 0.0):
        """Update extraction status in the monitoring API."""
        try:
            data = {
                "status": status,
                "current_diocese": current_diocese,
                "parishes_processed": parishes_processed,
                "total_parishes": total_parishes,
                "success_rate": success_rate,
                "progress_percentage": progress_percentage,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "started_at": datetime.now(timezone.utc).isoformat()
            }
            response = self.session.post(f"{self.base_url}/api/monitoring/extraction_status", json=data)
            print(f"✅ Updated extraction status: {status} (Status: {response.status_code})")
            return True
        except Exception as e:
            print(f"❌ Failed to update extraction status: {e}")
            return False

def main():
    """Test the monitoring integration."""
    print("🔧 Testing monitoring API integration...")

    monitor = MonitoringClient()

    # Test 1: Send initial log
    monitor.send_log("🚀 Test: Starting monitoring integration test")

    # Test 2: Update extraction status to running
    monitor.update_extraction_status(
        status="running",
        current_diocese="Archdiocese of Atlanta (Test)",
        parishes_processed=0,
        total_parishes=105,
        success_rate=0.0,
        progress_percentage=0.0
    )

    # Test 3: Simulate some progress
    for i in range(1, 6):
        time.sleep(1)

        # Send progress log
        monitor.send_log(f"🔄 Processing parish {i}/5: test-parish-{i}.org", parish_id=3000 + i)

        # Update status
        monitor.update_extraction_status(
            status="running",
            current_diocese="Archdiocese of Atlanta (Test)",
            parishes_processed=i,
            total_parishes=5,
            success_rate=(i/5) * 100,
            progress_percentage=(i/5) * 100
        )

        if i == 3:
            monitor.send_log("✅ Successfully extracted schedule data", "INFO", parish_id=3003)

    # Test 4: Complete the test
    monitor.send_log("✅ Test completed successfully")
    monitor.update_extraction_status(
        status="completed",
        current_diocese="Archdiocese of Atlanta (Test)",
        parishes_processed=5,
        total_parishes=5,
        success_rate=100.0,
        progress_percentage=100.0
    )

    print("🎉 Monitoring test completed! Check the dashboard at http://127.0.0.1:5173/dashboard")

if __name__ == "__main__":
    main()