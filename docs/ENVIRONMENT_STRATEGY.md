# Environment Strategy Guide

This guide explains the branch-based environment promotion strategy for the Diocesan Vitality project.

## Overview

The project uses a **branch-based environment strategy** to ensure safe deployments through multiple stages:

- **Development** (`develop` branch) → **Dev Cluster**
- **Staging** (`staging` branch) → **Staging Cluster**
- **Production** (`main` branch) → **Production Cluster**

## Environment Flow

```
develop branch  →  Dev Cluster     (testing & development)
     ↓
staging branch  →  Staging Cluster (pre-production validation)
     ↓
main branch     →  Production      (live system)
```

## Branch Strategy

### Development Branch (`develop`)
- **Purpose**: Active development and testing
- **Deployments**: Automatic deployment to dev cluster
- **Image Tags**: `dev-backend-<timestamp>`, `dev-frontend-<timestamp>`, `dev-pipeline-<timestamp>`
- **Testing**: Full CI/CD pipeline with GitHub Actions runners

### Staging Branch (`staging`)
- **Purpose**: Pre-production validation and user acceptance testing
- **Deployments**: Automatic deployment to staging cluster
- **Image Tags**: `staging-backend-<timestamp>`, `staging-frontend-<timestamp>`, `staging-pipeline-<timestamp>`
- **Testing**: Full integration tests and smoke tests

### Main Branch (`main`)
- **Purpose**: Production releases
- **Deployments**: Semantic versioning with automated releases
- **Image Tags**: `backend-1.2.3`, `frontend-1.2.3`, `pipeline-1.2.3` (semantic versions)
- **Testing**: Complete CI/CD pipeline + semantic release validation

## Safe Testing Workflow

### 1. Development Testing
```bash
# Make changes and commit to develop branch
git checkout develop
git add .
git commit -m "feat: add new feature"
git push origin develop
```

**Result**:
- Triggers CI/CD pipeline
- Builds dev-tagged images
- Deploys to dev cluster only
- Runs all tests in dev environment

### 2. Staging Validation
```bash
# Promote develop to staging when ready
git checkout staging
git merge develop
git push origin staging
```

**Result**:
- Triggers staging deployment
- Builds staging-tagged images
- Deploys to staging cluster
- Runs integration and smoke tests

### 3. Production Release
```bash
# Create semantic release commit on main
git checkout main
git merge staging
git commit -m "feat: release new feature to production"
git push origin main
```

**Result**:
- Triggers semantic release workflow
- Creates new semantic version (e.g., 1.2.3)
- Builds production images with semantic tags
- Updates Kubernetes manifests
- Deploys to production cluster via ArgoCD

## CI/CD Pipeline Behavior

### Environment Detection
The pipeline automatically detects the target environment based on the branch:

```yaml
case "$BRANCH" in
  "develop")  ENV="dev" ;;
  "staging")  ENV="staging" ;;
  "main")     ENV="prod" ;;
esac
```

### Image Tagging Strategy

**Development/Staging** (timestamp-based):
```
tomatl/diocesan-vitality:dev-backend-2024-01-15-14-30-25
tomatl/diocesan-vitality:staging-frontend-2024-01-15-14-30-25
```

**Production** (semantic versioning):
```
tomatl/diocesan-vitality:backend-1.2.3
tomatl/diocesan-vitality:frontend-1.2.3
```

## ArgoCD Application Configuration

### Development
- **ApplicationSet**: `diocesan-vitality-dev`
- **Target Branch**: `develop`
- **Namespace**: `diocesan-vitality-dev`
- **Cluster Label**: `environment: dev`

### Staging
- **ApplicationSet**: `diocesan-vitality-stg`
- **Target Branch**: `staging`
- **Namespace**: `diocesan-vitality-stg`
- **Cluster Label**: `environment: stg`

### Production
- **ApplicationSet**: `diocesan-vitality-prd`
- **Target Branch**: `main`
- **Namespace**: `diocesan-vitality-production`
- **Cluster Label**: `environment: prd`

## Environment-Specific Configurations

### Kubernetes Manifests
Each environment has its own Kustomize overlay:

```
k8s/environments/
├── development/
│   ├── namespace.yaml
│   ├── development-patches.yaml
│   └── kustomization.yaml
├── staging/
│   ├── namespace.yaml
│   ├── staging-patches.yaml
│   └── kustomization.yaml
└── production/
    ├── namespace.yaml
    ├── production-patches.yaml
    └── kustomization.yaml
```

### Docker Compose Testing
Each environment has its own Docker Compose file for local testing:

```
docker-compose.dev.yml     # Development testing
docker-compose.staging.yml # Staging validation
```

## Environment Variables

### Development
```yaml
ENVIRONMENT: development
DATABASE_URL: ${DEV_DATABASE_URL}
SUPABASE_URL: ${DEV_SUPABASE_URL}
SUPABASE_KEY: ${DEV_SUPABASE_KEY}
```

### Staging
```yaml
ENVIRONMENT: staging
DATABASE_URL: ${STAGING_DATABASE_URL}
SUPABASE_URL: ${STAGING_SUPABASE_URL}
SUPABASE_KEY: ${STAGING_SUPABASE_KEY}
```

### Production
```yaml
ENVIRONMENT: production
DATABASE_URL: ${PRODUCTION_DATABASE_URL}
SUPABASE_URL: ${PRODUCTION_SUPABASE_URL}
SUPABASE_KEY: ${PRODUCTION_SUPABASE_KEY}
```

## Resource Allocation

### Development (Minimal)
```yaml
replicas:
  backend: 1
  frontend: 1
  pipeline: 1

resources:
  requests: 128Mi/100m
  limits: 256Mi/200m
```

### Staging (Moderate)
```yaml
replicas:
  backend: 2
  frontend: 2
  pipeline: 1

resources:
  requests: 256Mi/200m
  limits: 512Mi/500m
```

### Production (High Availability)
```yaml
replicas:
  backend: 3
  frontend: 3
  pipeline: 2

resources:
  requests: 512Mi/300m
  limits: 1Gi/1000m
```

## Deployment Commands

### Local Environment Testing
```bash
# Test development environment
docker-compose -f docker-compose.dev.yml up -d

# Test staging environment
docker-compose -f docker-compose.staging.yml up -d
```

### Manual Deployments
```bash
# Deploy to specific environment
kubectl apply -k k8s/environments/development
kubectl apply -k k8s/environments/staging
kubectl apply -k k8s/environments/production
```

### ArgoCD Sync
```bash
# Sync specific environment
argocd app sync diocesan-vitality-dev
argocd app sync diocesan-vitality-stg
argocd app sync diocesan-vitality-prd
```

## Monitoring and Verification

### Health Checks
Each environment provides health endpoints:

- **Dev**: `https://dev-api.diocesan-vitality.com/health`
- **Staging**: `https://staging-api.diocesan-vitality.com/health`
- **Production**: `https://api.diocesan-vitality.com/health`

### Dashboard Access
- **Dev**: `https://dev.diocesan-vitality.com/dashboard`
- **Staging**: `https://staging.diocesan-vitality.com/dashboard`
- **Production**: `https://diocesan-vitality.com/dashboard`

## Troubleshooting

### Common Issues

**1. Pipeline not triggering for branch**
```bash
# Check if branch is included in workflow triggers
grep -A 5 "branches:" .github/workflows/ci-cd-pipeline.yml
```

**2. ArgoCD not syncing**
```bash
# Check ArgoCD application status
kubectl get applications -n argocd
argocd app get diocesan-vitality-dev
```

**3. Environment variables not updating**
```bash
# Verify environment-specific patches
kubectl get deployment backend-deployment -o yaml | grep -A 10 env
```

### Log Access
```bash
# View deployment logs by environment
kubectl logs -n diocesan-vitality-dev deployment/backend-deployment
kubectl logs -n diocesan-vitality-stg deployment/backend-deployment
kubectl logs -n diocesan-vitality-production deployment/backend-deployment
```

## Best Practices

### 1. Feature Development
- Always start with `develop` branch
- Test thoroughly in dev environment
- Only promote to staging when dev testing is complete

### 2. Hotfixes
- Create hotfix branch from `main`
- Test in dev, validate in staging
- Merge to `main` for production release

### 3. Release Management
- Use conventional commits for automatic versioning
- Include comprehensive commit messages
- Tag releases with semantic versions

### 4. Environment Isolation
- Keep environment-specific secrets separate
- Use different databases for each environment
- Monitor resource usage per environment

## Security Considerations

### 1. Secret Management
- Use Kubernetes secrets for sensitive data
- Rotate credentials regularly
- Separate secrets by environment

### 2. Network Security
- Implement network policies between environments
- Use TLS/SSL for all communications
- Restrict database access by environment

### 3. Access Control
- Implement RBAC for each environment
- Limit production access to authorized personnel
- Audit all production deployments

## Related Documentation

- [KUBERNETES_DEPLOYMENT.md](./KUBERNETES_DEPLOYMENT.md) - Detailed Kubernetes setup
- [COMMANDS.md](./COMMANDS.md) - Development commands
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview