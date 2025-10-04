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

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from core.logger import get_logger

logger = get_logger(__name__)

# Web scraping
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
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
    IFRAME_EMBEDDED = "iframe_embedded"
    HOVER_NAVIGATION = "hover_navigation"
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
    distance_miles: Optional[float] = None


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


def clean_parish_name_and_extract_address(raw_name: str) -> Dict:
    """
    Enhanced address parsing using both usaddress library and regex fallbacks.
    Extracts parish name, distance, and professional-grade address components.
    """
    # Handle None or empty input
    if not raw_name or not isinstance(raw_name, str):
        return {
            "name": "",
            "street_address": None,
            "city": None,
            "state": None,
            "zip_code": None,
            "full_address": None,
            "distance_miles": None,
        }

    cleaned_data = {
        "name": raw_name,
        "street_address": None,
        "city": None,
        "state": None,
        "zip_code": None,
        "full_address": None,
        "distance_miles": None,
    }

    # Step 1: Extract distance (e.g., (203.7 Miles))
    distance_match = re.search(r"\((\d+\.?\d*)\s*Miles\)", raw_name, re.IGNORECASE)
    if distance_match:
        try:
            cleaned_data["distance_miles"] = float(distance_match.group(1))
            # Remove distance from raw_name
            raw_name = raw_name.replace(distance_match.group(0), "").strip()
        except ValueError:
            pass  # Keep distance as None if conversion fails

    # Step 2: Try enhanced address parsing with usaddress library
    enhanced_result = enhanced_address_parsing(raw_name)
    if enhanced_result["success"]:
        # Use enhanced parsing results
        cleaned_data.update(
            {
                "name": enhanced_result["parish_name"],
                "street_address": enhanced_result["street_address"],
                "city": enhanced_result["city"],
                "state": enhanced_result["state"],
                "zip_code": enhanced_result["zip_code"],
                "full_address": enhanced_result["full_address"],
            }
        )
        return cleaned_data

    # Step 3: Fallback to original regex-based parsing
    return legacy_address_parsing(raw_name, cleaned_data)


def enhanced_address_parsing(raw_name: str) -> Dict:
    """
    Professional address parsing using usaddress library with intelligent fallbacks.
    """
    try:
        import usaddress

        # Look for address patterns in the string
        # Address patterns typically start with a number
        address_pattern = re.search(
            r"(\d+\s+[A-Za-z0-9\s\.\-\,]+(?:street|st|avenue|ave|road|rd|drive|dr|way|lane|ln|boulevard|blvd|court|ct|plaza|pl|terrace|ter|circle|cir|parkway|pkwy|highway|hwy|route|rte|blvd).*?)$",
            raw_name,
            re.IGNORECASE,
        )

        if not address_pattern:
            return {"success": False}

        potential_address = address_pattern.group(1).strip()
        parish_name = raw_name.replace(potential_address, "").strip().rstrip(",").strip()

        # Parse the address with usaddress
        parsed_components, address_type = usaddress.tag(potential_address)

        # Only proceed if we got a valid street address
        if address_type != "Street Address":
            return {"success": False}

        # Extract components using usaddress labels
        street_parts = []

        # Build street address from components
        if parsed_components.get("AddressNumber"):
            street_parts.append(parsed_components["AddressNumber"])

        if parsed_components.get("StreetNamePreDirectional"):
            street_parts.append(parsed_components["StreetNamePreDirectional"])

        if parsed_components.get("StreetNamePreType"):
            street_parts.append(parsed_components["StreetNamePreType"])

        if parsed_components.get("StreetName"):
            street_parts.append(parsed_components["StreetName"])

        if parsed_components.get("StreetNamePostType"):
            street_parts.append(parsed_components["StreetNamePostType"])

        if parsed_components.get("StreetNamePostDirectional"):
            street_parts.append(parsed_components["StreetNamePostDirectional"])

        # Handle unit/apartment info
        unit_parts = []
        for unit_key in ["OccupancyType", "OccupancyIdentifier"]:
            if parsed_components.get(unit_key):
                unit_parts.append(parsed_components[unit_key])

        street_address = " ".join(street_parts)
        if unit_parts:
            street_address += " " + " ".join(unit_parts)

        city = parsed_components.get("PlaceName", "")
        state = parsed_components.get("StateName", "")
        zip_code = parsed_components.get("ZipCode", "")

        # Build full address
        full_address_parts = [street_address]
        if city:
            full_address_parts.append(city)
        if state:
            if city:
                full_address_parts[-1] = f"{city}, {state}"
            else:
                full_address_parts.append(state)
        if zip_code:
            full_address_parts.append(zip_code)

        full_address = " ".join(full_address_parts)

        return {
            "success": True,
            "parish_name": parish_name,
            "street_address": street_address,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "full_address": full_address,
            "parsing_method": "usaddress_enhanced",
        }

    except Exception as e:
        # If usaddress fails, return failure to trigger fallback
        logger.debug(f"Enhanced address parsing failed: {e}")
        return {"success": False}


def legacy_address_parsing(raw_name: str, cleaned_data: Dict) -> Dict:
    """
    Legacy regex-based address parsing as fallback.
    """
    # Regex to find common address patterns at the end of the string
    address_pattern = re.compile(
        r"(\d+\s+[\w\s\.\-]+(?:street|st|avenue|ave|road|rd|drive|dr|way|lane|ln|boulevard|blvd|court|ct|plaza|pl|terrace|ter|circle|cir|parkway|pkwy|highway|hwy|route|rte|blvd)\.?,?\s*.*?\s*\w{2}\s*\d{5}(?:-\d{4})?)$",
        re.IGNORECASE,
    )
    address_match = address_pattern.search(raw_name)

    if address_match:
        full_address = address_match.group(1).strip()
        cleaned_data["full_address"] = full_address

        # Remove the extracted address from the raw_name to get the clean name
        cleaned_data["name"] = raw_name.replace(full_address, "").strip()

        # Attempt to parse address components from full_address
        # City, State, Zip Code
        city_state_zip_match = re.search(r"([A-Za-z\s\.]+),\s*([A-Za-z]{2})\s*(\d{5}(?:-\d{4})?)$", full_address)
        if city_state_zip_match:
            cleaned_data["city"] = city_state_zip_match.group(1).strip()
            cleaned_data["state"] = city_state_zip_match.group(2).strip()
            cleaned_data["zip_code"] = city_state_zip_match.group(3).strip()
            # The street address is everything before the city, state, zip
            street_address_raw = full_address.replace(city_state_zip_match.group(0), "").strip()
            cleaned_data["street_address"] = street_address_raw.rstrip(",").strip()
        else:
            # Fallback for just street and zip if city/state not clearly parsed
            zip_match = re.search(r"(\d{5}(?:-\d{4})?)$", full_address)
            if zip_match:
                cleaned_data["zip_code"] = zip_match.group(1)
                cleaned_data["street_address"] = full_address.replace(zip_match.group(0), "").strip().rstrip(",").strip()
            else:
                cleaned_data["street_address"] = full_address  # If no clear components, treat as street

    # Final clean up of the name (remove trailing commas, extra spaces)
    cleaned_data["name"] = re.sub(r",\s*$", "", cleaned_data["name"]).strip()
    cleaned_data["name"] = re.sub(r"\s+", " ", cleaned_data["name"]).strip()

    return cleaned_data


# =============================================================================
# PATTERN DETECTION SYSTEM
# =============================================================================


class PatternDetector:
    """Detects patterns in diocese websites for targeted extraction"""

    def detect_pattern(self, html_content: str, url: str) -> DioceseSitePattern:
        """Analyze website content and detect the best extraction pattern"""
        soup = BeautifulSoup(html_content, "html.parser")
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
            notes=notes,
        )

    def _detect_platform(self, html_lower: str, url: str) -> DiocesePlatform:
        """Detect CMS/platform"""
        if "ecatholic.com" in url or "ecatholic" in html_lower:
            return DiocesePlatform.ECATHOLIC
        elif "squarespace" in html_lower:
            return DiocesePlatform.SQUARESPACE
        elif "wp-content" in html_lower or "wordpress" in html_lower:
            return DiocesePlatform.WORDPRESS
        elif "drupal" in html_lower:
            return DiocesePlatform.DRUPAL
        elif "dioslc.org" in url or "utahcatholicdiocese.org" in url:
            return DiocesePlatform.DIOCESAN_CUSTOM
        else:
            return DiocesePlatform.CUSTOM_CMS

    def _detect_listing_type(self, html_lower: str, soup: BeautifulSoup, url: str) -> ParishListingType:
        """Detect how parishes are listed"""

        # Check for iframe-embedded parish directories (HIGHEST PRIORITY)
        iframe_indicators = self._check_for_iframe_content(soup, html_lower, url)
        if iframe_indicators:
            return ParishListingType.IFRAME_EMBEDDED

        # Check for Salt Lake City style card layout
        if "col-lg location" in html_lower and "card-title" in html_lower and "dioslc.org" in url:
            return ParishListingType.DIOCESE_CARD_LAYOUT

        # Enhanced Parish Finder detection for eCatholic sites
        parish_finder_indicators = [
            "parishfinder" in url.lower(),
            "parish-finder" in url.lower(),
            "finderCore" in html_lower,
            "finder.js" in html_lower,
            "parish finder" in html_lower,
            "li.site" in html_lower and "siteInfo" in html_lower,
            "finderBar" in html_lower,
            "categories" in html_lower and "sites" in html_lower and "parishes" in html_lower,
            soup.find("ul", id="categories"),
            soup.find("div", id="finderCore"),
            soup.find("li", class_="site"),
        ]

        if any(parish_finder_indicators):
            return ParishListingType.PARISH_FINDER

        # Check for hover-based navigation patterns (Diocese of Wheeling-Charleston style)
        hover_navigation_indicators = [
            # Specific URL patterns for known hover navigation sites
            "dwc.org" in url.lower(),
            # Look for dropdown or hover navigation elements
            soup.find("li", class_=re.compile(r"dropdown|hover", re.I)),
            soup.find("ul", class_=re.compile(r"dropdown|nav|menu", re.I)),
            soup.find("nav", class_=re.compile(r"dropdown|hover", re.I)),
            # Navigation menus with hidden elements that appear on hover
            "dropdown" in html_lower and "nav" in html_lower,
            # CSS indicators of hover-based menus
            ":hover" in html_lower and "menu" in html_lower,
            # JavaScript navigation systems
            "hover" in html_lower and ("parish" in html_lower or "directory" in html_lower),
        ]

        if any(hover_navigation_indicators):
            return ParishListingType.HOVER_NAVIGATION

        # Interactive map indicators (but exclude known hover navigation sites)
        if "dwc.org" not in url.lower():  # Don't override hover navigation for known sites
            map_indicators = ["leaflet", "google.maps", "mapbox", "parish-map", "interactive"]
            if any(indicator in html_lower for indicator in map_indicators):
                return ParishListingType.INTERACTIVE_MAP

        # Table indicators
        if soup.find("table") and ("parish" in html_lower or "church" in html_lower):
            return ParishListingType.STATIC_TABLE

        # Card/grid layout
        if soup.find_all(class_=re.compile(r"(card|grid|parish-item)", re.I)):
            return ParishListingType.CARD_GRID

        # Pagination
        if any(word in html_lower for word in ["pagination", "page-numbers", "next-page"]):
            return ParishListingType.PAGINATED_LIST

        return ParishListingType.SIMPLE_LIST

    def _check_for_iframe_content(self, soup: BeautifulSoup, html_lower: str, url: str) -> bool:
        """Check if parish directory content is loaded via iframe"""
        iframes = soup.find_all("iframe")

        for iframe in iframes:
            src = iframe.get("src", "") or ""
            src_lower = src.lower()

            # EXCLUDE payment, analytics, and social media iframes
            excluded_services = [
                "stripe.com",
                "paypal.com",
                "square.com",
                "donate",
                "payment",
                "analytics",
                "google-analytics",
                "googletagmanager",
                "facebook.com",
                "twitter.com",
                "youtube.com",
                "vimeo.com",
                "recaptcha",
                "ads",
                "advertising"
            ]

            # Skip if this is an excluded iframe
            if any(excluded in src_lower for excluded in excluded_services):
                continue

            # Check for mapping/parish directory services in iframes
            mapping_services = ["maptive.com", "google.com/maps", "mapbox.com", "arcgis.com", "leaflet", "openstreetmap"]

            parish_indicators = ["parish", "church", "directory", "locator", "finder"]

            # Check if iframe source contains mapping services or parish-related content
            if any(service in src_lower for service in mapping_services):
                return True

            # Specific check for Archdiocese of Denver Maptive iframe
            if "fortress.maptive.com" in src_lower and "archden" in src_lower:
                return True

            # Check for parish-related content in iframe
            if any(indicator in src_lower for indicator in parish_indicators):
                return True

        return False

    def _requires_javascript(self, html_lower: str) -> bool:
        """Check if JavaScript is required"""
        js_indicators = ["react", "angular", "vue", "leaflet", "google.maps", "ajax", "finder.js"]
        return any(indicator in html_lower for indicator in js_indicators)

    def _determine_extraction_strategy(self, platform, listing_type, soup, html_lower, url):
        """Determine the best extraction strategy"""

        if listing_type == ParishListingType.IFRAME_EMBEDDED:
            return (
                "iframe_extraction",
                0.95,
                {
                    "iframe_selector": "iframe[src*='maptive'], iframe[src*='parish'], iframe[src*='church']",
                    "maptive_url": "fortress.maptive.com",
                    "wait_selectors": "[data-parish], .parish, .church, .marker",
                    "data_extractors": ["window.parishData", "window.mapData", "window.locations"],
                },
                "Iframe-embedded parish directory detected - will extract from embedded content",
            )

        elif listing_type == ParishListingType.DIOCESE_CARD_LAYOUT:
            return (
                "diocese_card_extraction_with_details",
                0.95,
                {
                    "parish_cards": ".col-lg.location",
                    "parish_name": ".card-title",
                    "parish_city": ".card-body",
                    "parish_link": "a.card",
                },
                "Diocese card layout detected - specialized extraction for Salt Lake City style with detail page navigation",
            )

        elif listing_type == ParishListingType.HOVER_NAVIGATION:
            return (
                "navigation_extraction",
                0.9,
                {
                    "nav_selectors": ["nav", ".navbar", ".navigation", ".menu"],
                    "hover_targets": ["a[href*='parish']", ".menu-item", ".nav-item", ".dropdown"],
                    "dropdown_selectors": [".dropdown-menu a", ".submenu a", ".nav-dropdown a"],
                    "parish_indicators": ["parish", "church", "directory", "find", "locate"],
                },
                "Hover-based navigation detected - will interact with dropdown menus to find parish directory",
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
                    "sites_list": ".sites",
                },
                "Parish finder interface detected - specialized extraction for eCatholic-style interactive directory",
            )

        elif listing_type == ParishListingType.INTERACTIVE_MAP:
            return (
                "interactive_map_extraction",
                0.9,
                {"map_container": "#map, .map-container, .parish-map"},
                "Interactive map detected - will extract from JS data and markers",
            )

        elif listing_type == ParishListingType.STATIC_TABLE:
            return (
                "table_extraction",
                0.95,
                {"table": "table", "rows": "tr:not(:first-child)"},
                "HTML table detected - most reliable extraction method",
            )

        elif platform == DiocesePlatform.SQUARESPACE:
            return (
                "squarespace_extraction",
                0.8,
                {"items": ".summary-item, .parish-item", "title": ".summary-title"},
                "SquareSpace platform - using platform-specific selectors",
            )

        else:
            return (
                "generic_extraction",
                0.4,
                {"containers": "[class*='parish'], [class*='church']"},
                "Using generic extraction patterns",
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
        return " ".join(text.strip().split())

    def extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        if not text:
            return None

        # Look for phone patterns
        phone_pattern = r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
        match = re.search(phone_pattern, text)
        if match:
            return match.group()
        return None

    def extract_email(self, text: str) -> Optional[str]:
        """Extract email from text"""
        if not text:
            return None

        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        match = re.search(email_pattern, text)
        if match:
            return match.group()
        return None


# =============================================================================
# WEBDRIVER SETUP UTILITIES
# =============================================================================


def setup_enhanced_driver():
    """Set up Chrome WebDriver with options optimized for parish extraction"""

    logger.info("🔧 Setting up enhanced Chrome WebDriver...")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript-harmony-shipping")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")

    # User agent to avoid blocking
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(5)

        logger.info("✅ Chrome WebDriver initialized successfully")
        return driver

    except Exception as e:
        logger.error(f"❌ Failed to initialize WebDriver: {e}")
        raise


# =============================================================================
# DATABASE INTEGRATION FUNCTIONS
# =============================================================================


def _clean_supabase_data(data: Dict) -> Dict:
    """
    Removes None values and empty strings from a dictionary,
    while preserving boolean False and numeric 0 values.
    """
    cleaned_data = {}
    for k, v in data.items():
        if v is not None and v != "":
            cleaned_data[k] = v
        elif isinstance(v, (bool, int, float)):
            cleaned_data[k] = v
    return cleaned_data


def prepare_parish_for_supabase(
    parish_data: ParishData, diocese_id: int, diocese_name: str, diocese_url: str, parish_directory_url: str
) -> Dict:
    """Convert ParishData to format compatible with Supabase schema"""

    # Use street address if available, otherwise fall back to full address or address
    street_address = parish_data.street_address or parish_data.full_address or parish_data.address

    return {
        "Name": parish_data.name,
        "Status": "Parish",
        "Deanery": None,
        "Street Address": street_address,
        "City": parish_data.city,
        "State": parish_data.state,
        "Zip Code": parish_data.zip_code,
        "Phone Number": parish_data.phone,
        "Web": parish_data.website,
        "diocese_url": diocese_url,
        "parish_directory_url": parish_directory_url,
        "parish_detail_url": parish_data.parish_detail_url,
        "extraction_method": parish_data.extraction_method,
        "confidence_score": parish_data.confidence_score,
        "detail_extraction_success": parish_data.detail_extraction_success,
        "detail_extraction_error": parish_data.detail_extraction_error,
        "clergy_info": parish_data.clergy_info,
        "service_times": parish_data.service_times,
        "full_address": parish_data.full_address,
        "latitude": parish_data.latitude,
        "longitude": parish_data.longitude,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "diocese_id": diocese_id,
    }


PARISH_SKIP_TERMS = [
    "finder",
    "contact",
    "chancery",
    "pastoral center",
    "tv mass",
    "directory",
    "search",
    "filter",
    "map",
    "diocese",
    "bishop",
    "office",
    "center",
    "no parish registration",
    "archdiocese",
]


def enhanced_safe_upsert_to_supabase(
    parishes: List[ParishData],
    diocese_id: int,
    diocese_name: str,
    diocese_url: str,
    parish_directory_url: str,
    supabase,
    monitoring_client=None,
):
    """Enhanced version of Supabase upsert function with batch operations and Parish Finder support"""

    if not supabase:
        logger.error("  ❌ Supabase not available")
        return False

    if not parishes:
        logger.info("  📝 No parishes to process")
        return True

    # Phase 1: Filter and prepare data for batch processing
    valid_parishes = []
    skipped_count = 0
    detail_success_count = 0

    logger.info(f"  🔄 Preparing {len(parishes)} parishes for batch upload...")

    for parish in parishes:
        try:
            # Enhanced filtering for non-parish items
            if any(skip_word in parish.name.lower() for skip_word in PARISH_SKIP_TERMS):
                logger.debug(f"    ⏭️ Skipped: {parish.name} (not a parish)")
                skipped_count += 1
                continue

            # Must have a meaningful name to proceed
            if not parish.name or len(parish.name.strip()) < 3:
                logger.debug(f"    ⏭️ Skipped: Invalid name for parish")
                skipped_count += 1
                continue

            # Convert to schema format
            supabase_data = prepare_parish_for_supabase(parish, diocese_id, diocese_name, diocese_url, parish_directory_url)
            clean_data = _clean_supabase_data(supabase_data)

            # Must have a name to proceed
            if not clean_data.get("Name") or len(clean_data.get("Name", "")) < 3:
                logger.debug(f"    ⏭️ Skipped: Invalid name after cleaning")
                skipped_count += 1
                continue

            valid_parishes.append({"data": clean_data, "original": parish})

            if parish.detail_extraction_success:
                detail_success_count += 1

        except Exception as e:
            logger.warning(f"    ⚠️ Error preparing {parish.name}: {e}")
            skipped_count += 1

    if not valid_parishes:
        logger.info(f"  📊 Results: 0 saved, {skipped_count} skipped, 0 with detailed info")
        return False

    # Phase 2: Batch upsert with optimized batch size
    batch_size = min(50, len(valid_parishes))  # Optimal batch size for Supabase
    success_count = 0
    updated_count = 0
    new_count = 0
    total_batches = (len(valid_parishes) + batch_size - 1) // batch_size

    logger.info(f"  🚀 Processing {len(valid_parishes)} parishes in {total_batches} batch(es) of {batch_size}...")

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(valid_parishes))
        batch = valid_parishes[start_idx:end_idx]

        # Prepare batch data and check existing parishes before upsert
        batch_data = []
        parish_actions = {}  # Store whether each parish is new or existing

        for item in batch:
            parish = item["original"]
            parish_data = item["data"]
            batch_data.append(parish_data)

            # Check if parish already exists to determine insert vs update
            if monitoring_client:
                try:
                    existing = (
                        supabase.table("Parishes").select("id").eq("Name", parish.name).eq("diocese_id", diocese_id).execute()
                    )
                    is_new_parish = not existing.data
                    parish_actions[parish.name] = "Parish added" if is_new_parish else "Parish updated"
                except Exception as e:
                    parish_actions[parish.name] = "Parish saved"
                    logger.debug(f"Could not determine insert/update status for {parish.name}: {e}")

        try:
            # Execute batch upsert
            logger.info(f"    📦 Batch {batch_num + 1}/{total_batches}: Upserting {len(batch_data)} parishes...")
            response = supabase.table("Parishes").upsert(batch_data, on_conflict="Name,diocese_id").execute()

            if hasattr(response, "error") and response.error:
                logger.error(f"    ❌ Batch {batch_num + 1} database error: {response.error}")
                # Try individual upserts as fallback for this batch
                logger.info(f"    🔄 Falling back to individual upserts for batch {batch_num + 1}...")
                batch_success = _fallback_individual_upserts(batch, supabase, monitoring_client, diocese_name, parish_actions)
                success_count += batch_success
            else:
                batch_success = len(batch_data)
                success_count += batch_success
                logger.info(f"    ✅ Batch {batch_num + 1}: Successfully saved {batch_success} parishes")

                # Send monitoring logs for each parish inserted
                if monitoring_client:
                    for item in batch:
                        parish = item["original"]
                        action = parish_actions.get(parish.name, "Parish saved")
                        website_link = (
                            f" → <a href='{parish.website}' target='_blank'>{parish.website}</a>" if parish.website else ""
                        )
                        monitoring_client.send_log(
                            f"Step 3 │ ✅ {action}: {parish.name}, {diocese_name}{website_link}", "INFO"
                        )

                # Log sample of saved parishes for verification (console only)
                for i, item in enumerate(batch[:3]):  # Show first 3 parishes in batch
                    parish = item["original"]
                    detail_indicator = "📍" if parish.detail_extraction_success else "📌"
                    method_short = parish.extraction_method.replace("_extraction", "").replace("_", " ")
                    logger.info(f"      {detail_indicator} {parish.name} ({method_short}, {parish.confidence_score:.2f})")

                if len(batch) > 3:
                    logger.info(f"      ... and {len(batch) - 3} more parishes")

        except Exception as e:
            logger.error(f"    ❌ Batch {batch_num + 1} failed: {e}")
            # Try individual upserts as fallback
            logger.info(f"    🔄 Falling back to individual upserts for batch {batch_num + 1}...")
            batch_success, batch_updated, batch_new = _fallback_individual_upserts(batch, supabase, monitoring_client, diocese_name, parish_actions)
            success_count += batch_success
            updated_count += batch_updated
            new_count += batch_new

    # Phase 3: Summary reporting
    logger.info(f"  📊 Results: {success_count} saved ({new_count} new, {updated_count} updated), {skipped_count} skipped, {detail_success_count} with detailed info")
    if success_count > 0:
        success_rate = (success_count / (success_count + skipped_count)) * 100
        logger.info(f"  📈 Success rate: {success_rate:.1f}%")

        # Performance improvement calculation
        individual_calls_would_be = success_count + skipped_count
        actual_db_calls = total_batches + (skipped_count if success_count < len(valid_parishes) else 0)
        performance_improvement = ((individual_calls_would_be - actual_db_calls) / individual_calls_would_be) * 100
        logger.info(
            f"  ⚡ Performance: {actual_db_calls} DB calls vs {individual_calls_would_be} individual ({performance_improvement:.0f}% reduction)"
        )

    return success_count > 0


def _fallback_individual_upserts(
    batch: List[Dict], supabase, monitoring_client=None, diocese_name=None, parish_actions=None
) -> tuple:
    """Fallback function for individual upserts when batch fails

    Handles duplicate constraints by checking if parish exists and updating instead of inserting.

    Returns:
        tuple: (success_count, updated_count, new_count)
    """
    success_count = 0
    updated_count = 0
    new_count = 0

    for item in batch:
        try:
            parish = item["original"]
            data = item["data"]

            # Check if parish exists by Name or Web URL (both have unique constraints)
            existing = None
            try:
                # Check by name first
                name_check = (
                    supabase.table("Parishes")
                    .select("id")
                    .eq("diocese_id", data["diocese_id"])
                    .eq("Name", data["Name"])
                    .execute()
                )
                if name_check.data:
                    existing = name_check.data[0]
                # If not found by name, check by Web URL (if provided)
                elif data.get("Web"):
                    web_check = (
                        supabase.table("Parishes")
                        .select("id")
                        .eq("diocese_id", data["diocese_id"])
                        .eq("Web", data["Web"])
                        .execute()
                    )
                    if web_check.data:
                        existing = web_check.data[0]
            except Exception as check_error:
                logger.debug(f"      Error checking existing parish {parish.name}: {check_error}")

            # Update if exists, insert if new
            if existing:
                response = supabase.table("Parishes").update(data).eq("id", existing["id"]).execute()
                action_verb = "updated"
                updated_count += 1
            else:
                response = supabase.table("Parishes").insert(data).execute()
                action_verb = "added"
                new_count += 1

            if not (hasattr(response, "error") and response.error):
                success_count += 1
                logger.info(f"      ✅ 📌 Parish {action_verb}: {parish.name}")

                # Send to monitoring if available
                if monitoring_client and diocese_name:
                    action = f"Parish {action_verb}"
                    website_link = (
                        f" → <a href='{parish.website}' target='_blank'>{parish.website}</a>" if parish.website else ""
                    )
                    monitoring_client.send_log(f"Step 3 │ ✅ {action}: {parish.name}, {diocese_name}{website_link}", "INFO")
            else:
                logger.error(f"      ❌ Individual {action_verb} error for {parish.name}: {response.error}")
        except Exception as e:
            parish = item["original"]
            # Check if it's a duplicate error that we can ignore
            if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                logger.warning(f"      ⚠️ Parish already exists (skipping): {parish.name}")
                success_count += 1  # Count as success since data is in DB
            else:
                logger.error(f"      ❌ Individual upsert failed for {parish.name}: {e}")

    if updated_count > 0 or new_count > 0:
        logger.info(f"      📊 Batch summary: {success_count} saved ({updated_count} updated, {new_count} new)")

    return success_count, updated_count, new_count


def analyze_parish_finder_quality(parishes: List[ParishData]) -> Dict:
    """Analyze the quality of Parish Finder extraction"""

    if not parishes:
        return {"error": "No parishes to analyze"}

    total_parishes = len(parishes)

    # Parish Finder specific analysis
    analysis = {
        "total_parishes": total_parishes,
        "extraction_methods": {},
        "parish_finder_specific": {
            "has_coordinates": sum(1 for p in parishes if p.latitude and p.longitude),
            "has_city": sum(1 for p in parishes if p.city),
            "has_site_info": sum(1 for p in parishes if p.detail_extraction_success),
            "confidence_distribution": {
                "high_confidence": sum(1 for p in parishes if p.confidence_score >= 0.8),
                "medium_confidence": sum(1 for p in parishes if 0.5 <= p.confidence_score < 0.8),
                "low_confidence": sum(1 for p in parishes if p.confidence_score < 0.5),
            },
        },
        "data_completeness": {
            "names_present": sum(1 for p in parishes if p.name and len(p.name) > 2),
            "cities_present": sum(1 for p in parishes if p.city),
            "addresses_present": sum(1 for p in parishes if p.street_address or p.full_address or p.address),
            "phones_present": sum(1 for p in parishes if p.phone),
            "websites_present": sum(1 for p in parishes if p.website),
            "coordinates_present": sum(1 for p in parishes if p.latitude and p.longitude),
            "clergy_info_present": sum(1 for p in parishes if p.clergy_info),
        },
    }

    # Track extraction methods used
    for parish in parishes:
        method = parish.extraction_method
        analysis["extraction_methods"][method] = analysis["extraction_methods"].get(method, 0) + 1

    # Calculate percentages
    analysis["data_completeness_percentages"] = {
        f"{key}_percentage": (value / total_parishes * 100) for key, value in analysis["data_completeness"].items()
    }

    # Overall quality score
    basic_score = (
        (analysis["data_completeness"]["names_present"] + analysis["data_completeness"]["cities_present"])
        / (total_parishes * 2)
        * 100
    )

    enhanced_score = (
        (
            analysis["data_completeness"]["addresses_present"]
            + analysis["data_completeness"]["phones_present"]
            + analysis["data_completeness"]["coordinates_present"]
        )
        / (total_parishes * 3)
        * 100
    )

    analysis["parish_finder_quality_score"] = (basic_score + enhanced_score) / 2

    return analysis
