#!/usr/bin/env python3
"""
Basic Pipeline Run Example

This example demonstrates how to run the Diocesan Vitality pipeline
with basic configuration for beginners.
"""

import logging
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def check_prerequisites():
    """Check if required environment variables are set."""
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "GENAI_API_KEY"]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error("Missing required environment variables: %s", missing_vars)
        logger.error("Please copy .env.example to .env and configure your API keys")
        return False

    return True


def run_basic_pipeline():
    """Run a basic pipeline with conservative settings."""
    logger.info("🚀 Starting Basic Pipeline Run Example")

    # Check prerequisites
    if not check_prerequisites():
        return False

    logger.info("✅ Prerequisites check passed")

    try:
        # Import the pipeline runner
        from src.diocesan_vitality.pipeline.runner import main as pipeline_main

        # Set conservative parameters for the example
        original_argv = sys.argv
        sys.argv = [
            "run_pipeline.py",
            "--max_parishes_per_diocese",
            "5",  # Process only 5 parishes per diocese
            "--skip_reporting",  # Skip reporting for faster execution
        ]

        logger.info("📊 Running pipeline with conservative settings:")
        logger.info("   - Max parishes per diocese: 5")
        logger.info("   - Skipping reporting phase")
        logger.info("   - This may take 5-10 minutes depending on your internet connection")

        # Run the pipeline
        pipeline_main()

        logger.info("✅ Pipeline completed successfully!")
        logger.info("📖 Next steps:")
        logger.info("   - Check your database for extracted data")
        logger.info("   - View the dashboard at http://localhost:3000")
        logger.info("   - Try running with more parishes: diocesan-vitality pipeline --max-parishes-per-diocese 25")

        return True

    except Exception as e:
        logger.error("❌ Pipeline failed: %s", e)
        logger.error("💡 Troubleshooting tips:")
        logger.error("   - Verify your .env file is configured correctly")
        logger.error("   - Check your internet connection")
        logger.error("   - Ensure Chrome/Chromium is installed")
        logger.error("   - Review the full error in the logs above")
        return False

    finally:
        # Restore original argv
        sys.argv = original_argv


def main():
    """Main function for the example."""
    logger.info("Diocesan Vitality - Basic Pipeline Run Example")
    logger.info("=" * 50)

    success = run_basic_pipeline()

    if success:
        logger.info("🎉 Example completed successfully!")
        return 0
    else:
        logger.error("❌ Example failed. Check the logs above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
