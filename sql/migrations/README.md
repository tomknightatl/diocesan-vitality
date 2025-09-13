# Database Migrations

This directory contains SQL migration scripts for the USCCB parish schedule extraction system.

## Migration Process

1. **Always run migrations in order** - migrations are numbered sequentially and may depend on previous changes
2. **Review each migration** before applying to understand the changes being made
3. **Backup your database** before applying production migrations
4. **Test migrations** in a development environment first

## Available Migrations

### 001_extend_schedule_types.sql
**Purpose**: Extend ScheduleKeywords table to support 'mass' and 'all' schedule types

**Changes**:
- Modifies the `ScheduleKeywords_schedule_type_check` constraint
- Adds support for `mass` and `all` schedule types alongside existing `reconciliation`, `adoration`, and `both`
- Enables database-driven keyword management for mass times extraction

**Prerequisites**: None

### 002_populate_mass_keywords.sql  
**Purpose**: Populate database with comprehensive mass-related keywords and universal schedule keywords

**Changes**:
- Adds 9 positive mass-specific keywords (`mass`, `masses`, `liturgy`, etc.)
- Adds 7 negative mass keywords to exclude non-mass content
- Adds 5 universal keywords (`parish`, `church`, `catholic`, etc.) with `all` type
- Adds 5 universal negative keywords to improve overall accuracy
- Uses `ON CONFLICT DO NOTHING` to prevent duplicate insertions

**Prerequisites**: 001_extend_schedule_types.sql must be applied first

## How to Apply Migrations

### Using psql (recommended):
```bash
# Connect to your database
psql -h <hostname> -U <username> -d <database>

# Apply migrations in order
\i sql/migrations/001_extend_schedule_types.sql
\i sql/migrations/002_populate_mass_keywords.sql
```

### Using Supabase Dashboard:
1. Go to SQL Editor in your Supabase dashboard
2. Copy and paste the migration content
3. Execute the SQL
4. Verify the results using the provided verification queries

## Verification

After applying migrations, you can verify they worked correctly:

```sql
-- Check that new schedule types are allowed
SELECT DISTINCT schedule_type FROM "ScheduleKeywords" ORDER BY schedule_type;

-- Check keyword counts by type
SELECT 
    schedule_type,
    COUNT(*) FILTER (WHERE NOT is_negative) as positive_keywords,
    COUNT(*) FILTER (WHERE is_negative) as negative_keywords,
    COUNT(*) as total_keywords
FROM "ScheduleKeywords" 
WHERE is_active = true
GROUP BY schedule_type
ORDER BY schedule_type;

-- Show total keywords in database
SELECT COUNT(*) as total_active_keywords FROM "ScheduleKeywords" WHERE is_active = true;
```

Expected results after both migrations:
- `reconciliation`: ~8 positive, ~4 negative keywords
- `adoration`: ~9 positive, ~5 negative keywords  
- `both`: ~5 positive, ~0 negative keywords
- `mass`: ~9 positive, ~7 negative keywords
- `all`: ~5 positive, ~5 negative keywords
- **Total**: ~60+ keywords

## Rollback

If you need to rollback migrations:

### Rollback 002_populate_mass_keywords.sql:
```sql
DELETE FROM "ScheduleKeywords" WHERE schedule_type IN ('mass', 'all');
```

### Rollback 001_extend_schedule_types.sql:
```sql
ALTER TABLE "ScheduleKeywords" 
DROP CONSTRAINT IF EXISTS "ScheduleKeywords_schedule_type_check";

ALTER TABLE "ScheduleKeywords" 
ADD CONSTRAINT "ScheduleKeywords_schedule_type_check" 
CHECK (schedule_type IN ('reconciliation', 'adoration', 'both'));
```

⚠️ **Warning**: Rollback will delete all mass and universal keywords. Only rollback if you're sure you want to lose this data.

## Integration with Code

After applying these migrations, the system will:

1. **Load keywords from database first** - `load_keywords_from_database()` will find mass keywords in DB
2. **Use fallback system as backup** - If database loading fails, fallback keywords still work
3. **Support all three schedule types** - reconciliation, adoration, and mass schedules
4. **Benefit from centralized keyword management** - Keywords can be updated via database instead of code changes

The existing AI extraction and Priority 3 enhancements will automatically work with the database-driven keywords once these migrations are applied.