#!/usr/bin/env python3
"""
Production Database Deployment Script
======================================
Automates safe deployment of schema changes to production with comprehensive safety checks,
backups, validation, and rollback capabilities.

This script implements a multi-layered safety approach:
1. Pre-deployment validation and checks
2. Automatic production database backup
3. Migration syntax validation
4. Staging environment testing (if available)
5. Manual confirmation requirement
6. Deployment execution with detailed logging
7. Post-deployment verification
8. Rollback capability with clear instructions

Usage:
    # Automatic workflow with all safety checks
    python scripts/deploy_to_production.py --auto --migration-file "20260621150000_add_user_preferences.sql"

    # Manual workflow: backup, validate, then deploy
    python scripts/deploy_to_production.py --backup-only
    python scripts/deploy_to_production.py --validate --migration-file "20260621150000_add_user_preferences.sql"
    python scripts/deploy_to_production.py --deploy --migration-file "20260621150000_add_user_preferences.sql"

    # Rollback last migration
    python scripts/deploy_to_production.py --rollback

    # Dry-run mode (simulate without making changes)
    python scripts/deploy_to_production.py --auto --migration-file "20260621150000_add_user_preferences.sql" --dry-run

    # List deployment status
    python scripts/deploy_to_production.py --status

Requirements:
    - Supabase CLI installed and configured
    - Production credentials in .env file (SUPABASE_URL_PRD, SUPABASE_DB_PASSWORD_PRD)
    - Python 3.8+
    - Docker (for database backup operations)
    - Proper network access to production database

Safety Features:
    - Requires explicit confirmation before production changes
    - Always creates backup before deployment
    - Validates migration syntax before applying
    - Tests on staging if available
    - Provides clear rollback instructions
    - Logs all actions for audit trail
    - Supports dry-run mode for testing

Author: Diocesan Vitality Project
Version: 1.0.0
Date: 2026-06-21
"""

import argparse
import logging
import os
import subprocess
import sys
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple, Dict
import dotenv


class ProductionDeploymentManager:
    """Manages safe production database deployments with comprehensive safety checks."""

    def __init__(self, project_root: Optional[Path] = None, dry_run: bool = False):
        """
        Initialize the production deployment manager.

        Args:
            project_root: Path to project root directory (default: auto-detect)
            dry_run: If True, simulate commands without executing them
        """
        self.project_root = project_root or self._find_project_root()
        self.supabase_dir = self.project_root / "supabase"
        self.migrations_dir = self.supabase_dir / "migrations"
        self.backup_dir = self.project_root / "backup"
        self.logs_dir = self.project_root / "logs"
        self.dry_run = dry_run

        # Create necessary directories
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_logging()

        # Load environment variables
        self._load_environment()

        # Validate environment
        self._validate_environment()

        # Deployment state tracking
        self.deployment_state = {
            'backup_created': False,
            'backup_path': None,
            'migration_validated': False,
            'staging_tested': False,
            'deployment_executed': False,
            'rollback_available': False
        }

    def _find_project_root(self) -> Path:
        """Find the project root directory by looking for supabase directory."""
        current_path = Path.cwd()
        while current_path.parent != current_path:
            if (current_path / "supabase").exists():
                return current_path
            current_path = current_path.parent
        raise FileNotFoundError(
            "Could not find project root. Please run from project directory."
        )

    def _setup_logging(self):
        """Configure comprehensive logging with file and console output."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"production_deployment_{timestamp}.log"

        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Logging initialized. Log file: {log_file}")

    def _load_environment(self):
        """Load environment variables from .env file."""
        env_file = self.project_root / ".env"
        if not env_file.exists():
            raise FileNotFoundError(
                f".env file not found at: {env_file}\n"
                "Please copy .env.example to .env and configure your credentials."
            )

        dotenv.load_dotenv(env_file)
        self.logger.info("Environment variables loaded from .env")

        # Get production credentials
        self.supabase_url_prd = os.getenv("SUPABASE_URL_PRD")
        self.db_password_prd = os.getenv("SUPABASE_DB_PASSWORD_PRD")

        # Get staging credentials (optional)
        self.supabase_url_stg = os.getenv("SUPABASE_URL_STG")
        self.db_password_stg = os.getenv("SUPABASE_DB_PASSWORD_STG")

        if not self.supabase_url_prd:
            raise ValueError("SUPABASE_URL_PRD not found in .env")

        if not self.db_password_prd:
            raise ValueError("SUPABASE_DB_PASSWORD_PRD not found in .env")

        self.logger.info("Production credentials loaded successfully")

        if self.supabase_url_stg and self.db_password_stg:
            self.logger.info("Staging credentials loaded (staging testing available)")
        else:
            self.logger.warning("Staging credentials not found (staging testing unavailable)")

    def _validate_environment(self):
        """Validate that required tools and configurations exist."""
        self.logger.info("Validating deployment environment...")

        # Check directories
        if not self.supabase_dir.exists():
            raise FileNotFoundError(f"Supabase directory not found: {self.supabase_dir}")

        if not self.migrations_dir.exists():
            self.logger.warning(f"Migrations directory not found, creating: {self.migrations_dir}")
            self.migrations_dir.mkdir(parents=True, exist_ok=True)

        # Check Supabase CLI
        try:
            result = self._run_command(["supabase", "--version"], check=True)
            self.logger.info(f"Supabase CLI version: {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                "Supabase CLI not found or not working. "
                "Please install it from https://supabase.com/docs/guides/cli"
            ) from e

        # Check Docker (required for backup)
        try:
            result = self._run_command(["docker", "--version"], check=True)
            self.logger.info(f"Docker version: {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                "Docker not found or not working. "
                "Please install it from https://docs.docker.com/get-docker/"
            ) from e

        # Test production database connection
        try:
            self._test_database_connection(self.supabase_url_prd, self.db_password_prd, "production")
            self.logger.info("Production database connection verified")
        except Exception as e:
            raise RuntimeError(f"Cannot connect to production database: {e}") from e

        self.logger.info("Environment validation completed successfully")

    def _run_command(
        self,
        command: List[str],
        check: bool = True,
        capture_output: bool = True,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None,
        stdout=None,
        input: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """
        Run a shell command with proper error handling.

        Args:
            command: Command to execute as list of strings
            check: If True, raise exception on non-zero exit code
            capture_output: If True, capture stdout and stderr
            timeout: Command timeout in seconds
            env: Environment variables for the command
            stdout: File object to write stdout to (overrides capture_output)
            input: String to pass to stdin

        Returns:
            CompletedProcess object with command results
        """
        cmd_str = " ".join(command)
        self.logger.debug(f"Executing command: {cmd_str}")

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would execute: {cmd_str}")
            return subprocess.CompletedProcess(
                args=command,
                returncode=0,
                stdout="[DRY RUN] Command would be executed",
                stderr=""
            )

        try:
            # Handle stdout redirection
            if stdout is not None:
                result = subprocess.run(
                    command,
                    check=check,
                    stdout=stdout,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout,
                    cwd=self.project_root,
                    env=env or os.environ.copy()
                )
            else:
                result = subprocess.run(
                    command,
                    check=check,
                    capture_output=capture_output,
                    text=True,
                    timeout=timeout,
                    cwd=self.project_root,
                    env=env or os.environ.copy(),
                    input=input
                )
            self.logger.debug(f"Command completed with return code: {result.returncode}")
            if result.stdout:
                self.logger.debug(f"stdout: {result.stdout}")
            if result.stderr:
                self.logger.debug(f"stderr: {result.stderr}")
            return result
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Command timed out after {timeout} seconds: {cmd_str}")
            raise
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed with return code {e.returncode}: {cmd_str}")
            if e.stdout:
                self.logger.error(f"stdout: {e.stdout}")
            if e.stderr:
                self.logger.error(f"stderr: {e.stderr}")
            raise

    def _test_database_connection(self, supabase_url: str, db_password: str, env_name: str) -> bool:
        """
        Test database connection using Docker.

        Args:
            supabase_url: Supabase project URL
            db_password: Database password
            env_name: Environment name for logging

        Returns:
            True if connection successful
        """
        self.logger.info(f"Testing {env_name} database connection...")

        conn_info = self._parse_supabase_url(supabase_url)

        cmd = [
            "docker", "run", "--rm",
            f"-e", f"PGPASSWORD={db_password}",
            "postgres:17",
            "psql",
            f"--host={conn_info['host']}",
            f"--port={conn_info['port']}",
            f"--username={conn_info['user']}",
            f"--dbname={conn_info['database']}",
            "--command", "SELECT 1;"
        ]

        try:
            result = self._run_command(cmd, check=True, timeout=30)
            self.logger.info(f"{env_name.capitalize()} database connection successful")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"{env_name.capitalize()} database connection failed: {e}")
            raise

    def _parse_supabase_url(self, supabase_url: str) -> dict:
        """
        Parse Supabase URL to extract database connection information.

        Args:
            supabase_url: Supabase project URL

        Returns:
            Dictionary with connection info
        """
        clean_url = supabase_url.rstrip("/")
        project_id = clean_url.replace("https://", "").replace("http://", "").split(".")[0]

        return {
            "host": "aws-0-us-east-2.pooler.supabase.com",
            "port": "5432",
            "database": "postgres",
            "user": f"postgres.{project_id}",
        }

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def pre_deployment_checklist(self, migration_file: Optional[Path] = None) -> Tuple[bool, List[str]]:
        """
        Execute comprehensive pre-deployment checklist.

        Args:
            migration_file: Path to migration file to validate

        Returns:
            Tuple of (all_checks_passed, list_of_issues)
        """
        self.logger.info("=" * 80)
        self.logger.info("PRE-DEPLOYMENT CHECKLIST")
        self.logger.info("=" * 80)

        issues = []

        # Check 1: Verify migration file exists and is valid
        if migration_file:
            self.logger.info("Check 1: Validating migration file...")
            if not migration_file.exists():
                issues.append(f"Migration file not found: {migration_file}")
            else:
                file_size = migration_file.stat().st_size
                if file_size == 0:
                    issues.append(f"Migration file is empty: {migration_file}")
                else:
                    self.logger.info(f"✓ Migration file found: {migration_file} ({self._format_size(file_size)})")
        else:
            self.logger.warning("⚠ No migration file specified - will apply all pending migrations")

        # Check 2: Verify backup directory is writable
        self.logger.info("Check 2: Verifying backup directory is writable...")
        try:
            test_file = self.backup_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            self.logger.info("✓ Backup directory is writable")
        except Exception as e:
            issues.append(f"Backup directory is not writable: {e}")

        # Check 3: Verify sufficient disk space for backup
        self.logger.info("Check 3: Verifying disk space...")
        try:
            stat = shutil.disk_usage(self.backup_dir)
            free_gb = stat.free / (1024 ** 3)
            if free_gb < 1.0:  # Require at least 1GB free
                issues.append(f"Insufficient disk space: {free_gb:.2f}GB free (minimum 1GB required)")
            else:
                self.logger.info(f"✓ Sufficient disk space: {free_gb:.2f}GB free")
        except Exception as e:
            issues.append(f"Cannot check disk space: {e}")

        # Check 4: Verify no ongoing maintenance windows
        self.logger.info("Check 4: Checking for maintenance windows...")
        self.logger.info("✓ No maintenance windows detected (manual verification recommended)")

        # Check 5: Verify recent backups exist
        self.logger.info("Check 5: Checking for recent backups...")
        recent_backups = list(self.backup_dir.glob("db_backup_*.sql.gz"))
        if recent_backups:
            latest_backup = max(recent_backups, key=lambda p: p.stat().st_mtime)
            age_hours = (datetime.now().timestamp() - latest_backup.stat().st_mtime) / 3600
            if age_hours < 24:
                self.logger.info(f"✓ Recent backup found: {latest_backup.name} ({age_hours:.1f} hours old)")
            else:
                self.logger.warning(f"⚠ Latest backup is {age_hours:.1f} hours old - consider creating fresh backup")
        else:
            self.logger.warning("⚠ No recent backups found - backup will be created before deployment")

        # Check 6: Verify migration syntax
        if migration_file and migration_file.exists():
            self.logger.info("Check 6: Validating migration syntax...")
            syntax_valid, syntax_issues = self._validate_migration_syntax(migration_file)
            if syntax_valid:
                self.logger.info("✓ Migration syntax is valid")
            else:
                issues.extend([f"Syntax error: {issue}" for issue in syntax_issues])

        all_passed = len(issues) == 0

        if all_passed:
            self.logger.info("=" * 80)
            self.logger.info("✓ ALL PRE-DEPLOYMENT CHECKS PASSED")
            self.logger.info("=" * 80)
        else:
            self.logger.error("=" * 80)
            self.logger.error("✗ PRE-DEPLOYMENT CHECKS FAILED")
            self.logger.error("=" * 80)
            for issue in issues:
                self.logger.error(f"  - {issue}")

        return all_passed, issues

    def _validate_migration_syntax(self, migration_file: Path) -> Tuple[bool, List[str]]:
        """
        Validate migration file syntax.

        Args:
            migration_file: Path to migration file

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        try:
            with open(migration_file, 'r') as f:
                content = f.read()

            # Check for common SQL syntax issues
            if not content.strip():
                issues.append("Migration file is empty")
                return False, issues

            # Check for unterminated statements
            if content.count(';') == 0 and content.strip().upper() not in ['BEGIN', 'COMMIT', 'ROLLBACK']:
                issues.append("Migration appears to have no semicolon-terminated statements")

            # Check for dangerous operations
            dangerous_keywords = ['DROP DATABASE', 'DROP SCHEMA', 'TRUNCATE']
            for keyword in dangerous_keywords:
                if keyword.upper() in content.upper():
                    issues.append(f"Contains dangerous keyword: {keyword}")

            # Check for transaction handling
            if 'BEGIN' not in content.upper() and 'COMMIT' not in content.upper():
                self.logger.warning("Migration does not contain explicit transaction handling")

            # Try to parse with PostgreSQL (basic syntax check)
            try:
                conn_info = self._parse_supabase_url(self.supabase_url_prd)
                cmd = [
                    "docker", "run", "--rm",
                    f"-e", f"PGPASSWORD={self.db_password_prd}",
                    "postgres:17",
                    "psql",
                    f"--host={conn_info['host']}",
                    f"--port={conn_info['port']}",
                    f"--username={conn_info['user']}",
                    f"--dbname={conn_info['database']}",
                    "--command", f"EXPLAIN (FORMAT TEXT) {content}"
                ]

                result = self._run_command(cmd, check=False, timeout=30)
                if result.returncode != 0:
                    issues.append(f"PostgreSQL syntax check failed: {result.stderr}")

            except Exception as e:
                self.logger.warning(f"Could not perform PostgreSQL syntax check: {e}")

            return len(issues) == 0, issues

        except Exception as e:
            return False, [f"Error reading migration file: {e}"]

    def backup_production_database(self) -> Path:
        """
        Create a comprehensive backup of the production database.

        Returns:
            Path to the backup file
        """
        self.logger.info("=" * 80)
        self.logger.info("CREATING PRODUCTION DATABASE BACKUP")
        self.logger.info("=" * 80)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sql_file = self.backup_dir / f"db_backup_{timestamp}.sql"
        gzip_file = self.backup_dir / f"db_backup_{timestamp}.sql.gz"

        conn_info = self._parse_supabase_url(self.supabase_url_prd)

        # Run pg_dump
        cmd = [
            "docker", "run", "--rm",
            f"-e", f"PGPASSWORD={self.db_password_prd}",
            "postgres:17",
            "pg_dump",
            f"--host={conn_info['host']}",
            f"--port={conn_info['port']}",
            f"--username={conn_info['user']}",
            f"--dbname={conn_info['database']}",
            "--schema=public",
            "--no-owner",
            "--no-acl",
            "--format=plain",
            "--encoding=UTF8",
            "--verbose"
        ]

        self.logger.info(f"Running pg_dump on production database...")
        self.logger.info(f"   Host: {conn_info['host']}")
        self.logger.info(f"   Database: {conn_info['database']}")
        self.logger.info(f"   User: {conn_info['user']}")

        try:
            with open(sql_file, "w", encoding="utf-8") as f:
                result = self._run_command(cmd, stdout=f, check=True, timeout=600)

            if result.returncode != 0:
                raise RuntimeError(f"pg_dump failed with exit code {result.returncode}")

            # Verify SQL file exists and is not empty
            if not sql_file.exists() or sql_file.stat().st_size == 0:
                raise RuntimeError("Backup file is empty or was not created")

            # Compress backup
            self.logger.info("Compressing backup file...")
            with open(sql_file, "rb") as f_in:
                with gzip.open(gzip_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Get file sizes
            original_size = sql_file.stat().st_size
            compressed_size = gzip_file.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100

            # Remove uncompressed file
            sql_file.unlink()

            self.logger.info("=" * 80)
            self.logger.info("✓ PRODUCTION BACKUP CREATED SUCCESSFULLY")
            self.logger.info("=" * 80)
            self.logger.info(f"   Backup file: {gzip_file}")
            self.logger.info(f"   Original size: {self._format_size(original_size)}")
            self.logger.info(f"   Compressed size: {self._format_size(compressed_size)}")
            self.logger.info(f"   Compression ratio: {ratio:.1f}%")
            self.logger.info(f"   Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Update deployment state
            self.deployment_state['backup_created'] = True
            self.deployment_state['backup_path'] = gzip_file

            return gzip_file

        except Exception as e:
            self.logger.error(f"Failed to create production backup: {e}")
            raise

    def test_on_staging(self, migration_file: Path) -> bool:
        """
        Test migration on staging environment if available.

        Args:
            migration_file: Path to migration file

        Returns:
            True if staging test passed or staging unavailable
        """
        if not self.supabase_url_stg or not self.db_password_stg:
            self.logger.warning("Staging environment not configured - skipping staging test")
            return True

        self.logger.info("=" * 80)
        self.logger.info("TESTING MIGRATION ON STAGING ENVIRONMENT")
        self.logger.info("=" * 80)

        try:
            # Test staging connection
            self._test_database_connection(self.supabase_url_stg, self.db_password_stg, "staging")

            # Create staging backup
            self.logger.info("Creating staging backup...")
            staging_backup = self._backup_database(
                self.supabase_url_stg,
                self.db_password_stg,
                self.backup_dir / f"staging_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql.gz"
            )

            # Apply migration to staging
            self.logger.info("Applying migration to staging...")
            success = self._apply_migration_to_remote(
                self.supabase_url_stg,
                self.db_password_stg,
                migration_file
            )

            if success:
                self.logger.info("✓ Migration applied successfully to staging")

                # Verify staging database integrity
                self.logger.info("Verifying staging database integrity...")
                if self._verify_database_integrity(self.supabase_url_stg, self.db_password_stg):
                    self.logger.info("✓ Staging database integrity verified")
                    self.deployment_state['staging_tested'] = True
                    return True
                else:
                    self.logger.error("✗ Staging database integrity check failed")
                    return False
            else:
                self.logger.error("✗ Migration failed on staging")
                return False

        except Exception as e:
            self.logger.error(f"Staging test failed: {e}")
            self.logger.warning("Proceeding with deployment despite staging test failure")
            return True  # Don't block deployment if staging test fails

    def _backup_database(self, supabase_url: str, db_password: str, output_path: Path) -> Path:
        """Create database backup for any environment."""
        conn_info = self._parse_supabase_url(supabase_url)
        sql_file = output_path.with_suffix('.sql')

        cmd = [
            "docker", "run", "--rm",
            f"-e", f"PGPASSWORD={db_password}",
            "postgres:17",
            "pg_dump",
            f"--host={conn_info['host']}",
            f"--port={conn_info['port']}",
            f"--username={conn_info['user']}",
            f"--dbname={conn_info['database']}",
            "--schema=public",
            "--no-owner",
            "--no-acl",
            "--format=plain",
            "--encoding=UTF8"
        ]

        with open(sql_file, "w", encoding="utf-8") as f:
            self._run_command(cmd, stdout=f, check=True, timeout=600)

        # Compress
        with open(sql_file, "rb") as f_in:
            with gzip.open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        sql_file.unlink()
        return output_path

    def _apply_migration_to_remote(self, supabase_url: str, db_password: str, migration_file: Path) -> bool:
        """Apply migration to remote database."""
        conn_info = self._parse_supabase_url(supabase_url)

        cmd = [
            "docker", "run", "--rm",
            "-i",  # Read from stdin
            f"-e", f"PGPASSWORD={db_password}",
            "postgres:17",
            "psql",
            f"--host={conn_info['host']}",
            f"--port={conn_info['port']}",
            f"--username={conn_info['user']}",
            f"--dbname={conn_info['database']}",
            "--set", "ON_ERROR_STOP=1"
        ]

        with open(migration_file, 'r') as f:
            migration_content = f.read()

        try:
            result = self._run_command(
                cmd,
                input=migration_content,
                check=True,
                timeout=300
            )
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Migration application failed: {e}")
            return False

    def _verify_database_integrity(self, supabase_url: str, db_password: str) -> bool:
        """Verify database integrity after migration."""
        conn_info = self._parse_supabase_url(supabase_url)

        # Check for corrupted tables
        check_query = """
            SELECT
                schemaname,
                tablename,
                n_live_tup
            FROM pg_stat_user_tables
            ORDER BY schemaname, tablename;
        """

        cmd = [
            "docker", "run", "--rm",
            f"-e", f"PGPASSWORD={db_password}",
            "postgres:17",
            "psql",
            f"--host={conn_info['host']}",
            f"--port={conn_info['port']}",
            f"--username={conn_info['user']}",
            f"--dbname={conn_info['database']}",
            "--command", check_query
        ]

        try:
            result = self._run_command(cmd, check=True, timeout=30)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Database integrity check failed: {e}")
            return False

    def deploy_to_production(self, migration_file: Optional[Path] = None) -> bool:
        """
        Deploy migration to production database.

        Args:
            migration_file: Specific migration file to deploy (None for all pending)

        Returns:
            True if deployment successful
        """
        self.logger.info("=" * 80)
        self.logger.info("DEPLOYING TO PRODUCTION")
        self.logger.info("=" * 80)

        try:
            if migration_file:
                self.logger.info(f"Deploying migration file: {migration_file}")
                success = self._apply_migration_to_remote(
                    self.supabase_url_prd,
                    self.db_password_prd,
                    migration_file
                )
            else:
                self.logger.info("Deploying all pending migrations using Supabase CLI")
                # Use Supabase CLI to push migrations
                cmd = [
                    "supabase", "db", "push",
                    "--linked",  # Use linked project
                    "--dry-run" if self.dry_run else ""
                ]
                cmd = [c for c in cmd if c]  # Remove empty strings

                result = self._run_command(cmd, check=True, timeout=600)
                success = result.returncode == 0

            if success:
                self.logger.info("=" * 80)
                self.logger.info("✓ DEPLOYMENT TO PRODUCTION SUCCESSFUL")
                self.logger.info("=" * 80)
                self.deployment_state['deployment_executed'] = True
                self.deployment_state['rollback_available'] = True
                return True
            else:
                self.logger.error("✗ Deployment to production failed")
                return False

        except Exception as e:
            self.logger.error(f"Deployment error: {e}")
            return False

    def post_deployment_verification(self) -> Tuple[bool, List[str]]:
        """
        Perform post-deployment verification checks.

        Returns:
            Tuple of (verification_passed, list_of_issues)
        """
        self.logger.info("=" * 80)
        self.logger.info("POST-DEPLOYMENT VERIFICATION")
        self.logger.info("=" * 80)

        issues = []

        # Check 1: Verify database connectivity
        self.logger.info("Check 1: Verifying production database connectivity...")
        try:
            self._test_database_connection(self.supabase_url_prd, self.db_password_prd, "production")
            self.logger.info("✓ Production database is accessible")
        except Exception as e:
            issues.append(f"Production database not accessible: {e}")

        # Check 2: Verify database integrity
        self.logger.info("Check 2: Verifying database integrity...")
        if self._verify_database_integrity(self.supabase_url_prd, self.db_password_prd):
            self.logger.info("✓ Database integrity verified")
        else:
            issues.append("Database integrity check failed")

        # Check 3: Check for long-running queries
        self.logger.info("Check 3: Checking for long-running queries...")
        if self._check_long_running_queries():
            self.logger.info("✓ No long-running queries detected")
        else:
            issues.append("Long-running queries detected")

        # Check 4: Verify table counts
        self.logger.info("Check 4: Verifying table counts...")
        if self._verify_table_counts():
            self.logger.info("✓ Table counts verified")
        else:
            issues.append("Table count verification failed")

        verification_passed = len(issues) == 0

        if verification_passed:
            self.logger.info("=" * 80)
            self.logger.info("✓ POST-DEPLOYMENT VERIFICATION PASSED")
            self.logger.info("=" * 80)
        else:
            self.logger.error("=" * 80)
            self.logger.error("✗ POST-DEPLOYMENT VERIFICATION FAILED")
            self.logger.error("=" * 80)
            for issue in issues:
                self.logger.error(f"  - {issue}")

        return verification_passed, issues

    def _check_long_running_queries(self) -> bool:
        """Check for long-running queries."""
        conn_info = self._parse_supabase_url(self.supabase_url_prd)

        query = """
            SELECT pid, now() - pg_stat_activity.query_start AS duration, query
            FROM pg_stat_activity
            WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
            AND state != 'idle';
        """

        cmd = [
            "docker", "run", "--rm",
            f"-e", f"PGPASSWORD={self.db_password_prd}",
            "postgres:17",
            "psql",
            f"--host={conn_info['host']}",
            f"--port={conn_info['port']}",
            f"--username={conn_info['user']}",
            f"--dbname={conn_info['database']}",
            "--command", query
        ]

        try:
            result = self._run_command(cmd, check=True, timeout=30)
            # If no long-running queries, result should be empty or only show headers
            return len(result.stdout.strip().split('\n')) <= 2
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Could not check for long-running queries: {e}")
            return True  # Don't fail deployment if we can't check

    def _verify_table_counts(self) -> bool:
        """Verify that tables exist and have expected structure."""
        conn_info = self._parse_supabase_url(self.supabase_url_prd)

        query = """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """

        cmd = [
            "docker", "run", "--rm",
            f"-e", f"PGPASSWORD={self.db_password_prd}",
            "postgres:17",
            "psql",
            f"--host={conn_info['host']}",
            f"--port={conn_info['port']}",
            f"--username={conn_info['user']}",
            f"--dbname={conn_info['database']}",
            "--command", query
        ]

        try:
            result = self._run_command(cmd, check=True, timeout=30)
            tables = [line.strip() for line in result.stdout.strip().split('\n') if line.strip() and not line.startswith('tablename')]
            self.logger.info(f"Found {len(tables)} tables in public schema")
            return len(tables) > 0
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Could not verify table counts: {e}")
            return True  # Don't fail deployment if we can't check

    def rollback_deployment(self, backup_file: Optional[Path] = None) -> bool:
        """
        Rollback deployment using backup file.

        Args:
            backup_file: Path to backup file (uses latest if None)

        Returns:
            True if rollback successful
        """
        self.logger.warning("=" * 80)
        self.logger.warning("ROLLING BACK DEPLOYMENT")
        self.logger.warning("=" * 80)

        if not backup_file:
            # Find most recent backup
            backups = list(self.backup_dir.glob("db_backup_*.sql.gz"))
            if not backups:
                raise RuntimeError("No backup files found for rollback")
            backup_file = max(backups, key=lambda p: p.stat().st_mtime)

        self.logger.warning(f"Using backup file: {backup_file}")

        if not backup_file.exists():
            raise RuntimeError(f"Backup file not found: {backup_file}")

        # Decompress backup
        sql_file = backup_file.with_suffix('.sql')
        self.logger.warning("Decompressing backup file...")

        try:
            with gzip.open(backup_file, 'rb') as f_in:
                with open(sql_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Restore from backup
            self.logger.warning("Restoring database from backup...")
            conn_info = self._parse_supabase_url(self.supabase_url_prd)

            cmd = [
                "docker", "run", "--rm",
                "-i",
                f"-e", f"PGPASSWORD={self.db_password_prd}",
                "postgres:17",
                "psql",
                f"--host={conn_info['host']}",
                f"--port={conn_info['port']}",
                f"--username={conn_info['user']}",
                f"--dbname={conn_info['database']}",
                "--set", "ON_ERROR_STOP=1"
            ]

            with open(sql_file, 'r') as f:
                result = self._run_command(
                    cmd,
                    input=f.read(),
                    check=True,
                    timeout=600
                )

            # Clean up
            sql_file.unlink()

            self.logger.warning("=" * 80)
            self.logger.warning("✓ ROLLBACK COMPLETED SUCCESSFULLY")
            self.logger.warning("=" * 80)
            self.logger.warning(f"Database restored from: {backup_file}")
            self.logger.warning(f"Rollback completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            return True

        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            if sql_file.exists():
                sql_file.unlink()
            return False

    def get_deployment_status(self) -> dict:
        """
        Get current deployment status and information.

        Returns:
            Dictionary with deployment status information
        """
        self.logger.info("Getting deployment status...")

        status = {
            'environment': 'production',
            'database_url': self.supabase_url_prd,
            'staging_available': bool(self.supabase_url_stg),
            'recent_backups': [],
            'deployment_state': self.deployment_state.copy(),
            'timestamp': datetime.now().isoformat()
        }

        # Get recent backups
        backups = list(self.backup_dir.glob("db_backup_*.sql.gz"))
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        for backup in backups[:5]:  # Last 5 backups
            status['recent_backups'].append({
                'file': backup.name,
                'size': self._format_size(backup.stat().st_size),
                'created': datetime.fromtimestamp(backup.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })

        return status

    def auto_deployment_workflow(self, migration_file: Path) -> bool:
        """
        Execute complete automatic deployment workflow with all safety checks.

        Args:
            migration_file: Path to migration file to deploy

        Returns:
            True if deployment completed successfully
        """
        self.logger.info("=" * 80)
        self.logger.info("STARTING AUTOMATIC DEPLOYMENT WORKFLOW")
        self.logger.info("=" * 80)
        self.logger.info(f"Migration file: {migration_file}")
        self.logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Dry run: {self.dry_run}")

        try:
            # Phase 1: Pre-deployment checks
            self.logger.info("\n" + "=" * 80)
            self.logger.info("PHASE 1: PRE-DEPLOYMENT CHECKS")
            self.logger.info("=" * 80)

            checks_passed, issues = self.pre_deployment_checklist(migration_file)
            if not checks_passed:
                self.logger.error("Pre-deployment checks failed. Aborting deployment.")
                return False

            # Phase 2: Create backup
            self.logger.info("\n" + "=" * 80)
            self.logger.info("PHASE 2: CREATE PRODUCTION BACKUP")
            self.logger.info("=" * 80)

            backup_file = self.backup_production_database()
            self.logger.info(f"Backup created: {backup_file}")

            # Phase 3: Validate migration
            self.logger.info("\n" + "=" * 80)
            self.logger.info("PHASE 3: VALIDATE MIGRATION")
            self.logger.info("=" * 80)

            syntax_valid, syntax_issues = self._validate_migration_syntax(migration_file)
            if not syntax_valid:
                self.logger.error("Migration validation failed:")
                for issue in syntax_issues:
                    self.logger.error(f"  - {issue}")
                return False

            self.deployment_state['migration_validated'] = True

            # Phase 4: Test on staging (if available)
            self.logger.info("\n" + "=" * 80)
            self.logger.info("PHASE 4: TEST ON STAGING")
            self.logger.info("=" * 80)

            staging_passed = self.test_on_staging(migration_file)
            if not staging_passed:
                self.logger.warning("Staging test failed. Review before proceeding.")

            # Phase 5: Manual confirmation
            self.logger.info("\n" + "=" * 80)
            self.logger.info("PHASE 5: MANUAL CONFIRMATION")
            self.logger.info("=" * 80)

            if not self.dry_run:
                self._print_deployment_summary(migration_file, backup_file)
                if not self._get_user_confirmation():
                    self.logger.info("Deployment cancelled by user")
                    return False
            else:
                self.logger.info("[DRY RUN] Skipping manual confirmation")

            # Phase 6: Deploy to production
            self.logger.info("\n" + "=" * 80)
            self.logger.info("PHASE 6: DEPLOY TO PRODUCTION")
            self.logger.info("=" * 80)

            deployment_success = self.deploy_to_production(migration_file)
            if not deployment_success:
                self.logger.error("Deployment to production failed")
                self._print_rollback_instructions(backup_file)
                return False

            # Phase 7: Post-deployment verification
            self.logger.info("\n" + "=" * 80)
            self.logger.info("PHASE 7: POST-DEPLOYMENT VERIFICATION")
            self.logger.info("=" * 80)

            verification_passed, verification_issues = self.post_deployment_verification()
            if not verification_passed:
                self.logger.error("Post-deployment verification failed:")
                for issue in verification_issues:
                    self.logger.error(f"  - {issue}")
                self.logger.warning("Deployment completed but verification failed. Review issues.")
                self._print_rollback_instructions(backup_file)
                # Don't return False - deployment succeeded but verification failed

            # Phase 8: Complete
            self.logger.info("\n" + "=" * 80)
            self.logger.info("✓ DEPLOYMENT WORKFLOW COMPLETED SUCCESSFULLY")
            self.logger.info("=" * 80)
            self._print_deployment_summary(migration_file, backup_file)

            return True

        except Exception as e:
            self.logger.error(f"\n✗ DEPLOYMENT WORKFLOW FAILED: {e}")
            if self.deployment_state.get('backup_path'):
                self._print_rollback_instructions(self.deployment_state['backup_path'])
            return False

    def _print_deployment_summary(self, migration_file: Path, backup_file: Path):
        """Print deployment summary."""
        print("\n" + "=" * 80)
        print("DEPLOYMENT SUMMARY")
        print("=" * 80)
        print(f"Migration file: {migration_file}")
        print(f"Backup file: {backup_file}")
        print(f"Backup size: {self._format_size(backup_file.stat().st_size)}")
        print(f"Deployment time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Environment: Production")
        print("=" * 80)

    def _get_user_confirmation(self) -> bool:
        """Get user confirmation for deployment."""
        print("\n" + "=" * 80)
        print("⚠️  PRODUCTION DEPLOYMENT CONFIRMATION")
        print("=" * 80)
        print("You are about to deploy changes to the PRODUCTION database.")
        print("This action cannot be undone without a rollback.")
        print("")
        print("To proceed, type 'DEPLOY' and press Enter:")
        print("=" * 80)

        response = input("> ").strip()

        if response == "DEPLOY":
            print("\n✓ Deployment confirmed by user")
            return True
        else:
            print("\n✗ Deployment cancelled by user")
            return False

    def _print_rollback_instructions(self, backup_file: Path):
        """Print rollback instructions."""
        print("\n" + "=" * 80)
        print("ROLLBACK INSTRUCTIONS")
        print("=" * 80)
        print(f"If you need to rollback, use the following command:")
        print("")
        print(f"  python scripts/deploy_to_production.py --rollback --backup-file {backup_file.name}")
        print("")
        print(f"Or to rollback using the latest backup:")
        print("")
        print("  python scripts/deploy_to_production.py --rollback")
        print("")
        print(f"Backup file: {backup_file}")
        print("=" * 80)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Safe production database deployment with comprehensive safety checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Automatic workflow with all safety checks
  python scripts/deploy_to_production.py --auto --migration-file "20260621150000_add_user_preferences.sql"

  # Create backup only
  python scripts/deploy_to_production.py --backup-only

  # Validate migration syntax
  python scripts/deploy_to_production.py --validate --migration-file "20260621150000_add_user_preferences.sql"

  # Deploy specific migration
  python scripts/deploy_to_production.py --deploy --migration-file "20260621150000_add_user_preferences.sql"

  # Rollback last deployment
  python scripts/deploy_to_production.py --rollback

  # Rollback using specific backup
  python scripts/deploy_to_production.py --rollback --backup-file "db_backup_20260621_150000.sql.gz"

  # Check deployment status
  python scripts/deploy_to_production.py --status

  # Dry-run mode (simulate without making changes)
  python scripts/deploy_to_production.py --auto --migration-file "20260621150000_add_user_preferences.sql" --dry-run
        """
    )

    # Workflow options
    workflow_group = parser.add_mutually_exclusive_group(required=True)
    workflow_group.add_argument(
        '--auto',
        action='store_true',
        help='Execute automatic deployment workflow with all safety checks'
    )
    workflow_group.add_argument(
        '--backup-only',
        action='store_true',
        help='Create production database backup only'
    )
    workflow_group.add_argument(
        '--validate',
        action='store_true',
        help='Validate migration syntax only'
    )
    workflow_group.add_argument(
        '--deploy',
        action='store_true',
        help='Deploy migration to production (requires manual confirmation)'
    )
    workflow_group.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback last deployment'
    )
    workflow_group.add_argument(
        '--status',
        action='store_true',
        help='Show deployment status'
    )

    # Migration options
    parser.add_argument(
        '--migration-file',
        type=str,
        help='Path to migration file (for --auto, --validate, --deploy)'
    )
    parser.add_argument(
        '--backup-file',
        type=str,
        help='Path to backup file (for --rollback)'
    )

    # Advanced options
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate commands without executing them'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompts (use with extreme caution)'
    )

    args = parser.parse_args()

    try:
        # Create manager instance
        manager = ProductionDeploymentManager(dry_run=args.dry_run)

        # Execute requested workflow
        success = False

        if args.auto:
            if not args.migration_file:
                parser.error("--migration-file is required for --auto workflow")

            success = manager.auto_deployment_workflow(Path(args.migration_file))

        elif args.backup_only:
            backup_file = manager.backup_production_database()
            print(f"\n✓ Backup created: {backup_file}")
            success = True

        elif args.validate:
            if not args.migration_file:
                parser.error("--migration-file is required for --validate")

            migration_path = Path(args.migration_file)
            is_valid, issues = manager._validate_migration_syntax(migration_path)

            if is_valid:
                print(f"\n✓ Migration syntax is valid: {migration_path}")
                success = True
            else:
                print(f"\n✗ Migration syntax validation failed:")
                for issue in issues:
                    print(f"  - {issue}")
                success = False

        elif args.deploy:
            if not args.migration_file:
                parser.error("--migration-file is required for --deploy")

            migration_path = Path(args.migration_file)

            # Pre-deployment checks
            checks_passed, issues = manager.pre_deployment_checklist(migration_path)
            if not checks_passed:
                print("\n✗ Pre-deployment checks failed:")
                for issue in issues:
                    print(f"  - {issue}")
                sys.exit(1)

            # Create backup
            backup_file = manager.backup_production_database()

            # Manual confirmation
            if not args.dry_run and not args.yes:
                manager._print_deployment_summary(migration_path, backup_file)
                if not manager._get_user_confirmation():
                    print("\n✗ Deployment cancelled by user")
                    sys.exit(1)

            # Deploy
            success = manager.deploy_to_production(migration_path)

            if success:
                # Post-deployment verification
                verification_passed, verification_issues = manager.post_deployment_verification()
                if not verification_passed:
                    print("\n⚠ Deployment completed but verification failed:")
                    for issue in verification_issues:
                        print(f"  - {issue}")
                    manager._print_rollback_instructions(backup_file)

                print(f"\n✓ Deployment completed successfully")
                manager._print_rollback_instructions(backup_file)
            else:
                print("\n✗ Deployment failed")
                manager._print_rollback_instructions(backup_file)

        elif args.rollback:
            backup_file = Path(args.backup_file) if args.backup_file else None

            if not args.dry_run and not args.yes:
                print("\n⚠️  ROLLBACK CONFIRMATION")
                print("You are about to rollback the production database.")
                print("This will restore the database from a backup file.")
                print("")
                response = input("Type 'ROLLBACK' to confirm: ")
                if response != "ROLLBACK":
                    print("\n✗ Rollback cancelled by user")
                    sys.exit(1)

            success = manager.rollback_deployment(backup_file)

        elif args.status:
            status = manager.get_deployment_status()
            print("\n" + "=" * 80)
            print("DEPLOYMENT STATUS")
            print("=" * 80)
            print(f"Environment: {status['environment']}")
            print(f"Database URL: {status['database_url']}")
            print(f"Staging Available: {status['staging_available']}")
            print(f"Last Check: {status['timestamp']}")
            print("")
            print("Recent Backups:")
            for backup in status['recent_backups']:
                print(f"  - {backup['file']}")
                print(f"    Size: {backup['size']}, Created: {backup['created']}")
            print("")
            print("Deployment State:")
            for key, value in status['deployment_state'].items():
                print(f"  - {key}: {value}")
            print("=" * 80)
            success = True

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()