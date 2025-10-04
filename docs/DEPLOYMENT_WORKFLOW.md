# 🚀 Deployment Workflow Guide

This guide explains how to deploy code changes through the Development → Staging → Production pipeline using GitOps principles.

## 📋 Table of Contents

- [Overview](#overview)
- [Environment Architecture](#environment-architecture)
- [Deployment Flow](#deployment-flow)
- [Step-by-Step Procedures](#step-by-step-procedures)
- [Monitoring Deployments](#monitoring-deployments)
- [Rollback Procedures](#rollback-procedures)
- [Troubleshooting](#troubleshooting)

## Overview

Our deployment workflow follows **GitOps principles** where:

- ✅ Git is the single source of truth
- ✅ All deployments are triggered by Git commits
- ✅ ArgoCD automatically syncs cluster state with Git
- ✅ No direct kubectl access needed from CI/CD
- ✅ Full audit trail of all deployments

### Key Principle: Git → ArgoCD → Cluster

```
Developer Push → CI/CD Builds Images → Updates Git Manifests → ArgoCD Syncs → Cluster Updated
```

## Environment Architecture

### 🧪 Development Environment

- **Cluster**: `do-nyc2-dv-dev`
- **Branch**: `develop`
- **Namespace**: `diocesan-vitality-dev`
- **Purpose**: Feature development and testing
- **Auto-deploy**: ✅ Yes (on push to `develop`)
- **Approval**: ❌ Not required
- **URLs**:
  - Frontend: https://dev.ui.diocesanvitality.org
  - Backend: https://dev.api.diocesanvitality.org
  - ArgoCD: https://dev.argocd.diocesanvitality.org

### 🎭 Staging Environment

- **Cluster**: `do-nyc2-dv-stg`
- **Branch**: `main`
- **Namespace**: `diocesan-vitality-staging`
- **Purpose**: Pre-production testing and validation
- **Auto-deploy**: ✅ Yes (on push to `main`)
- **Approval**: ❌ Not required
- **URLs**:
  - Frontend: https://stg.ui.diocesanvitality.org
  - Backend: https://stg.api.diocesanvitality.org
  - ArgoCD: https://stg.argocd.diocesanvitality.org

### 🚀 Production Environment

- **Cluster**: `do-nyc2-dv-prd`
- **Branch**: `main`
- **Namespace**: `diocesan-vitality`
- **Purpose**: Live production system
- **Auto-deploy**: ❌ No (requires manual trigger)
- **Approval**: ✅ Required (GitHub environment protection)
- **URLs**:
  - Frontend: https://diocesanvitality.org
  - Backend: https://api.diocesanvitality.org
  - ArgoCD: https://prd.argocd.diocesanvitality.org

## Deployment Flow

### High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  1. DEVELOPMENT                                                  │
│                                                                  │
│  git push origin develop                                        │
│         ↓                                                        │
│  [Auto] CI/CD Triggers                                          │
│         ↓                                                        │
│  Build Images: development-backend-*, development-frontend-*    │
│         ↓                                                        │
│  Update: k8s/environments/development/kustomization.yaml        │
│         ↓                                                        │
│  Commit & Push to develop                                       │
│         ↓                                                        │
│  ArgoCD Syncs → do-nyc2-dv-dev                                  │
│                                                                  │
│  ✅ Development Deployed                                         │
└─────────────────────────────────────────────────────────────────┘
                           ↓
                   [Test & Validate]
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. STAGING                                                      │
│                                                                  │
│  git checkout main                                              │
│  git merge develop                                              │
│  git push origin main                                           │
│         ↓                                                        │
│  [Auto] CI/CD Triggers                                          │
│         ↓                                                        │
│  Build Images: staging-backend-*, staging-frontend-*            │
│         ↓                                                        │
│  Update: k8s/environments/staging/kustomization.yaml            │
│         ↓                                                        │
│  Commit & Push to main                                          │
│         ↓                                                        │
│  ArgoCD Syncs → do-nyc2-dv-stg                                  │
│                                                                  │
│  ✅ Staging Deployed                                             │
└─────────────────────────────────────────────────────────────────┘
                           ↓
                   [Smoke Tests]
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. PRODUCTION                                                   │
│                                                                  │
│  GitHub Actions → Workflow Dispatch                             │
│         ↓                                                        │
│  [Manual] Select "production" target                            │
│         ↓                                                        │
│  [Manual Approval Required] ⚠️                                   │
│         ↓                                                        │
│  Build Images: production-backend-*, production-frontend-*      │
│         ↓                                                        │
│  Update: k8s/environments/production/kustomization.yaml         │
│         ↓                                                        │
│  Commit & Push to main                                          │
│         ↓                                                        │
│  ArgoCD Syncs → do-nyc2-dv-prd                                  │
│                                                                  │
│  🎉 Production Deployed                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Step-by-Step Procedures

### 🧪 Deploying to Development

**When to use**: Feature development, bug fixes, experimental changes

1. **Create/work on feature branch:**

   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/my-new-feature

   # Make your changes
   git add .
   git commit -m "feat: Add new feature"
   git push origin feature/my-new-feature
   ```

2. **Create Pull Request:**
   - Go to GitHub
   - Create PR from `feature/my-new-feature` → `develop`
   - Wait for code quality checks to pass
   - Get code review approval
   - Merge to `develop`

3. **Automatic deployment happens:**
   - ✅ CI/CD workflow triggers automatically
   - ✅ Builds Docker images with `development-` prefix
   - ✅ Updates `k8s/environments/development/kustomization.yaml`
   - ✅ Commits changes back to `develop` branch
   - ✅ ArgoCD detects change and syncs to cluster

4. **Verify deployment:**

   ```bash
   # Check ArgoCD sync status
   # Visit: https://dev.argocd.diocesanvitality.org

   # Or via kubectl (if you have cluster access)
   kubectl config use-context do-nyc2-dv-dev
   kubectl get pods -n diocesan-vitality-dev
   kubectl get applications -n argocd
   ```

5. **Test your changes:**
   - Frontend: https://dev.ui.diocesanvitality.org
   - Backend: https://dev.api.diocesanvitality.org
   - Check logs in ArgoCD UI or via kubectl

**Timeline**: ~5-10 minutes from merge to live

---

### 🎭 Promoting to Staging

**When to use**: After dev testing is complete, ready for pre-production validation

1. **Ensure develop is stable:**

   ```bash
   # Make sure all tests pass in dev
   # Verify dev environment is working correctly
   ```

2. **Merge develop to main:**

   ```bash
   git checkout main
   git pull origin main
   git merge develop

   # Review the changes
   git log --oneline main..develop

   # Push to trigger staging deployment
   git push origin main
   ```

3. **Automatic deployment happens:**
   - ✅ CI/CD workflow triggers automatically
   - ✅ Builds Docker images with `staging-` prefix
   - ✅ Updates `k8s/environments/staging/kustomization.yaml`
   - ✅ Commits changes back to `main` branch
   - ✅ ArgoCD detects change and syncs to cluster

4. **Verify staging deployment:**

   ```bash
   # Check ArgoCD sync status
   # Visit: https://stg.argocd.diocesanvitality.org

   # Or via kubectl (if you have cluster access)
   kubectl config use-context do-nyc2-dv-stg
   kubectl get pods -n diocesan-vitality-staging
   kubectl get applications -n argocd
   ```

5. **Run staging validation:**
   - Frontend: https://stg.ui.diocesanvitality.org
   - Backend: https://stg.api.diocesanvitality.org
   - Run smoke tests
   - Verify data pipeline functionality
   - Check monitoring dashboards

**Timeline**: ~5-10 minutes from merge to live

---

### 🚀 Deploying to Production

**When to use**: After staging validation is complete, ready for production release

**⚠️ IMPORTANT**: Production deployments require manual approval!

1. **Verify staging is stable:**
   - ✅ All smoke tests passed
   - ✅ No critical errors in logs
   - ✅ Performance metrics acceptable
   - ✅ Data quality validated

2. **Trigger production deployment:**
   - Go to: https://github.com/tomknightatl/diocesan-vitality/actions
   - Click on "Multi-Cluster CI/CD Pipeline"
   - Click "Run workflow" button (top right)
   - Configure workflow:
     - **Branch**: `main`
     - **Target cluster**: `production`
     - **Force deploy**: `false` (skip tests only if absolutely necessary)
   - Click "Run workflow"

3. **Monitor workflow progress:**
   - Click on the running workflow
   - Watch stages complete:
     - ✅ Code Quality
     - ✅ Test Suite
     - ✅ Build Images
     - ⏸️ **Waiting for approval...**

4. **Approve production deployment:**
   - Workflow will pause at "production" environment
   - Review deployment details
   - Click "Review deployments"
   - Check the "production" box
   - Click "Approve and deploy"

5. **Automatic deployment continues:**
   - ✅ Builds Docker images with `production-` prefix
   - ✅ Updates `k8s/environments/production/kustomization.yaml`
   - ✅ Commits changes to `main` branch
   - ✅ ArgoCD detects change and syncs to cluster

6. **Verify production deployment:**

   ```bash
   # Check ArgoCD sync status
   # Visit: https://prd.argocd.diocesanvitality.org

   # Or via kubectl (if you have cluster access)
   kubectl config use-context do-nyc2-dv-prd
   kubectl get pods -n diocesan-vitality
   kubectl get applications -n argocd
   ```

7. **Post-deployment validation:**
   - Frontend: https://diocesanvitality.org
   - Backend: https://api.diocesanvitality.org
   - Monitor application logs
   - Check error rates
   - Verify data pipeline is running
   - Monitor user traffic

**Timeline**: ~10-15 minutes from approval to live

---

## Monitoring Deployments

### ArgoCD Dashboards

Each environment has its own ArgoCD instance for monitoring GitOps sync status:

- **Development**: https://devargocd.diocesanvitality.org
- **Staging**: https://stgargocd.diocesanvitality.org
- **Production**: https://argocd.diocesanvitality.org

**Login credentials**: See `.argocd-admin-password` file or GitHub secrets

### What to Monitor in ArgoCD

1. **Application Health**:
   - Green = Healthy
   - Yellow = Progressing
   - Red = Degraded

2. **Sync Status**:
   - Synced = Git matches cluster
   - OutOfSync = Git changes not yet applied
   - Unknown = ArgoCD can't determine status

3. **Recent Activity**:
   - View deployment history
   - See which commits triggered syncs
   - Check rollout progress

### GitHub Actions Monitoring

Monitor CI/CD pipeline progress:

- **All workflows**: https://github.com/tomknightatl/diocesan-vitality/actions
- **Specific workflow**: Click on workflow run to see detailed logs

### Application Monitoring

- **Frontend Dashboard**: Check application UI is loading
- **Backend API Health**: Check `/health` or `/docs` endpoints
- **Data Pipeline**: Monitor extraction progress at `/dashboard`

---

## Rollback Procedures

Because we use GitOps, rollbacks are as simple as reverting a Git commit!

### Quick Rollback (Revert Last Deployment)

```bash
# 1. Find the commit that updated the kustomization.yaml
git log --oneline k8s/environments/production/kustomization.yaml

# 2. Revert the commit
git revert <commit-hash>

# 3. Push the revert
git push origin main

# 4. ArgoCD will automatically sync the previous image tags
# Monitor at: https://prd.argocd.diocesanvitality.org
```

### Rollback to Specific Version

```bash
# 1. Check deployment history
git log --oneline k8s/environments/production/kustomization.yaml

# 2. View the old kustomization.yaml
git show <old-commit-hash>:k8s/environments/production/kustomization.yaml

# 3. Create a new commit with the old image tags
git checkout <old-commit-hash> -- k8s/environments/production/kustomization.yaml
git commit -m "⏪ Rollback production to <old-commit-hash>"
git push origin main

# 4. ArgoCD will sync automatically
```

### Emergency Manual Rollback (ArgoCD UI)

If Git is unavailable or you need immediate rollback:

1. Go to ArgoCD UI (e.g., https://prd.argocd.diocesanvitality.org)
2. Click on the application
3. Click "History and Rollback"
4. Select the previous successful deployment
5. Click "Rollback"

**⚠️ Warning**: Manual rollbacks create drift between Git and cluster. You must update Git afterward to match!

---

## Rollback Timeline

| Method       | Speed  | Git Updated               | Recommended For           |
| ------------ | ------ | ------------------------- | ------------------------- |
| Git Revert   | ~5 min | ✅ Yes                    | Preferred method          |
| Git Checkout | ~5 min | ✅ Yes                    | Specific version rollback |
| ArgoCD UI    | ~1 min | ❌ No (manual fix needed) | Emergency only            |

---

## Troubleshooting

### Problem: CI/CD workflow doesn't trigger

**Symptoms**: Push to `develop` or `main` doesn't start workflow

**Solutions**:

```bash
# 1. Check if workflow file is valid
# Go to: https://github.com/tomknightatl/diocesan-vitality/actions

# 2. Verify workflow triggers are correct
cat .github/workflows/multi-cluster-ci-cd.yml | grep -A 5 "on:"

# 3. Manually trigger workflow
# Go to Actions tab → Multi-Cluster CI/CD Pipeline → Run workflow
```

---

### Problem: ArgoCD shows "OutOfSync"

**Symptoms**: ArgoCD says cluster is out of sync with Git

**Solutions**:

```bash
# 1. Check what's different
# In ArgoCD UI, click "App Diff" to see differences

# 2. Manual sync (if needed)
# In ArgoCD UI, click "Sync" → "Synchronize"

# 3. Check ArgoCD Application logs
kubectl logs -n argocd deployment/argocd-application-controller
```

---

### Problem: Deployment stuck in "Progressing"

**Symptoms**: Pods keep restarting or won't reach Ready state

**Solutions**:

```bash
# 1. Check pod status
kubectl get pods -n diocesan-vitality-dev  # or staging/production

# 2. Check pod logs
kubectl logs -n diocesan-vitality-dev deployment/backend-deployment --tail=100

# 3. Describe pod to see events
kubectl describe pod -n diocesan-vitality-dev <pod-name>

# 4. Common issues:
# - Image pull errors: Check Docker Hub credentials
# - CrashLoopBackOff: Check application logs for startup errors
# - Resource limits: Check if cluster has enough resources
```

---

### Problem: Images not updating after deployment

**Symptoms**: Old code still running after deployment

**Solutions**:

```bash
# 1. Check kustomization.yaml was actually updated
git show HEAD:k8s/environments/development/kustomization.yaml

# 2. Verify ArgoCD synced the change
# In ArgoCD UI, check "Last Sync" timestamp

# 3. Check pod image tags
kubectl get pods -n diocesan-vitality-dev -o jsonpath='{.items[*].spec.containers[*].image}'

# 4. Force pod restart (if needed)
kubectl rollout restart deployment/backend-deployment -n diocesan-vitality-dev
```

---

### Problem: Production approval not showing

**Symptoms**: Workflow doesn't pause for approval

**Solutions**:

1. Check GitHub environment protection rules are configured
2. Go to: Repository Settings → Environments → production
3. Ensure "Required reviewers" is enabled
4. Add yourself as a required reviewer
5. Re-run the workflow

---

## Quick Reference

### Common Commands

```bash
# Check deployment status
kubectl get applications -n argocd

# View recent ArgoCD syncs
kubectl logs -n argocd deployment/argocd-application-controller --tail=50

# Force ArgoCD sync
# (Do this in ArgoCD UI or via argocd CLI)

# View image tags currently deployed
kubectl get pods -n diocesan-vitality-dev -o jsonpath='{.items[*].spec.containers[*].image}' | tr ' ' '\n'

# Restart deployment
kubectl rollout restart deployment/backend-deployment -n diocesan-vitality-dev
```

### URLs Quick Reference

| Environment | Frontend                            | Backend                              | ArgoCD                                  |
| ----------- | ----------------------------------- | ------------------------------------ | --------------------------------------- |
| Development | https://dev.ui.diocesanvitality.org | https://dev.api.diocesanvitality.org | https://dev.argocd.diocesanvitality.org |
| Staging     | https://stg.ui.diocesanvitality.org | https://stg.api.diocesanvitality.org | https://stg.argocd.diocesanvitality.org |
| Production  | https://diocesanvitality.org        | https://api.diocesanvitality.org     | https://prd.argocd.diocesanvitality.org |

### Branch → Environment Mapping

| Branch          | Environment | Auto-Deploy | Approval |
| --------------- | ----------- | ----------- | -------- |
| `develop`       | Development | ✅ Yes      | ❌ No    |
| `main`          | Staging     | ✅ Yes      | ❌ No    |
| `main` (manual) | Production  | ❌ No       | ✅ Yes   |

---

## Best Practices

### ✅ DO:

- ✅ Test thoroughly in dev before promoting to staging
- ✅ Run smoke tests in staging before deploying to production
- ✅ Use feature branches and pull requests for all changes
- ✅ Write descriptive commit messages
- ✅ Monitor ArgoCD after deployments
- ✅ Check application logs after production deployments
- ✅ Keep Git history clean (squash/rebase when appropriate)

### ❌ DON'T:

- ❌ Push directly to `develop` or `main` (use PRs)
- ❌ Skip testing in dev/staging environments
- ❌ Use `kubectl apply` to bypass GitOps
- ❌ Manually edit resources in the cluster
- ❌ Force push to `main` branch
- ❌ Approve production deployments without verification
- ❌ Make changes during business hours without notification

---

## Related Documentation

- **[CI/CD Pipeline Overview](CI_CD_PIPELINE.md)** - Complete CI/CD pipeline documentation
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Docker and Kubernetes deployment details
- **[ArgoCD Setup](../k8s/argocd/README.md)** - ArgoCD configuration and setup
- **[Local Development](LOCAL_DEVELOPMENT.md)** - Running the application locally
- **[Architecture](ARCHITECTURE.md)** - System architecture overview

---

## Support

**Questions or issues?**

- Check the troubleshooting section above
- Review ArgoCD logs and application logs
- Open an issue on GitHub: https://github.com/tomknightatl/diocesan-vitality/issues
