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

- **`extract_dioceses.py`**: Initial scraping of U.S. dioceses from the USCCB website. Populates the foundational `Dioceses` table with names, addresses, and official websites.

- **`find_parishes.py` / `02_Find_Parish_Directories (older but working).py`**: AI-powered system that analyzes diocese websites to locate parish directory pages. Uses Google Gemini AI and custom search APIs with intelligent fallback mechanisms.

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

2. **Install Google Chrome**

   The project uses Selenium for web scraping, which requires a Chrome browser and ChromeDriver. While `webdriver-manager` will attempt to download the correct ChromeDriver automatically, it does *not* install Chrome itself.

   **For Linux (Debian/Ubuntu-based systems):**

   ```bash
   # Download the Google Chrome signing key and save it to /usr/share/keyrings/
   wget -O- https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg

   # Add the Google Chrome repository to your sources list, referencing the new keyring file
   echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list > /dev/null

   # Update your package list
   sudo apt update

   # Install Google Chrome
   sudo apt install google-chrome-stable
   ```

   **For other operating systems:**

   Please download and install Chrome from the official website: [https://www.google.com/chrome/](https://www.google.com/chrome/)

### Environment Setup

This project uses a virtual environment to manage dependencies and environment variables to securely store API keys.

3.  **Create and Activate a Virtual Environment**

    It is highly recommended to use a virtual environment to manage project dependencies.

    ```bash
    # Navigate to the root of your project directory
    cd /home/tomk/USCCB

    # Create a virtual environment named 'venv'
    python3 -m venv venv

    # Activate the virtual environment
    # On macOS/Linux:
    source venv/bin/activate

    # On Windows:
    # .\venv\Scripts\activate
    ```

    Your command prompt should now show `(venv)` indicating the virtual environment is active.

4.  **Install Dependencies**

    With your virtual environment activated, install the required Python packages using `pip`:

    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure Environment Variables**

    This project uses environment variables to securely store API keys and other sensitive information. You need to create a `.env` file in the root directory of the project.

    Create a file named `.env` in `/home/tomk/USCCB/` 
    
    Either (1) copy the contents of the LastPass password ".env file for USCCB repo" and paste that text into the .env file, or (2) Replacing the following placeholder values with the actual keys:

    ```
    SUPABASE_URL="your_supabase_url_here"
    SUPABASE_KEY="your_supabase_anon_key_here"
    GENAI_API_KEY_USCCB="your_google_genai_api_key_here"
    SEARCH_API_KEY_USCCB="your_google_custom_search_api_key_here"
    SEARCH_CX_USCCB="your_google_custom_search_engine_id_here"
    ```

    **Important:**
       *   The code reads these variables using `python-dotenv`.
    *   .gitignore is set to ignore these files.    **Do not commit your `.env` file to version control (e.g., Git).** It contains sensitive information.  

### Running Python Scripts

You can run the Python scripts directly from your terminal:

```bash
python YOUR_SCRIPT_NAME.py
```

### Chrome Installation for Selenium

The project uses Selenium for web scraping, which requires a Chrome browser and ChromeDriver.

**Important:** You must have Google Chrome installed on your system. While `webdriver-manager` will attempt to download the correct ChromeDriver automatically, it does *not* install Chrome itself.

If you are on Linux and Chrome is not installed, you can typically install it using:

```bash
sudo apt-get update
sudo apt-get install google-chrome-stable
```

For other operating systems, please download and install Chrome from the official website: [https://www.google.com/chrome/](https://www.google.com/chrome/)

**Troubleshooting Chrome Installation Errors:**

If you encounter errors like "Permission denied" or "Chrome not found" when running the Python scripts, it's likely due to Chrome not being installed or the script attempting to install it without sufficient permissions. In such cases:

1.  **Manually install Chrome** using the appropriate method for your operating system (e.g., `sudo apt-get install google-chrome-stable` for Debian/Ubuntu).
2.  Ensure Chrome is up-to-date.
3.  Check the `webdriver-manager` documentation for any specific troubleshooting related to ChromeDriver.



## Running the System

### Step 1: Build Diocese Database

```bash
python extract_dioceses.py --max_dioceses 0
# or simply:
python extract_dioceses.py
```

This script will:
- Scrape the USCCB website for all U.S. dioceses
- Extract names, addresses, and website URLs
- Store the data in the Supabase `Dioceses` table. If a diocese with the same name already exists, its `extracted_at` timestamp will be updated; otherwise, a new record will be inserted.

**Parameters**:
- `--max_dioceses`: Optional. Maximum number of dioceses to extract. Defaults to 5. Set to 0 or omit for no limit.

**Note**: The script contains some Jupyter-specific code (like `get_ipython()`). You may need to comment out or remove these lines when running as a standalone Python script.

### Step 2: Find Parish Directories

```bash
python find_parishes.py --max_dioceses_to_process 0
# or simply:
python find_parishes.py
```

This script will:
- Fetch dioceses from the database that don't have parish directory URLs
- Use Selenium to load each diocese website
- Apply AI analysis to identify parish directory links
- Use Google Custom Search as a fallback method
- Store discovered URLs in the `DiocesesParishDirectory` table

**Parameters**:
- `--max_dioceses_to_process`: Optional. Maximum number of dioceses to process. Defaults to 5. Set to 0 for no limit.

**Configuration**: Before running, ensure you've set:
- Mock/live API flags (`use_mock_genai_direct_page`, `use_mock_genai_snippet`, `use_mock_search_engine`) to `False` for live API calls

### Step 3: Extract Parish Information

```bash
python extract_parishes.py --num_dioceses 0 --num_parishes_per_diocese 0
# or simply:
python extract_parishes.py
```

This script will:
- Extract detailed parish information from diocese websites.

**Parameters**:
- `--num_dioceses`: Optional. Maximum number of dioceses to extract from. Defaults to 5. Set to 0 for no limit.
- `--num_parishes_per_diocese`: Optional. Maximum number of parishes to extract from each diocese. Defaults to 5. Set to 0 for no limit.

### Step 4: Extract Liturgical Information (Optional)

```bash
python extract_schedule.py --num_parishes 0
# or simply:
python extract_schedule.py
```

This script will:
- Scrape specified parish websites for Adoration and Reconciliation schedules
- Store the information in a Supabase table named `ParishSchedules`

**Parameters**:
- `--num_parishes`: Optional. Maximum number of parishes to extract from. Defaults to 5. Set to 0 for no limit.

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

## Reporting and Analytics

### `report_statistics.py`

This script connects to the Supabase database to provide statistics and visualizations of the collected data. It reports the current number of records in key tables and generates charts showing how these numbers have changed over time.

**Usage:**

```bash
python report_statistics.py
```

The script will generate PNG image files (e.g., `dioceses_records_over_time.png`, `parishes_records_over_time.png`) in the current directory, visualizing the record counts over time.

---

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