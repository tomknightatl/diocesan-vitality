# GitOps CI/CD Setup Guide

This guide will help you set up a simple CI/CD pipeline using GitOps principles for the USCCB project.

## Overview

Our CI/CD pipeline follows these principles:
- **Git as Single Source of Truth**: All deployments are driven by Git commits
- **Declarative Configuration**: Kubernetes manifests define the desired state
- **Automated Reconciliation**: ArgoCD continuously syncs Git state with cluster state
- **Progressive Delivery**: Changes flow through dev → staging → production

## Architecture

```
Developer → GitHub → GitHub Actions → Docker Hub → ArgoCD → Kubernetes
    ↑                                                            ↓
    └──────────────── GitOps Feedback Loop ────────────────────┘
```

## Prerequisites

1. **GitHub Repository Secrets** (Settings → Secrets and variables → Actions):
   - `DOCKER_USERNAME`: Your Docker Hub username
   - `DOCKER_PASSWORD`: Your Docker Hub access token

2. **ArgoCD Installed** in your Kubernetes cluster

3. **GitHub CLI** installed locally (for manual deployments)

## Quick Start

### Step 1: Set Up GitHub Secrets

```bash
# Using GitHub CLI
gh secret set DOCKER_USERNAME --body "your-dockerhub-username"
gh secret set DOCKER_PASSWORD --body "your-dockerhub-token"
```

### Step 2: Create Development Branch

```bash
# Create a develop branch for continuous integration
git checkout -b develop
git push -u origin develop
```

### Step 3: Deploy ArgoCD Application

```bash
# Deploy the ArgoCD application for dev environment
kubectl apply -f k8s/argocd/usccb-app-dev.yaml
```

### Step 4: Test the Pipeline

1. **Make a change** to your code
2. **Push to develop branch**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin develop
   ```
3. **Watch the CI pipeline** in GitHub Actions
4. **Monitor ArgoCD** for automatic deployment

## Workflow Explained

### Continuous Integration (CI)

When you push code to GitHub:

1. **Tests Run**: Python tests execute automatically
2. **Docker Build**: If tests pass, Docker images are built
3. **Image Push**: Images are tagged and pushed to Docker Hub
4. **Tag Strategy**:
   - `main` branch → `backend-latest`, `frontend-latest`
   - `develop` branch → `backend-develop`, `frontend-develop`
   - Feature branches → `backend-<commit-sha>`, `frontend-<commit-sha>`

### Continuous Deployment (CD)

ArgoCD monitors your Git repository:

1. **Auto-Sync**: ArgoCD detects changes in the `k8s/` directory
2. **Apply Changes**: New manifests are applied to the cluster
3. **Health Checks**: ArgoCD monitors application health
4. **Rollback**: Automatic rollback on failure (if configured)

## Development Workflow

### Local Development

```bash
# Run tests locally
make test

# Build and run with docker-compose
make run-local

# Check logs
docker-compose logs -f

# Stop local environment
make stop-local
```

### Feature Development

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and test locally
# ... edit files ...
make test
make run-local

# Push to trigger CI
git push origin feature/my-feature

# Create PR to develop branch
gh pr create --base develop
```

### Manual Deployment

For controlled deployments to specific environments:

```bash
# Deploy to dev environment
make deploy-dev

# Deploy to production (with confirmation)
make deploy-prod

# Or use GitHub Actions directly
gh workflow run cd.yml -f environment=dev -f image_tag=develop
```

## Environment Promotion Strategy

### GitFlow-inspired Approach

```
feature/* → develop → staging → main (production)
```

1. **Feature Branches**: Development work
2. **Develop Branch**: Integration testing (auto-deploy to dev)
3. **Staging Branch**: Pre-production testing (optional)
4. **Main Branch**: Production releases (auto-deploy to prod)

### Current Simple Setup

For now, we're keeping it simple:
- `develop` → Dev environment (auto-deploy)
- `main` → Production environment (manual or auto-deploy)

## Monitoring and Rollback

### Check Deployment Status

```bash
# View ArgoCD application status
kubectl get application usccb-dev -n argocd

# Get detailed status
kubectl describe application usccb-dev -n argocd

# View application in ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Then open https://localhost:8080
```

### Rollback if Needed

```bash
# Via ArgoCD CLI
argocd app rollback usccb-dev --revision <previous-revision>

# Or via Git revert
git revert HEAD
git push

# ArgoCD will automatically sync to the reverted state
```

## Advanced Features (Future Enhancements)

### 1. Automated Manifest Updates

Instead of manual manifest updates, automate with:
```yaml
# In CD workflow, use yq to update image tags
- name: Update image tag
  run: |
    yq eval '.spec.template.spec.containers[0].image = "${{ env.NEW_IMAGE }}"' \
      -i k8s/backend-deployment.yaml
```

### 2. PR-based Deployments

Create PRs for production deployments:
```yaml
# Auto-create PR for production
- uses: peter-evans/create-pull-request@v5
  with:
    title: "Deploy ${{ github.sha }} to production"
    branch: auto-deploy/prod-${{ github.sha }}
```

### 3. Slack Notifications

Add notifications for deployment events:
```yaml
- name: Notify Slack
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "Deployment to ${{ inputs.environment }} completed!"
      }
```

### 4. Automated Testing in K8s

Run integration tests in the cluster:
```yaml
- name: Run smoke tests
  run: |
    kubectl run test-pod --image=curlimages/curl \
      --rm -i --restart=Never -- \
      curl http://frontend-service.usccb-dev.svc.cluster.local
```

## Troubleshooting

### Common Issues

1. **Docker Push Fails**
   ```bash
   # Check Docker Hub login
   docker login
   # Verify secrets in GitHub
   gh secret list
   ```

2. **ArgoCD Not Syncing**
   ```bash
   # Check application status
   kubectl get app usccb-dev -n argocd -o yaml
   # Force sync
   argocd app sync usccb-dev
   ```

3. **Tests Failing in CI**
   ```bash
   # Run tests locally with same Python version
   python3.11 -m pytest tests/ -v
   ```

## Security Considerations

1. **Never commit secrets** to Git
2. **Use GitHub Secrets** for sensitive data
3. **Rotate Docker Hub tokens** regularly
4. **Use RBAC** in Kubernetes
5. **Enable branch protection** for main branch

## Next Steps

1. **Set up staging environment** for better testing
2. **Add integration tests** to CI pipeline
3. **Implement blue-green deployments** with ArgoCD
4. **Add monitoring** with Prometheus/Grafana
5. **Set up alerts** for deployment failures

## Quick Reference

```bash
# Always start by loading environment variables
source .env

# Check CI status
gh run list

# View CI logs
gh run view <run-id> --log

# Trigger manual deployment
gh workflow run cd.yml -f environment=dev -f image_tag=develop

# Check ArgoCD sync status
argocd app get usccb-dev

# Force ArgoCD sync
argocd app sync usccb-dev

# Rollback deployment
argocd app rollback usccb-dev <revision>

# Quick Docker Hub login check
echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin
```

---

Remember: Start simple, iterate often, and gradually add complexity as needed!