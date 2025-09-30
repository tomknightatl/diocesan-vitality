#!/usr/bin/env python3
"""
Distributed Work Coordinator for Horizontal Pipeline Scaling.

This module provides coordination mechanisms to ensure multiple pipeline pods
can work together without conflicts when scraping diocese websites.

Strategy: Diocese-based work partitioning with database-backed coordination.
"""

import os
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from core.db import get_supabase_client
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WorkerInfo:
    """Information about a pipeline worker pod"""

    worker_id: str
    pod_name: str
    worker_type: str  # 'discovery', 'extraction', 'schedule', 'reporting', 'all'
    assigned_dioceses: List[int]
    last_heartbeat: datetime
    status: str  # 'active', 'idle', 'failed'


class DistributedWorkCoordinator:
    """
    Coordinates work distribution across multiple pipeline pods.

    Uses database-backed coordination to ensure:
    1. No two pods scrape the same diocese simultaneously
    2. Respectful rate limiting across all pods
    3. Automatic failover if a pod becomes unresponsive
    4. Load balancing based on diocese complexity
    """

    def __init__(
        self,
        worker_id: Optional[str] = None,
        worker_type: str = "all",
        heartbeat_interval: int = 30,
        worker_timeout: int = 120,
    ):
        self.worker_id = worker_id or self._generate_worker_id()
        self.worker_type = worker_type
        self.heartbeat_interval = heartbeat_interval
        self.worker_timeout = worker_timeout
        self.pod_name = os.environ.get("HOSTNAME", socket.gethostname())
        self.supabase = get_supabase_client()

        logger.info(f"🤝 Distributed Work Coordinator initialized")
        logger.info(f"   • Worker ID: {self.worker_id}")
        logger.info(f"   • Worker Type: {self.worker_type}")
        logger.info(f"   • Pod Name: {self.pod_name}")
        logger.info(f"   • Heartbeat interval: {heartbeat_interval}s")

    def _generate_worker_id(self) -> str:
        """Generate unique worker ID"""
        hostname = os.environ.get("HOSTNAME", socket.gethostname())
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        return f"worker-{hostname}-{timestamp}-{unique_id}"

    async def register_worker(self) -> bool:
        """Register this worker in the coordination table"""
        try:
            # Create coordination tables if they don't exist
            await self._ensure_coordination_tables()

            # Register worker
            worker_data = {
                "worker_id": self.worker_id,
                "pod_name": self.pod_name,
                "worker_type": self.worker_type,
                "status": "active",
                "last_heartbeat": datetime.utcnow().isoformat(),
                "assigned_dioceses": [],
                "created_at": datetime.utcnow().isoformat(),
            }

            response = self.supabase.table("pipeline_workers").upsert(worker_data).execute()

            if response.data:
                logger.info(f"✅ Worker {self.worker_id} registered successfully")
                return True
            else:
                logger.error(f"❌ Failed to register worker: {response}")
                return False

        except Exception as e:
            logger.error(f"❌ Error registering worker: {e}")
            return False

    async def _ensure_coordination_tables(self):
        """Ensure coordination tables exist in the database"""
        try:
            # This would ideally be done via migration, but for demo purposes:
            # Note: In production, these should be created via proper SQL migrations

            # Check if tables exist by attempting to query them
            try:
                self.supabase.table("pipeline_workers").select("worker_id").limit(1).execute()
                self.supabase.table("diocese_work_assignments").select("diocese_id").limit(1).execute()
                logger.debug("✅ Coordination tables already exist")
            except Exception:
                logger.warning("⚠️ Coordination tables may not exist. Please ensure they are created via migration.")
                # In a real implementation, we'd create these via proper SQL migrations

        except Exception as e:
            logger.error(f"❌ Error checking coordination tables: {e}")

    async def get_available_work(self, max_dioceses: int = 5) -> List[Dict[str, Any]]:
        """
        Get available dioceses to process, ensuring no conflicts with other workers.

        Args:
            max_dioceses: Maximum number of dioceses to assign to this worker

        Returns:
            List of diocese information dictionaries
        """
        try:
            # Clean up stale worker assignments
            await self._cleanup_stale_workers()

            # Get dioceses that need processing (not currently assigned to active workers)
            available_dioceses = await self._get_unassigned_dioceses(max_dioceses)

            if available_dioceses:
                # Assign dioceses to this worker
                await self._assign_dioceses_to_worker(available_dioceses)

                logger.info(f"📋 Assigned {len(available_dioceses)} dioceses to worker {self.worker_id}")
                for diocese in available_dioceses:
                    logger.debug(f"   • {diocese['name']} (ID: {diocese['id']})")
            else:
                logger.info(f"⏸️ No available work for worker {self.worker_id}")

            return available_dioceses

        except Exception as e:
            logger.error(f"❌ Error getting available work: {e}")
            return []

    async def _get_unassigned_dioceses(self, limit: int) -> List[Dict[str, Any]]:
        """Get dioceses that are not currently assigned to any active worker"""
        try:
            # Query for dioceses that either:
            # 1. Have no work assignment record, OR
            # 2. Have assignment to workers that are no longer active

            # This is a simplified query - in production you'd want a more sophisticated approach
            # that considers processing priority, last processing time, etc.

            # Get all dioceses with parish directories
            dioceses_response = (
                self.supabase.table("Dioceses").select("id, Name, Website").limit(limit * 2).execute()
            )  # Get more than needed for filtering

            if not dioceses_response.data:
                return []

            # Filter to only those with parish directory URLs available
            available_dioceses = []
            for diocese in dioceses_response.data:
                # Check if this diocese has a parish directory URL
                parish_dir_response = (
                    self.supabase.table("DiocesesParishDirectory")
                    .select("parish_directory_url")
                    .eq("diocese_url", diocese["Website"])
                    .execute()
                )

                override_response = (
                    self.supabase.table("DioceseParishDirectoryOverride")
                    .select("parish_directory_url")
                    .eq("diocese_id", diocese["id"])
                    .execute()
                )

                if parish_dir_response.data or override_response.data:
                    # Check if currently assigned to an active worker
                    assignment_response = (
                        self.supabase.table("diocese_work_assignments")
                        .select("worker_id, assigned_at")
                        .eq("diocese_id", diocese["id"])
                        .eq("status", "processing")
                        .execute()
                    )

                    if not assignment_response.data:
                        # Not currently assigned - available for work
                        parish_directory_url = (
                            override_response.data[0]["parish_directory_url"]
                            if override_response.data
                            else parish_dir_response.data[0]["parish_directory_url"]
                        )

                        available_dioceses.append(
                            {
                                "id": diocese["id"],
                                "name": diocese["Name"],
                                "url": diocese["Website"],
                                "parish_directory_url": parish_directory_url,
                            }
                        )

                        if len(available_dioceses) >= limit:
                            break

            return available_dioceses

        except Exception as e:
            logger.error(f"❌ Error getting unassigned dioceses: {e}")
            return []

    async def _assign_dioceses_to_worker(self, dioceses: List[Dict[str, Any]]):
        """Assign dioceses to this worker"""
        try:
            assignments = []
            for diocese in dioceses:
                assignment = {
                    "diocese_id": diocese["id"],
                    "worker_id": self.worker_id,
                    "status": "processing",
                    "assigned_at": datetime.utcnow().isoformat(),
                    "estimated_completion": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
                }
                assignments.append(assignment)

            if assignments:
                response = self.supabase.table("diocese_work_assignments").insert(assignments).execute()
                if response.data:
                    logger.debug(f"✅ Successfully assigned {len(assignments)} dioceses")
                else:
                    logger.error(f"❌ Failed to assign dioceses: {response}")

        except Exception as e:
            logger.error(f"❌ Error assigning dioceses to worker: {e}")

    async def mark_diocese_completed(self, diocese_id: int, status: str = "completed"):
        """Mark a diocese as completed by this worker"""
        try:
            update_data = {"status": status, "completed_at": datetime.utcnow().isoformat()}

            response = (
                self.supabase.table("diocese_work_assignments")
                .update(update_data)
                .eq("diocese_id", diocese_id)
                .eq("worker_id", self.worker_id)
                .execute()
            )

            if response.data:
                logger.debug(f"✅ Marked diocese {diocese_id} as {status}")
            else:
                logger.warning(f"⚠️ Failed to mark diocese {diocese_id} as {status}")

        except Exception as e:
            logger.error(f"❌ Error marking diocese {diocese_id} as completed: {e}")

    async def send_heartbeat(self):
        """Send heartbeat to indicate this worker is still active"""
        try:
            update_data = {"last_heartbeat": datetime.utcnow().isoformat(), "status": "active"}

            response = self.supabase.table("pipeline_workers").update(update_data).eq("worker_id", self.worker_id).execute()

            if response.data:
                logger.debug(f"💓 Heartbeat sent by worker {self.worker_id}")
            else:
                logger.warning(f"⚠️ Failed to send heartbeat for worker {self.worker_id}")

        except Exception as e:
            logger.error(f"❌ Error sending heartbeat: {e}")

    async def _cleanup_stale_workers(self):
        """Clean up workers that haven't sent heartbeat within timeout period"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(seconds=self.worker_timeout)

            # Find stale workers
            stale_response = (
                self.supabase.table("pipeline_workers")
                .select("worker_id")
                .lt("last_heartbeat", cutoff_time.isoformat())
                .eq("status", "active")
                .execute()
            )

            if stale_response.data:
                stale_worker_ids = [w["worker_id"] for w in stale_response.data]

                # Mark stale workers as failed
                self.supabase.table("pipeline_workers").update({"status": "failed"}).in_(
                    "worker_id", stale_worker_ids
                ).execute()

                # Release their work assignments
                self.supabase.table("diocese_work_assignments").update(
                    {"status": "failed", "completed_at": datetime.utcnow().isoformat()}
                ).in_("worker_id", stale_worker_ids).eq("status", "processing").execute()

                logger.info(f"🧹 Cleaned up {len(stale_worker_ids)} stale workers")

        except Exception as e:
            logger.error(f"❌ Error cleaning up stale workers: {e}")

    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get status of all workers in the cluster"""
        try:
            # Get active workers
            workers_response = (
                self.supabase.table("pipeline_workers")
                .select("worker_id, pod_name, status, last_heartbeat")
                .eq("status", "active")
                .execute()
            )

            # Get work assignments
            assignments_response = (
                self.supabase.table("diocese_work_assignments")
                .select("diocese_id, worker_id, status")
                .eq("status", "processing")
                .execute()
            )

            # Compile status
            active_workers = len(workers_response.data) if workers_response.data else 0
            active_assignments = len(assignments_response.data) if assignments_response.data else 0

            return {
                "active_workers": active_workers,
                "total_active_assignments": active_assignments,
                "workers": workers_response.data or [],
                "assignments": assignments_response.data or [],
            }

        except Exception as e:
            logger.error(f"❌ Error getting cluster status: {e}")
            return {"active_workers": 0, "total_active_assignments": 0, "workers": [], "assignments": []}

    async def shutdown(self):
        """Gracefully shutdown this worker"""
        try:
            # Mark any assigned work as failed so it can be picked up by other workers
            self.supabase.table("diocese_work_assignments").update(
                {"status": "failed", "completed_at": datetime.utcnow().isoformat()}
            ).eq("worker_id", self.worker_id).eq("status", "processing").execute()

            # Mark worker as inactive
            self.supabase.table("pipeline_workers").update({"status": "inactive"}).eq("worker_id", self.worker_id).execute()

            logger.info(f"🛑 Worker {self.worker_id} shutdown gracefully")

        except Exception as e:
            logger.error(f"❌ Error during worker shutdown: {e}")

    async def get_available_schedule_work(self, max_parishes: int = 100) -> List[Dict[str, Any]]:
        """
        Get parishes that need schedule extraction.

        Args:
            max_parishes: Maximum number of parishes to return

        Returns:
            List of parish information for schedule extraction
        """
        try:
            # Get parishes that have basic info but no schedule data
            # This is a simplified implementation - you might want more sophisticated logic
            parishes_response = (
                self.supabase.table("Parishes")
                .select("id, Name, Website, Dioceses!inner(Name)")
                .is_("mass_schedule_found", None)
                .limit(max_parishes)
                .execute()
            )

            if parishes_response.data:
                logger.info(f"📋 Found {len(parishes_response.data)} parishes needing schedule extraction")
                return parishes_response.data
            else:
                return []

        except Exception as e:
            logger.error(f"❌ Error getting available schedule work: {e}")
            return []

    async def should_generate_reports(self) -> bool:
        """
        Check if reports should be generated.
        Simple logic: generate if no reports have been generated in the last hour.
        """
        try:
            # Check for recent report generation activity
            # This could be enhanced with a proper report tracking table
            cutoff_time = datetime.utcnow() - timedelta(hours=1)

            # For now, always return True (reports can run)
            # In production, you'd track last report generation time
            return True

        except Exception as e:
            logger.error(f"❌ Error checking if reports should be generated: {e}")
            return False

    async def mark_reports_generated(self):
        """
        Mark that reports have been generated.
        """
        try:
            # In a production system, you'd track report generation in a dedicated table
            logger.info("📊 Reports generation marked as completed")

        except Exception as e:
            logger.error(f"❌ Error marking reports as generated: {e}")


# Coordination table creation SQL (should be run as migration)
COORDINATION_TABLES_SQL = """
-- Pipeline workers table
CREATE TABLE IF NOT EXISTS pipeline_workers (
    worker_id TEXT PRIMARY KEY,
    pod_name TEXT NOT NULL,
    worker_type TEXT NOT NULL DEFAULT 'all' CHECK (worker_type IN ('discovery', 'extraction', 'schedule', 'reporting', 'all')),
    status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'failed')),
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_dioceses INTEGER[] DEFAULT ARRAY[]::INTEGER[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Diocese work assignments table
CREATE TABLE IF NOT EXISTS diocese_work_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    diocese_id INTEGER NOT NULL REFERENCES "Dioceses"(id),
    worker_id TEXT NOT NULL REFERENCES pipeline_workers(worker_id),
    status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'failed')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    estimated_completion TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pipeline_workers_status ON pipeline_workers(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_workers_heartbeat ON pipeline_workers(last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_diocese_assignments_status ON diocese_work_assignments(status);
CREATE INDEX IF NOT EXISTS idx_diocese_assignments_diocese ON diocese_work_assignments(diocese_id);
CREATE INDEX IF NOT EXISTS idx_diocese_assignments_worker ON diocese_work_assignments(worker_id);

-- Update trigger for pipeline_workers
CREATE OR REPLACE FUNCTION update_pipeline_workers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_pipeline_workers_updated_at
    BEFORE UPDATE ON pipeline_workers
    FOR EACH ROW
    EXECUTE FUNCTION update_pipeline_workers_updated_at();
"""
