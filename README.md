# United States Conference of Catholic Bishops (USCCB) Data Project

**IMPORTANT: Before you begin, please set up your development environment by following the instructions in `setup-venv.md`. This includes creating a virtual environment, installing dependencies, and configuring your API keys.**

## Overview

This project is a comprehensive data collection and analysis system for U.S. Catholic dioceses and parishes. It employs advanced web scraping techniques, AI-powered content analysis, and automated data processing to build and maintain a detailed database of Catholic institutions across the United States. The system collects information from the official USCCB website and individual diocese websites, including diocese details, parish directories, and detailed parish information.

## Key Features

- **Automated Diocese Discovery**: Scrapes the official USCCB website to collect diocese information
- **AI-Powered Parish Directory Detection**: Uses Google's Gemini AI to intelligently identify parish directory pages
- **Advanced Web Scraping**: Employs Selenium with retry logic and pattern detection for robust data extraction
- **Multi-Platform Parish Extraction**: Supports various website platforms including SquareSpace, WordPress, eCatholic, and custom implementations
- **Interactive Parish Finder Support**: Specialized extractors for JavaScript-based parish finder interfaces
- **Cloud Database Integration**: Stores data in Supabase with automated upserts and conflict resolution
- **Comprehensive Logging**: Detailed extraction statistics and error tracking

## Project Architecture

### Core Components

- **Python Scripts**: Primary execution environment for data collection and processing
- **Supabase Database**: Cloud-hosted PostgreSQL database for scalable data storage
- **Selenium WebDriver**: Handles dynamic content and JavaScript-heavy websites
- **Google Gemini AI**: Provides intelligent content analysis and link classification
- **Pattern Detection System**: Automatically identifies website types and optimal extraction strategies

### Data Pipeline

1. **Diocese Collection** → Scrapes USCCB for basic diocese information
2. **Parish Directory Discovery** → AI-powered detection of parish listing pages
3. **Parish Extraction** → Advanced scraping with platform-specific extractors
4. **Data Enhancement** → Extracts detailed parish information including addresses, contact info, and schedules
5. **Quality Assurance** → Validation and deduplication of extracted data

## Project Files

### Core Data Collection Scripts

- **`Build_Dioceses_Database.py`**: Initial scraping of U.S. dioceses from the USCCB website. Populates the foundational `Dioceses` table with names, addresses, and official websites.

- **`Find_Parish_Directory.py` / `02_Find_Parish_Directories (older but working).py`**: AI-powered system that analyzes diocese websites to locate parish directory pages. Uses Google Gemini AI and custom search APIs with intelligent fallback mechanisms.

### Parish Extraction Modules

- **`parish_extraction_core.py`**: Core components for parish extraction including:
  - Data models and enums (DiocesePlatform, ParishListingType, ParishData)
  - Pattern detection system for website analysis
  - Base extractor classes and utilities
  - WebDriver setup functions
  - Database integration and Supabase utilities
  - Quality analysis functions

- **`parish_extractors.py`**: Specialized extractor implementations featuring:
  - Enhanced Diocese Card Extractor with detail page navigation
  - Parish Finder Extractor for eCatholic sites
  - Table Extractor for HTML-based listings
  - Interactive Map Extractor for JavaScript maps
  - Generic Extractor as intelligent fallback
  - Main processing function orchestrating extraction

- **`Extract_Parish_From_Diocese_Directory.py`**: Legacy monolithic script containing all parish extraction functionality (now split into the above two modules)

### Specialized Tools

- **`Find_Adoration_and_Reconciliation_information_for_a_Parish.py`**: Targeted extraction of specific liturgical information including Adoration and Reconciliation schedules from parish websites.

### Utility Modules

- **`db_utils.py`**: Database interaction utilities with connection management, summary generation, and table analysis functions.
- **`llm_utils.py`**: Google Gemini AI integration with retry logic and error handling for robust AI-powered content analysis.

## Database Schema

The project uses Supabase (PostgreSQL) with the following key tables:

### `Dioceses`
- **Primary Data**: Diocese names, addresses, official websites
- **Source**: USCCB official directory

### `DiocesesParishDirectory`
- **Links**: Diocese URLs to their parish directory pages
- **Metadata**: Detection method, success status, AI confidence scores

### `Parishes`
- **Comprehensive Data**: Names, addresses, contact information, websites
- **Enhanced Fields**: Geographic coordinates, clergy information, service schedules
- **Extraction Metadata**: Confidence scores, extraction methods, data quality indicators

## Technology Stack

### Core Technologies
- **Python 3.x**
- **Supabase** (PostgreSQL) for cloud database
- **Selenium WebDriver** with Chrome for dynamic content
- **BeautifulSoup4** for HTML parsing
- **Google Gemini AI** for content analysis

### Web Scraping Libraries
- **Selenium**: JavaScript-enabled browsing and interaction
- **Requests**: HTTP client for simple requests
- **BeautifulSoup**: HTML/XML parsing and navigation
- **Tenacity**: Retry logic with exponential backoff
- **WebDriver Manager**: Automatic ChromeDriver management

### Data Processing
- **Pandas**: Data manipulation and analysis
- **JSON**: Configuration and result serialization
- **Regular Expressions**: Text pattern matching and extraction

## Getting Started

### Prerequisites

1. **Install Python 3.x** (3.8 or higher recommended)

2. **Install Dependencies**:
```bash
pip install supabase selenium webdriver-manager google-generativeai beautifulsoup4 pandas tenacity requests python-dotenv googleapiclient
```

3. **Install Chrome** (if not already installed):
```bash
# For Ubuntu/Debian
sudo apt-get update
sudo apt-get install google-chrome-stable

# For macOS
brew install --cask google-chrome

# For Windows
# Download from https://www.google.com/chrome/
```

### Environment Setup

1. **Create Environment Variables File** (`.env`):
```bash
# Create a .env file in your project root
touch .env
```

2. **Add Your Credentials** to `.env`:
```env
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# Google AI Configuration
GENAI_API_KEY_USCCB=your_gemini_api_key

# Google Custom Search (for parish directory discovery)
SEARCH_API_KEY_USCCB=your_search_api_key
SEARCH_CX_USCCB=your_search_engine_id

# Optional: GitHub (if using version control)
GitHubUserforUSCCB=your_github_username
GitHubPATforUSCCB=your_github_personal_access_token
```

3. **Load Environment Variables** in Python:
```python
from dotenv import load_dotenv
import os

load_dotenv()

# Access variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
```

## Running the System

### Step 1: Build Diocese Database

```bash
python Build_Dioceses_Database.py
```

This script will:
- Scrape the USCCB website for all U.S. dioceses
- Extract names, addresses, and website URLs
- Store the data in the Supabase `Dioceses` table

**Note**: The script contains some Jupyter-specific code (like `get_ipython()`). You may need to comment out or remove these lines when running as a standalone Python script.

### Step 2: Find Parish Directories

```bash
python Find_Parish_Directory.py
# or use the older version if needed:
python "02_Find_Parish_Directories (older but working).py"
```

This script will:
- Fetch dioceses from the database that don't have parish directory URLs
- Use Selenium to load each diocese website
- Apply AI analysis to identify parish directory links
- Use Google Custom Search as a fallback method
- Store discovered URLs in the `DiocesesParishDirectory` table

**Configuration**: Before running, ensure you've set:
- `MAX_DIOCESES_TO_PROCESS` (line ~20 in the script) to control how many dioceses to process
- Mock/live API flags (`use_mock_genai_direct_page`, `use_mock_genai_snippet`, `use_mock_search_engine`) to `False` for live API calls

### Step 3: Extract Parish Information

#### Option A: Use the Modular Approach (Recommended)

```python
#!/usr/bin/env python3
"""
Main script to extract parish data from U.S. Catholic dioceses
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Import extraction modules
from parish_extraction_core import (
    setup_enhanced_driver,
    PatternDetector,
    enhanced_safe_upsert_to_supabase,
    analyze_parish_finder_quality
)
from parish_extractors import (
    ensure_chrome_installed,
    process_diocese_with_detailed_extraction
)

# Load environment variables
load_dotenv()

def main():
    # Configuration
    MAX_DIOCESES = 5  # Adjust as needed
    
    # Ensure Chrome is installed
    if not ensure_chrome_installed():
        print("Chrome installation failed. Please install Chrome manually.")
        return
    
    # Initialize Supabase
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )
    
    # Get dioceses with parish directory URLs
    response = supabase.table('DiocesesParishDirectory').select(
        'diocese_url, parish_directory_url'
    ).not_.is_('parish_directory_url', 'null').limit(MAX_DIOCESES).execute()
    
    dioceses = response.data if response.data else []
    
    # Get diocese names
    diocese_urls = [d['diocese_url'] for d in dioceses]
    names_response = supabase.table('Dioceses').select(
        'Website, Name'
    ).in_('Website', diocese_urls).execute()
    
    url_to_name = {item['Website']: item['Name'] for item in names_response.data}
    
    # Process each diocese
    driver = setup_enhanced_driver()
    
    try:
        for diocese in dioceses:
            diocese_info = {
                'name': url_to_name.get(diocese['diocese_url'], 'Unknown'),
                'url': diocese['diocese_url'],
                'parish_directory_url': diocese['parish_directory_url']
            }
            
            print(f"Processing {diocese_info['name']}...")
            result = process_diocese_with_detailed_extraction(diocese_info, driver)
            
            # Save parishes to database
            if result['parishes_found']:
                enhanced_safe_upsert_to_supabase(
                    result['parishes_found'],
                    diocese_info['name'],
                    diocese_info['url'],
                    diocese_info['parish_directory_url'],
                    supabase
                )
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
```

Save this as `extract_parishes.py` and run:
```bash
python extract_parishes.py
```

#### Option B: Use the Legacy Script

```bash
python Extract_Parish_From_Diocese_Directory.py
```

**Note**: This script is very long and contains debug functions. You'll need to:
1. Comment out the debug function calls at the end
2. Remove or comment out Jupyter-specific code (like `!pip install` commands)
3. Ensure Chrome is installed before running

### Step 4: Extract Liturgical Information (Optional)

```bash
python Find_Adoration_and_Reconciliation_information_for_a_Parish.py
```

This script will:
- Scrape specified parish websites for Adoration and Reconciliation schedules
- Store the information in a local SQLite database

## Script Modifications for Standalone Execution

When converting from Jupyter notebooks to standalone Python scripts, make these changes:

### 1. Remove Jupyter-Specific Commands
Replace or remove:
- `get_ipython().system('command')` → Use `subprocess.run(['command'])`
- `!pip install package` → Run separately or use `subprocess.run(['pip', 'install', 'package'])`
- `from google.colab import userdata` → Use `os.getenv()` with python-dotenv

### 2. Handle Chrome Installation
For non-Colab environments, ensure Chrome is installed system-wide or modify the `ensure_chrome_installed()` function for your OS.

### 3. Environment Variables
Replace Colab secrets with environment variables:
```python
# Instead of:
from google.colab import userdata
SUPABASE_URL = userdata.get('SUPABASE_URL')

# Use:
from dotenv import load_dotenv
import os
load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
```

### 4. Create a Main Function
Wrap execution code in a main function:
```python
def main():
    # Your execution code here
    pass

if __name__ == "__main__":
    main()
```

## Automation and Scheduling

### Using Cron (Linux/macOS)
```bash
# Add to crontab for daily execution at 2 AM
0 2 * * * /usr/bin/python3 /path/to/extract_parishes.py >> /path/to/logs/extraction.log 2>&1
```

### Using Task Scheduler (Windows)
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (daily, weekly, etc.)
4. Set action to run Python script

### Using Python Scheduler
```python
import schedule
import time

def run_extraction():
    exec(open('extract_parishes.py').read())

schedule.every().day.at("02:00").do(run_extraction)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Troubleshooting

### Common Issues and Solutions

1. **Import Errors**:
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python path and virtual environment activation

2. **Chrome/ChromeDriver Issues**:
   - Ensure Chrome is installed
   - ChromeDriver should auto-download via webdriver-manager
   - For manual installation: Download from [ChromeDriver](https://chromedriver.chromium.org/)

3. **Supabase Connection Issues**:
   ```python
   # Test connection
   from supabase import create_client
   client = create_client(url, key)
   response = client.table('Dioceses').select('*').limit(1).execute()
   print(response)
   ```

4. **API Key Issues**:
   - Verify `.env` file is in the project root
   - Check environment variables are loaded: `print(os.getenv('SUPABASE_URL'))`
   - Ensure API keys have correct permissions

5. **Memory Issues**:
   - Process dioceses in smaller batches
   - Add garbage collection: `import gc; gc.collect()`

## Data Coverage

As of the latest runs, the system has successfully processed:
- **190+ U.S. Catholic Dioceses**
- **Thousands of Parish Records** with detailed information
- **High Success Rates**: 85-95% successful parish directory detection
- **Rich Data Fields**: Including addresses, coordinates, contact info, and schedules

## Contributing

The project is designed for extensibility:
- **New Extractors**: Add support for additional website platforms in `parish_extractors.py`
- **Enhanced AI**: Improve content analysis in `llm_utils.py`
- **Additional Data Points**: Extend `ParishData` model in `parish_extraction_core.py`
- **Quality Improvements**: Enhance validation in the pattern detection system

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- United States Conference of Catholic Bishops for providing publicly accessible diocese information
- Google AI for Gemini API access enabling intelligent content analysis
- Supabase for reliable cloud database infrastructure
- The open-source community for the excellent web scraping and data processing libraries