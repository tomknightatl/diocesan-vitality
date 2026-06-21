# Supabase Migration Commands Quick Reference

A quick cheat sheet for common Supabase CLI migration operations.

## Core Commands

### Migration Management
```bash
# Create new migration
supabase migration new <migration_name>

# List migration status
supabase migration list --local
supabase migration list --linked

# Apply pending migrations
supabase migration up --local
supabase migration up --linked

# Revert migrations (destructive!)
supabase migration down --local --last 1 --yes

# Repair migration history
supabase migration repair <version> --status applied --local

# Squash migrations
supabase migration squash --local --version <version>

# Fetch migration files
supabase migration fetch --local
```

### Schema Operations
```bash
# Generate schema diff
supabase db diff --local --schema public
supabase db diff --local --schema public --file <migration_file>

# Push migrations to remote
supabase db push --linked --dry-run
supabase db push --linked

# Pull schema from remote
supabase db pull --linked <migration_name>

# Reset database
supabase db reset --local

# Dump database
supabase db dump --local --schema public --file backup.sql
supabase db dump --local --data-only --file data_backup.sql

# Lint schema
supabase db lint --local --fail-on error

# Execute query
supabase db query --local "SELECT COUNT(*) FROM users;"
```

## Common Flags

```bash
--local      # Target local database
--linked     # Target linked Supabase project
--db-url     # Target specific database URL
--dry-run    # Preview without applying
--schema     # Specify schemas (comma-separated)
--debug      # Enable debug output
--yes        # Skip confirmation prompts
--password   # Database password
```

## Workflow Examples

### Development Workflow
```bash
# 1. Create migration
supabase migration new add_feature_table

# 2. Edit migration file
vim supabase/migrations/20260621150000_add_feature_table.sql

# 3. Apply locally
supabase migration up --local

# 4. Test changes
supabase db query --local "SELECT * FROM feature_table LIMIT 5;"

# 5. Reset if needed
supabase db reset --local
```

### Deployment Workflow
```bash
# 1. Verify migrations
supabase migration list --local
supabase db lint --local --fail-on error

# 2. Test deployment
supabase db push --linked --dry-run

# 3. Deploy to staging
supabase db push --linked

# 4. Verify deployment
supabase migration list --linked
```

### Schema Change Workflow
```bash
# 1. Make direct changes to local database
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres

# 2. Generate migration from changes
supabase db diff --local --schema public

# 3. Review and edit generated migration
vim supabase/migrations/<generated_file>.sql

# 4. Test migration
supabase db reset --local

# 5. Deploy
supabase db push --linked
```

## Migration File Template

```sql
-- Migration: <timestamp>_<name>.sql
-- Description: Brief description of changes
-- Author: Your Name
-- Date: YYYY-MM-DD

-- Schema changes
CREATE TABLE example_table (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_example_table_name ON example_table (name);

-- Comments
COMMENT ON TABLE example_table IS 'Example table';

-- RLS Policies
ALTER TABLE example_table ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for authenticated users"
ON example_table FOR SELECT
TO authenticated
USING (true);
```

## Troubleshooting

### Check Migration Status
```bash
supabase migration list --local
supabase migration list --linked
```

### Reset Local Database
```bash
supabase db reset --local
```

### Check Database Connection
```bash
supabase status
```

### Enable Debug Mode
```bash
supabase db diff --local --debug
supabase migration up --local --debug
```

### View Logs
```bash
docker logs supabase_db_diocesan-vitality
supabase logs
```

## File Locations

```
supabase/
├── config.toml              # Configuration file
├── migrations/              # Migration files
│   └── 20260621150000_name.sql
├── seed.sql                 # Seed data
└── roles.sql                # Custom roles

docs/
└── supabase-migration-reference.md  # Full documentation
```

## Common Patterns

### Add Column
```sql
ALTER TABLE table_name ADD COLUMN new_column TEXT;
```

### Add Index
```sql
CREATE INDEX idx_table_column ON table_name (column);
```

### Add Foreign Key
```sql
ALTER TABLE child_table 
ADD COLUMN parent_id UUID 
REFERENCES parent_table(id);
```

### Enable RLS
```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;
```

### Create Policy
```sql
CREATE POLICY "policy_name"
ON table_name FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);
```

## Best Practices

1. **Always test locally** before deploying
2. **Use descriptive names** for migrations
3. **Review generated diffs** before applying
4. **Backup before major changes**
5. **One logical change per migration**
6. **Test rollback procedures**
7. **Document complex migrations**
8. **Use transactions** for data migrations

## Emergency Commands

### Quick Backup
```bash
supabase db dump --linked --file emergency_backup.sql
```

### Quick Rollback
```bash
supabase migration down --linked --last 1 --yes
```

### Force Migration Repair
```bash
supabase migration repair <version> --status applied --linked
```

### Stop All Services
```bash
supabase stop
```

### Start All Services
```bash
supabase start
```

## Useful Queries

### Check Table Sizes
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Check Migration History
```sql
SELECT * FROM supabase_migrations.schema_migrations 
ORDER BY version;
```

### Check Active Locks
```sql
SELECT 
    pid,
    usename,
    pg_blocking_pids(pid) as blocked_by,
    query as blocked_query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;
```

---

*For detailed documentation, see [supabase-migration-reference.md](./supabase-migration-reference.md)*