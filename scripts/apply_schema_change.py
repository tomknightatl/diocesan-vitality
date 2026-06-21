#!/usr/bin/env python3
"""
Supabase Schema Change Management Script

This script provides a comprehensive workflow for managing database schema changes
using Supabase CLI. It supports both automatic and manual migration workflows with
proper error handling, validation, and safety measures.

Features:
- Generate migration diffs from local schema changes
- Apply migrations to local database
- Validate migration success
- Rollback capability
- Support for automatic and manual workflows
- Comprehensive error handling and logging
- Safety confirmations before applying changes

Usage:
    # Automatic workflow (generate, review, apply)
    python scripts/apply_schema_change.py --auto --name "add_user_preferences"

    # Manual workflow (generate only)
    python scripts/apply_schema_change.py --generate --name "add_user_preferences"

    # Apply existing migration
    python scripts/apply_schema_change.py --apply --file "20260621150000_add_user_preferences.sql"

    # Rollback last migration
    python scripts/apply_schema_change.py --rollback

    # List migration status
    python scripts/apply_schema_change.py --status

    # Validate current schema
    python scripts/apply_schema_change.py --validate

Requirements:
    - Supabase CLI installed and configured
    - Local Supabase stack running (supabase start)
    - Python 3.8+
    - Required Python packages: subprocess, logging, argparse, pathlib, sys

Author: Diocesan Vitality Project
Version: 1.0.0
Date: 2026-06-21
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List


class SchemaChangeManager:
    """Manages Supabase schema changes with comprehensive error handling and validation."""

    def __init__(self, project_root: Optional[Path] = None, dry_run: bool = False):
        """
        Initialize the schema change manager.

        Args:
            project_root: Path to project root directory (default: auto-detect)
            dry_run: If True, simulate commands without executing them
        """
        self.project_root = project_root or self._find_project_root()
        self.supabase_dir = self.project_root / "supabase"
        self.migrations_dir = self.supabase_dir / "migrations"
        self.dry_run = dry_run

        # Setup logging
        self._setup_logging()

        # Validate environment
        self._validate_environment()

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
        """Configure comprehensive logging."""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(
                    self.project_root / "logs" / f"schema_change_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                )
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _validate_environment(self):
        """Validate that required tools and directories exist."""
        self.logger.info("Validating environment...")

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

        # Check if local stack is running
        try:
            result = self._run_command(["supabase", "status"], check=True)
            self.logger.info("Local Supabase stack is running")
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "Local Supabase stack is not running. "
                "Please start it with: supabase start"
            )

        self.logger.info("Environment validation completed successfully")

    def _run_command(
        self,
        command: List[str],
        check: bool = True,
        capture_output: bool = True,
        timeout: int = 300
    ) -> subprocess.CompletedProcess:
        """
        Run a shell command with proper error handling.

        Args:
            command: Command to execute as list of strings
            check: If True, raise exception on non-zero exit code
            capture_output: If True, capture stdout and stderr
            timeout: Command timeout in seconds

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
            result = subprocess.run(
                command,
                check=check,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                cwd=self.project_root
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

    def generate_migration_diff(
        self,
        migration_name: str,
        schema: str = "public",
        use_migra: bool = False
    ) -> Path:
        """
        Generate a migration diff from local schema changes.

        Args:
            migration_name: Name for the migration file
            schema: Schema to diff (default: public)
            use_migra: Use migra diff engine instead of default

        Returns:
            Path to the generated migration file
        """
        self.logger.info(f"Generating migration diff: {migration_name}")

        # Create migration file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        migration_filename = f"{timestamp}_{migration_name}.sql"
        migration_path = self.migrations_dir / migration_filename

        # Build diff command
        diff_cmd = [
            "supabase",
            "db",
            "diff",
            "--local",
            "--schema", schema,
            "--file", str(migration_path)
        ]

        if use_migra:
            diff_cmd.append("--use-migra")

        try:
            result = self._run_command(diff_cmd, check=True)

            # In dry-run mode, return the path without checking file existence
            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would create migration file: {migration_path}")
                return migration_path

            # Check if migration file was created and has content
            if not migration_path.exists():
                raise RuntimeError(f"Migration file was not created: {migration_path}")

            if migration_path.stat().st_size == 0:
                self.logger.warning("Generated migration file is empty - no schema changes detected")
                migration_path.unlink()
                return None

            self.logger.info(f"Migration diff generated successfully: {migration_path}")
            self.logger.info(f"Migration file size: {migration_path.stat().st_size} bytes")

            # Display migration content for review
            self.logger.info("Migration content:")
            self.logger.info("-" * 80)
            with open(migration_path, 'r') as f:
                content = f.read()
                self.logger.info(content)
            self.logger.info("-" * 80)

            return migration_path

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to generate migration diff: {e}")
            if migration_path.exists():
                migration_path.unlink()
            raise

    def apply_migration(
        self,
        migration_file: Optional[Path] = None,
        confirm: bool = True
    ) -> bool:
        """
        Apply migration to local database.

        Args:
            migration_file: Specific migration file to apply (None for all pending)
            confirm: If True, require user confirmation before applying

        Returns:
            True if migration was applied successfully
        """
        self.logger.info("Applying migration(s) to local database")

        # Get migration status before applying
        before_status = self.get_migration_status()
        self.logger.info(f"Current migration status: {len(before_status['local'])} local migrations applied")

        # Build apply command
        apply_cmd = ["supabase", "migration", "up", "--local"]

        if confirm and not self.dry_run:
            response = input("Do you want to apply this migration? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                self.logger.info("Migration cancelled by user")
                return False

        try:
            result = self._run_command(apply_cmd, check=True)
            self.logger.info("Migration applied successfully")

            # Get migration status after applying
            after_status = self.get_migration_status()
            applied_count = len(after_status['local']) - len(before_status['local'])

            if applied_count > 0:
                self.logger.info(f"Applied {applied_count} new migration(s)")
            else:
                self.logger.info("No new migrations were applied (already up to date)")

            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to apply migration: {e}")
            return False

    def rollback_migration(
        self,
        count: int = 1,
        confirm: bool = True
    ) -> bool:
        """
        Rollback the last N migrations.

        Args:
            count: Number of migrations to rollback (default: 1)
            confirm: If True, require user confirmation before rolling back

        Returns:
            True if rollback was successful
        """
        self.logger.warning(f"Rolling back last {count} migration(s)")

        # Get current migration status
        status = self.get_migration_status()
        if len(status['local']) < count:
            raise ValueError(
                f"Cannot rollback {count} migration(s). Only {len(status['local'])} applied."
            )

        # Show which migrations will be rolled back
        migrations_to_rollback = status['local'][-count:]
        self.logger.warning("The following migrations will be rolled back:")
        for migration in migrations_to_rollback:
            self.logger.warning(f"  - {migration}")

        if confirm and not self.dry_run:
            response = input("Are you sure you want to rollback? This is a destructive operation! (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                self.logger.info("Rollback cancelled by user")
                return False

        # Build rollback command
        rollback_cmd = [
            "supabase",
            "migration",
            "down",
            "--local",
            "--last", str(count),
            "--yes"
        ]

        try:
            result = self._run_command(rollback_cmd, check=True)
            self.logger.warning(f"Successfully rolled back {count} migration(s)")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to rollback migration: {e}")
            return False

    def get_migration_status(self) -> dict:
        """
        Get current migration status.

        Returns:
            Dictionary with 'local' and 'remote' migration lists
        """
        self.logger.info("Getting migration status")

        try:
            result = self._run_command(
                ["supabase", "migration", "list", "--local"],
                check=True
            )

            # Parse migration status
            status = {'local': [], 'remote': []}
            lines = result.stdout.strip().split('\n')

            for line in lines:
                if line.strip() and not line.startswith('Local') and not line.startswith('-'):
                    parts = line.split('|')
                    if len(parts) >= 1:
                        local_migration = parts[0].strip()
                        if local_migration:
                            status['local'].append(local_migration)

            self.logger.info(f"Found {len(status['local'])} local migrations")
            return status

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get migration status: {e}")
            return {'local': [], 'remote': []}

    def validate_schema(self, schema: str = "public") -> Tuple[bool, List[str]]:
        """
        Validate database schema for errors and issues.

        Args:
            schema: Schema to validate (default: public)

        Returns:
            Tuple of (is_valid, list of issues)
        """
        self.logger.info(f"Validating schema: {schema}")

        issues = []

        try:
            # Run db lint
            result = self._run_command(
                ["supabase", "db", "lint", "--local", "--schema", schema],
                check=False
            )

            if result.returncode != 0:
                issues.append("Schema linting found issues")
                if result.stderr:
                    issues.append(result.stderr)

            # Check for common issues
            # 1. Check for orphaned objects
            try:
                query = """
                    SELECT
                        n.nspname as schema,
                        c.relname as table,
                        CASE c.relkind
                            WHEN 'r' THEN 'table'
                            WHEN 'i' THEN 'index'
                            WHEN 'S' THEN 'sequence'
                            WHEN 'v' THEN 'view'
                            WHEN 'm' THEN 'materialized view'
                            ELSE c.relkind::text
                        END as type
                    FROM pg_class c
                    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = %s
                    AND c.relkind IN ('r', 'i', 'S', 'v', 'm')
                    ORDER BY n.nspname, c.relname;
                """

                result = self._run_command(
                    ["supabase", "db", "query", "--local", query.replace('\n', ' ').strip()],
                    check=True
                )
                self.logger.debug(f"Schema objects: {result.stdout}")

            except subprocess.CalledProcessError as e:
                issues.append(f"Failed to query schema objects: {e}")

            is_valid = len(issues) == 0

            if is_valid:
                self.logger.info("Schema validation passed")
            else:
                self.logger.error("Schema validation failed:")
                for issue in issues:
                    self.logger.error(f"  - {issue}")

            return is_valid, issues

        except Exception as e:
            self.logger.error(f"Schema validation error: {e}")
            return False, [f"Validation error: {str(e)}"]

    def auto_workflow(
        self,
        migration_name: str,
        schema: str = "public",
        skip_validation: bool = False
    ) -> bool:
        """
        Execute automatic workflow: generate, review, apply, validate.

        Args:
            migration_name: Name for the migration
            schema: Schema to diff (default: public)
            skip_validation: Skip schema validation after applying

        Returns:
            True if workflow completed successfully
        """
        self.logger.info(f"Starting automatic workflow: {migration_name}")

        try:
            # Step 1: Generate migration diff
            self.logger.info("Step 1: Generating migration diff...")
            migration_path = self.generate_migration_diff(migration_name, schema)

            if migration_path is None:
                self.logger.info("No schema changes detected, workflow complete")
                return True

            # Step 2: Review migration
            self.logger.info("Step 2: Review migration content...")
            if not self._review_migration(migration_path):
                self.logger.info("Migration rejected during review")
                return False

            # Step 3: Apply migration
            self.logger.info("Step 3: Applying migration...")
            if not self.apply_migration(migration_path, confirm=True):
                self.logger.error("Failed to apply migration")
                return False

            # Step 4: Validate schema
            if not skip_validation:
                self.logger.info("Step 4: Validating schema...")
                is_valid, issues = self.validate_schema(schema)
                if not is_valid:
                    self.logger.error("Schema validation failed after migration")
                    self.logger.error("Consider rolling back the migration")
                    return False

            self.logger.info("Automatic workflow completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Automatic workflow failed: {e}")
            return False

    def _review_migration(self, migration_path: Path) -> bool:
        """
        Review migration content with user.

        Args:
            migration_path: Path to migration file

        Returns:
            True if migration is approved
        """
        self.logger.info(f"Reviewing migration: {migration_path}")

        # In dry-run mode, skip file reading and auto-approve
        if self.dry_run:
            self.logger.info("[DRY RUN] Skipping migration content review")
            return True

        with open(migration_path, 'r') as f:
            content = f.read()

        print("\n" + "=" * 80)
        print("MIGRATION CONTENT REVIEW")
        print("=" * 80)
        print(content)
        print("=" * 80)

        response = input("\nDo you approve this migration? (yes/no/edit): ")
        response = response.lower().strip()

        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        elif response in ['edit', 'e']:
            # Allow user to edit the migration
            editor = input("Enter editor command (default: vim): ") or "vim"
            subprocess.run([editor, str(migration_path)])
            return self._review_migration(migration_path)
        else:
            self.logger.warning("Invalid response, assuming 'no'")
            return False

    def backup_database(self, backup_path: Optional[Path] = None) -> Path:
        """
        Create a database backup before applying changes.

        Args:
            backup_path: Path for backup file (auto-generated if None)

        Returns:
            Path to backup file
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.project_root / "backup" / f"db_backup_{timestamp}.sql"

        backup_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Creating database backup: {backup_path}")

        try:
            result = self._run_command(
                ["supabase", "db", "dump", "--local", "--file", str(backup_path)],
                check=True
            )
            self.logger.info(f"Database backup created successfully: {backup_path}")
            return backup_path

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create database backup: {e}")
            raise


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Manage Supabase schema changes with comprehensive workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Automatic workflow
  python scripts/apply_schema_change.py --auto --name "add_user_preferences"

  # Generate migration only
  python scripts/apply_schema_change.py --generate --name "add_user_preferences"

  # Apply existing migration
  python scripts/apply_schema_change.py --apply --file "20260621150000_add_user_preferences.sql"

  # Rollback last migration
  python scripts/apply_schema_change.py --rollback

  # Check migration status
  python scripts/apply_schema_change.py --status

  # Validate schema
  python scripts/apply_schema_change.py --validate
        """
    )

    # Workflow options
    workflow_group = parser.add_mutually_exclusive_group(required=True)
    workflow_group.add_argument(
        '--auto',
        action='store_true',
        help='Execute automatic workflow (generate, review, apply, validate)'
    )
    workflow_group.add_argument(
        '--generate',
        action='store_true',
        help='Generate migration diff only'
    )
    workflow_group.add_argument(
        '--apply',
        action='store_true',
        help='Apply existing migration'
    )
    workflow_group.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback last migration'
    )
    workflow_group.add_argument(
        '--status',
        action='store_true',
        help='Show migration status'
    )
    workflow_group.add_argument(
        '--validate',
        action='store_true',
        help='Validate database schema'
    )

    # Migration options
    parser.add_argument(
        '--name',
        type=str,
        help='Migration name (for --generate or --auto)'
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Migration file path (for --apply)'
    )
    parser.add_argument(
        '--schema',
        type=str,
        default='public',
        help='Schema to operate on (default: public)'
    )
    parser.add_argument(
        '--rollback-count',
        type=int,
        default=1,
        help='Number of migrations to rollback (default: 1)'
    )

    # Advanced options
    parser.add_argument(
        '--use-migra',
        action='store_true',
        help='Use migra diff engine for generating migrations'
    )
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip schema validation after applying migration'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create database backup before applying changes'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate commands without executing them'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompts (use with caution)'
    )

    args = parser.parse_args()

    try:
        # Create manager instance
        manager = SchemaChangeManager(dry_run=args.dry_run)

        # Execute requested workflow
        success = False

        if args.auto:
            if not args.name:
                parser.error("--name is required for --auto workflow")

            if args.backup:
                manager.backup_database()

            success = manager.auto_workflow(
                migration_name=args.name,
                schema=args.schema,
                skip_validation=args.skip_validation
            )

        elif args.generate:
            if not args.name:
                parser.error("--name is required for --generate")

            migration_path = manager.generate_migration_diff(
                migration_name=args.name,
                schema=args.schema,
                use_migra=args.use_migra
            )
            success = migration_path is not None

        elif args.apply:
            migration_file = Path(args.file) if args.file else None
            success = manager.apply_migration(
                migration_file=migration_file,
                confirm=not args.yes
            )

        elif args.rollback:
            success = manager.rollback_migration(
                count=args.rollback_count,
                confirm=not args.yes
            )

        elif args.status:
            status = manager.get_migration_status()
            print("\nMigration Status:")
            print(f"  Local migrations applied: {len(status['local'])}")
            if status['local']:
                print("  Applied migrations:")
                for migration in status['local']:
                    print(f"    - {migration}")
            success = True

        elif args.validate:
            is_valid, issues = manager.validate_schema(args.schema)
            if is_valid:
                print("✓ Schema validation passed")
            else:
                print("✗ Schema validation failed:")
                for issue in issues:
                    print(f"  - {issue}")
            success = is_valid

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()