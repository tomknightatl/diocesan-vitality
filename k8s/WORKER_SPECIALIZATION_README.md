# Worker Specialization System

This directory contains Kubernetes deployments for specialized pipeline workers that use a single container image but different runtime configurations to handle specific pipeline stages.

## Worker Types

### 1. Discovery Worker (`discovery-deployment.yaml`)
- **Purpose**: Steps 1-2 (Diocese discovery + Parish directory finding)
- **Resources**: Lightweight (512Mi RAM, 200m CPU)
- **Replicas**: 1 (runs periodically)
- **Behavior**: Runs discovery cycles with 5-minute sleep intervals

### 2. Extraction Worker (`extraction-deployment.yaml`)
- **Purpose**: Step 3 (Parish detail extraction)
- **Resources**: High-performance (2.2Gi RAM, 800m CPU)
- **Replicas**: 2-5 (HPA managed)
- **Behavior**: Processes dioceses assigned by work coordinator

### 3. Schedule Worker (`schedule-deployment.yaml`)
- **Purpose**: Step 4 (Mass schedule extraction)
- **Resources**: WebDriver intensive (1.5Gi RAM, 600m CPU)
- **Replicas**: 1-3 (HPA managed)
- **Behavior**: Extracts schedules from individual parish websites

### 4. Reporting Worker (`reporting-deployment.yaml`)
- **Purpose**: Step 5 (Analytics and reporting)
- **Resources**: Lightweight (512Mi RAM, 200m CPU)
- **Replicas**: 1 (single instance)
- **Behavior**: Generates reports every 10 minutes

## Single Image Approach

All workers use the same container image (`tomatl/diocesan-vitality:pipeline-*`) but specialize at runtime using the `WORKER_TYPE` environment variable:

```yaml
env:
  - name: WORKER_TYPE
    value: "extraction"  # discovery, extraction, schedule, reporting, all
```

## Horizontal Pod Autoscaling

- **Extraction Workers**: Scale 2-5 based on CPU/memory utilization
- **Schedule Workers**: Scale 1-3 based on CPU/memory utilization
- **Discovery/Reporting**: Fixed replicas (no autoscaling needed)

## Resource Optimization

### Memory Allocation by Worker Type:
- **Discovery**: 512Mi (lightweight discovery)
- **Extraction**: 2.2Gi (concurrent parish processing)
- **Schedule**: 1.5Gi (WebDriver overhead)
- **Reporting**: 512Mi (analytics only)

### CPU Allocation by Worker Type:
- **Discovery**: 200m (periodic runs)
- **Extraction**: 800m (high concurrency)
- **Schedule**: 600m (WebDriver intensive)
- **Reporting**: 200m (lightweight analysis)

## Deployment Commands

### Deploy All Worker Types:
```bash
kubectl apply -f k8s/discovery-deployment.yaml
kubectl apply -f k8s/extraction-deployment.yaml
kubectl apply -f k8s/schedule-deployment.yaml
kubectl apply -f k8s/reporting-deployment.yaml
kubectl apply -f k8s/extraction-hpa.yaml
kubectl apply -f k8s/schedule-hpa.yaml
```

### Deploy Individual Worker Types:
```bash
# Discovery workers
kubectl apply -f k8s/discovery-deployment.yaml

# Extraction workers (with autoscaling)
kubectl apply -f k8s/extraction-deployment.yaml
kubectl apply -f k8s/extraction-hpa.yaml

# Schedule workers (with autoscaling)
kubectl apply -f k8s/schedule-deployment.yaml
kubectl apply -f k8s/schedule-hpa.yaml

# Reporting workers
kubectl apply -f k8s/reporting-deployment.yaml
```

## Monitoring and Observability

Each worker type can be monitored independently:

```bash
# View worker pods by type
kubectl get pods -l worker-type=extraction -n diocesan-vitality
kubectl get pods -l worker-type=schedule -n diocesan-vitality
kubectl get pods -l worker-type=discovery -n diocesan-vitality
kubectl get pods -l worker-type=reporting -n diocesan-vitality

# View worker logs
kubectl logs -l worker-type=extraction -n diocesan-vitality --tail=100
kubectl logs -l worker-type=schedule -n diocesan-vitality --tail=100

# Check HPA status
kubectl get hpa -n diocesan-vitality
```

## Work Coordination

Workers coordinate through the database using the `DistributedWorkCoordinator`:

- **Discovery Workers**: Run independently on schedule
- **Extraction Workers**: Coordinate diocese assignments
- **Schedule Workers**: Get parish work assignments
- **Reporting Workers**: Check if reports need generation

## Migration from Legacy Deployment

To migrate from the original `pipeline-deployment.yaml`:

1. **Scale down legacy deployment**:
   ```bash
   kubectl scale deployment pipeline-deployment --replicas=0 -n diocesan-vitality
   ```

2. **Deploy specialized workers**:
   ```bash
   kubectl apply -f k8s/discovery-deployment.yaml
   kubectl apply -f k8s/extraction-deployment.yaml
   kubectl apply -f k8s/extraction-hpa.yaml
   kubectl apply -f k8s/schedule-deployment.yaml
   kubectl apply -f k8s/schedule-hpa.yaml
   kubectl apply -f k8s/reporting-deployment.yaml
   ```

3. **Verify deployment**:
   ```bash
   kubectl get pods -n diocesan-vitality
   kubectl get hpa -n diocesan-vitality
   ```

4. **Remove legacy deployment** (after verification):
   ```bash
   kubectl delete -f k8s/pipeline-deployment.yaml
   kubectl delete -f k8s/pipeline-hpa.yaml
   ```

## Benefits

1. **Resource Efficiency**: Right-sized resources per task type
2. **Independent Scaling**: Scale extraction workers without affecting discovery
3. **Better Fault Isolation**: WebDriver issues don't affect parish discovery
4. **Cost Optimization**: Run expensive workers only when needed
5. **Monitoring Clarity**: Separate metrics per worker type
6. **Deployment Flexibility**: Deploy/update worker types independently

## Backward Compatibility

The system maintains backward compatibility:
- Original `pipeline-deployment.yaml` still works with `WORKER_TYPE=all`
- Existing monitoring and health checks continue to function
- Database schema supports both old and new worker coordination