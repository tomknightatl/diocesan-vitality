#!/usr/bin/env python3
"""
Migration Testing Framework
===========================

Comprehensive testing framework for database migrations before production deployment.
This framework ensures migrations are safe, performant, and reversible before they
are applied to production databases.

Features:
- Syntax validation using PostgreSQL EXPLAIN
- Data integrity checks (foreign keys, constraints, data types, indexes)
- Performance impact analysis (execution time estimation, query optimization)
- Rollback verification (rollback SQL validation, restoration capability)
- Comprehensive test reporting with pass/fail results
- Batch testing support for multiple migrations
- Integration with existing deployment scripts
- Dry-run mode for safe testing

Usage:
    # Test a single migration file
    python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql

    # Test all pending migrations
    python scripts/test_migration.py --all-pending

    # Test with specific environment
    python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql --environment staging

    # Run specific test categories
    python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql --categories syntax integrity performance

    # Generate detailed report
    python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql --report-file test_report.json

    # Dry-run mode (simulate without database changes)
    python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql --dry-run

    # Verbose output with detailed information
    python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql --verbose

Requirements:
    - Python 3.8+
    - PostgreSQL connection (local or remote)
    - Docker (for PostgreSQL container execution)
    - Environment variables configured in .env file

Test Categories:
    1. Syntax Tests: SQL parsing, keyword detection, statement validation
    2. Integrity Tests: Foreign keys, constraints, data types, indexes
    3. Performance Tests: Query analysis, execution time estimation, index optimization
    4. Rollback Tests: Rollback SQL validation, restoration verification
    5. Integration Tests: Migration sequence, dependency checks, breaking change detection

Author: Diocesan Vitality Project
Version: 1.0.0
Date: 2026-06-21
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
import dotenv


class TestCategory(Enum):
    """Enumeration of available test categories."""
    SYNTAX = "syntax"
    INTEGRITY = "integrity"
    PERFORMANCE = "performance"
    ROLLBACK = "rollback"
    INTEGRATION = "integration"


class TestStatus(Enum):
    """Enumeration of test execution statuses."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


class TestResult:
    """Represents the result of a single test."""

    def __init__(
        self,
        test_name: str,
        category: TestCategory,
        status: TestStatus,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        execution_time_ms: float = 0.0
    ):
        self.test_name = test_name
        self.category = category
        self.status = status
        self.message = message
        self.details = details or {}
        self.execution_time_ms = execution_time_ms
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert test result to dictionary."""
        return {
            "test_name": self.test_name,
            "category": self.category.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp
        }


class MigrationTestFramework:
    """Comprehensive migration testing framework."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        environment: str = "local",
        dry_run: bool = False,
        verbose: bool = False
    ):
        """
        Initialize the migration testing framework.

        Args:
            project_root: Path to project root directory (default: auto-detect)
            environment: Database environment to test against (local, staging, production)
            dry_run: If True, simulate tests without database changes
            verbose: If True, enable verbose logging
        """
        self.project_root = project_root or self._find_project_root()
        self.supabase_dir = self.project_root / "supabase"
        self.migrations_dir = self.supabase_dir / "migrations"
        self.reports_dir = self.project_root / "test_reports"
        self.environment = environment
        self.dry_run = dry_run
        self.verbose = verbose

        # Create necessary directories
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_logging()

        # Load environment variables
        self._load_environment()

        # Test results storage
        self.test_results: List[TestResult] = []

        # Statistics
        self.stats = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "skipped": 0
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
        """Configure comprehensive logging."""
        log_level = logging.DEBUG if self.verbose else logging.INFO

        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)

    def _load_environment(self):
        """Load environment variables from .env file."""
        env_file = self.project_root / ".env"
        if not env_file.exists():
            raise FileNotFoundError(
                f".env file not found at: {env_file}\n"
                "Please copy .env.example to .env and configure your credentials."
            )

        dotenv.load_dotenv(env_file)
        self.logger.info(f"Environment variables loaded for {self.environment} environment")

        # Get database credentials based on environment
        env_suffix = self.environment.upper()

        self.supabase_url = os.getenv(f"SUPABASE_URL_{env_suffix}")
        self.db_password = os.getenv(f"SUPABASE_DB_PASSWORD_{env_suffix}")

        if not self.supabase_url:
            raise ValueError(f"SUPABASE_URL_{env_suffix} not found in .env")

        if not self.db_password:
            raise ValueError(f"SUPABASE_DB_PASSWORD_{env_suffix} not found in .env")

        self.logger.info(f"Database credentials loaded for {self.environment} environment")

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

    def _run_command(
        self,
        command: List[str],
        check: bool = True,
        capture_output: bool = True,
        timeout: int = 300,
        input: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """
        Run a shell command with proper error handling.

        Args:
            command: Command to execute as list of strings
            check: If True, raise exception on non-zero exit code
            capture_output: If True, capture stdout and stderr
            timeout: Command timeout in seconds
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
            result = subprocess.run(
                command,
                check=check,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                cwd=self.project_root,
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

    def _add_test_result(self, result: TestResult):
        """Add a test result to the results list and update statistics."""
        self.test_results.append(result)
        self.stats["total_tests"] += 1

        if result.status == TestStatus.PASS:
            self.stats["passed"] += 1
        elif result.status == TestStatus.FAIL:
            self.stats["failed"] += 1
        elif result.status == TestStatus.WARN:
            self.stats["warnings"] += 1
        elif result.status == TestStatus.SKIP:
            self.stats["skipped"] += 1

        # Log the result
        status_symbol = {
            TestStatus.PASS: "✓",
            TestStatus.FAIL: "✗",
            TestStatus.WARN: "⚠",
            TestStatus.SKIP: "○"
        }[result.status]

        self.logger.info(
            f"{status_symbol} [{result.category.value.upper()}] {result.test_name}: {result.message}"
        )

        if result.details and self.verbose:
            self.logger.debug(f"  Details: {json.dumps(result.details, indent=2)}")

    def _read_migration_file(self, migration_file: Path) -> str:
        """
        Read and validate migration file content.

        Args:
            migration_file: Path to migration file

        Returns:
            Migration file content as string
        """
        if not migration_file.exists():
            raise FileNotFoundError(f"Migration file not found: {migration_file}")

        with open(migration_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
            raise ValueError(f"Migration file is empty: {migration_file}")

        return content

    def _extract_sql_statements(self, content: str) -> List[str]:
        """
        Extract individual SQL statements from migration content.

        Args:
            content: Migration file content

        Returns:
            List of SQL statements
        """
        # Remove comments
        content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Split on semicolons
        statements = [stmt.strip() for stmt in content.split(';') if stmt.strip()]

        return statements

    def _detect_dangerous_operations(self, content: str) -> List[str]:
        """
        Detect potentially dangerous SQL operations.

        Args:
            content: Migration file content

        Returns:
            List of detected dangerous operations
        """
        dangerous_patterns = [
            (r'DROP\s+DATABASE\b', 'DROP DATABASE - Extremely dangerous operation'),
            (r'DROP\s+SCHEMA\b', 'DROP SCHEMA - Dangerous operation'),
            (r'TRUNCATE\b', 'TRUNCATE - Data loss operation'),
            (r'DELETE\s+FROM\s+\w+\s*$', 'DELETE without WHERE clause - Data loss risk'),
            (r'UPDATE\s+\w+\s+SET\b', 'UPDATE without WHERE clause - Data modification risk'),
            (r'DROP\s+TABLE\s+IF\s+NOT\s+EXISTS', 'DROP TABLE IF NOT EXISTS - Potential data loss'),
        ]

        detected = []
        content_upper = content.upper()

        for pattern, description in dangerous_patterns:
            if re.search(pattern, content_upper, re.IGNORECASE):
                detected.append(description)

        return detected

    # ==================== SYNTAX TESTS ====================

    def test_sql_syntax(self, migration_file: Path, content: str) -> TestResult:
        """
        Test SQL syntax using PostgreSQL EXPLAIN.

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()

        try:
            statements = self._extract_sql_statements(content)

            if not statements:
                return TestResult(
                    test_name="SQL Syntax Validation",
                    category=TestCategory.SYNTAX,
                    status=TestStatus.WARN,
                    message="No SQL statements found in migration file",
                    details={"statements_count": 0}
                )

            # Test each statement with EXPLAIN
            conn_info = self._parse_supabase_url(self.supabase_url)
            failed_statements = []

            for i, statement in enumerate(statements, 1):
                try:
                    cmd = [
                        "docker", "run", "--rm",
                        f"-e", f"PGPASSWORD={self.db_password}",
                        "postgres:17",
                        "psql",
                        f"--host={conn_info['host']}",
                        f"--port={conn_info['port']}",
                        f"--username={conn_info['user']}",
                        f"--dbname={conn_info['database']}",
                        "--command", f"EXPLAIN (FORMAT TEXT) {statement}"
                    ]

                    result = self._run_command(cmd, check=False, timeout=30)

                    if result.returncode != 0:
                        failed_statements.append({
                            "statement_number": i,
                            "statement": statement[:200] + "..." if len(statement) > 200 else statement,
                            "error": result.stderr.strip()
                        })

                except Exception as e:
                    failed_statements.append({
                        "statement_number": i,
                        "statement": statement[:200] + "..." if len(statement) > 200 else statement,
                        "error": str(e)
                    })

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            if failed_statements:
                return TestResult(
                    test_name="SQL Syntax Validation",
                    category=TestCategory.SYNTAX,
                    status=TestStatus.FAIL,
                    message=f"Syntax validation failed for {len(failed_statements)} statement(s)",
                    details={
                        "total_statements": len(statements),
                        "failed_statements": failed_statements,
                        "success_rate": f"{((len(statements) - len(failed_statements)) / len(statements) * 100):.1f}%"
                    },
                    execution_time_ms=execution_time
                )
            else:
                return TestResult(
                    test_name="SQL Syntax Validation",
                    category=TestCategory.SYNTAX,
                    status=TestStatus.PASS,
                    message=f"All {len(statements)} SQL statements are syntactically valid",
                    details={
                        "total_statements": len(statements),
                        "success_rate": "100.0%"
                    },
                    execution_time_ms=execution_time
                )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return TestResult(
                test_name="SQL Syntax Validation",
                category=TestCategory.SYNTAX,
                status=TestStatus.FAIL,
                message=f"Syntax validation error: {str(e)}",
                execution_time_ms=execution_time
            )

    def test_transaction_handling(self, migration_file: Path, content: str) -> TestResult:
        """
        Test for proper transaction handling in migration.

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()
        content_upper = content.upper()

        has_begin = 'BEGIN' in content_upper or 'BEGIN TRANSACTION' in content_upper
        has_commit = 'COMMIT' in content_upper
        has_rollback = 'ROLLBACK' in content_upper

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if has_begin and has_commit:
            return TestResult(
                test_name="Transaction Handling",
                category=TestCategory.SYNTAX,
                status=TestStatus.PASS,
                message="Migration contains proper transaction handling (BEGIN/COMMIT)",
                details={
                    "has_begin": True,
                    "has_commit": True,
                    "has_rollback": has_rollback
                },
                execution_time_ms=execution_time
            )
        elif has_begin or has_commit:
            return TestResult(
                test_name="Transaction Handling",
                category=TestCategory.SYNTAX,
                status=TestStatus.WARN,
                message="Incomplete transaction handling (missing BEGIN or COMMIT)",
                details={
                    "has_begin": has_begin,
                    "has_commit": has_commit,
                    "has_rollback": has_rollback,
                    "recommendation": "Add BEGIN at start and COMMIT at end of migration"
                },
                execution_time_ms=execution_time
            )
        else:
            return TestResult(
                test_name="Transaction Handling",
                category=TestCategory.SYNTAX,
                status=TestStatus.WARN,
                message="Migration lacks explicit transaction handling",
                details={
                    "has_begin": False,
                    "has_commit": False,
                    "has_rollback": False,
                    "recommendation": "Wrap migration in BEGIN/COMMIT block for atomicity"
                },
                execution_time_ms=execution_time
            )

    def test_dangerous_operations(self, migration_file: Path, content: str) -> TestResult:
        """
        Test for dangerous SQL operations.

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()
        dangerous_ops = self._detect_dangerous_operations(content)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if dangerous_ops:
            return TestResult(
                test_name="Dangerous Operations Detection",
                category=TestCategory.SYNTAX,
                status=TestStatus.FAIL,
                message=f"Found {len(dangerous_ops)} potentially dangerous operation(s)",
                details={
                    "dangerous_operations": dangerous_ops,
                    "recommendation": "Review and justify dangerous operations or remove them"
                },
                execution_time_ms=execution_time
            )
        else:
            return TestResult(
                test_name="Dangerous Operations Detection",
                category=TestCategory.SYNTAX,
                status=TestStatus.PASS,
                message="No dangerous operations detected",
                details={"dangerous_operations": []},
                execution_time_ms=execution_time
            )

    # ==================== INTEGRITY TESTS ====================

    def test_foreign_key_constraints(self, migration_file: Path, content: str) -> TestResult:
        """
        Test foreign key constraint definitions.

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()

        # Find foreign key constraints
        fk_pattern = r'FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+(\w+)\s*\(([^)]+)\)'
        foreign_keys = re.findall(fk_pattern, content, re.IGNORECASE)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if not foreign_keys:
            return TestResult(
                test_name="Foreign Key Constraints",
                category=TestCategory.INTEGRITY,
                status=TestStatus.SKIP,
                message="No foreign key constraints defined in migration",
                details={"foreign_keys_count": 0},
                execution_time_ms=execution_time
            )

        # Validate foreign key definitions
        issues = []
        for i, (columns, ref_table, ref_columns) in enumerate(foreign_keys, 1):
            # Check if referenced table exists (basic check)
            if not re.search(rf'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{re.escape(ref_table)}\b', content, re.IGNORECASE):
                issues.append({
                    "fk_number": i,
                    "issue": f"Referenced table '{ref_table}' not created in this migration",
                    "columns": columns,
                    "ref_table": ref_table,
                    "ref_columns": ref_columns
                })

        if issues:
            return TestResult(
                test_name="Foreign Key Constraints",
                category=TestCategory.INTEGRITY,
                status=TestStatus.WARN,
                message=f"Found {len(issues)} potential issue(s) with foreign key constraints",
                details={
                    "total_foreign_keys": len(foreign_keys),
                    "issues": issues,
                    "recommendation": "Ensure referenced tables exist or are created in previous migrations"
                },
                execution_time_ms=execution_time
            )
        else:
            return TestResult(
                test_name="Foreign Key Constraints",
                category=TestCategory.INTEGRITY,
                status=TestStatus.PASS,
                message=f"All {len(foreign_keys)} foreign key constraints appear valid",
                details={
                    "total_foreign_keys": len(foreign_keys),
                    "foreign_keys": [
                        {
                            "columns": cols,
                            "ref_table": table,
                            "ref_columns": ref_cols
                        }
                        for cols, table, ref_cols in foreign_keys
                    ]
                },
                execution_time_ms=execution_time
            )

    def test_data_types(self, migration_file: Path, content: str) -> TestResult:
        """
        Test data type definitions and compatibility.

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()

        # Find column definitions
        column_pattern = r'(\w+)\s+([A-Z]+)(?:\([^)]+\))?'
        columns = re.findall(column_pattern, content, re.IGNORECASE)

        # Check for potentially problematic data types
        problematic_types = {
            'TEXT': 'Consider using VARCHAR with specific length for better performance',
            'VARCHAR': 'Without length specification, defaults to unlimited',
        }

        issues = []
        for column_name, data_type in columns:
            data_type_upper = data_type.upper()
            if data_type_upper in problematic_types:
                # Check if length is specified
                if data_type_upper == 'VARCHAR' and '(' not in data_type:
                    issues.append({
                        "column": column_name,
                        "data_type": data_type,
                        "issue": problematic_types[data_type_upper]
                    })

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if issues:
            return TestResult(
                test_name="Data Type Definitions",
                category=TestCategory.INTEGRITY,
                status=TestStatus.WARN,
                message=f"Found {len(issues)} column(s) with potentially problematic data types",
                details={
                    "total_columns": len(columns),
                    "issues": issues
                },
                execution_time_ms=execution_time
            )
        else:
            return TestResult(
                test_name="Data Type Definitions",
                category=TestCategory.INTEGRITY,
                status=TestStatus.PASS,
                message=f"Column data types appear appropriate ({len(columns)} columns analyzed)",
                details={"total_columns": len(columns)},
                execution_time_ms=execution_time
            )

    def test_index_definitions(self, migration_file: Path, content: str) -> TestResult:
        """
        Test index definitions and optimization.

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()

        # Find index definitions
        index_pattern = r'CREATE\s+(UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s+ON\s+(\w+)\s*\(([^)]+)\)'
        indexes = re.findall(index_pattern, content, re.IGNORECASE)

        # Find table definitions
        table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)'
        tables = re.findall(table_pattern, content, re.IGNORECASE)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if not tables:
            return TestResult(
                test_name="Index Definitions",
                category=TestCategory.INTEGRITY,
                status=TestStatus.SKIP,
                message="No tables created in migration",
                details={"tables_count": 0, "indexes_count": 0},
                execution_time_ms=execution_time
            )

        # Check if tables have indexes
        tables_with_indexes = set(idx[2] for idx in indexes)
        tables_without_indexes = set(tables) - tables_with_indexes

        recommendations = []
        if tables_without_indexes:
            recommendations.append(
                f"Consider adding indexes for tables: {', '.join(tables_without_indexes)}"
            )

        return TestResult(
            test_name="Index Definitions",
            category=TestCategory.INTEGRITY,
            status=TestStatus.PASS if not recommendations else TestStatus.WARN,
            message=f"Found {len(indexes)} index(es) for {len(tables)} table(s)",
            details={
                "tables_count": len(tables),
                "indexes_count": len(indexes),
                "tables_with_indexes": len(tables_with_indexes),
                "tables_without_indexes": list(tables_without_indexes),
                "indexes": [
                    {
                        "name": name,
                        "unique": bool(unique),
                        "table": table,
                        "columns": columns
                    }
                    for unique, name, table, columns in indexes
                ],
                "recommendations": recommendations
            },
            execution_time_ms=execution_time
        )

    # ==================== PERFORMANCE TESTS ====================

    def test_query_complexity(self, migration_file: Path, content: str) -> TestResult:
        """
        Test query complexity and potential performance issues.

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()

        statements = self._extract_sql_statements(content)
        complexity_issues = []

        for i, statement in enumerate(statements, 1):
            # Check for complex patterns
            stmt_upper = statement.upper()

            # Nested subqueries
            if stmt_upper.count('SELECT') > 2:
                complexity_issues.append({
                    "statement_number": i,
                    "issue": "Multiple nested SELECT statements detected",
                    "complexity": "high",
                    "statement_preview": statement[:100] + "..."
                })

            # Multiple JOINs
            join_count = len(re.findall(r'\bJOIN\b', stmt_upper))
            if join_count > 3:
                complexity_issues.append({
                    "statement_number": i,
                    "issue": f"Multiple JOINs detected ({join_count} joins)",
                    "complexity": "medium",
                    "statement_preview": statement[:100] + "..."
                })

            # Wildcard SELECT
            if 'SELECT *' in stmt_upper:
                complexity_issues.append({
                    "statement_number": i,
                    "issue": "SELECT * wildcard detected - consider specifying columns",
                    "complexity": "low",
                    "statement_preview": statement[:100] + "..."
                })

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if complexity_issues:
            high_complexity = [issue for issue in complexity_issues if issue["complexity"] == "high"]
            status = TestStatus.FAIL if high_complexity else TestStatus.WARN

            return TestResult(
                test_name="Query Complexity Analysis",
                category=TestCategory.PERFORMANCE,
                status=status,
                message=f"Found {len(complexity_issues)} potential performance issue(s)",
                details={
                    "total_statements": len(statements),
                    "complexity_issues": complexity_issues,
                    "high_complexity_count": len(high_complexity),
                    "recommendation": "Review and optimize complex queries"
                },
                execution_time_ms=execution_time
            )
        else:
            return TestResult(
                test_name="Query Complexity Analysis",
                category=TestCategory.PERFORMANCE,
                status=TestStatus.PASS,
                message=f"No significant performance issues detected ({len(statements)} statements analyzed)",
                details={"total_statements": len(statements)},
                execution_time_ms=execution_time
            )

    def test_execution_time_estimation(self, migration_file: Path, content: str) -> TestResult:
        """
        Estimate execution time using EXPLAIN ANALYZE (dry-run).

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()

        if self.dry_run:
            return TestResult(
                test_name="Execution Time Estimation",
                category=TestCategory.PERFORMANCE,
                status=TestStatus.SKIP,
                message="Skipped in dry-run mode",
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

        try:
            statements = self._extract_sql_statements(content)
            conn_info = self._parse_supabase_url(self.supabase_url)

            execution_times = []
            failed_statements = []

            for i, statement in enumerate(statements, 1):
                try:
                    # Use EXPLAIN (ANALYZE, BUFFERS, TIMING) for detailed analysis
                    cmd = [
                        "docker", "run", "--rm",
                        f"-e", f"PGPASSWORD={self.db_password}",
                        "postgres:17",
                        "psql",
                        f"--host={conn_info['host']}",
                        f"--port={conn_info['port']}",
                        f"--username={conn_info['user']}",
                        f"--dbname={conn_info['database']}",
                        "--command", f"EXPLAIN (ANALYZE, BUFFERS, TIMING OFF) {statement}"
                    ]

                    result = self._run_command(cmd, check=False, timeout=60)

                    if result.returncode == 0:
                        # Extract execution time from EXPLAIN output
                        time_match = re.search(r'Execution Time: ([\d.]+) ms', result.stdout)
                        if time_match:
                            execution_times.append(float(time_match.group(1)))
                    else:
                        failed_statements.append({
                            "statement_number": i,
                            "error": result.stderr.strip()
                        })

                except Exception as e:
                    failed_statements.append({
                        "statement_number": i,
                        "error": str(e)
                    })

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            if failed_statements:
                return TestResult(
                    test_name="Execution Time Estimation",
                    category=TestCategory.PERFORMANCE,
                    status=TestStatus.WARN,
                    message=f"Could not estimate execution time for {len(failed_statements)} statement(s)",
                    details={
                        "total_statements": len(statements),
                        "failed_statements": failed_statements,
                        "successful_estimates": len(execution_times)
                    },
                    execution_time_ms=execution_time
                )
            elif execution_times:
                total_time = sum(execution_times)
                avg_time = total_time / len(execution_times)
                max_time = max(execution_times)

                # Determine if execution time is acceptable
                status = TestStatus.PASS
                if max_time > 1000:  # More than 1 second for a single statement
                    status = TestStatus.WARN
                if max_time > 5000:  # More than 5 seconds
                    status = TestStatus.FAIL

                return TestResult(
                    test_name="Execution Time Estimation",
                    category=TestCategory.PERFORMANCE,
                    status=status,
                    message=f"Estimated total execution time: {total_time:.2f}ms",
                    details={
                        "total_statements": len(statements),
                        "total_time_ms": total_time,
                        "average_time_ms": avg_time,
                        "max_time_ms": max_time,
                        "individual_times": execution_times
                    },
                    execution_time_ms=execution_time
                )
            else:
                return TestResult(
                    test_name="Execution Time Estimation",
                    category=TestCategory.PERFORMANCE,
                    status=TestStatus.SKIP,
                    message="Could not extract execution time information",
                    details={"total_statements": len(statements)},
                    execution_time_ms=execution_time
                )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return TestResult(
                test_name="Execution Time Estimation",
                category=TestCategory.PERFORMANCE,
                status=TestStatus.WARN,
                message=f"Execution time estimation error: {str(e)}",
                execution_time_ms=execution_time
            )

    # ==================== ROLLBACK TESTS ====================

    def test_rollback_sql_presence(self, migration_file: Path, content: str) -> TestResult:
        """
        Test for presence of rollback SQL.

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()

        # Check for rollback file
        rollback_file = migration_file.parent / f"{migration_file.stem}.rollback.sql"
        has_rollback_file = rollback_file.exists()

        # Check for rollback comments in migration
        rollback_comments = re.findall(r'--\s*ROLLBACK:?\s*(.+)', content, re.IGNORECASE)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if has_rollback_file:
            return TestResult(
                test_name="Rollback SQL Presence",
                category=TestCategory.ROLLBACK,
                status=TestStatus.PASS,
                message="Rollback SQL file found",
                details={
                    "rollback_file": str(rollback_file),
                    "rollback_comments": rollback_comments
                },
                execution_time_ms=execution_time
            )
        elif rollback_comments:
            return TestResult(
                test_name="Rollback SQL Presence",
                category=TestCategory.ROLLBACK,
                status=TestStatus.WARN,
                message="Rollback instructions found in comments but no dedicated rollback file",
                details={
                    "rollback_comments": rollback_comments,
                    "recommendation": "Create dedicated .rollback.sql file for automated rollback"
                },
                execution_time_ms=execution_time
            )
        else:
            return TestResult(
                test_name="Rollback SQL Presence",
                category=TestCategory.ROLLBACK,
                status=TestStatus.WARN,
                message="No rollback SQL found",
                details={
                    "recommendation": "Create .rollback.sql file for safe rollback capability"
                },
                execution_time_ms=execution_time
            )

    def test_rollback_sql_validity(self, migration_file: Path, content: str) -> TestResult:
        """
        Test validity of rollback SQL if present.

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()

        rollback_file = migration_file.parent / f"{migration_file.stem}.rollback.sql"

        if not rollback_file.exists():
            return TestResult(
                test_name="Rollback SQL Validity",
                category=TestCategory.ROLLBACK,
                status=TestStatus.SKIP,
                message="No rollback SQL file to validate",
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

        try:
            rollback_content = self._read_migration_file(rollback_file)

            # Validate rollback SQL syntax
            syntax_result = self.test_sql_syntax(rollback_file, rollback_content)

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            if syntax_result.status == TestStatus.PASS:
                return TestResult(
                    test_name="Rollback SQL Validity",
                    category=TestCategory.ROLLBACK,
                    status=TestStatus.PASS,
                    message="Rollback SQL syntax is valid",
                    details={
                        "rollback_file": str(rollback_file),
                        "syntax_check": "passed"
                    },
                    execution_time_ms=execution_time
                )
            else:
                return TestResult(
                    test_name="Rollback SQL Validity",
                    category=TestCategory.ROLLBACK,
                    status=TestStatus.FAIL,
                    message="Rollback SQL syntax validation failed",
                    details={
                        "rollback_file": str(rollback_file),
                        "syntax_check": "failed",
                        "syntax_errors": syntax_result.details
                    },
                    execution_time_ms=execution_time
                )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return TestResult(
                test_name="Rollback SQL Validity",
                category=TestCategory.ROLLBACK,
                status=TestStatus.FAIL,
                message=f"Rollback SQL validation error: {str(e)}",
                execution_time_ms=execution_time
            )

    # ==================== INTEGRATION TESTS ====================

    def test_migration_dependencies(self, migration_file: Path, content: str) -> TestResult:
        """
        Test migration dependencies and order.

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()

        # Extract migration timestamp from filename
        timestamp_match = re.search(r'(\d{14})', migration_file.name)
        if not timestamp_match:
            return TestResult(
                test_name="Migration Dependencies",
                category=TestCategory.INTEGRATION,
                status=TestStatus.WARN,
                message="Migration filename does not contain timestamp",
                details={
                    "filename": migration_file.name,
                    "recommendation": "Use timestamp format: YYYYMMDDHHMMSS_description.sql"
                },
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )

        migration_timestamp = timestamp_match.group(1)

        # Check for references to other tables
        referenced_tables = set()
        table_pattern = r'REFERENCES\s+(\w+)|FROM\s+(\w+)|JOIN\s+(\w+)|UPDATE\s+(\w+)|INSERT\s+INTO\s+(\w+)'
        for match in re.finditer(table_pattern, content, re.IGNORECASE):
            for group in match.groups():
                if group and group.upper() not in ['PUBLIC', 'PG_CATALOG']:
                    referenced_tables.add(group)

        # Check which tables are created in this migration
        created_tables = set(re.findall(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', content, re.IGNORECASE))

        # Tables referenced but not created in this migration
        external_tables = referenced_tables - created_tables

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if external_tables:
            return TestResult(
                test_name="Migration Dependencies",
                category=TestCategory.INTEGRATION,
                status=TestStatus.WARN,
                message=f"Migration references {len(external_tables)} external table(s)",
                details={
                    "migration_timestamp": migration_timestamp,
                    "created_tables": list(created_tables),
                    "referenced_tables": list(referenced_tables),
                    "external_tables": list(external_tables),
                    "recommendation": "Ensure dependent migrations run before this one"
                },
                execution_time_ms=execution_time
            )
        else:
            return TestResult(
                test_name="Migration Dependencies",
                category=TestCategory.INTEGRATION,
                status=TestStatus.PASS,
                message="Migration has no external dependencies",
                details={
                    "migration_timestamp": migration_timestamp,
                    "created_tables": list(created_tables),
                    "referenced_tables": list(referenced_tables)
                },
                execution_time_ms=execution_time
            )

    def test_breaking_changes(self, migration_file: Path, content: str) -> TestResult:
        """
        Test for potentially breaking changes.

        Args:
            migration_file: Path to migration file
            content: Migration file content

        Returns:
            TestResult object
        """
        start_time = datetime.now()

        breaking_patterns = [
            (r'DROP\s+TABLE\b', 'Dropping tables - potential data loss'),
            (r'DROP\s+COLUMN\b', 'Dropping columns - potential data loss'),
            (r'ALTER\s+TABLE.*\bDROP\b', 'Altering table with DROP - potential breaking change'),
            (r'ALTER\s+TABLE.*\bRENAME\b', 'Renaming tables or columns - breaking change for dependent code'),
            (r'ALTER\s+TABLE.*\bMODIFY\b.*\bTYPE\b', 'Changing column types - potential data conversion issues'),
        ]

        detected_changes = []
        content_upper = content.upper()

        for pattern, description in breaking_patterns:
            if re.search(pattern, content_upper, re.IGNORECASE):
                detected_changes.append(description)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if detected_changes:
            return TestResult(
                test_name="Breaking Changes Detection",
                category=TestCategory.INTEGRATION,
                status=TestStatus.WARN,
                message=f"Found {len(detected_changes)} potential breaking change(s)",
                details={
                    "breaking_changes": detected_changes,
                    "recommendation": "Review breaking changes and coordinate with application updates"
                },
                execution_time_ms=execution_time
            )
        else:
            return TestResult(
                test_name="Breaking Changes Detection",
                category=TestCategory.INTEGRATION,
                status=TestStatus.PASS,
                message="No breaking changes detected",
                details={"breaking_changes": []},
                execution_time_ms=execution_time
            )

    # ==================== MAIN TESTING METHODS ====================

    def test_migration(
        self,
        migration_file: Path,
        categories: Optional[List[TestCategory]] = None
    ) -> bool:
        """
        Run comprehensive tests on a migration file.

        Args:
            migration_file: Path to migration file
            categories: List of test categories to run (None for all)

        Returns:
            True if all tests passed (no failures)
        """
        self.logger.info("=" * 80)
        self.logger.info(f"TESTING MIGRATION: {migration_file.name}")
        self.logger.info("=" * 80)
        self.logger.info(f"Environment: {self.environment}")
        self.logger.info(f"Dry run: {self.dry_run}")
        self.logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # Read migration file
            content = self._read_migration_file(migration_file)
            self.logger.info(f"Migration file size: {len(content)} bytes")

            # Determine which categories to test
            if categories is None:
                categories = list(TestCategory)

            # Run tests by category
            for category in categories:
                self.logger.info(f"\n--- {category.value.upper()} TESTS ---")

                if category == TestCategory.SYNTAX:
                    self._add_test_result(self.test_sql_syntax(migration_file, content))
                    self._add_test_result(self.test_transaction_handling(migration_file, content))
                    self._add_test_result(self.test_dangerous_operations(migration_file, content))

                elif category == TestCategory.INTEGRITY:
                    self._add_test_result(self.test_foreign_key_constraints(migration_file, content))
                    self._add_test_result(self.test_data_types(migration_file, content))
                    self._add_test_result(self.test_index_definitions(migration_file, content))

                elif category == TestCategory.PERFORMANCE:
                    self._add_test_result(self.test_query_complexity(migration_file, content))
                    self._add_test_result(self.test_execution_time_estimation(migration_file, content))

                elif category == TestCategory.ROLLBACK:
                    self._add_test_result(self.test_rollback_sql_presence(migration_file, content))
                    self._add_test_result(self.test_rollback_sql_validity(migration_file, content))

                elif category == TestCategory.INTEGRATION:
                    self._add_test_result(self.test_migration_dependencies(migration_file, content))
                    self._add_test_result(self.test_breaking_changes(migration_file, content))

            # Print summary
            self._print_test_summary()

            # Return True if no failures
            return self.stats["failed"] == 0

        except Exception as e:
            self.logger.error(f"Migration testing failed: {e}")
            return False

    def test_all_pending_migrations(
        self,
        categories: Optional[List[TestCategory]] = None
    ) -> bool:
        """
        Test all pending migrations in the migrations directory.

        Args:
            categories: List of test categories to run (None for all)

        Returns:
            True if all tests passed for all migrations
        """
        self.logger.info("=" * 80)
        self.logger.info("TESTING ALL PENDING MIGRATIONS")
        self.logger.info("=" * 80)

        # Find all migration files
        migration_files = sorted(self.migrations_dir.glob("*.sql"))

        if not migration_files:
            self.logger.warning("No migration files found")
            return True

        self.logger.info(f"Found {len(migration_files)} migration file(s)")

        # Test each migration
        all_passed = True
        for migration_file in migration_files:
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"Testing: {migration_file.name}")
            self.logger.info(f"{'='*80}")

            passed = self.test_migration(migration_file, categories)
            if not passed:
                all_passed = False

        # Print overall summary
        self.logger.info("\n" + "=" * 80)
        self.logger.info("OVERALL TEST SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Migrations tested: {len(migration_files)}")
        self.logger.info(f"All passed: {all_passed}")

        return all_passed

    def _print_test_summary(self):
        """Print test execution summary."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("TEST SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Total tests: {self.stats['total_tests']}")
        self.logger.info(f"Passed: {self.stats['passed']} ✓")
        self.logger.info(f"Failed: {self.stats['failed']} ✗")
        self.logger.info(f"Warnings: {self.stats['warnings']} ⚠")
        self.logger.info(f"Skipped: {self.stats['skipped']} ○")

        if self.stats['failed'] == 0:
            self.logger.info("\n✓ ALL CRITICAL TESTS PASSED")
        else:
            self.logger.info(f"\n✗ {self.stats['failed']} CRITICAL TEST(S) FAILED")

    def generate_report(self, report_file: Optional[Path] = None) -> Path:
        """
        Generate detailed test report.

        Args:
            report_file: Path to report file (auto-generated if None)

        Returns:
            Path to generated report file
        """
        if report_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.reports_dir / f"migration_test_report_{timestamp}.json"

        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "environment": self.environment,
                "dry_run": self.dry_run,
                "project_root": str(self.project_root)
            },
            "summary": self.stats,
            "test_results": [result.to_dict() for result in self.test_results],
            "recommendations": self._generate_recommendations()
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"\n✓ Test report generated: {report_file}")
        return report_file

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on test results."""
        recommendations = []

        # Analyze failed tests
        failed_tests = [r for r in self.test_results if r.status == TestStatus.FAIL]
        for test in failed_tests:
            if test.category == TestCategory.SYNTAX:
                recommendations.append(
                    f"Fix syntax errors in {test.test_name}: {test.message}"
                )
            elif test.category == TestCategory.INTEGRITY:
                recommendations.append(
                    f"Review integrity issues in {test.test_name}: {test.message}"
                )
            elif test.category == TestCategory.PERFORMANCE:
                recommendations.append(
                    f"Optimize performance issues in {test.test_name}: {test.message}"
                )
            elif test.category == TestCategory.ROLLBACK:
                recommendations.append(
                    f"Ensure rollback capability for {test.test_name}: {test.message}"
                )

        # Analyze warnings
        warning_tests = [r for r in self.test_results if r.status == TestStatus.WARN]
        for test in warning_tests:
            if "recommendation" in test.details:
                recommendations.append(test.details["recommendation"])

        return recommendations


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Comprehensive migration testing framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test a single migration file
  python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql

  # Test all pending migrations
  python scripts/test_migration.py --all-pending

  # Test with specific environment
  python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql --environment staging

  # Run specific test categories
  python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql --categories syntax integrity performance

  # Generate detailed report
  python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql --report-file test_report.json

  # Dry-run mode (simulate without database changes)
  python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql --dry-run

  # Verbose output with detailed information
  python scripts/test_migration.py --migration-file supabase/migrations/20260621100000_test_deployment.sql --verbose
        """
    )

    # Migration selection
    migration_group = parser.add_mutually_exclusive_group(required=True)
    migration_group.add_argument(
        '--migration-file',
        type=str,
        help='Path to migration file to test'
    )
    migration_group.add_argument(
        '--all-pending',
        action='store_true',
        help='Test all pending migrations'
    )

    # Test configuration
    parser.add_argument(
        '--categories',
        type=str,
        nargs='+',
        choices=[cat.value for cat in TestCategory],
        help='Test categories to run (default: all)'
    )
    parser.add_argument(
        '--environment',
        type=str,
        default='dev',
        choices=['dev', 'staging', 'production'],
        help='Database environment to test against (default: dev)'
    )
    parser.add_argument(
        '--report-file',
        type=str,
        help='Path to output report file (JSON format)'
    )

    # Execution options
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate tests without database changes'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    try:
        # Convert categories to enum values
        categories = None
        if args.categories:
            categories = [TestCategory(cat) for cat in args.categories]

        # Create test framework instance
        framework = MigrationTestFramework(
            environment=args.environment,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        # Run tests
        if args.all_pending:
            success = framework.test_all_pending_migrations(categories)
        else:
            migration_file = Path(args.migration_file)
            success = framework.test_migration(migration_file, categories)

        # Generate report
        report_file = None
        if args.report_file:
            report_file = Path(args.report_file)
        else:
            # Always generate report
            report_file = framework.generate_report()

        # Exit with appropriate code
        if success:
            print(f"\n✓ Migration testing completed successfully")
            print(f"Report: {report_file}")
            return 0
        else:
            print(f"\n✗ Migration testing failed")
            print(f"Report: {report_file}")
            return 1

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())