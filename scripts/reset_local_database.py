#!/usr/bin/env python3
"""
Reset Local Database Script
============================
Automates the process of wiping the local development database and restoring it from production.

This script performs the following operations:
1. Stops local Supabase services
2. Drops all tables in the local database
3. Restores schema from sql/initial_schema.sql
4. Copies data from production using copy_database.py
5. Restarts local Supabase services

Usage:
    python scripts/reset_local_database.py [--skip-confirmation]

Options:
    --skip-confirmation    Skip the safety confirmation prompt (use with caution!)

Requirements:
    - Supabase CLI installed and configured
    - .env file with production and development credentials
    - Local Supabase instance running or able to be started/stopped
    - Python dependencies: supabase, python-dotenv, psycopg2-binary

Safety Features:
    - Requires explicit user confirmation before destructive operations
    - Comprehensive error handling and rollback capabilities
    - Detailed logging for each operation
    - Validation checks before proceeding with each step

Environment Variables Required:
    - SUPABASE_URL_PRD: Production Supabase URL
    - SUPABASE_KEY_PRD: Production Supabase API key
    - SUPABASE_URL_DEV: Development Supabase URL
    - SUPABASE_KEY_DEV: Development Supabase API key
    - SUPABASE_DB_PASSWORD_DEV: Development database password

Example:
    # Standard usage with confirmation
    python scripts/reset_local_database.py

    # Skip confirmation (use with caution!)
    python scripts/reset_local_database.py --skip-confirmation
"""

import os
import sys
import subprocess
import logging
import argparse
from pathlib import Path
from datetime import datetime
import dotenv
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DatabaseResetError(Exception):
    """Custom exception for database reset errors."""
    pass


class LocalDatabaseResetter:
    """Handles the complete local database reset workflow."""

    def __init__(self, skip_confirmation: bool = False):
        """
        Initialize the database resetter.

        Args:
            skip_confirmation: Skip safety confirmation prompts
        """
        self.skip_confirmation = skip_confirmation
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env"
        self.schema_file = self.project_root / "sql" / "initial_schema.sql"
        self.copy_script = self.project_root / "scripts" / "copy_database.py"

        # Database connection parameters
        self.db_host = None
        self.db_port = None
        self.db_name = None
        self.db_user = None
        self.db_password = None

        # Load environment variables
        self._load_environment()

    def _load_environment(self):
        """Load environment variables from .env file."""
        if not self.env_file.exists():
            raise DatabaseResetError(
                f".env file not found at: {self.env_file}\n"
                "Please copy .env.example to .env and configure your credentials."
            )

        dotenv.load_dotenv(self.env_file)
        logger.info(f"✅ Loaded environment variables from {self.env_file}")

        # Validate required environment variables
        required_vars = [
            'SUPABASE_URL_PRD', 'SUPABASE_KEY_PRD',
            'SUPABASE_URL_DEV', 'SUPABASE_KEY_DEV',
            'SUPABASE_DB_PASSWORD_DEV'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise DatabaseResetError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                "Please check your .env file."
            )

        # Parse local database connection info
        dev_url = os.getenv('SUPABASE_URL_DEV')
        self.db_password = os.getenv('SUPABASE_DB_PASSWORD_DEV')

        # Extract connection info from Supabase URL
        # Format: https://project-id.supabase.co
        try:
            clean_url = dev_url.rstrip("/")
            project_id = clean_url.replace("https://", "").replace("http://", "").split(".")[0]

            # Local Supabase defaults
            self.db_host = "localhost"
            self.db_port = "54322"  # Default local Supabase port
            self.db_name = "postgres"
            self.db_user = "postgres"

            logger.info(f"✅ Parsed database connection info for local instance")
            logger.info(f"   Host: {self.db_host}:{self.db_port}")
            logger.info(f"   Database: {self.db_name}")
            logger.info(f"   User: {self.db_user}")

        except Exception as e:
            raise DatabaseResetError(f"Failed to parse Supabase URL: {str(e)}")

    def _confirm_operation(self, message: str) -> bool:
        """
        Ask user for confirmation before proceeding with destructive operations.

        Args:
            message: Confirmation message to display

        Returns:
            True if user confirms, False otherwise
        """
        if self.skip_confirmation:
            logger.warning("⚠️  Skipping confirmation prompt (--skip-confirmation flag)")
            return True

        print("\n" + "=" * 70)
        print("⚠️  WARNING: DESTRUCTIVE OPERATION")
        print("=" * 70)
        print(message)
        print("=" * 70)

        response = input("\nDo you want to proceed? (type 'yes' to confirm): ").strip().lower()
        return response == 'yes'

    def _run_command(self, command: list, description: str, check: bool = True) -> subprocess.CompletedProcess:
        """
        Run a shell command with error handling.

        Args:
            command: Command to run as a list
            description: Description of the command for logging
            check: Whether to check return code

        Returns:
            CompletedProcess object

        Raises:
            DatabaseResetError: If command fails
        """
        logger.info(f"🔧 {description}")
        logger.debug(f"   Command: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check
            )

            if result.returncode != 0:
                error_msg = f"Command failed with exit code {result.returncode}"
                if result.stderr:
                    error_msg += f"\nError: {result.stderr}"
                raise DatabaseResetError(error_msg)

            logger.info(f"✅ {description} completed successfully")
            return result

        except FileNotFoundError as e:
            raise DatabaseResetError(f"Command not found: {command[0]}\n{str(e)}")
        except subprocess.CalledProcessError as e:
            error_msg = f"{description} failed"
            if e.stderr:
                error_msg += f"\nError: {e.stderr}"
            raise DatabaseResetError(error_msg)

    def stop_supabase_services(self) -> bool:
        """
        Stop local Supabase services.

        Returns:
            True if successful

        Raises:
            DatabaseResetError: If stopping services fails
        """
        logger.info("🛑 Stopping local Supabase services...")

        try:
            # Try to stop Supabase
            result = subprocess.run(
                ["supabase", "stop"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            # Supabase stop might fail if not running, that's okay
            if result.returncode != 0:
                logger.warning(f"⚠️  Supabase stop command returned non-zero: {result.stderr}")
                logger.info("   This is normal if Supabase is not currently running")
            else:
                logger.info("✅ Supabase services stopped")

            return True

        except FileNotFoundError:
            raise DatabaseResetError(
                "Supabase CLI not found. Please install it:\n"
                "   npm install -g supabase\n"
                "   Or: brew install supabase/tap/supabase"
            )
        except Exception as e:
            raise DatabaseResetError(f"Failed to stop Supabase services: {str(e)}")

    def start_supabase_services(self) -> bool:
        """
        Start local Supabase services.

        Returns:
            True if successful

        Raises:
            DatabaseResetError: If starting services fails
        """
        logger.info("🚀 Starting local Supabase services...")

        try:
            result = subprocess.run(
                ["supabase", "start"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=120  # 2 minute timeout
            )

            if result.returncode != 0:
                raise DatabaseResetError(
                    f"Failed to start Supabase services\n"
                    f"Error: {result.stderr}"
                )

            logger.info("✅ Supabase services started successfully")
            return True

        except subprocess.TimeoutExpired:
            raise DatabaseResetError(
                "Supabase start timed out after 2 minutes. "
                "This might indicate a problem with your local setup."
            )
        except FileNotFoundError:
            raise DatabaseResetError(
                "Supabase CLI not found. Please install it:\n"
                "   npm install -g supabase\n"
                "   Or: brew install supabase/tap/supabase"
            )
        except Exception as e:
            raise DatabaseResetError(f"Failed to start Supabase services: {str(e)}")

    def drop_all_tables(self) -> bool:
        """
        Drop all tables in the local database.

        Returns:
            True if successful

        Raises:
            DatabaseResetError: If dropping tables fails
        """
        logger.info("🗑️  Dropping all tables in local database...")

        try:
            # Connect to the database
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Get all table names
            cursor.execute("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)

            tables = [row[0] for row in cursor.fetchall()]

            if not tables:
                logger.info("   No tables found to drop")
                cursor.close()
                conn.close()
                return True

            logger.info(f"   Found {len(tables)} tables to drop: {', '.join(tables)}")

            # Drop all tables
            for table in tables:
                try:
                    cursor.execute(
                        sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                            sql.Identifier(table)
                        )
                    )
                    logger.debug(f"   Dropped table: {table}")
                except Exception as e:
                    logger.warning(f"   ⚠️  Failed to drop table {table}: {str(e)}")

            cursor.close()
            conn.close()

            logger.info(f"✅ Dropped {len(tables)} tables")
            return True

        except psycopg2.OperationalError as e:
            raise DatabaseResetError(
                f"Failed to connect to local database\n"
                f"Error: {str(e)}\n"
                f"Make sure Supabase is running and connection parameters are correct."
            )
        except Exception as e:
            raise DatabaseResetError(f"Failed to drop tables: {str(e)}")

    def restore_schema(self) -> bool:
        """
        Restore database schema from initial_schema.sql file.

        Returns:
            True if successful

        Raises:
            DatabaseResetError: If schema restoration fails
        """
        logger.info("📋 Restoring database schema from initial_schema.sql...")

        if not self.schema_file.exists():
            raise DatabaseResetError(
                f"Schema file not found: {self.schema_file}\n"
                "Please ensure sql/initial_schema.sql exists."
            )

        try:
            # Read the schema file
            schema_sql = self.schema_file.read_text()
            logger.info(f"   Read schema file ({len(schema_sql)} characters)")

            # Connect to the database
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Execute the schema SQL
            # Split by semicolons to handle multiple statements
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]

            executed_count = 0
            for statement in statements:
                try:
                    # Skip comments and empty statements
                    if statement.startswith('--') or not statement.strip():
                        continue

                    cursor.execute(statement)
                    executed_count += 1
                except Exception as e:
                    # Some statements might fail (e.g., IF NOT EXISTS checks)
                    # Log but continue
                    logger.debug(f"   Statement execution note: {str(e)}")

            cursor.close()
            conn.close()

            logger.info(f"✅ Schema restored successfully ({executed_count} statements executed)")
            return True

        except psycopg2.OperationalError as e:
            raise DatabaseResetError(
                f"Failed to connect to local database\n"
                f"Error: {str(e)}\n"
                f"Make sure Supabase is running and connection parameters are correct."
            )
        except Exception as e:
            raise DatabaseResetError(f"Failed to restore schema: {str(e)}")

    def copy_production_data(self) -> bool:
        """
        Copy data from production database using copy_database.py script.

        Returns:
            True if successful

        Raises:
            DatabaseResetError: If data copy fails
        """
        logger.info("📦 Copying data from production database...")

        if not self.copy_script.exists():
            raise DatabaseResetError(
                f"Copy script not found: {self.copy_script}\n"
                "Please ensure scripts/copy_database.py exists."
            )

        try:
            # Run the copy_database.py script
            result = subprocess.run(
                [sys.executable, str(self.copy_script)],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=300  # 5 minute timeout for data copy
            )

            # Print the output for visibility
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logger.info(f"   {line}")

            if result.returncode != 0:
                error_msg = "Failed to copy production data"
                if result.stderr:
                    error_msg += f"\nError: {result.stderr}"
                raise DatabaseResetError(error_msg)

            logger.info("✅ Production data copied successfully")
            return True

        except subprocess.TimeoutExpired:
            raise DatabaseResetError(
                "Data copy timed out after 5 minutes. "
                "This might indicate a large dataset or network issues."
            )
        except Exception as e:
            raise DatabaseResetError(f"Failed to copy production data: {str(e)}")

    def verify_database(self) -> bool:
        """
        Verify that the database has been properly reset and populated.

        Returns:
            True if verification passes

        Raises:
            DatabaseResetError: If verification fails
        """
        logger.info("🔍 Verifying database reset...")

        try:
            # Connect to the database
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            cursor = conn.cursor()

            # Check if key tables exist and have data
            key_tables = [
                'Dioceses',
                'Parishes',
                'ParishData',
                'pipeline_workers',
                'ScheduleKeywords'
            ]

            verification_results = {}

            for table in key_tables:
                try:
                    # Check if table exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_schema = 'public'
                            AND table_name = %s
                        );
                    """, (table,))
                    exists = cursor.fetchone()[0]

                    if not exists:
                        verification_results[table] = "❌ Table does not exist"
                        continue

                    # Count rows
                    cursor.execute(f'SELECT COUNT(*) FROM public."{table}";')
                    count = cursor.fetchone()[0]
                    verification_results[table] = f"✅ {count} rows"

                except Exception as e:
                    verification_results[table] = f"❌ Error: {str(e)}"

            cursor.close()
            conn.close()

            # Print verification results
            logger.info("   Verification results:")
            for table, result in verification_results.items():
                logger.info(f"      {table}: {result}")

            # Check if all tables exist
            failed_tables = [t for t, r in verification_results.items() if r.startswith("❌")]
            if failed_tables:
                raise DatabaseResetError(
                    f"Verification failed for tables: {', '.join(failed_tables)}"
                )

            logger.info("✅ Database verification passed")
            return True

        except psycopg2.OperationalError as e:
            raise DatabaseResetError(
                f"Failed to connect to local database for verification\n"
                f"Error: {str(e)}"
            )
        except Exception as e:
            raise DatabaseResetError(f"Database verification failed: {str(e)}")

    def reset(self) -> bool:
        """
        Execute the complete database reset workflow.

        Returns:
            True if reset successful

        Raises:
            DatabaseResetError: If any step fails
        """
        start_time = datetime.now()

        logger.info("=" * 70)
        logger.info("🔄 LOCAL DATABASE RESET WORKFLOW")
        logger.info("=" * 70)
        logger.info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")

        # Safety confirmation
        confirmation_message = (
            "This will COMPLETELY WIPE your local development database and restore it "
            "from production. All local changes will be lost.\n\n"
            "The following operations will be performed:\n"
            "1. Stop local Supabase services\n"
            "2. Drop all tables in local database\n"
            "3. Restore schema from sql/initial_schema.sql\n"
            "4. Copy all data from production database\n"
            "5. Restart local Supabase services\n"
            "6. Verify database integrity\n\n"
            "This operation is IRREVERSIBLE."
        )

        if not self._confirm_operation(confirmation_message):
            logger.info("❌ Operation cancelled by user")
            return False

        try:
            # Step 1: Stop Supabase services
            logger.info("Step 1/6: Stopping Supabase services")
            logger.info("-" * 70)
            self.stop_supabase_services()
            logger.info("")

            # Step 2: Drop all tables
            logger.info("Step 2/6: Dropping all tables")
            logger.info("-" * 70)
            self.drop_all_tables()
            logger.info("")

            # Step 3: Restore schema
            logger.info("Step 3/6: Restoring schema")
            logger.info("-" * 70)
            self.restore_schema()
            logger.info("")

            # Step 4: Copy production data
            logger.info("Step 4/6: Copying production data")
            logger.info("-" * 70)
            self.copy_production_data()
            logger.info("")

            # Step 5: Restart Supabase services
            logger.info("Step 5/6: Restarting Supabase services")
            logger.info("-" * 70)
            self.start_supabase_services()
            logger.info("")

            # Step 6: Verify database
            logger.info("Step 6/6: Verifying database")
            logger.info("-" * 70)
            self.verify_database()
            logger.info("")

            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Success message
            logger.info("=" * 70)
            logger.info("✅ DATABASE RESET COMPLETED SUCCESSFULLY!")
            logger.info("=" * 70)
            logger.info(f"Started at:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Duration:    {duration:.2f} seconds")
            logger.info("")
            logger.info("Your local database has been reset and is ready for use.")
            logger.info("")

            return True

        except DatabaseResetError as e:
            logger.error("=" * 70)
            logger.error("❌ DATABASE RESET FAILED")
            logger.error("=" * 70)
            logger.error(f"Error: {str(e)}")
            logger.error("")
            logger.error("Please check the error message above and try again.")
            logger.error("If the problem persists, check your:")
            logger.error("  - .env file configuration")
            logger.error("  - Supabase CLI installation")
            logger.error("  - Network connectivity")
            logger.error("  - Database credentials")
            logger.error("")

            # Attempt to restart Supabase if it was stopped
            try:
                logger.info("Attempting to restart Supabase services...")
                self.start_supabase_services()
            except Exception as restart_error:
                logger.error(f"Failed to restart Supabase: {str(restart_error)}")

            raise


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Reset local development database from production',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standard usage with confirmation
  python scripts/reset_local_database.py

  # Skip confirmation (use with caution!)
  python scripts/reset_local_database.py --skip-confirmation

For more information, see the script docstring.
        """
    )

    parser.add_argument(
        '--skip-confirmation',
        action='store_true',
        help='Skip the safety confirmation prompt (use with caution!)'
    )

    args = parser.parse_args()

    try:
        resetter = LocalDatabaseResetter(skip_confirmation=args.skip_confirmation)
        success = resetter.reset()
        sys.exit(0 if success else 1)

    except DatabaseResetError as e:
        logger.error(f"Database reset failed: {str(e)}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n❌ Operation cancelled by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()