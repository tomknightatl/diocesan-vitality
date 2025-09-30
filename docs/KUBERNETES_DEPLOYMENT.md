# Kubernetes Deployment Guide

This guide covers deploying the Diocesan Vitality system on Kubernetes clusters.

---

## ⚠️ **IMPORTANT: GitOps-First Deployment Policy**

This project uses **GitOps principles** with ArgoCD for all deployments:

### ✅ **Production Deployments (REQUIRED)**

```bash
# DO THIS: Update manifests in Git, ArgoCD syncs automatically
git add k8s/environments/production/kustomization.yaml
git commit -m "Update production images"
git push origin main
# ArgoCD automatically syncs changes to cluster
```

### ❌ **DO NOT Use kubectl for Production**

```bash
# DON'T DO THIS: Direct kubectl commands bypass GitOps
kubectl apply -f k8s/  # ❌ Creates drift between Git and cluster
kubectl set image ...  # ❌ Changes not tracked in Git
kubectl patch ...      # ❌ Manual changes get overwritten by ArgoCD
```

### ✅ **Development/Debugging (ALLOWED)**

```bash
kubectl get pods -n diocesan-vitality-dev     # ✅ Read-only operations
kubectl logs deployment/backend-deployment    # ✅ Debugging
kubectl describe pod ...                      # ✅ Investigation
kubectl exec -it pod-name -- /bin/bash       # ✅ Troubleshooting
```

**📖 See [DEPLOYMENT_WORKFLOW.md](DEPLOYMENT_WORKFLOW.md) for complete GitOps deployment procedures.**

---

## Overview

The system consists of three main components deployed as Kubernetes Deployments:

- **Backend**: FastAPI service (`tomatl/diocesan-vitality:backend`)
- **Frontend**: React dashboard (`tomatl/diocesan-vitality:frontend`)
- **Pipeline**: Data extraction engine (`tomatl/diocesan-vitality:pipeline`)

## Architecture

### Deployment Strategy

- **GitOps with ArgoCD** for all environment deployments (primary method)
- **Kustomize** for environment-specific configuration
- **Continuous Deployment** via Git commits → ArgoCD syncs
- **Resource-optimized** for small cluster nodes (s-1vcpu-2gb)
- **Multi-environment support** (development, staging, production)

### Worker Specialization

The system supports specialized worker deployments:

- **Discovery Workers**: Diocese and parish directory discovery (512Mi/200m CPU)
- **Extraction Workers**: Parish detail extraction (2.2Gi/800m CPU, scales 2-5 pods)
- **Schedule Workers**: Mass schedule extraction (1.5Gi/600m CPU, scales 1-3 pods)
- **Reporting Workers**: Analytics and reporting (512Mi/200m CPU)

## Quick Start

### 1. Prerequisites

**Required Tools:**

```bash
kubectl   # Kubernetes CLI
docker    # Container runtime
```

**Required Secrets:**

- Docker Hub credentials
- Supabase database credentials
- Google AI API keys
- Google Custom Search credentials

### 2. Build and Push Images

**Note**: CI/CD pipeline automatically builds and pushes images with environment-specific tags.

For manual builds (development only):

```bash
# Set timestamp for image tagging
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
ENV="development"  # or staging, production

# Build all components with proper tags
docker build -f backend/Dockerfile -t tomatl/diocesan-vitality:${ENV}-backend-${TIMESTAMP} backend/
docker build -f frontend/Dockerfile -t tomatl/diocesan-vitality:${ENV}-frontend-${TIMESTAMP} frontend/
docker build -f Dockerfile.pipeline -t tomatl/diocesan-vitality:${ENV}-pipeline-${TIMESTAMP} .

# Push to registry
docker push tomatl/diocesan-vitality:${ENV}-backend-${TIMESTAMP}
docker push tomatl/diocesan-vitality:${ENV}-frontend-${TIMESTAMP}
docker push tomatl/diocesan-vitality:${ENV}-pipeline-${TIMESTAMP}

# Update kustomization.yaml (ArgoCD will sync automatically)
cd k8s/environments/${ENV}
kustomize edit set image tomatl/diocesan-vitality:backend=tomatl/diocesan-vitality:${ENV}-backend-${TIMESTAMP}
kustomize edit set image tomatl/diocesan-vitality:frontend=tomatl/diocesan-vitality:${ENV}-frontend-${TIMESTAMP}
kustomize edit set image tomatl/diocesan-vitality:pipeline=tomatl/diocesan-vitality:${ENV}-pipeline-${TIMESTAMP}

# Commit and push (triggers ArgoCD sync)
git add kustomization.yaml
git commit -m "Update ${ENV} images to ${TIMESTAMP}"
git push
```

**Recommended**: Use the CI/CD pipeline (push to `develop` or `main`) instead of manual builds.

### 3. Create Kubernetes Secrets

**Docker Registry Secret:**

```bash
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=docker.io \
  --docker-username=tomatl \
  --docker-password=YOUR_PERSONAL_ACCESS_TOKEN \
  --docker-email=your-email@example.com \
  -n diocesan-vitality
```

**Application Secrets:**

```bash
kubectl create secret generic diocesan-vitality-secrets \
  -n diocesan-vitality \
  --from-literal=supabase-url="https://your-project.supabase.co" \
  --from-literal=supabase-key="your-supabase-service-role-key" \
  --from-literal=genai-api-key="your-google-gemini-api-key" \
  --from-literal=search-api-key="your-google-search-api-key" \
  --from-literal=search-cx="your-google-search-cx-id"
```

### 4. Deploy with ArgoCD

The manifests in `k8s/` are automatically deployed by ArgoCD to the `diocesan-vitality` namespace.

**Verify Deployment:**

```bash
# Check application status
kubectl get applications -n argocd

# Check pods
kubectl get pods -n diocesan-vitality

# Check services
kubectl get services -n diocesan-vitality
```

## Environment Management

### Development Environment

**Location**: `k8s/environments/development/`

**Deploy to Development:**

```bash
# Build development images
DEV_TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)-dev
docker buildx build --platform linux/amd64,linux/arm64 \
  -f backend/Dockerfile \
  -t tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP} \
  --push backend/

# Update manifests
sed -i "s|image: tomatl/diocesan-vitality:.*backend.*|image: tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP}|g" \
  k8s/environments/development/development-patches.yaml

# Deploy via GitOps
git add k8s/environments/development/
git commit -m "Development deployment: ${DEV_TIMESTAMP}"
git push origin develop
```

### Production Environment

**Location**: `k8s/environments/production/`

Production deployments are handled by the semantic release workflow, which:

1. Builds semantic-versioned images
2. Updates manifests with new image tags
3. Commits changes for ArgoCD to sync

## Worker Specialization

### Single Image Deployment

All worker types use the same container image with runtime specialization:

```yaml
env:
  - name: WORKER_TYPE
    value: "extraction" # discovery, extraction, schedule, reporting
```

### Scaling Configuration

**Discovery Workers:**

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "200m"
  limits:
    memory: "1Gi"
    cpu: "500m"
replicas: 1
```

**Extraction Workers:**

```yaml
resources:
  requests:
    memory: "2.2Gi"
    cpu: "800m"
  limits:
    memory: "4Gi"
    cpu: "1500m"
replicas: 2-5 # Auto-scaling based on load
```

## Monitoring and Operations

### Health Checks

**Check Component Status:**

```bash
# Overall cluster health
kubectl get pods -n diocesan-vitality

# Individual component logs
kubectl logs deployment/backend-deployment -n diocesan-vitality
kubectl logs deployment/frontend-deployment -n diocesan-vitality
kubectl logs deployment/pipeline-deployment -n diocesan-vitality
```

### Dashboard Monitoring

**Access Methods:**

- **Production**: https://diocesanvitality.org/dashboard
- **Local Port Forward**: `kubectl port-forward service/frontend-service 3000:80 -n diocesan-vitality`

**Real-time Monitoring:**

- Live extraction progress
- Circuit breaker status
- Worker health and performance
- Database connection status

### Pipeline Operations

**Restart Pipeline:**

```bash
kubectl rollout restart deployment pipeline-deployment -n diocesan-vitality
```

**Scale Workers:**

```bash
# Scale extraction workers
kubectl scale deployment extraction-workers --replicas=5 -n diocesan-vitality

# Scale schedule workers
kubectl scale deployment schedule-workers --replicas=3 -n diocesan-vitality
```

**Monitor Pipeline:**

```bash
# Watch pipeline logs
kubectl logs -f deployment/pipeline-deployment -n diocesan-vitality

# Check circuit breaker status
kubectl exec deployment/pipeline-deployment -n diocesan-vitality -- \
  python -c "from core.circuit_breaker import CircuitBreakerMonitor; print(CircuitBreakerMonitor().get_status())"
```

## Resource Management

### Cluster Requirements

**Minimum Cluster:**

- **Node Type**: s-1vcpu-2gb (DigitalOcean)
- **Total Usage**: ~15m CPU (~1.5%), ~128Mi memory (~8%)

**Resource Allocation:**

```yaml
Frontend: 5m CPU,  32Mi memory
Backend: 5m CPU,  64Mi memory
Pipeline: 5m CPU,  32Mi memory
```

**Production Cluster:**

- **Node Type**: s-2vcpu-4gb or larger
- **Multiple nodes** for high availability
- **Auto-scaling** enabled for worker pods

### Storage

**Persistent Volumes:**

- Not required for stateless application
- Database hosted on Supabase (external)
- Logs handled by cluster logging system

## Security

### Network Policies

```yaml
# Restrict egress to required services only
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: diocesan-vitality-egress
spec:
  podSelector:
    matchLabels:
      app: diocesan-vitality
  egress:
    - to: [] # Supabase, Google APIs, target websites
      ports:
        - protocol: TCP
          port: 443
```

### Pod Security

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  capabilities:
    drop:
      - ALL
```

### Secrets Management

**Best Practices:**

- Use Kubernetes Secrets for sensitive data
- Rotate secrets regularly
- Use sealed-secrets or external secret management
- Never commit secrets to Git

## Troubleshooting

### Common Issues

**ImagePullBackOff:**

```bash
# Check registry secret
kubectl get secret dockerhub-secret -n diocesan-vitality

# Verify image exists
docker pull tomatl/diocesan-vitality:backend
```

**CrashLoopBackOff:**

```bash
# Check logs for errors
kubectl logs deployment/pipeline-deployment -n diocesan-vitality --tail=100

# Common causes: missing dependencies, invalid configuration
```

**Pod Pending:**

```bash
# Check node resources
kubectl describe nodes

# Check resource requests vs. available
kubectl top nodes
kubectl top pods -n diocesan-vitality
```

### Debug Commands

**Pod Investigation:**

```bash
# Get pod details
kubectl describe pod <pod-name> -n diocesan-vitality

# Execute commands in pod
kubectl exec -it deployment/backend-deployment -n diocesan-vitality -- bash

# Check environment variables
kubectl exec deployment/pipeline-deployment -n diocesan-vitality -- env
```

**Network Debugging:**

```bash
# Test service connectivity
kubectl exec -it deployment/backend-deployment -n diocesan-vitality -- \
  curl http://frontend-service/

# Check DNS resolution
kubectl exec -it deployment/pipeline-deployment -n diocesan-vitality -- \
  nslookup backend-service
```

## Advanced Configuration

### Custom Resource Definitions

For complex deployments, consider using operators:

- **Prometheus Operator** for monitoring
- **ArgoCD Operator** for GitOps
- **Sealed Secrets Operator** for secret management

### Multi-Cluster Deployment

For high availability across regions:

1. Deploy to multiple Kubernetes clusters
2. Use external load balancer (Cloudflare)
3. Implement cross-cluster secret synchronization
4. Configure database replication

### Disaster Recovery

**Backup Strategy:**

- Database backups via Supabase
- Configuration stored in Git
- Automated cluster provisioning with Terraform

**Recovery Procedure:**

1. Provision new cluster with Terraform
2. Deploy applications via ArgoCD
3. Restore database from Supabase backup
4. Update DNS to point to new cluster

## Performance Optimization

### Resource Tuning

**CPU Optimization:**

```yaml
resources:
  requests:
    cpu: "100m" # Guaranteed CPU
  limits:
    cpu: "500m" # Maximum CPU burst
```

**Memory Optimization:**

```yaml
resources:
  requests:
    memory: "256Mi" # Guaranteed memory
  limits:
    memory: "512Mi" # Maximum memory
```

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: extraction-workers-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: extraction-workers
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## Related Documentation

- [Infrastructure Setup](INFRASTRUCTURE_SETUP.md) - Terraform and cloud setup
- [CI/CD Pipeline](CI_CD_PIPELINE.md) - Automated deployments
- [Monitoring](MONITORING.md) - Observability and alerting
- [Security](../SECURITY.md) - Security policies and procedures
