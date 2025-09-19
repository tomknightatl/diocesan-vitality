#!/usr/bin/env python3
"""
AI-powered schedule extraction for accurate parish schedule parsing.
Uses Google Gemini AI to extract structured schedule information.
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import google.generativeai as genai
from core.logger import get_logger
from core.db import get_supabase_client
import config

logger = get_logger(__name__)


class ScheduleAIExtractor:
    """AI-powered extractor for parish schedules using Google Gemini."""

    def __init__(self):
        """Initialize the AI extractor with Gemini API."""
        try:
            genai.configure(api_key=config.GENAI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("AI Schedule Extractor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI Schedule Extractor: {e}")
            self.model = None

    def get_adaptive_confidence_threshold(self, url: str, content: str) -> int:
        """
        Calculate adaptive confidence threshold based on URL and content characteristics.

        Args:
            url: Source URL for context clues
            content: Page content for complexity analysis

        Returns:
            Adaptive confidence threshold (lower = more permissive)
        """
        base_threshold = 15  # Lowered from 20 to be more permissive
        adjustments = 0

        # URL-based adjustments
        url_lower = url.lower()

        # Major parishes/cathedrals should have lower thresholds
        if any(keyword in url_lower for keyword in ['cathedral', 'basilica', 'shrine']):
            adjustments -= 10
            logger.debug(f"Major parish detected, lowering threshold by 10")

        # Dedicated schedule pages should have lower thresholds
        if any(keyword in url_lower for keyword in ['schedule', 'hours', 'mass-times', 'adoration', 'confession', 'reconciliation']):
            adjustments -= 7  # Increased from 5 to be more permissive
            logger.debug(f"Dedicated schedule page detected, lowering threshold by 7")

        # Parish life/ministry pages often contain schedule info
        if any(keyword in url_lower for keyword in ['parish-life', 'ministry', 'ministries', 'worship', 'sacrament']):
            adjustments -= 5
            logger.debug(f"Parish life/ministry page detected, lowering threshold by 5")

        # Content-based adjustments
        content_length = len(content.split()) if content else 0

        # Large pages with lots of content should be more permissive
        if content_length > 2000:
            adjustments -= 5
            logger.debug(f"Large page ({content_length} words), lowering threshold by 5")
        elif content_length < 100:  # Only very small pages get penalty
            adjustments += 3  # Reduced from 5
            logger.debug(f"Very small page ({content_length} words), raising threshold by 3")

        # Sitemap pages should have higher thresholds but not too high
        if 'sitemap' in url_lower:
            adjustments += 10  # Reduced from 15
            logger.debug(f"Sitemap page detected, raising threshold by 10")

        # Generic 'about' pages might contain schedules
        if any(keyword in url_lower for keyword in ['about', 'contact', 'home', 'welcome']):
            adjustments -= 2
            logger.debug(f"Generic page that might contain schedule info, lowering threshold by 2")

        final_threshold = max(3, base_threshold + adjustments)  # Minimum threshold lowered to 3

        if final_threshold != base_threshold:
            logger.info(f"Adaptive threshold for {url}: {final_threshold} (base: {base_threshold}, adjustment: {adjustments:+d})")

        return final_threshold

    def extract_schedule_from_content(self, content: str, url: str, schedule_type: str) -> Dict:
        """
        Extract structured schedule information from webpage content using AI.

        Args:
            content: HTML content or text from the webpage
            url: Source URL for context
            schedule_type: 'adoration', 'reconciliation', or 'mass'

        Returns:
            Dict with structured schedule information
        """
        if not self.model:
            return self._get_empty_result(f"AI model not available")

        try:
            # Create targeted prompt for schedule extraction
            prompt = self._create_extraction_prompt(content, schedule_type)

            # Calculate timeout based on content size (larger content = longer timeout)
            content_size = len(content)
            if content_size > 20000:
                timeout_seconds = 120  # 2 minutes for very large content
            elif content_size > 10000:
                timeout_seconds = 90   # 1.5 minutes for large content
            else:
                timeout_seconds = 60   # 1 minute for normal content

            logger.info(f"Processing {content_size} chars with {timeout_seconds}s timeout for {schedule_type}")

            # Get AI response with timeout handling using concurrent.futures
            import concurrent.futures

            def generate_with_timeout():
                return self.model.generate_content(prompt)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(generate_with_timeout)
                try:
                    response = future.result(timeout=timeout_seconds)
                except concurrent.futures.TimeoutError:
                    logger.warning(f"AI processing timeout ({timeout_seconds}s) for {schedule_type} at {url}")
                    return self._get_empty_result(f"AI processing timeout after {timeout_seconds}s")

            # Parse AI response into structured data
            result = self._parse_ai_response(response.text, url, schedule_type)

            # Add URL and content for adaptive threshold calculation
            result['url'] = url
            result['content'] = content[:1000]  # Store first 1000 chars for threshold calculation

            logger.info(f"AI extraction completed for {schedule_type} at {url}")
            return result

        except Exception as e:
            logger.error(f"AI extraction failed for {schedule_type} at {url}: {e}")
            return self._get_empty_result(f"AI extraction error: {str(e)}")

    def _create_extraction_prompt(self, content: str, schedule_type: str) -> str:
        """Create a targeted prompt for schedule extraction."""

        # Clean and truncate content to fit within token limits
        cleaned_content = self._clean_content_for_ai(content)

        if schedule_type == "adoration":
            return f"""
You are an expert at extracting Catholic parish schedule information.
Analyze the following webpage content and extract ONLY Eucharistic Adoration schedule information.

Look for:
- Adoration, Exposition, Blessed Sacrament, Holy Hour schedules
- Perpetual Adoration availability
- Weekly recurring schedules (e.g., "Wednesdays 6-7 PM")
- Daily schedules if offered
- Special adoration events

WEBPAGE CONTENT:
{cleaned_content}

Please respond ONLY in this JSON format:
{{
    "has_weekly_schedule": true/false,
    "schedule_found": true/false,
    "days_offered": ["Monday", "Tuesday", etc.],
    "times": ["6:00 PM - 7:00 PM", "9:00 AM - 10:00 AM", etc.],
    "frequency": "weekly" | "daily" | "monthly" | "special_events" | "unknown",
    "schedule_details": "Full text description of the schedule",
    "is_perpetual": true/false,
    "confidence_score": 0-100,
    "notes": "Any additional relevant information"
}}

If no adoration schedule is found, return has_weekly_schedule: false and schedule_found: false.
"""
        elif schedule_type == "reconciliation":
            return f"""
You are an expert at extracting Catholic parish schedule information.
Analyze the following webpage content and extract ONLY Reconciliation/Confession schedule information.

Look for:
- Confession times and schedules
- Reconciliation service schedules
- Sacrament of Penance availability
- Weekly recurring schedules (e.g., "Saturdays 3:30-4:30 PM")
- "By appointment" availability
- Before/after Mass schedules

WEBPAGE CONTENT:
{cleaned_content}

Please respond ONLY in this JSON format:
{{
    "has_weekly_schedule": true/false,
    "schedule_found": true/false,
    "days_offered": ["Saturday", "Sunday", etc.],
    "times": ["3:30 PM - 4:30 PM", "Before 5:00 PM Mass", etc.],
    "frequency": "weekly" | "daily" | "by_appointment" | "before_mass" | "unknown",
    "schedule_details": "Full text description of the schedule",
    "by_appointment": true/false,
    "confidence_score": 0-100,
    "notes": "Any additional relevant information"
}}

If no reconciliation schedule is found, return has_weekly_schedule: false and schedule_found: false.
"""
        elif schedule_type == "mass":
            return f"""
You are an expert at extracting Catholic parish schedule information.
Analyze the following webpage content and extract ONLY Mass schedule information.

Look for:
- Mass times and schedules
- Sunday Mass schedules
- Weekday Mass schedules
- Saturday Vigil Mass schedules
- Holy Day schedules
- Liturgy and Eucharistic celebration times
- Weekly recurring schedules (e.g., "Sunday 8:00 AM, 10:30 AM, 12:00 PM")
- Daily Mass offerings
- Special liturgical schedules

WEBPAGE CONTENT:
{cleaned_content}

Please respond ONLY in this JSON format:
{{
    "has_weekly_schedule": true/false,
    "schedule_found": true/false,
    "days_offered": ["Sunday", "Monday", "Tuesday", etc.],
    "times": ["8:00 AM", "10:30 AM", "12:00 PM", etc.],
    "frequency": "weekly" | "daily" | "weekends_only" | "special_events" | "unknown",
    "schedule_details": "Full text description of the Mass schedule",
    "has_vigil_mass": true/false,
    "has_daily_mass": true/false,
    "confidence_score": 0-100,
    "notes": "Any additional relevant information"
}}

If no Mass schedule is found, return has_weekly_schedule: false and schedule_found: false.
"""

    def _clean_content_for_ai(self, content: str) -> str:
        """Clean and intelligently truncate content for AI processing."""
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', ' ', content)

        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)

        # Increased limit for large sitemap processing (Gemini 1.5 Flash can handle more)
        max_chars = 32000  # Increased from 8000 to handle large sitemaps

        if len(content) > max_chars:
            # For large content, try to find schedule-relevant sections first
            schedule_keywords = [
                'mass', 'schedule', 'confession', 'reconciliation', 'adoration',
                'eucharistic', 'holy hour', 'sacrament', 'liturgy', 'service',
                'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday',
                'daily', 'weekly', 'am', 'pm', 'time', 'hour'
            ]

            # Split content into chunks and prioritize schedule-relevant sections
            words = content.split()
            relevant_chunks = []
            current_chunk = []
            current_size = 0

            for word in words:
                word_lower = word.lower()
                is_relevant = any(keyword in word_lower for keyword in schedule_keywords)

                # If we find relevant content, prioritize it
                if is_relevant and current_size < max_chars:
                    current_chunk.append(word)
                    current_size += len(word) + 1
                elif current_size < max_chars * 0.7:  # Use 70% for general content
                    current_chunk.append(word)
                    current_size += len(word) + 1
                else:
                    break

            content = ' '.join(current_chunk)
            if len(content) > max_chars:
                content = content[:max_chars] + "..."

            logger.info(f"Large content processed: {len(content)} chars from original {len(' '.join(words))} chars")

        return content.strip()

    def _parse_ai_response(self, ai_response: str, url: str, schedule_type: str) -> Dict:
        """Parse AI response into structured format."""
        try:
            # Try to extract JSON from AI response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)

                # Add metadata
                parsed['source_url'] = url
                parsed['extraction_method'] = 'ai_gemini'
                parsed['extracted_at'] = datetime.now(timezone.utc).isoformat()
                parsed['schedule_type'] = schedule_type

                # Validate required fields
                parsed.setdefault('has_weekly_schedule', False)
                parsed.setdefault('schedule_found', False)
                parsed.setdefault('confidence_score', 0)

                return parsed
            else:
                logger.warning(f"No JSON found in AI response: {ai_response[:200]}")
                return self._get_empty_result("AI response format error")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON response: {e}")
            return self._get_empty_result(f"JSON parsing error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error parsing AI response: {e}")
            return self._get_empty_result(f"Response parsing error: {str(e)}")

    def _get_empty_result(self, error_message: str) -> Dict:
        """Return empty result structure."""
        return {
            'has_weekly_schedule': False,
            'schedule_found': False,
            'days_offered': [],
            'times': [],
            'frequency': 'unknown',
            'schedule_details': '',
            'confidence_score': 0,
            'notes': error_message,
            'extraction_method': 'ai_gemini',
            'extracted_at': datetime.now(timezone.utc).isoformat()
        }

    def batch_extract_schedules(self, parish_urls: List[Tuple[str, int, str]],
                              schedule_type: str) -> List[Dict]:
        """
        Extract schedules for multiple parish URLs.

        Args:
            parish_urls: List of (url, parish_id, content) tuples
            schedule_type: 'adoration', 'reconciliation', or 'mass'

        Returns:
            List of extraction results
        """
        results = []

        for url, parish_id, content in parish_urls:
            logger.info(f"Processing {schedule_type} extraction for parish {parish_id}: {url}")

            result = self.extract_schedule_from_content(content, url, schedule_type)
            result['parish_id'] = parish_id
            results.append(result)

            # Small delay to be respectful to the API
            import time
            time.sleep(0.5)

        return results


def save_ai_schedule_results(supabase, results: List[Dict]):
    """Save AI extraction results to database."""
    if not results:
        logger.info("No AI schedule results to save")
        return

    facts_to_save = []

    for result in results:
        parish_id = result.get('parish_id')
        schedule_type = result.get('schedule_type')

        if not parish_id or not schedule_type:
            continue

        # Use adaptive confidence threshold based on URL and content
        url = result.get('url', '')
        content = result.get('content', '')

        # Create temporary extractor instance if we need to calculate adaptive threshold
        temp_extractor = ScheduleAIExtractor()
        adaptive_threshold = temp_extractor.get_adaptive_confidence_threshold(url, content)

        confidence_score = result.get('confidence_score', 0)

        # Only save if schedule was found with adaptive confidence threshold
        if result.get('schedule_found') and confidence_score >= adaptive_threshold:

            # Create structured fact value
            fact_value = {
                'has_weekly_schedule': result.get('has_weekly_schedule', False),
                'days_offered': result.get('days_offered', []),
                'times': result.get('times', []),
                'frequency': result.get('frequency', 'unknown'),
                'schedule_details': result.get('schedule_details', ''),
                'confidence_score': result.get('confidence_score', 0)
            }

            facts_to_save.append({
                'parish_id': parish_id,
                'fact_type': f'{schedule_type.title()}Schedule',  # Use existing enum values
                'fact_value': json.dumps(fact_value),
                'fact_source_url': result.get('source_url'),
                'fact_string': result.get('schedule_details', ''),
                'confidence_score': result.get('confidence_score', 0),
                'extraction_method': 'ai_gemini'  # This field distinguishes AI vs keyword extraction
            })

    if facts_to_save:
        try:
            supabase.table('ParishData').upsert(facts_to_save,
                                              on_conflict='parish_id,fact_type').execute()
            logger.info(f"Successfully saved {len(facts_to_save)} AI schedule facts to database")
        except Exception as e:
            logger.error(f"Error saving AI schedule facts: {e}")
    else:
        logger.info("No high-confidence AI schedule results to save")


# Test function
def test_ai_extraction():
    """Test the AI extraction with sample content."""
    extractor = ScheduleAIExtractor()

    sample_content = """
    <h3>Mass Schedule</h3>
    <p>Sunday Masses: 8:00 AM, 10:30 AM, 12:00 PM</p>
    <p>Saturday Vigil: 5:00 PM</p>
    <p>Weekday Masses: Monday-Friday 8:00 AM, Wednesday 6:00 PM</p>

    <h3>Adoration Schedule</h3>
    <p>Eucharistic Adoration is held every Wednesday from 6:00 PM to 7:00 PM in the church.</p>
    <p>First Friday Holy Hour: 7:00 PM - 8:00 PM</p>

    <h3>Confession Schedule</h3>
    <p>Reconciliation: Saturdays 3:30 PM - 4:30 PM, or by appointment</p>
    """

    result = extractor.extract_schedule_from_content(
        sample_content,
        "https://example.com",
        "mass"
    )

    print("AI Extraction Result:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    test_ai_extraction()
