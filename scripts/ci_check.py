#!/usr/bin/env python3
"""
CI Check Script - Run the exact same checks as Simple CI workflow
This script replicates the Simple CI pipeline locally for fast feedback
"""

import subprocess
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(description, command, check=True):
    """Run a command and handle output"""
    print(f"\n🔍 {description}")
    print(f"Running: {command}")
    print("-" * 50)

    try:
        result = subprocess.run(command, shell=True, cwd=project_root, capture_output=False, check=check)

        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED with error: {e}")
        return False


def main():
    """Run all CI checks locally"""
    print("🚀 CI Check Script - Simple CI Pipeline Replica")
    print("=" * 60)
    print("This runs the EXACT same checks as the Simple CI workflow")
    print("=" * 60)

    # Track results
    results = []

    # 1. Black formatting check (exactly like CI)
    results.append(run_command("Black formatting check", "black --check --diff ."))

    # 2. Import sorting check (exactly like CI)
    results.append(run_command("Import sorting check", "isort --check-only --diff ."))

    # 3. Flake8 linting (exactly like CI)
    results.append(run_command("Flake8 linting", "flake8 ."))

    # Summary
    print("\n" + "=" * 60)
    print("📋 CI CHECK SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    for i, (desc, result) in enumerate(zip(["Black formatting", "Import sorting", "Flake8 linting"], results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {desc}: {status}")

    if passed == total:
        print(f"\n🎉 All {total} checks PASSED! Your code will pass Simple CI.")
        print("💡 You can now commit with confidence!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} of {total} checks FAILED.")
        print("🔧 Fix the issues above before committing to pass Simple CI.")
        print("\n💡 Quick fixes:")
        print("   - Run: black . && isort . && flake8 .")
        print("   - Then re-run this script")
        return 1


if __name__ == "__main__":
    # Ensure we're in a virtual environment or have the required tools
    missing_tools = []
    for tool in ["black", "isort", "flake8"]:
        if subprocess.run(f"which {tool}", shell=True, capture_output=True).returncode != 0:
            missing_tools.append(tool)

    if missing_tools:
        print(f"❌ Missing required tools: {', '.join(missing_tools)}")
        print("💡 Install with: pip install black isort flake8")
        sys.exit(1)

    sys.exit(main())
