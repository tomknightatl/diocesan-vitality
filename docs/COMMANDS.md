Here are the commands and parameters for each `.py` script in the root directory:

## Pipeline Scripts

### `run_pipeline.py`
Standard USCCB data extraction pipeline without monitoring.
*   **Command:** `python run_pipeline.py [OPTIONS]`
*   **Parameters:**
    *   `--skip_dioceses` (action: `store_true`): Skip the diocese extraction step.
    *   `--skip_parish_directories` (action: `store_true`): Skip finding parish directories.
    *   `--skip_parishes` (action: `store_true`): Skip the parish extraction step.
    *   `--skip_schedules` (action: `store_true`): Skip the schedule extraction step.
    *   `--skip_reporting` (action: `store_true`): Skip the reporting step.
    *   `--diocese_id` (type: `int`): ID of a specific diocese to process.
    *   `--max_parishes_per_diocese` (type: `int`, default: `config.DEFAULT_MAX_PARISHES_PER_DIOCESE`): Max parishes to extract per diocese.
    *   `--num_parishes_for_schedule` (type: `int`, default: `config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE`): Number of parishes to extract schedules for.

### `run_pipeline_monitored.py` 🖥️
**NEW** - Monitoring-enabled pipeline with real-time dashboard integration and WebSocket updates.
*   **Command:** `source venv/bin/activate && timeout 7200 python3 run_pipeline_monitored.py [OPTIONS]`
*   **Parameters:**
    *   `--skip_dioceses` (action: `store_true`): Skip the diocese extraction step.
    *   `--skip_parish_directories` (action: `store_true`): Skip finding parish directories.
    *   `--skip_parishes` (action: `store_true`): Skip the parish extraction step.
    *   `--skip_schedules` (action: `store_true`): Skip the schedule extraction step.
    *   `--skip_reporting` (action: `store_true`): Skip the reporting step.
    *   `--diocese_id` (type: `int`): ID of a specific diocese to process.
    *   `--max_parishes_per_diocese` (type: `int`, default: `config.DEFAULT_MAX_PARISHES_PER_DIOCESE`): Max parishes to extract per diocese.
    *   `--num_parishes_for_schedule` (type: `int`, default: `config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE`): Number of parishes to extract schedules for.
    *   `--monitoring_url` (type: `str`, default: `"http://localhost:8000"`): Monitoring backend URL.
    *   `--disable_monitoring` (action: `store_true`): Disable monitoring integration.
*   **Features:**
    *   Real-time extraction progress tracking
    *   Live system health monitoring
    *   Circuit breaker status visualization
    *   Performance metrics and error tracking
    *   WebSocket-based dashboard updates

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
Extracts parish information from diocese websites (sequential processing).
*   **Command:** `python extract_parishes.py [OPTIONS]`
*   **Parameters:**
    *   `--diocese_id` (type: `int`, default: `None`): ID of a specific diocese to process. If not provided, processes all.
    *   `--num_parishes_per_diocese` (type: `int`, default: `5`): Maximum number of parishes to extract from each diocese. Set to 0 for no limit.

### `async_extract_parishes.py` ⚡
**NEW** - High-performance concurrent parish extraction with 60% faster processing.
*   **Command:** `python async_extract_parishes.py [OPTIONS]`
*   **Parameters:**
    *   `--diocese_id` (type: `int`, default: `None`): ID of a specific diocese to process. If not provided, processes all.
    *   `--num_parishes_per_diocese` (type: `int`, default: `5`): Maximum number of parishes to extract from each diocese. Set to 0 for no limit.
    *   `--pool_size` (type: `int`, default: `4`): WebDriver pool size for concurrent requests (2-8 recommended).
    *   `--batch_size` (type: `int`, default: `8`): Batch size for concurrent parish detail requests (8-15 optimal).
    *   `--max_concurrent_dioceses` (type: `int`, default: `2`): Maximum dioceses to process concurrently (1-3).
*   **Performance:** 60% faster than sequential processing, optimized for dioceses with 20+ parishes.
*   **Features:**
    *   Asyncio-based concurrent request handling
    *   Connection pooling with intelligent rate limiting
    *   Circuit breaker protection for external service failures
    *   Memory-efficient processing with automatic garbage collection

### `extract_schedule.py`
Extracts adoration and reconciliation schedules from parish websites.
*   **Command:** `python extract_schedule.py [OPTIONS]`
*   **Parameters:**
    *   `--num_parishes` (type: `int`, default: `config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE`): Maximum number of parishes to extract from. Set to 0 for no limit.
    *   `--parish_id` (type: `int`, default: `None`): ID of a specific parish to process. Overrides `--num_parishes`.

### Test Scripts:
*   `test_circuit_breaker.py` - Tests circuit breaker functionality with different failure scenarios
*   `test_async_logic.py` - Tests async concurrent processing logic and performance
*   `test_async_extraction.py` - Comprehensive async extraction system tests (requires WebDriver)
*   `test_dashboard.py` 🖥️ **NEW** - Tests monitoring dashboard functionality with simulation data

### `test_dashboard.py` 🖥️
Tests the real-time monitoring dashboard with simulated extraction activity.
*   **Command:** `python test_dashboard.py [OPTIONS]`
*   **Parameters:**
    *   `--mode` (choices: `["basic", "extraction", "continuous"]`, default: `"extraction"`): Test mode to run
        *   `basic`: Tests basic monitoring functions without async
        *   `extraction`: Simulates complete extraction activity for dashboard testing
        *   `continuous`: Runs continuous monitoring demo with periodic updates

### Scripts without Command-Line Parameters:
The following scripts are primarily modules or configuration files and do not accept direct command-line arguments:
*   `config.py`
*   `llm_utils.py`
*   `parish_extraction_core.py`
*   `parish_extractors.py`
*   `report_statistics.py` (though it can be run directly, its `main` function doesn't take parameters)

## Usage Examples

### Pipeline Execution Examples

#### Monitoring-Enabled Pipeline (Recommended) 🖥️
```bash
# Basic monitored run with limits and 2-hour timeout
source venv/bin/activate && timeout 7200 python3 run_pipeline_monitored.py --max_parishes_per_diocese 10 --num_parishes_for_schedule 10

# Full extraction with monitoring (no limits)
source venv/bin/activate && timeout 7200 python3 run_pipeline_monitored.py --max_parishes_per_diocese 0 --num_parishes_for_schedule 0

# Background processing with monitoring
source venv/bin/activate && nohup python3 run_pipeline_monitored.py --max_parishes_per_diocese 10 --num_parishes_for_schedule 10 > pipeline.log 2>&1 &

# Process specific diocese with monitoring
source venv/bin/activate && python3 run_pipeline_monitored.py --diocese_id 2024 --max_parishes_per_diocese 25
```

#### Standard Pipeline (Without Monitoring)
```bash
# Basic run
python run_pipeline.py --max_parishes_per_diocese 10 --num_parishes_for_schedule 10

# Full extraction without limits
python run_pipeline.py --max_parishes_per_diocese 0 --num_parishes_for_schedule 0
```

### Performance Comparison Examples:

#### Basic Parish Extraction (Small Diocese)
```bash
# Sequential (traditional)
python extract_parishes.py --diocese_id 2024 --num_parishes_per_diocese 10

# Concurrent (60% faster)
python async_extract_parishes.py --diocese_id 2024 --num_parishes_per_diocese 10
```

#### Large Diocese Extraction (50+ Parishes)
```bash
# High-performance concurrent configuration
python async_extract_parishes.py \
  --diocese_id 2024 \
  --num_parishes_per_diocese 50 \
  --pool_size 6 \
  --batch_size 12
```

#### Maximum Performance (All Parishes)
```bash
# Process all parishes with maximum concurrency
python async_extract_parishes.py \
  --diocese_id 2024 \
  --num_parishes_per_diocese 0 \
  --pool_size 8 \
  --batch_size 15
```

### Dashboard Testing Examples
```bash
# Basic monitoring functionality test
python test_dashboard.py --mode basic

# Full extraction simulation for dashboard testing
python test_dashboard.py --mode extraction

# Continuous monitoring demo
python test_dashboard.py --mode continuous
```