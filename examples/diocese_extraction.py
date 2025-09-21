#!/usr/bin/env python3
"""
Diocese-Specific Extraction Example

This example demonstrates how to extract data for a specific diocese
using the async extraction capabilities.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_diocese_info(diocese_id: int) -> dict:
    """Get information about a specific diocese."""
    # This would typically query the database
    # For the example, we'll return sample data
    sample_dioceses = {
        1: {"name": "Archdiocese of Atlanta", "state": "Georgia"},
        2: {"name": "Diocese of Savannah", "state": "Georgia"},
        123: {"name": "Example Diocese", "state": "Example State"}
    }

    return sample_dioceses.get(diocese_id, {
        "name": f"Diocese {diocese_id}",
        "state": "Unknown"
    })


def extract_diocese(diocese_id: int, pool_size: int = 6, batch_size: int = 12):
    """Extract data for a specific diocese."""
    logger.info("🏛️ Diocese-Specific Extraction Example")
    logger.info("=" * 50)

    # Get diocese information
    diocese_info = get_diocese_info(diocese_id)
    logger.info(f"📍 Target Diocese: {diocese_info['name']} ({diocese_info['state']})")
    logger.info(f"🔧 Configuration:")
    logger.info(f"   - Diocese ID: {diocese_id}")
    logger.info(f"   - Pool Size: {pool_size} concurrent workers")
    logger.info(f"   - Batch Size: {batch_size} parishes per batch")

    try:
        # Import the async extractor
        from src.diocesan_vitality.pipeline.extract import main as extract_main

        # Set up parameters for async extraction
        original_argv = sys.argv
        sys.argv = [
            'async_extract_parishes.py',
            '--diocese_id', str(diocese_id),
            '--pool_size', str(pool_size),
            '--batch_size', str(batch_size)
        ]

        logger.info("🚀 Starting async extraction...")
        logger.info("💡 This process will:")
        logger.info("   1. Find all parishes in the diocese")
        logger.info("   2. Extract detailed information for each parish")
        logger.info("   3. Save results to the database")
        logger.info("   4. Generate extraction statistics")

        # Run the extraction
        extract_main()

        logger.info("✅ Diocese extraction completed successfully!")
        logger.info("📊 Check your database for the extracted parish data")

        return True

    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        logger.error("💡 Common issues:")
        logger.error("   - Diocese ID may not exist in the database")
        logger.error("   - Network connectivity issues")
        logger.error("   - Rate limiting from target websites")
        return False

    finally:
        # Restore original argv
        sys.argv = original_argv


def main():
    """Main function for the example."""
    parser = argparse.ArgumentParser(
        description="Extract data for a specific diocese",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python diocese_extraction.py --diocese-id 1                    # Extract Archdiocese of Atlanta
  python diocese_extraction.py --diocese-id 2 --pool-size 4      # Extract with 4 workers
  python diocese_extraction.py --diocese-id 123 --batch-size 8   # Extract with smaller batches

Available Diocese IDs (examples):
  1   - Archdiocese of Atlanta, Georgia
  2   - Diocese of Savannah, Georgia
  123 - Example Diocese for testing

Note: Check your database for the complete list of available dioceses.
        """
    )

    parser.add_argument(
        "--diocese-id",
        type=int,
        required=True,
        help="Diocese ID to extract (required)"
    )

    parser.add_argument(
        "--pool-size",
        type=int,
        default=6,
        help="Number of concurrent workers (default: 6)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=12,
        help="Number of parishes to process per batch (default: 12)"
    )

    args = parser.parse_args()

    # Validate pool size
    if args.pool_size < 1 or args.pool_size > 20:
        logger.error("Pool size must be between 1 and 20")
        return 1

    # Validate batch size
    if args.batch_size < 1 or args.batch_size > 50:
        logger.error("Batch size must be between 1 and 50")
        return 1

    # Check prerequisites
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'GENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please copy .env.example to .env and configure your API keys")
        return 1

    # Run the extraction
    success = extract_diocese(args.diocese_id, args.pool_size, args.batch_size)

    if success:
        logger.info("🎉 Diocese extraction example completed successfully!")
        return 0
    else:
        logger.error("❌ Diocese extraction example failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())