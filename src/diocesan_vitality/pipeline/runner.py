#!/usr/bin/env python3
"""
Pipeline runner module.

This module provides the main pipeline execution functionality,
serving as a wrapper around the existing run_pipeline.py script.
"""

import os
import sys

# Add the project root to the path so we can import the existing scripts
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)


def main():
    """Main pipeline runner entry point."""
    # Import the existing run_pipeline script
    try:
        import run_pipeline

        # Execute the main function from the existing script
        if hasattr(run_pipeline, "main"):
            run_pipeline.main()
        else:
            # If no main function, just run the script
            exec(open(os.path.join(project_root, "run_pipeline.py")).read())
    except ImportError as e:
        print(f"Error importing run_pipeline: {e}")
        print("Make sure you're running from the project root directory.")
        sys.exit(1)


if __name__ == "__main__":
    main()
