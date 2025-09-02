import argparse
import config
from extract_dioceses import main as extract_dioceses_main
from find_parishes import find_parish_directories
from extract_parishes import main as extract_parishes_main
from extract_schedule import main as extract_schedule_main

def main():
    parser = argparse.ArgumentParser(description="Run the USCCB data extraction pipeline.")
    parser.add_argument(
        "--skip_dioceses",
        action="store_true",
        help="Skip the diocese extraction step."
    )
    parser.add_argument(
        "--skip_parish_directories",
        action="store_true",
        help="Skip finding parish directories."
    )
    parser.add_argument(
        "--skip_parishes",
        action="store_true",
        help="Skip the parish extraction step."
    )
    parser.add_argument(
        "--skip_schedules",
        action="store_true",
        help="Skip the schedule extraction step."
    )
    parser.add_argument(
        "--max_dioceses",
        type=int,
        default=0,
        help="Max number of dioceses to extract."
    )
    parser.add_argument(
        "--max_parishes_per_diocese",
        type=int,
        default=0,
        help="Max parishes to extract per diocese."
    )
    parser.add_argument(
        "--num_parishes_for_schedule",
        type=int,
        default=5,
        help="Number of parishes to extract schedules for."
    )

    args = parser.parse_args()

    print("Starting USCCB data extraction pipeline...")

    if not config.validate_config():
        print("Exiting due to missing configuration.")
        return

    if not args.skip_dioceses:
        print("\n--- Running Diocese Extraction ---")
        extract_dioceses_main(args.max_dioceses)
    else:
        print("\n--- Skipping Diocese Extraction ---")

    if not args.skip_parish_directories:
        print("\n--- Finding Parish Directories ---")
        find_parish_directories(args.max_dioceses)
    else:
        print("\n--- Skipping Parish Directory Search ---")

    if not args.skip_parishes:
        print("\n--- Running Parish Extraction ---")
        extract_parishes_main(args.max_dioceses, args.max_parishes_per_diocese)
    else:
        print("\n--- Skipping Parish Extraction ---")

    if not args.skip_schedules:
        print("\n--- Running Schedule Extraction ---")
        extract_schedule_main(args.num_parishes_for_schedule)
    else:
        print("\n--- Skipping Schedule Extraction ---")

    print("\nPipeline finished.")

if __name__ == "__main__":
    main()
