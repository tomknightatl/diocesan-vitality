#!/usr/bin/env python3
"""
Setup script for Diocesan Vitality.

A comprehensive data collection and analysis system for U.S. Catholic dioceses and parishes.
"""

import os
from setuptools import setup, find_packages

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Read requirements
def read_requirements(filename):
    """Read requirements from file."""
    requirements_path = os.path.join(this_directory, filename)
    with open(requirements_path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Version management - use centralized version
def get_version():
    """Get version from centralized version file."""
    version_file = os.path.join(this_directory, "src", "diocesan_vitality", "__version__.py")

    # Read version from __version__.py
    version_vars = {}
    with open(version_file, encoding="utf-8") as f:
        exec(f.read(), version_vars)

    return version_vars.get("__version__", "0.9.0")

# Main requirements
install_requires = read_requirements("requirements.txt")

# Development requirements
extras_require = {
    "dev": [
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "pytest-asyncio>=0.21.0",
        "black>=23.0.0",
        "flake8>=6.0.0",
        "mypy>=1.0.0",
        "isort>=5.12.0",
        "pre-commit>=3.0.0",
        "bandit>=1.7.0",
        "safety>=2.3.0",
        "pip-audit>=2.6.0",
    ],
    "docs": [
        "sphinx>=6.0.0",
        "sphinx-rtd-theme>=1.3.0",
        "myst-parser>=2.0.0",
        "sphinx-autodoc-typehints>=1.24.0",
    ],
    "monitoring": [
        "prometheus-client>=0.17.0",
        "grafana-api>=1.0.3",
    ],
    "ml": [
        "scikit-learn>=1.3.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
    ],
}

# All extras
extras_require["all"] = list(set(sum(extras_require.values(), [])))

setup(
    name="diocesan-vitality",
    version=get_version(),
    author="Tom Knight",
    author_email="tom@diocesanvitality.org",
    description="Comprehensive data collection and analysis system for U.S. Catholic dioceses and parishes",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tomknightatl/diocesan-vitality",
    project_urls={
        "Homepage": "https://diocesanvitality.org",
        "Documentation": "https://diocesanvitality.org/docs",
        "Repository": "https://github.com/tomknightatl/diocesan-vitality",
        "Bug Tracker": "https://github.com/tomknightatl/diocesan-vitality/issues",
        "Changelog": "https://github.com/tomknightatl/diocesan-vitality/blob/main/CHANGELOG.md",
        "Live System": "https://diocesanvitality.org/dashboard",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "diocesan_vitality": [
            "extractors/*.py",
            "core/*.py",
            "config/*.yaml",
            "config/*.json",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Religion",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Database",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Environment :: Web Environment",
        "Framework :: AsyncIO",
        "Natural Language :: English",
    ],
    keywords=[
        "catholic",
        "diocese",
        "parish",
        "data-collection",
        "web-scraping",
        "religious-institutions",
        "research",
        "automation",
        "kubernetes",
        "ai",
        "machine-learning",
        "dashboard",
        "monitoring",
    ],
    python_requires=">=3.11",
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "diocesan-vitality=diocesan_vitality.cli:main",
            "dv=diocesan_vitality.cli:main",
            "dv-pipeline=diocesan_vitality.pipeline.runner:main",
            "dv-extract=diocesan_vitality.pipeline.extract:main",
            "dv-monitor=diocesan_vitality.monitoring.dashboard:main",
        ],
    },
    zip_safe=False,
    license="MIT",
    platforms=["any"],
    # Additional metadata
    maintainer="Tom Knight",
    maintainer_email="tom@diocesanvitality.org",
    download_url="https://github.com/tomknightatl/diocesan-vitality/archive/refs/heads/main.zip",
    # PyPI specific
    obsoletes_dist=[],
    provides_dist=["diocesan-vitality"],
    # Setuptools specific options
    options={
        "bdist_wheel": {
            "universal": False,  # Not universal because we use Python 3.11+ features
        },
    },
)

# Post-installation message
print("""
🎉 Diocesan Vitality installed successfully!

📚 Getting Started:
   diocesan-vitality --help
   dv quickstart

📖 Documentation:
   https://diocesanvitality.org/docs

🚀 Live System:
   https://diocesanvitality.org/dashboard

🔧 Configuration:
   Copy .env.example to .env and configure your API keys

🆘 Support:
   https://github.com/tomknightatl/diocesan-vitality/issues
""")