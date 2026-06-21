#!/usr/bin/env python3
"""
Test script for apply_schema_change.py

This script validates the functionality of the schema change management script
by testing various workflows and edge cases.

Usage:
    python scripts/test_apply_schema_change.py
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
            timeout=30
        )

        print(f"Exit Code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")

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
    print("Testing apply_schema_change.py script")
    print("="*80)

    tests = [
        {
            "name": "Help command",
            "cmd": ["python3", "scripts/apply_schema_change.py", "--help"],
            "description": "Display help information"
        },
        {
            "name": "Status check (dry-run)",
            "cmd": ["python3", "scripts/apply_schema_change.py", "--status", "--dry-run"],
            "description": "Check migration status in dry-run mode"
        },
        {
            "name": "Schema validation (dry-run)",
            "cmd": ["python3", "scripts/apply_schema_change.py", "--validate", "--dry-run"],
            "description": "Validate schema in dry-run mode"
        },
        {
            "name": "Generate migration (dry-run)",
            "cmd": ["python3", "scripts/apply_schema_change.py", "--generate", "--name", "test_migration", "--dry-run"],
            "description": "Generate migration diff in dry-run mode"
        },
        {
            "name": "Apply migration (dry-run)",
            "cmd": ["python3", "scripts/apply_schema_change.py", "--apply", "--dry-run", "--yes"],
            "description": "Apply migration in dry-run mode"
        },
        {
            "name": "Rollback migration (dry-run)",
            "cmd": ["python3", "scripts/apply_schema_change.py", "--rollback", "--dry-run", "--yes"],
            "description": "Rollback migration in dry-run mode"
        },
        {
            "name": "Auto workflow (dry-run)",
            "cmd": ["python3", "scripts/apply_schema_change.py", "--auto", "--name", "test_auto", "--dry-run", "--yes", "--skip-validation"],
            "description": "Execute automatic workflow in dry-run mode"
        },
        {
            "name": "Generate with migra engine (dry-run)",
            "cmd": ["python3", "scripts/apply_schema_change.py", "--generate", "--name", "test_migra", "--use-migra", "--dry-run"],
            "description": "Generate migration using migra engine in dry-run mode"
        },
        {
            "name": "Validate custom schema (dry-run)",
            "cmd": ["python3", "scripts/apply_schema_change.py", "--validate", "--schema", "auth", "--dry-run"],
            "description": "Validate auth schema in dry-run mode"
        },
        {
            "name": "Rollback validation (dry-run)",
            "cmd": ["python3", "scripts/apply_schema_change.py", "--rollback", "--rollback-count", "2", "--dry-run", "--yes"],
            "description": "Validate rollback error handling (expected to fail - only 1 migration exists)",
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