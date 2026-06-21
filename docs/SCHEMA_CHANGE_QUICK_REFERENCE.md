# Schema Change Management - Quick Reference

## Essential Commands

### Quick Start
```bash
# Automatic workflow (recommended)
python scripts/apply_schema_change.py --auto --name "your_migration_name"

# Check status
python scripts/apply_schema_change.py --status

# Validate schema
python scripts/apply_schema_change.py --validate
```

### Common Workflows

#### Add New Table
```bash
python scripts/apply_schema_change.py --auto --name "add_new_table"
```

#### Modify Existing Table
```bash
python scripts/apply_schema_change.py --auto --name "modify_users_table"
```

#### Rollback Last Change
```bash
python scripts/apply_schema_change.py --rollback
```

#### Test Without Changes
```bash
python scripts/apply_schema_change.py --auto --name "test" --dry-run
```

## Command Options

### Workflows (mutually exclusive)
- `--auto` - Full automatic workflow
- `--generate` - Generate migration only
- `--apply` - Apply existing migration
- `--rollback` - Rollback migration
- `--status` - Show migration status
- `--validate` - Validate schema

### Migration Settings
- `--name NAME` - Migration name
- `--file FILE` - Specific migration file
- `--schema SCHEMA` - Target schema (default: public)
- `--rollback-count N` - Number to rollback (default: 1)

### Safety Options
- `--dry-run` - Simulate without changes
- `--backup` - Create backup before changes
- `--yes` - Skip confirmations (use carefully!)
- `--skip-validation` - Skip validation (use carefully!)

### Advanced Options
- `--use-migra` - Use migra diff engine

## Examples

### Development Workflow
```bash
# 1. Make schema changes in Supabase Studio
# 2. Generate migration
python scripts/apply_schema_change.py --generate --name "add_feature"

# 3. Review the generated file
# 4. Apply migration
python scripts/apply_schema_change.py --apply

# 5. Validate
python scripts/apply_schema_change.py --validate
```

### Safe Production Workflow
```bash
# Test first
python scripts/apply_schema_change.py --auto --name "production_change" --dry-run

# Create backup and apply
python scripts/apply_schema_change.py --auto --name "production_change" --backup
```

### Emergency Rollback
```bash
# Quick rollback without confirmation
python scripts/apply_schema_change.py --rollback --yes
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| CLI not found | Install Supabase CLI |
| Stack not running | Run `supabase start` |
| No migration generated | No schema changes detected |
| Validation failed | Review errors, consider rollback |
| Can't rollback | Not enough migrations applied |

## File Locations

- **Script**: `scripts/apply_schema_change.py`
- **Migrations**: `supabase/migrations/`
- **Logs**: `logs/schema_change_*.log`
- **Backups**: `backup/db_backup_*.sql`

## Testing

```bash
# Run test suite
python scripts/test_apply_schema_change.py

# Test specific workflow
python scripts/apply_schema_change.py --status --dry-run
```

## Help

```bash
python scripts/apply_schema_change.py --help
```

## Key Points

✅ Always use `--dry-run` first for testing
✅ Use descriptive migration names
✅ Review generated migrations before applying
✅ Create backups for important changes
✅ Validate schema after applying
✅ Check logs for detailed information
⚠️ Use `--yes` only in automated scripts
⚠️ Rollback is destructive - use carefully