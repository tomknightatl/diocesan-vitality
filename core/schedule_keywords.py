#!/usr/bin/env python3
"""
Schedule Keywords Database Integration

This module provides functionality to load schedule extraction keywords
from the ScheduleKeywords database table instead of hardcoding them.
"""

from typing import Any, Dict, List, Tuple

from core.logger import get_logger
from supabase import Client

logger = get_logger(__name__)


def load_keywords_from_database(
    supabase: Client,
) -> Tuple[Dict[str, int], List[str], Dict[str, int], List[str], Dict[str, int], List[str]]:
    """
    Loads reconciliation, adoration, and mass times keywords from the ScheduleKeywords database table.

    Returns:
        Tuple containing:
        - reconciliation_keywords: Dict of positive reconciliation keywords and their weights
        - reconciliation_negative_keywords: List of negative reconciliation keywords
        - adoration_keywords: Dict of positive adoration keywords and their weights
        - adoration_negative_keywords: List of negative adoration keywords
        - mass_keywords: Dict of positive mass times keywords and their weights
        - mass_negative_keywords: List of negative mass times keywords
    """
    try:
        response = _fetch_keywords_from_database(supabase)
        if not response.data:
            logger.warning("No schedule keywords found in database, using fallback defaults")
            return get_fallback_keywords()

        keyword_containers = _initialize_keyword_containers()
        _process_keyword_rows(response.data, keyword_containers)
        _log_keyword_statistics(keyword_containers)

        return _build_keyword_tuple(keyword_containers)

    except Exception as e:
        logger.error(f"Error loading keywords from database: {e}")
        logger.info("Falling back to hardcoded keywords")
        return get_fallback_keywords()


def _fetch_keywords_from_database(supabase: Client):
    """Fetch all active keywords from the database"""
    return (
        supabase.table("ScheduleKeywords")
        .select("keyword, schedule_type, weight, is_negative")
        .eq("is_active", True)
        .execute()
    )


def _initialize_keyword_containers() -> Dict[str, Any]:
    """Initialize keyword storage containers"""
    return {
        "reconciliation_keywords": {},
        "reconciliation_negative": [],
        "adoration_keywords": {},
        "adoration_negative": [],
        "mass_keywords": {},
        "mass_negative": [],
    }


def _process_keyword_rows(rows: List[Dict], containers: Dict[str, Any]):
    """Process each keyword row and categorize appropriately"""
    for row in rows:
        keyword = row["keyword"]
        schedule_type = row["schedule_type"]
        weight = row["weight"]
        is_negative = row["is_negative"]

        if schedule_type == "reconciliation":
            _add_reconciliation_keyword(keyword, weight, is_negative, containers)
        elif schedule_type == "adoration":
            _add_adoration_keyword(keyword, weight, is_negative, containers)
        elif schedule_type == "mass":
            _add_mass_keyword(keyword, weight, is_negative, containers)
        elif schedule_type == "both":
            _add_both_keyword(keyword, weight, is_negative, containers)
        elif schedule_type == "all":
            _add_all_keyword(keyword, weight, is_negative, containers)


def _add_reconciliation_keyword(keyword: str, weight: int, is_negative: bool, containers: Dict[str, Any]):
    """Add keyword to reconciliation category"""
    if is_negative:
        containers["reconciliation_negative"].append(keyword)
    else:
        containers["reconciliation_keywords"][keyword] = weight


def _add_adoration_keyword(keyword: str, weight: int, is_negative: bool, containers: Dict[str, Any]):
    """Add keyword to adoration category"""
    if is_negative:
        containers["adoration_negative"].append(keyword)
    else:
        containers["adoration_keywords"][keyword] = weight


def _add_mass_keyword(keyword: str, weight: int, is_negative: bool, containers: Dict[str, Any]):
    """Add keyword to mass category"""
    if is_negative:
        containers["mass_negative"].append(keyword)
    else:
        containers["mass_keywords"][keyword] = weight


def _add_both_keyword(keyword: str, weight: int, is_negative: bool, containers: Dict[str, Any]):
    """Add keyword to both reconciliation and adoration categories"""
    if is_negative:
        containers["reconciliation_negative"].append(keyword)
        containers["adoration_negative"].append(keyword)
    else:
        containers["reconciliation_keywords"][keyword] = weight
        containers["adoration_keywords"][keyword] = weight


def _add_all_keyword(keyword: str, weight: int, is_negative: bool, containers: Dict[str, Any]):
    """Add keyword to all categories (reconciliation, adoration, mass)"""
    if is_negative:
        containers["reconciliation_negative"].append(keyword)
        containers["adoration_negative"].append(keyword)
        containers["mass_negative"].append(keyword)
    else:
        containers["reconciliation_keywords"][keyword] = weight
        containers["adoration_keywords"][keyword] = weight
        containers["mass_keywords"][keyword] = weight


def _log_keyword_statistics(containers: Dict[str, Any]):
    """Log statistics about loaded keywords"""
    logger.info(
        f"Loaded from database: {len(containers['reconciliation_keywords'])} reconciliation keywords, "
        f"{len(containers['reconciliation_negative'])} reconciliation negative keywords, "
        f"{len(containers['adoration_keywords'])} adoration keywords, "
        f"{len(containers['adoration_negative'])} adoration negative keywords, "
        f"{len(containers['mass_keywords'])} mass keywords, "
        f"{len(containers['mass_negative'])} mass negative keywords"
    )


def _build_keyword_tuple(
    containers: Dict[str, Any],
) -> Tuple[Dict[str, int], List[str], Dict[str, int], List[str], Dict[str, int], List[str]]:
    """Build the final tuple return value from containers"""
    return (
        containers["reconciliation_keywords"],
        containers["reconciliation_negative"],
        containers["adoration_keywords"],
        containers["adoration_negative"],
        containers["mass_keywords"],
        containers["mass_negative"],
    )


def get_fallback_keywords() -> Tuple[Dict[str, int], List[str], Dict[str, int], List[str], Dict[str, int], List[str]]:
    """
    Returns hardcoded fallback keywords if database loading fails.
    """
    # Original hardcoded keywords from extract_schedule.py
    reconciliation_keywords = {
        "reconciliation": 5,
        "confession": 5,
        "schedule": 8,
        "times": 3,
        "sacrament": 1,
    }

    reconciliation_negative = ["adoration", "baptism", "donate", "giving"]

    adoration_keywords = {"adoration": 5, "eucharist": 5, "schedule": 3, "times": 3}

    adoration_negative = [
        "reconciliation",
        "confession",
        "baptism",
        "donate",
        "giving",
    ]

    mass_keywords = {
        "mass": 8,
        "masses": 8,
        "liturgy": 5,
        "eucharist": 3,
        "schedule": 5,
        "times": 4,
        "sunday": 6,
        "weekday": 4,
        "saturday": 4,
    }

    mass_negative = [
        "adoration",
        "reconciliation",
        "confession",
        "baptism",
        "donate",
        "giving",
        "meeting",
    ]

    logger.info("Using fallback hardcoded keywords")
    return (
        reconciliation_keywords,
        reconciliation_negative,
        adoration_keywords,
        adoration_negative,
        mass_keywords,
        mass_negative,
    )


def get_all_keywords_for_priority_calculation(supabase: Client) -> Dict[str, int]:
    """
    Gets combined keywords dictionary for URL priority calculation.
    Merges reconciliation, adoration, and mass keywords, taking the higher weight if there are duplicates.
    """
    recon_kw, _, ador_kw, _, mass_kw, _ = load_keywords_from_database(supabase)

    # Merge dictionaries, taking higher weight for duplicate keys
    all_keywords = recon_kw.copy()
    for keyword, weight in ador_kw.items():
        if keyword in all_keywords:
            all_keywords[keyword] = max(all_keywords[keyword], weight)
        else:
            all_keywords[keyword] = weight

    for keyword, weight in mass_kw.items():
        if keyword in all_keywords:
            all_keywords[keyword] = max(all_keywords[keyword], weight)
        else:
            all_keywords[keyword] = weight

    return all_keywords


def add_keyword(
    supabase: Client,
    keyword: str,
    schedule_type: str,
    weight: int = 1,
    is_negative: bool = False,
    description: str | None = None,
) -> bool:
    """
    Adds a new keyword to the database.

    Args:
        supabase: Supabase client
        keyword: The keyword to add
        schedule_type: 'reconciliation', 'adoration', 'mass', 'both', or 'all'
        weight: Weight/importance of the keyword (higher = more important)
        is_negative: Whether this is a negative (exclusion) keyword
        description: Optional description of the keyword

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        data = {
            "keyword": keyword.lower(),
            "schedule_type": schedule_type,
            "weight": weight,
            "is_negative": is_negative,
            "is_active": True,
        }

        if description:
            data["description"] = description

        response = supabase.table("ScheduleKeywords").insert(data).execute()

        if response.data:
            logger.info(f"Successfully added keyword '{keyword}' for {schedule_type}")
            return True
        else:
            logger.error(f"Failed to add keyword '{keyword}'")
            return False

    except Exception as e:
        logger.error(f"Error adding keyword '{keyword}': {e}")
        return False


def update_keyword_weight(supabase: Client, keyword: str, schedule_type: str, new_weight: int) -> bool:
    """
    Updates the weight of an existing keyword.

    Args:
        supabase: Supabase client
        keyword: The keyword to update
        schedule_type: The schedule type to update
        new_weight: New weight value

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        response = (
            supabase.table("ScheduleKeywords")
            .update({"weight": new_weight})
            .eq("keyword", keyword.lower())
            .eq("schedule_type", schedule_type)
            .execute()
        )

        if response.data:
            logger.info(f"Updated weight for '{keyword}' ({schedule_type}) to {new_weight}")
            return True
        else:
            logger.error(f"Failed to update weight for '{keyword}'")
            return False

    except Exception as e:
        logger.error(f"Error updating keyword weight: {e}")
        return False


def deactivate_keyword(supabase: Client, keyword: str, schedule_type: str) -> bool:
    """
    Deactivates a keyword (sets is_active = false) instead of deleting it.

    Args:
        supabase: Supabase client
        keyword: The keyword to deactivate
        schedule_type: The schedule type to deactivate

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        response = (
            supabase.table("ScheduleKeywords")
            .update({"is_active": False})
            .eq("keyword", keyword.lower())
            .eq("schedule_type", schedule_type)
            .execute()
        )

        if response.data:
            logger.info(f"Deactivated keyword '{keyword}' for {schedule_type}")
            return True
        else:
            logger.error(f"Failed to deactivate keyword '{keyword}'")
            return False

    except Exception as e:
        logger.error(f"Error deactivating keyword: {e}")
        return False
