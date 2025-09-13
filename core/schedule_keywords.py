#!/usr/bin/env python3
"""
Schedule Keywords Database Integration

This module provides functionality to load schedule extraction keywords
from the ScheduleKeywords database table instead of hardcoding them.
"""

from typing import Dict, List, Tuple
from supabase import Client
from core.logger import get_logger

logger = get_logger(__name__)


def load_keywords_from_database(supabase: Client) -> Tuple[Dict[str, int], List[str], Dict[str, int], List[str], Dict[str, int], List[str]]:
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
        # Fetch all active keywords from database
        response = supabase.table('ScheduleKeywords')\
            .select('keyword, schedule_type, weight, is_negative')\
            .eq('is_active', True)\
            .execute()
        
        if not response.data:
            logger.warning("No schedule keywords found in database, using fallback defaults")
            return get_fallback_keywords()
        
        # Initialize containers
        reconciliation_keywords = {}
        reconciliation_negative = []
        adoration_keywords = {}
        adoration_negative = []
        mass_keywords = {}
        mass_negative = []
        
        # Process each keyword
        for row in response.data:
            keyword = row['keyword']
            schedule_type = row['schedule_type']
            weight = row['weight']
            is_negative = row['is_negative']
            
            if schedule_type == 'reconciliation':
                if is_negative:
                    reconciliation_negative.append(keyword)
                else:
                    reconciliation_keywords[keyword] = weight
                    
            elif schedule_type == 'adoration':
                if is_negative:
                    adoration_negative.append(keyword)
                else:
                    adoration_keywords[keyword] = weight
                    
            elif schedule_type == 'mass':
                if is_negative:
                    mass_negative.append(keyword)
                else:
                    mass_keywords[keyword] = weight
                    
            elif schedule_type == 'both':
                if is_negative:
                    reconciliation_negative.append(keyword)
                    adoration_negative.append(keyword)
                else:
                    reconciliation_keywords[keyword] = weight
                    adoration_keywords[keyword] = weight
                    
            elif schedule_type == 'all':
                if is_negative:
                    reconciliation_negative.append(keyword)
                    adoration_negative.append(keyword)
                    mass_negative.append(keyword)
                else:
                    reconciliation_keywords[keyword] = weight
                    adoration_keywords[keyword] = weight
                    mass_keywords[keyword] = weight
        
        logger.info(f"Loaded from database: {len(reconciliation_keywords)} reconciliation keywords, "
                   f"{len(reconciliation_negative)} reconciliation negative keywords, "
                   f"{len(adoration_keywords)} adoration keywords, "
                   f"{len(adoration_negative)} adoration negative keywords, "
                   f"{len(mass_keywords)} mass keywords, "
                   f"{len(mass_negative)} mass negative keywords")
        
        return (reconciliation_keywords, reconciliation_negative, 
                adoration_keywords, adoration_negative, 
                mass_keywords, mass_negative)
                
    except Exception as e:
        logger.error(f"Error loading keywords from database: {e}")
        logger.info("Falling back to hardcoded keywords")
        return get_fallback_keywords()


def get_fallback_keywords() -> Tuple[Dict[str, int], List[str], Dict[str, int], List[str], Dict[str, int], List[str]]:
    """
    Returns hardcoded fallback keywords if database loading fails.
    """
    # Original hardcoded keywords from extract_schedule.py
    reconciliation_keywords = {
        'reconciliation': 5, 
        'confession': 5, 
        'schedule': 8, 
        'times': 3, 
        'sacrament': 1
    }
    
    reconciliation_negative = ['adoration', 'baptism', 'donate', 'giving']
    
    adoration_keywords = {
        'adoration': 5, 
        'eucharist': 5, 
        'schedule': 3, 
        'times': 3
    }
    
    adoration_negative = ['reconciliation', 'confession', 'baptism', 'donate', 'giving']
    
    mass_keywords = {
        'mass': 8,
        'masses': 8, 
        'liturgy': 5,
        'eucharist': 3,
        'schedule': 5,
        'times': 4,
        'sunday': 6,
        'weekday': 4,
        'saturday': 4
    }
    
    mass_negative = ['adoration', 'reconciliation', 'confession', 'baptism', 'donate', 'giving', 'meeting']
    
    logger.info("Using fallback hardcoded keywords")
    return (reconciliation_keywords, reconciliation_negative, 
            adoration_keywords, adoration_negative,
            mass_keywords, mass_negative)


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


def add_keyword(supabase: Client, keyword: str, schedule_type: str, weight: int = 1, 
                is_negative: bool = False, description: str = None) -> bool:
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
            'keyword': keyword.lower(),
            'schedule_type': schedule_type,
            'weight': weight,
            'is_negative': is_negative,
            'is_active': True
        }
        
        if description:
            data['description'] = description
            
        response = supabase.table('ScheduleKeywords').insert(data).execute()
        
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
        response = supabase.table('ScheduleKeywords')\
            .update({'weight': new_weight})\
            .eq('keyword', keyword.lower())\
            .eq('schedule_type', schedule_type)\
            .execute()
            
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
        response = supabase.table('ScheduleKeywords')\
            .update({'is_active': False})\
            .eq('keyword', keyword.lower())\
            .eq('schedule_type', schedule_type)\
            .execute()
            
        if response.data:
            logger.info(f"Deactivated keyword '{keyword}' for {schedule_type}")
            return True
        else:
            logger.error(f"Failed to deactivate keyword '{keyword}'")
            return False
            
    except Exception as e:
        logger.error(f"Error deactivating keyword: {e}")
        return False