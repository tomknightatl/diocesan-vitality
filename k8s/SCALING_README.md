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

## 🐳 Docker Image Management

### Building and Deploying New Images

To deploy new code changes, you need to build new Docker images with timestamped tags and update the Kubernetes manifests.

#### 1. Build and Tag Images with Timestamp

```bash
# Generate timestamp
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
echo "Using timestamp: $TIMESTAMP"

# Build images with timestamped tags
docker build -f backend/Dockerfile -t tomatl/diocesan-vitality:backend-$TIMESTAMP backend/
docker build -f frontend/Dockerfile -t tomatl/diocesan-vitality:frontend-$TIMESTAMP frontend/
docker build -f Dockerfile.pipeline -t tomatl/diocesan-vitality:pipeline-$TIMESTAMP .

# Push to Docker Hub
docker push tomatl/diocesan-vitality:backend-$TIMESTAMP
docker push tomatl/diocesan-vitality:frontend-$TIMESTAMP
docker push tomatl/diocesan-vitality:pipeline-$TIMESTAMP

echo "All images pushed with timestamp: $TIMESTAMP"
```

#### 2. Update Kubernetes Manifests

Update the image tags in the deployment files:

```bash
# Update backend deployment
sed -i "s|image: tomatl/diocesan-vitality:backend-.*|image: tomatl/diocesan-vitality:backend-$TIMESTAMP|g" k8s/backend-deployment.yaml

# Update frontend deployment
sed -i "s|image: tomatl/diocesan-vitality:frontend-.*|image: tomatl/diocesan-vitality:frontend-$TIMESTAMP|g" k8s/frontend-deployment.yaml

# Update pipeline deployment
sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$TIMESTAMP|g" k8s/pipeline-deployment.yaml
```

#### 3. Commit and Deploy via GitOps

```bash
# Stage changes
git add k8s/backend-deployment.yaml k8s/frontend-deployment.yaml k8s/pipeline-deployment.yaml

# Commit with descriptive message
git commit -m "Update all deployments to use timestamped Docker images ($TIMESTAMP)

- backend: tomatl/diocesan-vitality:backend-$TIMESTAMP
- frontend: tomatl/diocesan-vitality:frontend-$TIMESTAMP
- pipeline: tomatl/diocesan-vitality:pipeline-$TIMESTAMP

[Include description of changes in this deployment]"

# Push to trigger ArgoCD sync
git push origin main
```

#### 4. Monitor Deployment

```bash
# Watch ArgoCD sync status
kubectl get application diocesan-vitality-app -n argocd -w

# Monitor pod rollout
kubectl get pods -n diocesan-vitality -w

# Check new image is deployed
kubectl describe pod -n diocesan-vitality $(kubectl get pods -n diocesan-vitality -l app=pipeline -o name | head -1) | grep Image:
```

### Why Timestamped Tags?

- **Immutable deployments**: Each timestamp creates a unique, traceable deployment
- **Easy rollbacks**: Can revert to any previous timestamp instantly
- **No caching issues**: Kubernetes must pull new tagged images
- **GitOps compatibility**: Works seamlessly with ArgoCD workflows
- **Audit trail**: Git history shows exactly when each image was deployed

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

## ⚠️ Prevention Best Practices

### ArgoCD Degradation Prevention

To prevent ArgoCD from entering a degraded state, follow these practices:

1. **Docker Image Verification**
   ```bash
   # Always verify images exist before updating manifests
   docker images | grep "diocesan-vitality.*backend"
   docker images | grep "diocesan-vitality.*frontend"
   docker images | grep "diocesan-vitality.*pipeline"

   # Test image pull before committing
   docker pull tomatl/diocesan-vitality:backend-$TIMESTAMP
   ```

2. **Resource Planning Before Scaling**
   ```bash
   # Check current resource usage before scaling up
   kubectl get hpa -n diocesan-vitality
   kubectl top pods -n diocesan-vitality

   # Example: High usage indicates need for resource adjustment
   # CPU: 945%/70%, Memory: 223%/80% -> scale gradually, not 1→5
   ```

3. **Gradual Scaling Strategy**
   ```bash
   # Instead of jumping from 1 to 5 pods:
   # Step 1: Scale to 2 pods, monitor stability
   sed -i 's/maxReplicas: 1/maxReplicas: 2/' k8s/pipeline-hpa.yaml
   git add k8s/pipeline-hpa.yaml && git commit -m "Scale up to 2 pods" && git push

   # Step 2: Monitor for stability, then scale to 5
   # Wait for ArgoCD sync and verify no ImagePullBackOff or pod evictions
   kubectl get pods -n diocesan-vitality
   kubectl get applications -n argocd
   ```

4. **GitOps Compliance**
   ```bash
   # ❌ Never use direct kubectl commands for config changes:
   # kubectl scale deployment pipeline-deployment --replicas=5

   # ✅ Always use Git commits for configuration changes:
   git add k8s/pipeline-hpa.yaml
   git commit -m "Scale HPA maxReplicas to 5 for load testing"
   git push
   ```

5. **ArgoCD Health Monitoring**
   ```bash
   # Regular health checks before major changes
   kubectl get applications -n argocd

   # Look for these healthy states:
   # diocesan-vitality-app   Synced   Healthy

   # Investigate any OutOfSync or Degraded status:
   kubectl describe application diocesan-vitality-app -n argocd
   ```

### Resource Pressure Prevention

1. **Memory Request Alignment**
   ```yaml
   # In pipeline-deployment.yaml, align requests with actual usage
   resources:
     requests:
       memory: "1.6Gi"  # Match actual usage patterns
       cpu: "100m"
     limits:
       memory: "2Gi"    # Allow some headroom
       cpu: "500m"
   ```

2. **Node Capacity Planning**
   ```bash
   # Check node capacity before scaling
   kubectl describe nodes | grep -A 5 "Allocated resources"

   # Ensure sufficient memory/CPU for pod scaling
   kubectl top nodes
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

4. **ArgoCD Degraded Status (OutOfSync/Degraded)**

   **Symptoms**: ArgoCD shows `OutOfSync` or `Degraded` status with constant sync thrashing

   **Common Causes & Fixes**:

   a) **Missing Docker Images (ImagePullBackOff)**
   ```bash
   # Identify failed pods
   kubectl get pods -n diocesan-vitality | grep ImagePullBackOff

   # Check specific pod events
   kubectl describe pod <pod-name> -n diocesan-vitality | grep -A 10 "Events:"

   # Fix: Create missing image from existing one
   docker tag tomatl/diocesan-vitality:backend-<existing-tag> tomatl/diocesan-vitality:backend-<missing-tag>
   docker push tomatl/diocesan-vitality:backend-<missing-tag>

   # Delete failed pod to restart
   kubectl delete pod <pod-name> -n diocesan-vitality
   ```

   b) **Resource Pressure (Pod Evictions)**
   ```bash
   # Check for evicted/failed pods
   kubectl get pods -n diocesan-vitality | grep -E "(Error|ContainerStatusUnknown|Evicted)"

   # Check pod resource usage vs requests
   kubectl top pods -n diocesan-vitality
   kubectl describe pod <pod-name> -n diocesan-vitality | grep -A 5 "Limits:"

   # Clean up failed pods
   kubectl get pods -n diocesan-vitality | grep -E "(Error|ContainerStatusUnknown)" | awk '{print $1}' | xargs -I {} kubectl delete pod {} -n diocesan-vitality

   # Scale down HPA to reduce pressure
   sed -i 's/maxReplicas: 5/maxReplicas: 2/' k8s/pipeline-hpa.yaml
   git add k8s/pipeline-hpa.yaml && git commit -m "Scale down HPA to reduce resource pressure" && git push
   ```

   c) **Force ArgoCD Sync**
   ```bash
   # Trigger manual sync
   kubectl patch application diocesan-vitality-app -n argocd --type merge -p '{"operation": {"initiatedBy": {"username": "admin"}, "sync": {"revision": "HEAD"}}}'

   # Monitor sync progress
   kubectl get applications -n argocd -w
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