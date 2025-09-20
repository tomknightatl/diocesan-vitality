# Diocesan Vitality Pipeline Kubernetes Deployment

This directory contains Kubernetes manifests for running the Diocesan Vitality data extraction pipeline on your DOKS cluster.

## Overview

The pipeline runs as a **continuous Deployment** in Kubernetes, using the same Docker image naming convention as your backend and frontend:
- **Backend**: `tomatl/diocesan-vitality:backend`
- **Frontend**: `tomatl/diocesan-vitality:frontend`
- **Pipeline**: `tomatl/diocesan-vitality:pipeline`

The pipeline provides:
- **Continuous execution** via Deployment (always running, auto-restart on completion)
- **Real-time monitoring** via WebSocket dashboard integration
- **Secure credential management** via Kubernetes Secrets
- **Resource management** with minimal CPU and memory usage (optimized for s-1vcpu-2gb node)
- **Scalability** and **reliability** in cloud environment

## Quick Start

### Deploy with ArgoCD (Recommended)
Since the pipeline manifests are in the `k8s/` directory, they will be automatically deployed by your ArgoCD Application to the `diocesan-vitality` namespace.

1. **Build and push the pipeline image**:
   ```bash
   docker build -f Dockerfile.pipeline -t tomatl/diocesan-vitality:pipeline .
   docker push tomatl/diocesan-vitality:pipeline
   ```

2. **Ensure Docker registry secret exists**:
   ```bash
   kubectl create secret docker-registry dockerhub-secret \
     --docker-server=docker.io \
     --docker-username=tomatl \
     --docker-password=YOUR_PERSONAL_ACCESS_TOKEN \
     --docker-email=your-email@example.com \
     -n diocesan-vitality
   ```

3. **Create application secrets**:
   ```bash
   # Create the diocesan-vitality-secrets secret with your actual API credentials
   kubectl create secret generic diocesan-vitality-secrets \
     -n diocesan-vitality \
     --from-literal=supabase-url="https://your-project.supabase.co" \
     --from-literal=supabase-key="your-supabase-service-role-key" \
     --from-literal=genai-api-key="your-google-gemini-api-key" \
     --from-literal=search-api-key="your-google-search-api-key" \
     --from-literal=search-cx="your-google-search-cx-id"

   # Verify the secret was created successfully
   kubectl get secret diocesan-vitality-secrets -n diocesan-vitality
   kubectl describe secret diocesan-vitality-secrets -n diocesan-vitality  # Shows keys but not values
   ```

   **Required credentials:**
   - **supabase-url**: Your Supabase project URL (format: `https://xxxxx.supabase.co`)
   - **supabase-key**: Your Supabase service role key (found in Project Settings → API)
   - **genai-api-key**: Google Gemini API key (from Google AI Studio)
   - **search-api-key**: Google Custom Search JSON API key
   - **search-cx**: Google Custom Search Engine ID

4. **Deploy via ArgoCD** - Pipeline will be deployed automatically as a Deployment

### Deploying Updated Pipeline Image

When you make changes to the pipeline code and need to deploy a new version:

1. **Update requirements.txt** (if adding new dependencies):
   ```bash
   # Add any new Python packages to requirements.txt
   echo "new-package-name" >> requirements.txt
   ```

2. **Build and push new image**:
   ```bash
   # Build the updated pipeline image
   docker build -f Dockerfile.pipeline -t tomatl/diocesan-vitality:pipeline .

   # Push to Docker Hub
   docker push tomatl/diocesan-vitality:pipeline
   ```

3. **Deploy to Kubernetes**:
   ```bash
   # Restart deployment to pull latest image
   kubectl rollout restart deployment pipeline-deployment -n diocesan-vitality

   # Monitor the deployment
   kubectl rollout status deployment pipeline-deployment -n diocesan-vitality

   # Check new pod is running
   kubectl get pods -n diocesan-vitality -l app=pipeline
   ```

4. **Verify deployment**:
   ```bash
   # Check logs for successful startup
   kubectl logs -f deployment/pipeline-deployment -n diocesan-vitality

   # Monitor via dashboard
   # Visit: https://diocesanvitality.org/dashboard
   ```

### Manual Pipeline Restart
To restart the pipeline without rebuilding (triggers fresh execution):
```bash
kubectl rollout restart deployment pipeline-deployment -n diocesan-vitality
```

## Files Explained

### Core Files
- `Dockerfile.pipeline` - Container image for the pipeline
- `pipeline-deployment.yaml` - Continuous pipeline deployment
- `backend-deployment.yaml` - Backend API deployment
- `frontend-deployment.yaml` - Frontend web application
- `*-service.yaml` - Kubernetes services for each component
- `pipeline-secrets.yaml` - Secret template (DO NOT commit with real values)
- `pipeline-configmap.yaml` - Non-sensitive configuration

### ArgoCD Files
- `diocesan-vitality-app.yaml` - ArgoCD Application definition (in root directory)

## Usage

### Monitoring Pipeline
The pipeline runs continuously and can be monitored via:

**Dashboard (Recommended):**
- Visit https://diocesanvitality.org/dashboard
- Real-time WebSocket monitoring with live logs, circuit breaker status, and progress

**Command Line:**
```bash
# Check pod status
kubectl get pods -n diocesan-vitality -l app=pipeline

# Watch live logs
kubectl logs -f deployment/pipeline-deployment -n diocesan-vitality

# Check ArgoCD application health
kubectl get applications -n argocd
```

### Restarting Pipeline
To manually restart the pipeline (triggers fresh execution):
```bash
kubectl rollout restart deployment pipeline-deployment -n diocesan-vitality
```

### Customizing Pipeline Arguments
Edit `pipeline-deployment.yaml` to modify the `args` section:
```yaml
args:
- "--max_parishes_per_diocese"
- "50"
- "--num_parishes_for_schedule"
- "100"
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

### Troubleshooting

**Check deployment status:**
```bash
kubectl get deployments -n diocesan-vitality
kubectl describe deployment pipeline-deployment -n diocesan-vitality
```

**Check pod issues:**
```bash
kubectl get pods -n diocesan-vitality -l app=pipeline
kubectl describe pod <pod-name> -n diocesan-vitality
```

**View detailed logs:**
```bash
kubectl logs -f deployment/pipeline-deployment -n diocesan-vitality --tail=50
```

**Common Issues:**
- **ImagePullBackOff**: Check dockerhub-secret exists and is valid
- **CrashLoopBackOff**: Check logs for missing dependencies (e.g., PyPDF2)
- **Pending**: Check node resources, may need to restart other pods

**Force refresh pipeline image:**
```bash
# Restart deployment to pull latest image
kubectl rollout restart deployment pipeline-deployment -n diocesan-vitality

# Check rollout status
kubectl rollout status deployment pipeline-deployment -n diocesan-vitality
```

### Resource Configuration

The pipeline is optimized for resource-constrained environments:
- **CPU**: 5m (request) / 50m (limit)
- **Memory**: 32Mi (request) / 128Mi (limit)

This allows all three services (frontend, backend, pipeline) to run on a single s-1vcpu-2gb DOKS node.

**Total Resource Usage:**
- Frontend: 5m CPU, 32Mi memory
- Backend: 5m CPU, 64Mi memory
- Pipeline: 5m CPU, 32Mi memory
- **Total**: ~15m CPU (~1.5%), ~128Mi memory (~8%)

### Security Notes

- Secrets are stored in Kubernetes Secrets, not in code
- Container runs as non-root user
- Chrome runs in headless mode with minimal privileges
- Network access is limited to required external APIs

### Accessing from Your Domain

Since you have Cloudflare tunnel and `diocesanvitality.org`, you can:

1. **Add a web interface** by creating a FastAPI service that can trigger jobs
2. **Set up monitoring** with endpoints that show job status
3. **Create webhooks** that trigger pipeline runs from external events

Would you like me to create any of these additional components?