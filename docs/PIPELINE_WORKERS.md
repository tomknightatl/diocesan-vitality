# Pipeline Worker Types and Architecture

## Overview

The Diocesan Vitality pipeline uses a **distributed worker architecture** with specialized worker types for different stages of the data extraction process. This architecture enables:

- **Independent scaling** of different pipeline stages based on workload
- **Resource optimization** with worker-specific CPU/memory allocations
- **Parallel processing** across multiple pods
- **Single container image** with runtime specialization via environment variables

## Pipeline Stages and Worker Types

### 🔍 Discovery Worker (`worker_type: discovery`)

**Pipeline Steps: 1-2 (Diocese and Parish Directory Discovery)**

#### Responsibilities

- **Step 1: Extract Dioceses**
  - Scrapes the official USCCB source for diocese information
  - Extracts diocese names, addresses, and official websites
  - Stores data in `Dioceses` table
  - Script: `extract_dioceses.py`

- **Step 2: Find Parish Directories**
  - AI-powered detection of parish listing pages on diocese websites
  - Uses Google Gemini AI for intelligent link classification
  - Stores parish directory URLs in `DiocesesParishDirectory` table
  - Script: `find_parishes.py`

#### Characteristics

- **Resource Allocation**: 512Mi RAM, 200m CPU
- **Execution Pattern**: Runs continuously in infinite loop with 5-minute sleep between cycles
- **Scaling**: 1 pod (lightweight operations)
- **Primary Technology**: HTTP requests, BeautifulSoup, Google Gemini AI

---

### ⚡ Extraction Worker (`worker_type: extraction`)

**Pipeline Step: 3 (Parish Detail Extraction)**

#### Responsibilities

- **Step 3: Extract Parishes**
  - Extracts detailed parish information from directory pages
  - Employs specialized extractors for different website platforms:
    - Diocese Card Layout
    - Parish Finder (eCatholic)
    - HTML Tables
    - Interactive Maps
    - Generic patterns
  - Stores comprehensive parish data in `Parishes` table
  - Script: `async_extract_parishes.py`

#### Characteristics

- **Resource Allocation**: 2.2Gi RAM, 800m CPU
- **Execution Pattern**: Continuous processing with work coordination
- **Scaling**: 2-5 pods (HPA: scales based on CPU/memory)
- **Primary Technology**: Selenium WebDriver, async processing, BeautifulSoup
- **Performance**: High-performance concurrent processing with connection pooling

---

### 📅 Schedule Worker (`worker_type: schedule`)

**Pipeline Step: 4 (Mass Schedule Extraction)**

#### Responsibilities

- **Step 4: Extract Schedules**
  - Visits individual parish websites to extract liturgical schedules
  - Parses Mass times, Adoration schedules, and Reconciliation times
  - Handles dynamic JavaScript content
  - Stores schedule data in `ParishSchedules` table
  - Script: `extract_schedule_respectful.py`

#### Characteristics

- **Resource Allocation**: 1.5Gi RAM, 600m CPU
- **Execution Pattern**: Batch processing with respectful delays
- **Scaling**: 1-3 pods (HPA: scales based on workload)
- **Primary Technology**: Selenium WebDriver, AI content analysis
- **Rate Limiting**: Built-in respectful delays between requests

---

### 📊 Reporting Worker (`worker_type: reporting`)

**Pipeline Step: 5 (Analytics and Report Generation)**

#### Responsibilities

- **Step 5: Generate Reports**
  - Runs analytics on collected data
  - Generates statistics and insights
  - Produces data quality metrics
  - Creates summary reports
  - Script: `report_statistics.py`

#### Characteristics

- **Resource Allocation**: 512Mi RAM, 200m CPU
- **Execution Pattern**: Runs every 6 hours
- **Scaling**: 1 pod (lightweight operations)
- **Primary Technology**: Pandas, SQL queries, data analysis

---

### 🔄 All Worker (`worker_type: all`)

**Pipeline Steps: All (1-5)**

#### Responsibilities

- Backwards compatible mode that runs all pipeline steps sequentially
- Coordinates work through distributed work coordinator
- Used for:
  - Single-instance deployments
  - Development and testing
  - Legacy compatibility

#### Characteristics

- **Resource Allocation**: Configurable (defaults to extraction worker resources)
- **Execution Pattern**: Sequential execution of all stages
- **Scaling**: Typically 1 pod
- **Primary Technology**: All of the above

---

## Architecture Details

### Single Image Deployment

All worker types use the **same Docker container image** with runtime specialization:

```yaml
# Example: Extraction worker deployment
env:
  - name: WORKER_TYPE
    value: "extraction"
```

The `distributed_pipeline_runner.py` reads the `WORKER_TYPE` environment variable and executes the appropriate worker logic.

### Worker Coordination

Workers coordinate through the database using:

- **`pipeline_workers` table**: Tracks active workers, heartbeats, and status
- **`diocese_work_assignments` table**: Manages work distribution across workers
- **Heartbeat mechanism**: 30-second heartbeats to detect failed workers
- **Automatic failover**: Work reassignment when workers become inactive

### Resource Optimization

Each worker type has optimized resource allocation:

| Worker Type | Memory | CPU  | Scaling  | Reason                                              |
| ----------- | ------ | ---- | -------- | --------------------------------------------------- |
| Discovery   | 512Mi  | 200m | 1 pod    | Lightweight HTTP and AI calls                       |
| Extraction  | 2.2Gi  | 800m | 2-5 pods | Multiple WebDriver instances, concurrent processing |
| Schedule    | 1.5Gi  | 600m | 1-3 pods | WebDriver with AI analysis                          |
| Reporting   | 512Mi  | 200m | 1 pod    | Data analysis and SQL queries                       |

### Pod Distribution and Anti-Affinity

**Workers per Pod:** Each pod runs **exactly 1 worker process**

- 1 pod = 1 Python process = 1 worker
- Worker identified by pod name (`WORKER_ID: metadata.name`)

**Pods per Node:** **Prefers 1 pod per node, but allows multiple if needed**

The deployment uses soft pod anti-affinity:

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution: # Soft constraint
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app
                operator: In
                values:
                  - pipeline
          topologyKey: "kubernetes.io/hostname"
```

**Behavior:**

- **Ideal case** (enough nodes): Pipeline pods spread across different nodes (1 pod per node)
- **Limited nodes**: Multiple pods can run on same node, balanced evenly
- **Single node**: All pods run on the same node (preference ignored)
- **Why soft?** Ensures pods can still be scheduled even with limited nodes

### Horizontal Pod Autoscaling (HPA)

Extraction and Schedule workers use HPA for dynamic scaling:

```yaml
# Extraction Worker HPA
minReplicas: 2
maxReplicas: 5
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Execution Flow

```
┌─────────────────┐
│ Discovery       │  Step 1: Extract Dioceses
│ Worker          │  Step 2: Find Parish Directories
│ (continuous)    │         ↓
└─────────────────┘         │
                            ↓
┌─────────────────┐         │
│ Extraction      │ ←───────┘
│ Workers (2-5)   │  Step 3: Extract Parishes
│ (coordinated)   │         ↓
└─────────────────┘         │
                            ↓
┌─────────────────┐         │
│ Schedule        │ ←───────┘
│ Workers (1-3)   │  Step 4: Extract Schedules
│ (coordinated)   │         ↓
└─────────────────┘         │
                            ↓
┌─────────────────┐         │
│ Reporting       │ ←───────┘
│ Worker          │  Step 5: Generate Reports
│ (every 6h)      │
└─────────────────┘
```

## Configuration

### Environment Variables

- `WORKER_TYPE`: Specifies the worker type (discovery, extraction, schedule, reporting, all)
- `MAX_PARISHES_PER_DIOCESE`: Limit parishes processed per diocese (extraction worker)
- `NUM_PARISHES_FOR_SCHEDULE`: Batch size for schedule extraction
- `MONITORING_URL`: Backend monitoring service URL

### Deployment Configuration

Worker types are configured in Kubernetes manifests:

- **Development**: `k8s/environments/development/development-patches.yaml`
- **Staging**: `k8s/environments/staging/staging-patches.yaml`
- **Production**: `k8s/environments/production/production-patches.yaml`

### Running Locally

```bash
# Discovery worker
WORKER_TYPE=discovery python -m pipeline.distributed_pipeline_runner

# Extraction worker
WORKER_TYPE=extraction python -m pipeline.distributed_pipeline_runner

# Schedule worker
WORKER_TYPE=schedule python -m pipeline.distributed_pipeline_runner

# Reporting worker
WORKER_TYPE=reporting python -m pipeline.distributed_pipeline_runner

# All steps (backwards compatible)
python -m pipeline.distributed_pipeline_runner  # defaults to 'all'
```

## Monitoring

Each worker type reports to the monitoring dashboard:

- **Worker status**: Active, inactive, failed
- **Heartbeat**: 30-second intervals
- **Progress**: Current diocese, parishes processed
- **Performance**: Success rate, processing speed
- **Circuit breakers**: Website-specific failure tracking

Access the monitoring dashboard at:

- **Production**: https://diocesanvitality.org/dashboard
- **Development**: https://devui.diocesanvitality.org/dashboard
- **Staging**: https://stgui.diocesanvitality.org/dashboard

## Best Practices

1. **Discovery Workers**: Always run 1 pod continuously to ensure new dioceses/directories are discovered
2. **Extraction Workers**: Scale based on backlog - monitor queue size in dashboard
3. **Schedule Workers**: Limit scaling to avoid overwhelming parish websites
4. **Reporting Workers**: Run periodically (6-hour intervals) to avoid unnecessary database load
5. **Resource Limits**: Always set resource limits to prevent pod eviction
6. **Graceful Shutdown**: Workers handle SIGTERM/SIGINT for clean database state

## Troubleshooting

### Worker Not Starting

- Check `WORKER_TYPE` environment variable is set correctly
- Verify database connectivity (SUPABASE_URL, SUPABASE_KEY)
- Check pod logs: `kubectl logs -n <namespace> <pod-name>`

### Worker Showing as Failed

- Check for Python exceptions in logs
- Verify website accessibility (circuit breakers may be tripped)
- Check resource limits (OOMKilled indicates memory issues)

### No Work Being Processed

- Verify previous pipeline stages completed successfully
- Check work coordination tables (`diocese_work_assignments`)
- Ensure workers are registered in `pipeline_workers` table

### High Resource Usage

- Review `max_parishes_per_diocese` setting (lower for less memory)
- Check for WebDriver memory leaks (schedule/extraction workers)
- Consider scaling down HPA limits

## Related Documentation

- [Architecture Overview](ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Database Schema](DATABASE.md)
- [Monitoring Guide](MONITORING.md)
- [Local Development](LOCAL_DEVELOPMENT.md)
