"""
Version information for Diocesan Vitality.

This module provides centralized version management for the entire project.
Version is automatically updated by semantic-release during CI/CD.
"""

import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

# Version information - updated automatically by semantic-release
__version__ = "2.0.0"
__version_info__ = tuple(int(i) for i in __version__.split("."))

# Build metadata - populated during CI/CD build process
BUILD_INFO = {
    "version": __version__,
    "version_info": __version_info__,
    "git_commit": os.getenv("GITHUB_SHA", "unknown"),
    "git_branch": os.getenv("GITHUB_REF_NAME", "unknown"),
    "build_date": os.getenv("BUILD_DATE", datetime.utcnow().isoformat()),
    "build_number": os.getenv("GITHUB_RUN_NUMBER", "unknown"),
    "docker_tags": {
        "backend": f"tomatl/diocesan-vitality:backend-{__version__}",
        "frontend": f"tomatl/diocesan-vitality:frontend-{__version__}",
        "pipeline": f"tomatl/diocesan-vitality:pipeline-{__version__}",
    },
    "registry_url": "https://hub.docker.com/r/tomatl/diocesan-vitality",
    "release_notes_url": f"https://github.com/tomknightatl/diocesan-vitality/releases/tag/v{__version__}",
}


def get_version(include_build: bool = False) -> str:
    """
    Get version string.

    Args:
        include_build: Include build metadata in version string

    Returns:
        Version string
    """
    if include_build and BUILD_INFO.get("git_commit") != "unknown":
        commit_short = BUILD_INFO["git_commit"][:7]
        return f"{__version__}+{commit_short}"
    return __version__


def get_version_info() -> Tuple[int, ...]:
    """
    Get version info tuple.

    Returns:
        Version info tuple (major, minor, patch)
    """
    return __version_info__


def get_build_info() -> Dict[str, Any]:
    """
    Get complete build information.

    Returns:
        Dictionary containing all build metadata
    """
    return BUILD_INFO.copy()


def get_docker_tags() -> Dict[str, str]:
    """
    Get Docker image tags for current version.

    Returns:
        Dictionary mapping component names to Docker tags
    """
    return BUILD_INFO["docker_tags"].copy()


def get_release_info() -> Dict[str, str]:
    """
    Get release information.

    Returns:
        Dictionary containing release metadata
    """
    return {
        "version": __version__,
        "release_date": BUILD_INFO.get("build_date", "unknown"),
        "git_commit": BUILD_INFO.get("git_commit", "unknown"),
        "git_branch": BUILD_INFO.get("git_branch", "unknown"),
        "release_url": BUILD_INFO["release_notes_url"],
        "registry_url": BUILD_INFO["registry_url"],
    }


def is_development_version() -> bool:
    """
    Check if this is a development version.

    Returns:
        True if version contains development indicators
    """
    dev_indicators = ["dev", "alpha", "beta", "rc", "pre"]
    return any(indicator in __version__.lower() for indicator in dev_indicators)


def is_stable_version() -> bool:
    """
    Check if this is a stable release version.

    Returns:
        True if version is stable (no dev indicators)
    """
    return not is_development_version()


# Version compatibility checks
def requires_version(min_version: str) -> bool:
    """
    Check if current version meets minimum requirement.

    Args:
        min_version: Minimum required version string

    Returns:
        True if current version >= min_version
    """
    min_version_info = tuple(int(i) for i in min_version.split("."))
    return __version_info__ >= min_version_info


def supports_feature(feature_version: str) -> bool:
    """
    Check if current version supports a feature introduced in specific version.

    Args:
        feature_version: Version when feature was introduced

    Returns:
        True if current version supports the feature
    """
    return requires_version(feature_version)


# CLI version display
def print_version_info(verbose: bool = False) -> None:
    """
    Print version information to stdout.

    Args:
        verbose: Include detailed build information
    """
    print(f"Diocesan Vitality v{__version__}")

    if verbose:
        info = get_build_info()
        print(f"Build Date: {info['build_date']}")
        print(f"Git Commit: {info['git_commit']}")
        print(f"Git Branch: {info['git_branch']}")
        print(f"Build Number: {info['build_number']}")
        print("\nDocker Images:")
        for component, tag in info["docker_tags"].items():
            print(f"  {component.capitalize()}: {tag}")
        print(f"\nRelease Notes: {info['release_notes_url']}")


# Validate version format
def _validate_version(version: str) -> bool:
    """Validate semantic version format."""
    try:
        parts = version.split(".")
        if len(parts) != 3:
            return False
        for part in parts:
            int(part)
        return True
    except ValueError:
        return False


# Ensure version is valid
if not _validate_version(__version__):
    raise ValueError(f"Invalid version format: {__version__}")

# Export main version info
__all__ = [
    "__version__",
    "__version_info__",
    "BUILD_INFO",
    "get_version",
    "get_version_info",
    "get_build_info",
    "get_docker_tags",
    "get_release_info",
    "is_development_version",
    "is_stable_version",
    "requires_version",
    "supports_feature",
    "print_version_info",
]
