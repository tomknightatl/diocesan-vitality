#!/usr/bin/env python3
"""
Parish validation system to filter out diocesan departments and ensure data quality.
Provides intelligent classification of extracted entities as actual parishes vs administrative units.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of parish validation check"""

    is_valid: bool
    confidence: float  # 0.0 to 1.0
    reason: str
    matched_keywords: List[str]
    excluded_keywords: List[str]


class ParishValidator:
    """
    Intelligent parish validation system that distinguishes between actual parishes
    and diocesan administrative entities.
    """

    def __init__(self):
        # High-confidence parish indicators
        self.PARISH_KEYWORDS = {
            # Direct parish identifiers
            "parish",
            "church",
            "cathedral",
            "basilica",
            "chapel",
            # Religious community indicators
            "abbey",
            "monastery",
            "convent",
            "shrine",
            "mission",
            # Saint/religious name patterns
            "saint",
            "st.",
            "holy",
            "blessed",
            "our lady",
            "sacred heart",
            "immaculate",
            "assumption",
            "annunciation",
            "nativity",
            # Catholic-specific terms
            "catholic",
            "roman catholic",
            "byzantine",
            "maronite",
        }

        # Strong exclusion indicators (diocesan departments)
        self.EXCLUDE_KEYWORDS = {
            # Administrative offices
            "office",
            "department",
            "ministry",
            "center",
            "council",
            "committee",
            "bureau",
            "division",
            "program",
            "service",
            "agency",
            # Specific diocesan functions
            "chancellor",
            "vicar general",
            "bishop",
            "tribunal",
            "finance",
            "communications",
            "stewardship",
            "catechesis",
            "formation",
            # Educational/support services
            "school",
            "education",
            "retreat center",
            "meeting rooms",
            "catholic charities",
            "social services",
            "youth ministry",
            # Administrative roles/positions
            "director",
            "coordinator",
            "administrator",
            "manager",
            "staff",
            "employment",
            "human resources",
            "development",
        }

        # Medium-confidence parish indicators
        self.WEAK_PARISH_KEYWORDS = {
            "community",
            "congregation",
            "worship",
            "mass",
            "liturgy",
            "sacraments",
            "baptism",
            "confirmation",
            "eucharist",
        }

        # Location-based indicators (suggest parish presence)
        self.LOCATION_KEYWORDS = {
            "avenue",
            "street",
            "road",
            "drive",
            "boulevard",
            "lane",
            "north",
            "south",
            "east",
            "west",
            "downtown",
            "heights",
        }

        # Compile regex patterns for efficiency
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficient matching"""

        # Saint name patterns - common variations
        self.saint_pattern = re.compile(r"\b(?:saint|st\.?|san|santa|santo)\s+[a-z]+", re.IGNORECASE)

        # Address patterns
        self.address_pattern = re.compile(
            r"\b\d+\s+[a-z\s]+(?:street|st|avenue|ave|road|rd|drive|dr|boulevard|blvd|lane|ln)\b", re.IGNORECASE
        )

        # Phone number patterns
        self.phone_pattern = re.compile(r"\b(?:\(\d{3}\)|\d{3}[-.]?)\s*\d{3}[-.]?\d{4}\b")

    def validate_parish(
        self, name: str, url: Optional[str] = None, address: Optional[str] = None, additional_text: Optional[str] = None
    ) -> ValidationResult:
        """
        Comprehensive parish validation using multiple signals.

        Args:
            name: Entity name to validate
            url: Optional URL for additional context
            address: Optional address information
            additional_text: Optional additional context text

        Returns:
            ValidationResult with confidence score and reasoning
        """

        # Combine all available text for analysis
        full_text = self._prepare_text(name, url, address, additional_text)
        name_lower = name.lower().strip()

        # Initialize scoring
        parish_score = 0.0
        exclude_score = 0.0
        matched_parish = []
        matched_exclude = []

        # 1. Check for strong parish indicators
        for keyword in self.PARISH_KEYWORDS:
            if keyword in name_lower:
                parish_score += 2.0
                matched_parish.append(keyword)

        # 2. Check for strong exclusion indicators
        for keyword in self.EXCLUDE_KEYWORDS:
            if keyword in name_lower:
                exclude_score += 2.5  # Slightly stronger weight for exclusions
                matched_exclude.append(keyword)

        # 3. Check for weak parish indicators
        for keyword in self.WEAK_PARISH_KEYWORDS:
            if keyword in name_lower:
                parish_score += 0.5
                matched_parish.append(keyword)

        # 4. Saint name pattern matching
        if self.saint_pattern.search(name):
            parish_score += 1.5
            matched_parish.append("saint_pattern")

        # 5. Address/location context (if available)
        if address and self.address_pattern.search(address):
            parish_score += 1.0
            matched_parish.append("address_pattern")

        # 6. URL context analysis
        if url:
            url_lower = url.lower()
            if any(term in url_lower for term in ["parish", "church", "catholic"]):
                parish_score += 0.5
                matched_parish.append("url_context")

        # 7. Length and format heuristics
        if len(name.strip()) < 3:
            exclude_score += 1.0  # Too short to be a parish name
            matched_exclude.append("too_short")

        if name.isupper() and len(name) > 20:
            exclude_score += 0.5  # ALL CAPS long text often administrative
            matched_exclude.append("all_caps_long")

        # 8. Common navigation/generic terms
        navigation_terms = {"home", "contact", "about", "contact us", "about us"}
        if name_lower in navigation_terms:
            exclude_score += 2.0
            matched_exclude.append("navigation_term")

        # Calculate final confidence and decision
        confidence = self._calculate_confidence(parish_score, exclude_score)
        is_valid = self._make_decision(parish_score, exclude_score)
        reason = self._generate_reason(parish_score, exclude_score, matched_parish, matched_exclude)

        result = ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            reason=reason,
            matched_keywords=matched_parish,
            excluded_keywords=matched_exclude,
        )

        # Log detailed analysis for debugging
        logger.debug(
            f"Parish validation: '{name}' -> {result.is_valid} " f"(confidence: {result.confidence:.2f}) - {result.reason}"
        )

        return result

    def _prepare_text(self, name: str, url: str, address: str, additional: str) -> str:
        """Combine all available text for analysis"""
        texts = [text for text in [name, url, address, additional] if text]
        return " ".join(texts).lower()

    def _calculate_confidence(self, parish_score: float, exclude_score: float) -> float:
        """Calculate confidence score between 0.0 and 1.0"""
        total_score = parish_score + exclude_score
        if total_score == 0:
            return 0.5  # Neutral confidence when no signals

        # Normalize to 0-1 range, with bias toward higher scores
        confidence = min(max(abs(parish_score - exclude_score) / (total_score + 1), 0.1), 0.95)
        return confidence

    def _make_decision(self, parish_score: float, exclude_score: float) -> bool:
        """Make binary decision: is this a valid parish?"""

        # Strong exclusion rules
        if exclude_score >= 2.0 and parish_score < 1.0:
            return False

        # Strong parish rules
        if parish_score >= 2.0 and exclude_score < 1.0:
            return True

        # Special case: facility terms should override saint names
        # (e.g., "St. Mary's Meeting Rooms" should be excluded despite having "St.")
        if exclude_score >= 2.0 and parish_score <= 4.0:
            return False

        # Tie-breaker: favor parish if scores are close
        return parish_score > exclude_score

    def _generate_reason(
        self, parish_score: float, exclude_score: float, matched_parish: List[str], matched_exclude: List[str]
    ) -> str:
        """Generate human-readable reason for the decision"""

        if parish_score > exclude_score:
            reason = f"Parish indicators (score: {parish_score:.1f}): {', '.join(matched_parish[:3])}"
            if matched_exclude:
                reason += f" | Excluded: {', '.join(matched_exclude[:2])}"
        elif exclude_score > parish_score:
            reason = f"Administrative indicators (score: {exclude_score:.1f}): {', '.join(matched_exclude[:3])}"
            if matched_parish:
                reason += f" | Parish signals: {', '.join(matched_parish[:2])}"
        else:
            reason = f"Neutral (parish: {parish_score:.1f}, exclude: {exclude_score:.1f})"

        return reason

    def batch_validate(self, entities: List[Dict]) -> List[Dict]:
        """
        Validate a batch of entities and return only valid parishes.

        Args:
            entities: List of entity dictionaries with 'name' field required

        Returns:
            List of valid parish entities with validation metadata added
        """
        valid_parishes = []

        for entity in entities:
            name = entity.get("name", "").strip()
            if not name:
                continue

            result = self.validate_parish(
                name=name, url=entity.get("url"), address=entity.get("address"), additional_text=entity.get("description")
            )

            if result.is_valid:
                # Add validation metadata
                entity["validation"] = {
                    "confidence": result.confidence,
                    "reason": result.reason,
                    "matched_keywords": result.matched_keywords,
                }
                valid_parishes.append(entity)

        logger.info(f"Parish validation: {len(valid_parishes)}/{len(entities)} entities validated as parishes")
        return valid_parishes

    def get_validation_stats(self, entities: List[Dict]) -> Dict:
        """Get detailed validation statistics for a batch"""

        stats = {
            "total": len(entities),
            "valid_parishes": 0,
            "excluded_admin": 0,
            "high_confidence": 0,
            "low_confidence": 0,
            "exclusion_reasons": {},
            "parish_indicators": {},
        }

        for entity in entities:
            name = entity.get("name", "").strip()
            if not name:
                continue

            result = self.validate_parish(name=name)

            if result.is_valid:
                stats["valid_parishes"] += 1
                if result.confidence > 0.7:
                    stats["high_confidence"] += 1
                else:
                    stats["low_confidence"] += 1

                # Track parish indicators
                for keyword in result.matched_keywords:
                    stats["parish_indicators"][keyword] = stats["parish_indicators"].get(keyword, 0) + 1
            else:
                stats["excluded_admin"] += 1

                # Track exclusion reasons
                for keyword in result.excluded_keywords:
                    stats["exclusion_reasons"][keyword] = stats["exclusion_reasons"].get(keyword, 0) + 1

        return stats


# Global validator instance
parish_validator = ParishValidator()


def validate_parish_entity(name: str, **kwargs) -> bool:
    """
    Quick validation function for single parish name.

    Args:
        name: Entity name to validate
        **kwargs: Optional url, address, additional_text

    Returns:
        True if entity is likely a valid parish
    """
    result = parish_validator.validate_parish(name, **kwargs)
    return result.is_valid


def filter_valid_parishes(entities: List[Dict]) -> List[Dict]:
    """
    Filter a list of entities to return only valid parishes.

    Args:
        entities: List of entity dictionaries

    Returns:
        Filtered list containing only valid parishes
    """
    return parish_validator.batch_validate(entities)
