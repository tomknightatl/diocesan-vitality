# Production Deployment Script - Quick Reference

## Quick Start

### Basic Commands

```bash
# Deploy with full safety checks (RECOMMENDED)
python scripts/deploy_to_production.py --auto --migration-file "migration.sql"

# Validate migration only
python scripts/deploy_to_production.py --validate --migration-file "migration.sql"

# Create backup only
python scripts/deploy_to_production.py --backup-only

# Check deployment status
python scripts/deploy_to_production.py --status

# Rollback last deployment
python scripts/deploy_to_production.py --rollback
```

### Testing Commands

```bash
# Test deployment without making changes
python scripts/deploy_to_production.py --auto --migration-file "migration.sql" --dry-run

# Validate migration syntax
python scripts/deploy_to_production.py --validate --migration-file "migration.sql" --dry-run
```

## Safety Checklist

### Before Deployment
- [ ] Migration tested in development environment
- [ ] Migration file reviewed for dangerous operations
- [ ] Recent backup exists (check with `--status`)
- [ ] Sufficient disk space available (minimum 1GB)
- [ ] Low-traffic period scheduled
- [ ] Rollback plan prepared

### During Deployment
- [ ] Use `--dry-run` first for testing
- [ ] Monitor log files: `tail -f logs/production_deployment_*.log`
- [ ] Verify all pre-deployment checks pass
- [ ] Keep rollback command ready
- [ ] Have database access available

### After Deployment
- [ ] Verify post-deployment checks pass
- [ ] Monitor application for errors
- [ ] Check database performance
- [ ] Document deployment results
- [ ] Update team on deployment status

## Common Workflows

### Standard Deployment
```bash
# 1. Validate migration
python scripts/deploy_to_production.py --validate --migration-file "add_column.sql"

# 2. Check status
python scripts/deploy_to_production.py --status

# 3. Deploy (will require confirmation)
python scripts/deploy_to_production.py --auto --migration-file "add_column.sql"
```

### Emergency Rollback
```bash
# Quick rollback to latest backup
python scripts/deploy_to_production.py --rollback --yes

# Or rollback to specific backup
python scripts/deploy_to_production.py --rollback --backup-file "db_backup_20260621_150000.sql.gz" --yes
```

### Testing Migration
```bash
# Test without making changes
python scripts/deploy_to_production.py --auto --migration-file "test.sql" --dry-run --yes
```

## Error Handling

### Common Errors and Solutions

| Error | Solution |
|-------|----------|
| `Supabase CLI not found` | Install: https://supabase.com/docs/guides/cli |
| `Docker not found` | Install: https://docs.docker.com/get-docker/ |
| `Cannot connect to production database` | Check `.env` credentials |
| `Insufficient disk space` | Free up disk space (min 1GB) |
| `Migration syntax validation failed` | Review SQL syntax in migration file |

### Getting Help

```bash
# Show full help
python scripts/deploy_to_production.py --help

# Check logs for detailed error information
cat logs/production_deployment_*.log
```

## Configuration

### Required Environment Variables (.env)
```bash
SUPABASE_URL_PRD="your_production_url"
SUPABASE_DB_PASSWORD_PRD="your_production_password"
```

### Optional Environment Variables (.env)
```bash
SUPABASE_URL_STG="your_staging_url"
SUPABASE_DB_PASSWORD_STG="your_staging_password"
```

## Safety Features

### Automatic Safety Checks
- ✓ Environment validation (tools, credentials, connectivity)
- ✓ Pre-deployment checklist (6 comprehensive checks)
- ✓ Migration syntax validation
- ✓ Automatic backup creation
- ✓ Staging environment testing (if available)
- ✓ Manual confirmation requirement
- ✓ Post-deployment verification

### Rollback Capability
- ✓ Automatic backup detection
- ✓ Specific backup selection
- ✓ Verified restoration process
- ✓ Clear rollback instructions

### Logging and Monitoring
- ✓ Dual logging (console + file)
- ✓ Timestamped log files
- ✓ Detailed operation tracking
- ✓ Error reporting and troubleshooting

## Advanced Options

### Command-Line Flags
- `--dry-run`: Simulate without making changes
- `--yes`: Skip confirmation prompts (use with caution!)
- `--migration-file`: Specify migration file
- `--backup-file`: Specify backup file for rollback

### Example: Automated Deployment
```bash
# For CI/CD or automated workflows (use with extreme caution)
python scripts/deploy_to_production.py --auto --migration-file "migration.sql" --yes
```

## Monitoring

### Log Files
- **Location**: `logs/production_deployment_YYYYMMDD_HHMMSS.log`
- **Monitor in real-time**: `tail -f logs/production_deployment_*.log`

### Status Information
```bash
# Check current deployment status
python scripts/deploy_to_production.py --status
```

## Best Practices

1. **Always test first**: Use `--dry-run` before actual deployment
2. **Review migrations**: Check for dangerous operations before deploying
3. **Schedule wisely**: Deploy during low-traffic periods
4. **Monitor closely**: Watch logs and application performance
5. **Be prepared**: Keep rollback commands ready
6. **Document everything**: Record deployment results and issues

## Emergency Procedures

### If Deployment Fails
1. Check log files for error details
2. Verify database connectivity
3. Review migration file for issues
4. Consider rollback if necessary
5. Contact database administrator if needed

### If Rollback Fails
1. Verify backup file exists and is valid
2. Check database connectivity
3. Review log files for specific errors
4. Contact database administrator immediately
5. Consider manual database restoration

## Support and Documentation

- **Full Documentation**: `docs/DEPLOYMENT_SCRIPT_IMPLEMENTATION.md`
- **Test Suite**: `scripts/test_deploy_to_production.py`
- **Example Migration**: `supabase/migrations/20260621100000_test_deployment.sql`
- **Log Files**: `logs/production_deployment_*.log`

## Quick Reference Card

```bash
# DEPLOY
python scripts/deploy_to_production.py --auto --migration-file "file.sql"

# VALIDATE
python scripts/deploy_to_production.py --validate --migration-file "file.sql"

# BACKUP
python scripts/deploy_to_production.py --backup-only

# ROLLBACK
python scripts/deploy_to_production.py --rollback

# STATUS
python scripts/deploy_to_production.py --status

# TEST
python scripts/deploy_to_production.py --auto --migration-file "file.sql" --dry-run
```

---

**Remember**: This script operates on production data. Always use `--dry-run` first and ensure you have recent backups before deploying!