"""
Enhanced deduplication utilities for parish data.

This module provides sophisticated deduplication logic that goes beyond simple
string matching to identify parishes with similar names, addresses, or other
identifying information.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional, Set, Tuple


@dataclass
class DeduplicationMetrics:
    """Metrics for deduplication analysis."""

    original_count: int
    deduplicated_count: int
    duplicates_removed: int
    similarity_threshold: float

    @property
    def deduplication_rate(self) -> float:
        """Calculate percentage of duplicates removed."""
        if self.original_count == 0:
            return 0.0
        return (self.duplicates_removed / self.original_count) * 100


class ParishDeduplicator:
    """
    Advanced parish deduplication using multiple similarity metrics.

    This class provides sophisticated deduplication that considers:
    - Name similarity (fuzzy string matching)
    - Address similarity
    - Phone number matching
    - Website URL matching
    - Normalized name patterns
    """

    def __init__(self, name_similarity_threshold: float = 0.85, address_similarity_threshold: float = 0.80):
        """
        Initialize the deduplicator.

        Args:
            name_similarity_threshold: Threshold for name similarity (0.0-1.0)
            address_similarity_threshold: Threshold for address similarity (0.0-1.0)
        """
        self.name_similarity_threshold = name_similarity_threshold
        self.address_similarity_threshold = address_similarity_threshold

        # Common parish name variations for normalization
        self.name_normalizations = {
            # Saint variations
            r"\bst\.?\s+": "saint ",
            r"\bsts\.?\s+": "saints ",
            # Common abbreviations
            r"\bblessed\s+virgin\s+mary\b": "bvm",
            r"\bour\s+lady\s+of\b": "ol of",
            r"\bimmaculate\s+heart\s+of\s+mary\b": "ihm",
            r"\bsacred\s+heart\s+of\s+jesus\b": "shj",
            # Church type variations
            r"\bcatholic\s+church\b": "church",
            r"\bparish\s+church\b": "church",
            r"\bchurch\s+of\b": "",
            # Remove extra whitespace
            r"\s+": " ",
        }

    def normalize_name(self, name: str) -> str:
        """
        Normalize parish name for better matching.

        Args:
            name: Original parish name

        Returns:
            Normalized name for comparison
        """
        if not name:
            return ""

        # Convert to lowercase and strip
        normalized = name.lower().strip()

        # Apply normalizations
        for pattern, replacement in self.name_normalizations.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        # Remove punctuation and extra spaces
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two parish names.

        Uses both exact normalized matching and fuzzy string similarity.

        Args:
            name1: First parish name
            name2: Second parish name

        Returns:
            Similarity score (0.0-1.0)
        """
        if not name1 or not name2:
            return 0.0

        # Normalize names
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)

        # Check for exact match after normalization
        if norm1 == norm2:
            return 1.0

        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, norm1, norm2).ratio()

    def calculate_address_similarity(self, addr1: str, addr2: str) -> float:
        """
        Calculate similarity between two addresses.

        Args:
            addr1: First address
            addr2: Second address

        Returns:
            Similarity score (0.0-1.0)
        """
        if not addr1 or not addr2:
            return 0.0

        # Normalize addresses
        norm_addr1 = self._normalize_address(addr1)
        norm_addr2 = self._normalize_address(addr2)

        if norm_addr1 == norm_addr2:
            return 1.0

        return SequenceMatcher(None, norm_addr1, norm_addr2).ratio()

    def _normalize_address(self, address: str) -> str:
        """Normalize address for comparison."""
        if not address:
            return ""

        # Convert to lowercase and strip
        normalized = address.lower().strip()

        # Common address abbreviations
        abbreviations = {
            r"\bstreet\b": "st",
            r"\bavenue\b": "ave",
            r"\bdriver\b": "dr",
            r"\broad\b": "rd",
            r"\bboulevard\b": "blvd",
            r"\blane\b": "ln",
            r"\bcourt\b": "ct",
            r"\bcircle\b": "cir",
            r"\bplace\b": "pl",
            r"\bapartment\b": "apt",
            r"\bsuite\b": "ste",
            r"\bnorth\b": "n",
            r"\bsouth\b": "s",
            r"\beast\b": "e",
            r"\bwest\b": "w",
        }

        for pattern, replacement in abbreviations.items():
            normalized = re.sub(pattern, replacement, normalized)

        # Remove punctuation and extra spaces
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def are_parishes_duplicate(self, parish1, parish2) -> Tuple[bool, dict]:
        """
        Determine if two parishes are duplicates.

        Args:
            parish1: First Parish object
            parish2: Second Parish object

        Returns:
            Tuple of (is_duplicate: bool, similarity_metrics: dict)
        """
        metrics = {
            "name_similarity": 0.0,
            "address_similarity": 0.0,
            "phone_match": False,
            "website_match": False,
            "is_duplicate": False,
            "reason": "",
        }

        # Calculate name similarity
        name_sim = self.calculate_name_similarity(parish1.name, parish2.name)
        metrics["name_similarity"] = name_sim

        # Calculate address similarity
        addr1 = (
            getattr(parish1, "street_address", None)
            or getattr(parish1, "full_address", None)
            or getattr(parish1, "address", None)
        )
        addr2 = (
            getattr(parish2, "street_address", None)
            or getattr(parish2, "full_address", None)
            or getattr(parish2, "address", None)
        )

        addr_sim = self.calculate_address_similarity(addr1 or "", addr2 or "")
        metrics["address_similarity"] = addr_sim

        # Check phone match
        phone1 = getattr(parish1, "phone", None)
        phone2 = getattr(parish2, "phone", None)
        if phone1 and phone2:
            # Normalize phones (remove non-digits)
            norm_phone1 = re.sub(r"\D", "", phone1)
            norm_phone2 = re.sub(r"\D", "", phone2)
            metrics["phone_match"] = norm_phone1 == norm_phone2 and len(norm_phone1) >= 10

        # Check website match
        website1 = getattr(parish1, "website", None)
        website2 = getattr(parish2, "website", None)
        if website1 and website2:
            metrics["website_match"] = website1.lower().strip() == website2.lower().strip()

        # Determine if duplicate based on criteria
        is_duplicate = False
        reason = ""

        # High name similarity
        if name_sim >= self.name_similarity_threshold:
            is_duplicate = True
            reason = f"High name similarity ({name_sim:.2f})"

            # Even higher confidence with address similarity
            if addr_sim >= self.address_similarity_threshold:
                reason += f" + address similarity ({addr_sim:.2f})"

        # Phone or website exact match with moderate name similarity
        elif (metrics["phone_match"] or metrics["website_match"]) and name_sim >= 0.70:
            is_duplicate = True
            if metrics["phone_match"]:
                reason = f"Phone match + name similarity ({name_sim:.2f})"
            else:
                reason = f"Website match + name similarity ({name_sim:.2f})"

        # Very high address similarity with moderate name similarity
        elif addr_sim >= 0.90 and name_sim >= 0.60:
            is_duplicate = True
            reason = f"High address similarity ({addr_sim:.2f}) + name similarity ({name_sim:.2f})"

        metrics["is_duplicate"] = is_duplicate
        metrics["reason"] = reason

        return is_duplicate, metrics

    def deduplicate_parishes(self, parishes: List) -> Tuple[List, DeduplicationMetrics]:
        """
        Remove duplicate parishes from a list.

        Args:
            parishes: List of Parish objects

        Returns:
            Tuple of (deduplicated_parishes, metrics)
        """
        if not parishes:
            return [], DeduplicationMetrics(0, 0, 0, self.name_similarity_threshold)

        original_count = len(parishes)
        unique_parishes = []
        duplicates_removed = 0

        # Track parishes we've already processed
        processed_indices: Set[int] = set()

        for i, parish in enumerate(parishes):
            if i in processed_indices:
                continue

            # This parish is unique so far
            unique_parishes.append(parish)
            processed_indices.add(i)

            # Check remaining parishes for duplicates
            for j, other_parish in enumerate(parishes[i + 1 :], start=i + 1):
                if j in processed_indices:
                    continue

                is_duplicate, metrics = self.are_parishes_duplicate(parish, other_parish)

                if is_duplicate:
                    # Mark as processed (duplicate)
                    processed_indices.add(j)
                    duplicates_removed += 1

                    # Optionally merge information from duplicate
                    self._merge_parish_info(parish, other_parish)

        deduplicated_count = len(unique_parishes)

        metrics = DeduplicationMetrics(
            original_count=original_count,
            deduplicated_count=deduplicated_count,
            duplicates_removed=duplicates_removed,
            similarity_threshold=self.name_similarity_threshold,
        )

        return unique_parishes, metrics

    def _merge_parish_info(self, primary_parish, duplicate_parish):
        """
        Merge information from duplicate parish into primary parish.

        This helps preserve any additional details that might have been
        extracted differently between the two parishes.
        """
        # Merge missing fields from duplicate to primary
        fields_to_merge = ["phone", "website", "street_address", "full_address", "address", "city", "state", "zip_code"]

        for field in fields_to_merge:
            primary_value = getattr(primary_parish, field, None)
            duplicate_value = getattr(duplicate_parish, field, None)

            # If primary is missing this field but duplicate has it, use duplicate's value
            if not primary_value and duplicate_value:
                setattr(primary_parish, field, duplicate_value)
