# Pipeline Logging and Monitoring Guide

This guide covers how to view logs, monitor the pipeline, and run Python scripts manually for debugging and development.

## 📋 Table of Contents
- [Kubernetes Pipeline Logs](#kubernetes-pipeline-logs)
- [Real-time Dashboard Monitoring](#real-time-dashboard-monitoring)
- [Manual Python Script Execution](#manual-python-script-execution)
- [Local Development Monitoring](#local-development-monitoring)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)

---

## 🏭 Kubernetes Pipeline Logs

### Viewing Live Pipeline Logs
The pipeline runs as a Deployment in Kubernetes. Here are the key commands to view logs:

```bash
# View live logs (follows new entries)
kubectl logs -f deployment/pipeline-deployment -n usccb

# View last 50 lines of logs
kubectl logs deployment/pipeline-deployment -n usccb --tail=50

# View logs with timestamps
kubectl logs deployment/pipeline-deployment -n usccb --timestamps=true

# View logs from the last hour
kubectl logs deployment/pipeline-deployment -n usccb --since=1h
```

### Pipeline Pod Management
```bash
# Check pipeline pod status
kubectl get pods -n usccb -l app=pipeline

# Get detailed pod information
kubectl describe pod -l app=pipeline -n usccb

# View logs of specific pod (if multiple exist)
kubectl logs <pod-name> -n usccb

# Follow logs of specific pod
kubectl logs -f <pod-name> -n usccb
```

### Pipeline Deployment Management
```bash
# Check deployment status
kubectl get deployment pipeline-deployment -n usccb

# View deployment details and events
kubectl describe deployment pipeline-deployment -n usccb

# Restart pipeline (triggers fresh execution)
kubectl rollout restart deployment pipeline-deployment -n usccb

# Check rollout status
kubectl rollout status deployment pipeline-deployment -n usccb
```

### Log Filtering and Analysis
```bash
# Filter logs for errors only
kubectl logs deployment/pipeline-deployment -n usccb | grep -i error

# Filter logs for specific diocese processing
kubectl logs deployment/pipeline-deployment -n usccb | grep "Diocese:"

# Filter logs for circuit breaker events
kubectl logs deployment/pipeline-deployment -n usccb | grep "Circuit breaker"

# Save logs to file for analysis
kubectl logs deployment/pipeline-deployment -n usccb > pipeline-logs.txt
```

---

## 📊 Real-time Dashboard Monitoring

### Dashboard Access
The pipeline provides real-time monitoring through a web dashboard:

**Production Dashboard:** https://usccb.diocesanvitality.org/dashboard

**Local Dashboard:** http://localhost:3000/dashboard (when running locally)

### Dashboard Features
The dashboard provides real-time monitoring of:

- **System Health**: CPU, memory usage, uptime
- **Extraction Status**: Current diocese, parishes processed, success rate
- **Performance Metrics**: Processing speed, queue size, pool utilization
- **Circuit Breaker Status**: Service health and failure protection
- **Live Log Stream**: Real-time log entries with color-coded levels
- **Error Alerts**: Recent errors and warning notifications
- **Extraction History**: Recent completed extractions with statistics

### WebSocket Connection
The dashboard connects via WebSocket for real-time updates:
- **Production**: `wss://api.diocesanvitality.org/ws/monitoring`
- **Development**: `ws://localhost:8000/ws/monitoring`

If you see "Dashboard disconnected", check:
1. Backend service is running
2. WebSocket endpoint is accessible
3. No firewall blocking WebSocket connections

---

## 🐍 Manual Python Script Execution

### Prerequisites
```bash
# Ensure you're in the project directory
cd /path/to/USCCB

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Set up environment variables (if needed)
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-supabase-key"
export GENAI_API_KEY_USCCB="your-genai-key"
export SEARCH_API_KEY_USCCB="your-search-key"
export SEARCH_CX_USCCB="your-search-cx"
```

### Running Individual Pipeline Components

#### 1. Diocese Extraction
```bash
# Extract all dioceses
python extract_dioceses.py --max_dioceses 0

# Extract limited number of dioceses
python extract_dioceses.py --max_dioceses 5

# View progress with verbose output
python extract_dioceses.py --max_dioceses 10
```

#### 2. Parish Directory Discovery
```bash
# Find parish directories for all dioceses
python find_parishes.py --max_dioceses_to_process 0

# Process specific diocese
python find_parishes.py --diocese_id 123

# Limit processing to 3 dioceses
python find_parishes.py --max_dioceses_to_process 3
```

#### 3. Parish Data Extraction

**Sequential Processing (Standard):**
```bash
# Extract from specific diocese
python extract_parishes.py --diocese_id 123 --num_parishes_per_diocese 25

# Extract from all dioceses (limited parishes)
python extract_parishes.py --num_parishes_per_diocese 10

# Extract all parishes (no limit)
python extract_parishes.py --num_parishes_per_diocese 0
```

**Concurrent Processing (60% Faster):**
```bash
# High-performance extraction
python async_extract_parishes.py \
  --diocese_id 123 \
  --num_parishes_per_diocese 50 \
  --pool_size 6 \
  --batch_size 12

# Maximum performance configuration
python async_extract_parishes.py \
  --num_parishes_per_diocese 0 \
  --pool_size 8 \
  --batch_size 15 \
  --max_concurrent_dioceses 3
```

#### 4. Schedule Extraction
```bash
# Extract schedules from first 100 parishes
python extract_schedule.py --num_parishes 100

# Extract from specific parish
python extract_schedule.py --parish_id 456

# Extract from all parishes
python extract_schedule.py --num_parishes 0
```

### Complete Pipeline Execution

#### Standard Pipeline (No Monitoring)
```bash
# Basic pipeline run
python run_pipeline.py \
  --max_parishes_per_diocese 50 \
  --num_parishes_for_schedule 100

# Skip specific steps
python run_pipeline.py \
  --skip_schedules \
  --max_parishes_per_diocese 25

# Process specific diocese
python run_pipeline.py \
  --diocese_id 123 \
  --max_parishes_per_diocese 0
```

#### Monitored Pipeline (With Dashboard Integration)
```bash
# Monitored pipeline with dashboard updates
python run_pipeline_monitored.py \
  --max_parishes_per_diocese 50 \
  --num_parishes_for_schedule 100

# Background execution with monitoring
nohup python run_pipeline_monitored.py \
  --max_parishes_per_diocese 50 \
  --num_parishes_for_schedule 100 \
  > pipeline.log 2>&1 &

# Disable monitoring (fallback mode)
python run_pipeline_monitored.py \
  --disable_monitoring \
  --max_parishes_per_diocese 25
```

### Debugging and Testing Scripts

#### Circuit Breaker Testing
```bash
# Test circuit breaker functionality
python test_circuit_breaker.py
```

#### Dashboard Testing
```bash
# Test basic monitoring functions
python test_dashboard.py --mode basic

# Simulate extraction for dashboard testing
python test_dashboard.py --mode extraction

# Continuous monitoring demo
python test_dashboard.py --mode continuous
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
python run_pipeline_monitored.py \
  --max_parishes_per_diocese 5 \
  --num_parishes_for_schedule 10 \
  --monitoring_url "http://localhost:8000"

# View dashboard at: http://localhost:3000/dashboard
```

---

## 🚨 Troubleshooting Common Issues

### Pipeline Not Starting
```bash
# Check pod status
kubectl get pods -n usccb -l app=pipeline

# Check events and errors
kubectl describe pod -l app=pipeline -n usccb

# Check deployment status
kubectl get deployment pipeline-deployment -n usccb

# Common fixes:
kubectl rollout restart deployment pipeline-deployment -n usccb
```

### Missing Dependencies
```bash
# Check logs for import errors
kubectl logs deployment/pipeline-deployment -n usccb | grep -i "modulenotfounderror\|importerror"

# If missing PyPDF2 or other packages:
# 1. Add to requirements.txt
# 2. Rebuild Docker image
# 3. Restart deployment
```

### Database Connection Issues
```bash
# Check if secrets exist
kubectl get secrets -n usccb

# Verify secret contents (without exposing values)
kubectl describe secret usccb-secrets -n usccb

# Test connection manually
python -c "import config; print(config.validate_config())"
```

### WebDriver/Chrome Issues
```bash
# Check Chrome installation in container
kubectl exec -it deployment/pipeline-deployment -n usccb -- which google-chrome

# Check ChromeDriver
kubectl exec -it deployment/pipeline-deployment -n usccb -- chromedriver --version

# View Chrome-specific errors
kubectl logs deployment/pipeline-deployment -n usccb | grep -i "chrome\|webdriver"
```

### Circuit Breaker Activation
```bash
# View circuit breaker status
kubectl logs deployment/pipeline-deployment -n usccb | grep "Circuit breaker"

# Check dashboard for circuit breaker states
# Visit: https://usccb.diocesanvitality.org/dashboard

# Reset by restarting pipeline
kubectl rollout restart deployment pipeline-deployment -n usccb
```

### Performance Issues
```bash
# Check resource usage
kubectl top pods -n usccb

# Check node capacity
kubectl describe nodes

# Monitor memory/CPU limits
kubectl describe pod -l app=pipeline -n usccb | grep -A 10 "Limits\|Requests"
```

### Log Analysis Commands
```bash
# Count error messages
kubectl logs deployment/pipeline-deployment -n usccb | grep -c "ERROR"

# Find most recent errors
kubectl logs deployment/pipeline-deployment -n usccb | grep "ERROR" | tail -10

# Check processing statistics
kubectl logs deployment/pipeline-deployment -n usccb | grep -E "processed|extracted|completed"

# Monitor extraction progress
kubectl logs -f deployment/pipeline-deployment -n usccb | grep -E "Diocese:|Parish:|Schedule:"
```

---

## 📝 Log Examples and Interpretations

### Successful Pipeline Start
```
2025-09-13 19:57:58,776 - core.circuit_breaker - INFO - 🔌 Circuit Breaker Manager initialized
2025-09-13 19:57:58,789 - core.circuit_breaker - INFO - 🔌 Circuit breaker 'webdriver_javascript' initialized
2025-09-13 19:57:59,123 - __main__ - INFO - Starting USCCB data extraction pipeline...
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