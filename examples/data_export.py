#!/usr/bin/env python3
"""
Data Export Example

This example demonstrates how to export extracted data to various formats
including CSV, JSON, and Excel.
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_database_connection():
    """Get database connection."""
    try:
        # Import database utilities
        sys.path.insert(0, str(project_root / "core"))
        from db import get_db_connection

        return get_db_connection()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None


def fetch_parishes_data(limit: int = None, diocese_id: int = None) -> List[Dict[str, Any]]:
    """Fetch parishes data from the database."""
    conn = get_database_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        # Build query
        query = """
        SELECT
            p.id,
            p.name,
            p.address,
            p.city,
            p.state,
            p.zip_code,
            p.phone,
            p.email,
            p.website_url,
            p.diocese_id,
            d.name as diocese_name,
            p.created_at,
            p.updated_at
        FROM parishes p
        LEFT JOIN dioceses d ON p.diocese_id = d.id
        """

        params = []
        if diocese_id:
            query += " WHERE p.diocese_id = %s"
            params.append(diocese_id)

        query += " ORDER BY p.created_at DESC"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        # Convert to list of dictionaries
        parishes = []
        for row in rows:
            parish = dict(zip(columns, row))
            # Convert datetime objects to strings
            for key, value in parish.items():
                if hasattr(value, "isoformat"):
                    parish[key] = value.isoformat()
            parishes.append(parish)

        logger.info(f"📊 Fetched {len(parishes)} parishes from database")
        return parishes

    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return []

    finally:
        if conn:
            conn.close()


def export_to_csv(data: List[Dict[str, Any]], output_file: Path) -> bool:
    """Export data to CSV format."""
    try:
        if not data:
            logger.warning("No data to export")
            return False

        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"✅ CSV export completed: {output_file}")
        return True

    except Exception as e:
        logger.error(f"❌ CSV export failed: {e}")
        return False


def export_to_json(data: List[Dict[str, Any]], output_file: Path) -> bool:
    """Export data to JSON format."""
    try:
        export_data = {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "total_records": len(data),
                "source": "Diocesan Vitality Data Export",
            },
            "parishes": data,
        }

        with open(output_file, "w", encoding="utf-8") as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)

        logger.info(f"✅ JSON export completed: {output_file}")
        return True

    except Exception as e:
        logger.error(f"❌ JSON export failed: {e}")
        return False


def export_to_excel(data: List[Dict[str, Any]], output_file: Path) -> bool:
    """Export data to Excel format."""
    try:
        # Try to import pandas for Excel export
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas not installed. Install with: pip install pandas openpyxl")
            return False

        if not data:
            logger.warning("No data to export")
            return False

        # Create DataFrame
        df = pd.DataFrame(data)

        # Export to Excel with multiple sheets
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name="Parishes", index=False)

            # Summary sheet
            summary_data = {
                "Metric": [
                    "Total Parishes",
                    "Unique Dioceses",
                    "Parishes with Websites",
                    "Parishes with Email",
                    "Parishes with Phone",
                    "Export Date",
                ],
                "Value": [
                    len(df),
                    df["diocese_id"].nunique() if "diocese_id" in df.columns else 0,
                    df["website_url"].notna().sum() if "website_url" in df.columns else 0,
                    df["email"].notna().sum() if "email" in df.columns else 0,
                    df["phone"].notna().sum() if "phone" in df.columns else 0,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ],
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

        logger.info(f"✅ Excel export completed: {output_file}")
        return True

    except Exception as e:
        logger.error(f"❌ Excel export failed: {e}")
        return False


def main():
    """Main function for the data export example."""
    parser = argparse.ArgumentParser(
        description="Export Diocesan Vitality data to various formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python data_export.py --format csv --output parishes.csv
  python data_export.py --format json --output parishes.json --limit 100
  python data_export.py --format excel --output parishes.xlsx --diocese-id 1
  python data_export.py --format all --output parishes_export

Supported Formats:
  csv    - Comma-separated values (simple, widely compatible)
  json   - JavaScript Object Notation (structured, with metadata)
  excel  - Excel workbook with multiple sheets (requires pandas)
  all    - Export to all formats with appropriate extensions

Note: Excel format requires 'pandas' and 'openpyxl' packages:
      pip install pandas openpyxl
        """,
    )

    parser.add_argument(
        "--format", choices=["csv", "json", "excel", "all"], default="csv", help="Export format (default: csv)"
    )

    parser.add_argument("--output", required=True, help="Output file path (without extension for 'all' format)")

    parser.add_argument("--limit", type=int, help="Limit number of records to export")

    parser.add_argument("--diocese-id", type=int, help="Export data for specific diocese only")

    args = parser.parse_args()

    logger.info("📊 Diocesan Vitality Data Export Example")
    logger.info("=" * 50)

    # Check prerequisites
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please copy .env.example to .env and configure your database credentials")
        return 1

    # Fetch data
    logger.info("🔄 Fetching data from database...")
    data = fetch_parishes_data(limit=args.limit, diocese_id=args.diocese_id)

    if not data:
        logger.error("❌ No data found to export")
        return 1

    logger.info(f"📈 Found {len(data)} records to export")

    # Prepare output file(s)
    output_path = Path(args.output)
    success = True

    # Export based on format
    if args.format == "csv":
        output_file = output_path.with_suffix(".csv")
        success = export_to_csv(data, output_file)

    elif args.format == "json":
        output_file = output_path.with_suffix(".json")
        success = export_to_json(data, output_file)

    elif args.format == "excel":
        output_file = output_path.with_suffix(".xlsx")
        success = export_to_excel(data, output_file)

    elif args.format == "all":
        # Export to all formats
        formats = [(".csv", export_to_csv), (".json", export_to_json), (".xlsx", export_to_excel)]

        for ext, export_func in formats:
            output_file = output_path.with_suffix(ext)
            format_success = export_func(data, output_file)
            success = success and format_success

    if success:
        logger.info("🎉 Data export completed successfully!")
        logger.info("📁 Output files created in current directory")
        if args.format == "excel":
            logger.info("💡 Excel file includes both parish data and summary statistics")
        return 0
    else:
        logger.error("❌ Data export failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
