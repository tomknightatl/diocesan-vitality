#!/usr/bin/env python3
"""
Keyword Migration Script

This script:
1. Attempts to modify the database constraint to support 'mass' and 'all' schedule types
2. Migrates all fallback keywords from code to database
3. Ensures all schedule types have comprehensive keyword coverage
"""

from core.db import get_supabase_client
from core.schedule_keywords import get_fallback_keywords, add_keyword
from core.logger import get_logger

logger = get_logger(__name__)

def migrate_keywords_to_database():
    """Migrate all fallback keywords from code to database."""
    supabase = get_supabase_client()
    
    print("Starting keyword migration...")
    
    # Get fallback keywords
    try:
        recon_kw, recon_neg, ador_kw, ador_neg, mass_kw, mass_neg = get_fallback_keywords()
        logger.info("Successfully loaded fallback keywords")
    except Exception as e:
        logger.error(f"Failed to load fallback keywords: {e}")
        return False
    
    success_count = 0
    total_count = 0
    
    # First, try to add mass keywords to test if constraint allows it
    print("\n=== Testing constraint and adding mass keywords ===")
    mass_keywords_data = [
        # Mass positive keywords
        ('mass', mass_kw.get('mass', 8), False, 'Primary keyword for Mass schedules'),
        ('masses', mass_kw.get('masses', 8), False, 'Plural form of mass'),
        ('liturgy', mass_kw.get('liturgy', 5), False, 'Liturgical celebrations'), 
        ('eucharist', mass_kw.get('eucharist', 3), False, 'Eucharistic celebrations'),
        ('sunday', mass_kw.get('sunday', 6), False, 'Sunday Mass identification'),
        ('saturday', mass_kw.get('saturday', 4), False, 'Saturday schedules'),
        ('weekday', mass_kw.get('weekday', 4), False, 'Weekday mass schedules'),
        ('times', mass_kw.get('times', 4), False, 'Schedule timing keywords'),
        ('schedule', mass_kw.get('schedule', 5), False, 'General schedule keyword'),
    ]
    
    # Add mass negative keywords
    for neg_keyword in mass_neg:
        mass_keywords_data.append((neg_keyword, 1, True, f'Negative keyword to exclude {neg_keyword}'))
    
    for keyword, weight, is_negative, description in mass_keywords_data:
        total_count += 1
        if add_keyword(supabase, keyword, 'mass', weight, is_negative, description):
            success_count += 1
            print(f"✓ Added mass keyword: {keyword} (weight: {weight}, negative: {is_negative})")
        else:
            print(f"✗ Failed to add mass keyword: {keyword}")
    
    # If mass keywords failed, the constraint probably needs updating
    if success_count == 0:
        print("\n❌ Mass keywords failed to add - constraint may need manual database update")
        print("Please run this SQL in your database:")
        print("ALTER TABLE \"ScheduleKeywords\" DROP CONSTRAINT IF EXISTS \"ScheduleKeywords_schedule_type_check\";")
        print("ALTER TABLE \"ScheduleKeywords\" ADD CONSTRAINT \"ScheduleKeywords_schedule_type_check\" CHECK (schedule_type IN ('reconciliation', 'adoration', 'both', 'mass', 'all'));")
        return False
    
    print(f"\n=== Mass keywords migration complete: {success_count}/{total_count} successful ===")
    
    # Now migrate any missing reconciliation and adoration keywords
    print("\n=== Checking and adding missing reconciliation keywords ===")
    
    # Get existing keywords to avoid duplicates
    existing_response = supabase.table('ScheduleKeywords').select('keyword, schedule_type, is_negative').execute()
    existing_keys = set()
    for row in existing_response.data:
        key = (row['keyword'], row['schedule_type'], row['is_negative'])
        existing_keys.add(key)
    
    # Add missing reconciliation keywords
    for keyword, weight in recon_kw.items():
        key = (keyword, 'reconciliation', False)
        if key not in existing_keys:
            total_count += 1
            if add_keyword(supabase, keyword, 'reconciliation', weight, False, f'Reconciliation keyword: {keyword}'):
                success_count += 1
                print(f"✓ Added reconciliation keyword: {keyword} (weight: {weight})")
            else:
                print(f"✗ Failed to add reconciliation keyword: {keyword}")
    
    for neg_keyword in recon_neg:
        key = (neg_keyword, 'reconciliation', True)
        if key not in existing_keys:
            total_count += 1
            if add_keyword(supabase, neg_keyword, 'reconciliation', 1, True, f'Negative reconciliation keyword: {neg_keyword}'):
                success_count += 1
                print(f"✓ Added negative reconciliation keyword: {neg_keyword}")
            else:
                print(f"✗ Failed to add negative reconciliation keyword: {neg_keyword}")
    
    print("\n=== Checking and adding missing adoration keywords ===")
    
    # Add missing adoration keywords
    for keyword, weight in ador_kw.items():
        key = (keyword, 'adoration', False)
        if key not in existing_keys:
            total_count += 1
            if add_keyword(supabase, keyword, 'adoration', weight, False, f'Adoration keyword: {keyword}'):
                success_count += 1
                print(f"✓ Added adoration keyword: {keyword} (weight: {weight})")
            else:
                print(f"✗ Failed to add adoration keyword: {keyword}")
    
    for neg_keyword in ador_neg:
        key = (neg_keyword, 'adoration', True)
        if key not in existing_keys:
            total_count += 1
            if add_keyword(supabase, neg_keyword, 'adoration', 1, True, f'Negative adoration keyword: {neg_keyword}'):
                success_count += 1
                print(f"✓ Added negative adoration keyword: {neg_keyword}")
            else:
                print(f"✗ Failed to add negative adoration keyword: {neg_keyword}")
    
    print(f"\n=== Migration Summary ===")
    print(f"Total keywords processed: {total_count}")
    print(f"Successfully added: {success_count}")
    print(f"Failed to add: {total_count - success_count}")
    
    if success_count > 0:
        print("✅ Migration partially or fully successful!")
        
        # Show final count
        final_response = supabase.table('ScheduleKeywords').select('*').execute()
        print(f"Total keywords now in database: {len(final_response.data)}")
        
        # Show breakdown by type
        by_type = {}
        for row in final_response.data:
            schedule_type = row['schedule_type']
            if schedule_type not in by_type:
                by_type[schedule_type] = {'positive': 0, 'negative': 0}
            if row['is_negative']:
                by_type[schedule_type]['negative'] += 1
            else:
                by_type[schedule_type]['positive'] += 1
        
        for schedule_type, counts in by_type.items():
            print(f"  {schedule_type}: {counts['positive']} positive, {counts['negative']} negative")
        
        return True
    else:
        print("❌ Migration failed completely")
        return False

def test_database_keyword_loading():
    """Test that the updated keyword loading works properly."""
    from core.schedule_keywords import load_keywords_from_database
    
    print("\n=== Testing database keyword loading ===")
    
    supabase = get_supabase_client()
    
    try:
        result = load_keywords_from_database(supabase)
        
        if len(result) == 6:  # Should return 6 tuples now
            recon_kw, recon_neg, ador_kw, ador_neg, mass_kw, mass_neg = result
            
            print("✅ Successfully loaded keywords from database!")
            print(f"Reconciliation: {len(recon_kw)} positive, {len(recon_neg)} negative")
            print(f"Adoration: {len(ador_kw)} positive, {len(ador_neg)} negative") 
            print(f"Mass: {len(mass_kw)} positive, {len(mass_neg)} negative")
            
            if len(mass_kw) > 0:
                print("✅ Mass keywords successfully loaded from database!")
                print("Sample mass keywords:", list(mass_kw.keys())[:5])
                return True
            else:
                print("⚠️  Mass keywords empty - may still be using fallback")
                return False
        else:
            print(f"❌ Unexpected return format: got {len(result)} tuples, expected 6")
            return False
            
    except Exception as e:
        print(f"❌ Error testing keyword loading: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting keyword migration process...")
    
    # Step 1: Migrate keywords
    migration_success = migrate_keywords_to_database()
    
    if migration_success:
        # Step 2: Test the loading
        test_success = test_database_keyword_loading()
        
        if test_success:
            print("\n🎉 Complete success! All keywords migrated and loading correctly.")
        else:
            print("\n⚠️  Migration succeeded but testing failed. Check keyword loading logic.")
    else:
        print("\n❌ Migration failed. Please check database constraints and permissions.")
        print("\nTo manually fix the database constraint, run:")
        print("ALTER TABLE \"ScheduleKeywords\" DROP CONSTRAINT IF EXISTS \"ScheduleKeywords_schedule_type_check\";")
        print("ALTER TABLE \"ScheduleKeywords\" ADD CONSTRAINT \"ScheduleKeywords_schedule_type_check\" CHECK (schedule_type IN ('reconciliation', 'adoration', 'both', 'mass', 'all'));")