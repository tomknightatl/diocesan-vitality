#!/usr/bin/env python3
"""
Distributed Pipeline Runner for Horizontal Scaling with Worker Specialization.

This is an enhanced version of run_pipeline.py that coordinates with other
pipeline pods to ensure respectful, non-conflicting data extraction with
specialized worker types.

Key Features:
- Diocese-based work partitioning
- Worker type specialization (discovery, extraction, schedule, reporting)
- Automatic failover and load balancing
- Respectful rate limiting across the cluster
- Real-time coordination via database
- Single image deployment with runtime specialization
"""

import argparse
import asyncio
import os
import signal
import sys
import time
from enum import Enum
from typing import Optional

import config
from async_extract_parishes import main_async as extract_parishes_main_async
from core.distributed_work_coordinator import DistributedWorkCoordinator
from core.logger import get_logger
from core.monitoring_client import ExtractionMonitoring, get_monitoring_client

# Import the existing pipeline components
from extract_dioceses import main as extract_dioceses_main
from extract_schedule_respectful import main as extract_schedule_main
from find_parishes import find_parish_directories
from report_statistics import main as report_statistics_main

logger = get_logger(__name__)


class WorkerType(Enum):
    """Specialized worker types for different pipeline stages"""

    DISCOVERY = "discovery"  # Steps 1-2: Diocese + Parish directory discovery
    EXTRACTION = "extraction"  # Step 3: Parish detail extraction
    SCHEDULE = "schedule"  # Step 4: Schedule extraction
    REPORTING = "reporting"  # Step 5: Report generation
    ALL = "all"  # Backwards compatible - runs all steps


class DistributedPipelineRunner:
    """
    Distributed pipeline runner that coordinates with other pods.
    """

    def __init__(
        self,
        worker_type: WorkerType = WorkerType.ALL,
        max_parishes_per_diocese: int = 50,
        num_parishes_for_schedule: int = 101,
        monitoring_url: str = "http://backend-service:8000",
        disable_monitoring: bool = False,
        worker_id: Optional[str] = None,
    ):

        self.worker_type = worker_type
        self.max_parishes_per_diocese = max_parishes_per_diocese
        self.num_parishes_for_schedule = num_parishes_for_schedule
        self.monitoring_url = monitoring_url
        self.disable_monitoring = disable_monitoring

        # Initialize coordinator with worker type information
        self.coordinator = DistributedWorkCoordinator(worker_id=worker_id, worker_type=worker_type.value)

        # Initialize monitoring with the actual worker_id from coordinator
        self.monitoring_client = get_monitoring_client(monitoring_url, self.coordinator.worker_id)
        if disable_monitoring:
            self.monitoring_client.disable()
            logger.info("📊 Monitoring disabled")
        else:
            logger.info(f"📊 Monitoring enabled: {monitoring_url}")

        # Graceful shutdown handling
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info(f"🚀 Distributed Pipeline Runner initialized (Worker Type: {worker_type.value})")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True

    async def run_distributed_pipeline(self):
        """
        Run the distributed pipeline with coordination.
        """
        try:
            # Register this worker
            if not await self.coordinator.register_worker():
                logger.error("❌ Failed to register worker - cannot proceed")
                return

            self.monitoring_client.send_log(
                f"Pipeline │ Starting distributed pipeline (Worker: {self.coordinator.worker_id}, Type: {self.worker_type.value})",
                "INFO",
            )

            start_time = time.time()

            if not config.validate_config():
                self.monitoring_client.report_error(
                    error_type="ConfigurationError", message="Missing configuration - pipeline cannot start"
                )
                logger.error("Exiting due to missing configuration.")
                return

            # Run specialized worker logic based on worker type
            await self._run_specialized_worker()

            # Generate reports if this worker type handles reporting
            if self.worker_type in [WorkerType.REPORTING, WorkerType.ALL]:
                await self._run_reporting_if_needed()

            total_time = time.time() - start_time
            self.monitoring_client.send_log(
                f"Pipeline │ 🎉 Distributed pipeline completed in {total_time:.1f} seconds", "INFO"
            )

        except Exception as e:
            logger.error(f"❌ Error in distributed pipeline: {e}", exc_info=True)
            self.monitoring_client.report_error(
                error_type="DistributedPipelineError", message=f"Distributed pipeline failed: {str(e)}"
            )
        finally:
            await self.coordinator.shutdown()

    async def _run_specialized_worker(self):
        """
        Run worker logic based on the specialized worker type.
        """
        logger.info(f"🎯 Running specialized worker: {self.worker_type.value}")

        if self.worker_type == WorkerType.DISCOVERY:
            await self._run_discovery_worker()
        elif self.worker_type == WorkerType.EXTRACTION:
            await self._run_extraction_worker()
        elif self.worker_type == WorkerType.SCHEDULE:
            await self._run_schedule_worker()
        elif self.worker_type == WorkerType.REPORTING:
            await self._run_reporting_worker()
        elif self.worker_type == WorkerType.ALL:
            # Backwards compatible - run coordinated extraction
            await self._run_coordinated_extraction()
        else:
            logger.error(f"❌ Unknown worker type: {self.worker_type}")

    async def _run_discovery_worker(self):
        """
        Run diocese and parish directory discovery (Steps 1-2).
        Lightweight worker that runs periodically.
        """
        logger.info("🔍 Running discovery worker (Steps 1-2)")

        try:
            while not self.shutdown_requested:
                # Step 1: Extract Dioceses
                self.monitoring_client.send_log("Step 1 │ Extract Dioceses: Discovering new dioceses", "INFO")
                extract_dioceses_main(max_dioceses=0)  # No limit for discovery
                self.monitoring_client.send_log("Step 1 │ ✅ Diocese extraction completed", "INFO")

                # Step 2: Find Parish Directories
                self.monitoring_client.send_log("Step 2 │ Find Parish Directories: AI-powered directory discovery", "INFO")
                find_parish_directories(diocese_id=None, max_dioceses_to_process=0)  # Process all
                self.monitoring_client.send_log("Step 2 │ ✅ Parish directory discovery completed", "INFO")

                # Discovery workers can sleep longer between cycles
                logger.info("⏸️ Discovery worker completed - sleeping for next cycle (5 minutes)")
                await asyncio.sleep(300)  # 5 minute sleep for discovery workers

        except Exception as e:
            logger.error(f"❌ Error in discovery worker: {e}")
            self.monitoring_client.report_error(
                error_type="DiscoveryWorkerError", message=f"Discovery worker failed: {str(e)}"
            )

    async def _run_extraction_worker(self):
        """
        Run parish detail extraction (Step 3).
        High-performance worker for concurrent parish processing.
        """
        logger.info("⚡ Running extraction worker (Step 3)")
        await self._run_coordinated_extraction()

    async def _run_schedule_worker(self):
        """
        Run schedule extraction (Step 4).
        WebDriver-intensive worker for schedule parsing.
        """
        logger.info("📅 Running schedule worker (Step 4)")

        # Heartbeat task to keep worker alive
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        try:
            while not self.shutdown_requested:
                # Get parishes that need schedule extraction
                available_work = await self.coordinator.get_available_schedule_work(
                    max_parishes=self.num_parishes_for_schedule
                )

                if not available_work:
                    logger.info("⏸️ No schedule work available, waiting...")
                    await asyncio.sleep(60)
                    continue

                # Process schedule extraction
                self.monitoring_client.send_log(
                    f"Step 4 │ Extract Schedules: Processing {len(available_work)} parishes", "INFO"
                )

                extract_schedule_main(
                    num_parishes=len(available_work), parish_id=None, max_pages_per_parish=10, diocese_id=None
                )

                self.monitoring_client.send_log("Step 4 │ ✅ Schedule extraction batch completed", "INFO")

                # Respectful delay between batches
                await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"❌ Error in schedule worker: {e}")
            self.monitoring_client.report_error(error_type="ScheduleWorkerError", message=f"Schedule worker failed: {str(e)}")
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    async def _run_reporting_worker(self):
        """
        Run reporting and analytics (Step 5).
        Lightweight worker for data analysis and report generation.
        """
        logger.info("📊 Running reporting worker (Step 5)")

        try:
            while not self.shutdown_requested:
                # Check if reports need to be generated
                if await self.coordinator.should_generate_reports():
                    self.monitoring_client.send_log("Step 5 │ Generating reports and analytics", "INFO")

                    report_statistics_main()

                    self.monitoring_client.send_log("Step 5 │ ✅ Report generation completed", "INFO")
                    await self.coordinator.mark_reports_generated()

                # Reports don't need to run frequently
                await asyncio.sleep(600)  # 10 minute sleep for reporting

        except Exception as e:
            logger.error(f"❌ Error in reporting worker: {e}")
            self.monitoring_client.report_error(
                error_type="ReportingWorkerError", message=f"Reporting worker failed: {str(e)}"
            )

    async def _run_coordinated_extraction(self):
        """
        Run the main extraction pipeline with coordination.
        """
        # Heartbeat task to keep worker alive
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        try:
            while not self.shutdown_requested:
                # Get available work from coordinator
                available_dioceses = await self.coordinator.get_available_work(
                    max_dioceses=5  # Process up to 5 dioceses at a time
                )

                if not available_dioceses:
                    # No work available - wait and check again
                    logger.info("⏸️ No work available, waiting for new assignments...")
                    await asyncio.sleep(30)
                    continue

                # Process assigned dioceses
                await self._process_assigned_dioceses(available_dioceses)

                # Check cluster status
                cluster_status = await self.coordinator.get_cluster_status()
                logger.info(
                    f"🏗️ Cluster status: {cluster_status['active_workers']} workers, "
                    f"{cluster_status['total_active_assignments']} active assignments"
                )

        except Exception as e:
            logger.error(f"❌ Error in coordinated extraction: {e}")
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    async def _process_assigned_dioceses(self, dioceses):
        """Process the dioceses assigned to this worker"""
        for diocese in dioceses:
            if self.shutdown_requested:
                break

            try:
                logger.info(f"🏢 Processing diocese: {diocese['name']} (ID: {diocese['id']})")

                # Update monitoring
                self.monitoring_client.update_extraction_status(
                    status="running", current_diocese=diocese["name"], parishes_processed=0
                )

                # Extract parishes for this diocese
                with ExtractionMonitoring(diocese["name"], self.max_parishes_per_diocese) as monitor:
                    self.monitoring_client.send_log(f"Diocese │ {diocese['name']}: Starting parish extraction", "INFO")

                    # Run async parish extraction for this specific diocese
                    results = await extract_parishes_main_async(
                        diocese_id=diocese["id"],
                        num_parishes_per_diocese=self.max_parishes_per_diocese,
                        pool_size=4,
                        batch_size=8,
                        max_concurrent_dioceses=1,  # Only process one diocese at a time per worker
                    )

                    if results and results.get("successful_dioceses"):
                        parishes_extracted = results["total_parishes_extracted"]
                        monitor.update_progress(self.max_parishes_per_diocese, parishes_extracted)

                        self.monitoring_client.send_log(
                            f"Diocese │ {diocese['name']}: ✅ Extracted {parishes_extracted} parishes", "INFO"
                        )
                    else:
                        self.monitoring_client.send_log(f"Diocese │ {diocese['name']}: ⚠️ No parishes extracted", "WARNING")

                # Mark diocese as completed
                await self.coordinator.mark_diocese_completed(diocese["id"], "completed")

                # Respectful delay between dioceses
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"❌ Error processing diocese {diocese['name']}: {e}")
                await self.coordinator.mark_diocese_completed(diocese["id"], "failed")

                self.monitoring_client.report_error(
                    error_type="DioceseProcessingError",
                    message=f"Failed to process diocese {diocese['name']}: {str(e)}",
                    diocese=diocese["name"],
                )

    async def _run_reporting_if_needed(self):
        """Run reporting step if no other worker is doing it"""
        try:
            # Simple coordination: only run reports if we're the "lead" worker
            # (could be enhanced with more sophisticated coordination)
            cluster_status = await self.coordinator.get_cluster_status()

            # If we're the only worker or the first worker alphabetically, run reports
            if not cluster_status["workers"] or self.coordinator.worker_id == min(
                w["worker_id"] for w in cluster_status["workers"]
            ):

                logger.info("📊 Running report generation as lead worker")

                self.monitoring_client.send_log("Reports │ Generating statistical reports", "INFO")

                try:
                    report_statistics_main()
                    self.monitoring_client.send_log("Reports │ ✅ Report generation completed", "INFO")
                except Exception as e:
                    logger.error(f"❌ Report generation failed: {e}")
                    self.monitoring_client.report_error(
                        error_type="ReportingError", message=f"Report generation failed: {str(e)}"
                    )

        except Exception as e:
            logger.error(f"❌ Error in reporting step: {e}")

    async def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain worker registration"""
        while not self.shutdown_requested:
            try:
                await self.coordinator.send_heartbeat()
                await asyncio.sleep(self.coordinator.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error sending heartbeat: {e}")
                await asyncio.sleep(5)


async def main_async():
    """Main async function for distributed pipeline"""
    parser = argparse.ArgumentParser(description="Run distributed data extraction pipeline with worker specialization.")

    parser.add_argument(
        "--worker_type",
        type=str,
        choices=[wt.value for wt in WorkerType],
        default=None,
        help="Worker type specialization (discovery, extraction, schedule, reporting, all)",
    )
    parser.add_argument("--max_parishes_per_diocese", type=int, default=50, help="Max parishes to extract per diocese.")
    parser.add_argument(
        "--num_parishes_for_schedule", type=int, default=101, help="Number of parishes to extract schedules for."
    )
    parser.add_argument("--monitoring_url", type=str, default="http://backend-service:8000", help="Monitoring backend URL.")
    parser.add_argument("--disable_monitoring", action="store_true", help="Disable monitoring integration.")
    parser.add_argument("--worker_id", type=str, default=None, help="Custom worker ID (auto-generated if not provided).")

    args = parser.parse_args()

    # Determine worker type from args or environment variable
    worker_type_str = args.worker_type or os.environ.get("WORKER_TYPE", "all")
    worker_type = WorkerType(worker_type_str.lower())

    # Initialize and run distributed pipeline
    runner = DistributedPipelineRunner(
        worker_type=worker_type,
        max_parishes_per_diocese=args.max_parishes_per_diocese,
        num_parishes_for_schedule=args.num_parishes_for_schedule,
        monitoring_url=args.monitoring_url,
        disable_monitoring=args.disable_monitoring,
        worker_id=args.worker_id,
    )

    await runner.run_distributed_pipeline()


def main():
    """Synchronous wrapper for the async main function"""
    return asyncio.run(main_async())


if __name__ == "__main__":
    main()
