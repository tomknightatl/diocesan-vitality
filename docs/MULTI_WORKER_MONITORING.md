# Multi-Worker Monitoring Dashboard

This document describes the monitoring system for distributed pipeline workers, supporting both single and multi-worker deployments.

## Overview

The monitoring dashboard now supports two modes:
1. **Aggregate View** - Combined metrics from all workers (default)
2. **Individual Worker View** - Detailed view of a specific worker

## Architecture

### Backend Changes

#### MonitoringManager
- **Multi-worker support**: Tracks individual worker data in `self.workers` dictionary
- **Aggregate calculations**: Combines metrics across workers for system-wide view
- **Backward compatibility**: Maintains legacy single-worker API endpoints

#### New API Endpoints

**Worker-specific endpoints:**
- `POST /api/monitoring/worker/{worker_id}/extraction_status` - Update worker extraction status
- `POST /api/monitoring/worker/{worker_id}/circuit_breakers` - Update worker circuit breakers
- `GET /api/monitoring/worker/{worker_id}` - Get detailed worker status

**Multi-worker management:**
- `GET /api/monitoring/workers` - List all workers with basic status
- `POST /api/monitoring/mode/{mode}` - Switch between aggregate/individual mode

### Frontend Changes

#### Dashboard Features
- **Worker Selector**: Dropdown in header to switch between workers
- **Aggregate Metrics**: Shows combined data from all active workers
- **Worker Status Indicators**: Color-coded badges for each worker
- **Enhanced Extraction Status**: Displays active worker count and distributed progress

#### Worker Selection
```jsx
// Switch to aggregate view
📈 Aggregate View (3 workers)

// Individual worker views
🔧 worker-pod-12345 [RUNNING]
🔧 worker-pod-67890 [IDLE]
```

### Monitoring Client Changes

#### Worker ID Support
```python
# Initialize with worker ID for distributed deployments
monitoring_client = get_monitoring_client(
    base_url="http://localhost:8000",
    worker_id="worker-pod-12345"
)

# Routes automatically to worker-specific endpoints
monitoring_client.update_extraction_status(status="running", ...)
monitoring_client.update_circuit_breakers({...})
```

#### Context Manager
```python
# Extraction monitoring with worker identification
with ExtractionMonitoring("Diocese Name", 100, worker_id="worker-pod-12345") as monitor:
    # Extraction work here
    monitor.update_progress(50, 45)
```

## Usage

### Single Worker Deployment (Existing)
No changes required - existing scripts continue to work with legacy endpoints.

```python
# Works as before - uses legacy endpoints
monitoring_client = get_monitoring_client("http://localhost:8000")
```

### Multi-Worker Deployment (New)

#### 1. Initialize Workers with IDs
```python
import socket
import os

# Generate unique worker ID
worker_id = os.environ.get('HOSTNAME', socket.gethostname())

# Initialize monitoring with worker ID
monitoring_client = get_monitoring_client(
    base_url="http://localhost:8000",
    worker_id=worker_id
)
```

#### 2. Dashboard Features
- **Aggregate View**: Default view showing combined metrics
  - Total parishes processed across all workers
  - Average success rate weighted by worker activity
  - Count of active/idle workers
  - Combined circuit breaker statistics

- **Individual View**: Select specific worker from dropdown
  - Worker-specific extraction progress
  - Worker-specific circuit breaker status
  - Worker-specific error logs

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

## Deployment

### Kubernetes Configuration
Workers should be configured with unique identifiers:

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

### Worker Initialization
```python
import os
from core.monitoring_client import get_monitoring_client

# Get worker ID from environment
worker_id = os.environ.get('WORKER_ID', os.environ.get('HOSTNAME'))

# Initialize monitoring
monitoring_client = get_monitoring_client(
    base_url=os.environ.get('MONITORING_URL', 'http://localhost:8000'),
    worker_id=worker_id
)
```

## Benefits

1. **Scalability**: Monitor unlimited number of workers
2. **Visibility**: See both system-wide and individual worker performance
3. **Troubleshooting**: Isolate issues to specific workers
4. **Load Balancing**: Identify uneven work distribution
5. **Backward Compatibility**: Existing single-worker setups continue working

## Migration Path

### Phase 1: Backward Compatible (Current)
- Deploy updated monitoring backend
- Existing workers continue using legacy endpoints
- Dashboard shows single worker data in new UI

### Phase 2: Hybrid Deployment
- New workers use worker IDs
- Mix of legacy and worker-specific endpoints
- Dashboard shows both aggregate and individual views

### Phase 3: Full Multi-Worker
- All workers use worker IDs
- Legacy endpoints deprecated
- Full distributed monitoring capabilities

## Monitoring Best Practices

1. **Worker Naming**: Use descriptive, consistent worker IDs
2. **Health Checks**: Monitor worker heartbeats and staleness
3. **Circuit Breaker Tuning**: Adjust thresholds based on aggregate load
4. **Error Correlation**: Use worker IDs to trace issues
5. **Capacity Planning**: Monitor worker utilization for scaling decisions