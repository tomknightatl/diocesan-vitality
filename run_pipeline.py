import argparse
from core.logger import get_logger
import config
from extract_dioceses import main as extract_dioceses_main
from find_parishes import find_parish_directories
from extract_parishes import main as extract_parishes_main
from extract_schedule import main as extract_schedule_main
from report_statistics import main as report_statistics_main

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Run the USCCB data extraction pipeline.")
    parser.add_argument("--skip_dioceses", action="store_true", help="Skip the diocese extraction step.")
    parser.add_argument("--skip_parish_directories", action="store_true", help="Skip finding parish directories.")
    parser.add_argument("--skip_parishes", action="store_true", help="Skip the parish extraction step.")
    parser.add_argument("--skip_schedules", action="store_true", help="Skip the schedule extraction step.")
    parser.add_argument("--skip_reporting", action="store_true", help="Skip the reporting step.")
    parser.add_argument("--diocese_id", type=int, help="ID of a specific diocese to process.")
    parser.add_argument("--max_parishes_per_diocese", type=int, default=config.DEFAULT_MAX_PARISHES_PER_DIOCESE, help="Max parishes to extract per diocese.")
    parser.add_argument("--num_parishes_for_schedule", type=int, default=config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE, help="Number of parishes to extract schedules for.")
    args = parser.parse_args()

    logger.info("Starting USCCB data extraction pipeline...")

    if not config.validate_config():
        logger.error("Exiting due to missing configuration.")
        return

    # If a specific diocese is targeted, we can skip the full diocese extraction
    if args.diocese_id and not args.skip_dioceses:
        logger.info(f"--diocese_id is set to {args.diocese_id}, skipping full diocese extraction.")
        args.skip_dioceses = True

    if not args.skip_dioceses:
        try:
            logger.info("\n--- Running Diocese Extraction ---")
            extract_dioceses_main(0) # Setting max_dioceses to 0 to run for all
        except Exception as e:
            logger.error(f"Diocese extraction failed: {e}", exc_info=True)
    else:
        logger.info("\n--- Skipping Diocese Extraction ---")

    if not args.skip_parish_directories:
        try:
            logger.info("\n--- Finding Parish Directories ---")
            find_parish_directories(diocese_id=args.diocese_id)
        except Exception as e:
            logger.error(f"Parish directory search failed: {e}", exc_info=True)
    else:
        logger.info("\n--- Skipping Parish Directory Search ---")

    if not args.skip_parishes:
        try:
            logger.info("\n--- Running Parish Extraction ---")
            extract_parishes_main(diocese_id=args.diocese_id, num_parishes_per_diocese=args.max_parishes_per_diocese)
        except Exception as e:
            logger.error(f"Parish extraction failed: {e}", exc_info=True)
    else:
        logger.info("\n--- Skipping Parish Extraction ---")

    if not args.skip_schedules:
        try:
            logger.info("\n--- Running Schedule Extraction ---")
            extract_schedule_main(args.num_parishes_for_schedule)
        except Exception as e:
            logger.error(f"Schedule extraction failed: {e}", exc_info=True)
    else:
        logger.info("\n--- Skipping Schedule Extraction ---")

    if not args.skip_reporting:
        try:
            logger.info("\n--- Running Reporting ---")
            report_statistics_main()
        except Exception as e:
            logger.error(f"Reporting failed: {e}", exc_info=True)
    else:
        logger.info("\n--- Skipping Reporting ---")

    logger.info("\nPipeline finished.")

if __name__ == "__main__":
    main()
