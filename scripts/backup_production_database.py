#!/usr/bin/env python3
"""
Production Database Backup Script
==================================
Creates a full backup of the production Supabase database including DDL and data.
Outputs a compressed SQL file suitable for Google Drive upload.

Usage:
    python scripts/backup_production_database.py

Output:
    backup/db_backup_YYYYMMDD_HHMMSS.sql.gz
"""

import os
import sys
import subprocess
import gzip
import shutil
from pathlib import Path
from datetime import datetime
import dotenv


def parse_supabase_url(supabase_url: str) -> dict:
    """
    Parse Supabase URL to extract database connection information.
    Returns host, port, database, and user info.

    Args:
        supabase_url: Supabase project URL (e.g., https://nzcwtjloonumxpsqzarq.supabase.co)

    Returns:
        dict with keys: host, port, database, user
    """
    if not supabase_url:
        raise ValueError("SUPABASE_URL is empty or not set")

    # Extract project ID from URL
    clean_url = supabase_url.rstrip("/")
    project_id = clean_url.replace("https://", "").replace("http://", "").split(".")[0]

    return {
        "host": "aws-0-us-east-2.pooler.supabase.com",
        "port": "5432",
        "database": "postgres",
        "user": f"postgres.{project_id}",
    }


def run_pg_dump(conn_info: dict, db_password: str, output_file: Path) -> bool:
    """
    Execute pg_dump to create a full database backup using Docker.
    Uses PostgreSQL 17 Docker image for version compatibility.

    Args:
        conn_info: Dictionary with database connection info
        db_password: Database password
        output_file: Path to output SQL file

    Returns:
        True if successful, False otherwise
    """
    cmd = [
        "docker",
        "run",
        "--rm",
        f"-e",
        f"PGPASSWORD={db_password}",
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
    ]

    print(f"🔧 Running pg_dump via Docker (PostgreSQL 17)...")
    print(f"   Host: {conn_info['host']}")
    print(f"   Database: {conn_info['database']}")
    print(f"   User: {conn_info['user']}")
    print("")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            print(f"❌ pg_dump failed with exit code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False

        print(f"✅ pg_dump completed successfully")
        return True

    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker:")
        print("   https://docs.docker.com/get-docker/")
        return False
    except Exception as e:
        print(f"❌ Error running pg_dump: {str(e)}")
        return False

        print(f"✅ pg_dump completed successfully")
        return True

    except FileNotFoundError:
        print("❌ pg_dump not found. Please install PostgreSQL client tools:")
        print("   sudo apt-get install postgresql-client  # Ubuntu/Debian")
        print("   brew install postgresql                 # macOS")
        return False
    except Exception as e:
        print(f"❌ Error running pg_dump: {str(e)}")
        return False


def compress_file(input_file: Path, output_file: Path) -> bool:
    """
    Compress a file using gzip.

    Args:
        input_file: Path to input file
        output_file: Path to output compressed file

    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"🗜️  Compressing backup file...")

        with open(input_file, "rb") as f_in:
            with gzip.open(output_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Get file sizes
        original_size = float(input_file.stat().st_size)
        compressed_size = float(output_file.stat().st_size)
        ratio = (1 - compressed_size / original_size) * 100

        print(f"✅ Compression completed")
        print(f"   Original size: {format_size(float(original_size))}")
        print(f"   Compressed size: {format_size(float(compressed_size))}")
        print(f"   Compression ratio: {ratio:.1f}%")
        print("")

        return True

    except Exception as e:
        print(f"❌ Error compressing file: {str(e)}")
        return False


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def print_backup_info(backup_file: Path) -> None:
    """Print information about the backup file."""
    file_size = float(backup_file.stat().st_size)

    print(f"📊 Backup Information:")
    print(f"   File: {backup_file}")
    print(f"   Size: {format_size(file_size)}")
    print(f"   Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")


def print_google_drive_instructions(backup_file: Path) -> None:
    """Print instructions for uploading to Google Drive."""
    print("📤 Google Drive Upload Instructions:")
    print("=" * 60)
    print("")
    print("Step 1: Open Google Drive")
    print("   - Go to: https://drive.google.com")
    print("   - Sign in with your account")
    print("")
    print("Step 2: Navigate to Backup Folder")
    print("   - Create or navigate to: /diocesan-vitality/backups/")
    print("   - Organize by date: /diocesan-vitality/backups/2026/")
    print("")
    print("Step 3: Upload Backup File")
    print(f"   - Locate: {backup_file.absolute()}")
    print("   - Drag and drop the file to Google Drive")
    print("   - Or click 'New' → 'File upload' and select the file")
    print("")
    print("Step 4: Verify Upload")
    print("   - Confirm file size matches local backup")
    print("   - Check that file can be downloaded")
    print("")
    print("💡 Alternative: Google Drive for Desktop")
    print("   - Install: https://www.google.com/drive/download/")
    print("   - Sync local backup folder to Google Drive")
    print("   - Automatic backup when drive syncs")
    print("")
    print("=" * 60)


def main():
    """Main function to execute backup process."""
    print("=" * 60)
    print("🗄️  Production Database Backup")
    print("=" * 60)
    print("")

    # Load environment variables
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        print(f"❌ .env file not found at: {env_file}")
        print("💡 Copy .env.example to .env and configure your credentials")
        sys.exit(1)

    dotenv.load_dotenv(env_file)

    # Get credentials
    supabase_url = os.getenv("SUPABASE_URL")
    db_password = os.getenv("SUPABASE_DB_PASSWORD")

    if not supabase_url:
        print("❌ SUPABASE_URL not found in .env")
        sys.exit(1)

    if not db_password:
        print("❌ SUPABASE_DB_PASSWORD not found in .env")
        sys.exit(1)

    print(f"✅ Loaded credentials from .env")
    print("")

    # Parse connection info
    try:
        conn_info = parse_supabase_url(supabase_url)
        print(f"✅ Extracted connection info")
        print("")
    except ValueError as e:
        print(f"❌ {str(e)}")
        sys.exit(1)

    # Create backup directory if it doesn't exist
    backup_dir = Path(__file__).parent.parent / "backup"
    backup_dir.mkdir(exist_ok=True)

    # Generate timestamp for backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sql_file = backup_dir / f"db_backup_{timestamp}.sql"
    gzip_file = backup_dir / f"db_backup_{timestamp}.sql.gz"

    # Run pg_dump
    if not run_pg_dump(conn_info, db_password, sql_file):
        print("❌ Backup failed: pg_dump error")
        sys.exit(1)

    # Verify SQL file exists and is not empty
    if not sql_file.exists() or sql_file.stat().st_size == 0:
        print(f"❌ Backup failed: SQL file is empty or doesn't exist")
        sys.exit(1)

    # Compress backup
    if not compress_file(sql_file, gzip_file):
        print("❌ Backup failed: compression error")
        sys.exit(1)

    # Remove uncompressed SQL file
    sql_file.unlink()

    # Print backup info
    print_backup_info(gzip_file)

    # Print Google Drive instructions
    print_google_drive_instructions(gzip_file)

    print("")
    print("=" * 60)
    print("✅ Backup completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
