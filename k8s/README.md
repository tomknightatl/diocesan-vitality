# USCCB Pipeline Kubernetes Deployment

This directory contains Kubernetes manifests and deployment scripts for running the USCCB data extraction pipeline on your DOKS cluster.

## Overview

The pipeline runs as containerized jobs in Kubernetes, using the same Docker image naming convention as your backend and frontend:
- **Backend**: `$DOCKER_USERNAME/usccb:backend`
- **Frontend**: `$DOCKER_USERNAME/usccb:frontend`
- **Pipeline**: `$DOCKER_USERNAME/usccb:pipeline`

The pipeline provides:
- **Scheduled execution** via CronJob (daily at 2 AM UTC)
- **On-demand execution** via Job manifests
- **Secure credential management** via Kubernetes Secrets
- **Resource management** with CPU and memory limits
- **Scalability** and **reliability** in cloud environment

## Quick Start

### Option 1: Deploy with ArgoCD (Recommended)
Since the pipeline manifests are in the `k8s/` directory, they will be automatically deployed by your existing ArgoCD ApplicationSet to the `usccb` namespace.

1. **Build and push the pipeline image**:
   ```bash
   docker build -f Dockerfile.pipeline -t $DOCKER_USERNAME/usccb:pipeline .
   docker push $DOCKER_USERNAME/usccb:pipeline
   ```

2. **Create secrets** (in usccb namespace):
   ```bash
   kubectl create secret generic usccb-secrets -n usccb \
     --from-literal=supabase-url='your-supabase-url' \
     --from-literal=supabase-key='your-supabase-key' \
     --from-literal=genai-api-key='your-genai-key' \
     --from-literal=search-api-key='your-search-key' \
     --from-literal=search-cx='your-search-cx'
   ```

3. **Sync ArgoCD** - The pipeline will be deployed automatically

### Option 2: Manual Deployment
   ```bash
   ./scripts/deploy-pipeline.sh
   ```

## Files Explained

### Core Files
- `Dockerfile.pipeline` - Container image for the pipeline
- `pipeline-cronjob.yaml` - Scheduled daily execution
- `pipeline-job.yaml` - On-demand execution template
- `pipeline-secrets.yaml` - Secret template (DO NOT commit with real values)
- `pipeline-configmap.yaml` - Non-sensitive configuration

### Scripts
- `scripts/deploy-pipeline.sh` - Automated deployment script

## Usage

### Running Scheduled Jobs
The CronJob runs automatically daily at 2 AM UTC. Monitor with:
```bash
kubectl get cronjobs
kubectl get jobs
```

### Running Manual Jobs
Create a one-time job:
```bash
kubectl apply -f k8s/pipeline-job.yaml
```

Monitor job progress:
```bash
kubectl get jobs
kubectl logs -l job-name=usccb-pipeline-job
```

### Customizing Pipeline Arguments
Edit `pipeline-job.yaml` to modify the `args` section:
```yaml
args:
- "--diocese_id"
- "123"
- "--skip_schedules"
- "--max_parishes_per_diocese"
- "25"
```

Available arguments:
- `--skip_dioceses` - Skip diocese extraction
- `--skip_parish_directories` - Skip finding parish directories
- `--skip_parishes` - Skip parish extraction
- `--skip_schedules` - Skip schedule extraction
- `--skip_reporting` - Skip reporting
- `--diocese_id` - Process specific diocese ID
- `--max_parishes_per_diocese` - Limit parishes per diocese
- `--num_parishes_for_schedule` - Number for schedule extraction

### Monitoring and Troubleshooting

**View running pods:**
```bash
kubectl get pods -n usccb -l job-name=usccb-pipeline-cronjob
```

**Check logs:**
```bash
kubectl logs -f <pod-name> -n usccb
```

**Describe job status:**
```bash
kubectl describe job usccb-pipeline-job -n usccb
```

**View CronJob status:**
```bash
kubectl get cronjobs -n usccb
```

**Clean up completed jobs:**
```bash
kubectl delete job usccb-pipeline-job -n usccb
```

### Resource Configuration

The containers are configured with:
- **CPU**: 1 core (request) / 2 cores (limit)
- **Memory**: 2GB (request) / 4GB (limit)

Adjust in the YAML files based on your cluster capacity and needs.

### Security Notes

- Secrets are stored in Kubernetes Secrets, not in code
- Container runs as non-root user
- Chrome runs in headless mode with minimal privileges
- Network access is limited to required external APIs

### Accessing from Your Domain

Since you have Cloudflare tunnel and `usccb.diocesevitality.org`, you can:

1. **Add a web interface** by creating a FastAPI service that can trigger jobs
2. **Set up monitoring** with endpoints that show job status
3. **Create webhooks** that trigger pipeline runs from external events

Would you like me to create any of these additional components?