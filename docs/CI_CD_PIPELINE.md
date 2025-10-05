# 🚀 Multi-Cluster CI/CD Pipeline Guide

This document explains the comprehensive Continuous Integration and Continuous Deployment pipeline for the Diocesan Vitality project with multi-cluster support.

## 📋 Pipeline Overview

The CI/CD pipeline supports three environments with dedicated Kubernetes clusters:

```
📝 Code Push → 🔍 Quality → 🧪 Tests → 🏗️ Build → 🏢 Multi-Cluster Deploy
                                                ├── 🧪 Development (do-nyc2-dv-dev)
                                                ├── 🎭 Staging (do-nyc2-dv-stg)
                                                └── 🚀 Production (ArgoCD)
```

## 🏢 Cluster Architecture

### Development Cluster: `do-nyc2-dv-dev`
- **Purpose**: Feature development and testing
- **Trigger**: Push to `develop` branch
- **Resources**: Minimal (1 replica each)
- **Namespace**: `diocesan-vitality-dev`

### Staging Cluster: `do-nyc2-dv-stg`
- **Purpose**: Pre-production testing and validation
- **Trigger**: Push to `main` branch
- **Resources**: Production-like (2 replicas)
- **Namespace**: `diocesan-vitality-staging`

### Production Cluster: `do-nyc2-dv-prd`
- **Purpose**: Live production environment
- **Trigger**: Manual workflow dispatch
- **Deployment**: Via ArgoCD (GitOps)
- **Namespace**: `diocesan-vitality`

## 🏗️ Pipeline Stages

### Stage 1: Code Quality & Static Analysis
- **Python Code Formatting** (Black)
- **Import Sorting** (isort)
- **Linting** (Flake8)
- **Frontend Linting** (ESLint)
- **Type Checking** (MyPy - warnings allowed)

### Stage 2: Unit & Integration Tests
- **Backend Unit Tests** (pytest with coverage)
- **Frontend Tests** (Jest/Vitest with coverage)
- **Coverage Reports** (uploaded to CodeCov)

### Stage 3: Integration Tests
- **Database Integration Tests** (with PostgreSQL service)
- **Cross-component Integration Tests**
- **Environment Variable Validation**

### Stage 4: Build Staging Images
- **Multi-architecture Docker builds** (ARM64 + AMD64)
- **Staging image tags** with branch and timestamp
- **Push to Docker Hub** with staging tags

### Stage 5: Deploy to Staging
- **Update staging Kubernetes manifests**
- **Deploy to staging namespace**
- **Commit staging deployment to repository**

### Stage 6: Smoke Tests
- **Wait for staging stabilization**
- **Health check endpoints**
- **Basic functionality verification**

### Stage 7: Production Deployment (Main Branch Only)
- **Retag staging images as production**
- **Update production Kubernetes manifests**
- **Deploy to production namespace**
- **Commit production deployment**

## 🔄 Workflow Triggers

### Automatic Triggers
- **Push to `develop`**: Deploy to development cluster (do-nyc2-dv-dev)
- **Push to `main`**: Deploy to staging cluster (do-nyc2-dv-stg)
- **Pull Requests**: Quality checks + tests only (no deployment)

### Manual Triggers
```bash
# Deploy to specific cluster
gh workflow run multi-cluster-ci-cd.yml -f target_cluster=development
gh workflow run multi-cluster-ci-cd.yml -f target_cluster=staging
gh workflow run multi-cluster-ci-cd.yml -f target_cluster=production

# Emergency bypass (use with caution)
gh workflow run multi-cluster-ci-cd.yml -f target_cluster=production -f force_deploy=true

# Using the deployment script
./scripts/deploy-cluster.sh development --build-images
./scripts/deploy-cluster.sh staging
./scripts/deploy-cluster.sh production --force
```

## 🛡️ Safety Gates

### Production Deployment Requirements
- ✅ All quality checks must pass
- ✅ All unit tests must pass
- ✅ All integration tests must pass
- ✅ Staging deployment must succeed
- ✅ Smoke tests must pass
- ✅ Must be on `main` branch
- ✅ Manual approval in production environment

### Environment Protection
The pipeline uses GitHub Environments with protection rules:
- **Staging Environment**: Automatic deployment after tests pass
- **Production Environment**: Requires manual approval + successful staging

## 📊 Branch Strategy

### Main Branches
- **`main`**: Production-ready code, triggers full pipeline
- **`develop`**: Integration branch, deploys to staging only

### Feature Workflow
```bash
# Feature development
git checkout -b feature/new-feature
git push origin feature/new-feature  # Triggers PR pipeline

# Merge to develop for staging testing
git checkout develop
git merge feature/new-feature
git push origin develop  # Deploys to staging

# Merge to main for production
git checkout main
git merge develop
git push origin main  # Deploys to production (with approval)
```

## 🏷️ Image Tagging Strategy

### Staging Images
- `staging-backend-YYYY-MM-DD-HH-mm-ss`
- `staging-frontend-YYYY-MM-DD-HH-mm-ss`
- `staging-pipeline-YYYY-MM-DD-HH-mm-ss`
- `staging-[component]-latest`

### Production Images
- `backend-YYYY-MM-DD-HH-mm-ss`
- `frontend-YYYY-MM-DD-HH-mm-ss`
- `pipeline-YYYY-MM-DD-HH-mm-ss`
- `[component]-latest`

## 🧪 Testing Strategy

### Unit Tests
- **Backend**: pytest with coverage reporting
- **Frontend**: Jest/Vitest with coverage reporting
- **Minimum Coverage**: 70% (configurable)

### Integration Tests
- **Database**: PostgreSQL service container
- **API Integration**: Service-to-service communication
- **Configuration**: Environment variables and secrets

### Smoke Tests
- **Health Endpoints**: Basic connectivity checks
- **Core Functionality**: Critical user journeys
- **Performance**: Response time validation

## 🔧 Setup Requirements

### Repository Secrets
```bash
# Docker Hub credentials
DOCKER_USERNAME: Docker Hub username
DOCKER_PASSWORD: Docker Hub access token

# Cluster configurations (base64 encoded kubeconfigs)
DEV_KUBECONFIG: Base64 encoded kubeconfig for do-nyc2-dv-dev
STAGING_KUBECONFIG: Base64 encoded kubeconfig for do-nyc2-dv-stg
PRODUCTION_KUBECONFIG: Base64 encoded kubeconfig for production cluster

# Environment-specific variables
DEV_DATABASE_URL: Development database connection string
DEV_SUPABASE_URL: Development Supabase URL
DEV_SUPABASE_KEY: Development Supabase key
DEV_GENAI_API_KEY: Development Google AI key

STAGING_DATABASE_URL: Staging database connection string
STAGING_SUPABASE_URL: Staging Supabase URL
STAGING_SUPABASE_KEY: Staging Supabase key
STAGING_GENAI_API_KEY: Staging Google AI key
```

### GitHub Environment Configuration
1. Create "development" environment in GitHub
2. Create "staging" environment in GitHub
3. Create "production" environment in GitHub
4. Configure protection rules (see Environment Setup below)

### Cluster Setup
Ensure each cluster has:
- Proper RBAC permissions for deployments
- Network policies allowing inter-service communication
- Ingress controllers configured (if using external access)
- Monitoring and logging solutions

### Local Development
```bash
# Install development dependencies
pip install black isort flake8 mypy pytest pytest-cov
cd frontend && npm install

# Run quality checks locally
black .
isort .
flake8 .
cd frontend && npm run lint

# Run tests locally
pytest
cd frontend && npm test
```

## 🛠️ Environment Setup

### Creating GitHub Environments

**1. Navigate to Repository Settings**
- Go to `https://github.com/YOUR_USERNAME/diocesan-vitality/settings`
- Click **Environments** in the left sidebar

**2. Create Staging Environment**
- Click **New environment**
- Name: `staging`
- **No protection rules needed** (auto-deploy)

**3. Create Production Environment**
- Click **New environment**
- Name: `production`
- **Protection rules:**
  - ✅ **Required reviewers**: Add yourself and team members
  - ✅ **Wait timer**: 0 minutes (or desired delay)
  - ✅ **Deployment branches**: `main` only

### Environment Variables (Optional)
Add environment-specific variables:
- `STAGING_DATABASE_URL`
- `PRODUCTION_DATABASE_URL`
- `STAGING_API_URL`
- `PRODUCTION_API_URL`

## 📈 Monitoring & Observability

### GitHub Actions Dashboard
- **Workflow Status**: `https://github.com/YOUR_USERNAME/diocesan-vitality/actions`
- **Environment Deployments**: Repository → Environments
- **Coverage Reports**: Integrated with CodeCov

### Useful Commands
```bash
# Watch current workflow
gh run watch

# List recent runs
gh run list

# View specific run
gh run view [RUN_ID]

# Cancel running workflow
gh run cancel [RUN_ID]
```

## 🚨 Troubleshooting

### Common Issues

**Pipeline Fails at Quality Stage**
```bash
# Fix locally before pushing
black .
isort .
flake8 .
cd frontend && npm run lint
```

**Tests Fail**
```bash
# Run tests locally to debug
pytest -v
cd frontend && npm test
```

**Staging Deployment Fails**
- Check Kubernetes manifests syntax
- Verify Docker images were built successfully
- Check staging environment logs

**Production Deployment Blocked**
- Ensure all previous stages passed
- Check if manual approval is pending
- Verify branch is `main`

### Emergency Procedures

**Hotfix Deployment**
```bash
# Create hotfix branch from main
git checkout main
git checkout -b hotfix/critical-fix

# Make minimal fix
git commit -m "hotfix: critical issue"
git push origin hotfix/critical-fix

# Fast-track to main (after code review)
git checkout main
git merge hotfix/critical-fix
git push origin main
```

**Rollback Production**
```bash
# Revert to previous commit
git revert HEAD
git push origin main

# Or force deploy previous version
gh workflow run ci-cd-pipeline.yml -f environment=production -f force_deploy=true
```

## 🎯 Best Practices

### Development Workflow
1. **Feature Branches**: Always create feature branches from `develop`
2. **Pull Requests**: Required for all changes to `main` and `develop`
3. **Code Review**: At least one approval required
4. **Testing**: Write tests for new features
5. **Documentation**: Update docs with changes

### Deployment Best Practices
1. **Staging First**: Always test in staging before production
2. **Small Changes**: Prefer small, frequent deployments
3. **Monitoring**: Watch deployments and be ready to rollback
4. **Communication**: Announce production deployments to team

### Security Best Practices
1. **Secrets Management**: Never commit secrets to repository
2. **Environment Isolation**: Staging and production completely separate
3. **Access Control**: Limit production deployment access
4. **Audit Trail**: All deployments logged and traceable

## 📚 References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments)
- [Docker Multi-platform Builds](https://docs.docker.com/build/building/multi-platform/)
- [pytest Documentation](https://docs.pytest.org/)
- [Jest Testing Framework](https://jestjs.io/)

## 🆘 Getting Help

If you encounter issues with the CI/CD pipeline:
1. Check the GitHub Actions logs for detailed error messages
2. Verify all required secrets and environment variables are set
3. Test components locally before pushing
4. Review this documentation for setup requirements
5. Check if any GitHub environments need manual approval
