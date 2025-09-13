#!/usr/bin/env python3
"""
Monitoring-enabled USCCB data extraction pipeline.
Integrates with the real-time dashboard for live operational visibility.
"""

import argparse
import time
from core.logger import get_logger
from core.monitoring_client import get_monitoring_client, ExtractionMonitoring
import config
from extract_dioceses import main as extract_dioceses_main
from find_parishes import find_parish_directories
from extract_parishes import main as extract_parishes_main
from extract_schedule import main as extract_schedule_main
from report_statistics import main as report_statistics_main

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run the USCCB data extraction pipeline with monitoring.")
    parser.add_argument("--skip_dioceses", action="store_true", help="Skip the diocese extraction step.")
    parser.add_argument("--skip_parish_directories", action="store_true", help="Skip finding parish directories.")
    parser.add_argument("--skip_parishes", action="store_true", help="Skip the parish extraction step.")
    parser.add_argument("--skip_schedules", action="store_true", help="Skip the schedule extraction step.")
    parser.add_argument("--skip_reporting", action="store_true", help="Skip the reporting step.")
    parser.add_argument("--diocese_id", type=int, help="ID of a specific diocese to process.")
    parser.add_argument("--max_parishes_per_diocese", type=int, default=config.DEFAULT_MAX_PARISHES_PER_DIOCESE, help="Max parishes to extract per diocese.")
    parser.add_argument("--num_parishes_for_schedule", type=int, default=config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE, help="Number of parishes to extract schedules for.")
    parser.add_argument("--monitoring_url", type=str, default="http://localhost:8000", help="Monitoring backend URL.")
    parser.add_argument("--disable_monitoring", action="store_true", help="Disable monitoring integration.")
    
    args = parser.parse_args()

    # Initialize monitoring client
    monitoring_client = get_monitoring_client(args.monitoring_url)
    if args.disable_monitoring:
        monitoring_client.disable()
        logger.info("📊 Monitoring disabled")
    else:
        logger.info(f"📊 Monitoring enabled: {args.monitoring_url}")

    # Send initial log
    monitoring_client.send_log("🚀 Starting USCCB data extraction pipeline", "INFO")
    
    logger.info("Starting USCCB data extraction pipeline with monitoring...")
    start_time = time.time()

    if not config.validate_config():
        monitoring_client.report_error(
            error_type="ConfigurationError", 
            message="Missing configuration - pipeline cannot start"
        )
        logger.error("Exiting due to missing configuration.")
        return

    # If a specific diocese is targeted, we can skip the full diocese extraction
    if args.diocese_id and not args.skip_dioceses:
        logger.info(f"--diocese_id is set to {args.diocese_id}, skipping full diocese extraction.")
        args.skip_dioceses = True

    # Step 1: Extract Dioceses
    if not args.skip_dioceses:
        try:
            logger.info("\n--- Step 1: Extract Dioceses ---")
            monitoring_client.send_log("1️⃣ Extract Dioceses: Scraping USCCB website for all U.S. dioceses", "INFO")
            monitoring_client.update_extraction_status(
                status="running",
                current_diocese="USCCB Website",
                parishes_processed=0
            )
            
            extract_dioceses_main(0)  # Setting max_dioceses to 0 to run for all
            
            monitoring_client.send_log("✅ Step 1 Complete: Diocese extraction completed successfully", "INFO")
            
        except Exception as e:
            monitoring_client.report_error(
                error_type="DiocesesExtractionError",
                message=f"Diocese extraction failed: {str(e)}"
            )
            logger.error(f"Diocese extraction failed: {e}", exc_info=True)
    else:
        logger.info("\n--- Skipping Step 1: Extract Dioceses ---")
        monitoring_client.send_log("⏭️ Step 1 Skipped: Extract Dioceses", "INFO")

    # Step 2: Find Parish Directories
    if not args.skip_parish_directories:
        try:
            logger.info("\n--- Step 2: Find Parish Directories ---")
            monitoring_client.send_log("2️⃣ Find Parish Directories: Using AI to locate parish directory pages", "INFO")
            monitoring_client.update_extraction_status(
                status="running",
                current_diocese="Parish Directory Discovery",
                parishes_processed=0
            )
            
            find_parish_directories(diocese_id=args.diocese_id, max_dioceses_to_process=20)
            
            monitoring_client.send_log("✅ Step 2 Complete: Parish directory discovery completed", "INFO")
            
        except Exception as e:
            monitoring_client.report_error(
                error_type="ParishDirectoryError",
                message=f"Parish directory search failed: {str(e)}"
            )
            logger.error(f"Parish directory search failed: {e}", exc_info=True)
    else:
        logger.info("\n--- Skipping Step 2: Find Parish Directories ---")
        monitoring_client.send_log("⏭️ Step 2 Skipped: Find Parish Directories", "INFO")

    # Step 3: Extract Parishes
    if not args.skip_parishes:
        try:
            logger.info("\n--- Step 3: Extract Parishes ---")
            
            # Get diocese info for monitoring
            if args.diocese_id:
                from core.db import get_supabase_client
                supabase = get_supabase_client()
                response = supabase.table('Dioceses').select('Name').eq('id', args.diocese_id).execute()
                diocese_name = response.data[0]['Name'] if response.data else f"Diocese ID {args.diocese_id}"
            else:
                diocese_name = "Multiple Dioceses"
            
            # Use monitoring context for parish extraction
            with ExtractionMonitoring(diocese_name, args.max_parishes_per_diocese) as monitor:
                monitoring_client.send_log(f"3️⃣ Extract Parishes: Collecting detailed parish information from {diocese_name}", "INFO")
                
                # Run parish extraction
                extract_parishes_main(args.diocese_id, args.max_parishes_per_diocese)
                
                # Update final progress (this would be better integrated into extract_parishes_main)
                monitor.update_progress(args.max_parishes_per_diocese, int(args.max_parishes_per_diocese * 0.85))
            
            monitoring_client.send_log("✅ Step 3 Complete: Parish extraction completed successfully", "INFO")
            
        except Exception as e:
            monitoring_client.report_error(
                error_type="ParishExtractionError",
                message=f"Parish extraction failed: {str(e)}",
                diocese=diocese_name if 'diocese_name' in locals() else None
            )
            logger.error(f"Parish extraction failed: {e}", exc_info=True)
    else:
        logger.info("\n--- Skipping Step 3: Extract Parishes ---")
        monitoring_client.send_log("⏭️ Step 3 Skipped: Extract Parishes", "INFO")

    # Step 4: Extract Schedules
    if not args.skip_schedules:
        try:
            logger.info("\n--- Step 4: Extract Schedules ---")
            monitoring_client.send_log("4️⃣ Extract Schedules: Visiting parish websites to gather mass and service times", "INFO")
            monitoring_client.update_extraction_status(
                status="running",
                current_diocese="Schedule Extraction",
                parishes_processed=0,
                total_parishes=args.num_parishes_for_schedule
            )
            
            extract_schedule_main(args.num_parishes_for_schedule)
            
            monitoring_client.send_log("✅ Step 4 Complete: Schedule extraction completed successfully", "INFO")
            
        except Exception as e:
            monitoring_client.report_error(
                error_type="ScheduleExtractionError",
                message=f"Schedule extraction failed: {str(e)}"
            )
            logger.error(f"Schedule extraction failed: {e}", exc_info=True)
    else:
        logger.info("\n--- Skipping Step 4: Extract Schedules ---")
        monitoring_client.send_log("⏭️ Step 4 Skipped: Extract Schedules", "INFO")

    # Step 5: Reporting
    if not args.skip_reporting:
        try:
            logger.info("\n--- Generating Reports ---")
            monitoring_client.send_log("📊 Generating statistical reports", "INFO")
            
            report_statistics_main()
            
            monitoring_client.send_log("✅ Report generation completed successfully", "INFO")
            
        except Exception as e:
            monitoring_client.report_error(
                error_type="ReportingError",
                message=f"Report generation failed: {str(e)}"
            )
            logger.error(f"Report generation failed: {e}", exc_info=True)
    else:
        logger.info("\n--- Skipping Report Generation ---")
        monitoring_client.send_log("⏭️ Report generation skipped", "INFO")

    # Pipeline completion
    total_time = time.time() - start_time
    monitoring_client.update_extraction_status(status="idle")
    monitoring_client.send_log(f"🎉 Pipeline completed in {total_time:.1f} seconds", "INFO")
    
    logger.info("USCCB data extraction pipeline completed!")


if __name__ == "__main__":
    main()