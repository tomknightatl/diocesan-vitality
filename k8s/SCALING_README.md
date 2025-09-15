# Pipeline Horizontal Scaling with ArgoCD

This document describes how to deploy and manage the horizontally-scalable pipeline using ArgoCD.

## 🏗️ Architecture Overview

The distributed pipeline uses:
- **Diocese-based work partitioning** to prevent scraping conflicts
- **Database coordination** via Supabase for worker management
- **Kubernetes HPA** for automatic scaling based on resource usage
- **ArgoCD GitOps** for declarative deployments

## 📦 ArgoCD Integration

### Current Setup
Your ArgoCD application (`k8s/argocd/diocesan-vitality-app.yaml`) automatically syncs all manifests in the `k8s/` directory:

```yaml
spec:
  source:
    repoURL: https://github.com/tomknightatl/diocesan-vitality
    targetRevision: HEAD
    path: k8s  # ArgoCD monitors this directory
  syncPolicy:
    automated:
      prune: true      # Removes deleted resources
      selfHeal: true   # Auto-fixes drift
```

### New Manifests Added

1. **Updated `pipeline-deployment.yaml`**
   - Now uses `distributed_pipeline_runner.py`
   - Includes worker coordination environment variables
   - Added health checks for HPA integration
   - Graceful shutdown for coordination cleanup

2. **New `pipeline-hpa.yaml`**
   - Horizontal Pod Autoscaler (1-5 replicas)
   - Scales on CPU (70%) and memory (80%) usage
   - Conservative scale-down, aggressive scale-up
   - Pod Disruption Budget ensures availability

## 🚀 Deployment Process

### 1. Prerequisites

**Database Migration Required:**
```sql
-- Run this in your Supabase SQL editor
-- File: sql/migrations/004_create_pipeline_coordination_tables.sql

CREATE TABLE IF NOT EXISTS pipeline_workers (
    worker_id TEXT PRIMARY KEY,
    pod_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'failed')),
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_dioceses INTEGER[] DEFAULT ARRAY[]::INTEGER[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS diocese_work_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    diocese_id INTEGER NOT NULL REFERENCES "Dioceses"(id),
    worker_id TEXT NOT NULL REFERENCES pipeline_workers(worker_id),
    status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'failed')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    estimated_completion TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_pipeline_workers_status ON pipeline_workers(status);
CREATE INDEX IF NOT EXISTS idx_diocese_assignments_status ON diocese_work_assignments(status);
```

### 2. Docker Image Update

Ensure your Docker image includes the new distributed runner files:
- `distributed_pipeline_runner.py`
- `core/distributed_work_coordinator.py`
- `monitor_distributed_pipeline.py`
- `scale_pipeline.py`

### 3. ArgoCD Deployment

Since ArgoCD has `automated` sync enabled, it will automatically:

1. **Detect changes** when you push to the repository
2. **Update the deployment** to use the distributed runner
3. **Create the HPA** for automatic scaling
4. **Apply the Pod Disruption Budget**

**Manual sync (if needed):**
```bash
# Sync via ArgoCD CLI
argocd app sync diocesan-vitality-app

# Or via kubectl if you have the ArgoCD CRDs
kubectl patch application diocesan-vitality-app -n argocd --type merge -p='{"operation":{"initiatedBy":{"username":"manual-sync"}}}'
```

### 4. Verification

Check that everything is deployed correctly:

```bash
# Check if HPA is created and functioning
kubectl get hpa -n diocesan-vitality

# Check pipeline deployment status
kubectl get deployment pipeline-deployment -n diocesan-vitality

# Check pod disruption budget
kubectl get pdb -n diocesan-vitality

# Monitor ArgoCD application status
kubectl get application diocesan-vitality-app -n argocd
```

## 📊 Monitoring & Management

### Real-time Cluster Monitoring
```bash
# Watch cluster status (from any pod with Python environment)
python monitor_distributed_pipeline.py --watch

# Single status check
python monitor_distributed_pipeline.py
```

### Manual Scaling
```bash
# Scale to 3 pods and monitor for 2 minutes
python scale_pipeline.py 3

# Scale to 1 pod without monitoring
python scale_pipeline.py 1 --no-monitor

# Scale via kubectl (HPA will override this eventually)
kubectl scale deployment pipeline-deployment --replicas=2 -n diocesan-vitality
```

### Checking HPA Status
```bash
# View HPA status and metrics
kubectl describe hpa pipeline-hpa -n diocesan-vitality

# Watch HPA scaling decisions
kubectl get hpa pipeline-hpa -n diocesan-vitality -w
```

## 🔧 Configuration

### HPA Tuning
Edit `k8s/pipeline-hpa.yaml` to adjust scaling behavior:

```yaml
spec:
  minReplicas: 1    # Minimum pods
  maxReplicas: 5    # Maximum pods
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        averageUtilization: 70  # Scale up when CPU > 70%
```

### Pipeline Configuration
Environment variables in `pipeline-deployment.yaml`:

```yaml
env:
- name: MAX_PARISHES_PER_DIOCESE
  value: "50"  # Adjust based on your throughput needs
- name: NUM_PARISHES_FOR_SCHEDULE
  value: "101" # Adjust based on your processing requirements
```

## 🛠️ Troubleshooting

### Common Issues

1. **Pods not scaling**
   ```bash
   # Check if metrics-server is running
   kubectl get deployment metrics-server -n kube-system

   # Check HPA events
   kubectl describe hpa pipeline-hpa -n diocesan-vitality
   ```

2. **Worker coordination issues**
   ```bash
   # Check database connectivity from pods
   kubectl exec -it deployment/pipeline-deployment -n diocesan-vitality -- python -c "from core.db import get_supabase_client; print('OK' if get_supabase_client() else 'FAIL')"

   # Check coordination tables
   python monitor_distributed_pipeline.py
   ```

3. **ArgoCD sync issues**
   ```bash
   # Check ArgoCD application status
   kubectl get application diocesan-vitality-app -n argocd -o yaml

   # Check for sync errors
   kubectl describe application diocesan-vitality-app -n argocd
   ```

### Cleanup Stale Assignments
```bash
# Clean up stale work assignments (dry run)
python monitor_distributed_pipeline.py --cleanup

# Actually clean them up
python monitor_distributed_pipeline.py --cleanup --no-dry-run
```

## 📈 Benefits

- **GitOps Best Practices**: All changes tracked in Git, deployed via ArgoCD
- **Automatic Scaling**: HPA responds to load without manual intervention
- **Zero Conflicts**: Diocese-based partitioning prevents scraping conflicts
- **High Availability**: Pod disruption budgets ensure service continuity
- **Observable**: Rich monitoring and metrics for operational visibility

## 🔄 Rollback

If you need to rollback to the single-pod pipeline:

1. **Disable HPA**: `kubectl delete hpa pipeline-hpa -n diocesan-vitality`
2. **Revert deployment**: Change `command` back to `["python", "run_pipeline.py"]` in `pipeline-deployment.yaml`
3. **Commit and push**: ArgoCD will automatically sync the changes

The distributed coordinator will gracefully handle the transition.