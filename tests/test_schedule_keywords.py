#!/usr/bin/env python3
"""
Test script for schedule keywords database functionality.
"""

from dotenv import load_dotenv
from core.db import get_supabase_client
from core.schedule_keywords import (
    load_keywords_from_database, 
    get_all_keywords_for_priority_calculation,
    add_keyword,
    update_keyword_weight
)
from core.logger import get_logger

logger = get_logger(__name__)


def main():
    """Test the schedule keywords functionality."""
    load_dotenv()
    
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Could not initialize Supabase client")
        return
    
    print("Testing Schedule Keywords Database Integration")
    print("=" * 50)
    
    # Test loading keywords
    print("\n1. Loading keywords from database...")
    recon_kw, recon_neg, ador_kw, ador_neg, mass_kw, mass_neg = load_keywords_from_database(supabase)
    
    print(f"Reconciliation keywords: {recon_kw}")
    print(f"Reconciliation negative: {recon_neg}")
    print(f"Adoration keywords: {ador_kw}")
    print(f"Adoration negative: {ador_neg}")
    
    # Test getting all keywords for priority calculation
    print("\n2. Getting combined keywords for priority calculation...")
    all_kw = get_all_keywords_for_priority_calculation(supabase)
    print(f"Combined keywords: {all_kw}")
    
    # Test adding a new keyword
    print("\n3. Testing keyword addition...")
    success = add_keyword(
        supabase, 
        "communion", 
        "adoration", 
        weight=3, 
        description="Related to eucharistic communion"
    )
    print(f"Add keyword result: {success}")
    
    # Test updating keyword weight
    print("\n4. Testing keyword weight update...")
    success = update_keyword_weight(supabase, "communion", "adoration", 4)
    print(f"Update weight result: {success}")
    
    print("\n5. Reloading keywords after changes...")
    recon_kw2, recon_neg2, ador_kw2, ador_neg2, mass_kw2, mass_neg2 = load_keywords_from_database(supabase)
    print(f"Updated adoration keywords: {ador_kw2}")
    
    print("\nSchedule keywords test completed!")


if __name__ == "__main__":
    main()