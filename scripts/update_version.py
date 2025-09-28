#!/usr/bin/env python3
"""
Version update script for semantic-release.

This script is called by semantic-release to update version information
across the project when a new release is created.
"""

import os
import re
import sys
from pathlib import Path


def update_version_file(new_version: str) -> None:
    """Update the __version__.py file with new version."""
    version_file = Path("src/diocesan_vitality/__version__.py")

    if not version_file.exists():
        print(f"❌ Version file not found: {version_file}")
        sys.exit(1)

    # Read current content
    content = version_file.read_text(encoding="utf-8")

    # Update version string
    updated_content = re.sub(r'__version__ = "[^"]*"', f'__version__ = "{new_version}"', content)

    # Update version_info tuple
    version_parts = new_version.split(".")
    version_tuple = f"({', '.join(version_parts)})"
    updated_content = re.sub(r"__version_info__ = \([^)]*\)", f"__version_info__ = {version_tuple}", updated_content)

    # Write updated content
    version_file.write_text(updated_content, encoding="utf-8")
    print(f"✅ Updated version to {new_version} in {version_file}")


def update_docker_tags(new_version: str) -> None:
    """Update Docker tags in version file."""
    version_file = Path("src/diocesan_vitality/__version__.py")
    content = version_file.read_text(encoding="utf-8")

    # Update docker tags with new version
    docker_tags_pattern = r'"docker_tags": \{[^}]*\}'
    new_docker_tags = f""""docker_tags": {{
        "backend": "tomatl/diocesan-vitality:backend-{new_version}",
        "frontend": "tomatl/diocesan-vitality:frontend-{new_version}",
        "pipeline": "tomatl/diocesan-vitality:pipeline-{new_version}",
    }}"""

    updated_content = re.sub(docker_tags_pattern, new_docker_tags, content, flags=re.DOTALL)

    # Update release notes URL
    updated_content = re.sub(
        r'"release_notes_url": "https://github\.com/tomknightatl/diocesan-vitality/releases/tag/v[^"]*"',
        f'"release_notes_url": "https://github.com/tomknightatl/diocesan-vitality/releases/tag/v{new_version}"',
        updated_content,
    )

    version_file.write_text(updated_content, encoding="utf-8")
    print(f"✅ Updated Docker tags and release URL for version {new_version}")


def validate_version(version: str) -> bool:
    """Validate semantic version format."""
    pattern = r"^\d+\.\d+\.\d+$"
    return bool(re.match(pattern, version))


def main() -> None:
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <new_version>")
        sys.exit(1)

    new_version = sys.argv[1]

    # Validate version format
    if not validate_version(new_version):
        print(f"❌ Invalid version format: {new_version}")
        print("Expected format: MAJOR.MINOR.PATCH (e.g., 1.2.3)")
        sys.exit(1)

    print(f"🔄 Updating project version to {new_version}")

    # Update version file
    update_version_file(new_version)

    # Update Docker tags
    update_docker_tags(new_version)

    # Create VERSION file for semantic-release
    version_file = Path("VERSION")
    version_file.write_text(new_version, encoding="utf-8")
    print(f"✅ Created VERSION file with {new_version}")

    print(f"🎉 Successfully updated all version references to {new_version}")


if __name__ == "__main__":
    main()
