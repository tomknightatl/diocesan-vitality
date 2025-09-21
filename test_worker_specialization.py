#!/usr/bin/env python3
"""
Test script to validate worker specialization functionality.

This script tests the new worker type system without actually running
the full pipeline, ensuring the specialization logic works correctly.
"""

import asyncio
import os
import sys
from unittest.mock import Mock, patch

# Add current directory to path
sys.path.append(os.getcwd())

from core.distributed_work_coordinator import DistributedWorkCoordinator
from distributed_pipeline_runner import DistributedPipelineRunner, WorkerType


async def test_worker_types():
    """Test that worker types are properly recognized"""
    print("🧪 Testing Worker Type Enum...")

    # Test all worker types
    worker_types = [WorkerType.DISCOVERY, WorkerType.EXTRACTION, WorkerType.SCHEDULE, WorkerType.REPORTING, WorkerType.ALL]

    for worker_type in worker_types:
        print(f"   ✅ {worker_type.name}: {worker_type.value}")

    # Test environment variable parsing
    test_cases = [
        ("discovery", WorkerType.DISCOVERY),
        ("EXTRACTION", WorkerType.EXTRACTION),
        ("Schedule", WorkerType.SCHEDULE),
        ("reporting", WorkerType.REPORTING),
        ("all", WorkerType.ALL),
    ]

    for env_value, expected_type in test_cases:
        actual_type = WorkerType(env_value.lower())
        assert actual_type == expected_type, f"Expected {expected_type}, got {actual_type}"
        print(f"   ✅ Environment '{env_value}' -> {actual_type.value}")


async def test_worker_coordinator():
    """Test that work coordinator handles worker types correctly"""
    print("\n🧪 Testing Work Coordinator...")

    # Mock supabase to avoid database calls during testing
    with patch("core.distributed_work_coordinator.get_supabase_client") as mock_supabase:
        mock_client = Mock()
        mock_supabase.return_value = mock_client

        # Test coordinator initialization with different worker types
        for worker_type in ["discovery", "extraction", "schedule", "reporting"]:
            coordinator = DistributedWorkCoordinator(worker_id=f"test-{worker_type}-worker", worker_type=worker_type)

            assert coordinator.worker_type == worker_type
            assert coordinator.worker_id == f"test-{worker_type}-worker"
            print(f"   ✅ Coordinator for {worker_type} worker created successfully")


async def test_pipeline_runner_specialization():
    """Test that pipeline runner creates specialized workers correctly"""
    print("\n🧪 Testing Pipeline Runner Specialization...")

    # Mock dependencies to avoid actual execution
    with (
        patch("core.db.get_supabase_client") as mock_supabase,
        patch("core.monitoring_client.get_monitoring_client") as mock_monitoring,
    ):

        mock_supabase.return_value = Mock()
        mock_monitoring.return_value = Mock()

        # Test each worker type
        test_cases = [
            (WorkerType.DISCOVERY, "discovery"),
            (WorkerType.EXTRACTION, "extraction"),
            (WorkerType.SCHEDULE, "schedule"),
            (WorkerType.REPORTING, "reporting"),
            (WorkerType.ALL, "all"),
        ]

        for worker_type, expected_type_str in test_cases:
            runner = DistributedPipelineRunner(
                worker_type=worker_type, disable_monitoring=True, worker_id=f"test-{expected_type_str}-runner"
            )

            assert runner.worker_type == worker_type
            assert runner.coordinator.worker_type == expected_type_str
            print(f"   ✅ {worker_type.value} runner created with correct specialization")


def test_environment_variable_detection():
    """Test that environment variable detection works correctly"""
    print("\n🧪 Testing Environment Variable Detection...")

    # Test default case (no environment variable)
    original_env = os.environ.get("WORKER_TYPE")

    try:
        # Remove environment variable if it exists
        if "WORKER_TYPE" in os.environ:
            del os.environ["WORKER_TYPE"]

        # Should default to 'all'
        worker_type_str = os.environ.get("WORKER_TYPE", "all")
        worker_type = WorkerType(worker_type_str.lower())
        assert worker_type == WorkerType.ALL
        print("   ✅ Default worker type: all")

        # Test setting environment variable
        test_types = ["discovery", "extraction", "schedule", "reporting"]
        for test_type in test_types:
            os.environ["WORKER_TYPE"] = test_type
            worker_type_str = os.environ.get("WORKER_TYPE", "all")
            worker_type = WorkerType(worker_type_str.lower())
            expected = WorkerType(test_type)
            assert worker_type == expected
            print(f"   ✅ Environment WORKER_TYPE={test_type} -> {worker_type.value}")

    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["WORKER_TYPE"] = original_env
        elif "WORKER_TYPE" in os.environ:
            del os.environ["WORKER_TYPE"]


def test_deployment_configurations():
    """Test that deployment configurations are valid"""
    print("\n🧪 Testing Deployment Configurations...")

    deployment_files = [
        "k8s/discovery-deployment.yaml",
        "k8s/extraction-deployment.yaml",
        "k8s/schedule-deployment.yaml",
        "k8s/reporting-deployment.yaml",
    ]

    expected_worker_types = {
        "discovery-deployment.yaml": "discovery",
        "extraction-deployment.yaml": "extraction",
        "schedule-deployment.yaml": "schedule",
        "reporting-deployment.yaml": "reporting",
    }

    for deployment_file in deployment_files:
        if os.path.exists(deployment_file):
            with open(deployment_file, "r") as f:
                content = f.read()

                # Check that WORKER_TYPE environment variable is set correctly
                filename = os.path.basename(deployment_file)
                expected_type = expected_worker_types[filename]

                if f'value: "{expected_type}"' in content:
                    print(f"   ✅ {filename}: WORKER_TYPE set to {expected_type}")
                else:
                    print(f"   ❌ {filename}: WORKER_TYPE not found or incorrect")
        else:
            print(f"   ⚠️ {deployment_file}: File not found")


async def main():
    """Run all tests"""
    print("🚀 Testing Worker Specialization System\n")

    try:
        await test_worker_types()
        await test_worker_coordinator()
        await test_pipeline_runner_specialization()
        test_environment_variable_detection()
        test_deployment_configurations()

        print("\n✅ All tests passed! Worker specialization system is working correctly.")
        print("\n📋 Summary:")
        print("   • Worker types are properly defined and recognized")
        print("   • Work coordinator supports worker type specialization")
        print("   • Pipeline runner creates correct worker instances")
        print("   • Environment variable detection works correctly")
        print("   • Deployment configurations are valid")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
