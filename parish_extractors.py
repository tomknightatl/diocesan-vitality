# -*- coding: utf-8 -*-
"""
Parish Extractor Implementations
Specialized extractors for different diocese website platforms and layouts.

This module contains:
- Diocese card extractor with detail page navigation
- Parish Finder extractor for eCatholic sites
- Table extractor for HTML tables
- Interactive map extractor for JavaScript-based maps
- Generic extractor as fallback
- Main processing function for diocese extraction
"""

# =============================================================================
# DEPENDENCIES AND IMPORTS
# =============================================================================

import gc
import time
import re
import subprocess
from typing import Dict, List, Optional
from datetime import datetime, timezone
from core.logger import get_logger
logger = get_logger(__name__)

# Web scraping
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import core components from the companion module
from parish_extraction_core import (
    BaseExtractor, ParishData,
    DioceseSitePattern,
    ParishListingType, DiocesePlatform, PatternDetector,
    setup_enhanced_driver, enhanced_safe_upsert_to_supabase, clean_parish_name_and_extract_address
)

# =============================================================================
# CHROME INSTALLATION FOR GOOGLE COLAB
# =============================================================================

def ensure_chrome_installed():
    """Ensures Chrome is installed in the Colab environment."""
    try:
        # Check if Chrome is already available
        result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Chrome is already installed and available.")
            return True

        logger.info("🔧 Chrome not found. Installing Chrome for Selenium...")

        # Install Chrome
        # Using subprocess.run for better control and error handling
        subprocess.run(['apt-get', 'update'], capture_output=True, text=True, check=True)
        subprocess.run(['wget', '-q', '-O', '-', 'https://dl.google.com/linux/linux_signing_key.pub'], capture_output=True, text=True, check=True)
        subprocess.run(['apt-key', 'add', '-'], input=subprocess.run(['wget', '-q', '-O', '-', 'https://dl.google.com/linux/linux_signing_key.pub'], capture_output=True, text=True).stdout, capture_output=True, text=True, check=True)
        subprocess.run(['echo', "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main"], capture_output=True, text=True, check=True)
        subprocess.run(['sh', '-c', 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list'], capture_output=True, text=True, check=True)
        subprocess.run(['apt-get', 'update'], capture_output=True, text=True, check=True)
        subprocess.run(['apt-get', 'install', '-y', 'google-chrome-stable'], capture_output=True, text=True, check=True)

        # Verify installation
        result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ Chrome installed successfully: {result.stdout.strip()}")
            return True
        else:
            logger.error("❌ Chrome installation may have failed.")
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error during Chrome installation (subprocess failed): {e}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ Error during Chrome installation: {e}")
        return False

# =============================================================================
# ENHANCED DIOCESE CARD EXTRACTOR WITH DETAIL PAGE NAVIGATION
# =============================================================================

class EnhancedDiocesesCardExtractor(BaseExtractor):
    """Enhanced extractor that clicks on each parish card to get detailed information"""

    def __init__(self, pattern: DioceseSitePattern):
        super().__init__(pattern)
        self.detail_extraction_count = 0
        self.detail_extraction_errors = 0

    def extract(self, driver, soup: BeautifulSoup, url: str) -> List[ParishData]:
        parishes = []

        try:
            logger.info("    📍 Enhanced diocese card layout detected - extracting with detail pages")

            # Find all parish cards using the specific Salt Lake City structure
            parish_cards = soup.find_all('div', class_='col-lg location')
            logger.info(f"    📊 Found {len(parish_cards)} parish cards")

            for i, card in enumerate(parish_cards, 1):
                try:
                    logger.info(f"    🔄 Processing parish {i}/{len(parish_cards)}")
                    parish_data = self._extract_parish_from_card_with_details(card, url, driver, i)
                    if parish_data:
                        parishes.append(parish_data)
                        if parish_data.detail_extraction_success:
                            self.detail_extraction_count += 1
                        else:
                            self.detail_extraction_errors += 1
                except Exception as e:
                    logger.warning(f"    ⚠️ Error extracting from card {i}: {str(e)[:100]}...")
                    self.detail_extraction_errors += 1
                    continue

            logger.info(f"    📊 Summary: {self.detail_extraction_count} detailed extractions successful, {self.detail_extraction_errors} failed")

        except Exception as e:
            logger.error(f"    ⚠️ Enhanced diocese card extraction error: {str(e)[:100]}...")

        return parishes

    def _extract_parish_from_card_with_details(self, card, base_url: str, driver, card_number: int) -> Optional[ParishData]:
        """Extract parish data from a single card and navigate to detail page"""
        try:
            # Step 1: Extract basic information from the card
            card_link = card.find('a', class_='card')
            if not card_link:
                return None

            # Extract raw name from card title
            title_elem = card_link.find('h4', class_='card-title')
            if not title_elem:
                return None

            raw_name = self.clean_text(title_elem.get_text())
            if not raw_name or len(raw_name) < 3:
                return None

            # Use the new cleaning function to separate name and address components
            cleaned_data = clean_parish_name_and_extract_address(raw_name)
            name = cleaned_data["name"]
            street_address = cleaned_data["street_address"]
            city = cleaned_data["city"]
            state = cleaned_data["state"]
            zip_code = cleaned_data["zip_code"]
            full_address = cleaned_data["full_address"]
            distance_miles = cleaned_data["distance_miles"]

            # Skip non-parish entries based on the cleaned name
            skip_terms = [
                'no parish registration', 'contact', 'chancery', 'pastoral center',
                'tv mass', 'directory', 'finder', 'diocese', 'bishop', 'office'
            ]
            if any(term in name.lower() for term in skip_terms):
                return None

            # Extract city from card body (if not already extracted by clean_parish_name_and_extract_address)
            if not city:
                card_body = card_link.find('div', class_='card-body')
                if card_body:
                    body_text = card_body.get_text()
                    lines = [line.strip() for line in body_text.split('\n') if line.strip()]

                    # The city is usually the second line (after the parish name)
                    if len(lines) >= 2:
                        city_line = lines[1]
                        if city_line and not city_line.startswith('Learn More'):
                            city = self.clean_text(city_line)

            # Extract state from city if present (format: "City, ST")
            if city and not state and ', ' in city:
                city_parts = city.split(', ')
                if len(city_parts) == 2:
                    city = city_parts[0].strip()
                    state = city_parts[1].strip()

            # Extract parish detail URL
            parish_detail_url = None
            href = card_link.get('href')
            if href:
                if href.startswith('/'):
                    parish_detail_url = urljoin(base_url, href)
                else:
                    parish_detail_url = href

            # Step 2: Navigate to detail page and extract additional information
            detailed_info = self._extract_details_from_parish_page(driver, parish_detail_url, name)

            # Step 3: Create comprehensive parish data object
            parish_data = ParishData(
                name=name,
                city=city,
                state=state,
                street_address=street_address,
                full_address=full_address,
                zip_code=zip_code,
                distance_miles=distance_miles,
                parish_detail_url=parish_detail_url,
                confidence_score=0.9,
                extraction_method="enhanced_diocese_card_extraction"
            )

            # Add detailed information if extraction was successful
            if detailed_info['success']:
                parish_data.street_address = parish_data.street_address or detailed_info.get('street_address')
                parish_data.full_address = parish_data.full_address or detailed_info.get('full_address')
                parish_data.zip_code = parish_data.zip_code or detailed_info.get('zip_code')
                parish_data.phone = detailed_info.get('phone')
                parish_data.website = detailed_info.get('website')
                parish_data.clergy_info = detailed_info.get('clergy_info')
                parish_data.service_times = detailed_info.get('service_times')
                parish_data.detail_extraction_success = True
                parish_data.confidence_score = 0.95
                logger.info(f"      ✅ {name}: Complete details extracted")
            else:
                parish_data.detail_extraction_success = False
                parish_data.detail_extraction_error = detailed_info.get('error')
                logger.warning(f"      ⚠️ {name}: Basic info only - {detailed_info.get('error', 'Unknown error')}")

            return parish_data

        except Exception as e:
            logger.warning(f"    ⚠️ Error parsing card {card_number}: {str(e)[:50]}...")
            return None

    def _extract_details_from_parish_page(self, driver, parish_url: str, parish_name: str) -> Dict:
        """Navigate to parish detail page and extract detailed information"""

        if not parish_url:
            return {'success': False, 'error': 'No detail URL available'}

        try:
            logger.info(f"      🔗 Navigating to: {parish_url}")

            # Navigate to the parish detail page
            driver.get(parish_url)
            # Wait for page content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Get the page source and parse it
            detail_html = driver.page_source
            detail_soup = BeautifulSoup(detail_html, 'html.parser')

            # Initialize result dictionary
            result = {
                'success': True,
                'street_address': None,
                'full_address': None,
                'zip_code': None,
                'phone': None,
                'website': None,
                'clergy_info': None,
                'service_times': None
            }

            # Extract contact information from the detail page
            self._extract_contact_info(detail_soup, result)
            self._extract_service_times(detail_soup, result)
            self._extract_clergy_info(detail_soup, result)

            return result

        except Exception as e:
            error_msg = f"Failed to extract details: {str(e)[:100]}"
            print(f"      ❌ {parish_name}: {error_msg}")
            return {'success': False, 'error': error_msg}

    def _extract_contact_info(self, soup: BeautifulSoup, result: Dict):
        """Extract contact information from parish detail page"""
        try:
            # Look for contact info section
            contact_sections = soup.find_all(['div', 'section'], class_=re.compile(r'contact', re.I))
            fa_ul_sections = soup.find_all('ul', class_='fa-ul')
            all_contact_sections = contact_sections + fa_ul_sections

            for section in all_contact_sections:
                text_content = section.get_text()

                # Extract phone number
                if not result['phone']:
                    phone_links = section.find_all('a', href=re.compile(r'^tel:'))
                    if phone_links:
                        phone = phone_links[0].get_text().strip()
                        result['phone'] = self.clean_text(phone)
                    else:
                        phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text_content)
                        if phone_match:
                            result['phone'] = phone_match.group()

                # Extract website
                if not result['website']:
                    website_links = section.find_all('a', href=re.compile(r'^http'))
                    for link in website_links:
                        href = link.get('href', '')
                        if not any(skip in href.lower() for skip in ['facebook', 'twitter', 'instagram', 'dioslc.org']):
                            result['website'] = href
                            break

                # Extract address
                if not result['full_address']:
                    address_lines = []
                    list_items = section.find_all('li')

                    for li in list_items:
                        li_text = li.get_text().strip()
                        if re.search(r'\d+.*(?:street|st|avenue|ave|road|rd|drive|dr|way|lane|ln|boulevard|blvd)', li_text, re.I):
                            address_lines.append(li_text)
                        elif re.search(r'\d+\s+[A-Za-z]', li_text) and ',' in li_text:
                            address_lines.append(li_text)

                    if address_lines:
                        full_address = address_lines[0]
                        result['full_address'] = full_address
                        self._parse_address_components(full_address, result)

        except Exception as e:
            logger.warning(f"        ⚠️ Error extracting contact info: {str(e)[:50]}")

    def _parse_address_components(self, full_address: str, result: Dict):
        """Parse full address into street address and zip code"""
        try:
            # Extract zip code (5 digits, possibly followed by 4 more)
            zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', full_address)
            if zip_match:
                result['zip_code'] = zip_match.group(1)

            # Extract street address (everything before the first comma, or before city/state)
            address_parts = full_address.split(',')
            if len(address_parts) > 0:
                potential_street = address_parts[0].strip()
                if re.search(r'\d+', potential_street):
                    result['street_address'] = potential_street

        except Exception as e:
            logger.warning(f"        ⚠️ Error parsing address: {str(e)[:30]}")

    def _extract_service_times(self, soup: BeautifulSoup, result: Dict):
        """Extract service times from parish detail page"""
        try:
            service_sections = soup.find_all(['div', 'section'],
                                           string=re.compile(r'service.*times|mass.*times|masses|schedule', re.I))

            service_headers = soup.find_all(['h3', 'h4'],
                                          string=re.compile(r'service.*times|mass.*times|masses|schedule', re.I))

            service_lists = []
            for header in service_headers:
                next_sibling = header.find_next_sibling(['ul', 'div'])
                if next_sibling:
                    service_lists.append(next_sibling)

            all_service_sections = service_sections + service_lists

            for section in all_service_sections:
                if section:
                    service_text = section.get_text()
                    lines = [line.strip() for line in service_text.split('\n') if line.strip()]
                    schedule_lines = [line for line in lines if len(line) > 10 and
                                    any(keyword in line.lower() for keyword in
                                        ['sunday', 'saturday', 'daily', 'mass', 'service', 'am', 'pm'])]

                    if schedule_lines:
                        result['service_times'] = '; '.join(schedule_lines[:5])
                        break

        except Exception as e:
            logger.warning(f"        ⚠️ Error extracting service times: {str(e)[:50]}")

    def _extract_clergy_info(self, soup: BeautifulSoup, result: Dict):
        """Extract clergy information from parish detail page"""
        try:
            clergy_sections = soup.find_all(['div', 'section'], class_=re.compile(r'clergy|pastor|priest', re.I))
            directory_cards = soup.find_all(['div'], class_=re.compile(r'directory|card', re.I))
            all_clergy_sections = clergy_sections + directory_cards

            clergy_info = []
            for section in all_clergy_sections:
                titles = section.find_all(['h4', 'h5'], class_=re.compile(r'title|name', re.I))
                for title in titles:
                    title_text = title.get_text().strip()
                    if any(clergy_word in title_text.lower() for clergy_word in
                           ['reverend', 'father', 'pastor', 'deacon', 'rev.', 'fr.', 'dcn.']):

                        role_elem = title.find_next_sibling(['p', 'div'])
                        role_text = role_elem.get_text().strip() if role_elem else ""

                        if role_text:
                            clergy_info.append(f"{title_text}: {role_text}")
                        else:
                            clergy_info.append(title_text)

            if clergy_info:
                result['clergy_info'] = '; '.join(clergy_info[:3])

        except Exception as e:
            logger.warning(f"        ⚠️ Error extracting clergy info: {str(e)[:50]}")

# =============================================================================
# PARISH FINDER EXTRACTOR FOR ECATHOLIC SITES
# =============================================================================

class ParishFinderExtractor(BaseExtractor):
    """Extractor for eCatholic Parish Finder interfaces (like Parma)"""

    def extract(self, driver, soup: BeautifulSoup, url: str) -> List[ParishData]:
        parishes = []

        try:
            logger.info("    📍 Parish finder interface detected")

            # Try different selectors for parish items
            parish_selectors = [
                "li.location.parishes",  # eCatholic specific
                "li.site",
                ".site",
                "li[data-latitude]",
                ".parish-item",
                "[class*='parish'][class*='location']",  # More specific for eCatholic
                "[class*='parish']"
            ]

            parish_elements = []
            for selector in parish_selectors:
                elements = soup.find_all(class_=lambda x: x and 'site' in x) if selector == "li.site" else soup.select(selector)
                if elements:
                    parish_elements = elements
                    logger.info(f"    📊 Found {len(parish_elements)} parish elements using {selector}")
                    break

            if not parish_elements:
                logger.warning("    ⚠️ No parish elements found")
                return parishes

            for i, element in enumerate(parish_elements, 1):
                try:
                    parish_data = self._extract_parish_from_finder_element(element, url, i)
                    if parish_data:
                        parishes.append(parish_data)
                        logger.info(f"      ✅ Extracted: {parish_data.name}")
                    else:
                        logger.warning(f"      ⚠️ Skipped element {i}: No valid parish data")

                except Exception as e:
                    logger.error(f"      ❌ Error processing element {i}: {str(e)[:50]}...")
                    continue

            logger.info(f"    📊 Successfully extracted {len(parishes)} parishes from parish finder")

        except Exception as e:
            logger.error(f"    ❌ Parish finder extraction error: {str(e)[:100]}...")

        return parishes

    def _extract_parish_from_finder_element(self, element, base_url: str, element_num: int) -> Optional[ParishData]:
        """Extract parish data from a single parish finder element with enhanced detail extraction"""
        try:
            # Extract parish name - handle eCatholic specific structure
            name = None
            
            # First try eCatholic specific selectors
            title_span = element.find('span', {'data-bind': lambda x: x and 'title' in x})
            if title_span:
                name = self.clean_text(title_span.get_text())
            
            # Fallback to standard selectors
            if not name:
                name_selectors = ['.name', '.parish-name', 'h3', 'h4', '.title', 'span']
                for selector in name_selectors:
                    name_elem = element.select_one(selector)
                    if name_elem:
                        name = self.clean_text(name_elem.get_text())
                        break

            # Another fallback - extract from the anchor text if present
            if not name:
                anchor = element.find('a')
                if anchor:
                    # Try to get text from first span in anchor
                    first_span = anchor.find('span')
                    if first_span:
                        name = self.clean_text(first_span.get_text())

            # Use the new cleaning function to separate name and address components
            cleaned_data = clean_parish_name_and_extract_address(name)
            clean_name = cleaned_data["name"]
            base_street_address = cleaned_data["street_address"]
            base_city = cleaned_data["city"]
            base_state = cleaned_data["state"]
            base_zip_code = cleaned_data["zip_code"]
            base_full_address = cleaned_data["full_address"]
            distance_miles = cleaned_data["distance_miles"]

            # Re-evaluate name after cleaning
            if not clean_name or len(clean_name) < 3:
                return None

            # Skip non-parish entries based on the cleaned name
            if any(skip_word in clean_name.lower() for skip_word in
                   ['finder', 'directory', 'map', 'search', 'filter']):
                return None

            # Enhanced data extraction from expandable detail sections
            enhanced_data = self._extract_enhanced_parish_details(element)
            
            # Merge base data with enhanced data (enhanced takes priority)
            street_address = enhanced_data.get('street_address') or base_street_address
            city = enhanced_data.get('city') or base_city
            state = enhanced_data.get('state') or base_state
            zip_code = enhanced_data.get('zip_code') or base_zip_code
            full_address = enhanced_data.get('full_address') or base_full_address
            phone = enhanced_data.get('phone')
            fax = enhanced_data.get('fax')
            website = enhanced_data.get('website')
            
            # Use enhanced address as primary, fallback to base
            address = street_address or base_street_address

            # For parish finder, coordinates might be in data attributes
            lat = lng = None
            if element:
                lat_attrs = ['data-lat', 'data-latitude', 'lat', 'latitude']
                lng_attrs = ['data-lng', 'data-longitude', 'data-lon', 'lng', 'longitude', 'lon']
                
                for attr in lat_attrs:
                    if element.get(attr):
                        try:
                            lat = float(element.get(attr))
                            break
                        except (ValueError, TypeError):
                            continue
                            
                for attr in lng_attrs:
                    if element.get(attr):
                        try:
                            lng = float(element.get(attr))
                            break
                        except (ValueError, TypeError):
                            continue

            return ParishData(
                name=clean_name,
                city=city,
                address=address,
                street_address=street_address,
                state=state,
                zip_code=zip_code,
                full_address=full_address,
                phone=phone,
                website=website,
                latitude=float(lat) if lat else None,
                longitude=float(lng) if lng else None,
                distance_miles=distance_miles,
                confidence_score=0.85,  # Increased confidence with enhanced data
                extraction_method="parish_finder_enhanced_extraction"
            )

        except Exception as e:
            logger.warning(f"        ⚠️ Error parsing parish element {element_num}: {str(e)[:50]}...")
            return None

    def _extract_enhanced_parish_details(self, soup_element) -> Dict:
        """Extract enhanced parish details from expandable detail sections"""
        enhanced_data = {}
        
        try:
            # Look for the expandable detail container
            detail_section = soup_element.find('div', class_='mapLocationDetail')
            if not detail_section:
                return enhanced_data
            
            # Get all text content from the detail section
            detail_text = detail_section.get_text() if detail_section else ""
            
            if detail_text:
                # Extract phone number with more comprehensive patterns
                phone_patterns = [
                    r'Phone:\s*(\(?(?:\d{3})\)?\s*[-.\s]?\d{3}[-.\s]?\d{4})',
                    r'P:\s*(\(?(?:\d{3})\)?\s*[-.\s]?\d{3}[-.\s]?\d{4})',
                    r'\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b'
                ]
                
                for pattern in phone_patterns:
                    phone_match = re.search(pattern, detail_text, re.IGNORECASE)
                    if phone_match:
                        phone_raw = phone_match.group(1).strip()
                        # Standardize phone format
                        phone_clean = re.sub(r'[^\d]', '', phone_raw)
                        if len(phone_clean) == 10:
                            enhanced_data['phone'] = f"({phone_clean[:3]}) {phone_clean[3:6]}-{phone_clean[6:]}"
                        break

                # Extract fax number
                fax_match = re.search(r'Fax:\s*(\(?(?:\d{3})\)?\s*[-.\s]?\d{3}[-.\s]?\d{4})', detail_text, re.IGNORECASE)
                if fax_match:
                    fax_raw = fax_match.group(1).strip()
                    fax_clean = re.sub(r'[^\d]', '', fax_raw)
                    if len(fax_clean) == 10:
                        enhanced_data['fax'] = f"({fax_clean[:3]}) {fax_clean[3:6]}-{fax_clean[6:]}"

                # Extract website from detail section
                website_link = detail_section.find('a')
                if website_link and website_link.get('href'):
                    href = website_link.get('href').strip()
                    if href.startswith('http') or href.startswith('www'):
                        enhanced_data['website'] = href

                # Extract enhanced address with zip code
                # Look for complete address patterns in the detail text
                address_patterns = [
                    # Full address with zip: "123 Main St City, ST 12345"
                    r'(\d+\s+[A-Za-z0-9\s\.\-]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Way|Lane|Ln|Boulevard|Blvd|Court|Ct|Plaza|Pl|Terrace|Ter|Circle|Cir|Parkway|Pkwy|Highway|Hwy|Route|Rte)\.?,?\s*[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)',
                    # Address with zip on new line: "123 Main St\nCity, ST 12345"
                    r'(\d+\s+[A-Za-z0-9\s\.\-]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Way|Lane|Ln|Boulevard|Blvd|Court|Ct|Plaza|Pl|Terrace|Ter|Circle|Cir|Parkway|Pkwy|Highway|Hwy|Route|Rte)\.?)\s*\n?\s*([A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)'
                ]
                
                for pattern in address_patterns:
                    addr_match = re.search(pattern, detail_text, re.IGNORECASE | re.MULTILINE)
                    if addr_match:
                        if len(addr_match.groups()) == 1:
                            # Single group - complete address
                            full_addr = addr_match.group(1).strip()
                            enhanced_data['full_address'] = full_addr
                            
                            # Parse components
                            self._parse_address_components(full_addr, enhanced_data)
                        else:
                            # Two groups - street + city/state/zip
                            street = addr_match.group(1).strip()
                            city_state_zip = addr_match.group(2).strip()
                            full_addr = f"{street} {city_state_zip}"
                            enhanced_data['full_address'] = full_addr
                            enhanced_data['street_address'] = street
                            
                            # Parse city, state, zip from second group
                            self._parse_city_state_zip(city_state_zip, enhanced_data)
                        break

        except Exception as e:
            logger.debug(f"Error extracting enhanced details: {e}")
        
        return enhanced_data

    def _parse_address_components(self, full_address: str, enhanced_data: Dict):
        """Parse address components from full address string"""
        # City, State, Zip pattern
        city_state_zip_match = re.search(r'(.+?),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)$', full_address)
        if city_state_zip_match:
            before_city = city_state_zip_match.group(1)
            state = city_state_zip_match.group(2)
            zip_code = city_state_zip_match.group(3)
            
            # Split before_city into street and city
            parts = before_city.strip().split()
            if len(parts) >= 4:  # At least "123 Main St CityName"
                # Find where street ends and city begins (look for street suffixes)
                street_suffixes = ['Street', 'St', 'Avenue', 'Ave', 'Road', 'Rd', 'Drive', 'Dr', 'Way', 'Lane', 'Ln', 'Boulevard', 'Blvd', 'Court', 'Ct']
                
                for i, part in enumerate(parts):
                    if any(suffix.lower() == part.lower() for suffix in street_suffixes):
                        street_address = ' '.join(parts[:i+1])
                        city = ' '.join(parts[i+1:])
                        enhanced_data['street_address'] = street_address
                        enhanced_data['city'] = city
                        break
                else:
                    # No clear street suffix, assume last 1-2 words are city
                    if len(parts) >= 2:
                        enhanced_data['street_address'] = ' '.join(parts[:-1])
                        enhanced_data['city'] = parts[-1]
            
            enhanced_data['state'] = state
            enhanced_data['zip_code'] = zip_code

    def _parse_city_state_zip(self, city_state_zip: str, enhanced_data: Dict):
        """Parse city, state, and zip from city/state/zip string"""
        match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)$', city_state_zip)
        if match:
            enhanced_data['city'] = match.group(1).strip()
            enhanced_data['state'] = match.group(2).strip()
            enhanced_data['zip_code'] = match.group(3).strip()

    def _extract_from_site_info(self, name: str, city: str, site_info, element, base_url: str) -> Optional[ParishData]:
        """Extract detailed information from siteInfo section"""
        try:
            main_section = site_info.find('div', class_='main')
            if not main_section:
                return None

            # Extract address from title section
            title_section = main_section.find('div', class_='title')
            address = None
            phone = None

            if title_section:
                address_div = title_section.find('div', class_='address')
                if address_div:
                    address = self.clean_text(address_div.get_text())

                phone_holder = title_section.find('div', class_='phoneFaxHolder')
                if phone_holder:
                    phone_span = phone_holder.find('span', class_='phone')
                    if phone_span:
                        phone = self.clean_text(phone_span.get_text())

            # Extract website from linkContainer
            website = None
            link_container = main_section.find('div', class_='linkContainer')
            if link_container:
                url_link = link_container.find('a', class_='urlLink')
                if url_link:
                    website = url_link.get('href')

            # Extract coordinates from the main element
            latitude = None
            longitude = None

            if element.get('data-latitude'):
                try:
                    latitude = float(element.get('data-latitude'))
                except (ValueError, TypeError):
                    pass

            if element.get('data-longitude'):
                try:
                    longitude = float(element.get('data-longitude'))
                except (ValueError, TypeError):
                    pass

            # Extract detailed info from extendedInfo if available
            clergy_info = None
            extended_info = site_info.find('div', class_='extendedInfo')
            if extended_info:
                details_div = extended_info.find('div', class_='details')
                if details_div:
                    details_text = details_div.get_text()
                    if details_text and len(details_text.strip()) > 10:
                        clergy_info = self.clean_text(details_text)

            return ParishData(
                name=name,
                city=city,
                address=address,
                phone=phone,
                website=website,
                latitude=latitude,
                longitude=longitude,
                clergy_info=clergy_info,
                confidence_score=0.9,
                extraction_method="parish_finder_detailed_extraction",
                detail_extraction_success=True if (address or phone or website or clergy_info) else False
            )

        except Exception as e:
            logger.warning(f"        ⚠️ Error extracting from siteInfo: {str(e)[:50]}...")
            return None

# =============================================================================
# TABLE EXTRACTOR FOR HTML TABLES
# =============================================================================

class TableExtractor(BaseExtractor):
    """Extractor for HTML table-based parish listings"""

    def extract(self, driver, soup: BeautifulSoup, url: str) -> List[ParishData]:
        parishes = []

        try:
            tables = soup.find_all('table')

            for table in tables:
                table_text = table.get_text().lower()
                if any(keyword in table_text for keyword in ['parish', 'church', 'name', 'address']):
                    rows = table.find_all('tr')[1:]  # Skip header row

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 1:
                            parish_data = self._extract_parish_from_table_row(cells, url)
                            if parish_data:
                                parishes.append(parish_data)

        except Exception as e:
            logger.error(f"    ⚠️ Table extraction error: {str(e)[:100]}...")

        return parishes

    def _extract_parish_from_table_row(self, cells, base_url: str) -> Optional[ParishData]:
        """Extract parish data from table row cells"""
        if not cells:
            return None

        # First cell usually contains the name
        name = self.clean_text(cells[0].get_text())
        if not name or len(name) < 3:
            return None

        # Use the new cleaning function to separate name and address components
        cleaned_data = clean_parish_name_and_extract_address(name)
        clean_name = cleaned_data["name"]
        street_address = cleaned_data["street_address"]
        city = cleaned_data["city"]
        state = cleaned_data["state"]
        zip_code = cleaned_data["zip_code"]
        full_address = cleaned_data["full_address"]
        distance_miles = cleaned_data["distance_miles"]

        # Re-evaluate name after cleaning
        if not clean_name or len(clean_name) < 3:
            return None

        # Extract other information from remaining cells
        address = None
        phone = None
        website = None

        for i, cell in enumerate(cells[1:], 1):
            cell_text = cell.get_text()

            # Check for phone pattern
            if self.extract_phone(cell_text):
                phone = self.extract_phone(cell_text)

            # Check for address pattern
            elif re.search(r'\d+.*(?:street|st|avenue|ave|road|rd|drive|dr)', cell_text, re.I):
                address = self.clean_text(cell_text)

            # Check for website
            link = cell.find('a')
            if link and link.get('href', '').startswith('http'):
                website = link.get('href')

            # If it looks like a city (short text, no numbers)
            elif len(cell_text.strip()) < 30 and not re.search(r'\d', cell_text) and len(cell_text.strip()) > 2:
                city = self.clean_text(cell_text)

        return ParishData(
            name=clean_name,
            address=address,
            city=city,
            street_address=street_address,
            state=state,
            zip_code=zip_code,
            full_address=full_address,
            phone=phone,
            website=website,
            distance_miles=distance_miles,
            confidence_score=0.85,
            extraction_method="table_extraction"
        )

# =============================================================================
# IMPROVED INTERACTIVE MAP EXTRACTOR
# =============================================================================

class ImprovedInteractiveMapExtractor(BaseExtractor):
    """Improved extractor for JavaScript-powered maps with better error handling"""

    def extract(self, driver, soup: BeautifulSoup, url: str) -> List[ParishData]:
        parishes = []

        try:
            # Try to find map containers
            map_selectors = [
                "#map", ".map", ".parish-map", ".church-map",
                "[id*='map']", "[class*='map']",
                "#parish-finder", ".parish-finder"
            ]

            map_found = False
            for selector in map_selectors:
                try:
                    WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    map_found = True
                    logger.info(f"    📍 Found map container: {selector}")
                    break
                except:
                    continue

            if not map_found:
                logger.info(f"    ℹ️ No map container found, trying direct JS extraction...")

            # Method 1: Extract from JavaScript variables
            parishes.extend(self._extract_from_js_variables(driver))

            # Method 2: Look for parish data in script tags
            if not parishes:
                parishes.extend(self._extract_from_script_tags(soup))

            # Method 3: Extract from map markers
            if not parishes and map_found:
                parishes.extend(self._extract_from_markers(driver))

        except Exception as e:
            print(f"    ℹ️ Map extraction completed with info: {str(e)[:100]}...")

        return parishes

    def _extract_from_script_tags(self, soup: BeautifulSoup) -> List[ParishData]:
        """Extract parish data from script tags containing JSON"""
        parishes = []

        try:
            script_tags = soup.find_all('script')

            for script in script_tags:
                if not script.string:
                    continue

                script_content = script.string

                # Look for JSON-like data containing parish information
                if any(keyword in script_content.lower() for keyword in
                       ['parish', 'church', 'location', 'marker']):

                    # Try to extract JSON objects
                    import json

                    # Look for common patterns
                    patterns = [
                        r'parishes\s*[:=]\s*(\[.*?\])',
                        r'locations\s*[:=]\s*(\[.*?\])',
                        r'markers\s*[:=]\s*(\[.*?\])',
                        r'churches\s*[:=]\s*(\[.*?\])'
                    ]

                    for pattern in patterns:
                        matches = re.findall(pattern, script_content, re.DOTALL)
                        for match in matches:
                            try:
                                data = json.loads(match)
                                if isinstance(data, list):
                                    for item in data:
                                        parish = self._parse_js_parish_object(item)
                                        if parish:
                                            parishes.append(parish)
                            except:
                                continue

                        if parishes:
                            break

                if parishes:
                    break

        except Exception as e:
            print(f"    ℹ️ Script tag extraction info: {str(e)[:50]}...")

        return parishes

    def _extract_from_js_variables(self, driver) -> List[ParishData]:
        """Extract from common JavaScript variable names"""
        parishes = []

        # Common variable names
        js_vars = [
            "parishes", "parishData", "locations", "markers", "churchData",
            "parishList", "churches", "mapData", "data", "items",
            "parishInfo", "churchInfo", "mapMarkers", "points"
        ]

        for var_name in js_vars:
            try:
                js_data = driver.execute_script(f"""
                    try {{
                        return window.{var_name};
                    }} catch(e) {{
                        return null;
                    }}
                """ ) # Fixed f-string braces

                if js_data and isinstance(js_data, list) and len(js_data) > 0:
                    print(f"    📊 Found data in window.{var_name}: {len(js_data)} items")

                    for item in js_data:
                        parish = self._parse_js_parish_object(item)
                        if parish:
                            parishes.append(parish)

                    if parishes:
                        break

            except Exception as e:
                continue

        return parishes

    def _parse_js_parish_object(self, data: Dict) -> Optional[ParishData]:
        """Parse parish data from JavaScript object"""
        if not isinstance(data, dict):
            return None

        # Field mapping for name
        name = None
        for field in ['name', 'title', 'parishName', 'churchName', 'parish_name',
                      'church_name', 'label', 'text', 'Name', 'Title']:
            if field in data and data[field]:
                name = str(data[field]).strip()
                break

        if not name or len(name) < 3:
            return None

        # Use the new cleaning function to separate name and address components
        cleaned_data = clean_parish_name_and_extract_address(name)
        clean_name = cleaned_data["name"]
        street_address = cleaned_data["street_address"]
        city = cleaned_data["city"] or data.get('city', data.get('location', data.get('City'))) # Prioritize cleaned city, then data
        state = cleaned_data["state"]
        zip_code = cleaned_data["zip_code"]
        full_address = cleaned_data["full_address"]
        distance_miles = cleaned_data["distance_miles"]


        # Skip non-parish entries based on the cleaned name
        if any(skip_word in clean_name.lower() for skip_word in
               ['finder', 'directory', 'map', 'search', 'filter']):
            return None

        # Field mapping for other data
        address = None
        for field in ['address', 'location', 'fullAddress', 'street', 'addr']:
            if field in data and data[field]:
                address = str(data[field]).strip()
                break

        phone = None
        for field in ['phone', 'telephone', 'phoneNumber', 'tel', 'Phone']:
            if field in data and data[field]:
                phone = str(data[field]).strip()
                break

        website = None
        for field in ['website', 'url', 'link', 'web', 'Website', 'URL']:
            if field in data and data[field]:
                website = str(data[field]).strip()
                break

        # Coordinates
        lat = data.get('lat', data.get('latitude', data.get('Lat')))
        lng = data.get('lng', data.get('longitude', data.get('lon', data.get('Lng'))))

        return ParishData(
            name=clean_name,
            city=city,
            address=address,
            street_address=street_address,
            state=state,
            zip_code=zip_code,
            full_address=full_address,
            phone=phone,
            website=website,
            latitude=float(lat) if lat else None,
            longitude=float(lng) if lng else None,
            distance_miles=distance_miles,
            confidence_score=0.8,
            extraction_method="improved_js_extraction"
        )

    def _extract_from_markers(self, driver) -> List[ParishData]:
        """Extract by clicking map markers"""
        parishes = []

        try:
            # Marker selectors
            marker_selectors = [
                ".marker", ".leaflet-marker", ".map-marker",
                "[class*='marker']", ".gm-style-iw", ".mapboxgl-marker"
            ]

            markers = []
            for selector in marker_selectors:
                try:
                    found_markers = driver.find_elements(By.CSS_SELECTOR, selector)
                    if found_markers:
                        markers = found_markers
                        print(f"    📍 Found {len(markers)} markers using {selector}")
                        break
                except:
                    continue

            if not markers:
                print(f"    ℹ️ No clickable markers found")
                return parishes

            # Limit markers to avoid timeout
            for i, marker in enumerate(markers[:5]):
                try:
                    # Scroll marker into view
                    driver.execute_script("arguments[0].scrollIntoView(true);", marker)
                    # Wait for scroll to complete
                    WebDriverWait(driver, 3).until(
                        lambda d: d.execute_script("return arguments[0].getBoundingClientRect().top < window.innerHeight;", marker)
                    )

                    # Click marker
                    driver.execute_script("arguments[0].click();", marker)
                    # Wait for potential popup or content change
                    WebDriverWait(driver, 5).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, ".popup, .info-window, .marker-popup")) > 0 or True
                    )

                    # Look for popup content
                    popup_selectors = [
                        ".popup", ".info-window", ".mapboxgl-popup",
                        ".leaflet-popup", ".gm-style-iw-d"
                    ]

                    popup_text = None
                    for popup_selector in popup_selectors:
                        try:
                            popup = driver.find_element(By.CSS_SELECTOR, popup_selector)
                            popup_text = popup.text
                            break
                        except:
                            continue

                    if popup_text and len(popup_text) > 10:
                        parish_data = self._parse_popup_content(popup_text)
                        if parish_data:
                            parishes.append(parish_data)

                except Exception as e:
                    continue

        except Exception as e:
            print(f"    ℹ️ Marker extraction completed: {str(e)[:50]}...")

        return parishes

    def _parse_popup_content(self, popup_text: str) -> Optional[ParishData]:
        """Parse parish information from popup text"""
        lines = [line.strip() for line in popup_text.split('\n') if line.strip()]

        if not lines:
            return None

        raw_name = lines[0]  # First line is usually the name

        # Use the new cleaning function to separate name and address components
        cleaned_data = clean_parish_name_and_extract_address(raw_name)
        name = cleaned_data["name"]
        street_address = cleaned_data["street_address"]
        city = cleaned_data["city"]
        state = cleaned_data["state"]
        zip_code = cleaned_data["zip_code"]
        full_address = cleaned_data["full_address"]
        distance_miles = cleaned_data["distance_miles"]

        # Skip if it doesn't look like a parish name (based on cleaned name)
        if not any(indicator in name.lower() for indicator in
                   ['parish', 'church', 'st.', 'saint', 'our lady', 'holy', 'cathedral']):
            return None

        address = None
        phone = None

        # Look for address and phone in remaining lines
        for line in lines[1:]:
            if self.extract_phone(line):
                phone = self.extract_phone(line)
            elif re.search(r'\d+.*(?:street|st|avenue|ave|road|rd|drive|dr)', line, re.I):
                address = line

        return ParishData(
            name=name,
            address=address,
            street_address=street_address,
            city=city,
            state=state,
            zip_code=zip_code,
            full_address=full_address,
            phone=phone,
            distance_miles=distance_miles,
            confidence_score=0.6,
            extraction_method="marker_popup_extraction"
        )

# =============================================================================
# IMPROVED GENERIC EXTRACTOR
# =============================================================================

class ImprovedGenericExtractor(BaseExtractor):
    """Improved generic extractor as fallback"""

    def extract(self, driver, soup: BeautifulSoup, url: str) -> List[ParishData]:
        parishes = []

        try:
            print("    🔍 Using improved generic extraction...")

            # Look for common parish container patterns
            selectors = [
                "[class*='parish']",
                "[class*='church']",
                "[class*='location']",
                "article",
                ".entry",
                "[id*='parish']"
            ]

            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    print(f"      📊 Found {len(elements)} elements with {selector}")

                    for element in elements[:20]:  # Limit to prevent timeout
                        parish_data = self._extract_parish_from_generic_element(element, url)
                        if parish_data:
                            parishes.append(parish_data)

                    if parishes:
                        break

        except Exception as e:
            print(f"    ⚠️ Generic extraction error: {str(e)[:100]}...")

        return parishes

    def _extract_parish_from_generic_element(self, element, base_url: str) -> Optional[ParishData]:
        """Extract parish data from generic element"""
        try:
            # Look for name in various heading tags
            name = None
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
                heading = element.find(tag)
                if heading:
                    name = self.clean_text(heading.get_text())
                    if name and len(name) > 2:
                        break

            if not name:
                # Try getting first significant text
                text_content = element.get_text()
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                if lines:
                    name = lines[0]

            # Use the new cleaning function to separate name and address components
            cleaned_data = clean_parish_name_and_extract_address(name)
            clean_name = cleaned_data["name"]
            street_address = cleaned_data["street_address"]
            city = cleaned_data["city"]
            state = cleaned_data["state"]
            zip_code = cleaned_data["zip_code"]
            full_address = cleaned_data["full_address"]
            distance_miles = cleaned_data["distance_miles"]

            # Re-evaluate name after cleaning
            if not clean_name or len(clean_name) < 3:
                return None

            # Skip non-parish entries based on the cleaned name
            if not any(indicator in clean_name.lower() for indicator in
                      ['parish', 'church', 'st.', 'saint', 'our lady', 'holy', 'cathedral']):
                return None

            # Extract other information (phone, website) from the original element_text
            # as they might be separate from the name/address block
            phone = self.extract_phone(element_text)

            website = None
            links = element.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href.startswith('http') and not any(skip in href.lower()
                                                     for skip in ['facebook', 'twitter', 'instagram']):
                    website = href
                    break

            return ParishData(
                name=clean_name,
                street_address=street_address,
                city=city,
                state=state,
                zip_code=zip_code,
                full_address=full_address,
                phone=phone,
                website=website,
                distance_miles=distance_miles,
                confidence_score=0.4,
                extraction_method="improved_generic_extraction"
            )

        except Exception as e:
            return None

# =============================================================================
# MAIN PROCESSING FUNCTION
# =============================================================================

def process_diocese_with_detailed_extraction(diocese_info: Dict, driver, max_parishes: int = 0) -> Dict:
    """
    Enhanced processing function that extracts detailed parish information
    by navigating to individual parish detail pages
    """

    diocese_url = diocese_info['url']
    diocese_name = diocese_info['name']
    parish_directory_url = diocese_info['parish_directory_url']

    print(f"\n{'='*60}")
    print(f"🔍 ENHANCED DETAILED PROCESSING: {diocese_name}")
    print(f"📍 Main URL: {diocese_url}")
    print(f"📂 Parish Directory URL: {parish_directory_url}")
    print(f"{'='*60}")

    result = {
        'diocese_name': diocese_name,
        'diocese_url': diocese_url,
        'parish_directory_url': parish_directory_url,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'pattern_detected': None,
        'parishes_found': [],
        'success': False,
        'extraction_methods_used': [],
        'processing_time': 0,
        'errors': [],
        'detail_extraction_stats': {
            'attempted': 0,
            'successful': 0,
            'failed': 0,
            'success_rate': 0.0
        },
        'field_extraction_stats': {
            'addresses_extracted': 0,
            'phones_extracted': 0,
            'websites_extracted': 0,
            'zip_codes_extracted': 0,
            'clergy_info_extracted': 0,
            'service_times_extracted': 0
        }
    }

    start_time = time.time()

    try:
        # Step 1: Load the parish directory page
        print("  📥 Loading parish directory page...")
        driver.get(parish_directory_url)
        # Wait for JavaScript content to load - check for common parish directory elements
        try:
            WebDriverWait(driver, 15).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, 
                    "li.site, .parish-item, .parish-card, .location, table tr, .finder-result")) > 0
            )
        except:
            # Fallback: wait for body and give JS a moment
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(1)  # Minimal fallback delay

        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')

        # Step 2: Detect pattern
        print("  🔍 Detecting website pattern...")
        detector = PatternDetector()
        pattern = detector.detect_pattern(html_content, parish_directory_url)
        
        # Clean up detector after pattern detection
        del detector

        result['pattern_detected'] = {
            'platform': pattern.platform.value,
            'listing_type': pattern.listing_type.value,
            'confidence': pattern.confidence_score,
            'extraction_method': pattern.extraction_method,
            'javascript_required': pattern.javascript_required,
            'notes': pattern.notes
        }

        print(f"    📋 Platform: {pattern.platform.value}")
        print(f"    📊 Listing Type: {pattern.listing_type.value}")
        print(f"    🎯 Confidence: {pattern.confidence_score:.2f}")
        print(f"    ⚙️ Method: {pattern.extraction_method}")

        # Step 3: Extract parishes with detailed information
        parishes = []

        # Try extractors in order of specificity
        extractors_to_try = []

        # Primary extractor based on detected pattern
        if pattern.listing_type == ParishListingType.PARISH_FINDER:
            extractors_to_try.append(('ParishFinderExtractor', ParishFinderExtractor(pattern)))
        elif pattern.listing_type == ParishListingType.DIOCESE_CARD_LAYOUT:
            extractors_to_try.append(('EnhancedDiocesesCardExtractor', EnhancedDiocesesCardExtractor(pattern)))
        elif pattern.listing_type == ParishListingType.STATIC_TABLE:
            extractors_to_try.append(('TableExtractor', TableExtractor(pattern)))
        elif pattern.listing_type == ParishListingType.INTERACTIVE_MAP:
            extractors_to_try.append(('ImprovedInteractiveMapExtractor', ImprovedInteractiveMapExtractor(pattern)))

        # Add other extractors as fallbacks in priority order
        fallback_extractors = [
            ('ParishFinderExtractor', ParishFinderExtractor(pattern)),
            ('EnhancedDiocesesCardExtractor', EnhancedDiocesesCardExtractor(pattern)),
            ('TableExtractor', TableExtractor(pattern)),
            ('ImprovedInteractiveMapExtractor', ImprovedInteractiveMapExtractor(pattern)),
            ('ImprovedGenericExtractor', ImprovedGenericExtractor(pattern))
        ]

        # Add fallbacks that aren't already in the list
        for name, extractor in fallback_extractors:
            if not any(existing_name == name for existing_name, _ in extractors_to_try):
                extractors_to_try.append((name, extractor))

        # Try each extractor until we find parishes
        for extractor_name, extractor in extractors_to_try:
            try:
                print(f"  🔄 Trying {extractor_name}...")
                current_parishes = extractor.extract(driver, soup, parish_directory_url)

                if current_parishes:
                    parishes.extend(current_parishes)
                    result['extraction_methods_used'].append(extractor_name)
                    print(f"    ✅ {extractor_name} found {len(current_parishes)} parishes")

                    # If we found parishes with a specialized extractor, prefer those results
                    if extractor_name in ['ParishFinderExtractor', 'EnhancedDiocesesCardExtractor'] and len(current_parishes) > 3:
                        print(f"    🎯 Using {extractor_name} - stopping extraction")
                        break

                    # If we found a good number of parishes with any method, stop
                    if len(parishes) > 10:
                        break
                else:
                    print(f"    ⚠️ {extractor_name} found no parishes")

            except Exception as e:
                print(f"    ❌ {extractor_name} failed: {str(e)[:100]}")
                result['errors'].append(f"{extractor_name}: {str(e)[:100]}")

        # Step 4: Process results and calculate statistics
        if parishes:
            # Remove duplicates and validate
            unique_parishes = []
            seen_names = set()
            parish_count = 0

            for parish in parishes:
                if max_parishes != 0 and parish_count >= max_parishes:
                    break

                name_key = parish.name.lower().strip()
                if name_key not in seen_names and len(parish.name) > 2:
                    # Set the source URLs for each parish
                    parish.diocese_url = diocese_url
                    parish.parish_directory_url = parish_directory_url
                    unique_parishes.append(parish)
                    seen_names.add(name_key)
                    parish_count += 1

            result['parishes_found'] = unique_parishes
            result['success'] = True

            # Calculate detailed extraction statistics
            total_parishes = len(unique_parishes)
            detailed_successful = sum(1 for p in unique_parishes if p.detail_extraction_success)
            detailed_failed = sum(1 for p in unique_parishes if hasattr(p, 'detail_extraction_success') and not p.detail_extraction_success)

            result['detail_extraction_stats'] = {
                'attempted': total_parishes,
                'successful': detailed_successful,
                'failed': detailed_failed,
                'success_rate': (detailed_successful / total_parishes * 100) if total_parishes > 0 else 0
            }

            # Calculate field extraction statistics
            result['field_extraction_stats'] = {
                'addresses_extracted': sum(1 for p in unique_parishes if p.street_address or p.full_address or p.address),
                'phones_extracted': sum(1 for p in unique_parishes if p.phone),
                'websites_extracted': sum(1 for p in unique_parishes if p.website),
                'zip_codes_extracted': sum(1 for p in unique_parishes if p.zip_code),
                'clergy_info_extracted': sum(1 for p in unique_parishes if p.clergy_info),
                'service_times_extracted': sum(1 for p in unique_parishes if p.service_times)
            }

            print(f"  ✅ Found {len(unique_parishes)} unique parishes")
            print(f"  📊 Detail extraction: {detailed_successful}/{total_parishes} successful ({result['detail_extraction_stats']['success_rate']:.1f}%)")

            # Show field extraction summary
            field_stats = result['field_extraction_stats']
            print(f"  📋 Field extraction summary:")
            print(f"      📍 Addresses: {field_stats['addresses_extracted']}/{total_parishes}")
            print(f"      📞 Phones: {field_stats['phones_extracted']}/{total_parishes}")
            print(f"      🌐 Websites: {field_stats['websites_extracted']}/{total_parishes}")
            print(f"      📮 Zip Codes: {field_stats['zip_codes_extracted']}/{total_parishes}")
            print(f"      👥 Clergy Info: {field_stats['clergy_info_extracted']}/{total_parishes}")
            print(f"      ⏰ Service Times: {field_stats['service_times_extracted']}/{total_parishes}")

        else:
            print("  ❌ No parishes found with any extraction method")
            result['success'] = False

    except Exception as e:
        error_msg = str(e)
        result['errors'].append(error_msg)
        print(f"  ❌ Processing error: {error_msg}")

    finally:
        # Strategic memory cleanup after processing
        # Clean up large objects that accumulate during processing
        
        # Clear local variables that might hold references
        if 'soup' in locals():
            soup.decompose()  # Release BeautifulSoup memory
            del soup
        if 'html_content' in locals():
            del html_content
        if 'parishes' in locals():
            del parishes
        
        # Force garbage collection to free up memory
        collected = gc.collect()
        if collected > 0:
            logger.debug(f"  🧹 Freed {collected} objects during diocese processing cleanup")
            
        result['processing_time'] = time.time() - start_time
        print(f"  ⏱️ Completed in {result['processing_time']:.1f}s")

    return result

# =============================================================================
# MAIN EXECUTION EXAMPLE
# =============================================================================

if __name__ == "__main__":
    print("Parish Extractor Module Loaded")
    print("This module contains specialized extractors for different diocese website platforms.")
    print("\nAvailable extractors:")
    print("  - EnhancedDiocesesCardExtractor: For diocese card layouts with detail pages")
    print("  - ParishFinderExtractor: For eCatholic Parish Finder interfaces")
    print("  - TableExtractor: For HTML table-based listings")
    print("  - ImprovedInteractiveMapExtractor: For JavaScript-powered maps")
    print("  - ImprovedGenericExtractor: Generic fallback extractor")
    print("\nMain function:")
    print("  - process_diocese_with_detailed_extraction(): Process a diocese and extract parish data")
    print("\nTo use this module, import it and call the appropriate functions.")
    print("Example:")
    print("  from parish_extractors import process_diocese_with_detailed_extraction, setup_enhanced_driver")
    print("  driver = setup_enhanced_driver()")
    print("  result = process_diocese_with_detailed_extraction(diocese_info, driver)")
