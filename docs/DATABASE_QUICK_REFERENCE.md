# Database Quick Reference Guide

**Complete quick reference for database operations, migrations, and management in the Diocesan Vitality project.**

## Table of Contents

- [Essential Commands](#essential-commands)
- [Common Workflows](#common-workflows)
- [Database Reset](#database-reset)
- [Schema Changes](#schema-changes)
- [Migration Testing](#migration-testing)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)
- [File Locations](#file-locations)
- [Environment Variables](#environment-variables)

---

## Essential Commands

### Quick Start Commands

```bash
# Check database status
make db-check

# Reset local database (use with caution!)
python scripts/reset_local_database.py

# Apply schema changes
python scripts/apply_schema_change.py --auto --name "your_migration_name"

# Test migration
python scripts/test_migration.py

# Deploy to production
python scripts/deploy_to_production.py --auto --migration-file "migration.sql"

# Create backup
python scripts/backup_production_database.py
```

### Makefile Commands

```bash
# Database operations
make db-check              # Test database connection
make db-status            # Show migration status
make db-validate          # Validate schema integrity
make db-backup            # Create database backup
make db-rollback          # Rollback last migration

# Development operations
make env-check            # Check environment configuration
make start                # Start development services
make stop                 # Stop development services
make pipeline             # Run pipeline test
```

---

## Common Workflows

### Workflow 1: Adding a New Table

```bash
# 1. Create table using Supabase Studio or SQL
supabase db query --local "
  CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
  );
"

# 2. Generate migration
python scripts/apply_schema_change.py --auto --name "add_user_preferences_table"

# 3. Review and approve when prompted
# 4. Migration is automatically applied and validated
```

### Workflow 2: Modifying Existing Table

```bash
# 1. Add column to existing table
supabase db query --local "ALTER TABLE users ADD COLUMN last_login TIMESTAMPTZ;"

# 2. Generate migration
python scripts/apply_schema_change.py --generate --name "add_users_last_login"

# 3. Review migration content
cat supabase/migrations/20260621100721_add_users_last_login.sql

# 4. Apply migration
python scripts/apply_schema_change.py --apply

# 5. Validate schema
python scripts/apply_schema_change.py --validate
```

### Workflow 3: Production Deployment

```bash
# 1. Validate migration
python scripts/deploy_to_production.py --validate --migration-file "migration.sql"

# 2. Test deployment (dry-run)
python scripts/deploy_to_production.py --auto --migration-file "migration.sql" --dry-run

# 3. Deploy to production
python scripts/deploy_to_production.py --auto --migration-file "migration.sql"

# 4. Type "DEPLOY" when prompted
# 5. Monitor deployment progress
# 6. Verify post-deployment checks pass
```

### Workflow 4: Emergency Rollback

```bash
# Quick rollback without confirmation
python scripts/deploy_to_production.py --rollback --yes

# Or rollback to specific backup
python scripts/deploy_to_production.py --rollback --backup-file "db_backup_20260621_150000.sql.gz"
```

---

## Database Reset

### When to Use Database Reset

Use the database reset workflow when:
- **Schema Changes**: After major database schema updates
- **Data Corruption**: When local data becomes corrupted
- **Testing Scenarios**: When you need fresh production-like data
- **Development Reset**: When switching between development branches
- **Performance Issues**: When database performance degrades
- **Sync Issues**: When local and production databases become out of sync

### Reset Commands

```bash
# Standard reset (with confirmation)
python scripts/reset_local_database.py

# Automated reset (skip confirmation - use with caution!)
python scripts/reset_local_database.py --skip-confirmation
```

### What Reset Does

1. **Stops local Supabase services** - Ensures clean database state
2. **Drops all tables** - Removes all existing data and schema
3. **Restores schema** - Applies clean schema from `sql/initial_schema.sql`
4. **Copies production data** - Transfers all data from production database
5. **Restarts Supabase services** - Brings local instance back online
6. **Verifies database integrity** - Confirms successful reset

### ⚠️ Safety Warnings

**CRITICAL: Database reset is a destructive operation that cannot be undone!**

- **All local data will be permanently lost**
- **Any uncommitted changes will be wiped**
- **Local test data will be replaced with production data**
- **The operation requires explicit confirmation by default**
- **Always backup important local data before proceeding**

---

## Schema Changes

### Schema Change Management

The `apply_schema_change.py` script provides comprehensive workflow for managing database schema changes.

### Automatic Workflow (Recommended)

```bash
python scripts/apply_schema_change.py --auto --name "descriptive_name"
```

This will:
1. Generate a migration diff from local schema changes
2. Display the migration content for review
3. Ask for confirmation before applying
4. Apply the migration to the local database
5. Validate the schema for errors

### Manual Workflow

```bash
# Step 1: Generate migration only
python scripts/apply_schema_change.py --generate --name "add_feature"

# Step 2: Review the generated file
cat supabase/migrations/20260621150000_add_feature.sql

# Step 3: Apply migration
python scripts/apply_schema_change.py --apply

# Step 4: Validate schema
python scripts/apply_schema_change.py --validate
```

### Rollback Schema Changes

```bash
# Rollback last migration
python scripts/apply_schema_change.py --rollback

# Rollback multiple migrations
python scripts/apply_schema_change.py --rollback --rollback-count 3

# Rollback with confirmation skip (use with caution)
python scripts/apply_schema_change.py --rollback --yes
```

### Schema Validation

```bash
# Validate current schema
python scripts/apply_schema_change.py --validate

# Validate specific schema
python scripts/apply_schema_change.py --validate --schema public

# Check migration status
python scripts/apply_schema_change.py --status
```

---

## Migration Testing

### Test Migration Syntax

```bash
# Test migration syntax
python scripts/test_migration.py --migration-file "migration.sql"

# Run all tests
python scripts/test_migration.py --all

# Run specific test categories
python scripts/test_migration.py --syntax
python scripts/test_migration.py --integrity
python scripts/test_migration.py --performance
```

### Test Categories

- **Syntax Tests**: SQL syntax validation, dangerous operations detection
- **Integrity Tests**: Data type definitions, index definitions, foreign key constraints
- **Performance Tests**: Query complexity analysis, execution time estimation
- **Rollback Tests**: Rollback SQL presence, rollback SQL validity
- **Integration Tests**: Migration dependencies, breaking changes detection

### Test Results

Test results are saved to `test_reports/migration_test_report_YYYYMMDD_HHMMSS.json` in JSON format for automated processing.

---

## Production Deployment

### Pre-Deployment Checklist

```bash
# Run automated pre-deployment checks
python scripts/deploy_to_production.py --auto --migration-file "migration.sql" --dry-run
```

### Deployment Steps

1. **Validate Migration**
   ```bash
   python scripts/deploy_to_production.py --validate --migration-file "migration.sql"
   ```

2. **Create Backup**
   ```bash
   python scripts/deploy_to_production.py --backup-only
   ```

3. **Deploy to Production**
   ```bash
   python scripts/deploy_to_production.py --auto --migration-file "migration.sql"
   ```

4. **Type "DEPLOY"** when prompted for confirmation

5. **Monitor Deployment Progress**
   ```bash
   tail -f logs/production_deployment_*.log
   ```

6. **Verify Post-Deployment**
   - Check application logs
   - Test API endpoints
   - Verify database schema
   - Monitor performance

### Post-Deployment Verification

```bash
# Check database connectivity
python scripts/deploy_to_production.py --status

# Verify schema changes
psql -c "\dt"  # Should show new/modified tables

# Test application functionality
curl http://localhost:8000/api/dioceses
```

---

## Troubleshooting

### Common Issues

#### Issue: Database Connection Failed

**Symptoms**: `Failed to connect to local database`, `OperationalError`

**Solution**:
```bash
# Check Supabase status
supabase status

# Start Supabase if not running
supabase start

# Verify environment variables
cat .env | grep SUPABASE
```

#### Issue: Migration Not Applied

**Symptoms**: Migration shows as pending but should be applied

**Solution**:
```bash
# Check migration status
python scripts/apply_schema_change.py --status

# Apply pending migrations
python scripts/apply_schema_change.py --apply

# Or use Supabase CLI directly
supabase migration up --local
```

#### Issue: Rollback Failed

**Symptoms**: `Cannot rollback N migration(s)`, `relation does not exist`

**Solution**:
```bash
# Check migration status
python scripts/apply_schema_change.py --status

# You're trying to rollback more than applied
# Adjust rollback count
python scripts/apply_schema_change.py --rollback --rollback-count 1

# Or reset database completely
supabase db reset --local
```

#### Issue: Schema Validation Failed

**Symptoms**: `Schema validation failed`, errors in validation output

**Solution**:
```bash
# Review validation errors
python scripts/apply_schema_change.py --validate

# Check for specific issues
supabase db lint --local --schema public

# Consider rolling back
python scripts/apply_schema_change.py --rollback
```

#### Issue: Production Deployment Failed

**Symptoms**: Deployment fails during production deployment

**Solution**:
```bash
# Check deployment logs
tail -100 logs/production_deployment_*.log

# Verify production credentials
cat .env | grep SUPABASE_URL_PRD

# Test production connection
python scripts/deploy_to_production.py --status

# Rollback if needed
python scripts/deploy_to_production.py --rollback
```

### Debug Mode

```bash
# Enable debug logging
supabase db diff --local --debug
supabase migration up --local --debug

# Check logs
docker logs supabase_db_diocesan-vitality
supabase logs
```

---

## File Locations

### Project Structure

```
diocesan-vitality/
├── .env                          # Environment configuration (git-ignored)
├── Makefile                      # Build and deployment commands
├── scripts/
│   ├── reset_local_database.py   # Database reset script
│   ├── apply_schema_change.py    # Schema change management
│   ├── test_migration.py         # Migration testing
│   ├── deploy_to_production.py   # Production deployment
│   └── backup_production_database.py  # Database backup
├── supabase/
│   ├── config.toml               # Supabase configuration
│   ├── migrations/               # Migration files
│   │   └── 20260621150000_name.sql
│   ├── seed.sql                  # Seed data
│   └── roles.sql                 # Custom roles
├── sql/
│   └── initial_schema.sql        # Initial database schema
├── backup/                       # Database backups (auto-created)
│   └── db_backup_*.sql.gz
├── logs/                         # Operation logs (auto-created)
│   ├── production_deployment_*.log
│   └── schema_change_*.log
└── test_reports/                 # Test results (auto-created)
    └── migration_test_report_*.json
```

### Documentation Files

```
docs/
├── DATABASE_QUICK_REFERENCE.md  # This file
├── LOCAL_DEVELOPMENT.md          # Local development setup
├── SCHEMA_CHANGE_MANAGEMENT.md   # Schema change guide
├── SCHEMA_CHANGE_QUICK_REFERENCE.md  # Schema change quick ref
├── PRODUCTION_MIGRATION_GUIDE.md # Production deployment guide
├── supabase-migration-reference.md  # Supabase CLI reference
├── supabase-migration-quick-reference.md  # Supabase quick ref
├── END_TO_END_TEST_REPORT.md     # Testing report
├── E2E_TESTING_SUMMARY.md        # Testing summary
├── ACTIONABLE_RECOMMENDATIONS.md # Implementation recommendations
└── TESTING_COMPLETION_SUMMARY.md # Testing completion summary
```

---

## Environment Variables

### Required Environment Variables

Create a `.env` file in the project root with these required variables:

```bash
# Production Database Credentials
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your_supabase_service_role_key"

# Development Database Credentials
SUPABASE_URL_DEV="http://localhost:54321"
SUPABASE_KEY_DEV="your_dev_service_role_key"
SUPABASE_DB_PASSWORD_DEV="your_dev_db_password"

# AI Integration
GENAI_API_KEY="your_google_gemini_api_key"

# Search Integration
SEARCH_API_KEY="your_google_custom_search_api_key"
SEARCH_CX="your_custom_search_engine_id"

# Monitoring
MONITORING_URL="http://localhost:8000"

# Docker Hub (for deployment)
DOCKER_USERNAME="your_dockerhub_username"
DOCKER_PASSWORD="your_dockerhub_password_or_token"
```

### Optional Environment Variables

For enhanced functionality, configure these optional variables:

```bash
# Staging Environment Credentials
SUPABASE_URL_STG="https://your-staging-project.supabase.co"
SUPABASE_KEY_STG="your_staging_service_role_key"
SUPABASE_DB_PASSWORD_STG="your_staging_db_password"

# Database Reset Configuration
SUPABASE_STOP_WAIT_TIME="10"  # Seconds to wait after stopping Supabase
```

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit environment file
nano .env  # or use your preferred editor

# Verify configuration
python scripts/deploy_to_production.py --status --dry-run
```

---

## Best Practices

### Development Workflow

1. **Always test locally** before deploying to production
2. **Use descriptive migration names** for better traceability
3. **Review generated migrations** before applying
4. **Create backups** for important changes
5. **Validate schema** after applying migrations
6. **Test rollback procedures** before production deployment
7. **Commit migration files** to version control
8. **Document complex changes** with comments

### Production Deployment

1. **Always use dry-run mode** for testing first
2. **Create backups** before every deployment
3. **Test in staging** if available
4. **Monitor deployments** closely
5. **Have rollback plans** ready
6. **Document deployments** for audit trails
7. **Notify stakeholders** of changes
8. **Verify post-deployment** functionality

### Safety Measures

1. **Never skip confirmations** unless in automated scripts
2. **Always backup** before destructive operations
3. **Test rollback SQL** manually before production
4. **Use transactions** for data consistency
5. **Monitor performance** after changes
6. **Keep migration history** for rollback capability
7. **Document all changes** for team knowledge

---

## Quick Command Reference

### Database Operations

```bash
# Connection and Status
make db-check                    # Test database connection
supabase status                 # Check Supabase status
python scripts/deploy_to_production.py --status  # Deployment status

# Migration Management
python scripts/apply_schema_change.py --status    # Migration status
supabase migration list --local               # List migrations
supabase migration up --local                 # Apply migrations

# Schema Operations
python scripts/apply_schema_change.py --validate  # Validate schema
supabase db lint --local --schema public      # Lint schema
supabase db diff --local --schema public      # Generate diff

# Backup and Restore
python scripts/backup_production_database.py  # Create backup
python scripts/deploy_to_production.py --backup-only  # Backup only
python scripts/deploy_to_production.py --rollback     # Rollback
```

### Development Operations

```bash
# Environment Setup
make env-check                    # Check environment
make install                      # Install dependencies
make start                        # Start services
make stop                         # Stop services

# Testing
make test                         # Run all tests
make test-quick                   # Run quick tests
python scripts/test_migration.py  # Test migration

# Pipeline Operations
make pipeline                     # Run pipeline test
make pipeline-single DIOCESE_ID=123  # Single diocese
```

### Production Operations

```bash
# Deployment
python scripts/deploy_to_production.py --auto --migration-file "migration.sql"  # Deploy
python scripts/deploy_to_production.py --validate --migration-file "migration.sql"  # Validate

# Monitoring
tail -f logs/production_deployment_*.log  # View logs
kubectl logs -n diocesan-vitality deployment/backend-deployment --tail=100  # K8s logs

# Emergency
python scripts/deploy_to_production.py --rollback --yes  # Emergency rollback
```

---

## Additional Resources

### Documentation

- **[Local Development Guide](LOCAL_DEVELOPMENT.md)** - Complete local development setup
- **[Schema Change Management](SCHEMA_CHANGE_MANAGEMENT.md)** - Schema change workflow
- **[Production Migration Guide](PRODUCTION_MIGRATION_GUIDE.md)** - Production deployment
- **[Supabase Migration Reference](supabase-migration-reference.md)** - Supabase CLI commands
- **[End-to-End Test Report](END_TO_END_TEST_REPORT.md)** - Testing results

### External Resources

- **[Supabase CLI Documentation](https://supabase.com/docs/guides/cli)** - Official Supabase docs
- **[PostgreSQL Documentation](https://www.postgresql.org/docs/)** - PostgreSQL reference
- **[Database Best Practices](https://supabase.com/docs/guides/database)** - Database design guide

---

## Support and Troubleshooting

### Getting Help

- **Documentation**: Check relevant documentation files first
- **Logs**: Review log files in `logs/` directory
- **Test Results**: Check `test_reports/` for detailed test output
- **Environment**: Verify `.env` configuration
- **Community**: Check project issues and discussions

### Common Solutions

1. **Connection Issues**: Check Supabase status and environment variables
2. **Migration Issues**: Validate migration syntax and check dependencies
3. **Performance Issues**: Monitor database queries and indexes
4. **Deployment Issues**: Review logs and verify credentials
5. **Rollback Issues**: Check migration status and database state

---

## Summary

This quick reference guide provides essential commands and workflows for database operations in the Diocesan Vitality project. Key points:

- **Always test locally** before production deployment
- **Use automatic workflows** for most operations
- **Create backups** before destructive operations
- **Validate changes** after applying migrations
- **Monitor deployments** closely in production
- **Have rollback plans** ready for emergencies
- **Document changes** for team knowledge sharing

For detailed information on specific topics, refer to the comprehensive documentation files listed in the [Documentation Files](#documentation-files) section.

---

*Last Updated: June 21, 2026*  
*Version: 1.0*  
*Project: Diocesan Vitality*