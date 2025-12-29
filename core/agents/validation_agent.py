#!/usr/bin/env python3
"""
Validation Agent for Agentic Schedule Extraction

This agent validates extracted schedules for accuracy and completeness.

Phase 1 Implementation: Basic format validation and confidence scoring
"""

from typing import Dict
import re
from datetime import datetime
import logging

# Setup logging
logger = logging.getLogger(__name__)


class ValidationAgent:
    """Validates extracted schedules for accuracy"""

    def __init__(self):
        """Initialize validation components"""
        self.format_validator = FormatValidator()
        self.confidence_scorer = ConfidenceScorer()

    def validate_schedule(self, state: Dict) -> Dict:
        """
        Perform comprehensive validation

        Args:
            state: Current workflow state

        Returns:
            Updated state with validation results
        """
        logger.info(f"🔍 Validating schedule for {state['parish_url']}")

        if not state.get("schedule_found"):
            logger.info("🔍 No schedule to validate")
            return state

        schedule_data = state["final_schedule"]

        # Format validation
        format_valid = self.format_validator.validate(schedule_data)
        logger.debug(f"🔍 Format validation score: {format_valid:.2f}")

        # Confidence scoring
        confidence_score = self.confidence_scorer.calculate(schedule_data)
        logger.debug(f"🔍 Confidence score: {confidence_score}")

        # Calculate overall validity
        validity_score = (0.7 * format_valid + 0.3 * (confidence_score / 100)) * 100

        # Update state
        state["knowledge_graph"]["validation"] = {
            "is_valid": validity_score > 70,
            "validity_score": round(validity_score, 2),
            "needs_human_review": validity_score < 70,
            "format_valid": round(format_valid, 2),
            "confidence_score": confidence_score,
            "timestamp": self._get_current_timestamp(),
        }

        # Flag for human review if needed
        if validity_score < 70:
            state["knowledge_graph"]["human_review"] = {
                "required": True,
                "reason": "Low validity score",
                "score": validity_score,
            }
            logger.info(
                f"🔍 Schedule flagged for human review (score: {validity_score:.1f})"
            )
        else:
            logger.info(
                f"✅ Schedule validated successfully (score: {validity_score:.1f})"
            )

        return state

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()


class FormatValidator:
    """Validates schedule format"""

    def validate(self, schedule_data: Dict) -> float:
        """
        Check if schedule has valid format

        Args:
            schedule_data: Schedule data to validate

        Returns:
            Format validity score (0.0 - 1.0)
        """
        score = 0.0

        # Check required fields
        if "schedule_details" in schedule_data:
            score += 0.2

        # Check for time patterns
        if self._has_time_patterns(schedule_data.get("schedule_details", "")):
            score += 0.3

        # Check for day patterns
        if self._has_day_patterns(schedule_data.get("schedule_details", "")):
            score += 0.3

        # Check confidence
        if schedule_data.get("confidence", 0) > 50:
            score += 0.2

        return min(1.0, score)

    def _has_time_patterns(self, text: str) -> bool:
        """
        Check for time-related patterns

        Args:
            text: Text to check

        Returns:
            True if time patterns found
        """
        if not text:
            return False

        time_patterns = [
            r"\d{1,2}:\d{2}\s*(am|pm|AM|PM)",  # 3:30 PM
            r"\d{1,2}\s*-\s*\d{1,2}\s*(am|pm|AM|PM)",  # 3-4 PM
            r"hours?\s*per\s*(week|month|day)",  # hours per week
            r"by\s*appointment",
        ]

        return any(re.search(pattern, text, re.IGNORECASE) for pattern in time_patterns)

    def _has_day_patterns(self, text: str) -> bool:
        """
        Check for day-related patterns

        Args:
            text: Text to check

        Returns:
            True if day patterns found
        """
        if not text:
            return False

        day_patterns = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "weekday",
            "weekend",
            "daily",
            "weekly",
        ]

        return any(day in text.lower() for day in day_patterns)


class ConfidenceScorer:
    """Calculates confidence scores for extracted schedules"""

    def calculate(self, schedule_data: Dict) -> int:
        """
        Calculate confidence score based on extraction method and data

        Args:
            schedule_data: Schedule data

        Returns:
            Confidence score (0-100)
        """
        # Base confidence from extraction method
        method = schedule_data.get("method", "unknown")

        if method == "ai_extraction":
            base_confidence = 70
        elif method == "keyword_extraction":
            base_confidence = 50
        else:
            base_confidence = 30

        # Adjust based on AI confidence if available
        if "confidence" in schedule_data:
            base_confidence = max(base_confidence, schedule_data["confidence"])

        # Adjust based on schedule details
        details = schedule_data.get("schedule_details", "")
        if len(details) > 50:  # More detailed = more confident
            base_confidence = min(100, base_confidence + 10)
        elif len(details) < 10:  # Very short = less confident
            base_confidence = max(0, base_confidence - 20)

        return min(100, max(0, base_confidence))
