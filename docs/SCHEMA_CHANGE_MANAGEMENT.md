# Schema Change Management Script

## Overview

The `apply_schema_change.py` script provides a comprehensive workflow for managing database schema changes using Supabase CLI. It supports both automatic and manual migration workflows with proper error handling, validation, and safety measures.

## Features

- **Generate migration diffs** from local schema changes using `supabase db diff`
- **Apply migrations** to local database with validation
- **Rollback capability** to undo migrations
- **Schema validation** to detect errors and issues
- **Automatic workflow** that combines generate, review, apply, and validate steps
- **Manual workflow** for step-by-step control
- **Database backup** before applying changes
- **Dry-run mode** for testing without making changes
- **Comprehensive logging** for audit trails
- **Safety confirmations** before destructive operations

## Installation

### Prerequisites

1. **Supabase CLI** - Install from https://supabase.com/docs/guides/cli
2. **Python 3.8+** - Required for script execution
3. **Local Supabase stack** - Start with `supabase start`

### Setup

The script is located at `scripts/apply_schema_change.py` and is executable:

```bash
chmod +x scripts/apply_schema_change.py
```

## Usage

### Basic Commands

#### 1. Automatic Workflow (Recommended)

The automatic workflow handles the entire process: generate, review, apply, and validate.

```bash
python scripts/apply_schema_change.py --auto --name "add_user_preferences"
```

This will:
1. Generate a migration diff from local schema changes
2. Display the migration content for review
3. Ask for confirmation before applying
4. Apply the migration to the local database
5. Validate the schema for errors

#### 2. Generate Migration Only

Generate a migration diff without applying it:

```bash
python scripts/apply_schema_change.py --generate --name "add_user_preferences"
```

#### 3. Apply Existing Migration

Apply a specific migration file:

```bash
python scripts/apply_schema_change.py --apply --file "20260621150000_add_user_preferences.sql"
```

Apply all pending migrations:

```bash
python scripts/apply_schema_change.py --apply
```

#### 4. Rollback Migration

Rollback the last migration:

```bash
python scripts/apply_schema_change.py --rollback
```

Rollback multiple migrations:

```bash
python scripts/apply_schema_change.py --rollback --rollback-count 3
```

#### 5. Check Migration Status

View current migration status:

```bash
python scripts/apply_schema_change.py --status
```

#### 6. Validate Schema

Validate database schema for errors:

```bash
python scripts/apply_schema_change.py --validate
```

Validate specific schema:

```bash
python scripts/apply_schema_change.py --validate --schema auth
```

### Advanced Options

#### Dry-Run Mode

Test commands without executing them:

```bash
python scripts/apply_schema_change.py --auto --name "test_migration" --dry-run
```

#### Database Backup

Create a backup before applying changes:

```bash
python scripts/apply_schema_change.py --auto --name "important_change" --backup
```

#### Skip Validation

Skip schema validation after applying (use with caution):

```bash
python scripts/apply_schema_change.py --auto --name "quick_change" --skip-validation
```

#### Use Migra Diff Engine

Use the migra diff engine instead of the default:

```bash
python scripts/apply_schema_change.py --generate --name "change" --use-migra
```

#### Skip Confirmations

Skip confirmation prompts (use with caution in automated scripts):

```bash
python scripts/apply_schema_change.py --apply --yes
```

## Workflow Examples

### Example 1: Adding a New Table

```bash
# 1. Make schema changes using Supabase Studio or SQL
# 2. Generate migration
python scripts/apply_schema_change.py --generate --name "add_user_preferences"

# 3. Review the generated migration file
# 4. Apply the migration
python scripts/apply_schema_change.py --apply

# 5. Validate the schema
python scripts/apply_schema_change.py --validate
```

### Example 2: Automatic Workflow with Backup

```bash
# Complete workflow with backup and safety measures
python scripts/apply_schema_change.py \
  --auto \
  --name "add_audit_log_table" \
  --backup \
  --schema public
```

### Example 3: Testing Before Deployment

```bash
# Test the workflow without making changes
python scripts/apply_schema_change.py \
  --auto \
  --name "test_deployment" \
  --dry-run
```

### Example 4: Rollback After Failed Migration

```bash
# If a migration causes issues, rollback immediately
python scripts/apply_schema_change.py --rollback --yes
```

## Command Reference

### Workflow Options

| Option | Description |
|--------|-------------|
| `--auto` | Execute automatic workflow (generate, review, apply, validate) |
| `--generate` | Generate migration diff only |
| `--apply` | Apply existing migration |
| `--rollback` | Rollback last migration |
| `--status` | Show migration status |
| `--validate` | Validate database schema |

### Migration Options

| Option | Description |
|--------|-------------|
| `--name NAME` | Migration name (for --generate or --auto) |
| `--file FILE` | Migration file path (for --apply) |
| `--schema SCHEMA` | Schema to operate on (default: public) |
| `--rollback-count N` | Number of migrations to rollback (default: 1) |

### Advanced Options

| Option | Description |
|--------|-------------|
| `--use-migra` | Use migra diff engine for generating migrations |
| `--skip-validation` | Skip schema validation after applying migration |
| `--backup` | Create database backup before applying changes |
| `--dry-run` | Simulate commands without executing them |
| `--yes` | Skip confirmation prompts (use with caution) |

## Error Handling

The script includes comprehensive error handling for common scenarios:

### Environment Validation

- Checks for Supabase CLI installation
- Verifies local Supabase stack is running
- Validates required directories exist

### Migration Errors

- Handles failed migration generation
- Detects empty migration files
- Validates migration syntax
- Provides rollback capability

### Database Errors

- Handles connection issues
- Detects constraint violations
- Validates schema integrity
- Provides detailed error messages

## Logging

The script creates detailed logs for audit trails:

- **Log Location**: `logs/schema_change_YYYYMMDD_HHMMSS.log`
- **Log Levels**: INFO, WARNING, ERROR, DEBUG
- **Log Content**: Command execution, results, errors, and timestamps

Example log entry:

```
2026-06-21 10:07:20,830 - __main__ - INFO - Validating environment...
2026-06-21 10:07:20,830 - __main__ - INFO - Executing command: supabase --version
2026-06-21 10:07:20,830 - __main__ - INFO - Supabase CLI version: 1.50.0
2026-06-21 10:07:20,830 - __main__ - INFO - Local Supabase stack is running
```

## Safety Features

### Confirmation Prompts

The script requires confirmation for destructive operations:

- **Migration application**: "Do you want to apply this migration? (yes/no)"
- **Rollback operations**: "Are you sure you want to rollback? This is a destructive operation! (yes/no)"
- **Migration review**: "Do you approve this migration? (yes/no/edit)"

### Dry-Run Mode

Test workflows without making changes:

```bash
python scripts/apply_schema_change.py --auto --name "test" --dry-run
```

### Database Backup

Automatic backup before changes:

```bash
python scripts/apply_schema_change.py --auto --name "important" --backup
```

### Schema Validation

Automatic validation after applying migrations:

```bash
python scripts/apply_schema_change.py --auto --name "change" --validate
```

## Troubleshooting

### Issue: "Supabase CLI not found"

**Solution**: Install Supabase CLI from https://supabase.com/docs/guides/cli

### Issue: "Local Supabase stack is not running"

**Solution**: Start the local stack with `supabase start`

### Issue: "Migration file was not created"

**Solution**: Check for schema changes. If no changes exist, no migration will be generated.

### Issue: "Schema validation failed"

**Solution**: Review the validation errors and fix schema issues. Consider rolling back the migration.

### Issue: "Cannot rollback N migration(s)"

**Solution**: You're trying to rollback more migrations than have been applied. Check migration status first.

## Best Practices

### 1. Use Automatic Workflow

For most cases, use the automatic workflow for complete process management:

```bash
python scripts/apply_schema_change.py --auto --name "descriptive_name"
```

### 2. Test with Dry-Run First

Always test workflows with dry-run mode:

```bash
python scripts/apply_schema_change.py --auto --name "test" --dry-run
```

### 3. Create Backups for Important Changes

For critical schema changes, always create backups:

```bash
python scripts/apply_schema_change.py --auto --name "critical" --backup
```

### 4. Use Descriptive Migration Names

Use clear, descriptive names for migrations:

- ✅ Good: `add_user_preferences_table`
- ✅ Good: `add_index_on_users_email`
- ❌ Bad: `change1`
- ❌ Bad: `fix`

### 5. Review Generated Migrations

Always review auto-generated migrations before applying:

```bash
python scripts/apply_schema_change.py --generate --name "change"
# Review the generated file
python scripts/apply_schema_change.py --apply
```

### 6. Validate After Changes

Always validate the schema after applying migrations:

```bash
python scripts/apply_schema_change.py --validate
```

### 7. Keep Migration History

Track migration history for rollback capability:

```bash
python scripts/apply_schema_change.py --status
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Database Migration

on:
  push:
    branches: [main]

jobs:
  migrate:
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
        run: python scripts/apply_schema_change.py --apply --yes

      - name: Validate Schema
        run: python scripts/apply_schema_change.py --validate

      - name: Stop Local Stack
        run: supabase stop
```

## Testing

The script includes a comprehensive test suite:

```bash
python scripts/test_apply_schema_change.py
```

This tests all major workflows:
- Help command
- Status checking
- Schema validation
- Migration generation
- Migration application
- Rollback operations
- Automatic workflow
- Advanced options

## Migration File Structure

Generated migration files follow this structure:

```
supabase/migrations/
├── 20260621150000_add_user_preferences.sql
├── 20260621151000_add_indexes.sql
└── 20260621152000_update_constraints.sql
```

### Migration File Format

```sql
-- Migration: 20260621150000_add_user_preferences.sql
-- Description: Add user preferences table
-- Generated: 2026-06-21 15:00:00

-- Schema changes
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

-- Comments
COMMENT ON TABLE user_preferences IS 'User preference settings';
```

## Support and Documentation

- **Supabase CLI Documentation**: https://supabase.com/docs/guides/cli
- **Migration Reference**: `docs/supabase-migration-reference.md`
- **Project Documentation**: See project README and docs directory

## Version History

- **v1.0.0** (2026-06-21): Initial release
  - Automatic and manual workflows
  - Migration generation and application
  - Rollback capability
  - Schema validation
  - Comprehensive error handling
  - Dry-run mode
  - Database backup support

## Contributing

When contributing to this script:

1. Follow existing code style and patterns
2. Add comprehensive error handling
3. Include detailed logging
4. Update documentation for new features
5. Test thoroughly with the test suite
6. Ensure backward compatibility

## License

This script is part of the Diocesan Vitality Project and follows the project's license terms.

---

**Author**: Diocesan Vitality Project
**Version**: 1.0.0
**Last Updated**: 2026-06-21