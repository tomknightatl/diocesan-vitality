# Supabase CLI Migration Command Reference Guide

This comprehensive guide documents Supabase CLI's migration and schema management capabilities for the Diocesan Vitality project. It covers all essential commands, best practices, and common scenarios for database schema management.

## Table of Contents

1. [Overview](#overview)
2. [Core Migration Commands](#core-migration-commands)
3. [Database Schema Commands](#database-schema-commands)
4. [Advanced Migration Operations](#advanced-migration-operations)
5. [Best Practices](#best-practices)
6. [Common Scenarios](#common-scenarios)
7. [Troubleshooting](#troubleshooting)
8. [Integration with Project Workflow](#integration-with-project-workflow)

---

## Overview

Supabase CLI provides a comprehensive set of tools for managing database migrations and schema changes. The project uses Supabase for local development with the following configuration:

- **Project ID**: `diocesan-vitality`
- **Local Database Port**: `54322`
- **Shadow Database Port**: `54320` (for diff operations)
- **Migration Directory**: `supabase/migrations/`
- **Config File**: `supabase/config.toml`

### Key Concepts

- **Migrations**: Version-controlled SQL files that track schema changes
- **Shadow Database**: Temporary database used for generating schema diffs
- **Local vs Remote**: Commands can target local development or remote production databases
- **Migration History**: Tracked in `supabase_migrations` schema table

---

## Core Migration Commands

### `supabase migration new`

Creates a new empty migration file with timestamp prefix.

**Purpose**: Initialize a new migration for schema changes

**Syntax**:
```bash
supabase migration new <migration_name>
```

**Example**:
```bash
supabase migration new add_user_preferences_table
```

**Output**: Creates file like `supabase/migrations/20260621150000_add_user_preferences_table.sql`

**Best Practices**:
- Use descriptive, snake_case names
- One logical change per migration
- Include timestamp in commit messages for traceability

**Common Pitfalls**:
- Creating migrations without applying them
- Using non-descriptive names
- Not following naming conventions

---

### `supabase migration list`

Lists migration status for local and remote databases.

**Purpose**: View migration history and sync status

**Syntax**:
```bash
supabase migration list [flags]
```

**Flags**:
- `--local`: List migrations applied to local database
- `--linked`: List migrations applied to linked project
- `--db-url <url>`: List migrations for specific database
- `--password <pwd>`: Password for remote database

**Example**:
```bash
supabase migration list --local
```

**Output**:
```
Connecting to local database...

  Local          | Remote         | Time (UTC)          
  ----------------|----------------|---------------------
  20260621145819 | 20260621145819 | 2026-06-21 14:58:19 
  20260621150000 | 20260621150000 | 2026-06-21 15:00:00 
```

**Best Practices**:
- Check migration status before deploying
- Verify local and remote are in sync
- Use in CI/CD pipelines for validation

---

### `supabase migration up`

Applies pending migrations to a database.

**Purpose**: Execute new migrations on target database

**Syntax**:
```bash
supabase migration up [flags]
```

**Flags**:
- `--local`: Apply to local database (default)
- `--linked`: Apply to linked project
- `--db-url <url>`: Apply to specific database
- `--include-all`: Include all migrations not in remote history

**Example**:
```bash
supabase migration up --local
```

**Output**:
```
Connecting to local database...
Applying migration 20260621150000_add_user_preferences.sql...
Local database is up to date.
```

**Best Practices**:
- Test migrations locally first
- Use `--dry-run` with `db push` for testing
- Always backup before applying to production

**Common Pitfalls**:
- Applying migrations out of order
- Not testing data migrations
- Missing dependencies between migrations

---

### `supabase migration down`

Reverts applied migrations (destructive operation).

**Purpose**: Rollback migrations to previous state

**Syntax**:
```bash
supabase migration down [flags]
```

**Flags**:
- `--local`: Revert on local database (default)
- `--linked`: Revert on linked project
- `--db-url <url>`: Revert on specific database
- `--last <n>`: Revert last n migrations
- `--yes`: Skip confirmation prompt

**Example**:
```bash
supabase migration down --local --last 1 --yes
```

**Output**:
```
Connecting to local database...
Resetting database to version: 20260621145819
NOTICE (00000): dropping table: public.user_preferences
```

**⚠️ Warning**: This is a destructive operation that will lose data.

**Best Practices**:
- Use only in local development
- Never use in production without careful planning
- Consider data backup before reverting
- Use `--yes` only in automated scripts

**Common Pitfalls**:
- Losing production data
- Breaking foreign key constraints
- Not considering dependent migrations

---

### `supabase migration repair`

Repairs migration history table.

**Purpose**: Fix migration history when it gets out of sync

**Syntax**:
```bash
supabase migration repair <version> [flags]
```

**Flags**:
- `--local`: Repair local database (default)
- `--linked`: Repair linked project
- `--db-url <url>`: Repair specific database
- `--status <applied|reverted>`: Set migration status
- `--password <pwd>`: Password for remote database

**Example**:
```bash
supabase migration repair 20260621150000 --status applied --local
```

**Use Cases**:
- Manual migration execution outside CLI
- Failed migration recovery
- History table corruption

**Best Practices**:
- Use only when absolutely necessary
- Verify database state before repairing
- Document repair operations

---

### `supabase migration squash`

Combines multiple migrations into a single file.

**Purpose**: Consolidate migration history for cleaner management

**Syntax**:
```bash
supabase migration squash [flags]
```

**Flags**:
- `--local`: Squash local migrations (default)
- `--linked`: Squash linked project migrations
- `--db-url <url>`: Squash specific database migrations
- `--version <ver>`: Squash up to specific version
- `--password <pwd>`: Password for remote database

**Example**:
```bash
supabase migration squash --local --version 20260621150000
```

**Best Practices**:
- Use during major refactoring
- Keep squashed migrations logically grouped
- Test thoroughly after squashing

**Common Pitfalls**:
- Losing intermediate migration states
- Breaking deployment pipelines
- Not updating documentation

---

### `supabase migration fetch`

Retrieves migration files from database history.

**Purpose**: Extract migration SQL from applied migrations

**Syntax**:
```bash
supabase migration fetch [flags]
```

**Flags**:
- `--local`: Fetch from local database (default)
- `--linked`: Fetch from linked project
- `--db-url <url>`: Fetch from specific database

**Example**:
```bash
supabase migration fetch --local
```

**Use Cases**:
- Recovering lost migration files
- Auditing applied migrations
- Syncing migration files with database state

---

## Database Schema Commands

### `supabase db diff`

Generates schema differences between database states.

**Purpose**: Create migration files from schema changes automatically

**Syntax**:
```bash
supabase db diff [flags] [path...]
```

**Flags**:
- `--local`: Diff local database against migrations (default)
- `--linked`: Diff linked project against local
- `--from <source>`: Source state (local, linked, migrations, or URL)
- `--to <target>`: Target state (local, linked, migrations, or URL)
- `--schema <schemas>`: Comma-separated list of schemas to include
- `--file <path>`: Save diff as new migration file
- `--output <path>`: Write diff output to file
- `--use-migra`: Use migra diff engine
- `--use-pgadmin`: Use pgAdmin diff engine
- `--use-pg-schema`: Use pg-schema-diff engine
- `--use-pg-delta`: Use pg-delta engine

**Examples**:

Generate diff for review:
```bash
supabase db diff --local --schema public
```

Create migration file from diff:
```bash
supabase db diff --local --schema public --file supabase/migrations/auto_generated_change.sql
```

Diff specific schemas:
```bash
supabase db diff --local --schema public,auth --output /tmp/schema_changes.sql
```

**Output Example**:
```sql
alter table "public"."users" add column "preferences" jsonb;
create index "idx_users_preferences" on "public"."users" using gin ("preferences");
```

**How It Works**:
1. Creates shadow database from migrations
2. Applies current migrations to shadow DB
3. Compares shadow DB with actual database
4. Generates SQL for differences

**Best Practices**:
- Review generated diffs before applying
- Use descriptive migration names instead of auto-generated
- Test diffs in development first
- Commit both migration files and any manual changes

**Common Pitfalls**:
- Generated diffs may not be optimal
- Missing data migrations
- Not handling existing data correctly
- Overwriting manual migration improvements

**⚠️ Warning**: The diff tool is not foolproof. Manual review and modification is often required.

---

### `supabase db push`

Pushes new migrations to remote database.

**Purpose**: Deploy local migrations to production/staging

**Syntax**:
```bash
supabase db push [flags]
```

**Flags**:
- `--linked`: Push to linked project (default)
- `--local`: Push to local database
- `--db-url <url>`: Push to specific database
- `--password <pwd>`: Password for remote database
- `--dry-run`: Print migrations without applying
- `--include-all`: Include all migrations not in remote history
- `--include-roles`: Include custom roles from `supabase/roles.sql`
- `--include-seed`: Include seed data from config

**Examples**:

Test push without applying:
```bash
supabase db push --linked --dry-run
```

Push to linked project:
```bash
supabase db push --linked
```

Push with seed data:
```bash
supabase db push --linked --include-seed
```

**Best Practices**:
- Always use `--dry-run` first
- Test in staging before production
- Review migration order
- Have rollback plan ready
- Use during low-traffic periods

**Common Pitfalls**:
- Pushing untested migrations
- Not considering data dependencies
- Breaking existing applications
- Missing database permissions

---

### `supabase db pull`

Pulls schema from remote database.

**Purpose**: Sync local schema with remote database state

**Syntax**:
```bash
supabase db pull [flags] [migration_name]
```

**Flags**:
- `--linked`: Pull from linked project (default)
- `--local`: Pull from local database
- `--db-url <url>`: Pull from specific database
- `--password <pwd>`: Password for remote database
- `--schema <schemas>`: Comma-separated list of schemas
- `--use-pg-delta`: Use pg-delta for declarative schema
- `--diff-engine <engine>`: Diff engine (migra, pg-delta)

**Examples**:

Pull and create migration:
```bash
supabase db pull --linked sync_production_schema
```

Pull specific schemas:
```bash
supabase db pull --linked --schema public,auth
```

**Best Practices**:
- Use when remote changes were made manually
- Review generated migrations carefully
- Test pulled migrations locally
- Document manual schema changes

**Common Pitfalls**:
- Overwriting local work
- Not understanding manual changes
- Breaking local development
- Migration conflicts

---

### `supabase db reset`

Resets database to current migration state.

**Purpose**: Clean slate development environment

**Syntax**:
```bash
supabase db reset [flags]
```

**Flags**:
- `--local`: Reset local database (default)
- `--linked`: Reset linked project
- `--db-url <url>`: Reset specific database
- `--password <pwd>`: Password for remote database
- `--debug`: Enable debug output

**Example**:
```bash
supabase db reset --local
```

**Output**:
```
Resetting local database...
Recreating database...
Initialising schema...
Seeding globals from roles.sql...
Applying migration 20260621145819_initial_schema.sql...
Restarting containers...
Finished supabase db reset on branch main.
```

**What It Does**:
1. Drops and recreates database
2. Applies all migrations in order
3. Runs seed files if configured
4. Restarts containers

**Best Practices**:
- Use frequently in local development
- Great for testing migration scripts
- Ensures clean state for testing
- Use before major schema changes

**⚠️ Warning**: This will delete all data in the target database.

---

### `supabase db dump`

Dumps database schema or data.

**Purpose**: Backup database or extract specific components

**Syntax**:
```bash
supabase db dump [flags]
```

**Flags**:
- `--local`: Dump local database (default)
- `--linked`: Dump linked project
- `--db-url <url>`: Dump specific database
- `--password <pwd>`: Password for remote database
- `--schema <schemas>`: Comma-separated list of schemas
- `--data-only`: Dump only data, not schema
- `--use-copy`: Use COPY instead of INSERT
- `--exclude <tables>`: Exclude specific tables
- `--role-only`: Dump only cluster roles
- `--file <path>`: Save dump to file
- `--dry-run`: Print dump without executing

**Examples**:

Dump schema only:
```bash
supabase db dump --local --schema public --file backup_schema.sql
```

Dump data only:
```bash
supabase db dump --local --data-only --file backup_data.sql
```

Dump specific tables:
```bash
supabase db dump --local --exclude "temp_*" --file clean_dump.sql
```

**Best Practices**:
- Regular backups before migrations
- Use `--data-only` for data migrations
- Test restore procedures
- Keep backups in version control

---

### `supabase db lint`

Checks database for schema errors.

**Purpose**: Validate schema integrity and best practices

**Syntax**:
```bash
supabase db lint [flags]
```

**Flags**:
- `--local`: Lint local database (default)
- `--linked`: Lint linked project
- `--db-url <url>`: Lint specific database
- `--schema <schemas>`: Comma-separated list of schemas
- `--level <warning|error>`: Error level to emit
- `--fail-on <none|warning|error>`: Exit code on errors

**Example**:
```bash
supabase db lint --local --schema public --fail-on error
```

**Best Practices**:
- Run before committing migrations
- Include in CI/CD pipelines
- Fix warnings before they become errors
- Use as code quality gate

---

### `supabase db query`

Execute SQL queries directly.

**Purpose**: Quick database operations and testing

**Syntax**:
```bash
supabase db query [flags] <sql>
```

**Flags**:
- `--local`: Query local database (default)
- `--linked`: Query linked project
- `--db-url <url>`: Query specific database
- `--password <pwd>`: Password for remote database

**Example**:
```bash
supabase db query --local "SELECT COUNT(*) FROM users;"
```

**Best Practices**:
- Use for quick testing and verification
- Not recommended for complex operations
- Prefer migration files for schema changes

---

## Advanced Migration Operations

### Working with Multiple Environments

**Development Workflow**:
```bash
# 1. Create migration
supabase migration new add_new_feature

# 2. Edit migration file
vim supabase/migrations/20260621150000_add_new_feature.sql

# 3. Apply locally
supabase migration up --local

# 4. Test changes
supabase db query --local "SELECT * FROM new_feature LIMIT 5;"

# 5. Reset if needed
supabase db reset --local
```

**Staging Workflow**:
```bash
# 1. Test push to staging
supabase db push --linked --dry-run

# 2. Apply to staging
supabase db push --linked

# 3. Verify staging
supabase migration list --linked
```

**Production Workflow**:
```bash
# 1. Final verification
supabase db lint --local --fail-on error

# 2. Backup production
supabase db dump --linked --file production_backup.sql

# 3. Deploy to production
supabase db push --linked

# 4. Verify deployment
supabase migration list --linked
```

---

### Data Migrations

**Pattern for Data Migrations**:
```sql
-- supabase/migrations/20260621150000_migrate_user_data.sql

-- Step 1: Add new column
ALTER TABLE users ADD COLUMN new_status TEXT;

-- Step 2: Migrate existing data
UPDATE users 
SET new_status = 
  CASE 
    WHEN old_status = 'active' THEN 'verified'
    WHEN old_status = 'pending' THEN 'unverified'
    ELSE 'unknown'
  END;

-- Step 3: Add constraint after data migration
ALTER TABLE users 
ADD CONSTRAINT check_new_status 
CHECK (new_status IN ('verified', 'unverified', 'unknown'));

-- Step 4: Drop old column (in separate migration)
-- ALTER TABLE users DROP COLUMN old_status;
```

**Best Practices**:
- Separate schema and data migrations
- Test data migrations on copies
- Use transactions for data consistency
- Plan for rollback scenarios

---

### Handling Foreign Keys

**Safe Foreign Key Migration Pattern**:
```sql
-- Step 1: Add nullable foreign key
ALTER TABLE orders 
ADD COLUMN user_id BIGINT REFERENCES users(id);

-- Step 2: Migrate data
UPDATE orders 
SET user_id = (SELECT id FROM users WHERE email = orders.user_email);

-- Step 3: Make foreign key NOT NULL
ALTER TABLE orders 
ALTER COLUMN user_id SET NOT NULL;

-- Step 4: Drop old column
ALTER TABLE orders DROP COLUMN user_email;
```

---

### Index Management

**Adding Indexes**:
```sql
-- Create index concurrently to avoid locking
CREATE INDEX CONCURRENTLY idx_users_email 
ON users (email);

-- Add comment for documentation
COMMENT ON INDEX idx_users_email IS 'Index for user email lookups';
```

**Dropping Indexes**:
```sql
-- Drop index concurrently
DROP INDEX CONCURRENTLY IF EXISTS idx_users_email;
```

---

## Best Practices

### Migration File Organization

**Naming Convention**:
```
supabase/migrations/
├── 20260621145819_initial_schema.sql
├── 20260621150000_add_users_table.sql
├── 20260621151000_add_user_preferences.sql
└── 20260621152000_add_indexes.sql
```

**File Structure**:
```sql
-- Migration header
-- Description: Add user preferences table
-- Author: Your Name
-- Date: 2026-06-21

-- Schema changes
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_preferences_user_id 
ON user_preferences (user_id);

-- Comments
COMMENT ON TABLE user_preferences IS 'User preference settings';
COMMENT ON COLUMN user_preferences.preferences IS 'JSONB preference data';

-- RLS Policies
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own preferences"
ON user_preferences FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own preferences"
ON user_preferences FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own preferences"
ON user_preferences FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
```

---

### Testing Migrations

**Local Testing Checklist**:
1. ✅ Create migration file
2. ✅ Apply to local database
3. ✅ Verify schema changes
4. ✅ Test with application
5. ✅ Test rollback procedure
6. ✅ Reset and reapply
7. ✅ Check for data issues

**Automated Testing**:
```bash
#!/bin/bash
# test_migration.sh

# Reset database
supabase db reset --local

# Apply migration
supabase migration up --local

# Run tests
pytest tests/test_migration.py

# Check schema
supabase db lint --local --fail-on error

echo "Migration tests passed!"
```

---

### Version Control

**Git Workflow**:
```bash
# 1. Create feature branch
git checkout -b feature/add-user-preferences

# 2. Create and edit migration
supabase migration new add_user_preferences
vim supabase/migrations/20260621150000_add_user_preferences.sql

# 3. Test locally
supabase db reset --local

# 4. Commit migration
git add supabase/migrations/20260621150000_add_user_preferences.sql
git commit -m "Add user preferences table

- Add user_preferences table with RLS
- Add indexes for performance
- Include migration documentation"

# 5. Push and create PR
git push origin feature/add-user-preferences
```

---

### Documentation

**Migration Documentation Template**:
```markdown
## Migration: 20260621150000_add_user_preferences.sql

### Description
Adds user preferences table to store user-specific settings and preferences.

### Changes
- New table: `user_preferences`
- New indexes: `idx_user_preferences_user_id`
- RLS policies for user data isolation

### Impact
- No breaking changes
- Adds new functionality
- Requires application update to use preferences

### Rollback
```sql
DROP TABLE IF EXISTS user_preferences CASCADE;
```

### Testing
- Tested locally with sample data
- Verified RLS policies
- Checked index performance

### Deployment
- Deployed to staging: 2026-06-21
- Deployed to production: 2026-06-22
```

---

## Common Scenarios

### Scenario 1: Adding a New Table

**Steps**:
1. Create migration file
2. Define table schema
3. Add indexes and constraints
4. Configure RLS policies
5. Test locally
6. Deploy to staging
7. Deploy to production

**Example Migration**:
```sql
-- Create audit log table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id UUID,
    old_values JSONB,
    new_values JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs (created_at DESC);
CREATE INDEX idx_audit_logs_table_name ON audit_logs (table_name);

-- Enable RLS
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Service role can manage audit logs"
ON audit_logs FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

---

### Scenario 2: Modifying Existing Table

**Steps**:
1. Create migration file
2. Add columns (nullable first)
3. Migrate existing data
4. Add constraints
5. Make columns NOT NULL
6. Test thoroughly

**Example Migration**:
```sql
-- Add status column to orders table
ALTER TABLE orders ADD COLUMN status TEXT;

-- Migrate existing data
UPDATE orders 
SET status = 'completed'
WHERE completed_at IS NOT NULL;

UPDATE orders 
SET status = 'pending'
WHERE completed_at IS NULL AND status IS NULL;

-- Add check constraint
ALTER TABLE orders 
ADD CONSTRAINT check_order_status 
CHECK (status IN ('pending', 'processing', 'completed', 'cancelled'));

-- Make column NOT NULL
ALTER TABLE orders 
ALTER COLUMN status SET NOT NULL;

-- Add default value
ALTER TABLE orders 
ALTER COLUMN status SET DEFAULT 'pending';

-- Add index
CREATE INDEX idx_orders_status ON orders (status);
```

---

### Scenario 3: Renaming Columns

**Safe Renaming Pattern**:
```sql
-- Step 1: Add new column
ALTER TABLE users ADD COLUMN new_email TEXT;

-- Step 2: Migrate data
UPDATE users SET new_email = email;

-- Step 3: Add constraints to new column
ALTER TABLE users 
ALTER COLUMN new_email SET NOT NULL,
ADD CONSTRAINT unique_new_email UNIQUE (new_email);

-- Step 4: Update dependent objects (views, functions)
CREATE OR REPLACE VIEW user_summary AS
SELECT id, new_email as email, created_at FROM users;

-- Step 5: Drop old column (in separate migration after verification)
-- ALTER TABLE users DROP COLUMN email;
```

---

### Scenario 4: Handling Large Data Migrations

**Batch Processing Pattern**:
```sql
-- Process in batches to avoid locking
DO $$
DECLARE
  batch_size INT := 1000;
  offset_val INT := 0;
  total_count INT;
BEGIN
  SELECT COUNT(*) INTO total_count FROM large_table WHERE status IS NULL;
  
  WHILE offset_val < total_count LOOP
    UPDATE large_table
    SET status = 'processed'
    WHERE id IN (
      SELECT id FROM large_table
      WHERE status IS NULL
      ORDER BY id
      LIMIT batch_size
      OFFSET offset_val
    );
    
    offset_val := offset_val + batch_size;
    RAISE NOTICE 'Processed % records', offset_val;
    
    -- Commit periodically
    COMMIT;
  END LOOP;
END $$;
```

---

### Scenario 5: Recovering from Failed Migration

**Recovery Steps**:
1. Identify failed migration
2. Assess database state
3. Create repair migration
4. Test repair locally
5. Apply repair to affected database
6. Update migration history

**Example Repair**:
```bash
# 1. Check migration status
supabase migration list --linked

# 2. Identify issue
supabase db query --linked "SELECT * FROM supabase_migrations ORDER BY version;"

# 3. Create repair migration
supabase migration new repair_failed_migration

# 4. Add repair SQL
vim supabase/migrations/20260621160000_repair_failed_migration.sql

# 5. Test locally
supabase migration up --local

# 6. Apply to production
supabase migration up --linked

# 7. Update history if needed
supabase migration repair 20260621150000 --status applied --linked
```

---

## Troubleshooting

### Common Issues and Solutions

**Issue 1: Migration Out of Order**

**Symptoms**:
```
Error: Migration 20260621150000 depends on 20260621145819 which is not applied
```

**Solutions**:
```bash
# Check migration order
supabase migration list --local

# Apply missing migrations
supabase migration up --local

# Or repair history if manually applied
supabase migration repair 20260621145819 --status applied --local
```

---

**Issue 2: Shadow Database Errors**

**Symptoms**:
```
Error: Failed to create shadow database
```

**Solutions**:
```bash
# Check shadow database port
netstat -an | grep 54320

# Reset local stack
supabase stop
supabase start

# Clear shadow database
docker ps -a | grep shadow
docker rm -f <shadow_container_id>
```

---

**Issue 3: Foreign Key Constraint Failures**

**Symptoms**:
```
Error: insert or update on table violates foreign key constraint
```

**Solutions**:
```sql
-- Check constraint details
SELECT
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';
```

---

**Issue 4: Migration Lock Timeout**

**Symptoms**:
```
Error: could not obtain lock on relation
```

**Solutions**:
```sql
-- Check for locks
SELECT 
    pid,
    usename,
    pg_blocking_pids(pid) as blocked_by,
    query as blocked_query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;

-- Kill blocking sessions if necessary
SELECT pg_terminate_backend(pid);
```

---

**Issue 5: Disk Space Issues**

**Symptoms**:
```
Error: could not extend file: No space left on device
```

**Solutions**:
```bash
# Check disk space
df -h

# Clean up old migrations
find supabase/migrations -name "*.sql" -mtime +30 -delete

# Vacuum database
supabase db query --local "VACUUM FULL;"
```

---

### Debug Mode

**Enable Debug Logging**:
```bash
supabase db diff --local --debug
supabase migration up --local --debug
```

**Check Logs**:
```bash
# Docker logs
docker logs supabase_db_diocesan-vitality

# Supabase logs
supabase logs
```

---

## Integration with Project Workflow

### Development Workflow Integration

**1. Local Development**:
```bash
# Start local stack
supabase start

# Make schema changes
supabase migration new feature_change

# Edit migration file
vim supabase/migrations/20260621150000_feature_change.sql

# Apply and test
supabase migration up --local
```

**2. Testing**:
```bash
# Reset for clean testing
supabase db reset --local

# Run tests
pytest tests/

# Lint schema
supabase db lint --local --fail-on error
```

**3. Code Review**:
```bash
# Generate diff for review
supabase db diff --local --schema public > /tmp/schema_changes.sql

# Review changes
cat /tmp/schema_changes.sql
```

**4. Deployment**:
```bash
# Test deployment
supabase db push --linked --dry-run

# Deploy to staging
supabase db push --linked

# Verify deployment
supabase migration list --linked
```

---

### CI/CD Integration

**GitHub Actions Example**:
```yaml
name: Database Migration

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test-migrations:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Supabase CLI
        run: |
          wget https://github.com/supabase/supabase/releases/latest/download/supabase_linux_amd64.tar.gz
          tar -xzf supabase_linux_amd64.tar.gz
          sudo mv supabase /usr/local/bin/
      
      - name: Start Local Stack
        run: supabase start
      
      - name: Apply Migrations
        run: supabase migration up --local
      
      - name: Lint Schema
        run: supabase db lint --local --fail-on error
      
      - name: Run Tests
        run: pytest tests/
      
      - name: Stop Local Stack
        run: supabase stop
```

---

### Monitoring and Alerts

**Migration Monitoring**:
```bash
# Check migration status
supabase migration list --linked

# Monitor database performance
supabase db query --linked "
  SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
  FROM pg_stat_user_tables
  ORDER BY n_tup_ins DESC;
"
```

---

## Quick Reference

### Essential Commands

```bash
# Create migration
supabase migration new <name>

# List migrations
supabase migration list --local

# Apply migrations
supabase migration up --local

# Generate diff
supabase db diff --local --schema public

# Push to remote
supabase db push --linked

# Reset database
supabase db reset --local

# Backup database
supabase db dump --local --file backup.sql
```

### Common Flags

```bash
--local      # Target local database
--linked     # Target linked project
--dry-run    # Preview without applying
--schema     # Specify schemas
--debug      # Enable debug output
--yes        # Skip confirmations
```

### File Locations

```
supabase/
├── config.toml           # Configuration
├── migrations/           # Migration files
│   └── 20260621150000_name.sql
├── seed.sql             # Seed data
└── roles.sql            # Custom roles
```

---

## Additional Resources

- [Supabase CLI Documentation](https://supabase.com/docs/guides/cli)
- [PostgreSQL Migration Best Practices](https://www.postgresql.org/docs/current/ddl-alter.html)
- [Database Schema Design](https://supabase.com/docs/guides/database)
- [Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)

---

## Conclusion

This guide provides a comprehensive reference for Supabase CLI migration commands and best practices. Key takeaways:

1. **Always test locally** before deploying to production
2. **Use descriptive migration names** for better traceability
3. **Review generated diffs** before applying
4. **Backup before major changes** to enable rollback
5. **Document migrations** for team knowledge sharing
6. **Use CI/CD integration** for automated testing
7. **Monitor migration performance** in production

Following these practices will ensure smooth database schema evolution and minimize deployment risks.

---

*Last Updated: 2026-06-21*
*Version: 1.0*
*Project: Diocesan Vitality*