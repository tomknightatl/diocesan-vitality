# Python Scripts Documentation

This document provides an overview of the Python scripts in the root directory of the repository, categorized by their function. It also includes recommendations for code cleanup and organization.

## Alphabetical List of Scripts

- `async_extract_parishes.py`
- `config.py`
- `extract_dioceses.py`
- `extract_schedule_respectful.py`
- `find_parishes.py`
- `parish_extraction_core.py`
- `parish_extractors.py`
- `report_statistics.py`
- `respectful_automation.py`
- `run_pipeline.py`

## Scripts by Logical Category

### Core Pipeline & Execution

- **`run_pipeline.py`**: The main entry point for the entire data extraction pipeline. It orchestrates the execution of the different extraction steps.
- **`extract_dioceses.py`**: Step 1 of the pipeline. Extracts diocese information from the main conference website.
- **`find_parishes.py`**: Step 2 of the pipeline. Analyzes diocese websites to find the specific URL for the parish directory.
- **`async_extract_parishes.py`**: Step 3 of the pipeline. Asynchronously extracts detailed parish information from the parish directory pages.
- **`extract_schedule_respectful.py`**: Step 4 of the pipeline. Extracts Mass, confession, and adoration schedules from parish websites using respectful automation practices.

### Extraction Logic & Core Components

- **`parish_extraction_core.py`**: Contains the core data models (e.g., `ParishData`), enums, and fundamental utilities used across the parish extraction process.
- **`parish_extractors.py`**: A key module containing the various extractor classes (e.g., `TableExtractor`, `EnhancedDiocesesCardExtractor`, `ParishFinderExtractor`) responsible for parsing different website layouts.
- **`respectful_automation.py`**: Implements respectful web scraping practices, including `robots.txt` compliance, rate limiting, and bot blocking detection.

### Configuration

- **`config.py`**: Manages environment variables and central configuration for the application, such as API keys and default settings.

### Reporting

- **`report_statistics.py`**: Generates statistics and time-series plots from the data in the Supabase database, outputting them as images for the frontend.

## Recommended Changes

Based on the analysis of the current scripts in the root directory, there are no immediate recommendations for deletion or merging. The existing scripts are well-structured and each serves a clear purpose within the data extraction pipeline.
