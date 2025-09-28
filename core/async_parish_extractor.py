#!/usr/bin/env python3
"""
Async Parish Extractor with concurrent request handling.
High-performance parish detail extraction using asyncio and intelligent batching.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.async_driver import get_async_driver_pool
from core.logger import get_logger
from parish_extraction_core import ParishData, clean_parish_name_and_extract_address

logger = get_logger(__name__)


@dataclass
class ParishExtractionJob:
    """Represents a parish detail extraction job"""

    parish_name: str
    parish_url: str
    base_info: Dict[str, Any]
    priority: int = 1
    extraction_method: str = "standard"


class AsyncParishExtractor:
    """
    Async parish extractor with concurrent request handling and intelligent batching.
    Dramatically improves extraction performance while respecting rate limits.
    """

    def __init__(self, pool_size: int = 4, batch_size: int = 8):
        self.pool_size = pool_size
        self.batch_size = batch_size
        self.driver_pool = None
        self.extraction_stats = {
            "total_parishes": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "concurrent_requests": 0,
            "total_time": 0,
            "average_time_per_parish": 0,
        }

        logger.info(f"🚀 Async Parish Extractor initialized (pool: {pool_size}, batch: {batch_size})")

    async def initialize(self):
        """Initialize the async driver pool"""
        self.driver_pool = await get_async_driver_pool(self.pool_size)
        logger.info("✅ Async Parish Extractor ready for concurrent extraction")

    async def extract_parish_details_concurrent(
        self, parishes: List[ParishData], diocese_name: str, max_concurrent: int = None
    ) -> List[ParishData]:
        """
        Extract detailed information for multiple parishes concurrently.

        Args:
            parishes: List of parishes with basic information
            diocese_name: Name of the diocese for logging
            max_concurrent: Maximum concurrent requests (defaults to pool_size * 2)

        Returns:
            List of parishes with enhanced detail information
        """
        if not parishes:
            return []

        if not self.driver_pool:
            await self.initialize()

        max_concurrent = max_concurrent or (self.pool_size * 2)

        logger.info(f"🔄 Starting concurrent parish detail extraction for {len(parishes)} parishes")
        logger.info(f"⚡ Concurrency: {max_concurrent} | Batch size: {self.batch_size}")

        start_time = time.time()

        # Create extraction jobs
        extraction_jobs = []
        for parish in parishes:
            if self._should_extract_details(parish):
                job = ParishExtractionJob(
                    parish_name=parish.name,
                    parish_url=self._get_detail_url(parish),
                    base_info=parish.__dict__.copy(),
                    priority=self._calculate_priority(parish),
                    extraction_method=self._determine_extraction_method(parish),
                )
                extraction_jobs.append(job)

        if not extraction_jobs:
            logger.info("ℹ️ No parishes require detail extraction")
            return parishes

        logger.info(f"📝 Created {len(extraction_jobs)} extraction jobs")

        # Process jobs in batches
        enhanced_parishes = []
        failed_count = 0

        for i in range(0, len(extraction_jobs), self.batch_size):
            batch = extraction_jobs[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(extraction_jobs) + self.batch_size - 1) // self.batch_size

            logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} parishes)")

            # Create batch requests
            batch_requests = []
            for job in batch:
                request = {
                    "url": job.parish_url,
                    "callback": self._extract_parish_detail_sync,
                    "args": (job.parish_name, job.base_info),
                    "priority": job.priority,
                    "max_retries": 2,
                }
                batch_requests.append(request)

            # Execute batch concurrently
            try:
                batch_results = await self.driver_pool.batch_requests(
                    batch_requests, batch_size=min(max_concurrent, len(batch))
                )

                # Process results
                for job, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        logger.warning(f"❌ Failed to extract details for {job.parish_name}: {result}")
                        # Create parish with base info only
                        parish = self._create_parish_from_base_info(job.base_info)
                        enhanced_parishes.append(parish)
                        failed_count += 1
                    else:
                        enhanced_parishes.append(result)
                        self.extraction_stats["successful_extractions"] += 1

                # Small delay between batches to be respectful
                if batch_num < total_batches:
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"❌ Batch {batch_num} failed completely: {e}")
                # Add all jobs in batch as failed
                for job in batch:
                    parish = self._create_parish_from_base_info(job.base_info)
                    enhanced_parishes.append(parish)
                    failed_count += 1

        # Update statistics
        total_time = time.time() - start_time
        self.extraction_stats.update(
            {
                "total_parishes": len(parishes),
                "failed_extractions": failed_count,
                "total_time": total_time,
                "average_time_per_parish": total_time / max(len(parishes), 1),
            }
        )

        # Log results
        success_rate = (self.extraction_stats["successful_extractions"] / max(len(extraction_jobs), 1)) * 100

        logger.info(f"✅ Concurrent extraction completed in {total_time:.2f}s")
        logger.info(
            f"📊 Results: {self.extraction_stats['successful_extractions']} successful, "
            f"{failed_count} failed ({success_rate:.1f}% success rate)"
        )
        logger.info(
            f"⚡ Performance: {self.extraction_stats['average_time_per_parish']:.2f}s per parish "
            f"({60/self.extraction_stats['average_time_per_parish']:.1f} parishes/minute)"
        )

        return enhanced_parishes

    def _should_extract_details(self, parish: ParishData) -> bool:
        """Determine if a parish needs detail extraction"""
        # Extract details if we have a potential detail URL and missing key information
        if not hasattr(parish, "detail_url") or not parish.detail_url:
            return False

        # Check if we're missing important information
        missing_info = not parish.phone or not parish.website or not parish.full_address or not parish.zip_code

        return missing_info

    def _get_detail_url(self, parish: ParishData) -> str:
        """Get the detail URL for a parish"""
        if hasattr(parish, "detail_url") and parish.detail_url:
            return parish.detail_url
        return ""

    def _calculate_priority(self, parish: ParishData) -> int:
        """Calculate extraction priority for a parish (lower = higher priority)"""
        priority = 5  # Default priority

        # Higher priority for parishes with more missing information
        missing_fields = 0
        if not parish.phone:
            missing_fields += 1
        if not parish.website:
            missing_fields += 1
        if not parish.full_address:
            missing_fields += 1
        if not parish.zip_code:
            missing_fields += 1

        # Lower number = higher priority
        priority = max(1, 5 - missing_fields)

        return priority

    def _determine_extraction_method(self, parish: ParishData) -> str:
        """Determine the best extraction method for a parish"""
        if hasattr(parish, "detail_url") and parish.detail_url:
            if "ecatholic" in parish.detail_url.lower():
                return "ecatholic"
            elif "diocese" in parish.detail_url.lower():
                return "diocese_standard"
        return "standard"

    def _extract_parish_detail_sync(self, driver, parish_name: str, base_info: Dict) -> ParishData:
        """
        Synchronous parish detail extraction (runs in thread pool).
        This is the actual extraction logic that runs in the WebDriver.
        """
        try:
            # Load the parish detail page
            try:
                current_url = driver.current_url
                # Handle async driver Task object
                if hasattr(current_url, "__await__") or "Task" in str(type(current_url)):
                    current_url = "unknown_url"
            except Exception:
                current_url = "unknown_url"
            logger.debug(f"🔍 Extracting details for: {parish_name}")

            # Wait for page content
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            # Get page source and parse
            try:
                html_content = driver.page_source
                # Handle case where async driver returns Task instead of string
                if (
                    hasattr(html_content, "__await__")
                    or str(type(html_content)) == "<class 'coroutine'>"
                    or "Task" in str(type(html_content))
                ):
                    logger.warning(f"⚠️ Async driver returned Task object instead of string, using fallback")
                    # Try to get page source using alternative method
                    html_content = driver.execute_script("return document.documentElement.outerHTML;")
                soup = BeautifulSoup(html_content, "html.parser")
            except (TypeError, ValueError) as e:
                if "invalid type" in str(e).lower():
                    logger.warning(f"⚠️ BeautifulSoup markup error: {e}")
                    # Fallback: use driver execute_script to get HTML
                    try:
                        html_content = driver.execute_script("return document.documentElement.outerHTML;")
                        soup = BeautifulSoup(html_content, "html.parser")
                    except Exception as fallback_error:
                        logger.error(f"❌ Fallback HTML extraction failed: {fallback_error}")
                        raise e
                else:
                    raise e

            # Extract enhanced information
            enhanced_info = self._extract_enhanced_parish_info(soup, base_info)

            # Create enhanced ParishData object
            parish = ParishData(
                name=enhanced_info.get("name", parish_name),
                address=enhanced_info.get("address", base_info.get("address", "")),
                phone=enhanced_info.get("phone", base_info.get("phone", "")),
                website=enhanced_info.get("website", base_info.get("website", "")),
                zip_code=enhanced_info.get("zip_code", base_info.get("zip_code", "")),
                full_address=enhanced_info.get("full_address", base_info.get("full_address", "")),
                clergy_info=enhanced_info.get("clergy_info", ""),
                service_times=enhanced_info.get("service_times", ""),
                enhanced_extraction=True,
            )

            logger.debug(f"✅ Enhanced extraction completed for: {parish_name}")
            return parish

        except Exception as e:
            logger.warning(f"⚠️ Detail extraction failed for {parish_name}: {str(e)}")
            # Return parish with base info
            return self._create_parish_from_base_info(base_info)

    def _extract_enhanced_parish_info(self, soup: BeautifulSoup, base_info: Dict) -> Dict:
        """Extract enhanced parish information from detail page"""
        enhanced_info = base_info.copy()

        try:
            # Enhanced contact information extraction
            self._extract_contact_details(soup, enhanced_info)

            # Enhanced address extraction
            self._extract_address_details(soup, enhanced_info)

            # Clergy information
            self._extract_clergy_info(soup, enhanced_info)

            # Service times
            self._extract_service_times(soup, enhanced_info)

            # Website information
            self._extract_website_info(soup, enhanced_info)

        except Exception as e:
            logger.debug(f"⚠️ Error in enhanced extraction: {e}")

        return enhanced_info

    def _extract_contact_details(self, soup: BeautifulSoup, info: Dict):
        """Extract contact information"""
        # Phone numbers
        phone_selectors = [
            "span[data-phone]",
            ".phone",
            ".telephone",
            'a[href^="tel:"]',
            ".contact-phone",
            '[class*="phone"]',
            '[id*="phone"]',
        ]

        for selector in phone_selectors:
            elements = soup.select(selector)
            for element in elements:
                phone_text = element.get_text(strip=True)
                if phone_text and len(phone_text) >= 10:
                    info["phone"] = phone_text
                    break
            if info.get("phone"):
                break

        # Fax numbers
        fax_selectors = [".fax", '[class*="fax"]', '[id*="fax"]']
        for selector in fax_selectors:
            elements = soup.select(selector)
            for element in elements:
                fax_text = element.get_text(strip=True)
                if fax_text:
                    info["fax"] = fax_text
                    break

    def _extract_address_details(self, soup: BeautifulSoup, info: Dict):
        """Extract detailed address information"""
        address_selectors = [
            ".address",
            ".location",
            '[class*="address"]',
            '[id*="address"]',
            ".contact-address",
            ".parish-address",
        ]

        for selector in address_selectors:
            elements = soup.select(selector)
            for element in elements:
                address_text = element.get_text(strip=True)
                if address_text and len(address_text) > 10:
                    # Use enhanced address parsing
                    parsed_address = clean_parish_name_and_extract_address(address_text)
                    if parsed_address.get("full_address"):
                        info.update(parsed_address)
                        break

    def _extract_clergy_info(self, soup: BeautifulSoup, info: Dict):
        """Extract clergy information"""
        clergy_selectors = [
            ".pastor",
            ".priest",
            ".clergy",
            '[class*="pastor"]',
            '[class*="priest"]',
            ".staff",
            '[id*="pastor"]',
        ]

        clergy_info = []
        for selector in clergy_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 3:
                    clergy_info.append(text)

        if clergy_info:
            info["clergy_info"] = "; ".join(clergy_info[:3])  # Limit to top 3

    def _extract_service_times(self, soup: BeautifulSoup, info: Dict):
        """Extract service times and mass schedules"""
        service_selectors = [
            ".mass-times",
            ".schedule",
            ".service-times",
            '[class*="mass"]',
            '[class*="service"]',
            ".liturgy",
            '[id*="mass"]',
            '[id*="schedule"]',
        ]

        service_info = []
        for selector in service_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 5:
                    service_info.append(text)

        if service_info:
            info["service_times"] = "; ".join(service_info[:2])  # Limit to top 2

    def _extract_website_info(self, soup: BeautifulSoup, info: Dict):
        """Extract website information"""
        website_selectors = ['a[href*="www."]', 'a[href^="http"]', ".website", '[class*="website"]', '[id*="website"]']

        for selector in website_selectors:
            elements = soup.select(selector)
            for element in elements:
                href = element.get("href", "")
                if href and href.startswith("http") and "parish" in href.lower():
                    info["website"] = href
                    break

    def _create_parish_from_base_info(self, base_info: Dict) -> ParishData:
        """Create ParishData object from base information"""
        return ParishData(
            name=base_info.get("name", ""),
            address=base_info.get("address", ""),
            phone=base_info.get("phone", ""),
            website=base_info.get("website", ""),
            zip_code=base_info.get("zip_code", ""),
            full_address=base_info.get("full_address", ""),
            clergy_info=base_info.get("clergy_info", ""),
            service_times=base_info.get("service_times", ""),
            enhanced_extraction=False,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        stats = self.extraction_stats.copy()
        if self.driver_pool:
            stats["driver_pool_stats"] = self.driver_pool.get_stats()
        return stats

    def log_stats(self):
        """Log comprehensive extraction statistics"""
        logger.info("📊 Async Parish Extractor Statistics:")
        logger.info(f"  • Total Parishes: {self.extraction_stats['total_parishes']}")
        logger.info(f"  • Successful Extractions: {self.extraction_stats['successful_extractions']}")
        logger.info(f"  • Failed Extractions: {self.extraction_stats['failed_extractions']}")
        logger.info(f"  • Average Time per Parish: {self.extraction_stats['average_time_per_parish']:.2f}s")
        logger.info(
            f"  • Extraction Rate: {60/max(self.extraction_stats['average_time_per_parish'], 0.1):.1f} parishes/minute"
        )

        if self.driver_pool:
            self.driver_pool.log_stats()


# Global async extractor instance
_async_extractor = None


async def get_async_parish_extractor(pool_size: int = 4, batch_size: int = 8) -> AsyncParishExtractor:
    """Get or create the global async parish extractor"""
    global _async_extractor

    if _async_extractor is None:
        _async_extractor = AsyncParishExtractor(pool_size, batch_size)
        await _async_extractor.initialize()

    return _async_extractor
