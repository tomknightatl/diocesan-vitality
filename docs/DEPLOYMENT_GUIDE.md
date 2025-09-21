# 🚀 Deployment Guide

This guide explains how to deploy new code changes to production using GitOps principles with ArgoCD.

Run the commands in this document on a x86_64 machine. (Because Docker has known issues building images on Raspberry Pi ARM64.)

## 📋 Overview

The deployment process follows GitOps best practices:
1. **Build** new Docker images with timestamped tags
2. **Update** Kubernetes manifests with new image tags
3. **Commit** changes to Git
4. **ArgoCD** automatically syncs and deploys

## 🚀 Automated Docker Builds with GitHub Actions

### 🚀 Automated Deployment (Recommended)

The project now uses **GitHub Actions** for automated multi-architecture Docker builds. Simply push code changes to trigger automatic builds:

```bash
# Quick deployment script
./scripts/deploy.sh
```

Or manually:

```bash
# Commit your changes
git add .
git commit -m "Your changes description"

# Push to main branch (triggers GitHub Actions)
git push origin main
```

**What happens automatically:**
1. 🔍 **Change Detection**: GitHub Actions detects changes in `backend/`, `frontend/`, or pipeline files
2. 🏗️ **Multi-Arch Build**: Builds images for both ARM64 and AMD64 architectures  
3. 📤 **Push to Registry**: Automatically pushes images to Docker Hub
4. 📝 **Update Manifests**: Updates Kubernetes deployment files with new image tags
5. 🔄 **GitOps Trigger**: Commits updated manifests back to repository for ArgoCD sync

### 📋 GitHub Actions Workflow Features

- **🎯 Smart Change Detection**: Only builds images that have changed
- **⚡ Multi-Architecture Support**: Builds for both ARM64 (development) and AMD64 (production)
- **🚀 Caching**: Uses GitHub Actions cache for faster builds
- **🔐 Secure**: Uses repository secrets for Docker Hub credentials
- **📊 Monitoring**: Full build logs and status in GitHub Actions tab
- **🔄 GitOps Integration**: Automatically updates Kubernetes manifests and triggers ArgoCD sync

### 🛠️ Manual Build Trigger

Force build all images regardless of changes:

```bash
# Using GitHub CLI
gh workflow run docker-build-push.yml -f force_build=true

# Or use the deployment script
./scripts/deploy.sh
# Choose option 2: "Force build all images"
```

### 📋 Setup Requirements

**Repository Secrets (required):**
- `DOCKER_USERNAME`: Your Docker Hub username  
- `DOCKER_PASSWORD`: Your Docker Hub password or access token

**Add secrets at:** `https://github.com/your-username/diocesan-vitality/settings/secrets/actions`

---

## 🐳 Manual Docker Builds (Alternative)

### Container Registry Options

This project supports both **Docker Hub** and **GitHub Container Registry (GHCR)**:

| Registry | Use Case | Access |
|----------|----------|--------|
| **Docker Hub** (`tomatl/diocesan-vitality`) | Production deployments, public images | Docker Hub account |
| **GitHub Container Registry** (`ghcr.io/tomknightatl/diocesan-vitality`) | Development, private/internal use | GitHub PAT token |

### Step 1: Build Images with Timestamp

For comprehensive Docker commands and deployment scripts, see the **[📝 Commands Guide](COMMANDS.md#docker-commands)**.

**Multi-Architecture Build (Recommended):**

Choose your target registry:

#### Docker Hub (Production)
```bash
# Generate timestamp
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)

# Enable buildx for multi-arch builds
docker buildx create --use --name multi-arch-builder 2>/dev/null || docker buildx use multi-arch-builder

# Build multi-arch images for both ARM64 (development) and AMD64 (production)
echo "🏗️ Building multi-arch backend image..."
docker buildx build --platform linux/amd64,linux/arm64 \
  -f backend/Dockerfile \
  -t tomatl/diocesan-vitality:backend-$TIMESTAMP \
  --push backend/

echo "🏗️ Building multi-arch frontend image..."
docker buildx build --platform linux/amd64,linux/arm64 \
  -f frontend/Dockerfile \
  -t tomatl/diocesan-vitality:frontend-$TIMESTAMP \
  --push frontend/

echo "🏗️ Building multi-arch pipeline image..."
docker buildx build --platform linux/amd64,linux/arm64 \
  -f Dockerfile.pipeline \
  -t tomatl/diocesan-vitality:pipeline-$TIMESTAMP \
  --push .

echo "✅ All multi-arch images built and pushed to Docker Hub with timestamp: $TIMESTAMP"
```

#### GitHub Container Registry (Development/Internal)
```bash
# Generate timestamp
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)

# Login to GitHub Container Registry (requires GitHub PAT token)
echo $GITHUB_TOKEN | docker login ghcr.io -u tomknightatl --password-stdin

# Build multi-arch images for GitHub Container Registry
echo "🏗️ Building multi-arch backend image for GHCR..."
docker buildx build --platform linux/amd64,linux/arm64 \
  -f backend/Dockerfile \
  -t ghcr.io/tomknightatl/diocesan-vitality:backend-$TIMESTAMP \
  --push backend/

echo "🏗️ Building multi-arch frontend image for GHCR..."
docker buildx build --platform linux/amd64,linux/arm64 \
  -f frontend/Dockerfile \
  -t ghcr.io/tomknightatl/diocesan-vitality:frontend-$TIMESTAMP \
  --push frontend/

echo "🏗️ Building multi-arch pipeline image for GHCR..."
docker buildx build --platform linux/amd64,linux/arm64 \
  -f Dockerfile.pipeline \
  -t ghcr.io/tomknightatl/diocesan-vitality:pipeline-$TIMESTAMP \
  --push .

echo "✅ All multi-arch images built and pushed to GHCR with timestamp: $TIMESTAMP"
```

**Single Architecture Build (Alternative):**
```bash
# Generate timestamp and build images for current architecture only
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
docker build -f backend/Dockerfile -t tomatl/diocesan-vitality:backend-$TIMESTAMP backend/
docker build -f frontend/Dockerfile -t tomatl/diocesan-vitality:frontend-$TIMESTAMP frontend/
docker build -f Dockerfile.pipeline -t tomatl/diocesan-vitality:pipeline-$TIMESTAMP .
```

**→ See [Commands Guide - Docker Section](COMMANDS.md#docker-commands) for complete build and deployment commands.**

### Step 2: Push Images to Docker Hub (Single-Arch Only)

*Note: Multi-arch builds automatically push during build with `--push` flag*

```bash
# Push all images to Docker Hub (only needed for single-arch builds)
echo "📤 Pushing backend image..."
docker push tomatl/diocesan-vitality:backend-$TIMESTAMP

echo "📤 Pushing frontend image..."
docker push tomatl/diocesan-vitality:frontend-$TIMESTAMP

echo "📤 Pushing pipeline image..."
docker push tomatl/diocesan-vitality:pipeline-$TIMESTAMP

echo "🎉 All images pushed to Docker Hub with timestamp: $TIMESTAMP"
```

### Step 3: Update Kubernetes Manifests

```bash
# Update image tags in deployment manifests
echo "📝 Updating Kubernetes manifests..."

# Backend deployment
sed -i "s|image: tomatl/diocesan-vitality:backend-.*|image: tomatl/diocesan-vitality:backend-$TIMESTAMP|g" k8s/backend-deployment.yaml

# Frontend deployment
sed -i "s|image: tomatl/diocesan-vitality:frontend-.*|image: tomatl/diocesan-vitality:frontend-$TIMESTAMP|g" k8s/frontend-deployment.yaml

# Pipeline deployment (legacy - single worker)
sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$TIMESTAMP|g" k8s/pipeline-deployment.yaml

# Specialized worker deployments (recommended)
sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$TIMESTAMP|g" k8s/discovery-deployment.yaml
sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$TIMESTAMP|g" k8s/extraction-deployment.yaml
sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$TIMESTAMP|g" k8s/schedule-deployment.yaml
sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$TIMESTAMP|g" k8s/reporting-deployment.yaml

echo "✅ Kubernetes manifests updated with new image tags"
```

### Step 4: Deploy via GitOps

```bash
# Stage the updated manifests (choose deployment strategy)
# Option 1: Legacy single worker deployment
git add k8s/backend-deployment.yaml k8s/frontend-deployment.yaml k8s/pipeline-deployment.yaml

# Option 2: Specialized worker deployments (recommended)
git add k8s/backend-deployment.yaml k8s/frontend-deployment.yaml \
       k8s/discovery-deployment.yaml k8s/extraction-deployment.yaml \
       k8s/schedule-deployment.yaml k8s/reporting-deployment.yaml

# Commit with descriptive message
git commit -m "Deploy timestamped images ($TIMESTAMP)

🐳 Image Updates:
- backend: tomatl/diocesan-vitality:backend-$TIMESTAMP
- frontend: tomatl/diocesan-vitality:frontend-$TIMESTAMP
- pipeline: tomatl/diocesan-vitality:pipeline-$TIMESTAMP

# Get current production timestamp
CURRENT_PROD_TIMESTAMP=$(kubectl get application diocesan-vitality-app -n argocd -o jsonpath='{.status.sync.revision}' | xargs git log --format='%B' -n 1 | grep -oP 'timestamped images \(\K[^)]+' | head -n 1)

if [ -n "$CURRENT_PROD_TIMESTAMP" ]; then
    echo "📊 Current production timestamp: $CURRENT_PROD_TIMESTAMP"

    # Get commit messages since the current production timestamp
    CHANGES_SINCE=$(git log --oneline --grep="Deploy timestamped images ($CURRENT_PROD_TIMESTAMP)" --since="$(git log --grep="Deploy timestamped images ($CURRENT_PROD_TIMESTAMP)" --format='%ci' -n 1)" --format='- %s' | grep -v "Deploy timestamped images" | head -10)

    if [ -n "$CHANGES_SINCE" ]; then
        DEPLOYMENT_NOTES="
📝 Changes since production ($CURRENT_PROD_TIMESTAMP):
$CHANGES_SINCE"
    else
        DEPLOYMENT_NOTES="
📝 Changes in this deployment:
- [Add description of what changed]
- [List any new features or fixes]
- [Note any breaking changes]"
    fi
else
    echo "⚠️ Could not determine current production timestamp, using default format"
    DEPLOYMENT_NOTES="
📝 Changes in this deployment:
- [Add description of what changed]
- [List any new features or fixes]
- [Note any breaking changes]"
fi

echo "$DEPLOYMENT_NOTES""

# Push to trigger ArgoCD deployment
echo "🚀 Pushing to Git to trigger ArgoCD deployment..."
git push origin main

echo "✅ Deployment initiated! ArgoCD will sync automatically."
```

## 🎯 Worker Specialization Deployment

The system supports two deployment strategies:

### Legacy Deployment (Single Worker Type)
Uses `k8s/pipeline-deployment.yaml` with all pipeline steps in one worker type.

### Specialized Workers (Recommended)
Uses separate deployments for optimized resource allocation:

| Worker Type | File | Resources | Replicas | Purpose |
|-------------|------|-----------|----------|---------|
| Discovery | `discovery-deployment.yaml` | 512Mi/200m CPU | 1 | Steps 1-2: Diocese + Parish directory discovery |
| Extraction | `extraction-deployment.yaml` | 2.2Gi/800m CPU | 2-5 (HPA) | Step 3: Parish detail extraction |
| Schedule | `schedule-deployment.yaml` | 1.5Gi/600m CPU | 1-3 (HPA) | Step 4: Mass schedule extraction |
| Reporting | `reporting-deployment.yaml` | 512Mi/200m CPU | 1 | Step 5: Analytics and reporting |

### Migration to Specialized Workers

**Step 1: Scale down legacy deployment**
```bash
kubectl scale deployment pipeline-deployment --replicas=0 -n diocesan-vitality
```

**Step 2: Deploy specialized workers**
```bash
kubectl apply -f k8s/discovery-deployment.yaml
kubectl apply -f k8s/extraction-deployment.yaml
kubectl apply -f k8s/extraction-hpa.yaml
kubectl apply -f k8s/schedule-deployment.yaml
kubectl apply -f k8s/schedule-hpa.yaml
kubectl apply -f k8s/reporting-deployment.yaml
```

**Step 3: Verify deployment**
```bash
kubectl get pods -n diocesan-vitality -l worker-type
kubectl get hpa -n diocesan-vitality
```

### Benefits of Specialized Workers
- **Resource Efficiency**: Right-sized resources per task type
- **Independent Scaling**: Scale extraction workers without affecting discovery
- **Better Fault Isolation**: WebDriver issues don't affect parish discovery
- **Cost Optimization**: Run expensive workers only when needed

## 🏗️ Multi-Architecture Support

This project supports both ARM64 (development on Raspberry Pi/Apple Silicon) and AMD64 (production deployment) architectures.

### Why Multi-Arch?
- **Development Flexibility**: Build on ARM64 (Raspberry Pi, Mac M1/M2) and AMD64 (traditional x86)
- **Production Compatibility**: Deploy to x86 clusters while developing on ARM
- **Future-Proof**: Ready for ARM64 server adoption

### Architecture Considerations
- **Pipeline Image**: Requires Chrome/Chromium for web scraping - multi-arch build handles architecture-specific browser installation
- **Backend/Frontend**: Platform-agnostic Python and Node.js applications work on both architectures

## 🔄 Development Cluster Deployment

### Overview

In addition to production deployments, you can deploy to a development cluster for testing changes in a production-like environment.

### Development Deployment Workflow

#### Option 1: Automatic via GitHub Actions
```bash
# Push to develop branch triggers automatic development deployment
git checkout develop
git push origin develop

# GitHub Actions will:
# 1. Build multi-arch images with development tags
# 2. Push to Docker Hub
# 3. Update k8s/environments/development/ manifests
# 4. Commit changes back to develop branch
# 5. ArgoCD syncs to development cluster
```

#### Option 2: Manual Development Deployment
```bash
# Build and push development images (see previous section)
DEV_TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)-dev

# Build and push to Docker Hub or GHCR
docker buildx build --platform linux/amd64,linux/arm64 \
  -f backend/Dockerfile \
  -t tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP} \
  --push backend/

# Update development manifests
sed -i "s|image: tomatl/diocesan-vitality:.*backend.*|image: tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP}|g" k8s/environments/development/development-patches.yaml

# Commit and push to develop branch
git add k8s/environments/development/
git commit -m "Development deployment: ${DEV_TIMESTAMP}"
git push origin develop
```

### Development Cluster Monitoring

Monitor the development cluster deployment:

```bash
# Switch to development cluster
kubectl config use-context do-nyc2-dv-dev

# Monitor ArgoCD application sync for development
kubectl get application diocesan-vitality-dev -n argocd -w

# Watch development pods
kubectl get pods -n diocesan-vitality-dev -w

# Check development deployments
kubectl get deployments -n diocesan-vitality-dev

# View development logs
kubectl logs deployment/backend-deployment -n diocesan-vitality-dev --follow
kubectl logs deployment/extraction-deployment -n diocesan-vitality-dev --follow
```

### Development vs Production Environments

| **Development** | **Production** |
|----------------|----------------|
| `kubectl config use-context do-nyc2-dv-dev` | `kubectl config use-context do-nyc2-dv-prd` |
| `diocesan-vitality-dev` namespace | `diocesan-vitality` namespace |
| ArgoCD syncs from `develop` branch | ArgoCD syncs from `main` branch |
| `k8s/environments/development/` | `k8s/environments/production/` |
| Development image tags (`-dev` suffix) | Production image tags (timestamps only) |

## 📊 Monitoring Deployment

### Watch ArgoCD Sync

```bash
# Production monitoring
kubectl get application diocesan-vitality-app -n argocd -w

# Development monitoring
kubectl get application diocesan-vitality-dev -n argocd -w

# Check sync status once
kubectl get application diocesan-vitality-app -n argocd -o jsonpath='{.status.sync.status}'
```

### Monitor Pod Rollout

```bash
# Watch pods being updated
kubectl get pods -n diocesan-vitality -w

# Check current pod status
kubectl get pods -n diocesan-vitality -o wide

# Verify new images are deployed
kubectl describe pods -n diocesan-vitality | grep "Image:" | sort | uniq
```

### Verify Specific Services

```bash
# Check backend deployment
kubectl describe deployment backend-deployment -n diocesan-vitality | grep Image:

# Check frontend deployment
kubectl describe deployment frontend-deployment -n diocesan-vitality | grep Image:

# Check pipeline deployment (legacy)
kubectl describe deployment pipeline-deployment -n diocesan-vitality | grep Image:

# Check specialized worker deployments
kubectl describe deployment discovery-deployment -n diocesan-vitality | grep Image:
kubectl describe deployment extraction-deployment -n diocesan-vitality | grep Image:
kubectl describe deployment schedule-deployment -n diocesan-vitality | grep Image:
kubectl describe deployment reporting-deployment -n diocesan-vitality | grep Image:
```

## 🔄 Rollback Process

If you need to rollback to a previous version:

```bash
# Find previous image timestamp from git history
git log --oneline -10 | grep "Deploy timestamped images"

# Update manifests to previous timestamp
ROLLBACK_TIMESTAMP="2025-09-15-17-30-45"  # Replace with desired timestamp

# Update manifests
sed -i "s|image: tomatl/diocesan-vitality:backend-.*|image: tomatl/diocesan-vitality:backend-$ROLLBACK_TIMESTAMP|g" k8s/backend-deployment.yaml
sed -i "s|image: tomatl/diocesan-vitality:frontend-.*|image: tomatl/diocesan-vitality:frontend-$ROLLBACK_TIMESTAMP|g" k8s/frontend-deployment.yaml
sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$ROLLBACK_TIMESTAMP|g" k8s/pipeline-deployment.yaml

# Commit and push rollback
git add k8s/*.yaml
git commit -m "Rollback to images from $ROLLBACK_TIMESTAMP"
git push origin main
```

## 🎯 Complete Deployment Script

For the complete deployment script and all deployment commands, see the **[📝 Commands Guide - Complete Deployment Script](COMMANDS.md#complete-deployment-script)**.

The script handles:
- Timestamped image building
- Docker Hub pushing
- Kubernetes manifest updates
- GitOps commit and push

**→ See [Commands Guide](COMMANDS.md#complete-deployment-script) for the full automated deployment script.**

## 💡 Best Practices

- **Always test locally** before deploying to production
- **Use multi-arch builds** for development flexibility and production compatibility
- **Use descriptive commit messages** explaining what changed
- **Monitor deployments** to ensure they complete successfully
- **Keep timestamps** for easy rollback identification
- **Document breaking changes** in commit messages
- **Verify health checks** pass after deployment

## 🔧 Troubleshooting

### Common Issues

1. **Image pull errors**: Verify images were pushed to Docker Hub successfully
2. **ArgoCD not syncing**: Check application status with `kubectl describe application diocesan-vitality-app -n argocd`
3. **Pods stuck in pending**: Check resource constraints and node capacity
4. **Health check failures**: Review pod logs with `kubectl logs -n diocesan-vitality <pod-name>`
5. **Architecture mismatch**: Use multi-arch builds to support both ARM64 and AMD64

### Multi-Arch Troubleshooting

```bash
# Check if buildx is available
docker buildx version

# List available builders
docker buildx ls

# Inspect multi-arch image
docker buildx imagetools inspect tomatl/diocesan-vitality:backend-$TIMESTAMP
```

### Getting Help

- Check ArgoCD dashboard for sync status
- Review pod events: `kubectl describe pods -n diocesan-vitality`
- Check application logs: `kubectl logs -n diocesan-vitality deployment/<deployment-name>`
