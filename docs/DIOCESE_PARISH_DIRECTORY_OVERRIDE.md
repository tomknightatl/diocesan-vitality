# Diocese Parish Directory Override System

## Overview

The Diocese Parish Directory Override system allows manual specification of parish directory URLs when the automated discovery process fails or finds incorrect URLs. This system provides a manual override mechanism for Step 3 (Parish Extraction) of the pipeline.

## Database Schema

### DioceseParishDirectoryOverride Table

The `DioceseParishDirectoryOverride` table has the same structure as `DiocesesParishDirectory`:

```sql
CREATE TABLE "public"."DioceseParishDirectoryOverride" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "diocese_url" character varying,           -- Diocese website URL
    "parish_directory_url" character varying,  -- Override parish directory URL
    "found" character varying,                 -- Status/reason for override
    "found_method" character varying,          -- Method used to find override
    "updated_at" character varying,            -- When override was last updated
    "diocese_id" integer                       -- Foreign key to Dioceses.id
);
```

## How It Works

### Priority System

When Step 3 (Parish Extraction) runs, the system uses this priority order:

1. **Override Table First**: Check `DioceseParishDirectoryOverride` for the diocese_id
2. **Original Table Fallback**: If no override exists, use `DiocesesParishDirectory`
3. **Skip Diocese**: If neither table has a URL, skip the diocese

### Implementation

The `get_parish_directory_url_with_override()` function in `async_extract_parishes.py` handles this logic:

```python
def get_parish_directory_url_with_override(supabase, diocese_id: int, diocese_url: str) -> tuple:
    # Check override table first
    override_response = supabase.table('DioceseParishDirectoryOverride').select(
        'parish_directory_url, found_method'
    ).eq('diocese_id', diocese_id).execute()

    if override_response.data:
        return override_url, 'override'

    # Fallback to original table
    original_response = supabase.table('DiocesesParishDirectory').select(
        'parish_directory_url'
    ).eq('diocese_url', diocese_url).execute()

    return original_url, 'original'
```

## Usage Examples

### 1. Adding an Override

```sql
-- Add override for Archdiocese of Atlanta (diocese_id = 2024)
INSERT INTO "public"."DioceseParishDirectoryOverride"
(diocese_id, diocese_url, parish_directory_url, found, found_method, updated_at)
VALUES
(2024, 'https://archatl.com', 'https://archatl.com/parishes-directory', 'manual override', 'manual', NOW()::text);
```

### 2. Viewing All Overrides

```sql
SELECT
    o.diocese_id,
    d.Name as diocese_name,
    o.diocese_url,
    o.parish_directory_url,
    o.found,
    o.found_method,
    o.created_at
FROM "public"."DioceseParishDirectoryOverride" o
LEFT JOIN "public"."Dioceses" d ON o.diocese_id = d.id
ORDER BY o.created_at DESC;
```

### 3. Checking URL Resolution

```sql
-- See which URL will be used for a specific diocese
SELECT
    d.id as diocese_id,
    d.Name as diocese_name,
    COALESCE(override.parish_directory_url, original.parish_directory_url) as parish_directory_url,
    CASE
        WHEN override.parish_directory_url IS NOT NULL THEN 'override'
        ELSE 'original'
    END as source
FROM "public"."Dioceses" d
LEFT JOIN "public"."DiocesesParishDirectory" original ON d.id = original.diocese_id
LEFT JOIN "public"."DioceseParishDirectoryOverride" override ON d.id = override.diocese_id
WHERE d.id = 2024;
```

### 4. Updating an Override

```sql
-- Update existing override
UPDATE "public"."DioceseParishDirectoryOverride"
SET
    parish_directory_url = 'https://new-parish-directory-url.com',
    found = 'URL corrected',
    found_method = 'manual correction',
    updated_at = NOW()::text
WHERE diocese_id = 2024;
```

### 5. Removing an Override

```sql
-- Remove override (will fall back to original table)
DELETE FROM "public"."DioceseParishDirectoryOverride"
WHERE diocese_id = 2024;
```

## When to Use Overrides

### Common Scenarios

1. **Automated Discovery Failed**: Step 2 couldn't find the parish directory page
2. **Wrong URL Found**: Step 2 found a page that isn't actually the parish directory
3. **Website Structure Changed**: Diocese updated their website structure
4. **Better URL Available**: A more complete or accurate parish directory page exists

### Best Practices

1. **Document the Reason**: Use descriptive values in `found` and `found_method` fields
2. **Include Diocese ID**: Always specify the `diocese_id` for proper foreign key relationship
3. **Test the URL**: Verify the override URL actually works before adding it
4. **Use Current Timestamp**: Set `updated_at` to track when the override was made

## Monitoring and Logging

### Log Messages

When Step 3 runs, you'll see these log messages indicating override usage:

```
🔄 Using override parish directory URL for diocese 2024: https://archatl.com/parishes-directory (method: manual)
✅ Found parish directory URL for Archdiocese of Atlanta (source: override)
```

### Tracking Usage

The system adds a `url_source` field to the processing data to track whether each diocese used an override or original URL.

## Database Setup

To create the override table, run:

```bash
# Execute the SQL file
psql -h [hostname] -U [username] -d [database] -f sql/create_diocese_parish_directory_override.sql
```

Or execute the SQL commands directly in your database client.

## Integration Points

### Scripts That Use Overrides

- **async_extract_parishes.py**: Main Step 3 script that processes parishes
- **run_pipeline.py**: Pipeline orchestrator that calls Step 3

### Functions That Check Overrides

- **get_parish_directory_url_with_override()**: Core override resolution function
- All diocese processing logic in Step 3

## Future Enhancements

Potential improvements to the override system:

1. **Web UI**: Admin interface to manage overrides
2. **Validation**: Automatic checking of override URLs
3. **History**: Track changes to override URLs over time
4. **Bulk Import**: CSV-based override management
5. **Notifications**: Alert when overrides are used or needed