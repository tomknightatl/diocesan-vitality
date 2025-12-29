#!/usr/bin/env python3
"""
Extraction Agent for Agentic Schedule Extraction

This agent extracts schedule data from various content types using AI and specialized tools.

Phase 1 Implementation: HTML extraction with existing AI extractor
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)


class ExtractionAgent:
    """Extracts schedule data from various content types"""

    def __init__(self):
        """Initialize extraction tools"""
        # Reuse existing AI extractor
        try:
            from core.schedule_ai_extractor import ScheduleAIExtractor

            self.ai_extractor = ScheduleAIExtractor()
            logger.info("✅ AI Extractor initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI Extractor: {e}")
            self.ai_extractor = None

    def extract_schedule(self, state: Dict) -> Dict:
        """
        Extract schedule from discovered sources

        Args:
            state: Current workflow state

        Returns:
            Updated state with extraction results
        """
        logger.info(f"🔧 Starting extraction for {state['parish_url']}")

        if not state.get("sources_checked"):
            logger.info("🔧 No sources to extract from")
            return state

        schedule_type = state["schedule_type"]

        for source_url in state["sources_checked"]:
            if source_url in state.get("extraction_attempts", []):
                continue

            logger.info(f"🔧 Extracting from {source_url}")

            # Determine content type
            content_type = self._detect_content_type(source_url)
            logger.debug(f"🔧 Detected content type: {content_type}")

            # Fetch content
            content = self._fetch_content(source_url, content_type)

            if not content:
                logger.warning(f"🔧 No content fetched from {source_url}")
                continue

            # Extract schedule
            extraction_result = self._extract_from_content(
                content, content_type, schedule_type
            )

            # Update state
            state["extraction_attempts"].append(source_url)
            state["knowledge_graph"]["extraction"] = {
                "source": source_url,
                "content_type": content_type,
                "result": extraction_result,
                "timestamp": self._get_current_timestamp(),
            }

            # Check for success
            if extraction_result.get("schedule_found", False):
                logger.info(f"🎯 Successfully extracted schedule from {source_url}")
                state["schedule_found"] = True
                state["final_schedule"] = extraction_result
                return state

        logger.info("🔧 No schedule found in any source")
        return state

    def _detect_content_type(self, url: str) -> str:
        """
        Determine content type from URL and headers

        Args:
            url: Source URL

        Returns:
            Content type string
        """
        if url.lower().endswith(".pdf"):
            return "application/pdf"
        elif any(
            keyword in url.lower() for keyword in ["calendar", "events", "schedule"]
        ):
            return "text/calendar"
        else:
            return "text/html"

    def _fetch_content(self, url: str, content_type: str) -> Optional[str]:
        """
        Fetch content using appropriate method

        Args:
            url: Source URL
            content_type: Content type

        Returns:
            Content as string, or None if failed
        """
        try:
            if content_type == "application/pdf":
                return self._fetch_pdf(url)
            elif content_type == "text/calendar":
                return self._fetch_calendar(url)
            else:
                return self._fetch_html(url)
        except Exception as e:
            logger.error(f"🔧 Failed to fetch content from {url}: {e}")
            return None

    def _extract_from_content(
        self, content: str, content_type: str, schedule_type: str
    ) -> Dict:
        """
        Extract schedule based on content type

        Args:
            content: Content to extract from
            content_type: Type of content
            schedule_type: Schedule type (reconciliation/adoration)

        Returns:
            Extraction result dictionary
        """
        if content_type == "application/pdf":
            # Phase 2: PDF extraction
            return self._extract_from_pdf(content, schedule_type)

        elif content_type == "text/calendar":
            # Phase 2: Calendar extraction
            return self._extract_from_calendar(content, schedule_type)

        else:  # text/html
            return self._extract_from_html(content, schedule_type)

    def _extract_from_html(self, html_content: str, schedule_type: str) -> Dict:
        """
        Extract schedule from HTML content using AI

        Args:
            html_content: HTML content
            schedule_type: Schedule type

        Returns:
            Extraction result
        """
        if not self.ai_extractor:
            return {"schedule_found": False, "error": "AI extractor not available"}

        try:
            logger.info(f"🤖 Extracting {schedule_type} schedule using AI")

            result = self.ai_extractor.extract_schedule_from_content(
                html_content,
                "",  # URL not needed for Phase 1
                schedule_type,
            )

            # Format result for consistency
            formatted_result = {
                "schedule_found": result.get("schedule_found", False),
                "schedule_details": result.get("schedule_details", ""),
                "confidence": result.get("confidence_score", 0),
                "method": "ai_extraction",
                "source_url": "",  # Will be set by caller
                "content_type": "text/html",
            }

            logger.info(
                f"🤖 AI extraction confidence: {formatted_result['confidence']}"
            )
            return formatted_result

        except Exception as e:
            logger.error(f"🤖 AI extraction failed: {e}")
            return {
                "schedule_found": False,
                "error": str(e),
                "method": "ai_extraction_error",
            }

    def _extract_from_pdf(self, pdf_content: str, schedule_type: str) -> Dict:
        """
        Extract schedule from PDF content (Phase 2 placeholder)

        Args:
            pdf_content: PDF text content
            schedule_type: Schedule type

        Returns:
            Extraction result
        """
        logger.info("📄 PDF extraction (Phase 2)")
        return {"schedule_found": False, "error": "Not implemented in Phase 1"}

    def _extract_from_calendar(self, calendar_data: str, schedule_type: str) -> Dict:
        """
        Extract schedule from calendar data (Phase 2 placeholder)

        Args:
            calendar_data: Calendar data
            schedule_type: Schedule type

        Returns:
            Extraction result
        """
        logger.info("📅 Calendar extraction (Phase 2)")
        return {"schedule_found": False, "error": "Not implemented in Phase 1"}

    def _fetch_html(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from URL

        Args:
            url: URL to fetch

        Returns:
            HTML content or None
        """
        try:
            import requests
            from requests.exceptions import RequestException

            logger.debug(f"🌐 Fetching HTML from {url}")

            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; Parish Schedule Research)"
                },
            )

            response.raise_for_status()
            return response.text

        except RequestException as e:
            logger.error(f"🌐 Failed to fetch {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"🌐 Unexpected error fetching {url}: {e}")
            return None

    def _fetch_pdf(self, url: str) -> Optional[str]:
        """
        Fetch PDF content (Phase 2 placeholder)

        Args:
            url: URL to fetch

        Returns:
            PDF text or None
        """
        logger.debug(f"📄 Fetching PDF from {url}")
        # Phase 2 implementation will go here
        return None

    def _fetch_calendar(self, url: str) -> Optional[str]:
        """
        Fetch calendar data using Playwright (Phase 2 placeholder)

        Args:
            url: URL to fetch

        Returns:
            Calendar data or None
        """
        logger.debug(f"📅 Fetching calendar from {url}")
        # Phase 2 implementation will go here
        return None

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
