# Python Scripts and Commands

This document provides comprehensive information about all Python scripts in the root directory, including their commands, parameters, and purposes.

## Scripts Overview

### Pipeline Scripts (Execution Order)

### `run_pipeline.py` 🖥️
Diocesan Vitality data extraction pipeline with monitoring and real-time dashboard integration.
*   **Command:** `source venv/bin/activate && timeout 7200 python3 run_pipeline.py [OPTIONS]`
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
Extracts dioceses information from the Diocesan Vitality website.
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

### `report_statistics.py`
Generates statistics and visualizations of collected data from the database.
*   **Command:** `python report_statistics.py`
*   **Features:**
    *   Database record counts and trends
    *   Time-series visualizations
    *   PNG file generation for charts

### Scripts without Command-Line Parameters:
The following scripts are primarily modules or configuration files and do not accept direct command-line arguments:
*   `config.py`
*   `llm_utils.py`
*   `parish_extraction_core.py`
*   `parish_extractors.py`

## Usage Examples

### Pipeline Execution Examples

#### Monitoring-Enabled Pipeline (Recommended) 🖥️
```bash
# Basic monitored run with limits and 2-hour timeout
source venv/bin/activate && timeout 7200 python3 run_pipeline.py --max_parishes_per_diocese 10 --num_parishes_for_schedule 10

# Full extraction with monitoring (no limits)
source venv/bin/activate && timeout 7200 python3 run_pipeline.py --max_parishes_per_diocese 0 --num_parishes_for_schedule 0

# Background processing with monitoring
source venv/bin/activate && nohup python3 run_pipeline.py --max_parishes_per_diocese 10 --num_parishes_for_schedule 10 > pipeline.log 2>&1 &

# Process specific diocese with monitoring
source venv/bin/activate && python3 run_pipeline.py --diocese_id 2024 --max_parishes_per_diocese 25
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

---

## Script Categories and Functions

### Core Pipeline Scripts (Execution Order)
- **`run_pipeline.py`**: Main entry point orchestrating the entire data extraction pipeline
- **`extract_dioceses.py`**: Step 1 - Extracts diocese information from the conference website
- **`find_parishes.py`**: Step 2 - Analyzes diocese websites to find parish directory URLs
- **`async_extract_parishes.py`**: Step 3 - Asynchronously extracts detailed parish information
- **`extract_schedule_respectful.py`**: Step 4 - Extracts Mass schedules using respectful automation

### Core Components and Utilities
- **`parish_extraction_core.py`**: Data models (ParishData), enums, and fundamental utilities
- **`parish_extractors.py`**: Extractor classes for parsing different website layouts
- **`respectful_automation.py`**: Respectful web scraping with robots.txt compliance and rate limiting

### Configuration and Reporting
- **`config.py`**: Environment variables and central application configuration
- **`report_statistics.py`**: Generates statistics and time-series plots from database data

All scripts are well-structured with clear purposes in the data extraction pipeline.

---

## Development Commands

### Local Development Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# .\venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Edit with your API keys
```

### Start Development Services
```bash
# Terminal 1 - Backend API
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend Application
cd frontend
npm install  # First time only
npm run dev

# Terminal 3 - Pipeline with Monitoring
source venv/bin/activate
python run_pipeline.py --monitoring_url http://localhost:8000 \
  --max_parishes_per_diocese 10 --num_parishes_for_schedule 5
```

### Testing and Debugging Commands
```bash
# Test database connection
python -c "from core.db import get_supabase_client; print('DB:', get_supabase_client().table('Dioceses').select('*').limit(1).execute())"

# Test API endpoints
curl http://localhost:8000/api/dioceses
curl http://localhost:8000/api/monitoring/status

# Test frontend build
cd frontend && npm run build

# Clear Chrome cache (if issues)
rm -rf /tmp/chrome-*

# Check running processes
ps aux | grep chrome
ps aux | grep python
```

### Chrome WebDriver Debugging
```bash
# Update webdriver
python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"

# Run with visible Chrome (for debugging)
export CHROME_VISIBLE=true
python extract_schedule.py --num_parishes 1

# Test individual API keys
python -c "from core.ai_client import get_genai_client; print('AI:', get_genai_client().generate_content('Hello').text[:50])"
```

---

## Docker Commands

### Building Images Locally
```bash
# Build individual services for testing
docker build -f backend/Dockerfile -t diocesan-vitality:backend-dev backend/
docker build -f frontend/Dockerfile -t diocesan-vitality:frontend-dev frontend/
docker build -f Dockerfile.pipeline -t diocesan-vitality:pipeline-dev .

# Test pipeline container
docker run --rm --env-file .env diocesan-vitality:pipeline-dev python run_pipeline.py --skip_schedules
```

### Production Image Building with Timestamps
```bash
# Generate timestamp for deployment
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
echo "🏷️ Using timestamp: $TIMESTAMP"

# Build all three images with timestamped tags
docker build -f backend/Dockerfile -t tomatl/diocesan-vitality:backend-$TIMESTAMP backend/
docker build -f frontend/Dockerfile -t tomatl/diocesan-vitality:frontend-$TIMESTAMP frontend/
docker build -f Dockerfile.pipeline -t tomatl/diocesan-vitality:pipeline-$TIMESTAMP .

# Push to Docker Hub
docker push tomatl/diocesan-vitality:backend-$TIMESTAMP
docker push tomatl/diocesan-vitality:frontend-$TIMESTAMP
docker push tomatl/diocesan-vitality:pipeline-$TIMESTAMP
```

---

## Deployment Commands

### GitOps Deployment Process
```bash
# Update Kubernetes manifests with new image tags
sed -i "s|image: tomatl/diocesan-vitality:backend-.*|image: tomatl/diocesan-vitality:backend-$TIMESTAMP|g" k8s/backend-deployment.yaml
sed -i "s|image: tomatl/diocesan-vitality:frontend-.*|image: tomatl/diocesan-vitality:frontend-$TIMESTAMP|g" k8s/frontend-deployment.yaml
sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$TIMESTAMP|g" k8s/pipeline-deployment.yaml

# Commit and push to trigger ArgoCD deployment
git add k8s/backend-deployment.yaml k8s/frontend-deployment.yaml k8s/pipeline-deployment.yaml
git commit -m "Deploy timestamped images ($TIMESTAMP)"
git push origin main
```

### Monitoring Deployment
```bash
# Watch ArgoCD application sync
kubectl get application diocesan-vitality-app -n argocd -w

# Monitor pod rollout
kubectl get pods -n diocesan-vitality -w

# Verify new images are deployed
kubectl describe pods -n diocesan-vitality | grep "Image:" | sort | uniq
```

### Deployment Rollback
```bash
# Find previous image timestamp from git history
git log --oneline -10 | grep "Deploy timestamped images"

# Rollback to previous timestamp
ROLLBACK_TIMESTAMP="2025-09-15-17-30-45"  # Replace with desired timestamp
sed -i "s|image: tomatl/diocesan-vitality:backend-.*|image: tomatl/diocesan-vitality:backend-$ROLLBACK_TIMESTAMP|g" k8s/backend-deployment.yaml
sed -i "s|image: tomatl/diocesan-vitality:frontend-.*|image: tomatl/diocesan-vitality:frontend-$ROLLBACK_TIMESTAMP|g" k8s/frontend-deployment.yaml
sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$ROLLBACK_TIMESTAMP|g" k8s/pipeline-deployment.yaml

git add k8s/*.yaml
git commit -m "Rollback to images from $ROLLBACK_TIMESTAMP"
git push origin main
```

---

## Kubernetes Operations

### Pipeline Management
```bash
# View live pipeline logs
kubectl logs -f deployment/pipeline-deployment -n diocesan-vitality

# View last 50 lines of logs
kubectl logs deployment/pipeline-deployment -n diocesan-vitality --tail=50

# View logs with timestamps
kubectl logs deployment/pipeline-deployment -n diocesan-vitality --timestamps=true

# Check pipeline pod status
kubectl get pods -n diocesan-vitality -l app=pipeline

# Restart pipeline (triggers fresh execution)
kubectl rollout restart deployment pipeline-deployment -n diocesan-vitality
```

### Log Analysis and Filtering
```bash
# Filter logs for errors only
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep -i error

# Filter logs for specific diocese processing
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep "Diocese:"

# Filter logs for circuit breaker events
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep "Circuit breaker"

# Save logs to file for analysis
kubectl logs deployment/pipeline-deployment -n diocesan-vitality > pipeline-logs.txt

# Count error messages
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep -c "ERROR"

# Monitor extraction progress
kubectl logs -f deployment/pipeline-deployment -n diocesan-vitality | grep -E "Diocese:|Parish:|Schedule:"
```

### Resource Monitoring
```bash
# Check resource usage
kubectl top pods -n diocesan-vitality

# Check node capacity
kubectl describe nodes

# Monitor memory/CPU limits
kubectl describe pod -l app=pipeline -n diocesan-vitality | grep -A 10 "Limits\|Requests"

# Get detailed pod information
kubectl describe pod -l app=pipeline -n diocesan-vitality
```

---

## Database and API Testing

### Database Testing
```bash
# Test Supabase connection
python -c "
import config
from core.db import get_supabase_client
client = get_supabase_client()
response = client.table('Dioceses').select('*').limit(1).execute()
print('DB Connection:', 'SUCCESS' if response.data else 'FAILED')
"

# Test distributed coordination tables (if using scaling)
python -c "
from core.distributed_work_coordinator import DistributedWorkCoordinator
coordinator = DistributedWorkCoordinator()
print('✅ Coordination tables accessible')
"

# Validate configuration
python -c "import config; print(config.validate_config())"
```

### API Testing
```bash
# Test backend endpoints
curl http://localhost:8000/api/dioceses
curl http://localhost:8000/api/monitoring/status

# Test WebSocket connection (requires wscat: npm install -g wscat)
wscat -c ws://localhost:8000/ws/monitoring

# Check environment variables
cat .env | grep -v "^#"
```

---

## Troubleshooting Commands

### Common Issue Resolution
```bash
# Chrome/ChromeDriver issues
kubectl exec -it deployment/pipeline-deployment -n diocesan-vitality -- which google-chrome
kubectl exec -it deployment/pipeline-deployment -n diocesan-vitality -- chromedriver --version
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep -i "chrome\|webdriver"

# Database connection issues
kubectl get secrets -n diocesan-vitality
kubectl describe secret diocesan-vitality-secrets -n diocesan-vitality

# Missing dependencies
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep -i "modulenotfounderror\|importerror"

# Circuit breaker status
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep "Circuit breaker"
```

### Performance Analysis
```bash
# Find most recent errors
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep "ERROR" | tail -10

# Check processing statistics
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep -E "processed|extracted|completed"

# Monitor system resources
htop  # Local development
kubectl top pods -n diocesan-vitality  # Kubernetes
```

---

## Complete Deployment Script

For convenience, here's a complete script that handles the entire deployment process:

```bash
#!/bin/bash
# deploy.sh - Complete deployment script

set -e  # Exit on any error

echo "🚀 Starting deployment process..."

# Generate timestamp
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
echo "🏷️ Using timestamp: $TIMESTAMP"

# Build images
echo "🔨 Building Docker images..."
docker build -f backend/Dockerfile -t tomatl/diocesan-vitality:backend-$TIMESTAMP backend/
docker build -f frontend/Dockerfile -t tomatl/diocesan-vitality:frontend-$TIMESTAMP frontend/
docker build -f Dockerfile.pipeline -t tomatl/diocesan-vitality:pipeline-$TIMESTAMP .

# Push images
echo "📤 Pushing images to Docker Hub..."
docker push tomatl/diocesan-vitality:backend-$TIMESTAMP
docker push tomatl/diocesan-vitality:frontend-$TIMESTAMP
docker push tomatl/diocesan-vitality:pipeline-$TIMESTAMP

# Update manifests
echo "📝 Updating Kubernetes manifests..."
sed -i "s|image: tomatl/diocesan-vitality:backend-.*|image: tomatl/diocesan-vitality:backend-$TIMESTAMP|g" k8s/backend-deployment.yaml
sed -i "s|image: tomatl/diocesan-vitality:frontend-.*|image: tomatl/diocesan-vitality:frontend-$TIMESTAMP|g" k8s/frontend-deployment.yaml
sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$TIMESTAMP|g" k8s/pipeline-deployment.yaml

# Commit and push
echo "📦 Committing changes..."
git add k8s/backend-deployment.yaml k8s/frontend-deployment.yaml k8s/pipeline-deployment.yaml
git commit -m "Deploy timestamped images ($TIMESTAMP)"
git push origin main

echo "🎉 Deployment complete! ArgoCD will sync automatically."
echo "📊 Monitor with: kubectl get pods -n diocesan-vitality -w"
```

All scripts are well-structured with clear purposes in the data extraction pipeline.