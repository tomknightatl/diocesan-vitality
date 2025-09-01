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

- **Jupyter Notebooks**: Primary execution environment for data collection and processing
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

## Notebooks

### Primary Data Collection

- **`Build Dioceses Database.ipynb`**: Initial scraping of U.S. dioceses from the USCCB website. Populates the foundational `Dioceses` table with names, addresses, and official websites.

- **`Find_Parish_Directory.ipynb`**: Sophisticated AI-powered system that analyzes diocese websites to locate parish directory pages. Uses Google Gemini AI and custom search APIs with intelligent fallback mechanisms.

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

### Specialized Tools

- **`Find_Adoration_and_Reconciliation_information_for_a_Parish.ipynb`**: Targeted extraction of specific liturgical information including Adoration and Reconciliation schedules from parish websites.

### Utility and Analysis

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
- **Python 3.x** with Jupyter Notebooks
- **Supabase** (PostgreSQL) for cloud database
- **Selenium WebDriver** with Chrome for dynamic content
- **BeautifulSoup4** for HTML parsing
- **Google Gemini AI** for content analysis

### AI and Machine Learning
- **Google Generative AI (Gemini)**: Link classification and content analysis
- **Pattern Recognition**: Automated website type detection
- **Confidence Scoring**: Quality assessment of extracted data

### Web Scraping Libraries
- **Selenium**: JavaScript-enabled browsing and interaction
- **Requests**: HTTP client for simple requests
- **BeautifulSoup**: HTML/XML parsing and navigation
- **Tenacity**: Retry logic with exponential backoff

### Data Processing
- **Pandas**: Data manipulation and analysis
- **JSON**: Configuration and result serialization
- **Regular Expressions**: Text pattern matching and extraction

## Getting Started

### Prerequisites

```bash
pip install supabase selenium webdriver-manager google-generativeai beautifulsoup4 pandas tenacity
```

### Environment Setup

1. **Supabase Configuration**:
   - Create a Supabase project
   - Set up `SUPABASE_URL` and `SUPABASE_KEY` in Google Colab secrets

2. **Google AI Setup**:
   - Obtain a Gemini API key from Google AI Studio
   - Configure `GENAI_API_KEY_USCCB` in Colab secrets

3. **Google Custom Search (Optional)**:
   - Set up `SEARCH_API_KEY_USCCB` and `SEARCH_CX_USCCB` for fallback search capabilities

### Running the System

1. **Initialize Diocese Data**:
   ```
   Run Build Dioceses Database.ipynb
   ```

2. **Discover Parish Directories**:
   ```
   Run Find_Parish_Directory.ipynb
   ```

3. **Extract Parish Details**:
   ```python
   # Import the parish extraction modules
   from parish_extraction_core import setup_enhanced_driver, PatternDetector
   from parish_extractors import process_diocese_with_detailed_extraction
   
   # Set up driver and process dioceses
   driver = setup_enhanced_driver()
   result = process_diocese_with_detailed_extraction(diocese_info, driver)
   ```

### Configuration Options

Each notebook and module includes configurable parameters:
- **Processing Limits**: Control the number of dioceses to process
- **Mock vs Live APIs**: Toggle between test mode and production APIs
- **Extraction Confidence**: Adjust AI confidence thresholds
- **Retry Logic**: Configure timeout and retry parameters

## Data Quality Features

### Extraction Statistics
- Success rates by diocese and extraction method
- Confidence scores for AI-powered classifications
- Field completion rates (addresses, phones, websites, etc.)
- Processing time and performance metrics

### Error Handling
- Comprehensive retry logic with exponential backoff
- Graceful degradation when APIs are unavailable
- Detailed error logging and recovery mechanisms
- Data validation and duplicate detection

### Quality Assurance
- Multiple extraction methods with fallback options
- AI-powered content verification
- Geographic coordinate validation
- Contact information format verification

## Advanced Features

### Pattern Recognition System
The system automatically detects website platforms and selects optimal extraction strategies:
- **eCatholic Sites**: Specialized parish finder interface handling
- **SquareSpace**: Platform-specific CSS selector optimization
- **WordPress/Drupal**: CMS-aware content extraction
- **Custom Implementations**: Adaptive parsing for unique diocese websites

### AI-Powered Analysis
- **Content Classification**: Gemini AI evaluates link relevance and quality
- **Context Understanding**: Analyzes surrounding text for better accuracy
- **Confidence Scoring**: Provides quality metrics for extracted data
- **Fallback Intelligence**: Multiple analysis methods ensure comprehensive coverage

### Performance Optimization
- **Intelligent Caching**: Avoids reprocessing completed dioceses
- **Batch Processing**: Efficient handling of large diocese sets
- **Rate Limiting**: Respectful scraping with configurable delays
- **Resource Management**: Automatic WebDriver lifecycle management

## Data Coverage

As of the latest runs, the system has successfully processed:
- **190+ U.S. Catholic Dioceses**
- **Thousands of Parish Records** with detailed information
- **High Success Rates**: 85-95% successful parish directory detection
- **Rich Data Fields**: Including addresses, coordinates, contact info, and schedules

## Contributing

The project is designed for extensibility:
- **New Extractors**: Add support for additional website platforms
- **Enhanced AI**: Improve content analysis with better prompts
- **Additional Data Points**: Extend schema for new information types
- **Quality Improvements**: Enhance validation and error handling

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- United States Conference of Catholic Bishops for providing publicly accessible diocese information
- Google AI for Gemini API access enabling intelligent content analysis
- Supabase for reliable cloud database infrastructure
- The open-source community for the excellent web scraping and data processing libraries