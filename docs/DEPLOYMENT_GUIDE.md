# 🚀 Deployment Guide

This guide explains how to deploy new code changes to production using GitOps principles with ArgoCD.

## 📋 Overview

The deployment process follows GitOps best practices:
1. **Build** new Docker images with timestamped tags
2. **Update** Kubernetes manifests with new image tags
3. **Commit** changes to Git
4. **ArgoCD** automatically syncs and deploys

## 🐳 Building and Deploying New Images

### Step 1: Build Images with Timestamp

For comprehensive Docker commands and deployment scripts, see the **[📝 Commands Guide](COMMANDS.md#docker-commands)**.

**Multi-Architecture Build (Recommended):**
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

echo "✅ All multi-arch images built and pushed with timestamp: $TIMESTAMP"
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

# Pipeline deployment
sed -i "s|image: tomatl/diocesan-vitality:pipeline-.*|image: tomatl/diocesan-vitality:pipeline-$TIMESTAMP|g" k8s/pipeline-deployment.yaml

echo "✅ Kubernetes manifests updated with new image tags"
```

### Step 4: Deploy via GitOps

```bash
# Stage the updated manifests
git add k8s/backend-deployment.yaml k8s/frontend-deployment.yaml k8s/pipeline-deployment.yaml

# Commit with descriptive message
git commit -m "Deploy timestamped images ($TIMESTAMP)

🐳 Image Updates:
- backend: tomatl/diocesan-vitality:backend-$TIMESTAMP
- frontend: tomatl/diocesan-vitality:frontend-$TIMESTAMP
- pipeline: tomatl/diocesan-vitality:pipeline-$TIMESTAMP

📝 Changes in this deployment:
- [Add description of what changed]
- [List any new features or fixes]
- [Note any breaking changes]"

# Push to trigger ArgoCD deployment
echo "🚀 Pushing to Git to trigger ArgoCD deployment..."
git push origin main

echo "✅ Deployment initiated! ArgoCD will sync automatically."
```

## 🏗️ Multi-Architecture Support

This project supports both ARM64 (development on Raspberry Pi/Apple Silicon) and AMD64 (production deployment) architectures.

### Why Multi-Arch?
- **Development Flexibility**: Build on ARM64 (Raspberry Pi, Mac M1/M2) and AMD64 (traditional x86)
- **Production Compatibility**: Deploy to x86 clusters while developing on ARM
- **Future-Proof**: Ready for ARM64 server adoption

### Architecture Considerations
- **Pipeline Image**: Requires Chrome/Chromium for web scraping - multi-arch build handles architecture-specific browser installation
- **Backend/Frontend**: Platform-agnostic Python and Node.js applications work on both architectures

## 📊 Monitoring Deployment

### Watch ArgoCD Sync

```bash
# Monitor ArgoCD application sync status
kubectl get application diocesan-vitality-app -n argocd -w

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

# Check pipeline deployment
kubectl describe deployment pipeline-deployment -n diocesan-vitality | grep Image:
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