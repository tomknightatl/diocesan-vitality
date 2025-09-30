#!/usr/bin/env python3
"""
Distributed Pipeline Monitor

A utility script to monitor the status of the distributed pipeline,
showing active workers, work assignments, and cluster health.
"""

import argparse
import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict

from core.db import get_supabase_client
from core.distributed_work_coordinator import DistributedWorkCoordinator
from core.logger import get_logger

logger = get_logger(__name__)


class PipelineMonitor:
    """Monitor for distributed pipeline cluster"""

    def __init__(self):
        self.supabase = get_supabase_client()

    async def get_cluster_overview(self) -> Dict[str, Any]:
        """Get overview of entire cluster"""
        try:
            # Get active workers
            workers_response = (
                self.supabase.table("pipeline_workers")
                .select("worker_id, pod_name, status, last_heartbeat, created_at")
                .order("last_heartbeat", desc=True)
                .execute()
            )

            # Get work assignments
            assignments_response = (
                self.supabase.table("diocese_work_assignments")
                .select("diocese_id, worker_id, status, assigned_at, completed_at")
                .order("assigned_at", desc=True)
                .execute()
            )

            # Get diocese info for assignments
            diocese_response = self.supabase.table("Dioceses").select("id, Name").execute()

            diocese_names = {d["id"]: d["Name"] for d in diocese_response.data} if diocese_response.data else {}

            # Compile overview
            now = datetime.utcnow()
            active_workers = []
            inactive_workers = []

            if workers_response.data:
                for worker in workers_response.data:
                    last_heartbeat = datetime.fromisoformat(worker["last_heartbeat"].replace("Z", "+00:00"))
                    time_since_heartbeat = (now - last_heartbeat).total_seconds()

                    worker_info = {
                        **worker,
                        "time_since_heartbeat": time_since_heartbeat,
                        "is_healthy": time_since_heartbeat < 120,  # 2 minutes
                    }

                    if worker["status"] == "active" and worker_info["is_healthy"]:
                        active_workers.append(worker_info)
                    else:
                        inactive_workers.append(worker_info)

            # Group assignments by status
            assignments_by_status = {}
            if assignments_response.data:
                for assignment in assignments_response.data:
                    status = assignment["status"]
                    if status not in assignments_by_status:
                        assignments_by_status[status] = []

                    assignment_info = {
                        **assignment,
                        "diocese_name": diocese_names.get(assignment["diocese_id"], f"Unknown ({assignment['diocese_id']})"),
                    }
                    assignments_by_status[status].append(assignment_info)

            return {
                "timestamp": now.isoformat(),
                "active_workers": active_workers,
                "inactive_workers": inactive_workers,
                "total_workers": len(workers_response.data) if workers_response.data else 0,
                "assignments_by_status": assignments_by_status,
                "cluster_health": {
                    "healthy_workers": len(active_workers),
                    "total_workers": len(workers_response.data) if workers_response.data else 0,
                    "processing_dioceses": len(assignments_by_status.get("processing", [])),
                    "completed_dioceses": len(assignments_by_status.get("completed", [])),
                    "failed_dioceses": len(assignments_by_status.get("failed", [])),
                },
            }

        except Exception as e:
            logger.error(f"❌ Error getting cluster overview: {e}")
            return {"error": str(e)}

    def print_cluster_status(self, overview: Dict[str, Any]):
        """Print formatted cluster status"""
        if "error" in overview:
            print(f"❌ Error: {overview['error']}")
            return

        print("🏗️  Distributed Pipeline Cluster Status")
        print("=" * 50)
        print(f"📅 Timestamp: {overview['timestamp']}")
        print()

        # Cluster health summary
        health = overview["cluster_health"]
        print("🩺 Cluster Health:")
        print(f"   • Healthy workers: {health['healthy_workers']}/{health['total_workers']}")
        print(f"   • Processing dioceses: {health['processing_dioceses']}")
        print(f"   • Completed dioceses: {health['completed_dioceses']}")
        print(f"   • Failed dioceses: {health['failed_dioceses']}")
        print()

        # Active workers
        print("👥 Active Workers:")
        if overview["active_workers"]:
            for worker in overview["active_workers"]:
                heartbeat_age = int(worker["time_since_heartbeat"])
                health_indicator = "💚" if worker["is_healthy"] else "💛"
                print(f"   {health_indicator} {worker['worker_id']}")
                print(f"      Pod: {worker['pod_name']}")
                print(f"      Last heartbeat: {heartbeat_age}s ago")
                print()
        else:
            print("   No active workers")
        print()

        # Inactive workers
        if overview["inactive_workers"]:
            print("💀 Inactive Workers:")
            for worker in overview["inactive_workers"]:
                heartbeat_age = int(worker["time_since_heartbeat"])
                print(f"   ❌ {worker['worker_id']} ({worker['status']})")
                print(f"      Last heartbeat: {heartbeat_age}s ago")
            print()

        # Work assignments
        assignments = overview["assignments_by_status"]
        if assignments:
            print("📋 Work Assignments:")

            for status, assignment_list in assignments.items():
                if assignment_list:
                    status_icon = {"processing": "🔄", "completed": "✅", "failed": "❌"}.get(status, "❓")

                    print(f"   {status_icon} {status.upper()} ({len(assignment_list)}):")
                    for assignment in assignment_list[:5]:  # Show first 5
                        print(f"      • {assignment['diocese_name']} (Worker: {assignment['worker_id'][:12]}...)")
                    if len(assignment_list) > 5:
                        print(f"      ... and {len(assignment_list) - 5} more")
                    print()

    async def cleanup_stale_assignments(self, dry_run: bool = True):
        """Clean up stale work assignments"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=2)  # 2 hours

            # Find stale assignments
            stale_response = (
                self.supabase.table("diocese_work_assignments")
                .select("id, diocese_id, worker_id")
                .eq("status", "processing")
                .lt("assigned_at", cutoff_time.isoformat())
                .execute()
            )

            if stale_response.data:
                print(f"🧹 Found {len(stale_response.data)} stale assignments (older than 2 hours)")

                if not dry_run:
                    # Mark as failed
                    stale_ids = [a["id"] for a in stale_response.data]
                    self.supabase.table("diocese_work_assignments").update(
                        {"status": "failed", "completed_at": datetime.utcnow().isoformat()}
                    ).in_("id", stale_ids).execute()

                    print(f"✅ Marked {len(stale_ids)} stale assignments as failed")
                else:
                    print("🔍 Dry run - would mark these assignments as failed:")
                    for assignment in stale_response.data:
                        print(f"   • Diocese {assignment['diocese_id']} (Worker: {assignment['worker_id']})")
            else:
                print("✅ No stale assignments found")

        except Exception as e:
            logger.error(f"❌ Error cleaning up stale assignments: {e}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Monitor distributed pipeline cluster")
    parser.add_argument("--watch", action="store_true", help="Watch mode - refresh every 30 seconds")
    parser.add_argument("--cleanup", action="store_true", help="Clean up stale assignments")
    parser.add_argument("--no-dry-run", action="store_true", help="Actually perform cleanup (not just dry run)")

    args = parser.parse_args()

    monitor = PipelineMonitor()

    if args.cleanup:
        await monitor.cleanup_stale_assignments(dry_run=not args.no_dry_run)
        return

    if args.watch:
        print("👀 Watching cluster status (Ctrl+C to exit)...")
        try:
            while True:
                overview = await monitor.get_cluster_overview()

                # Clear screen
                print("\033[2J\033[H", end="")

                monitor.print_cluster_status(overview)
                print("Refreshing in 30 seconds... (Ctrl+C to exit)")

                await asyncio.sleep(30)
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")
    else:
        overview = await monitor.get_cluster_overview()
        monitor.print_cluster_status(overview)


if __name__ == "__main__":
    asyncio.run(main())
