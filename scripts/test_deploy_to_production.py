#!/usr/bin/env python3
"""
Test script for deploy_to_production.py

This script validates the functionality of the production deployment script
by testing various workflows and safety checks in dry-run mode.

Usage:
    python scripts/test_deploy_to_production.py
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, expected_fail=False):
    """Run a command and return success status."""
    print(f"\n{'='*80}")
    print(f"TEST: {description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        print(f"Exit Code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout[:1000]}")  # Truncate long output
        if result.stderr:
            print(f"STDERR:\n{result.stderr[:1000]}")

        # If we expect failure, success means the command failed as expected
        if expected_fail:
            success = result.returncode != 0
            if success:
                print("✓ Test passed: Command failed as expected")
            else:
                print("✗ Test failed: Command should have failed but succeeded")
        else:
            success = result.returncode == 0

        return success
    except subprocess.TimeoutExpired:
        print("✗ Command timed out")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing deploy_to_production.py script")
    print("="*80)
    print("All tests run in dry-run mode for safety")
    print("="*80)

    tests = [
        {
            "name": "Help command",
            "cmd": ["python3", "scripts/deploy_to_production.py", "--help"],
            "description": "Display help information"
        },
        {
            "name": "Status check (dry-run)",
            "cmd": ["python3", "scripts/deploy_to_production.py", "--status", "--dry-run"],
            "description": "Check deployment status in dry-run mode"
        },
        {
            "name": "Backup only (dry-run)",
            "cmd": ["python3", "scripts/deploy_to_production.py", "--backup-only", "--dry-run"],
            "description": "Create backup in dry-run mode"
        },
        {
            "name": "Validate migration (dry-run)",
            "cmd": ["python3", "scripts/deploy_to_production.py", "--validate", "--migration-file", "test_migration.sql", "--dry-run"],
            "description": "Validate migration in dry-run mode (expected to fail - file doesn't exist)",
            "expected_fail": True
        },
        {
            "name": "Deploy migration (dry-run)",
            "cmd": ["python3", "scripts/deploy_to_production.py", "--deploy", "--migration-file", "test_migration.sql", "--dry-run", "--yes"],
            "description": "Deploy migration in dry-run mode (expected to fail - file doesn't exist)",
            "expected_fail": True
        },
        {
            "name": "Rollback (dry-run)",
            "cmd": ["python3", "scripts/deploy_to_production.py", "--rollback", "--dry-run", "--yes"],
            "description": "Rollback in dry-run mode"
        },
        {
            "name": "Auto workflow (dry-run)",
            "cmd": ["python3", "scripts/deploy_to_production.py", "--auto", "--migration-file", "test_migration.sql", "--dry-run", "--yes"],
            "description": "Execute automatic workflow in dry-run mode (expected to fail - file doesn't exist)",
            "expected_fail": True
        },
        {
            "name": "Rollback with specific backup (dry-run)",
            "cmd": ["python3", "scripts/deploy_to_production.py", "--rollback", "--backup-file", "db_backup_20260621_150000.sql.gz", "--dry-run", "--yes"],
            "description": "Rollback with specific backup in dry-run mode"
        },
        {
            "name": "Missing migration file validation",
            "cmd": ["python3", "scripts/deploy_to_production.py", "--auto", "--dry-run"],
            "description": "Validate error handling for missing migration file",
            "expected_fail": True
        },
        {
            "name": "Missing required arguments",
            "cmd": ["python3", "scripts/deploy_to_production.py", "--validate", "--dry-run"],
            "description": "Validate error handling for missing required arguments",
            "expected_fail": True
        }
    ]

    results = []
    for test in tests:
        expected_fail = test.get("expected_fail", False)
        success = run_command(test["cmd"], test["description"], expected_fail)
        results.append({
            "name": test["name"],
            "success": success
        })

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for r in results if r["success"])
    total = len(results)

    for result in results:
        status = "✓ PASS" if result["success"] else "✗ FAIL"
        print(f"{status}: {result['name']}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())