#!/usr/bin/env python3
"""
Main CLI entry point for Diocesan Vitality.
"""

import argparse
import sys
from typing import List, Optional

from ..__version__ import __version__, print_version_info
from ..monitoring.dashboard import main as monitor_main
from ..pipeline.extract import main as extract_main
from ..pipeline.runner import main as pipeline_main


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog="diocesan-vitality",
        description="Comprehensive data collection and analysis system for U.S. Catholic dioceses and parishes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  diocesan-vitality --version                    Show version information
  diocesan-vitality pipeline --help              Show pipeline options
  diocesan-vitality extract --diocese-id 123     Extract specific diocese
  diocesan-vitality monitor                      Start monitoring dashboard

For more information, visit: https://diocesanvitality.org/docs
        """,
    )

    parser.add_argument("--version", "-v", action="store_true", help="Show version information")

    parser.add_argument("--verbose", action="store_true", help="Show detailed version information")

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands", metavar="COMMAND")

    # Pipeline command
    pipeline_parser = subparsers.add_parser(
        "pipeline", help="Run the data extraction pipeline", description="Execute the main data collection pipeline"
    )
    pipeline_parser.add_argument(
        "--max-parishes-per-diocese", type=int, default=50, help="Maximum parishes to process per diocese (default: 50)"
    )
    pipeline_parser.add_argument("--diocese-id", type=int, help="Process specific diocese ID only")
    pipeline_parser.add_argument("--skip-dioceses", action="store_true", help="Skip diocese extraction phase")
    pipeline_parser.add_argument("--skip-parishes", action="store_true", help="Skip parish extraction phase")
    pipeline_parser.add_argument("--skip-schedules", action="store_true", help="Skip schedule extraction phase")

    # Extract command
    extract_parser = subparsers.add_parser(
        "extract", help="Run specific extraction tasks", description="Execute specific data extraction operations"
    )
    extract_parser.add_argument("--diocese-id", type=int, required=True, help="Diocese ID to extract")
    extract_parser.add_argument("--pool-size", type=int, default=6, help="Number of concurrent workers (default: 6)")
    extract_parser.add_argument("--batch-size", type=int, default=12, help="Batch size for processing (default: 12)")

    # Monitor command
    monitor_parser = subparsers.add_parser(
        "monitor", help="Start monitoring dashboard", description="Launch the monitoring and observability dashboard"
    )
    monitor_parser.add_argument("--port", type=int, default=8000, help="Port to run dashboard on (default: 8000)")
    monitor_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")

    # Quickstart command
    quickstart_parser = subparsers.add_parser(
        "quickstart", help="Quick setup and test run", description="Perform quick setup and run a test extraction"
    )

    return parser


def handle_version(args: argparse.Namespace) -> None:
    """Handle version command."""
    if args.verbose:
        print_version_info(verbose=True)
    else:
        print(f"Diocesan Vitality v{__version__}")


def handle_pipeline(args: argparse.Namespace) -> None:
    """Handle pipeline command."""
    # Convert argparse namespace to argv format expected by pipeline_main
    pipeline_args = ["run_pipeline.py"]

    if args.max_parishes_per_diocese:
        pipeline_args.extend(["--max_parishes_per_diocese", str(args.max_parishes_per_diocese)])

    if args.diocese_id:
        pipeline_args.extend(["--diocese_id", str(args.diocese_id)])

    if args.skip_dioceses:
        pipeline_args.append("--skip_dioceses")

    if args.skip_parishes:
        pipeline_args.append("--skip_parishes")

    if args.skip_schedules:
        pipeline_args.append("--skip_schedules")

    # Replace sys.argv temporarily
    original_argv = sys.argv
    try:
        sys.argv = pipeline_args
        pipeline_main()
    finally:
        sys.argv = original_argv


def handle_extract(args: argparse.Namespace) -> None:
    """Handle extract command."""
    # Convert argparse namespace to argv format expected by extract_main
    extract_args = ["async_extract_parishes.py"]
    extract_args.extend(["--diocese_id", str(args.diocese_id)])
    extract_args.extend(["--pool_size", str(args.pool_size)])
    extract_args.extend(["--batch_size", str(args.batch_size)])

    # Replace sys.argv temporarily
    original_argv = sys.argv
    try:
        sys.argv = extract_args
        extract_main()
    finally:
        sys.argv = original_argv


def handle_monitor(args: argparse.Namespace) -> None:
    """Handle monitor command."""
    # Convert argparse namespace to format expected by monitor_main
    monitor_args = ["monitor.py"]
    monitor_args.extend(["--port", str(args.port)])
    monitor_args.extend(["--host", args.host])

    # Replace sys.argv temporarily
    original_argv = sys.argv
    try:
        sys.argv = monitor_args
        monitor_main()
    finally:
        sys.argv = original_argv


def handle_quickstart(args: argparse.Namespace) -> None:
    """Handle quickstart command."""
    print("🚀 Diocesan Vitality Quickstart")
    print("=" * 50)
    print()
    print("This will run a quick test extraction to verify your setup.")
    print()

    # Run a small test pipeline
    test_args = argparse.Namespace(
        max_parishes_per_diocese=5,
        diocese_id=None,
        skip_dioceses=False,
        skip_parishes=False,
        skip_schedules=True,  # Skip schedules for quickstart
    )

    print("Starting test pipeline with 5 parishes per diocese...")
    print("Skipping schedule extraction for faster testing.")
    print()

    handle_pipeline(test_args)

    print()
    print("✅ Quickstart complete!")
    print("📖 Next steps:")
    print("   - Check the dashboard: http://localhost:3000")
    print("   - Run full pipeline: diocesan-vitality pipeline")
    print("   - View documentation: https://diocesanvitality.org/docs")


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Handle version first
    if args.version:
        handle_version(args)
        return 0

    # Handle commands
    if args.command == "pipeline":
        handle_pipeline(args)
    elif args.command == "extract":
        handle_extract(args)
    elif args.command == "monitor":
        handle_monitor(args)
    elif args.command == "quickstart":
        handle_quickstart(args)
    else:
        # No command provided, show help
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
