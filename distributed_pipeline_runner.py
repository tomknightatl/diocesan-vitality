#!/usr/bin/env python3
"""
Distributed Pipeline Runner for Horizontal Scaling.

This is an enhanced version of run_pipeline.py that coordinates with other
pipeline pods to ensure respectful, non-conflicting data extraction.

Key Features:
- Diocese-based work partitioning
- Automatic failover and load balancing
- Respectful rate limiting across the cluster
- Real-time coordination via database
"""

import argparse
import asyncio
import time
import signal
import sys
from typing import Optional

from core.logger import get_logger
from core.monitoring_client import get_monitoring_client, ExtractionMonitoring
from core.distributed_work_coordinator import DistributedWorkCoordinator
import config

# Import the existing pipeline components
from extract_dioceses import main as extract_dioceses_main
from find_parishes import find_parish_directories
from async_extract_parishes import main_async as extract_parishes_main_async
from extract_schedule_respectful import main as extract_schedule_main
from report_statistics import main as report_statistics_main

logger = get_logger(__name__)


class DistributedPipelineRunner:
    """
    Distributed pipeline runner that coordinates with other pods.
    """

    def __init__(self,
                 max_parishes_per_diocese: int = 50,
                 num_parishes_for_schedule: int = 101,
                 monitoring_url: str = "http://backend-service:8000",
                 disable_monitoring: bool = False,
                 worker_id: Optional[str] = None):

        self.max_parishes_per_diocese = max_parishes_per_diocese
        self.num_parishes_for_schedule = num_parishes_for_schedule
        self.monitoring_url = monitoring_url
        self.disable_monitoring = disable_monitoring

        # Initialize coordinator
        self.coordinator = DistributedWorkCoordinator(worker_id=worker_id)

        # Initialize monitoring
        self.monitoring_client = get_monitoring_client(monitoring_url)
        if disable_monitoring:
            self.monitoring_client.disable()
            logger.info("📊 Monitoring disabled")
        else:
            logger.info(f"📊 Monitoring enabled: {monitoring_url}")

        # Graceful shutdown handling
        self.shutdown_requested = False
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("🚀 Distributed Pipeline Runner initialized")

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
                f"Pipeline │ Starting distributed pipeline (Worker: {self.coordinator.worker_id})",
                "INFO"
            )

            start_time = time.time()

            if not config.validate_config():
                self.monitoring_client.report_error(
                    error_type="ConfigurationError",
                    message="Missing configuration - pipeline cannot start"
                )
                logger.error("Exiting due to missing configuration.")
                return

            # Run coordinated pipeline steps
            await self._run_coordinated_extraction()

            # Generate reports (can be done by any worker)
            await self._run_reporting_if_needed()

            total_time = time.time() - start_time
            self.monitoring_client.send_log(
                f"Pipeline │ 🎉 Distributed pipeline completed in {total_time:.1f} seconds",
                "INFO"
            )

        except Exception as e:
            logger.error(f"❌ Error in distributed pipeline: {e}", exc_info=True)
            self.monitoring_client.report_error(
                error_type="DistributedPipelineError",
                message=f"Distributed pipeline failed: {str(e)}"
            )
        finally:
            await self.coordinator.shutdown()

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
                logger.info(f"🏗️ Cluster status: {cluster_status['active_workers']} workers, "
                          f"{cluster_status['total_active_assignments']} active assignments")

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
                    status="running",
                    current_diocese=diocese['name'],
                    parishes_processed=0
                )

                # Extract parishes for this diocese
                with ExtractionMonitoring(diocese['name'], self.max_parishes_per_diocese) as monitor:
                    self.monitoring_client.send_log(
                        f"Diocese │ {diocese['name']}: Starting parish extraction",
                        "INFO"
                    )

                    # Run async parish extraction for this specific diocese
                    results = await extract_parishes_main_async(
                        diocese_id=diocese['id'],
                        num_parishes_per_diocese=self.max_parishes_per_diocese,
                        pool_size=4,
                        batch_size=8,
                        max_concurrent_dioceses=1  # Only process one diocese at a time per worker
                    )

                    if results and results.get('successful_dioceses'):
                        parishes_extracted = results['total_parishes_extracted']
                        monitor.update_progress(self.max_parishes_per_diocese, parishes_extracted)

                        self.monitoring_client.send_log(
                            f"Diocese │ {diocese['name']}: ✅ Extracted {parishes_extracted} parishes",
                            "INFO"
                        )
                    else:
                        self.monitoring_client.send_log(
                            f"Diocese │ {diocese['name']}: ⚠️ No parishes extracted",
                            "WARNING"
                        )

                # Mark diocese as completed
                await self.coordinator.mark_diocese_completed(diocese['id'], 'completed')

                # Respectful delay between dioceses
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"❌ Error processing diocese {diocese['name']}: {e}")
                await self.coordinator.mark_diocese_completed(diocese['id'], 'failed')

                self.monitoring_client.report_error(
                    error_type="DioceseProcessingError",
                    message=f"Failed to process diocese {diocese['name']}: {str(e)}",
                    diocese=diocese['name']
                )

    async def _run_reporting_if_needed(self):
        """Run reporting step if no other worker is doing it"""
        try:
            # Simple coordination: only run reports if we're the "lead" worker
            # (could be enhanced with more sophisticated coordination)
            cluster_status = await self.coordinator.get_cluster_status()

            # If we're the only worker or the first worker alphabetically, run reports
            if (not cluster_status['workers'] or
                self.coordinator.worker_id == min(w['worker_id'] for w in cluster_status['workers'])):

                logger.info("📊 Running report generation as lead worker")

                self.monitoring_client.send_log("Reports │ Generating statistical reports", "INFO")

                try:
                    report_statistics_main()
                    self.monitoring_client.send_log("Reports │ ✅ Report generation completed", "INFO")
                except Exception as e:
                    logger.error(f"❌ Report generation failed: {e}")
                    self.monitoring_client.report_error(
                        error_type="ReportingError",
                        message=f"Report generation failed: {str(e)}"
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
    parser = argparse.ArgumentParser(description="Run distributed data extraction pipeline.")

    parser.add_argument("--max_parishes_per_diocese", type=int, default=50,
                       help="Max parishes to extract per diocese.")
    parser.add_argument("--num_parishes_for_schedule", type=int, default=101,
                       help="Number of parishes to extract schedules for.")
    parser.add_argument("--monitoring_url", type=str, default="http://backend-service:8000",
                       help="Monitoring backend URL.")
    parser.add_argument("--disable_monitoring", action="store_true",
                       help="Disable monitoring integration.")
    parser.add_argument("--worker_id", type=str, default=None,
                       help="Custom worker ID (auto-generated if not provided).")

    args = parser.parse_args()

    # Initialize and run distributed pipeline
    runner = DistributedPipelineRunner(
        max_parishes_per_diocese=args.max_parishes_per_diocese,
        num_parishes_for_schedule=args.num_parishes_for_schedule,
        monitoring_url=args.monitoring_url,
        disable_monitoring=args.disable_monitoring,
        worker_id=args.worker_id
    )

    await runner.run_distributed_pipeline()


def main():
    """Synchronous wrapper for the async main function"""
    return asyncio.run(main_async())


if __name__ == "__main__":
    main()