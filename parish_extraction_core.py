# -*- coding: utf-8 -*-
"""
Parish Extraction Core Components
Core classes and utilities for parish data extraction from diocese websites.

This module contains:
- Data models and enums for parish extraction
- Pattern detection system for website analysis
- Base extractor classes and utilities
- Database integration functions
"""

# =============================================================================
# DEPENDENCIES AND IMPORTS
# =============================================================================

import os
import time
import json
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse

# Web scraping
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# =============================================================================
# DATA MODELS AND ENUMS
# =============================================================================

class DiocesePlatform(Enum):
    SQUARESPACE = "squarespace"
    WORDPRESS = "wordpress"
    DRUPAL = "drupal"
    CUSTOM_CMS = "custom"
    STATIC_HTML = "static"
    ECATHOLIC = "ecatholic"
    DIOCESAN_CUSTOM = "diocesan_custom"
    UNKNOWN = "unknown"

class ParishListingType(Enum):
    INTERACTIVE_MAP = "interactive_map"
    STATIC_TABLE = "static_table"
    CARD_GRID = "card_grid"
    SIMPLE_LIST = "simple_list"
    PAGINATED_LIST = "paginated_list"
    SEARCHABLE_DIRECTORY = "searchable_directory"
    PARISH_FINDER = "parish_finder"
    DIOCESE_CARD_LAYOUT = "diocese_card_layout"
    PDF_DIRECTORY = "pdf_directory"
    UNKNOWN = "unknown"

@dataclass
class ParishData:
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pastor: Optional[str] = None
    mass_times: Optional[str] = None
    # Enhanced fields for detailed extraction
    street_address: Optional[str] = None
    full_address: Optional[str] = None
    parish_detail_url: Optional[str] = None
    clergy_info: Optional[str] = None
    service_times: Optional[str] = None
    # Metadata fields
    confidence_score: float = 0.5
    extraction_method: str = "unknown"
    diocese_url: Optional[str] = None
    parish_directory_url: Optional[str] = None
    detail_extraction_success: bool = False
    detail_extraction_error: Optional[str] = None

@dataclass
class DioceseSitePattern:
    platform: DiocesePlatform
    listing_type: ParishListingType
    confidence_score: float
    extraction_method: str
    specific_selectors: Dict[str, str]
    javascript_required: bool
    pagination_pattern: Optional[str] = None
    notes: str = ""

# =============================================================================
# PATTERN DETECTION SYSTEM
# =============================================================================

class PatternDetector:
    """Detects patterns in diocese websites for targeted extraction"""

    def detect_pattern(self, html_content: str, url: str) -> DioceseSitePattern:
        """Analyze website content and detect the best extraction pattern"""
        soup = BeautifulSoup(html_content, 'html.parser')
        html_lower = html_content.lower()

        # Platform detection
        platform = self._detect_platform(html_lower, url)

        # Listing type detection
        listing_type = self._detect_listing_type(html_lower, soup, url)

        # JavaScript requirement
        js_required = self._requires_javascript(html_lower)

        # Determine extraction method and confidence
        extraction_method, confidence, selectors, notes = self._determine_extraction_strategy(
            platform, listing_type, soup, html_lower, url
        )

        return DioceseSitePattern(
            platform=platform,
            listing_type=listing_type,
            confidence_score=confidence,
            extraction_method=extraction_method,
            specific_selectors=selectors,
            javascript_required=js_required,
            notes=notes
        )

    def _detect_platform(self, html_lower: str, url: str) -> DiocesePlatform:
        """Detect CMS/platform"""
        if 'ecatholic.com' in url or 'ecatholic' in html_lower:
            return DiocesePlatform.ECATHOLIC
        elif 'squarespace' in html_lower:
            return DiocesePlatform.SQUARESPACE
        elif 'wp-content' in html_lower or 'wordpress' in html_lower:
            return DiocesePlatform.WORDPRESS
        elif 'drupal' in html_lower:
            return DiocesePlatform.DRUPAL
        elif 'dioslc.org' in url or 'utahcatholicdiocese.org' in url:
            return DiocesePlatform.DIOCESAN_CUSTOM
        else:
            return DiocesePlatform.CUSTOM_CMS

    def _detect_listing_type(self, html_lower: str, soup: BeautifulSoup, url: str) -> ParishListingType:
        """Detect how parishes are listed"""

        # Check for Salt Lake City style card layout
        if ('col-lg location' in html_lower and 'card-title' in html_lower and
            'dioslc.org' in url):
            return ParishListingType.DIOCESE_CARD_LAYOUT

        # Enhanced Parish Finder detection for eCatholic sites
        parish_finder_indicators = [
            'parishfinder' in url.lower(),
            'parish-finder' in url.lower(),
            'finderCore' in html_lower,
            'finder.js' in html_lower,
            'parish finder' in html_lower,
            'li.site' in html_lower and 'siteInfo' in html_lower,
            'finderBar' in html_lower,
            'categories' in html_lower and 'sites' in html_lower and 'parishes' in html_lower,
            soup.find('ul', id='categories'),
            soup.find('div', id='finderCore'),
            soup.find('li', class_='site')
        ]

        if any(parish_finder_indicators):
            return ParishListingType.PARISH_FINDER

        # Interactive map indicators
        map_indicators = ['leaflet', 'google.maps', 'mapbox', 'parish-map', 'interactive']
        if any(indicator in html_lower for indicator in map_indicators):
            return ParishListingType.INTERACTIVE_MAP

        # Table indicators
        if soup.find('table') and ('parish' in html_lower or 'church' in html_lower):
            return ParishListingType.STATIC_TABLE

        # Card/grid layout
        if soup.find_all(class_=re.compile(r'(card|grid|parish-item)', re.I)):
            return ParishListingType.CARD_GRID

        # Pagination
        if any(word in html_lower for word in ['pagination', 'page-numbers', 'next-page']):
            return ParishListingType.PAGINATED_LIST

        return ParishListingType.SIMPLE_LIST

    def _requires_javascript(self, html_lower: str) -> bool:
        """Check if JavaScript is required"""
        js_indicators = ['react', 'angular', 'vue', 'leaflet', 'google.maps', 'ajax', 'finder.js']
        return any(indicator in html_lower for indicator in js_indicators)

    def _determine_extraction_strategy(self, platform, listing_type, soup, html_lower, url):
        """Determine the best extraction strategy"""

        if listing_type == ParishListingType.DIOCESE_CARD_LAYOUT:
            return (
                "diocese_card_extraction_with_details",
                0.95,
                {
                    "parish_cards": ".col-lg.location",
                    "parish_name": ".card-title",
                    "parish_city": ".card-body",
                    "parish_link": "a.card"
                },
                "Diocese card layout detected - specialized extraction for Salt Lake City style with detail page navigation"
            )

        elif listing_type == ParishListingType.PARISH_FINDER:
            return (
                "parish_finder_extraction",
                0.95,
                {
                    "parish_list": "li.site, .site",
                    "parish_name": ".name",
                    "parish_city": ".city",
                    "parish_info": ".siteInfo",
                    "parish_details": ".details",
                    "categories": "#categories",
                    "sites_list": ".sites"
                },
                "Parish finder interface detected - specialized extraction for eCatholic-style interactive directory"
            )

        elif listing_type == ParishListingType.INTERACTIVE_MAP:
            return (
                "interactive_map_extraction",
                0.9,
                {"map_container": "#map, .map-container, .parish-map"},
                "Interactive map detected - will extract from JS data and markers"
            )

        elif listing_type == ParishListingType.STATIC_TABLE:
            return (
                "table_extraction",
                0.95,
                {"table": "table", "rows": "tr:not(:first-child)"},
                "HTML table detected - most reliable extraction method"
            )

        elif platform == DiocesePlatform.SQUARESPACE:
            return (
                "squarespace_extraction",
                0.8,
                {"items": ".summary-item, .parish-item", "title": ".summary-title"},
                "SquareSpace platform - using platform-specific selectors"
            )

        else:
            return (
                "generic_extraction",
                0.4,
                {"containers": "[class*='parish'], [class*='church']"},
                "Using generic extraction patterns"
            )

# =============================================================================
# BASE EXTRACTOR CLASS
# =============================================================================

class BaseExtractor:
    """Base class for parish extractors"""

    def __init__(self, pattern: DioceseSitePattern):
        self.pattern = pattern

    def extract(self, driver, soup: BeautifulSoup, url: str) -> List[ParishData]:
        """Extract parishes from the given page"""
        raise NotImplementedError

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return ' '.join(text.strip().split())

    def extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        if not text:
            return None

        # Look for phone patterns
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        match = re.search(phone_pattern, text)
        if match:
            return match.group()
        return None

    def extract_email(self, text: str) -> Optional[str]:
        """Extract email from text"""
        if not text:
            return None

        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        if match:
            return match.group()
        return None

# =============================================================================
# WEBDRIVER SETUP UTILITIES
# =============================================================================

def setup_enhanced_driver():
    """Set up Chrome WebDriver with options optimized for parish extraction"""

    print("🔧 Setting up enhanced Chrome WebDriver...")

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--disable-images')
    chrome_options.add_argument('--disable-javascript-harmony-shipping')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')

    # User agent to avoid blocking
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)

        print("✅ Chrome WebDriver initialized successfully")
        return driver

    except Exception as e:
        print(f"❌ Failed to initialize WebDriver: {e}")
        raise

# =============================================================================
# DATABASE INTEGRATION FUNCTIONS
# =============================================================================

def prepare_parish_for_supabase(parish_data: ParishData, diocese_name: str, diocese_url: str, parish_directory_url: str) -> Dict:
    """Convert ParishData to format compatible with Supabase schema"""

    # Use street address if available, otherwise fall back to full address or address
    street_address = parish_data.street_address or parish_data.full_address or parish_data.address

    return {
        'Name': parish_data.name,
        'Status': 'Parish',
        'Deanery': None,
        'Street Address': street_address,
        'City': parish_data.city,
        'State': parish_data.state,
        'Zip Code': parish_data.zip_code,
        'Phone Number': parish_data.phone,
        'Web': parish_data.website,
        'diocese_url': diocese_url,
        'parish_directory_url': parish_directory_url,
        'parish_detail_url': parish_data.parish_detail_url,
        'extraction_method': parish_data.extraction_method,
        'confidence_score': parish_data.confidence_score,
        'detail_extraction_success': parish_data.detail_extraction_success,
        'detail_extraction_error': parish_data.detail_extraction_error,
        'clergy_info': parish_data.clergy_info,
        'service_times': parish_data.service_times,
        'full_address': parish_data.full_address,
        'latitude': parish_data.latitude,
        'longitude': parish_data.longitude,
        'extracted_at': datetime.now().isoformat()
    }

def enhanced_safe_upsert_to_supabase(parishes: List[ParishData], diocese_name: str, diocese_url: str, 
                                     parish_directory_url: str, supabase):
    """Enhanced version of Supabase upsert function with Parish Finder support"""

    if not supabase:
        print("  ❌ Supabase not available")
        return False

    success_count = 0
    detail_success_count = 0
    skipped_count = 0

    for parish in parishes:
        try:
            # Enhanced filtering for non-parish items
            skip_terms = [
                'finder', 'contact', 'chancery', 'pastoral center', 'tv mass',
                'directory', 'search', 'filter', 'map', 'diocese', 'bishop',
                'office', 'center', 'no parish registration', 'archdiocese'
            ]

            if any(skip_word in parish.name.lower() for skip_word in skip_terms):
                print(f"    ⏭️ Skipped: {parish.name} (not a parish)")
                skipped_count += 1
                continue

            # Must have a meaningful name to proceed
            if not parish.name or len(parish.name.strip()) < 3:
                print(f"    ⏭️ Skipped: Invalid name for parish")
                skipped_count += 1
                continue

            # Convert to schema format
            supabase_data = prepare_parish_for_supabase(parish, diocese_name, diocese_url, parish_directory_url)

            # Remove None values and empty strings, but keep boolean False and numeric 0
            clean_data = {}
            for k, v in supabase_data.items():
                if v is not None and v != "":
                    clean_data[k] = v
                elif isinstance(v, (bool, int, float)):
                    clean_data[k] = v

            # Must have a name to proceed
            if not clean_data.get('Name') or len(clean_data.get('Name', '')) < 3:
                print(f"    ⏭️ Skipped: Invalid name after cleaning")
                skipped_count += 1
                continue

            # Use existing upsert logic
            response = supabase.table('Parishes').insert(clean_data).execute()

            if hasattr(response, 'error') and response.error:
                print(f"    ❌ Database error for {parish.name}: {response.error}")
            else:
                success_count += 1
                if parish.detail_extraction_success:
                    detail_success_count += 1
                    detail_indicator = "📍"
                else:
                    detail_indicator = "📌"

                # Show confidence and extraction method
                method_short = parish.extraction_method.replace('_extraction', '').replace('_', ' ')
                print(f"    ✅ {detail_indicator} Saved: {parish.name}")
                print(f"        📊 Method: {method_short}, Confidence: {parish.confidence_score:.2f}")

                # Show what fields were captured
                captured_fields = []
                if parish.city: captured_fields.append("city")
                if parish.address or parish.street_address or parish.full_address: captured_fields.append("address")
                if parish.phone: captured_fields.append("phone")
                if parish.website: captured_fields.append("website")
                if parish.latitude and parish.longitude: captured_fields.append("coordinates")
                if parish.clergy_info: captured_fields.append("clergy")
                if parish.service_times: captured_fields.append("schedule")

                if captured_fields:
                    print(f"        📋 Fields: {', '.join(captured_fields)}")

        except Exception as e:
            print(f"    ❌ Error saving {parish.name}: {e}")

    print(f"  📊 Results: {success_count} saved, {skipped_count} skipped, {detail_success_count} with detailed info")
    if success_count > 0:
        success_rate = (success_count / (success_count + skipped_count)) * 100
        print(f"  📈 Success rate: {success_rate:.1f}%")

    return success_count > 0

def analyze_parish_finder_quality(parishes: List[ParishData]) -> Dict:
    """Analyze the quality of Parish Finder extraction"""

    if not parishes:
        return {'error': 'No parishes to analyze'}

    total_parishes = len(parishes)

    # Parish Finder specific analysis
    analysis = {
        'total_parishes': total_parishes,
        'extraction_methods': {},
        'parish_finder_specific': {
            'has_coordinates': sum(1 for p in parishes if p.latitude and p.longitude),
            'has_city': sum(1 for p in parishes if p.city),
            'has_site_info': sum(1 for p in parishes if p.detail_extraction_success),
            'confidence_distribution': {
                'high_confidence': sum(1 for p in parishes if p.confidence_score >= 0.8),
                'medium_confidence': sum(1 for p in parishes if 0.5 <= p.confidence_score < 0.8),
                'low_confidence': sum(1 for p in parishes if p.confidence_score < 0.5)
            }
        },
        'data_completeness': {
            'names_present': sum(1 for p in parishes if p.name and len(p.name) > 2),
            'cities_present': sum(1 for p in parishes if p.city),
            'addresses_present': sum(1 for p in parishes if p.street_address or p.full_address or p.address),
            'phones_present': sum(1 for p in parishes if p.phone),
            'websites_present': sum(1 for p in parishes if p.website),
            'coordinates_present': sum(1 for p in parishes if p.latitude and p.longitude),
            'clergy_info_present': sum(1 for p in parishes if p.clergy_info)
        }
    }

    # Track extraction methods used
    for parish in parishes:
        method = parish.extraction_method
        analysis['extraction_methods'][method] = analysis['extraction_methods'].get(method, 0) + 1

    # Calculate percentages
    analysis['data_completeness_percentages'] = {
        f"{key}_percentage": (value / total_parishes * 100)
        for key, value in analysis['data_completeness'].items()
    }

    # Overall quality score
    basic_score = (analysis['data_completeness']['names_present'] +
                  analysis['data_completeness']['cities_present']) / (total_parishes * 2) * 100

    enhanced_score = (analysis['data_completeness']['addresses_present'] +
                     analysis['data_completeness']['phones_present'] +
                     analysis['data_completeness']['coordinates_present']) / (total_parishes * 3) * 100

    analysis['parish_finder_quality_score'] = (basic_score + enhanced_score) / 2

    return analysis