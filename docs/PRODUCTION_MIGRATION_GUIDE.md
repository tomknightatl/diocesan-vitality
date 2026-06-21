# 🚀 Production Migration Guide

**Complete deployment guide for production database migrations with comprehensive safety procedures, testing protocols, and rollback capabilities.**

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites and Setup](#prerequisites-and-setup)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Migration Testing Procedures](#migration-testing-procedures)
- [Deployment Steps](#deployment-steps)
- [Post-Deployment Verification](#post-deployment-verification)
- [Rollback Procedures](#rollback-procedures)
- [Approval Process](#approval-process)
- [Emergency Procedures](#emergency-procedures)
- [Safety Measures and Best Practices](#safety-measures-and-best-practices)
- [Common Scenarios and Examples](#common-scenarios-and-examples)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Integration with CI/CD](#integration-with-cicd)
- [Team Responsibilities and Escalation](#team-responsibilities-and-escalation)
- [See Also](#see-also)
- [Historical Revisions](#historical-revisions)

---

## Overview

This guide provides comprehensive procedures for deploying database migrations to production environments safely and reliably. The production migration process implements multiple layers of safety checks, automated backups, validation procedures, and rollback capabilities to ensure database integrity and minimize downtime.

### Production Migration Workflow

The production migration process follows a structured 8-phase workflow:

1. **Pre-Deployment Checks** - Comprehensive validation of environment, files, and resources
2. **Backup Creation** - Automatic full database backup before any changes
3. **Migration Validation** - Syntax and safety verification of migration files
4. **Staging Testing** - Optional testing on staging environment (if available)
5. **Manual Confirmation** - Explicit approval required for production changes
6. **Production Deployment** - Execution of migration with detailed logging
7. **Post-Deployment Verification** - Integrity and functionality checks
8. **Documentation** - Recording deployment results and lessons learned

### Key Safety Features

- **Automatic Backups**: Full database backup before every deployment
- **Multi-Layer Validation**: Environment, syntax, and safety checks
- **Manual Confirmation**: Explicit "DEPLOY" confirmation required
- **Rollback Capability**: Verified rollback procedures with clear instructions
- **Comprehensive Logging**: Detailed audit trail of all operations
- **Dry-Run Mode**: Safe testing without making changes
- **Staging Testing**: Optional pre-production validation

### Deployment Script

The primary tool for production migrations is `scripts/deploy_to_production.py`, which implements all safety features and workflows described in this guide.

---

## Prerequisites and Setup

### System Requirements

#### Required Software

- **Python 3.8+**: Script execution and automation
- **Supabase CLI**: Database operations and migration management
- **Docker**: Database backup and restore operations
- **Git**: Version control and deployment tracking

#### Installation Commands

```bash
# Install Python 3.8+ (if not already installed)
# Ubuntu/Debian:
sudo apt update && sudo apt install python3.8 python3-pip

# macOS:
brew install python@3.8

# Install Supabase CLI
curl -fsSL https://supabase.com/install.sh | bash

# Install Docker
# Ubuntu/Debian:
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# macOS:
brew install --cask docker
```

### Environment Configuration

#### Required Environment Variables

Create a `.env` file in the project root with the following required variables:

```bash
# Production Database Credentials
SUPABASE_URL_PRD="https://your-project.supabase.co"
SUPABASE_DB_PASSWORD_PRD="your_production_db_password"
```

#### Optional Environment Variables

For enhanced functionality, configure these optional variables:

```bash
# Staging Environment Credentials (for staging testing)
SUPABASE_URL_STG="https://your-staging-project.supabase.co"
SUPABASE_DB_PASSWORD_STG="your_staging_db_password"
```

#### Environment Setup Steps

1. **Copy Environment Template**
   ```bash
   cp .env.example .env
   ```

2. **Edit Environment File**
   ```bash
   nano .env  # or your preferred editor
   ```

3. **Verify Configuration**
   ```bash
   # Test production database connection
   python scripts/deploy_to_production.py --status --dry-run
   ```

### Directory Structure

Ensure the following directory structure exists:

```
diocesan-vitality/
├── .env                          # Environment configuration (git-ignored)
├── scripts/
│   ├── deploy_to_production.py   # Main deployment script
│   └── test_deploy_to_production.py  # Testing script
├── supabase/
│   └── migrations/               # Migration files
├── backup/                       # Database backups (auto-created)
└── logs/                         # Deployment logs (auto-created)
```

### Initial Setup Validation

Validate your setup before attempting any production deployments:

```bash
# Run comprehensive setup validation
python scripts/deploy_to_production.py --status

# Expected output:
# ✓ Environment validation completed successfully
# ✓ Production database connection verified
# ✓ Supabase CLI version: X.XX.X
# ✓ Docker version: X.XX.X
```

---

## Pre-Deployment Checklist

### Comprehensive Pre-Flight Validation

The pre-deployment checklist ensures all safety measures are in place before any production changes. This checklist is automatically executed by the deployment script but should also be manually verified.

#### 1. Environment Validation

**Purpose**: Ensure all required tools and configurations are properly set up.

**Checks Performed**:
- [ ] Supabase CLI installed and accessible
- [ ] Docker installed and running
- [ ] Python 3.8+ available
- [ ] Production database credentials configured
- [ ] Network connectivity to production database
- [ ] Sufficient disk space (minimum 1GB free)

**Validation Command**:
```bash
python scripts/deploy_to_production.py --status --dry-run
```

**Success Criteria**:
- All tools show correct versions
- Database connection test succeeds
- No credential errors
- Disk space check passes

#### 2. Migration File Validation

**Purpose**: Ensure migration files are valid and safe to deploy.

**Checks Performed**:
- [ ] Migration file exists and is readable
- [ ] File is not empty
- [ ] File size is reasonable (not suspiciously large)
- [ ] SQL syntax is valid
- [ ] No dangerous operations (DROP DATABASE, DROP SCHEMA, TRUNCATE)
- [ ] Proper transaction handling (BEGIN/COMMIT)
- [ ] Statements are properly terminated

**Validation Command**:
```bash
python scripts/deploy_to_production.py --validate --migration-file "migration.sql"
```

**Example Valid Migration**:
```sql
-- Migration: 20260621150000_add_user_preferences.sql
-- Description: Add user preferences table

BEGIN;

-- Create table
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

-- Add comments
COMMENT ON TABLE user_preferences IS 'User preference settings';

COMMIT;
```

**Common Issues to Check**:
- Missing transaction blocks
- Unterminated SQL statements
- Dangerous operations
- Syntax errors
- Missing foreign key references

#### 3. Backup Verification

**Purpose**: Ensure backup capability and verify recent backups exist.

**Checks Performed**:
- [ ] Backup directory exists and is writable
- [ ] Sufficient disk space for new backup
- [ ] Recent backup exists (within 24 hours recommended)
- [ ] Backup files are not corrupted
- [ ] Backup compression is working

**Validation Commands**:
```bash
# Check backup directory
ls -lh backup/

# Verify recent backups
find backup/ -name "db_backup_*.sql.gz" -mtime -1

# Test backup creation
python scripts/deploy_to_production.py --backup-only --dry-run
```

**Backup Retention Policy**:
- Keep last 7 daily backups
- Keep last 4 weekly backups
- Keep last 12 monthly backups
- Archive older backups to cold storage

#### 4. Staging Environment Check (Optional)

**Purpose**: Validate staging environment for pre-production testing.

**Checks Performed**:
- [ ] Staging credentials configured (if available)
- [ ] Staging database is accessible
- [ ] Staging schema matches production structure
- [ ] Staging has sufficient test data

**Validation Command**:
```bash
# Check if staging is configured
grep SUPABASE_URL_STG .env

# Test staging connection (if configured)
python scripts/deploy_to_production.py --status --dry-run
# Look for: "Staging credentials loaded (staging testing available)"
```

#### 5. Application State Verification

**Purpose**: Ensure application is in a stable state for migration.

**Checks Performed**:
- [ ] No ongoing maintenance windows
- [ ] Application is running normally
- [ ] No critical errors in logs
- [ ] Database performance is normal
- [ ] No long-running transactions

**Verification Commands**:
```bash
# Check application logs
kubectl logs -n diocesan-vitality deployment/backend-deployment --tail=100

# Check database performance
# (Use Supabase dashboard or monitoring tools)

# Check for long-running queries
# (See Post-Deployment Verification section)
```

#### 6. Stakeholder Notification

**Purpose**: Ensure all stakeholders are aware of upcoming deployment.

**Notification Checklist**:
- [ ] Development team notified
- [ ] Operations team notified
- [ ] Stakeholders informed of potential downtime
- [ ] Support team briefed on changes
- [ ] Documentation updated
- [ ] Rollback plan communicated

**Notification Template**:
```
Subject: Production Database Migration - [Date/Time]

Deployment Details:
- Migration: [Migration name/description]
- Scheduled Time: [Date and time]
- Expected Downtime: [Duration or "None"]
- Impact: [Description of changes]

Rollback Plan:
- Rollback available: Yes/No
- Rollback time: [Estimated duration]
- Rollback procedure: [Reference to documentation]

Contact:
- Lead: [Name]
- Emergency Contact: [Name/Phone]

Questions or concerns? Contact [Name]
```

#### 7. Change Management Approval

**Purpose**: Ensure proper approval process is followed.

**Approval Checklist**:
- [ ] Migration reviewed by database administrator
- [ ] Code review completed
- [ ] Testing documented
- [ ] Risk assessment completed
- [ ] Rollback plan approved
- [ ] Change request approved
- [ ] Scheduled maintenance window approved

### Pre-Deployment Checklist Summary

Use this summary checklist before every production deployment:

```bash
# Quick pre-deployment validation
python scripts/deploy_to_production.py --auto --migration-file "migration.sql" --dry-run

# Manual checklist items:
□ Environment validated
□ Migration file validated
□ Backup capability verified
□ Staging tested (if available)
□ Application state verified
□ Stakeholders notified
□ Approvals obtained
□ Rollback plan ready
```

---

## Migration Testing Procedures

### Testing Framework Overview

The migration testing framework ensures migrations are safe and reliable before production deployment. Testing occurs at multiple levels:

1. **Local Development Testing**: Initial validation on local environment
2. **Staging Environment Testing**: Pre-production validation (if available)
3. **Automated Syntax Testing**: SQL syntax and safety validation
4. **Performance Testing**: Impact assessment on database performance
5. **Rollback Testing**: Verification of rollback procedures

### Local Development Testing

#### Purpose

Validate migrations in a safe, isolated environment before production deployment.

#### Testing Procedure

1. **Start Local Supabase Stack**
   ```bash
   supabase start
   ```

2. **Apply Migration Locally**
   ```bash
   python scripts/apply_schema_change.py --auto --name "test_migration"
   ```

3. **Validate Schema Changes**
   ```bash
   # Check schema structure
   supabase db diff --schema public

   # Validate schema integrity
   python scripts/apply_schema_change.py --validate
   ```

4. **Test Application Functionality**
   ```bash
   # Run application tests
   pytest tests/

   # Test specific functionality affected by migration
   pytest tests/test_migration_impact.py
   ```

5. **Verify Data Integrity**
   ```bash
   # Check for data corruption
   supabase db reset --debug

   # Verify constraints and indexes
   psql -c "\d+ table_name"
   ```

#### Local Testing Checklist

- [ ] Migration applies without errors
- [ ] Schema changes match expectations
- [ ] Application tests pass
- [ ] Data integrity maintained
- [ ] Performance impact acceptable
- [ ] Rollback works correctly

### Staging Environment Testing

#### Purpose

Validate migrations in a production-like environment before actual production deployment.

#### Testing Procedure

1. **Create Staging Backup**
   ```bash
   python scripts/deploy_to_production.py --backup-only --dry-run
   # Manually copy backup to staging environment
   ```

2. **Apply Migration to Staging**
   ```bash
   # The deployment script automatically tests on staging if configured
   python scripts/deploy_to_production.py --auto --migration-file "migration.sql" --dry-run
   ```

3. **Run Staging Tests**
   ```bash
   # Deploy to staging environment
   # (Use your staging deployment process)

   # Run integration tests
   pytest tests/integration/ --env=staging

   # Test with staging data
   # (Use staging-specific test procedures)
   ```

4. **Monitor Staging Performance**
   ```bash
   # Monitor database performance
   # (Use Supabase dashboard or monitoring tools)

   # Check for slow queries
   # (See Performance Testing section)
   ```

5. **Verify Staging Rollback**
   ```bash
   # Test rollback procedure
   python scripts/deploy_to_production.py --rollback --dry-run
   ```

#### Staging Testing Checklist

- [ ] Staging backup created successfully
- [ ] Migration applies to staging without errors
- [ ] Integration tests pass on staging
- [ ] Performance impact acceptable
- [ ] No data loss or corruption
- [ ] Rollback procedure verified

### Automated Syntax Testing

#### Purpose

Automatically validate SQL syntax and detect dangerous operations.

#### Testing Procedure

1. **Syntax Validation**
   ```bash
   python scripts/deploy_to_production.py --validate --migration-file "migration.sql"
   ```

2. **Safety Checks**
   The deployment script automatically checks for:
   - SQL syntax errors
   - Dangerous operations (DROP DATABASE, DROP SCHEMA, TRUNCATE)
   - Missing transaction blocks
   - Unterminated statements
   - Empty migration files

3. **Manual Review**
   Always review the migration file manually:
   ```bash
   cat supabase/migrations/migration.sql
   ```

#### Syntax Testing Checklist

- [ ] SQL syntax is valid
- [ ] No dangerous operations detected
- [ ] Transaction blocks present
- [ ] Statements properly terminated
- [ ] File is not empty
- [ ] Manual review completed

### Performance Testing

#### Purpose

Assess the performance impact of migrations on production database.

#### Testing Procedure

1. **Baseline Performance Measurement**
   ```bash
   # Measure current performance metrics
   # - Query execution times
   # - Database connection count
   # - CPU and memory usage
   # - Disk I/O operations
   ```

2. **Apply Migration and Measure**
   ```bash
   # Apply migration to test environment
   python scripts/apply_schema_change.py --auto --name "performance_test"

   # Measure post-migration performance
   # Compare with baseline
   ```

3. **Load Testing** (if applicable)
   ```bash
   # Simulate production load
   # Monitor performance under load
   # Check for bottlenecks
   ```

4. **Query Performance Analysis**
   ```bash
   # Analyze affected queries
   EXPLAIN ANALYZE SELECT * FROM affected_table;

   # Check for missing indexes
   # (Use database monitoring tools)
   ```

#### Performance Testing Checklist

- [ ] Baseline performance measured
- [ ] Post-migration performance acceptable
- [ ] No significant query degradation
- [ ] Resource usage within limits
- [ ] Load testing completed (if applicable)
- [ ] Performance optimization applied (if needed)

### Rollback Testing

#### Purpose

Verify rollback procedures work correctly before production deployment.

#### Testing Procedure

1. **Create Test Backup**
   ```bash
   python scripts/deploy_to_production.py --backup-only
   ```

2. **Apply Test Migration**
   ```bash
   python scripts/deploy_to_production.py --deploy --migration-file "test_migration.sql"
   ```

3. **Verify Migration Applied**
   ```bash
   # Check that changes are present
   psql -c "\d+ new_table"
   ```

4. **Perform Rollback**
   ```bash
   python scripts/deploy_to_production.py --rollback
   ```

5. **Verify Rollback Success**
   ```bash
   # Check that changes are reverted
   psql -c "\dt"  # Should not show new_table

   # Verify data integrity
   # Run application tests
   ```

#### Rollback Testing Checklist

- [ ] Backup created successfully
- [ ] Migration applies correctly
- [ ] Changes verified
- [ ] Rollback executes without errors
- [ ] Changes completely reverted
- [ ] Data integrity maintained
- [ ] Application functions normally

### Testing Documentation

Document all testing results:

```markdown
## Migration Test Results

**Migration**: [Migration name]
**Date**: [Test date]
**Tester**: [Tester name]

### Local Testing
- Status: ✓ PASS / ✗ FAIL
- Issues: [Any issues found]
- Resolution: [How issues were resolved]

### Staging Testing
- Status: ✓ PASS / ✗ FAIL
- Issues: [Any issues found]
- Resolution: [How issues were resolved]

### Performance Testing
- Baseline: [Performance metrics]
- Post-migration: [Performance metrics]
- Impact: [Acceptable / Unacceptable]

### Rollback Testing
- Status: ✓ PASS / ✗ FAIL
- Issues: [Any issues found]

### Approval
- Ready for production: YES / NO
- Additional testing required: [If any]
```

---

## Deployment Steps

### Step-by-Step Deployment Process

Follow these detailed steps for safe production deployment.

#### Phase 1: Preparation

**Step 1.1: Complete Pre-Deployment Checklist**

```bash
# Run automated pre-deployment checks
python scripts/deploy_to_production.py --auto --migration-file "migration.sql" --dry-run
```

**Manual Verification**:
- [ ] All pre-deployment checklist items completed
- [ ] Stakeholders notified
- [ ] Approvals obtained
- [ ] Rollback plan ready

**Step 1.2: Verify Migration File**

```bash
# Validate migration syntax
python scripts/deploy_to_production.py --validate --migration-file "migration.sql"

# Review migration content
cat supabase/migrations/migration.sql
```

**Step 1.3: Check Deployment Status**

```bash
# Check current deployment status
python scripts/deploy_to_production.py --status

# Verify recent backups exist
ls -lh backup/
```

#### Phase 2: Backup Creation

**Step 2.1: Create Production Backup**

```bash
# Create backup only (manual workflow)
python scripts/deploy_to_production.py --backup-only
```

**Expected Output**:
```
================================================================================
CREATING PRODUCTION DATABASE BACKUP
================================================================================
Running pg_dump on production database...
   Host: aws-0-us-east-2.pooler.supabase.com
   Database: postgres
   User: postgres.your-project-id
================================================================================
✓ PRODUCTION BACKUP CREATED SUCCESSFULLY
================================================================================
   Backup file: backup/db_backup_20260621_150000.sql.gz
   Original size: 125.50 MB
   Compressed size: 15.25 MB
   Compression ratio: 87.9%
   Created: 2026-06-21 15:00:00
```

**Step 2.2: Verify Backup Integrity**

```bash
# Check backup file exists
ls -lh backup/db_backup_*.sql.gz

# Verify backup can be decompressed
gunzip -t backup/db_backup_20260621_150000.sql.gz
```

**Step 2.3: Document Backup**

Record backup information:
```markdown
## Pre-Deployment Backup

**Date**: 2026-06-21 15:00:00
**File**: db_backup_20260621_150000.sql.gz
**Size**: 15.25 MB (compressed)
**Migration**: [Migration name]
**Purpose**: Pre-deployment backup for rollback
```

#### Phase 3: Migration Validation

**Step 3.1: Validate Migration Syntax**

```bash
# Automated syntax validation
python scripts/deploy_to_production.py --validate --migration-file "migration.sql"
```

**Expected Output**:
```
✓ Migration syntax is valid: supabase/migrations/migration.sql
```

**Step 3.2: Manual Code Review**

Review the migration file for:
- Correct SQL syntax
- Appropriate transaction handling
- No dangerous operations
- Proper error handling
- Data preservation

**Step 3.3: Staging Testing** (if available)

```bash
# The deployment script will automatically test on staging if configured
python scripts/deploy_to_production.py --auto --migration-file "migration.sql" --dry-run
```

#### Phase 4: Manual Confirmation

**Step 4.1: Review Deployment Summary**

The deployment script will display a summary:

```
================================================================================
DEPLOYMENT SUMMARY
================================================================================
Migration file: supabase/migrations/migration.sql
Backup file: backup/db_backup_20260621_150000.sql.gz
Backup size: 15.25 MB
Deployment time: 2026-06-21 15:00:00
Environment: Production
================================================================================
```

**Step 4.2: Provide Manual Confirmation**

```
================================================================================
⚠️  PRODUCTION DEPLOYMENT CONFIRMATION
================================================================================
You are about to deploy changes to the PRODUCTION database.
This action cannot be undone without a rollback.

To proceed, type 'DEPLOY' and press Enter:
================================================================================
>
```

**Type**: `DEPLOY`

**Step 4.3: Confirm Rollback Instructions**

The script will display rollback instructions:

```
================================================================================
ROLLBACK INSTRUCTIONS
================================================================================
If you need to rollback, use the following command:

  python scripts/deploy_to_production.py --rollback --backup-file db_backup_20260621_150000.sql.gz

Or to rollback using the latest backup:

  python scripts/deploy_to_production.py --rollback

Backup file: backup/db_backup_20260621_150000.sql.gz
================================================================================
```

#### Phase 5: Production Deployment

**Step 5.1: Execute Deployment**

```bash
# Automatic workflow (recommended)
python scripts/deploy_to_production.py --auto --migration-file "migration.sql"

# Or manual workflow
python scripts/deploy_to_production.py --deploy --migration-file "migration.sql"
```

**Expected Output**:
```
================================================================================
DEPLOYING TO PRODUCTION
================================================================================
Deploying migration file: supabase/migrations/migration.sql
================================================================================
✓ DEPLOYMENT TO PRODUCTION SUCCESSFUL
================================================================================
```

**Step 5.2: Monitor Deployment Progress**

Watch for:
- Progress messages
- Any warnings or errors
- Completion status

**Step 5.3: Verify Deployment Success**

```bash
# Check deployment logs
tail -f logs/production_deployment_*.log

# Verify migration was applied
# (Use Supabase dashboard or direct database query)
```

#### Phase 6: Post-Deployment Verification

**Step 6.1: Run Post-Deployment Checks**

The deployment script automatically runs verification checks:

```
================================================================================
POST-DEPLOYMENT VERIFICATION
================================================================================
Check 1: Verifying production database connectivity...
✓ Production database is accessible
Check 2: Verifying database integrity...
✓ Database integrity verified
Check 3: Checking for long-running queries...
✓ No long-running queries detected
Check 4: Verifying table counts...
✓ Table counts verified
================================================================================
✓ POST-DEPLOYMENT VERIFICATION PASSED
================================================================================
```

**Step 6.2: Manual Verification**

Perform manual checks:
- [ ] Database schema changes applied correctly
- [ ] Application functions normally
- [ ] No errors in application logs
- [ ] Performance is acceptable
- [ ] Data integrity maintained

**Step 6.3: Application Testing**

```bash
# Run application tests
pytest tests/

# Test specific functionality
# (Use your application testing procedures)
```

#### Phase 7: Documentation

**Step 7.1: Document Deployment**

Create deployment record:

```markdown
## Production Deployment Record

**Date**: 2026-06-21 15:00:00
**Migration**: migration.sql
**Deployed By**: [Your name]
**Status**: ✓ SUCCESS

### Pre-Deployment
- Backup: db_backup_20260621_150000.sql.gz
- Checks: All passed
- Approvals: Obtained

### Deployment
- Start Time: 15:00:00
- End Time: 15:05:00
- Duration: 5 minutes
- Issues: None

### Post-Deployment
- Verification: All checks passed
- Application Status: Normal
- Performance: Acceptable

### Rollback Information
- Backup Available: Yes
- Rollback Tested: Yes
- Rollback Time: ~5 minutes
```

**Step 7.2: Notify Stakeholders**

Send deployment completion notification:

```
Subject: Production Migration Completed - [Migration Name]

Deployment Details:
- Migration: [Migration name]
- Completed: [Date and time]
- Duration: [Deployment duration]
- Status: ✓ SUCCESS

Verification:
- All checks passed
- Application functioning normally
- No issues detected

Next Steps:
- Monitor application performance
- Watch for any issues
- Report any problems immediately

Contact:
- Lead: [Name]
- Emergency Contact: [Name/Phone]
```

### Complete Deployment Example

Here's a complete example of deploying a migration:

```bash
# 1. Validate migration
python scripts/deploy_to_production.py --validate --migration-file "20260621150000_add_user_preferences.sql"

# 2. Run automatic deployment workflow
python scripts/deploy_to_production.py --auto --migration-file "20260621150000_add_user_preferences.sql"

# 3. Type "DEPLOY" when prompted
# 4. Wait for deployment to complete
# 5. Verify post-deployment checks pass
# 6. Monitor application logs
# 7. Document deployment results
```

### Deployment Time Estimates

Typical deployment times:

- **Simple Migration** (add table, add index): 2-5 minutes
- **Complex Migration** (data transformation, schema changes): 5-15 minutes
- **Large Data Migration** (significant data changes): 15-60 minutes
- **Rollback**: 5-15 minutes

**Factors affecting deployment time**:
- Database size
- Migration complexity
- Network latency
- Database load
- Backup/restore time

---

## Post-Deployment Verification

### Comprehensive Verification Procedures

Post-deployment verification ensures the migration was successful and the database is in a healthy state.

### Automated Verification Checks

The deployment script automatically performs these checks:

#### Check 1: Database Connectivity

**Purpose**: Verify production database is accessible.

**Check Performed**:
```sql
SELECT 1;
```

**Success Criteria**: Query returns `1` without errors.

#### Check 2: Database Integrity

**Purpose**: Verify database tables are not corrupted.

**Check Performed**:
```sql
SELECT
    schemaname,
    tablename,
    n_live_tup
FROM pg_stat_user_tables
ORDER BY schemaname, tablename;
```

**Success Criteria**: All tables return row counts without errors.

#### Check 3: Long-Running Queries

**Purpose**: Detect any queries that have been running too long.

**Check Performed**:
```sql
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
AND state != 'idle';
```

**Success Criteria**: No long-running queries detected.

#### Check 4: Table Counts

**Purpose**: Verify expected tables exist in the database.

**Check Performed**:
```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

**Success Criteria**: All expected tables are present.

### Manual Verification Procedures

#### Schema Verification

**Step 1: Verify Schema Changes**

```bash
# Connect to production database
psql -h aws-0-us-east-2.pooler.supabase.com -U postgres.project_id -d postgres

# Check new tables exist
\dt+ new_table_name

# Verify table structure
\d+ new_table_name

# Check indexes exist
\di+ index_name

# Verify constraints
\d+ table_name
```

**Step 2: Verify Data Integrity**

```sql
-- Check row counts
SELECT COUNT(*) FROM new_table_name;

-- Verify foreign key relationships
SELECT * FROM new_table_name LIMIT 10;

-- Check for NULL values where not expected
SELECT COUNT(*) FROM table_name WHERE important_column IS NULL;

-- Verify data consistency
SELECT column1, COUNT(*)
FROM table_name
GROUP BY column1
HAVING COUNT(*) > 1;
```

#### Application Verification

**Step 1: Check Application Logs**

```bash
# Check backend logs
kubectl logs -n diocesan-vitality deployment/backend-deployment --tail=100

# Check frontend logs
kubectl logs -n diocesan-vitality deployment/frontend-deployment --tail=100

# Check for errors
kubectl logs -n diocesan-vitality deployment/backend-deployment --tail=100 | grep -i error
```

**Step 2: Test Application Functionality**

```bash
# Run application tests
pytest tests/

# Test specific endpoints
curl -X GET https://api.example.com/endpoint

# Test authentication
curl -X POST https://api.example.com/auth/login -d '{"username":"test","password":"test"}'
```

**Step 3: Monitor Application Performance**

```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s https://api.example.com/endpoint

# Monitor resource usage
kubectl top pods -n diocesan-vitality

# Check database performance
# (Use Supabase dashboard or monitoring tools)
```

#### Performance Verification

**Step 1: Query Performance Analysis**

```sql
-- Analyze slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check query plans
EXPLAIN ANALYZE SELECT * FROM new_table_name WHERE condition = 'value';

-- Verify index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

**Step 2: Resource Usage Monitoring**

```bash
# Check database connections
SELECT count(*) FROM pg_stat_activity;

-- Monitor CPU usage
# (Use Supabase dashboard or monitoring tools)

# Check memory usage
# (Use Supabase dashboard or monitoring tools)

# Monitor disk I/O
# (Use Supabase dashboard or monitoring tools)
```

### Verification Checklist

Use this comprehensive checklist after every deployment:

#### Database Verification
- [ ] Database connectivity verified
- [ ] Database integrity check passed
- [ ] No long-running queries detected
- [ ] All expected tables present
- [ ] Schema changes applied correctly
- [ ] Indexes created successfully
- [ ] Constraints enforced properly
- [ ] Data integrity maintained

#### Application Verification
- [ ] Application starts successfully
- [ ] No errors in application logs
- [ ] API endpoints responding normally
- [ ] Authentication working correctly
- [ ] Database queries executing successfully
- [ ] User functions operating normally

#### Performance Verification
- [ ] Query performance acceptable
- [ ] No significant performance degradation
- [ ] Resource usage within limits
- [ ] Response times normal
- [ ] No memory leaks detected

#### Business Logic Verification
- [ ] Business rules enforced
- [ ] Data validations working
- [ ] Workflows functioning correctly
- [ ] Reports generating properly
- [ ] Integrations operating normally

### Verification Timeline

Perform verification at these intervals:

- **Immediate** (0-5 minutes after deployment):
  - Database connectivity
  - Schema changes
  - Application startup

- **Short-term** (5-30 minutes after deployment):
  - Application functionality
  - Error logs
  - Basic performance

- **Medium-term** (30 minutes - 2 hours after deployment):
  - Performance metrics
  - Resource usage
  - User feedback

- **Long-term** (2-24 hours after deployment):
  - Extended performance monitoring
  - Error patterns
  - User experience

### Verification Failure Handling

If verification fails:

1. **Assess Severity**
   - Critical: Application down, data corruption
   - High: Major functionality broken
   - Medium: Minor issues, performance degradation
   - Low: Cosmetic issues, non-critical errors

2. **Immediate Actions**
   - For critical/high severity: Initiate rollback
   - For medium severity: Monitor closely, prepare rollback
   - For low severity: Document, schedule fix

3. **Communication**
   - Notify stakeholders immediately
   - Provide clear status updates
   - Set expectations for resolution

4. **Resolution**
   - Execute rollback if necessary
   - Apply fixes for non-critical issues
   - Document lessons learned

---

## Rollback Procedures

### When to Rollback

Initiate rollback in these situations:

#### Critical Situations (Immediate Rollback Required)

- **Application Down**: Application is completely non-functional
- **Data Corruption**: Data integrity compromised or lost
- **Security Breach**: Migration introduced security vulnerabilities
- **Performance Severe**: Database or application performance severely degraded
- **Critical Errors**: Errors preventing core functionality

#### High Priority Situations (Rollback Recommended)

- **Major Functionality Broken**: Important features not working
- **Data Inconsistency**: Data relationships or constraints violated
- **Significant Performance Impact**: Noticeable performance degradation
- **Integration Failures**: External integrations not working
- **User Impact**: Users unable to complete critical tasks

#### Medium Priority Situations (Consider Rollback)

- **Minor Functionality Issues**: Non-critical features broken
- **Performance Degradation**: Slower than normal but acceptable
- **Error Rate Increase**: More errors but application functional
- **Data Quality Issues**: Minor data quality problems

#### Low Priority Situations (Monitor, Don't Rollback)

- **Cosmetic Issues**: UI/UX problems
- **Non-Critical Errors**: Errors that don't affect functionality
- **Minor Performance**: Slight performance impact
- **Edge Cases**: Issues affecting rare scenarios

### Rollback Decision Process

Use this decision tree for rollback decisions:

```
Is the application functional?
├─ No → ROLLBACK IMMEDIATELY
└─ Yes → Is data integrity compromised?
    ├─ Yes → ROLLBACK IMMEDIATELY
    └─ No → Is there a security issue?
        ├─ Yes → ROLLBACK IMMEDIATELY
        └─ No → Is performance severely degraded?
            ├─ Yes → ROLLBACK IMMEDIATELY
            └─ No → Are critical features broken?
                ├─ Yes → CONSIDER ROLLBACK
                └─ No → MONITOR CLOSELY
```

### Rollback Steps

#### Step 1: Assess Situation

```bash
# Check current status
python scripts/deploy_to_production.py --status

# Review recent logs
tail -100 logs/production_deployment_*.log

# Check application status
kubectl get pods -n diocesan-vitality
```

#### Step 2: Notify Stakeholders

```
Subject: URGENT: Production Rollback Initiated

Rollback Details:
- Reason: [Reason for rollback]
- Time: [Current time]
- Impact: [Expected impact]
- Duration: [Estimated rollback time]

Actions Taken:
- Rollback initiated
- Stakeholders notified
- [Other actions]

Next Steps:
- Monitor rollback progress
- Verify rollback success
- Investigate root cause

Contact:
- Lead: [Name]
- Emergency Contact: [Name/Phone]
```

#### Step 3: Execute Rollback

```bash
# Rollback to latest backup
python scripts/deploy_to_production.py --rollback

# Or rollback to specific backup
python scripts/deploy_to_production.py --rollback --backup-file "db_backup_20260621_150000.sql.gz"
```

**Expected Output**:
```
================================================================================
ROLLING BACK DEPLOYMENT
================================================================================
Using backup file: backup/db_backup_20260621_150000.sql.gz
Decompressing backup file...
Restoring database from backup...
================================================================================
✓ ROLLBACK COMPLETED SUCCESSFULLY
================================================================================
Database restored from: backup/db_backup_20260621_150000.sql.gz
Rollback completed at: 2026-06-21 15:30:00
================================================================================
```

#### Step 4: Verify Rollback Success

```bash
# Check database connectivity
python scripts/deploy_to_production.py --status

# Verify schema is restored
psql -c "\dt"  # Should show pre-migration schema

# Check application status
kubectl logs -n diocesan-vitality deployment/backend-deployment --tail=50

# Run application tests
pytest tests/
```

#### Step 5: Document Rollback

```markdown
## Production Rollback Record

**Date**: 2026-06-21 15:30:00
**Migration**: migration.sql
**Rolled Back By**: [Your name]
**Status**: ✓ SUCCESS

### Rollback Reason
- [Detailed reason for rollback]
- [Impact assessment]
- [Severity level]

### Rollback Details
- Backup Used: db_backup_20260621_150000.sql.gz
- Start Time: 15:30:00
- End Time: 15:35:00
- Duration: 5 minutes
- Issues: None

### Post-Rollback Verification
- Database: ✓ Restored
- Application: ✓ Functional
- Data: ✓ Intact
- Performance: ✓ Normal

### Next Steps
- Investigate root cause
- Fix migration issues
- Re-test deployment
- Schedule re-deployment
```

#### Step 6: Communicate Completion

```
Subject: Production Rollback Completed

Rollback Details:
- Completed: [Date and time]
- Duration: [Rollback duration]
- Status: ✓ SUCCESS

Verification:
- Database restored successfully
- Application functioning normally
- Data integrity verified

Next Steps:
- Root cause investigation underway
- Fix development in progress
- Re-deployment scheduled for [date/time]

Contact:
- Lead: [Name]
- Emergency Contact: [Name/Phone]
```

### Rollback Verification Checklist

After rollback, verify:

- [ ] Database connectivity restored
- [ ] Schema reverted to pre-migration state
- [ ] Data integrity maintained
- [ ] Application starts successfully
- [ ] No errors in application logs
- [ ] API endpoints responding normally
- [ ] Performance back to normal
- [ ] Users can access all features
- [ ] No data loss detected
- [ ] Integrations working correctly

### Rollback Time Estimates

Typical rollback times:

- **Simple Rollback** (small database, simple migration): 3-5 minutes
- **Complex Rollback** (large database, complex migration): 5-15 minutes
- **Large Data Rollback** (significant data changes): 15-30 minutes
- **Emergency Rollback** (critical situation): 2-10 minutes

### Rollback Best Practices

1. **Always Have Recent Backups**: Ensure backups are created before every deployment
2. **Test Rollback Procedures**: Regularly test rollback in non-production environments
3. **Document Rollback Reasons**: Clearly document why rollback was initiated
4. **Communicate Early**: Notify stakeholders as soon as rollback is considered
5. **Verify Thoroughly**: Don't assume rollback succeeded without verification
6. **Investigate Root Cause**: Always investigate why rollback was necessary
7. **Fix and Retest**: Don't redeploy without fixing the underlying issue
8. **Learn from Experience**: Use rollback experiences to improve processes

### Rollback Prevention

To minimize need for rollbacks:

- **Test Thoroughly**: Comprehensive testing in development and staging
- **Review Carefully**: Peer review of all migrations
- **Use Transactions**: Ensure migrations use proper transaction handling
- **Monitor Closely**: Watch for issues during and after deployment
- **Have Rollback Plans**: Plan rollback procedures before deployment
- **Start Small**: Deploy complex changes in stages
- **Monitor Performance**: Track performance metrics before and after

---

## Approval Process

### Approval Hierarchy

The approval process ensures proper oversight and risk management for production deployments.

#### Level 1: Standard Deployments

**Criteria**:
- Low-risk migrations (add table, add index, simple data changes)
- No breaking changes
- No data loss risk
- Tested thoroughly in staging

**Required Approvals**:
- [ ] Technical Lead review
- [ ] Database Administrator review
- [ ] Peer code review

**Approval Timeframe**: 1-2 business days

#### Level 2: Moderate Risk Deployments

**Criteria**:
- Medium-risk migrations (schema changes, data transformations)
- Minor breaking changes
- Low data loss risk
- Complex testing required

**Required Approvals**:
- [ ] Technical Lead review
- [ ] Database Administrator review
- [ ] Peer code review
- [ ] Product Owner approval
- [ ] Security review (if applicable)

**Approval Timeframe**: 2-3 business days

#### Level 3: High Risk Deployments

**Criteria**:
- High-risk migrations (major schema changes, large data migrations)
- Significant breaking changes
- Moderate data loss risk
- Extensive testing required
- Customer impact possible

**Required Approvals**:
- [ ] Technical Lead review
- [ ] Database Administrator review
- [ ] Peer code review
- [ ] Product Owner approval
- [ ] Security review
- [ ] Operations Manager approval
- [ ] Executive approval (if customer-facing)

**Approval Timeframe**: 3-5 business days

#### Level 4: Critical Deployments

**Criteria**:
- Critical infrastructure changes
- High data loss risk
- Major breaking changes
- Significant customer impact
- Regulatory compliance implications

**Required Approvals**:
- [ ] All Level 3 approvals
- [ ] CTO/VP Engineering approval
- [ ] Legal/Compliance review (if applicable)
- [ ] Customer notification (if applicable)
- [ ] External audit (if required)

**Approval Timeframe**: 5-10 business days

### Approval Workflow

#### Step 1: Submit Deployment Request

Create deployment request document:

```markdown
## Production Deployment Request

**Request ID**: DEPLOY-2026-001
**Date**: 2026-06-21
**Requested By**: [Your name]
**Deployment Date**: [Proposed date]

### Migration Details
- **Migration File**: migration.sql
- **Description**: [Clear description of changes]
- **Risk Level**: [Standard/Moderate/High/Critical]
- **Estimated Downtime**: [Duration or "None"]
- **Customer Impact**: [Description]

### Technical Details
- **Schema Changes**: [List of changes]
- **Data Changes**: [Description of data changes]
- **Breaking Changes**: [List of breaking changes]
- **Dependencies**: [Any dependencies]

### Testing
- **Local Testing**: ✓ Completed
- **Staging Testing**: ✓ Completed
- **Performance Testing**: ✓ Completed
- **Rollback Testing**: ✓ Completed
- **Test Results**: [Summary of test results]

### Risk Assessment
- **Technical Risk**: [Low/Medium/High]
- **Business Risk**: [Low/Medium/High]
- **Mitigation Strategies**: [List of mitigation strategies]

### Rollback Plan
- **Rollback Available**: Yes/No
- **Rollback Time**: [Estimated duration]
- **Rollback Procedure**: [Reference to documentation]

### Approvals Required
- [ ] Technical Lead
- [ ] Database Administrator
- [ ] Peer Reviewer
- [ ] Product Owner
- [ ] Security Review
- [ ] Operations Manager
```

#### Step 2: Technical Review

**Technical Lead Review**:
- [ ] Migration technically sound
- [ ] Best practices followed
- [ ] Performance impact acceptable
- [ ] Rollback plan adequate

**Database Administrator Review**:
- [ ] SQL syntax correct
- [ ] Schema changes appropriate
- [ ] Data integrity preserved
- [ ] Indexes and constraints proper

**Peer Code Review**:
- [ ] Code quality acceptable
- [ ] Documentation complete
- [ ] Testing thorough
- [ ] No obvious issues

#### Step 3: Business Review

**Product Owner Review**:
- [ ] Business requirements met
- [ ] User impact acceptable
- [ ] Timeline appropriate
- [ ] Communication plan adequate

**Security Review** (if applicable):
- [ ] No security vulnerabilities introduced
- [ ] Access controls maintained
- [ ] Data protection adequate
- [ ] Compliance requirements met

#### Step 4: Operations Review

**Operations Manager Review**:
- [ ] Deployment window appropriate
- [ ] Resource availability confirmed
- [ ] Monitoring plan adequate
- [ ] Support team notified

#### Step 5: Executive Approval

**For Critical Deployments**:
- [ ] CTO/VP Engineering approval
- [ ] Legal/Compliance review (if applicable)
- [ ] Customer notification (if applicable)

#### Step 6: Final Approval

**Deployment Coordinator**:
- [ ] All approvals obtained
- [ ] Documentation complete
- [ ] Testing verified
- [ ] Ready to deploy

### Approval Documentation

Maintain approval records:

```markdown
## Deployment Approval Record

**Request ID**: DEPLOY-2026-001
**Migration**: migration.sql
**Status**: ✓ APPROVED

### Approval Timeline
- **Submitted**: 2026-06-21
- **Technical Review**: 2026-06-22
- **Business Review**: 2026-06-23
- **Operations Review**: 2026-06-24
- **Final Approval**: 2026-06-25

### Approvals
- **Technical Lead**: ✓ Approved - [Name], [Date]
- **Database Administrator**: ✓ Approved - [Name], [Date]
- **Peer Reviewer**: ✓ Approved - [Name], [Date]
- **Product Owner**: ✓ Approved - [Name], [Date]
- **Security Review**: N/A
- **Operations Manager**: ✓ Approved - [Name], [Date]

### Conditions
- [List any conditions or requirements]

### Deployment Window
- **Approved Date**: [Date]
- **Time Window**: [Start time] - [End time]
- **Coordinator**: [Name]
```

### Approval Communication

Communicate approval decisions:

**Approval Notification**:
```
Subject: Deployment Approved - DEPLOY-2026-001

Deployment Request: DEPLOY-2026-001
Migration: migration.sql
Status: ✓ APPROVED

Deployment Details:
- Approved Date: [Date]
- Deployment Window: [Time window]
- Coordinator: [Name]

All required approvals have been obtained.
Proceed with deployment as planned.

Contact:
- Coordinator: [Name]
- Emergency Contact: [Name/Phone]
```

**Rejection Notification**:
```
Subject: Deployment Rejected - DEPLOY-2026-001

Deployment Request: DEPLOY-2026-001
Migration: migration.sql
Status: ✗ REJECTED

Rejection Reasons:
- [Reason 1]
- [Reason 2]
- [Reason 3]

Next Steps:
- Address rejection reasons
- Resubmit deployment request
- Schedule review meeting

Contact:
- Reviewer: [Name]
- Coordinator: [Name]
```

### Expedited Approval Process

For emergency deployments:

**Criteria for Expedited Approval**:
- Critical security vulnerability
- Production outage
- Data corruption
- Legal/compliance requirement

**Expedited Process**:
1. Document emergency situation
2. Contact all approvers directly
3. Obtain verbal/approval via chat
5. Document approvals after deployment
6. Conduct post-incident review

---

## Emergency Procedures

### Emergency Situations

Identify and respond to emergency situations quickly and effectively.

#### Type 1: Critical Database Failure

**Symptoms**:
- Database completely inaccessible
- All database queries failing
- Application completely down
- Data corruption suspected

**Immediate Actions**:
1. **Declare Emergency**
   ```bash
   # Notify all stakeholders
   # Send emergency notification
   ```

2. **Assess Situation**
   ```bash
   # Check database status
   python scripts/deploy_to_production.py --status

   # Check recent logs
   tail -100 logs/production_deployment_*.log

   # Check application status
   kubectl get pods -n diocesan-vitality
   ```

3. **Initiate Rollback** (if recent deployment)
   ```bash
   # Rollback to latest backup
   python scripts/deploy_to_production.py --rollback --yes
   ```

4. **Contact Database Administrator**
   - Immediate escalation
   - Provide detailed error information
   - Follow DBA guidance

5. **Communicate Status**
   ```
   Subject: EMERGENCY: Database Failure - [Time]

   Status: CRITICAL
   Impact: Application completely down
   Actions Taken:
   - Emergency declared
   - Rollback initiated
   - DBA contacted

   Next Steps:
   - Awaiting DBA guidance
   - Preparing additional recovery options

   Contact:
   - Lead: [Name]
   - Emergency Contact: [Name/Phone]
   ```

#### Type 2: Data Corruption

**Symptoms**:
- Data integrity errors
- Inconsistent query results
- Foreign key violations
- Missing or incorrect data

**Immediate Actions**:
1. **Stop Application Writes**
   ```bash
   # Scale down application to prevent further damage
   kubectl scale deployment backend-deployment --replicas=0 -n diocesan-vitality
   ```

2. **Assess Data Damage**
   ```sql
   -- Check for corrupted tables
   SELECT tablename
   FROM pg_tables
   WHERE schemaname = 'public';

   -- Check row counts
   SELECT COUNT(*) FROM potentially_corrupted_table;

   -- Check for data inconsistencies
   SELECT * FROM table_name WHERE condition = 'suspicious_value';
   ```

3. **Restore from Backup**
   ```bash
   # Identify last known good backup
   ls -lht backup/db_backup_*.sql.gz

   # Restore from backup
   python scripts/deploy_to_production.py --rollback --backup-file "known_good_backup.sql.gz" --yes
   ```

4. **Investigate Root Cause**
   - Review recent migrations
   - Check application logs
   - Analyze database queries
   - Identify corruption source

5. **Implement Preventive Measures**
   - Add additional validation
   - Improve error handling
   - Enhance monitoring
   - Update procedures

#### Type 3: Severe Performance Degradation

**Symptoms**:
- Queries extremely slow
- Timeouts occurring frequently
- High CPU/memory usage
- Application unresponsive

**Immediate Actions**:
1. **Identify Problem Queries**
   ```sql
   -- Find slow queries
   SELECT query, mean_exec_time, calls
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;

   -- Check for long-running queries
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query
   FROM pg_stat_activity
   WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
   AND state != 'idle';
   ```

2. **Kill Problem Queries** (if necessary)
   ```sql
   -- Kill specific long-running query
   SELECT pg_cancel_backend(pid);

   -- Or terminate more aggressively
   SELECT pg_terminate_backend(pid);
   ```

3. **Rollback Recent Changes** (if performance issue started after deployment)
   ```bash
   python scripts/deploy_to_production.py --rollback --yes
   ```

4. **Scale Resources** (if resource constraint)
   ```bash
   # Scale up database resources (if possible)
   # (Use Supabase dashboard or cloud provider tools)

   # Scale up application
   kubectl scale deployment backend-deployment --replicas=3 -n diocesan-vitality
   ```

5. **Monitor and Adjust**
   - Watch performance metrics
   - Adjust resources as needed
   - Implement query optimizations
   - Consider database tuning

#### Type 4: Security Incident

**Symptoms**:
- Unauthorized access detected
- Data breach suspected
- Malicious activity observed
- Security vulnerabilities exploited

**Immediate Actions**:
1. **Contain Incident**
   ```bash
   # Block suspicious IP addresses
   # (Use firewall or security tools)

   # Revoke compromised credentials
   # (Use database administration tools)

   # Stop affected services
   kubectl scale deployment backend-deployment --replicas=0 -n diocesan-vitality
   ```

2. **Assess Damage**
   - Review access logs
   - Identify compromised data
   - Determine scope of breach
   - Document findings

3. **Notify Security Team**
   - Immediate escalation
   - Provide incident details
   - Follow security protocols

4. **Restore Secure State**
   ```bash
   # Restore from pre-incident backup
   python scripts/deploy_to_production.py --rollback --backup-file "pre_incident_backup.sql.gz" --yes

   # Rotate all credentials
   # (Use security procedures)

   # Apply security patches
   # (Use security update procedures)
   ```

5. **Communicate** (if required)
   - Notify affected users (if data breach)
   - Report to authorities (if required)
   - Follow legal/compliance requirements

### Emergency Communication

#### Emergency Notification Template

```
Subject: URGENT: Production Emergency - [Type]

Emergency Type: [Database Failure/Data Corruption/Performance/Security]
Severity: CRITICAL
Time: [Current time]

Current Status:
- [Brief status description]

Impact:
- [Description of impact]

Actions Taken:
- [List of actions taken]

Next Steps:
- [Immediate next steps]

Contact:
- Incident Commander: [Name]
- Technical Lead: [Name]
- Emergency Contact: [Name/Phone]

Updates will be provided every [X] minutes.
```

#### Status Update Template

```
Subject: Emergency Status Update - [Type]

Emergency Type: [Type]
Time: [Current time]
Duration: [Time since start]

Current Status:
- [Updated status]

Progress:
- [What has been accomplished]

Remaining Work:
- [What still needs to be done]

ETA for Resolution:
- [Estimated time]

Contact:
- Incident Commander: [Name]
```

#### Resolution Notification Template

```
Subject: Emergency Resolved - [Type]

Emergency Type: [Type]
Start Time: [Start time]
Resolution Time: [Resolution time]
Duration: [Total duration]

Summary:
- [Brief summary of what happened]

Resolution:
- [How it was resolved]

Impact Assessment:
- [Impact on users/data]

Preventive Measures:
- [What will be done to prevent recurrence]

Post-Incident Review:
- Scheduled for: [Date/time]

Contact:
- Incident Commander: [Name]
```

### Emergency Escalation

#### Escalation Matrix

| Severity | Response Time | Escalation Path |
|----------|---------------|-----------------|
| Critical | < 5 minutes | Incident Commander → CTO → Executive Team |
| High | < 15 minutes | Technical Lead → Engineering Manager → CTO |
| Medium | < 1 hour | Team Lead → Engineering Manager |
| Low | < 4 hours | Team Lead |

#### Escalation Contacts

Maintain current contact information:

```markdown
## Emergency Contacts

### Primary Contacts
- **Incident Commander**: [Name] - [Phone] - [Email]
- **Technical Lead**: [Name] - [Phone] - [Email]
- **Database Administrator**: [Name] - [Phone] - [Email]

### Management Contacts
- **Engineering Manager**: [Name] - [Phone] - [Email]
- **CTO**: [Name] - [Phone] - [Email]
- **VP Engineering**: [Name] - [Phone] - [Email]

### Executive Contacts
- **CEO**: [Name] - [Phone] - [Email]
- **COO**: [Name] - [Phone] - [Email]

### External Contacts
- **Cloud Provider Support**: [Contact information]
- **Security Team**: [Contact information]
- **Legal Counsel**: [Contact information]
```

### Emergency Recovery Procedures

#### Recovery Steps

1. **Stabilize Environment**
   - Stop ongoing damage
   - Preserve evidence
   - Isolate affected systems

2. **Restore Services**
   - Restore from backups
   - Restart services
   - Verify functionality

3. **Verify Data Integrity**
   - Check data consistency
   - Validate relationships
   - Confirm no data loss

4. **Monitor Stability**
   - Watch for recurring issues
   - Monitor performance
   - Check error rates

5. **Document Everything**
   - Timeline of events
   - Actions taken
   - Lessons learned

#### Post-Emergency Review

Conduct post-incident review:

```markdown
## Post-Emergency Review

**Emergency Type**: [Type]
**Date**: [Date]
**Duration**: [Duration]

### What Happened?
- [Detailed description of emergency]

### Root Cause Analysis
- [Root cause identification]
- [Contributing factors]

### Timeline
- [Time] - [Event]
- [Time] - [Event]
- [Time] - [Event]

### What Went Well?
- [What worked correctly]
- [What should be repeated]

### What Could Be Improved?
- [What didn't work well]
- [What should be changed]

### Action Items
- [ ] [Action item] - [Owner] - [Due date]
- [ ] [Action item] - [Owner] - [Due date]

### Preventive Measures
- [New procedures to implement]
- [Monitoring to add]
- [Training to conduct]

### Documentation Updates
- [Documentation that needs updating]
```

---

## Safety Measures and Best Practices

### Comprehensive Safety Framework

Implement these safety measures to ensure reliable production deployments.

### Pre-Deployment Safety Measures

#### 1. Environment Isolation

**Practice**: Maintain separate environments for each stage.

**Implementation**:
```bash
# Development environment
supabase start  # Local development

# Staging environment
# Separate Supabase project for staging

# Production environment
# Dedicated production Supabase project
```

**Benefits**:
- Prevents accidental production changes
- Enables safe testing
- Provides rollback capability

#### 2. Comprehensive Testing

**Practice**: Test thoroughly at multiple levels.

**Testing Levels**:
- **Unit Tests**: Test individual components
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Test under load
- **Security Tests**: Test for vulnerabilities

**Implementation**:
```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Performance testing
pytest tests/performance/

# Security testing
pytest tests/security/
```

#### 3. Code Review Process

**Practice**: All migrations must be reviewed by peers.

**Review Checklist**:
- [ ] SQL syntax correct
- [ ] Best practices followed
- [ ] Performance considered
- [ ] Security implications assessed
- [ ] Rollback plan adequate
- [ ] Documentation complete

#### 4. Backup Verification

**Practice**: Regularly verify backup integrity.

**Implementation**:
```bash
# List recent backups
ls -lht backup/db_backup_*.sql.gz

# Verify backup can be restored
gunzip -t backup/db_backup_20260621_150000.sql.gz

# Test restore procedure (in non-production)
python scripts/deploy_to_production.py --rollback --dry-run
```

### During Deployment Safety Measures

#### 1. Transaction Safety

**Practice**: Use explicit transactions for all migrations.

**Implementation**:
```sql
-- Good: Explicit transaction
BEGIN;

-- Migration statements
CREATE TABLE new_table (...);
ALTER TABLE existing_table ADD COLUMN new_column VARCHAR(255);

-- Verify changes
-- (Add verification queries if needed)

COMMIT;

-- Bad: No transaction
CREATE TABLE new_table (...);
ALTER TABLE existing_table ADD COLUMN new_column VARCHAR(255);
```

#### 2. Incremental Changes

**Practice**: Break large migrations into smaller, manageable steps.

**Implementation**:
```sql
-- Instead of one large migration, use multiple small migrations:

-- Migration 1: Add new table
CREATE TABLE new_table (...);

-- Migration 2: Populate new table
INSERT INTO new_table SELECT ... FROM old_table;

-- Migration 3: Update references
UPDATE related_table SET new_table_id = ...;

-- Migration 4: Remove old table
DROP TABLE old_table;
```

#### 3. Backward Compatibility

**Practice**: Maintain backward compatibility during transitions.

**Implementation**:
```sql
-- Add new column (nullable)
ALTER TABLE users ADD COLUMN new_preference VARCHAR(255);

-- Deploy application code that uses new column
-- (Keep old code working)

-- Populate new column
UPDATE users SET new_preference = ...;

-- Make column non-nullable after data populated
ALTER TABLE users ALTER COLUMN new_preference SET NOT NULL;

-- Remove old column after transition complete
ALTER TABLE users DROP COLUMN old_preference;
```

#### 4. Monitoring During Deployment

**Practice**: Monitor deployment progress and system health.

**Implementation**:
```bash
# Monitor deployment logs
tail -f logs/production_deployment_*.log

# Monitor database performance
# (Use Supabase dashboard or monitoring tools)

# Monitor application logs
kubectl logs -f -n diocesan-vitality deployment/backend-deployment

# Monitor error rates
# (Use application monitoring tools)
```

### Post-Deployment Safety Measures

#### 1. Comprehensive Verification

**Practice**: Verify all aspects of the deployment.

**Verification Areas**:
- Database schema changes
- Data integrity
- Application functionality
- Performance metrics
- Error rates
- User experience

#### 2. Gradual Rollout

**Practice**: Roll out changes gradually when possible.

**Implementation**:
```bash
# For application changes, use feature flags
# Enable for small percentage of users first
# Monitor for issues
# Gradually increase percentage

# For database changes, use read replicas
# Apply changes to replica first
# Monitor replica performance
# Promote to primary when safe
```

#### 3. Extended Monitoring

**Practice**: Monitor for extended period after deployment.

**Monitoring Timeline**:
- **Immediate** (0-1 hour): Monitor for critical issues
- **Short-term** (1-24 hours): Monitor for performance issues
- **Medium-term** (1-7 days): Monitor for data quality issues
- **Long-term** (1-4 weeks): Monitor for long-term trends

#### 4. Documentation Updates

**Practice**: Update all documentation after deployment.

**Documentation to Update**:
- Database schema documentation
- API documentation
- Deployment procedures
- Troubleshooting guides
- Runbooks

### General Best Practices

#### 1. Naming Conventions

**Practice**: Use clear, consistent naming conventions.

**Migration Naming**:
```
YYYYMMDDHHMMSS_descriptive_name.sql

Examples:
20260621150000_add_user_preferences_table.sql
20260621151000_add_index_on_users_email.sql
20260621152000_update_user_constraints.sql
```

**Table Naming**:
- Use lowercase with underscores
- Be descriptive but concise
- Use singular form
- Prefix with module if applicable

```sql
-- Good
CREATE TABLE user_preferences (...);
CREATE TABLE order_items (...);

-- Bad
CREATE TABLE UserPreferences (...);
CREATE TABLE orderitems (...);
```

#### 2. Commenting

**Practice**: Add clear comments to migrations.

**Implementation**:
```sql
-- Migration: 20260621150000_add_user_preferences.sql
-- Description: Add user preferences table with JSONB storage
-- Author: John Doe
-- Date: 2026-06-21

BEGIN;

-- Create user preferences table
-- Stores user-specific settings and preferences
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add index for fast user lookups
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

-- Add index for JSONB queries
CREATE INDEX idx_user_preferences_preferences ON user_preferences USING GIN(preferences);

-- Add comments for documentation
COMMENT ON TABLE user_preferences IS 'User preference settings with JSONB storage';
COMMENT ON COLUMN user_preferences.preferences IS 'JSONB object storing user preferences';

COMMIT;
```

#### 3. Version Control

**Practice**: Keep all migrations under version control.

**Implementation**:
```bash
# All migrations in version control
git add supabase/migrations/
git commit -m "Add user preferences migration"

# Never modify committed migrations
# Always create new migrations for changes

# Use git branches for development
git checkout -b feature/add-preferences
# Create migration
git commit -m "Add user preferences migration"
git push origin feature/add-preferences
# Create pull request for review
```

#### 4. Change Management

**Practice**: Follow formal change management process.

**Process**:
1. Submit change request
2. Obtain required approvals
3. Schedule deployment window
4. Deploy with safety measures
5. Verify deployment success
6. Document deployment
7. Conduct post-deployment review

#### 5. Continuous Improvement

**Practice**: Learn from each deployment and improve processes.

**Improvement Areas**:
- Deployment speed
- Safety measures
- Testing procedures
- Monitoring capabilities
- Documentation quality
- Team communication

### Security Best Practices

#### 1. Credential Management

**Practice**: Never commit credentials to version control.

**Implementation**:
```bash
# Use .env file for credentials
# .env is in .gitignore

# Use environment variables in production
# Never hardcode credentials in scripts

# Rotate credentials regularly
# Use strong, unique passwords
```

#### 2. Principle of Least Privilege

**Practice**: Use minimum required permissions.

**Implementation**:
```sql
-- Create specific roles for specific tasks
CREATE ROLE migration_user WITH LOGIN PASSWORD 'secure_password';

-- Grant only necessary permissions
GRANT USAGE ON SCHEMA public TO migration_user;
GRANT CREATE ON SCHEMA public TO migration_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO migration_user;

-- Don't grant superuser privileges
```

#### 3. Audit Logging

**Practice**: Maintain audit trail of all changes.

**Implementation**:
```sql
-- Enable audit logging
-- (Use Supabase audit logging features)

-- Log all schema changes
-- (Deployment script logs all operations)

-- Review logs regularly
tail -f logs/production_deployment_*.log
```

#### 4. Data Protection

**Practice**: Protect sensitive data during migrations.

**Implementation**:
```sql
-- Avoid exposing sensitive data in logs
-- Use parameterized queries

-- Encrypt sensitive data at rest
-- (Use database encryption features)

-- Mask sensitive data in queries
SELECT id, email, -- Don't SELECT password_hash
FROM users;
```

---

## Common Scenarios and Examples

### Scenario 1: Adding a New Table

**Situation**: Add a new table to store user preferences.

**Migration File**:
```sql
-- Migration: 20260621150000_add_user_preferences.sql
-- Description: Add user preferences table

BEGIN;

-- Create table
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_preferences ON user_preferences USING GIN(preferences);

-- Add comments
COMMENT ON TABLE user_preferences IS 'User preference settings';

COMMIT;
```

**Deployment Steps**:
```bash
# 1. Validate migration
python scripts/deploy_to_production.py --validate --migration-file "20260621150000_add_user_preferences.sql"

# 2. Deploy
python scripts/deploy_to_production.py --auto --migration-file "20260621150000_add_user_preferences.sql"

# 3. Type "DEPLOY" when prompted

# 4. Verify deployment
psql -c "\d+ user_preferences"
```

**Verification**:
```sql
-- Check table exists
SELECT * FROM user_preferences LIMIT 0;

-- Verify indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'user_preferences';

-- Test foreign key
INSERT INTO user_preferences (user_id, preferences)
VALUES (test_user_id, '{"theme": "dark"}'::jsonb);
```

### Scenario 2: Adding a Column to Existing Table

**Situation**: Add a new column to the users table.

**Migration File**:
```sql
-- Migration: 20260621151000_add_last_login_column.sql
-- Description: Add last_login timestamp to users table

BEGIN;

-- Add nullable column first
ALTER TABLE users ADD COLUMN last_login TIMESTAMPTZ;

-- Add comment
COMMENT ON COLUMN users.last_login IS 'Timestamp of last user login';

COMMIT;
```

**Deployment Steps**:
```bash
# Deploy migration
python scripts/deploy_to_production.py --auto --migration-file "20260621151000_add_last_login_column.sql"
```

**Verification**:
```sql
-- Check column exists
\d+ users

-- Update column for existing users
UPDATE users SET last_login = NOW() WHERE last_login IS NULL;

-- Optionally make column non-nullable after data populated
-- ALTER TABLE users ALTER COLUMN last_login SET NOT NULL;
```

### Scenario 3: Creating an Index

**Situation**: Add an index to improve query performance.

**Migration File**:
```sql
-- Migration: 20260621152000_add_email_index.sql
-- Description: Add index on users.email for faster lookups

BEGIN;

-- Create index
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- Add comment
COMMENT ON INDEX idx_users_email IS 'Index for fast email lookups';

COMMIT;
```

**Deployment Steps**:
```bash
# Deploy migration
python scripts/deploy_to_production.py --auto --migration-file "20260621152000_add_email_index.sql"
```

**Verification**:
```sql
-- Check index exists
SELECT indexname FROM pg_indexes WHERE tablename = 'users' AND indexname = 'idx_users_email';

-- Test query performance
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
```

### Scenario 4: Data Migration

**Situation**: Migrate data from old structure to new structure.

**Migration File**:
```sql
-- Migration: 20260621153000_migrate_user_data.sql
-- Description: Migrate user data from old format to new format

BEGIN;

-- Add new column (nullable)
ALTER TABLE users ADD COLUMN preferences JSONB;

-- Migrate existing data
UPDATE users
SET preferences = jsonb_build_object(
    'theme', COALESCE(theme_setting, 'light'),
    'notifications', COALESCE(notification_setting::text, 'true')::boolean
)
WHERE preferences IS NULL;

-- Verify migration
-- (Add verification queries if needed)

COMMIT;
```

**Deployment Steps**:
```bash
# Deploy migration
python scripts/deploy_to_production.py --auto --migration-file "20260621153000_migrate_user_data.sql"
```

**Verification**:
```sql
-- Check data migration
SELECT COUNT(*) FROM users WHERE preferences IS NULL;
-- Should return 0

-- Sample migrated data
SELECT id, email, preferences FROM users LIMIT 5;

-- Verify data integrity
SELECT COUNT(*) FROM users WHERE preferences->>'theme' IN ('light', 'dark');
```

### Scenario 5: Schema Refactoring

**Situation**: Split a large table into multiple related tables.

**Migration File**:
```sql
-- Migration: 20260621154000_split_user_table.sql
-- Description: Split user table into users and user_profiles

BEGIN;

-- Create new user_profiles table
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bio TEXT,
    avatar_url VARCHAR(255),
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);

-- Migrate data
INSERT INTO user_profiles (user_id, bio, avatar_url, preferences)
SELECT id, bio, avatar_url, preferences
FROM users;

-- Remove columns from users table
ALTER TABLE users DROP COLUMN bio;
ALTER TABLE users DROP COLUMN avatar_url;
ALTER TABLE users DROP COLUMN preferences;

COMMIT;
```

**Deployment Steps**:
```bash
# Deploy migration
python scripts/deploy_to_production.py --auto --migration-file "20260621154000_split_user_table.sql"
```

**Verification**:
```sql
-- Check new table exists
\d+ user_profiles

-- Verify data migration
SELECT COUNT(*) FROM user_profiles;
-- Should match original user count

-- Verify relationships
SELECT u.id, up.bio
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id
LIMIT 5;

-- Check old columns removed
\d+ users
```

### Scenario 6: Adding Constraints

**Situation**: Add data validation constraints.

**Migration File**:
```sql
-- Migration: 20260621155000_add_constraints.sql
-- Description: Add validation constraints to users table

BEGIN;

-- Add check constraint
ALTER TABLE users ADD CONSTRAINT check_email_format
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- Add unique constraint
ALTER TABLE users ADD CONSTRAINT unique_email
UNIQUE (email);

-- Add foreign key constraint
ALTER TABLE orders ADD CONSTRAINT fk_orders_user_id
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

COMMIT;
```

**Deployment Steps**:
```bash
# Deploy migration
python scripts/deploy_to_production.py --auto --migration-file "20260621155000_add_constraints.sql"
```

**Verification**:
```sql
-- Test constraints
INSERT INTO users (email, password_hash) VALUES ('invalid-email', 'hash');
-- Should fail with check constraint error

INSERT INTO users (email, password_hash)
VALUES ('test@example.com', 'hash1');
INSERT INTO users (email, password_hash)
VALUES ('test@example.com', 'hash2');
-- Second insert should fail with unique constraint error
```

### Scenario 7: Performance Optimization

**Situation**: Optimize slow queries with indexes and query changes.

**Analysis**:
```sql
-- Identify slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Analyze query plan
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 'user-uuid' AND status = 'completed';
```

**Migration File**:
```sql
-- Migration: 20260621156000_optimize_queries.sql
-- Description: Add indexes for query optimization

BEGIN;

-- Add composite index
CREATE INDEX CONCURRENTLY idx_orders_user_status
ON orders(user_id, status)
WHERE status IN ('pending', 'completed');

-- Add partial index
CREATE INDEX CONCURRENTLY idx_orders_active
ON orders(created_at)
WHERE status = 'active';

-- Add covering index
CREATE INDEX CONCURRENTLY idx_orders_user_created_status
ON orders(user_id, created_at, status);

COMMIT;
```

**Deployment Steps**:
```bash
# Deploy migration
python scripts/deploy_to_production.py --auto --migration-file "20260621156000_optimize_queries.sql"
```

**Verification**:
```sql
-- Check indexes created
SELECT indexname FROM pg_indexes WHERE tablename = 'orders';

-- Test query performance
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 'user-uuid' AND status = 'completed';

-- Compare with baseline performance
```

### Scenario 8: Handling Rollback

**Situation**: Deployment caused issues and needs rollback.

**Rollback Steps**:
```bash
# 1. Assess situation
python scripts/deploy_to_production.py --status

# 2. Notify stakeholders
# Send emergency notification

# 3. Execute rollback
python scripts/deploy_to_production.py --rollback --yes

# 4. Verify rollback
psql -c "\dt"  # Check schema is restored
kubectl logs -n diocesan-vitality deployment/backend-deployment --tail=50

# 5. Test application
pytest tests/

# 6. Document rollback
# Create rollback record
```

**Rollback Verification**:
```sql
-- Verify schema is restored to previous state
\d+ table_name

-- Verify data integrity
SELECT COUNT(*) FROM important_table;

-- Test application functionality
# Run application tests
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: "Supabase CLI not found"

**Symptoms**:
```
RuntimeError: Supabase CLI not found or not working.
Please install it from https://supabase.com/docs/guides/cli
```

**Causes**:
- Supabase CLI not installed
- Supabase CLI not in PATH
- Incorrect installation

**Solutions**:

1. **Install Supabase CLI**
   ```bash
   # Linux/macOS
   curl -fsSL https://supabase.com/install.sh | bash

   # Verify installation
   supabase --version
   ```

2. **Add to PATH** (if needed)
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export PATH="$PATH:$HOME/.supabase/bin"

   # Reload shell
   source ~/.bashrc
   ```

3. **Verify Installation**
   ```bash
   supabase --version
   # Should show version number
   ```

#### Issue 2: "Docker not found"

**Symptoms**:
```
RuntimeError: Docker not found or not working.
Please install it from https://docs.docker.com/get-docker/
```

**Causes**:
- Docker not installed
- Docker daemon not running
- Insufficient permissions

**Solutions**:

1. **Install Docker**
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # macOS
   brew install --cask docker
   ```

2. **Start Docker Daemon**
   ```bash
   # Linux
   sudo systemctl start docker
   sudo systemctl enable docker

   # macOS
   # Start Docker Desktop application
   ```

3. **Verify Docker**
   ```bash
   docker --version
   docker ps
   ```

4. **Fix Permissions** (if needed)
   ```bash
   # Add user to docker group
   sudo usermod -aG docker $USER

   # Log out and log back in
   ```

#### Issue 3: "Cannot connect to production database"

**Symptoms**:
```
RuntimeError: Cannot connect to production database: connection refused
```

**Causes**:
- Incorrect credentials
- Network connectivity issues
- Database not accessible
- Firewall blocking connection

**Solutions**:

1. **Verify Credentials**
   ```bash
   # Check .env file
   cat .env | grep SUPABASE

   # Verify URL format
   # Should be: https://project-id.supabase.co
   ```

2. **Test Network Connectivity**
   ```bash
   # Test DNS resolution
   nslookup your-project.supabase.co

   # Test connection
   telnet aws-0-us-east-2.pooler.supabase.com 5432
   ```

3. **Check Firewall**
   ```bash
   # Ensure port 5432 is open
   sudo ufw status
   sudo ufw allow 5432
   ```

4. **Verify Database Status**
   - Check Supabase dashboard
   - Verify database is active
   - Check for maintenance windows

#### Issue 4: "Migration syntax validation failed"

**Symptoms**:
```
✗ Migration syntax validation failed:
  - Syntax error: unterminated dollar quote
```

**Causes**:
- SQL syntax errors
- Missing semicolons
- Incorrect quotes
- Invalid SQL statements

**Solutions**:

1. **Review Migration File**
   ```bash
   # Check migration file
   cat supabase/migrations/migration.sql

   # Look for common issues:
   # - Missing semicolons
   # - Unclosed quotes
   # - Invalid SQL syntax
   ```

2. **Test SQL Manually**
   ```bash
   # Connect to database
   psql -h host -U user -d database

   # Test SQL statements
   \i supabase/migrations/migration.sql
   ```

3. **Use SQL Validator**
   ```bash
   # Use PostgreSQL syntax checker
   psql -c "EXPLAIN (FORMAT TEXT) $(cat migration.sql)"
   ```

4. **Fix Common Issues**
   ```sql
   -- Missing semicolon
   CREATE TABLE test (id INT)  -- Wrong
   CREATE TABLE test (id INT); -- Correct

   -- Unclosed quote
   SELECT * FROM users WHERE name = 'John  -- Wrong
   SELECT * FROM users WHERE name = 'John'; -- Correct

   -- Invalid syntax
   CREATE TABEL test (id INT);  -- Wrong (TABEL instead of TABLE)
   CREATE TABLE test (id INT);  -- Correct
   ```

#### Issue 5: "Insufficient disk space"

**Symptoms**:
```
✗ Pre-deployment checks failed:
  - Insufficient disk space: 0.50GB free (minimum 1GB required)
```

**Causes**:
- Disk full
- Too many old backups
- Large log files

**Solutions**:

1. **Check Disk Space**
   ```bash
   df -h
   du -sh backup/
   du -sh logs/
   ```

2. **Clean Old Backups**
   ```bash
   # Remove old backups (keep recent ones)
   find backup/ -name "db_backup_*.sql.gz" -mtime +30 -delete

   # Or move to archive storage
   mv backup/old_backup.sql.gz /archive/
   ```

3. **Clean Log Files**
   ```bash
   # Compress old logs
   find logs/ -name "*.log" -mtime +7 -exec gzip {} \;

   # Remove very old logs
   find logs/ -name "*.log.gz" -mtime +90 -delete
   ```

4. **Free System Space**
   ```bash
   # Clean package cache
   sudo apt clean
   sudo apt autoremove

   # Clean Docker
   docker system prune -a
   ```

#### Issue 6: "Deployment timeout"

**Symptoms**:
```
Command timed out after 300 seconds
```

**Causes**:
- Large database
- Complex migration
- Network issues
- Database locks

**Solutions**:

1. **Increase Timeout**
   ```python
   # In deploy_to_production.py, increase timeout values
   timeout=600  # Increase from 300 to 600 seconds
   ```

2. **Check for Locks**
   ```sql
   -- Check for database locks
   SELECT pid, usename, query, state
   FROM pg_stat_activity
   WHERE state != 'idle';

   -- Kill blocking locks if necessary
   SELECT pg_terminate_backend(pid);
   ```

3. **Optimize Migration**
   ```sql
   -- Break large migration into smaller ones
   -- Use indexes to speed up operations
   -- Avoid full table scans
   ```

4. **Monitor Progress**
   ```bash
   # Monitor deployment progress
   tail -f logs/production_deployment_*.log

   # Check database activity
   # (Use Supabase dashboard)
   ```

#### Issue 7: "Post-deployment verification failed"

**Symptoms**:
```
✗ POST-DEPLOYMENT VERIFICATION FAILED
  - Database integrity check failed
```

**Causes**:
- Migration partially applied
- Data corruption
- Constraint violations
- Missing objects

**Solutions**:

1. **Check Verification Logs**
   ```bash
   # Review verification errors
   tail -100 logs/production_deployment_*.log

   # Identify specific failure
   ```

2. **Manual Verification**
   ```sql
   -- Check database integrity
   SELECT tablename
   FROM pg_tables
   WHERE schemaname = 'public';

   -- Check for corrupted tables
   SELECT * FROM potentially_corrupted_table LIMIT 10;

   -- Verify constraints
   SELECT constraint_name, constraint_type
   FROM information_schema.table_constraints
   WHERE table_name = 'table_name';
   ```

3. **Assess Rollback Need**
   ```bash
   # If critical issues, rollback immediately
   python scripts/deploy_to_production.py --rollback --yes
   ```

4. **Fix Issues Manually**
   ```sql
   -- Fix missing objects
   CREATE TABLE missing_table (...);

   -- Fix constraint violations
   UPDATE table_name SET column = value WHERE condition;

   -- Fix data issues
   DELETE FROM table_name WHERE invalid_condition;
   ```

#### Issue 8: "Application errors after deployment"

**Symptoms**:
- Application showing errors
- API endpoints failing
- Database connection errors

**Causes**:
- Schema changes broke application
- Missing database objects
- Data type mismatches
- Permission issues

**Solutions**:

1. **Check Application Logs**
   ```bash
   # Review application logs
   kubectl logs -n diocesan-vitality deployment/backend-deployment --tail=100

   # Look for specific errors
   kubectl logs -n diocesan-vitality deployment/backend-deployment --tail=100 | grep -i error
   ```

2. **Test Database Queries**
   ```bash
   # Test queries that application uses
   psql -c "SELECT * FROM table_name WHERE condition = 'value'"

   # Check for missing tables/columns
   \d+ table_name
   ```

3. **Verify Application Code**
   ```bash
   # Check if application code needs updating
   # Review recent commits
   git log --oneline -10

   # Check for schema mismatches
   ```

4. **Rollback if Necessary**
   ```bash
   # If application is completely broken, rollback
   python scripts/deploy_to_production.py --rollback --yes

   # Fix application code
   # Redeploy after fixes
   ```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
# Enable debug logging
python scripts/deploy_to_production.py --auto --migration-file "migration.sql" --dry-run

# Check debug logs
cat logs/production_deployment_*.log | grep DEBUG
```

### Getting Help

If you can't resolve an issue:

1. **Check Documentation**
   - Review this guide
   - Check Supabase documentation
   - Review deployment logs

2. **Contact Team**
   - Notify technical lead
   - Contact database administrator
   - Escalate if necessary

3. **Create Issue**
   - Document the problem
   - Include error messages
   - Provide steps to reproduce
   - Share relevant logs

---

## Integration with CI/CD

### Automated Deployment Pipeline

Integrate production migrations into your CI/CD pipeline for automated, reliable deployments.

### GitHub Actions Integration

#### Basic Deployment Workflow

Create `.github/workflows/production-migration.yml`:

```yaml
name: Production Database Migration

on:
  push:
    branches:
      - main
    paths:
      - 'supabase/migrations/**'
  workflow_dispatch:
    inputs:
      migration_file:
        description: 'Migration file to deploy'
        required: true
        type: string

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: |
          pip install python-dotenv

      - name: Install Supabase CLI
        run: |
          wget https://github.com/supabase/supabase/releases/latest/download/supabase_linux_amd64.tar.gz
          tar -xzf supabase_linux_amd64.tar.gz
          sudo mv supabase /usr/local/bin/

      - name: Setup Docker
        uses: docker/setup-buildx-action@v2

      - name: Configure environment
        run: |
          echo "SUPABASE_URL_PRD=${{ secrets.SUPABASE_URL_PRD }}" >> .env
          echo "SUPABASE_DB_PASSWORD_PRD=${{ secrets.SUPABASE_DB_PASSWORD_PRD }}" >> .env

      - name: Validate migration
        run: |
          python scripts/deploy_to_production.py --validate --migration-file "${{ inputs.migration_file || 'supabase/migrations/*.sql' }}"

      - name: Create backup
        run: |
          python scripts/deploy_to_production.py --backup-only

      - name: Deploy to production
        run: |
          python scripts/deploy_to_production.py --auto --migration-file "${{ inputs.migration_file || 'supabase/migrations/*.sql' }}" --yes

      - name: Verify deployment
        run: |
          python scripts/deploy_to_production.py --status

      - name: Notify on failure
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Production Migration Failed',
              body: 'Migration deployment failed. Check logs for details.',
              labels: ['bug', 'critical']
            })
```

#### Advanced Workflow with Staging

```yaml
name: Production Database Migration with Staging

on:
  push:
    branches:
      - main
    paths:
      - 'supabase/migrations/**'

jobs:
  test-staging:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Python and dependencies
        run: |
          python -m pip install --upgrade pip
          pip install python-dotenv

      - name: Install Supabase CLI
        run: |
          wget https://github.com/supabase/supabase/releases/latest/download/supabase_linux_amd64.tar.gz
          tar -xzf supabase_linux_amd64.tar.gz
          sudo mv supabase /usr/local/bin/

      - name: Configure staging environment
        run: |
          echo "SUPABASE_URL_STG=${{ secrets.SUPABASE_URL_STG }}" >> .env
          echo "SUPABASE_DB_PASSWORD_STG=${{ secrets.SUPABASE_DB_PASSWORD_STG }}" >> .env

      - name: Deploy to staging
        run: |
          python scripts/deploy_to_production.py --auto --migration-file "supabase/migrations/*.sql" --yes

      - name: Run tests
        run: |
          # Add your test commands here
          pytest tests/

  deploy-production:
    needs: test-staging
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Python and dependencies
        run: |
          python -m pip install --upgrade pip
          pip install python-dotenv

      - name: Install Supabase CLI
        run: |
          wget https://github.com/supabase/supabase/releases/latest/download/supabase_linux_amd64.tar.gz
          tar -xzf supabase_linux_amd64.tar.gz
          sudo mv supabase /usr/local/bin/

      - name: Setup Docker
        uses: docker/setup-buildx-action@v2

      - name: Configure production environment
        run: |
          echo "SUPABASE_URL_PRD=${{ secrets.SUPABASE_URL_PRD }}" >> .env
          echo "SUPABASE_DB_PASSWORD_PRD=${{ secrets.SUPABASE_DB_PASSWORD_PRD }}" >> .env

      - name: Request approval
        uses: trstringer/manual-approval@v1
        with:
          secret: ${{ secrets.GITHUB_TOKEN }}
          approvers: tech-lead,db-admin
          minimum-approvals: 2

      - name: Deploy to production
        run: |
          python scripts/deploy_to_production.py --auto --migration-file "supabase/migrations/*.sql" --yes

      - name: Verify deployment
        run: |
          python scripts/deploy_to_production.py --status

      - name: Notify success
        if: success()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.repos.createCommitComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              commit_sha: context.sha,
              body: '✅ Production migration deployed successfully'
            })
```

### Required GitHub Secrets

Configure these secrets in your GitHub repository:

```
SUPABASE_URL_PRD=your_production_supabase_url
SUPABASE_DB_PASSWORD_PRD=your_production_db_password
SUPABASE_URL_STG=your_staging_supabase_url
SUPABASE_DB_PASSWORD_STG=your_staging_db_password
```

### GitLab CI Integration

Create `.gitlab-ci.yml`:

```yaml
stages:
  - validate
  - backup
  - deploy
  - verify

variables:
  MIGRATION_FILE: "supabase/migrations/*.sql"

validate:
  stage: validate
  script:
    - pip install python-dotenv
    - wget https://github.com/supabase/supabase/releases/latest/download/supabase_linux_amd64.tar.gz
    - tar -xzf supabase_linux_amd64.tar.gz
    - sudo mv supabase /usr/local/bin/
    - echo "SUPABASE_URL_PRD=$SUPABASE_URL_PRD" >> .env
    - echo "SUPABASE_DB_PASSWORD_PRD=$SUPABASE_DB_PASSWORD_PRD" >> .env
    - python scripts/deploy_to_production.py --validate --migration-file "$MIGRATION_FILE"

backup:
  stage: backup
  script:
    - pip install python-dotenv
    - wget https://github.com/supabase/supabase/releases/latest/download/supabase_linux_amd64.tar.gz
    - tar -xzf supabase_linux_amd64.tar.gz
    - sudo mv supabase /usr/local/bin/
    - echo "SUPABASE_URL_PRD=$SUPABASE_URL_PRD" >> .env
    - echo "SUPABASE_DB_PASSWORD_PRD=$SUPABASE_DB_PASSWORD_PRD" >> .env
    - python scripts/deploy_to_production.py --backup-only

deploy:
  stage: deploy
  when: manual
  script:
    - pip install python-dotenv
    - wget https://github.com/supabase/supabase/releases/latest/download/supabase_linux_amd64.tar.gz
    - tar -xzf supabase_linux_amd64.tar.gz
    - sudo mv supabase /usr/local/bin/
    - echo "SUPABASE_URL_PRD=$SUPABASE_URL_PRD" >> .env
    - echo "SUPABASE_DB_PASSWORD_PRD=$SUPABASE_DB_PASSWORD_PRD" >> .env
    - python scripts/deploy_to_production.py --auto --migration-file "$MIGRATION_FILE" --yes

verify:
  stage: verify
  script:
    - pip install python-dotenv
    - wget https://github.com/supabase/supabase/releases/latest/download/supabase_linux_amd64.tar.gz
    - tar -xzf supabase_linux_amd64.tar.gz
    - sudo mv supabase /usr/local/bin/
    - echo "SUPABASE_URL_PRD=$SUPABASE_URL_PRD" >> .env
    - echo "SUPABASE_DB_PASSWORD_PRD=$SUPABASE_DB_PASSWORD_PRD" >> .env
    - python scripts/deploy_to_production.py --status
```

### Jenkins Pipeline Integration

Create `Jenkinsfile`:

```groovy
pipeline {
    agent any

    environment {
        SUPABASE_URL_PRD = credentials('supabase-url-prd')
        SUPABASE_DB_PASSWORD_PRD = credentials('supabase-db-password-prd')
        MIGRATION_FILE = "supabase/migrations/*.sql"
    }

    stages {
        stage('Validate') {
            steps {
                sh '''
                    pip install python-dotenv
                    wget https://github.com/supabase/supabase/releases/latest/download/supabase_linux_amd64.tar.gz
                    tar -xzf supabase_linux_amd64.tar.gz
                    sudo mv supabase /usr/local/bin/
                    echo "SUPABASE_URL_PRD=$SUPABASE_URL_PRD" >> .env
                    echo "SUPABASE_DB_PASSWORD_PRD=$SUPABASE_DB_PASSWORD_PRD" >> .env
                    python scripts/deploy_to_production.py --validate --migration-file "$MIGRATION_FILE"
                '''
            }
        }

        stage('Backup') {
            steps {
                sh '''
                    python scripts/deploy_to_production.py --backup-only
                '''
            }
        }

        stage('Deploy') {
            input {
                message 'Deploy to production?'
                ok 'Yes, deploy'
            }
            steps {
                sh '''
                    python scripts/deploy_to_production.py --auto --migration-file "$MIGRATION_FILE" --yes
                '''
            }
        }

        stage('Verify') {
            steps {
                sh '''
                    python scripts/deploy_to_production.py --status
                '''
            }
        }
    }

    post {
        success {
            echo 'Deployment successful!'
        }
        failure {
            echo 'Deployment failed!'
            emailext (
                subject: "Production Migration Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Migration deployment failed. Check Jenkins logs for details.",
                to: "${env.NOTIFICATION_EMAIL}"
            )
        }
    }
}
```

### CI/CD Best Practices

1. **Automated Testing**: Always run tests before deployment
2. **Manual Approval**: Require manual approval for production deployments
3. **Rollback Automation**: Automate rollback on failure
4. **Notification**: Send notifications on deployment status
5. **Logging**: Maintain detailed logs of all deployments
6. **Security**: Use secrets management for credentials
7. **Idempotency**: Ensure deployments can be safely retried

---

## Team Responsibilities and Escalation

### Role Definitions

#### Deployment Coordinator

**Responsibilities**:
- Coordinate deployment activities
- Ensure all pre-deployment checks completed
- Manage deployment timeline
- Communicate with stakeholders
- Document deployment results

**Required Skills**:
- Strong communication skills
- Understanding of deployment processes
- Attention to detail
- Problem-solving abilities

#### Technical Lead

**Responsibilities**:
- Review technical aspects of migrations
- Approve technical readiness
- Provide technical guidance
- Handle technical issues during deployment
- Conduct post-deployment reviews

**Required Skills**:
- Deep technical knowledge
- Database expertise
- Problem-solving skills
- Leadership abilities

#### Database Administrator

**Responsibilities**:
- Review database migrations
- Ensure database best practices
- Monitor database performance
- Handle database-related issues
- Maintain database integrity

**Required Skills**:
- Database administration expertise
- Performance tuning
- Backup and recovery
- Security knowledge

#### Application Developer

**Responsibilities**:
- Develop and test migrations
- Ensure application compatibility
- Conduct code reviews
- Fix deployment issues
- Update application code as needed

**Required Skills**:
- SQL expertise
- Application development
- Testing skills
- Debugging abilities

#### Quality Assurance Engineer

**Responsibilities**:
- Develop test plans
- Execute testing procedures
- Verify deployment success
- Identify issues
- Document test results

**Required Skills**:
- Testing methodologies
- Attention to detail
- Documentation skills
- Problem identification

#### Operations Engineer

**Responsibilities**:
- Monitor infrastructure
- Handle infrastructure issues
- Ensure resource availability
- Manage deployment environment
- Support rollback procedures

**Required Skills**:
- Infrastructure management
- Monitoring tools
- Problem-solving
- Automation skills

### Escalation Procedures

#### Level 1: Team-Level Issues

**Issues**: Minor technical problems, questions, clarifications

**Escalation Path**: Team Lead → Technical Lead

**Response Time**: < 1 hour

**Examples**:
- Syntax questions
- Minor deployment issues
- Documentation clarifications

#### Level 2: Department-Level Issues

**Issues**: Technical problems requiring specialized expertise

**Escalation Path**: Technical Lead → Database Administrator → Engineering Manager

**Response Time**: < 4 hours

**Examples**:
- Database performance issues
- Complex migration problems
- Application compatibility issues

#### Level 3: Organizational-Level Issues

**Issues**: Major problems affecting multiple teams or customers

**Escalation Path**: Engineering Manager → CTO → Executive Team

**Response Time**: < 24 hours

**Examples**:
- Production outages
- Data corruption
- Security incidents
- Customer-impacting issues

#### Level 4: Critical Emergencies

**Issues**: Critical situations requiring immediate attention

**Escalation Path**: Incident Commander → All relevant personnel → Executive Team

**Response Time**: < 15 minutes

**Examples**:
- Complete system failure
- Data loss
- Security breaches
- Regulatory compliance issues

### Communication Protocols

#### Regular Communication

**Daily Standups** (during deployment periods):
- What was accomplished yesterday
- What's planned for today
- Any blockers or issues

**Weekly Status Meetings**:
- Deployment progress updates
- Risk assessment
- Resource planning

#### Emergency Communication

**Immediate Notification**:
- Use emergency contact list
- Send to all relevant stakeholders
- Include severity level and impact

**Status Updates**:
- Provide regular updates (every 15-30 minutes)
- Include current status and next steps
- Be honest about challenges

**Resolution Notification**:
- Notify all stakeholders when resolved
- Provide summary of what happened
- Outline preventive measures

### Decision-Making Authority

#### Deployment Decisions

**Can Approve**:
- Deployment Coordinator: Standard deployments
- Technical Lead: Moderate-risk deployments
- Engineering Manager: High-risk deployments
- CTO: Critical deployments

#### Rollback Decisions

**Can Initiate**:
- Deployment Coordinator: Immediate rollback for critical issues
- Technical Lead: Rollback for high-priority issues
- Engineering Manager: Rollback for medium-priority issues

#### Emergency Decisions

**Can Declare Emergency**:
- Any team member: Can report potential emergency
- Incident Commander: Can declare emergency
- Engineering Manager: Can confirm emergency status

### Training and Onboarding

#### New Team Member Training

**Required Training**:
1. **Deployment Process Overview** (2 hours)
   - Review this guide
   - Understand deployment workflow
   - Learn safety procedures

2. **Hands-On Practice** (4 hours)
   - Practice in development environment
   - Execute test deployments
   - Practice rollback procedures

3. **Shadow Deployment** (1-2 deployments)
   - Observe actual production deployment
   - Learn from experienced team members
   - Ask questions

4. **Supervised Deployment** (1-2 deployments)
   - Execute deployment with supervision
   - Receive feedback
   - Build confidence

5. **Independent Deployment** (after approval)
   - Execute deployment independently
   - Document lessons learned
   - Continue improvement

#### Ongoing Training

**Regular Training Activities**:
- Monthly process reviews
- Quarterly training sessions
- Annual emergency drills
- Continuous learning opportunities

### Performance Metrics

#### Team Performance Metrics

**Deployment Success Rate**:
- Target: > 95%
- Measure: Successful deployments / Total deployments

**Deployment Time**:
- Target: < 30 minutes for standard deployments
- Measure: Time from start to completion

**Rollback Rate**:
- Target: < 5%
- Measure: Rollbacks / Total deployments

**Mean Time to Recovery (MTTR)**:
- Target: < 15 minutes
- Measure: Time from issue detection to resolution

#### Individual Performance Metrics

**Code Review Quality**:
- Number of issues found
- Review turnaround time
- Accuracy of assessments

**Testing Thoroughness**:
- Test coverage percentage
- Bug detection rate
- Test execution time

**Documentation Quality**:
- Completeness of documentation
- Accuracy of information
- Usability of documentation

---

## See Also

### Related Documentation

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - General deployment procedures
- [Schema Change Management](SCHEMA_CHANGE_MANAGEMENT.md) - Local schema management
- [Database Documentation](DATABASE.md) - Database structure and operations
- [CI/CD Pipeline](CI_CD_PIPELINE.md) - Continuous integration and deployment
- [Infrastructure Setup](INFRASTRUCTURE_SETUP.md) - Infrastructure configuration

### Supabase Documentation

- [Supabase CLI Documentation](https://supabase.com/docs/guides/cli)
- [Supabase Migrations](https://supabase.com/docs/guides/database/migrations)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

### External Resources

- [Database Migration Best Practices](https://www.postgresql.org/docs/current/ddl.html)
- [SQL Style Guide](https://www.sqlstyle.guide/)
- [Database Backup Strategies](https://www.postgresql.org/docs/current/backup.html)

---

## Historical Revisions

### Version 1.0.0 (2026-06-21)

**Initial Release**

**Created By**: Diane, Documentation Specialist

**Changes**:
- Created comprehensive production migration guide
- Documented complete deployment workflow
- Included safety measures and best practices
- Added troubleshooting procedures
- Provided common scenarios and examples
- Integrated CI/CD documentation
- Defined team responsibilities and escalation procedures

**Status**: Production Ready

**Reviewed By**: [To be completed]

**Approved By**: [To be completed]

---

## Appendix

### Quick Reference Commands

```bash
# Validate migration
python scripts/deploy_to_production.py --validate --migration-file "migration.sql"

# Create backup
python scripts/deploy_to_production.py --backup-only

# Deploy migration
python scripts/deploy_to_production.py --auto --migration-file "migration.sql"

# Check status
python scripts/deploy_to_production.py --status

# Rollback
python scripts/deploy_to_production.py --rollback

# Dry-run mode
python scripts/deploy_to_production.py --auto --migration-file "migration.sql" --dry-run
```

### Contact Information

**Documentation Maintainer**: Diane, Documentation Specialist
**Technical Contact**: [Technical Lead Name]
**Emergency Contact**: [Emergency Contact Information]

### Feedback and Contributions

For feedback, corrections, or contributions to this guide:
- Create an issue in the project repository
- Contact the documentation maintainer
- Submit a pull request with improvements

---

**End of Production Migration Guide**

**Last Updated**: 2026-06-21
**Version**: 1.0.0
**Status**: Production Ready