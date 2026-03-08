# Production Database Backup & Restore Guide

This guide covers creating backups of the production Supabase database and restoring them, including instructions for uploading backups to Google Drive.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup Instructions](#setup-instructions)
3. [Creating a Backup](#creating-a-backup)
4. [Uploading to Google Drive](#uploading-to-google-drive)
5. [Restoring from Backup](#restoring-from-backup)
6. [Troubleshooting](#troubleshooting)
7. [Backup Strategy Recommendations](#backup-strategy-recommendations)

---

## Prerequisites

Before creating backups, ensure you have:

### Required Software

- **PostgreSQL Client Tools** (for `pg_dump` and `psql`):
  - Ubuntu/Debian: `sudo apt-get install postgresql-client`
  - macOS: `brew install postgresql`
  - Windows: Download from [PostgreSQL official site](https://www.postgresql.org/download/windows/)

- **Python 3.7+** with required packages:
  ```bash
  pip install python-dotenv
  ```
  (Already included in `requirements.txt`)

- **gzip** (usually pre-installed on Linux/macOS)

### Required Configuration

- Valid `.env` file in project root with production database credentials:
  ```env
  SUPABASE_URL=https://<your-project-id>.supabase.co
  SUPABASE_DB_PASSWORD=<your-database-password>
  ```

---

## Setup Instructions

### 1. Verify PostgreSQL Client Installation

Check if `pg_dump` and `psql` are installed:

```bash
pg_dump --version
psql --version
```

You should see version numbers (e.g., `pg_dump (PostgreSQL) 16.13`).

### 2. Configure `.env` File

Ensure your `.env` file contains production database credentials:

```env
# Supabase Production
SUPABASE_KEY=<your-service-role-key>
SUPABASE_URL=https://<your-project-id>.supabase.co
SUPABASE_DB_PASSWORD=<your-database-password>
```

To get your database password:
1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Navigate to Settings → Database
4. Connect via URI: `postgresql://postgres.<project-ref>:<password>@aws-0-us-east-2.pooler.supabase.com:5432/postgres`
5. The `password` is your `SUPABASE_DB_PASSWORD`

### 3. Test Database Connection

```bash
# Export credentials
export SUPABASE_URL=$(grep '^SUPABASE_URL=' .env | cut -d'=' -f2 | tr -d '"')
export SUPABASE_DB_PASSWORD=$(grep '^SUPABASE_DB_PASSWORD=' .env | cut -d'=' -f2 | tr -d '"')

# Test connection
psql -h aws-0-us-east-2.pooler.supabase.com -U postgres.<project-id> -d postgres -c "SELECT version();"
```

---

## Creating a Backup

### Quick Start

Run the backup script from the project root:

```bash
python scripts/backup_production_database.py
```

### What It Does

The script performs these steps:

1. **Loads Credentials**: Reads `SUPABASE_URL` and `SUPABASE_DB_PASSWORD` from `.env`
2. **Extracts Connection Info**: Parses project ID and constructs database connection string
3. **Runs pg_dump**: Creates full backup including:
   - All tables (DDL and data)
   - Indexes, constraints, and sequences
   - Functions and triggers
   - Public schema only
4. **Compresses**: Applies gzip compression (~70% size reduction)
5. **Saves**: Outputs to `backup/db_backup_YYYYMMDD_HHMMSS.sql.gz`
6. **Displays Statistics**: Shows file size, compression ratio, and creation time
7. **Provides Instructions**: Shows how to upload to Google Drive

### Example Output

```
============================================================
🗄️  Production Database Backup
============================================================

✅ Loaded credentials from .env

✅ Extracted connection info

🔧 Running pg_dump...
   Host: aws-0-us-east-2.pooler.supabase.com
   Database: postgres
   User: postgres.nzcwtjloonumxpsqzarq

✅ pg_dump completed successfully
🗜️  Compressing backup file...
✅ Compression completed
   Original size: 45.67 MB
   Compressed size: 12.34 MB
   Compression ratio: 73.0%

📊 Backup Information:
   File: backup/db_backup_20260308_143522.sql.gz
   Size: 12.34 MB
   Created: 2026-03-08 14:35:22

📤 Google Drive Upload Instructions:
[...]

============================================================
✅ Backup completed successfully!
============================================================
```

### What Gets Backed Up

The backup includes:

- ✅ **All Tables**: Dioceses, Parishes, ParishData, etc.
- ✅ **All Data**: Every row in every table
- ✅ **Schema Structure**: Table definitions, columns, constraints
- ✅ **Indexes**: All database indexes
- ✅ **Sequences**: Auto-increment sequences
- ✅ **Functions**: Custom SQL functions
- ✅ **Triggers**: Database triggers
- ✅ **Views**: Database views

The backup excludes:

- ❌ **Owner/ACL info**: Ownership and access control for portability
- ❌ **System schemas**: Only `public` schema is backed up
- ❌ **Large objects**: BLOBs (if any)

---

## Uploading to Google Drive

### Method 1: Web Interface (Manual)

1. **Open Google Drive**
   - Navigate to: https://drive.google.com
   - Sign in with your account

2. **Create Backup Folder Structure**
   - Create folder: `diocesan-vitality/`
   - Create subfolder: `diocesan-vitality/backups/`
   - Create year subfolder: `diocesan-vitality/backups/2026/`

3. **Upload Backup File**
   - Click "New" → "File upload"
   - Navigate to: `backup/db_backup_YYYYMMDD_HHMMSS.sql.gz`
   - Select the file and click "Open"

4. **Verify Upload**
   - Confirm file uploaded successfully
   - Check file size matches local backup
   - Download to verify integrity (optional)

### Method 2: Google Drive for Desktop (Automatic)

1. **Install Google Drive for Desktop**
   - Download: https://www.google.com/drive/download/
   - Install on your machine

2. **Configure Sync**
   - Sign into Google Drive for Desktop
   - Navigate to Google Drive in file explorer
   - Create folder: `diocesan-vitality/backups/`
   - Move local `backup/` folder to Google Drive synced location

3. **Automatic Backups**
   - When you create a backup, it automatically syncs to Google Drive
   - No manual upload required
   - Monitor sync status via desktop tray icon

### Recommended Folder Structure

```
Google Drive/
└── diocesan-vitality/
    └── backups/
        ├── 2026/
        │   ├── 01/
        │   │   ├── db_backup_20260115_120000.sql.gz
        │   │   └── db_backup_20260122_120000.sql.gz
        │   └── 03/
        │       └── db_backup_20260308_143522.sql.gz  ← Latest
        ├── 2025/
        └── 2024/
```

---

## Restoring from Backup

### Option 1: Restore via psql (Command Line)

1. **Decompress Backup**
   ```bash
   gunzip backup/db_backup_20260308_143522.sql.gz
   # Result: backup/db_backup_20260308_143522.sql
   ```

2. **Restore to Database**
   ```bash
   # Set environment variables
   export PGPASSWORD="your-database-password"
   export DB_HOST="aws-0-us-east-2.pooler.supabase.com"
   export DB_PORT="5432"
   export DB_USER="postgres.nzcwtjloonumxpsqzarq"
   export DB_NAME="postgres"

   # Restore database
   psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f backup/db_backup_20260308_143522.sql
   ```

3. **Verify Restore**
   ```bash
   psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt"
   ```

### Option 2: Restore via Supabase SQL Editor

1. **Open Supabase SQL Editor**
   - Go to: https://supabase.com/dashboard/project/<project-id>/sql/new

2. **Decompress Backup** (if needed)
   ```bash
   gunzip backup/db_backup_20260308_143522.sql.gz
   ```

3. **Paste SQL File**
   - Open `backup/db_backup_20260308_143522.sql` in a text editor
   - Since the file is large, you may need to split it:
     ```bash
     # Split into chunks of 1MB
     split -l 50000 backup/db_backup_20260308_143522.sql chunk_
     # This creates chunk_aa, chunk_ab, etc.
     ```
   - Copy and paste each chunk into the SQL editor
   - Click "Run" after each chunk
   - Wait for completion before pasting the next chunk

4. **Verify Restore**
   - Run `SELECT * FROM "Parishes" LIMIT 10;` to verify data exists

### Option 3: Restore to Local PostgreSQL (Testing)

1. **Install PostgreSQL Locally**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib

   # macOS
   brew install postgresql
   brew services start postgresql
   ```

2. **Create Test Database**
   ```bash
   createdb test_restore
   ```

3. **Restore Backup**
   ```bash
   gunzip backup/db_backup_20260308_143522.sql.gz
   psql test_restore < backup/db_backup_20260308_143522.sql
   ```

4. **Verify Data**
   ```bash
   psql test_restore -c "\dt"
   psql test_restore -c 'SELECT COUNT(*) FROM "Parishes";'
   ```

### ⚠️ Important: Production Restore Precautions

**Before restoring to production:**

1. **Test First**: Always restore to a dev/staging environment first
2. **Backup Current Data**: Create a backup of current production state
3. **Plan Maintenance Window**: Schedule during low-traffic period
4. **Notify Users**: Alert users about potential downtime
5. **Verify Backup**: Confirm backup file is not corrupted
6. **Check Version Compatibility**: Ensure PostgreSQL versions match

**During restore:**

1. **Drop Existing Schema**: Clear target database first
2. **Monitor Progress**: Watch for errors during restore
3. **Verify Data**: Spot-check critical tables after restore

**After restore:**

1. **Verify Application**: Test application functionality
2. **Check Data Integrity**: Run validation scripts
3. **Monitor Performance**: Ensure no performance degradation
4. **Document**: Record restore details for audit trail

---

## Troubleshooting

### Common Issues

#### Issue 1: "pg_dump: command not found"

**Problem:** PostgreSQL client tools not installed

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install postgresql-client

# macOS
brew install postgresql

# Verify installation
pg_dump --version
```

#### Issue 2: "FATAL: password authentication failed"

**Problem:** Incorrect database password or user

**Solution:**
1. Verify `SUPABASE_DB_PASSWORD` in `.env` file
2. Check password from Supabase Dashboard:
   - Settings → Database → Connection Parameters
3. Ensure password is not wrapped in quotes
4. Check for special characters that need escaping

#### Issue 3: "Connection refused" or "timeout"

**Problem:** Network connectivity or firewall issues

**Solutions:**

1. **Check Internet Connection**
   ```bash
   ping aws-0-us-east-2.pooler.supabase.com
   ```

2. **Test with Telnet** (if available)
   ```bash
   telnet aws-0-us-east-2.pooler.supabase.com 5432
   ```

3. **Check Firewall Rules**
   - Ensure outbound connections on port 5432 are allowed
   - Try turning off VPN temporarily

4. **Use Direct DB Host** (bypass pooler)
   - Change pooler endpoint to direct DB host
   - Requires IPv6 connectivity

#### Issue 4: "gzip: (stdin): unexpected end of file"

**Problem:** Backup file corrupted during compression

**Solution:**
1. Check available disk space:
   ```bash
   df -h
   ```
2. Ensure sufficient space (at least 3x database size)
3. Delete old backups to free space
4. Re-run backup script

#### Issue 5: "psql: ERROR: relation already exists"

**Problem:** Trying to restore to database with existing schema

**Solution:**
1. Drop existing schema before restore:
   ```bash
   psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
   ```
2. Create fresh database instead

#### Issue 6: "ImportError: No module named 'dotenv'"

**Problem:** Python dependencies not installed

**Solution:**
```bash
# Install from requirements.txt
pip install -r requirements.txt

# Or install directly
pip install python-dotenv
```

#### Issue 7: Google Drive Upload Failed

**Problem:** Upload stops or times out for large files

**Solutions:**

1. **Check File Size**
   ```bash
   ls -lh backup/db_backup_*.sql.gz
   ```
   - Google Drive free tier: 15GB per file
   - If larger, split into multiple backups

2. **Stable Internet Connection**
   - Use wired connection
   - Avoid public WiFi

3. **Use Google Drive for Desktop**
   - More reliable for large files
   - Resumes interrupted uploads

4. **Verify File Integrity**
   ```bash
   # Check gzip file is valid
   gzip -t backup/db_backup_20260308_143522.sql.gz
   ```

### Debug Mode

Enable verbose output for troubleshooting:

```bash
# Run backup with pg_dump verbose
PGPASSWORD="your-password" pg_dump -h aws-0-us-east-2.pooler.supabase.com -U postgres.xxxx -d postgres --verbose
```

---

## Backup Strategy Recommendations

### Frequency

Environment | Frequency | Rationale
------------|-----------|-----------
Production  | Daily     | High activity, frequent data changes
Staging     | Weekly    | Less frequent, lower criticality
Development | On-demand | As needed before major changes

### Retention Policy

- **Daily backups**: Keep last 7 days
- **Weekly backups**: Keep last 4 weeks
- **Monthly backups**: Keep last 12 months
- **Annual backups**: Keep indefinitely (archive)

### Backup Types

1. **Full Backups** (this script)
   - Complete database snapshot
   - Run: Daily
   - Size: 10-100MB (compressed)
   - Storage: Google Drive

2. **Schema-Only Backups**
   - Structure without data
   - Run: Before schema changes
   - Use: `database-schema-refresh` from Makefile
   - Storage: Git repository (`sql/initial_schema.sql`)

3. **Incremental Backups** (future enhancement)
   - Only changed data since last backup
   - Implement: Custom timestamp-based exports
   - Use: For large databases (>10GB)

### Storage Locations

1. **Local Storage** (`backup/` directory)
   - Keep last 3 backups locally
   - Fast restore for emergencies
   - Automated cleanup via script

2. **Google Drive**
   - Primary cloud storage
   - All backups synced
   - Organized by date/year
   - Version history available

3. **Supabase Database** (consider for future)
   - Point-in-time recovery
   - Native backup features
   - Automatic daily backups (paid plans)

### Automation Ideas

#### Cron Job for Daily Backups

Add to crontab (`crontab -e`):

```bash
# Daily backup at 2:00 AM
0 2 * * * cd /path/to/diocesan-vitality && python scripts/backup_production_database.py >> logs/backup.log 2>&1
```

#### Backup Rotation Script

Create `scripts/rotate_backups.py`:

```python
# Keep last 5 backups, delete older ones
import glob
from pathlib import Path
import datetime

backup_dir = Path('backup')
backups = sorted(backup_dir.glob('db_backup_*.sql.gz'), reverse=True)

for old_backup in backups[5:]:
    old_backup.unlink()
    print(f'Deleted old backup: {old_backup}')
```

### Monitoring & Alerts

1. **Backup Success Notifications**
   - Send email/Slack after successful backup
   - Include file size, duration, timestamp

2. **Backup Failure Alerts**
   - Immediate notification on failure
   - Include error logs
   - Escalate if not resolved within 24h

3. **Storage Warnings**
   - Alert if storage exceeds 80% capacity
   - Clean up old backups automatically

### Testing & Validation

1. **Weekly Test Restores**
   - Restore most recent backup to staging
   - Verify critical tables
   - Check application functionality

2. **Monthly Full Validation**
   - Restore complete database to test environment
   - Run data integrity checks
   - Validate indices and constraints

3. **Backup Integrity Checks**
   ```bash
   # Test gzip integrity
   gzip -t backup/db_backup_*.sql.gz

   # Test SQL file syntax
   gunzip -c backup/db_backup_*.sql.gz | head -100 | psql -v ON_ERROR_STOP=1
   ```

---

## Emergency Procedures

### Disaster Recovery Checklist

If production database is corrupted or lost:

1. **Assess Damage**
   - Identify what data is affected
   - Determine if partial restore is sufficient
   - Check multiple backup dates for best candidate

2. **Select Backup**
   - Choose most recent valid backup before incident
   - Confirm backup file integrity
   - Document backup date/timestamp

3. **Pre-Restore Preparation**
   - Notify all stakeholders
   - Backup current (corrupted) state for analysis
   - Prepare maintenance window
   - Test restore on staging first

4. **Execute Restore**
   - Follow [Restore from Backup](#restoring-from-backup) procedures
   - Monitor progress closely
   - Address errors immediately

5. **Post-Restore Verification**
   - Verify critical data integrity
   - Test application functionality
   - Run validation scripts
   - Accept traffic only after verification complete

6. **Post-Incident Review**
   - Document root cause
   - Update backup/restore procedures
   - Implement preventive measures
   - Review backup frequency and retention

---

## Additional Resources

- [Supabase Database Documentation](https://supabase.com/docs/guides/database)
- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [pg_dump Manual](https://www.postgresql.org/docs/current/app-pgdump.html)
- [Google Drive Help](https://support.google.com/drive)

---

## Questions or Issues?

For questions or issues with backup/restore procedures:

1. Check the [Troubleshooting](#troubleshooting) section first
2. Review script logs: Check script output for specific errors
3. Verify credentials: Ensure `.env` values are correct
4. Test connectivity: Confirm database connection works
5. Contact team: If issue persists, reach out to development team

---

**Last Updated:** 2026-03-08  
**Script Version:** 1.0.0  
**Maintained By:** Development Team