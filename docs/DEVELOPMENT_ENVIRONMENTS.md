# Development Environments Guide

This guide covers how to develop the Diocesan Vitality system in both local and cloud environments.

## 🏠 Local Development

For complete local development setup, see **[LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)**.

**Quick local setup:**
```bash
# Prerequisites
make env-check
make db-check
make webdriver-check

# Start local environment
make start-full

# Test with minimal data
make pipeline
```

**Local environment provides:**
- ✅ Fast iteration and debugging
- ✅ No cloud costs
- ✅ Full control over environment
- ✅ Works offline (except for APIs)
- ❌ Limited by local hardware resources
- ❌ Architecture differences from production

## ☁️ Cloud Development (dv-dev cluster)

The `dv-dev` cluster provides a production-like environment for testing and development using **GitOps with ArgoCD**.

### Prerequisites for Cluster Development

1. **kubectl configured for dv-dev cluster:**
```bash
# Verify cluster access
kubectl config current-context
# Should show: dv-dev

# If not configured, set up cluster access:
doctl kubernetes cluster kubeconfig save dv-dev
kubectl config use-context dv-dev
```

2. **Git workflow setup:**
```bash
# Ensure you're working with the correct branches
git checkout develop  # For dv-dev deployments
git checkout main     # For dv-stg deployments

# Verify ArgoCD applications are installed
kubectl get applications -n argocd | grep diocesan-vitality
```

### GitOps Development Workflow (Recommended)

**Deploy to dv-dev cluster via GitOps:**
```bash
# 1. Develop and test locally first
make start-full
make pipeline

# 2. Commit changes to develop branch
git add .
git commit -m "feat: implement new feature"
git push origin develop

# 3. ArgoCD automatically deploys to dv-dev cluster
# Monitor deployment
kubectl get pods -n diocesan-vitality-dev -w
```

**Monitor your deployment:**
```bash
# Check pod status
kubectl get pods -n diocesan-vitality-dev

# View logs
kubectl logs -f deployment/pipeline -n diocesan-vitality-dev
kubectl logs -f deployment/backend -n diocesan-vitality-dev

# Check ArgoCD application status
kubectl get application dv-dev-diocesan-vitality -n argocd

# Access the application
kubectl port-forward svc/frontend 3000:80 -n diocesan-vitality-dev
# Visit: http://localhost:3000
```

### Option 2: Remote Development with kubectl exec

**Connect to running pod for debugging:**
```bash
# List running pods
kubectl get pods -n diocesan-vitality-dev

# Connect to pipeline pod
kubectl exec -it deployment/pipeline -n diocesan-vitality-dev -- /bin/bash

# Inside the pod, you can:
# - Edit files with vi/nano
# - Run Python scripts directly
# - Access the same environment as production
# - Debug with live data
```

**Run development commands in cluster:**
```bash
# Run pipeline with test data
kubectl exec deployment/pipeline -n diocesan-vitality-dev -- \
  python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 5

# Run async extraction
kubectl exec deployment/pipeline -n diocesan-vitality-dev -- \
  python async_extract_parishes.py --diocese_id 123 --pool_size 2 --batch_size 4

# Check environment variables
kubectl exec deployment/pipeline -n diocesan-vitality-dev -- env | grep -E "(SUPABASE|GENAI)"
```

### Option 3: Kubernetes Job for One-off Tasks

**Create a development job:**
```bash
# Create a job YAML for testing
cat <<EOF > dev-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: dev-test-$(date +%s)
  namespace: diocesan-vitality-dev
spec:
  template:
    spec:
      containers:
      - name: pipeline
        image: tomknightatl/diocesan-vitality:latest
        command: ["python", "run_pipeline.py"]
        args: ["--diocese_id", "123", "--max_parishes_per_diocese", "3"]
        envFrom:
        - secretRef:
            name: pipeline-secrets
      restartPolicy: Never
  backoffLimit: 1
EOF

# Run the job
kubectl apply -f dev-job.yaml

# Monitor job progress
kubectl get jobs -n diocesan-vitality-dev
kubectl logs job/dev-test-* -n diocesan-vitality-dev
```

### GitOps Development Workflow with ArgoCD

**1. Feature development (develop branch → dv-dev cluster):**
```bash
# Create feature branch
git checkout develop
git pull origin develop
git checkout -b feature/my-new-feature

# Develop locally
make start-full
make pipeline

# Merge to develop and push
git checkout develop
git merge feature/my-new-feature
git push origin develop

# ArgoCD automatically deploys to dv-dev cluster
# Monitor deployment status
kubectl get application dv-dev-diocesan-vitality -n argocd -w
```

**2. Staging deployment (main branch → dv-stg cluster):**
```bash
# When ready for staging
git checkout main
git merge develop
git push origin main

# ArgoCD automatically deploys to dv-stg cluster
# Monitor staging deployment
kubectl get application dv-stg-diocesan-vitality -n argocd -w
```

**3. Monitor and debug:**
```bash
# Check application status
kubectl get all -n diocesan-vitality-dev

# View real-time logs
kubectl logs -f deployment/pipeline -n diocesan-vitality-dev

# Access the frontend
kubectl port-forward svc/frontend 3000:80 -n diocesan-vitality-dev &
# Visit http://localhost:3000/dashboard

# Debug database connections
kubectl exec deployment/pipeline -n diocesan-vitality-dev -- \
  python -c "from core.db import get_supabase_client; print('DB OK:', get_supabase_client().table('Dioceses').select('*').limit(1).execute())"

# Force ArgoCD sync if needed
argocd app sync dv-dev-diocesan-vitality
```

### Accessing Services in dv-dev Cluster

**Frontend Dashboard:**
```bash
# Port forward to access locally
kubectl port-forward svc/frontend 3000:80 -n diocesan-vitality-dev

# Visit: http://localhost:3000
# Dashboard: http://localhost:3000/dashboard
```

**Backend API:**
```bash
# Port forward backend
kubectl port-forward svc/backend 8000:8000 -n diocesan-vitality-dev

# Visit: http://localhost:8000/docs
# API: http://localhost:8000/api/dioceses
```

**WebSocket Monitoring:**
```bash
# Connect to WebSocket for real-time updates
# ws://localhost:8000/ws/monitoring (when port-forwarded)
```

### Development Environment Comparison

| Feature | Local Development | dv-dev Cluster |
|---------|-------------------|----------------|
| **Setup Speed** | Fast (minutes) | Medium (build/deploy) |
| **Resource Limits** | Local hardware | Cloud resources |
| **Production Similarity** | Different | Identical |
| **Debugging** | Full IDE support | kubectl/logs |
| **Network Access** | Limited | Full cloud access |
| **Cost** | Free | Small cloud cost |
| **Collaboration** | Individual | Shared environment |
| **Data Volume** | Limited by local | Full production scale |

### Recommended GitOps Development Flow

**For new features:**
```bash
# 1. Create feature branch and develop locally
git checkout develop
git checkout -b feature/my-feature
make start-full
# Code and test basic functionality

# 2. Push to develop branch for dv-dev testing
git checkout develop
git merge feature/my-feature
git push origin develop
# ArgoCD automatically deploys to dv-dev

# 3. Test in dv-dev with production-like environment
kubectl exec deployment/pipeline -n diocesan-vitality-dev -- \
  python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 5

# 4. Deploy to staging for final testing
git checkout main
git merge develop
git push origin main
# ArgoCD automatically deploys to dv-stg

# 5. Manual production deployment when ready
argocd app sync diocesan-vitality-app  # Manual production sync
```

**For debugging production issues:**
```bash
# 1. Reproduce locally if possible
make pipeline

# 2. Create debug branch and deploy to dev environment
git checkout develop
git checkout -b debug/production-issue
# Make debugging changes
git checkout develop
git merge debug/production-issue
git push origin develop
# ArgoCD deploys to dv-dev

# 3. Debug with production data scale
kubectl exec deployment/pipeline -n diocesan-vitality-dev -- \
  python async_extract_parishes.py --diocese_id $AFFECTED_DIOCESE --pool_size 1 --batch_size 1
```

## 🔧 Development Environment Management

### Creating Development/Staging Infrastructure

**Complete setup (clusters + ArgoCD + Cloudflare tunnels):**
```bash
cd k8s/cluster-management

# 1. Authenticate with Cloudflare (one-time setup)
cloudflared tunnel login

# 2. Create complete infrastructure
./create-dev-stg-clusters.sh
# Choose 'y' when prompted for dev/staging cluster creation
# Choose 'y' when prompted for ArgoCD setup
# Choose 'y' when prompted for Cloudflare tunnel setup

# Alternative: Setup components separately
./setup-argocd.sh                    # ArgoCD only
./setup-cloudflare-tunnels.sh        # Cloudflare tunnels only
```

**What this sets up:**
- ✅ `dv-dev` cluster with development configuration
- ✅ `dv-stg` cluster with staging configuration  
- ✅ ArgoCD installed in both clusters
- ✅ GitHub repository connected to ArgoCD
- ✅ ApplicationSets for automatic deployments
- ✅ Cloudflare tunnels for secure ingress
- ✅ DNS records and sealed secrets
- ✅ kubectl contexts configured

**Resulting infrastructure:**
- **Dev UI**: `https://dev.ui.diocesanvitality.org`
- **Dev API**: `https://dev.api.diocesanvitality.org`
- **Dev ArgoCD**: `https://dev.argocd.diocesanvitality.org`
- **Staging UI**: `https://stg.ui.diocesanvitality.org`
- **Staging API**: `https://stg.api.diocesanvitality.org`
- **Staging ArgoCD**: `https://stg.argocd.diocesanvitality.org`

**Destroy clusters:**
```bash
cd k8s/cluster-management
./destroy-dev-stg-clusters.sh
# Choose 'y' and type 'DELETE ALL' when prompted
```

### Switching Between Environments

**Local to cluster:**
```bash
# Stop local services
make stop

# Deploy to cluster via GitOps
git checkout develop
git add .
git commit -m "deploy: switch to cluster development"
git push origin develop
# ArgoCD automatically deploys to dv-dev

# Switch kubectl context
kubectl config use-context dv-dev
```

**Cluster to local:**
```bash
# Scale down cluster (optional)
kubectl scale deployment --all --replicas=0 -n diocesan-vitality-dev

# Start local
make start-full
```

### Environment Variables in dv-dev

The cluster uses the same environment variables as local development, but they're stored as Kubernetes secrets:

```bash
# View current secrets (values are base64 encoded)
kubectl get secrets pipeline-secrets -n diocesan-vitality-dev -o yaml

# Update secrets if needed (rarely required)
kubectl create secret generic pipeline-secrets \
  --from-env-file=.env \
  --namespace=diocesan-vitality-dev \
  --dry-run=client -o yaml | kubectl apply -f -
```

## 🚨 Troubleshooting Cloud Development

### Common Issues

**1. Can't connect to cluster:**
```bash
# Check cluster status
doctl kubernetes cluster list

# Recreate kubeconfig
doctl kubernetes cluster kubeconfig save dv-dev
kubectl config use-context dv-dev
```

**2. Pods failing to start:**
```bash
# Check pod status
kubectl get pods -n diocesan-vitality-dev

# View pod events
kubectl describe pod <pod-name> -n diocesan-vitality-dev

# Check logs
kubectl logs <pod-name> -n diocesan-vitality-dev
```

**3. Image pull errors:**
```bash
# Verify image exists
docker pull tomknightatl/diocesan-vitality:latest

# Check if custom image was pushed
docker images | grep diocesan-vitality
```

**4. Environment variable issues:**
```bash
# Check secrets exist
kubectl get secrets -n diocesan-vitality-dev

# Verify environment variables in pod
kubectl exec deployment/pipeline -n diocesan-vitality-dev -- env | grep SUPABASE
```

## 📚 Additional Resources

- **[LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)** - Complete local setup guide
- **[COMMANDS.md](COMMANDS.md)** - All available pipeline commands
- **[CI_CD_PIPELINE.md](CI_CD_PIPELINE.md)** - Automated deployment workflows
- **[scripts/deploy-cluster.sh](../scripts/deploy-cluster.sh)** - Manual deployment script
- **[k8s/environments/development/](../k8s/environments/development/)** - Development cluster configuration

---

**Choose your development approach:**
- **Quick iteration** → Local development
- **Production-like testing** → dv-dev cluster
- **Collaboration** → dv-dev cluster
- **Resource-intensive tasks** → dv-dev cluster