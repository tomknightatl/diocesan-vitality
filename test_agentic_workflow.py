#!/usr/bin/env python3
"""
Test script for agentic workflow
"""

import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_workflow():
    """Test the agentic workflow with a sample parish"""
    try:
        from pipeline.agentic_schedule_extractor import scrape_parish_data_agentic

        # Test with a sample parish
        result = scrape_parish_data_agentic(
            url="https://example-parish.org", parish_id=1, max_iterations=5
        )

        logger.info(f"Test result: {result}")
        print("✅ Workflow test completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Workflow test failed: {e}")
        print(f"❌ Workflow test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_workflow()
    sys.exit(0 if success else 1)
