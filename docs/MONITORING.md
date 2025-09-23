# Pipeline Monitoring and Real-time Dashboard

This comprehensive guide covers monitoring the pipeline through logs, real-time dashboard, multi-worker support, and manual script execution for debugging and development.

## 📋 Table of Contents
- [Real-time Dashboard](#real-time-dashboard)
- [Multi-Worker Monitoring](#multi-worker-monitoring)
- [API Endpoints](#api-endpoints)
- [Kubernetes Pipeline Logs](#kubernetes-pipeline-logs)
- [Manual Python Script Execution](#manual-python-script-execution)
- [Local Development Monitoring](#local-development-monitoring)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)

---

## 📊 Real-time Dashboard

### Overview
The real-time monitoring dashboard provides **live operational visibility** into the Diocesan Vitality parish extraction system. It displays real-time extraction progress, system health, circuit breaker status, performance metrics, and error tracking through an intuitive web interface.

**Multi-Worker Support**: The dashboard supports monitoring multiple distributed workers with both aggregate and individual views, enabling scalable monitoring for distributed pipeline deployments.

### Dashboard Access
**Production Dashboard:** https://diocesanvitality.org/dashboard

**Local Dashboard:** http://localhost:5173/dashboard (when running locally)

### Features

#### 📊 **Real-time System Monitoring**
- **System Health**: CPU usage, memory utilization, uptime tracking
- **Extraction Status**: Live progress with parishes processed and success rates
- **Performance Metrics**: Parishes per minute, queue size, pool utilization
- **Alert System**: Real-time error notifications and warnings

#### 🔧 **Multi-Worker Support**
- **Worker Selector**: Dropdown to switch between aggregate view and individual workers
- **Aggregate Metrics**: Combined statistics from all active workers
- **Worker Status**: Individual worker health indicators and activity status
- **Distributed Progress**: System-wide extraction progress across multiple workers

#### 🛡️ **Enhanced Circuit Breaker Visualization**
- **Horizontal Layout**: 17+ circuit breakers displayed in organized rows with header columns
- **Health-Based Sorting**: Automatically sorts by health score with least healthy circuits at top
- **Color-Coded Health Indicators**: Green (healthy), yellow (warning), red (critical) status
- **Circuit States**: CLOSED/OPEN/HALF-OPEN status with real-time updates
- **Statistics**: Request counts, success rates, failure tracking with zero-value highlighting
- **Health Scoring**: Dynamic health calculation based on state, success rate, and blocked requests
- **Comprehensive Metrics**: Name, State, Requests, Health %, Success Rate, Failures, Blocked columns

#### 📈 **Performance Analytics**
- **Live Metrics**: Real-time performance tracking and trends
- **Extraction History**: Recent extraction results and success rates
- **Resource Utilization**: WebDriver pool usage and efficiency
- **Throughput Analysis**: Parishes processed per minute trends

#### 🚨 **Error Tracking & Alerts**
- **Live Error Feed**: Real-time error notifications with severity levels
- **Error Classification**: Categorized by type (parsing, network, timeout)
- **Diocese Context**: Error tracking per diocese for targeted debugging
- **Error History**: Recent error patterns and frequency analysis

#### 📋 **Live Extraction Log**
- **Real-time Logging**: Live stream of extraction activities
- **Log Levels**: INFO, WARNING, ERROR with color coding
- **Searchable History**: Scrollable log with timestamp filtering
- **Module Tracking**: Log entries categorized by extraction module

### WebSocket Connection
The dashboard connects via WebSocket for real-time updates:
- **Production**: `wss://api.diocesanvitality.org/ws/monitoring`
- **Development**: `ws://localhost:8000/ws/monitoring`

If you see "Dashboard disconnected", check:
1. Backend service is running
2. WebSocket endpoint is accessible
3. No firewall blocking WebSocket connections

### Setting Up Local Dashboard

**Complete Setup Instructions:**

1. **Activate Virtual Environment** (if using monitored pipeline):
   ```bash
   source venv/bin/activate
   ```

2. **Start the Backend Server** (in separate terminal):
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Start the Frontend Server** (in separate terminal):
   ```bash
   cd frontend
   npm run dev
   ```

4. **Open Dashboard**:
   Navigate to `http://localhost:5173/dashboard`

5. **Run Monitoring-Enabled Pipeline**:
   ```bash
   # Basic run with monitoring and 2-hour timeout
   source venv/bin/activate && timeout 7200 python3 run_pipeline.py --max_parishes_per_diocese 10 --num_parishes_for_schedule 10

   # Or test dashboard functionality
   python3 test_dashboard.py --mode extraction
   ```

---

## 🔧 Multi-Worker Monitoring

### Overview
The monitoring system supports both single and multi-worker deployments with two distinct modes:

1. **Aggregate View** - Combined metrics from all workers (default)
2. **Individual Worker View** - Detailed view of a specific worker

### Architecture

#### MonitoringManager Backend
- **Multi-worker support**: Tracks individual worker data in `self.workers` dictionary
- **Aggregate calculations**: Combines metrics across workers for system-wide view
- **Backward compatibility**: Maintains single-worker functionality

#### Dashboard Features
- **Worker Selector**: Switch between aggregate view and individual workers
- **Aggregate Metrics**: Shows combined data from all active workers
- **Worker Status Indicators**: Color-coded badges for each worker (🟢 running, 🟡 idle, 🔴 error, ⚪ stale)
- **Enhanced Extraction Status**: Displays active worker count and distributed progress

### Worker Status Classifications
Workers are classified based on their last update time:
- **running**: Currently active and processing (≤1min since last update)
- **idle**: Available but not currently processing
- **error**: Encountered an error state
- **stale**: No updates for >5 minutes

### Usage

#### Single Worker Deployment
No changes required - existing scripts continue to work:

```python
# Standard single-worker setup
monitoring_client = get_monitoring_client("http://localhost:8000")
```

#### Multi-Worker Deployment

**1. Initialize Workers with IDs**
```python
import os
from core.monitoring_client import get_monitoring_client

# Generate unique worker ID
worker_id = os.environ.get('WORKER_ID', os.environ.get('HOSTNAME'))

# Initialize monitoring with worker ID
monitoring_client = get_monitoring_client(
    base_url="http://localhost:8000",
    worker_id=worker_id
)
```

**2. Context Manager Usage**
```python
# Extraction monitoring with worker identification
with ExtractionMonitoring("Diocese Name", 100, worker_id="worker-pod-12345") as monitor:
    # Extraction work here
    monitor.update_progress(50, 45)
```

### Data Aggregation

#### Extraction Status
```python
{
    "status": "running",  # running if any worker active
    "active_workers": 2,
    "total_workers": 3,
    "parishes_processed": 150,  # sum across workers
    "total_parishes": 500,      # sum across workers
    "success_rate": 87.5,       # weighted average
    "current_diocese": "Diocese A, Diocese B"  # comma-separated
}
```

#### Circuit Breakers
```python
{
    "circuit_name": {
        "state": "CLOSED",           # worst state wins (OPEN > HALF_OPEN > CLOSED)
        "total_requests": 1250,      # sum across workers
        "total_successes": 1100,     # sum across workers
        "total_failures": 150,       # sum across workers
        "total_blocked": 25,         # sum across workers
        "success_rate": 88.0         # calculated from aggregated data
    }
}
```

### Kubernetes Configuration
Configure workers with unique identifiers:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pipeline-workers
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: pipeline
        env:
        - name: WORKER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: MONITORING_URL
          value: "http://monitoring-service:8000"
```

### Benefits
1. **Scalability**: Monitor unlimited number of workers
2. **Visibility**: See both system-wide and individual worker performance
3. **Troubleshooting**: Isolate issues to specific workers
4. **Load Balancing**: Identify uneven work distribution
5. **Backward Compatibility**: Existing single-worker setups continue working

---

## 🔌 API Endpoints

### Current Monitoring API

#### Worker Management
- `GET /api/monitoring/workers` - List all workers with basic status
- `GET /api/monitoring/worker/{worker_id}` - Get detailed worker status
- `POST /api/monitoring/mode/{mode}` - Switch between aggregate/individual mode

#### Status Updates
- `POST /api/monitoring/worker/{worker_id}/extraction_status` - Update worker extraction status
- `POST /api/monitoring/worker/{worker_id}/circuit_breakers` - Update worker circuit breakers
- `POST /api/monitoring/extraction_status` - Update extraction status (single-worker compatibility)
- `POST /api/monitoring/circuit_breakers` - Update circuit breaker status (single-worker compatibility)

#### Real-time Data
- `POST /api/monitoring/performance` - Update performance metrics
- `POST /api/monitoring/error` - Report an error
- `POST /api/monitoring/extraction_complete` - Report extraction completion
- `POST /api/monitoring/log` - Send live log entry

#### Monitoring Status
- `GET /api/monitoring/status` - Get current monitoring status
- `WS /ws/monitoring` - WebSocket endpoint for real-time updates

---

## 🏭 Kubernetes Pipeline Logs

### Viewing Live Pipeline Logs
The pipeline runs as a Deployment in Kubernetes. Here are the key commands to view logs:

```bash
# View live logs (follows new entries)
kubectl logs -f deployment/pipeline-deployment -n diocesan-vitality

# View last 50 lines of logs
kubectl logs deployment/pipeline-deployment -n diocesan-vitality --tail=50

# View logs with timestamps
kubectl logs deployment/pipeline-deployment -n diocesan-vitality --timestamps=true

# View logs from the last hour
kubectl logs deployment/pipeline-deployment -n diocesan-vitality --since=1h
```

### Pipeline Pod Management
```bash
# Check pipeline pod status
kubectl get pods -n diocesan-vitality -l app=pipeline

# Get detailed pod information
kubectl describe pod -l app=pipeline -n diocesan-vitality

# View logs of specific pod (if multiple exist)
kubectl logs <pod-name> -n diocesan-vitality

# Follow logs of specific pod
kubectl logs -f <pod-name> -n diocesan-vitality
```

### Pipeline Deployment Management
```bash
# Check deployment status
kubectl get deployment pipeline-deployment -n diocesan-vitality

# View deployment details and events
kubectl describe deployment pipeline-deployment -n diocesan-vitality

# Restart pipeline (triggers fresh execution)
kubectl rollout restart deployment pipeline-deployment -n diocesan-vitality

# Check rollout status
kubectl rollout status deployment pipeline-deployment -n diocesan-vitality
```

### Log Filtering and Analysis
```bash
# Filter logs for errors only
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep -i error

# Filter logs for specific diocese processing
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep "Diocese:"

# Filter logs for circuit breaker events
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep "Circuit breaker"

# Save logs to file for analysis
kubectl logs deployment/pipeline-deployment -n diocesan-vitality > pipeline-logs.txt
```

---

## 🐍 Manual Python Script Execution

### Prerequisites
```bash
# Ensure you're in the project directory
cd /path/to/Diocesan Vitality

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Set up environment variables (if needed)
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-supabase-key"
export GENAI_API_KEY_Diocesan Vitality="your-genai-key"
export SEARCH_API_KEY_Diocesan Vitality="your-search-key"
export SEARCH_CX_Diocesan Vitality="your-search-cx"
```

### Running Individual Pipeline Components

For comprehensive command examples and parameters for all scripts, see the **[📝 Commands Guide](COMMANDS.md)**.

**Quick Examples:**
```bash
# Diocese extraction
python extract_dioceses.py --max_dioceses 5

# Parish directory discovery
python find_parishes.py --diocese_id 123

# High-performance parish extraction
python async_extract_parishes.py --diocese_id 123 --pool_size 6 --batch_size 12

# Schedule extraction
python extract_schedule.py --num_parishes 100
```

**→ See [Commands Guide](COMMANDS.md) for complete parameters and usage examples.**

### Complete Pipeline Execution

For comprehensive pipeline execution examples, see the **[📝 Commands Guide](COMMANDS.md)**.

**Quick Examples:**
```bash
# Basic pipeline with monitoring
python run_pipeline.py --max_parishes_per_diocese 50 --num_parishes_for_schedule 100

# Background execution
nohup python run_pipeline.py --max_parishes_per_diocese 25 > pipeline.log 2>&1 &

# Process specific diocese
python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 0
```

**→ See [Commands Guide](COMMANDS.md) for complete pipeline execution options.**

### Testing Scripts

#### Dashboard Testing
```bash
# Basic monitoring test
python3 test_dashboard.py --mode basic

# Extraction simulation test (recommended)
python3 test_dashboard.py --mode extraction

# Continuous monitoring demo
python3 test_dashboard.py --mode continuous
```

#### Circuit Breaker Testing
```bash
# Test circuit breaker functionality
python test_circuit_breaker.py
```

#### Async Processing Testing
```bash
# Test async logic
python test_async_logic.py

# Test async extraction (requires WebDriver)
python test_async_extraction.py
```

---

## 🔧 Local Development Monitoring

### Running Backend API Locally
```bash
cd backend
source ../venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Running Frontend Locally
```bash
cd frontend
npm install
npm run dev
```

### Monitoring Local Pipeline
```bash
# Run monitored pipeline locally
source venv/bin/activate
python run_pipeline.py \
  --max_parishes_per_diocese 5 \
  --num_parishes_for_schedule 10 \
  --monitoring_url "http://localhost:8000"

# View dashboard at: http://localhost:5173/dashboard
```

---

## 🚨 Troubleshooting Common Issues

### Pipeline Not Starting
```bash
# Check pod status
kubectl get pods -n diocesan-vitality -l app=pipeline

# Check events and errors
kubectl describe pod -l app=pipeline -n diocesan-vitality

# Check deployment status
kubectl get deployment pipeline-deployment -n diocesan-vitality

# Common fixes:
kubectl rollout restart deployment pipeline-deployment -n diocesan-vitality
```

### Dashboard Not Connecting
1. **Check Backend Status**:
   ```bash
   curl http://localhost:8000/api/monitoring/status
   ```

2. **Verify WebSocket Endpoint**:
   ```bash
   wscat -c ws://localhost:8000/ws/monitoring
   ```

3. **Check Network Configuration**:
   - Ensure ports 8000 (backend) and 5173 (frontend) are accessible
   - Verify CORS settings in backend configuration

### Missing Dependencies
```bash
# Check logs for import errors
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep -i "modulenotfounderror\|importerror"

# If missing PyPDF2 or other packages:
# 1. Add to requirements.txt
# 2. Rebuild Docker image
# 3. Restart deployment
```

### Database Connection Issues
```bash
# Check if secrets exist
kubectl get secrets -n diocesan-vitality

# Verify secret contents (without exposing values)
kubectl describe secret diocesan-vitality-secrets -n diocesan-vitality

# Test connection manually
python -c "import config; print(config.validate_config())"
```

### WebDriver/Chrome Issues
```bash
# Check Chrome installation in container
kubectl exec -it deployment/pipeline-deployment -n diocesan-vitality -- which google-chrome

# Check ChromeDriver
kubectl exec -it deployment/pipeline-deployment -n diocesan-vitality -- chromedriver --version

# View Chrome-specific errors
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep -i "chrome\|webdriver"
```

### Circuit Breaker Activation
```bash
# View circuit breaker status
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep "Circuit breaker"

# Check dashboard for circuit breaker states
# Visit: https://diocesanvitality.org/dashboard

# Reset by restarting pipeline
kubectl rollout restart deployment pipeline-deployment -n diocesan-vitality
```

### Performance Issues
```bash
# Check resource usage
kubectl top pods -n diocesan-vitality

# Check node capacity
kubectl describe nodes

# Monitor memory/CPU limits
kubectl describe pod -l app=pipeline -n diocesan-vitality | grep -A 10 "Limits\|Requests"
```

### Log Analysis Commands
```bash
# Count error messages
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep -c "ERROR"

# Find most recent errors
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep "ERROR" | tail -10

# Check processing statistics
kubectl logs deployment/pipeline-deployment -n diocesan-vitality | grep -E "processed|extracted|completed"

# Monitor extraction progress
kubectl logs -f deployment/pipeline-deployment -n diocesan-vitality | grep -E "Diocese:|Parish:|Schedule:"
```

---

## 📊 Dashboard Integration

### Integration with Extraction Scripts

#### Basic Integration
```python
from core.monitoring_client import get_monitoring_client

# Get monitoring client
client = get_monitoring_client("http://localhost:8000")

# Report extraction start
client.extraction_started("Archdiocese of Atlanta", 25)

# Update progress
client.extraction_progress("Archdiocese of Atlanta", 10, 25, 85.0)

# Report completion
client.extraction_finished("Archdiocese of Atlanta", 24, 96.0, 145.5)
```

#### Context Manager (Recommended)
```python
from core.monitoring_client import ExtractionMonitoring

# Automatic monitoring with context manager
with ExtractionMonitoring("Archdiocese of Atlanta", 25) as monitor:
    for i, parish in enumerate(parishes):
        # Process parish...
        successful = process_parish(parish)

        # Update progress automatically
        monitor.update_progress(i + 1, successful_count)
```

#### Circuit Breaker Integration
```python
# Report circuit breaker events
client.circuit_breaker_opened("diocese_page_load", "Multiple timeouts")
client.circuit_breaker_closed("diocese_page_load")

# Update circuit breaker status
circuit_status = {
    "diocese_page_load": {
        "state": "CLOSED",
        "total_requests": 45,
        "success_rate": "95.6%",
        "total_failures": 2,
        "total_blocked": 0
    }
}
client.update_circuit_breakers(circuit_status)
```

---

## 📝 Log Examples and Interpretations

### Successful Pipeline Start
```
2025-09-13 19:57:58,776 - core.circuit_breaker - INFO - 🔌 Circuit Breaker Manager initialized
2025-09-13 19:57:58,789 - core.circuit_breaker - INFO - 🔌 Circuit breaker 'webdriver_javascript' initialized
2025-09-13 19:57:59,123 - __main__ - INFO - Starting Diocesan Vitality data extraction pipeline...
2025-09-13 19:58:00,456 - __main__ - INFO - --- Running Diocese Extraction ---
```

### Diocese Processing
```
2025-09-13 20:01:15,234 - extract_dioceses - INFO - Processing diocese: Diocese of Example (ID: 123)
2025-09-13 20:01:16,789 - extract_dioceses - INFO - Successfully extracted diocese data
```

### Parish Extraction Progress
```
2025-09-13 20:05:20,123 - extract_parishes - INFO - Processing 25 parishes from Diocese of Example
2025-09-13 20:05:21,456 - extract_parishes - INFO - Extracted parish: St. Example Parish (1/25)
2025-09-13 20:05:22,789 - extract_parishes - INFO - Extracted parish: Holy Example Church (2/25)
```

### Circuit Breaker Events
```
2025-09-13 20:10:30,123 - core.circuit_breaker - WARNING - Circuit breaker 'webdriver_javascript' failure (3/5)
2025-09-13 20:10:35,456 - core.circuit_breaker - ERROR - Circuit breaker 'webdriver_javascript' opened due to failures
2025-09-13 20:11:35,789 - core.circuit_breaker - INFO - Circuit breaker 'webdriver_javascript' attempting half-open
```

### Common Error Patterns
```bash
# Import/dependency errors
ModuleNotFoundError: No module named 'PyPDF2'

# WebDriver errors
selenium.common.exceptions.WebDriverException: chrome not reachable

# Database connection errors
supabase.exceptions.AuthApiException: Invalid API key

# Resource constraints
Error: failed to create containerd task: OCI runtime create failed
```

For more detailed command documentation, see [COMMANDS.md](COMMANDS.md).
