Here are the commands and parameters for each `.py` script in the root directory:
### `run_pipeline.py`
Runs the USCCB data extraction pipeline, orchestrating other scripts.
*   **Command:** `python run_pipeline.py [OPTIONS]`
*   **Parameters:**
    *   `--skip_dioceses` (action: `store_true`): Skip the diocese extraction step.
    *   `--skip_parish_directories` (action: `store_true`): Skip finding parish directories.
    *   `--skip_parishes` (action: `store_true`): Skip the parish extraction step.
    *   `--skip_schedules` (action: `store_true`): Skip the schedule extraction step.
    *   `--skip_reporting` (action: `store_true`): Skip the reporting step.
    *   `--diocese_id` (type: `int`, default: `2024`): ID of a specific diocese to process. Defaults to 2024 (Archdiocese of Atlanta).
    *   `--max_parishes_per_diocese` (type: `int`, default: `config.DEFAULT_MAX_PARISHES_PER_DIOCESE`): Max parishes to extract per diocese.
    *   `--num_parishes_for_schedule` (type: `int`, default: `config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE`): Number of parishes to extract schedules for.

### `extract_dioceses.py`
Extracts dioceses information from the USCCB website.
*   **Command:** `python extract_dioceses.py [OPTIONS]`
*   **Parameters:**
    *   `--max_dioceses` (type: `int`, default: `5`): Maximum number of dioceses to extract. Set to 0 or None for no limit.

### `find_parishes.py`
Finds parish directory URLs on diocesan websites.
*   **Command:** `python find_parishes.py [OPTIONS]`
*   **Parameters:**
    *   `--diocese_id` (type: `int`, default: `None`): ID of a specific diocese to process. If not provided, processes all.
    *   `--max_dioceses_to_process` (type: `int`, default: `5`): Maximum number of dioceses to process. Set to 0 for no limit.

### `extract_parishes.py`
Extracts parish information from diocese websites.
*   **Command:** `python extract_parishes.py [OPTIONS]`
*   **Parameters:**
    *   `--diocese_id` (type: `int`, default: `None`): ID of a specific diocese to process. If not provided, processes all.
    *   `--num_parishes_per_diocese` (type: `int`, default: `5`): Maximum number of parishes to extract from each diocese. Set to 0 for no limit.

### `extract_schedule.py`
Extracts adoration and reconciliation schedules from parish websites.
*   **Command:** `python extract_schedule.py [OPTIONS]`
*   **Parameters:**
    *   `--num_parishes` (type: `int`, default: `config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE`): Maximum number of parishes to extract from. Set to 0 for no limit.
    *   `--parish_id` (type: `int`, default: `None`): ID of a specific parish to process. Overrides `--num_parishes`.

### Scripts without Command-Line Parameters:
The following scripts are primarily modules or configuration files and do not accept direct command-line arguments:
*   `config.py`
*   `llm_utils.py`
*   `parish_extraction_core.py`
*   `parish_extractors.py`
*   `report_statistics.py` (though it can be run directly, its `main` function doesn't take parameters)