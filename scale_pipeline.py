#!/usr/bin/env python3
"""
Pipeline Scaling Utility

A utility script to manually scale the pipeline deployment up or down,
and monitor the effects on work distribution.
"""

import argparse
import subprocess
import time
import asyncio
from typing import Optional

from core.logger import get_logger
from monitor_distributed_pipeline import PipelineMonitor

logger = get_logger(__name__)


class PipelineScaler:
    """Utility for scaling pipeline deployment"""

    def __init__(self, namespace: str = "diocesan-vitality"):
        self.namespace = namespace
        self.deployment_name = "pipeline-deployment"
        self.monitor = PipelineMonitor()

    def get_current_replicas(self) -> Optional[int]:
        """Get current number of replicas"""
        try:
            result = subprocess.run([
                "kubectl", "get", "deployment", self.deployment_name,
                "-n", self.namespace,
                "-o", "jsonpath={.spec.replicas}"
            ], capture_output=True, text=True, check=True)

            return int(result.stdout.strip())

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error getting current replicas: {e}")
            return None
        except ValueError as e:
            logger.error(f"❌ Error parsing replica count: {e}")
            return None

    def scale_deployment(self, replicas: int) -> bool:
        """Scale deployment to specified number of replicas"""
        try:
            logger.info(f"🔧 Scaling {self.deployment_name} to {replicas} replicas...")

            result = subprocess.run([
                "kubectl", "scale", "deployment", self.deployment_name,
                f"--replicas={replicas}",
                "-n", self.namespace
            ], capture_output=True, text=True, check=True)

            logger.info(f"✅ Scaling command executed: {result.stdout.strip()}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error scaling deployment: {e}")
            if e.stderr:
                logger.error(f"Error details: {e.stderr}")
            return False

    def wait_for_scaling(self, target_replicas: int, timeout: int = 300):
        """Wait for scaling to complete"""
        logger.info(f"⏳ Waiting for scaling to complete (target: {target_replicas} replicas)...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check ready replicas
                result = subprocess.run([
                    "kubectl", "get", "deployment", self.deployment_name,
                    "-n", self.namespace,
                    "-o", "jsonpath={.status.readyReplicas}"
                ], capture_output=True, text=True, check=True)

                ready_replicas = int(result.stdout.strip()) if result.stdout.strip() else 0

                if ready_replicas == target_replicas:
                    logger.info(f"✅ Scaling completed! {ready_replicas}/{target_replicas} replicas ready")
                    return True

                logger.info(f"⏳ Scaling in progress: {ready_replicas}/{target_replicas} replicas ready")
                time.sleep(10)

            except (subprocess.CalledProcessError, ValueError) as e:
                logger.warning(f"⚠️ Error checking scaling status: {e}")
                time.sleep(5)

        logger.error(f"❌ Scaling timed out after {timeout} seconds")
        return False

    async def scale_and_monitor(self, target_replicas: int, monitor_duration: int = 120):
        """Scale deployment and monitor the effects"""
        current_replicas = self.get_current_replicas()
        if current_replicas is None:
            logger.error("❌ Cannot determine current replica count")
            return False

        logger.info(f"📊 Current replicas: {current_replicas}")

        if current_replicas == target_replicas:
            logger.info(f"✅ Already at target scale ({target_replicas} replicas)")
        else:
            # Perform scaling
            if not self.scale_deployment(target_replicas):
                return False

            # Wait for scaling to complete
            if not self.wait_for_scaling(target_replicas):
                return False

        # Monitor cluster for a while
        logger.info(f"👀 Monitoring cluster for {monitor_duration} seconds...")
        start_time = time.time()

        while time.time() - start_time < monitor_duration:
            overview = await self.monitor.get_cluster_overview()

            print("\n" + "="*50)
            print(f"⏰ Monitoring time: {int(time.time() - start_time)}s / {monitor_duration}s")
            self.monitor.print_cluster_status(overview)

            if time.time() - start_time < monitor_duration:
                await asyncio.sleep(30)

        logger.info("✅ Monitoring completed")
        return True


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Scale pipeline deployment and monitor effects")

    parser.add_argument("replicas", type=int, help="Target number of replicas")
    parser.add_argument("--namespace", "-n", default="diocesan-vitality",
                       help="Kubernetes namespace (default: diocesan-vitality)")
    parser.add_argument("--monitor-duration", type=int, default=120,
                       help="How long to monitor after scaling (seconds, default: 120)")
    parser.add_argument("--no-monitor", action="store_true",
                       help="Don't monitor after scaling")

    args = parser.parse_args()

    if args.replicas < 0:
        logger.error("❌ Replica count must be non-negative")
        return

    scaler = PipelineScaler(namespace=args.namespace)

    if args.no_monitor:
        # Just scale without monitoring
        current = scaler.get_current_replicas()
        if current is not None:
            logger.info(f"📊 Current replicas: {current}")

        if scaler.scale_deployment(args.replicas):
            scaler.wait_for_scaling(args.replicas)
    else:
        # Scale and monitor
        await scaler.scale_and_monitor(args.replicas, args.monitor_duration)


if __name__ == "__main__":
    asyncio.run(main())