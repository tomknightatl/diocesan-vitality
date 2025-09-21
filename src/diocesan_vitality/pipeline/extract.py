#!/usr/bin/env python3
"""
Extraction module.

This module provides the async parish extraction functionality,
serving as a wrapper around the existing async_extract_parishes.py script.
"""

import os
import sys

# Add the project root to the path so we can import the existing scripts
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)


def main():
    """Main extraction entry point."""
    # Import the existing async_extract_parishes script
    try:
        import async_extract_parishes

        # Execute the main function from the existing script
        if hasattr(async_extract_parishes, "main"):
            async_extract_parishes.main()
        else:
            # If no main function, just run the script
            exec(open(os.path.join(project_root, "async_extract_parishes.py")).read())
    except ImportError as e:
        print(f"Error importing async_extract_parishes: {e}")
        print("Make sure you're running from the project root directory.")
        sys.exit(1)


if __name__ == "__main__":
    main()
