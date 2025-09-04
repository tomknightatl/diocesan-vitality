# Bitnami Sealed Secrets ApplicationSet Configuration - Multi-Environment

## Repository Structure

The following files are included in your repository:

```
 📁 infra/
    └── 📁 argocd/
        ├── 📁 bitnami-sealed-secrets/
        │   ├── 📄 values-dev.yaml                          ← Development values
        │   ├── 📄 values-stg.yaml                          ← Staging values
        │   ├── 📄 values-prd.yaml                          ← Production values
        │   └── 📄 values-arg.yaml                          ← ArgoCD/Admin values
        ├── 📄 bitnami-sealed-secrets-application-set.yaml  ← Multi-environment ApplicationSet
        ├── 📄 README.md
        └── 📄 CLUSTER-LABELING.md
```

## ApplicationSet Configuration

The ApplicationSet YAML file (`bitnami-sealed-secrets-application-set.yaml`) is configured to deploy Bitnami Sealed Secrets Controller across multiple environments using environment-specific values files.

**Key Features:**
- **Multi-Environment Support**: Deploys to clusters labeled with `environment: dev`, `stg`, `prd`, or `arg`
- **Dynamic Configuration**: Uses environment-specific values files automatically
- **Multi-Source Configuration**: References both Helm chart and Git repository
- **Environment-Specific Values**: Uses `values-{env}.yaml` from your Git repository
- **Auto-Sync**: Automatically syncs changes from Git
- **Pre-configured**: Repository URL already set to `https://github.com/optinosis/optinosis.git`
- **Cluster-Level Component**: Deploys to `kube-system` namespace

## Environment Configuration

### 🔧 **Environment Labels and Values Files**

The ApplicationSet automatically selects the appropriate values file based on the cluster's environment label:

| Environment Label | Values File | Purpose |
|------------------|-------------|---------|
| `dev` | `values-dev.yaml` | Development environment |
| `stg` | `values-stg.yaml` | Staging environment |
| `prd` | `values-prd.yaml` | Production environment |
| `arg` | `values-arg.yaml` | ArgoCD/Administrative environment |

### 🎯 **Cluster Selector Logic**

The ApplicationSet uses a `matchExpressions` selector to target multiple environment types:

```yaml
selector:
  matchLabels:
    argocd.argoproj.io/secret-type: cluster
  matchExpressions:
  - key: environment
    operator: In
    values: ["dev", "stg", "prd", "arg"]
```

## Key Changes from Single Environment Configuration

### 🔄 **Multi-Environment Targeting**
- **Previous**: Only targeted clusters with `environment: development`
- **Current**: Targets clusters with environment labels: `dev`, `stg`, `prd`, `arg`
- **Dynamic**: Automatically uses corresponding values file for each environment

### 📁 **Environment-Specific Values Files**
- **Development**: `values-dev.yaml` - Minimal resources, monitoring disabled
- **Staging**: `values-stg.yaml` - Production-like setup with staging-specific settings
- **Production**: `values-prd.yaml` - Full monitoring, high availability, resource limits
- **ArgoCD/Admin**: `values-arg.yaml` - Administrative cluster configuration

### 🌐 **Scalable Architecture**
- **Single ApplicationSet**: Manages deployments across all environments
- **Consistent Versioning**: Same chart version across environments
- **Environment Isolation**: Each environment gets its own configuration
- **Centralized Management**: All environments managed from one ApplicationSet

## Deployment Instructions

### Step 1: Git clone this repo




### Step 1: Label your cluster(s)
kubectl label secret optinosis-cluster-dev-secret -n argocd environment=prd

# Optionally, label other clusters you want to receive development applications, replacing label with value, e.g., prd, dev, stg, arg, etc.

kubectl label secret kubeflow-cluster-secret -n argocd environment=<label>

# Verify the labels were applied
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=cluster --show-labels
Additional cluster labels can be created with the same pattern, e.g., dev, stg, prd, arg, ta1.




### Step 2: Apply the Multi-Environment ApplicationSet

```bash
# Apply the updated ApplicationSet
kubectl apply -f infra/argocd/bitnami-sealed-secrets-application-set.yaml
```

### Step 4: Verify Cluster Labels

Ensure your clusters are properly labeled for their environments:

```bash
# Verify cluster labels
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=cluster --show-labels

# Label clusters appropriately (examples)
kubectl label secret dev-cluster-secret -n argocd environment=dev
kubectl label secret staging-cluster-secret -n argocd environment=stg
kubectl label secret prod-cluster-secret -n argocd environment=prd
kubectl label secret argocd-cluster-secret -n argocd environment=arg
```

### Step 5: Monitor Multi-Environment Deployment

```bash
# Check if the ApplicationSet was created
kubectl get applicationsets -n argocd | grep bitnami-sealed-secrets

# Check applications generated for all environments
kubectl get applications -n argocd | grep sealed-secrets

# Monitor specific environment deployments
kubectl get application sealed-secrets-dev-cluster -n argocd -o jsonpath='{.status.sync.status}'
kubectl get application sealed-secrets-staging-cluster -n argocd -o jsonpath='{.status.sync.status}'
kubectl get application sealed-secrets-prod-cluster -n argocd -o jsonpath='{.status.sync.status}'
kubectl get application sealed-secrets-argocd-cluster -n argocd -o jsonpath='{.status.sync.status}'
```

### Step 6: Verify Controller Deployment Per Environment

```bash
# Development environment
kubectl get pods -n kube-system -l app.kubernetes.io/name=sealed-secrets --context=dev-cluster

# Staging environment
kubectl get pods -n kube-system -l app.kubernetes.io/name=sealed-secrets --context=staging-cluster

# Production environment
kubectl get pods -n kube-system -l app.kubernetes.io/name=sealed-secrets --context=prod-cluster

# ArgoCD environment
kubectl get pods -n kube-system -l app.kubernetes.io/name=sealed-secrets --context=argocd-cluster
```

## Environment-Specific Usage

### Development Environment
```bash
# Create sealed secrets for development
echo -n dev-password | kubectl create secret generic dev-secret \
  --dry-run=client \
  --from-file=password=/dev/stdin \
  -o yaml | kubeseal --context=dev-cluster -o yaml > dev-sealed-secret.yaml
```

### Staging Environment
```bash
# Create sealed secrets for staging
echo -n staging-password | kubectl create secret generic staging-secret \
  --dry-run=client \
  --from-file=password=/dev/stdin \
  -o yaml | kubeseal --context=staging-cluster -o yaml > staging-sealed-secret.yaml
```

### Production Environment
```bash
# Create sealed secrets for production
echo -n prod-password | kubectl create secret generic prod-secret \
  --dry-run=client \
  --from-file=password=/dev/stdin \
  -o yaml | kubeseal --context=prod-cluster -o yaml > prod-sealed-secret.yaml
```

## Environment-Specific Configuration Management

### Updating Environment Configurations

To update configuration for a specific environment:

1. **Edit environment values file**: Modify `infra/argocd/bitnami-sealed-secrets/values-{env}.yaml`
2. **Commit changes**: `git add` and `git commit` the changes
3. **Push to repository**: `git push origin main`
4. **ArgoCD auto-sync**: ApplicationSet will automatically detect and apply changes to the specific environment

### Environment Promotion Strategy

**Configuration Promotion Flow:**
1. **Development** (`values-dev.yaml`) - Initial testing and development
2. **Staging** (`values-stg.yaml`) - Pre-production validation
3. **Production** (`values-prd.yaml`) - Live environment deployment
4. **ArgoCD** (`values-arg.yaml`) - Administrative and management cluster

### Cross-Environment Consistency

**Version Management:**
- All environments use the same chart version (`2.17.0`)
- Environment-specific configurations in separate values files
- Consistent controller naming across environments
- Unified RBAC and security model

## Multi-Environment Benefits

### 🔒 **Security Isolation**
- **Environment-Specific Keys**: Each cluster has its own sealed secrets encryption keys
- **Namespace Scoping**: Secrets encrypted for specific environment contexts
- **Access Control**: Environment-specific RBAC configurations

### 🚀 **Deployment Flexibility**
- **Selective Deployment**: Deploy to specific environments by cluster labeling
- **Independent Scaling**: Each environment can have different resource requirements
- **Environment Parity**: Consistent deployment process across all environments

### 🔍 **Monitoring and Observability**
- **Environment Tags**: All resources tagged with environment labels
- **Per-Environment Monitoring**: Staging and production have monitoring enabled
- **Centralized Management**: Single ApplicationSet manages all environments

### 🛠️ **Operational Excellence**
- **GitOps Compliance**: All configuration changes tracked in Git
- **Automated Deployment**: No manual intervention required
- **Rollback Capability**: Easy rollback through Git history
- **Audit Trail**: Full deployment history and configuration changes

## Troubleshooting Multi-Environment Deployments

### Environment-Specific Issues

**Check Environment Applications:**
```bash
# List all sealed-secrets applications
kubectl get applications -n argocd -l app.kubernetes.io/name=sealed-secrets

# Check specific environment application status
kubectl describe application sealed-secrets-{cluster-name} -n argocd

# View environment-specific logs
kubectl logs deployment/sealed-secrets-controller -n kube-system --context={environment-context}
```

**Values File Issues:**
```bash
# Verify values file exists for environment
ls -la infra/argocd/bitnami-sealed-secrets/values-*.yaml

# Test values file syntax
helm template sealed-secrets bitnami-labs/sealed-secrets \
  --values infra/argocd/bitnami-sealed-secrets/values-{env}.yaml \
  --version 2.17.0
```

**Cluster Labeling Issues:**
```bash
# Check cluster labels
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=cluster \
  -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.metadata.labels.environment}{"\n"}{end}'

# Fix missing environment labels
kubectl label secret {cluster-secret-name} -n argocd environment={env}
```

### Environment Migration

**Adding New Environment:**
1. Create new values file: `values-{new-env}.yaml`
2. Label target cluster with `environment={new-env}`
3. Update ApplicationSet selector if needed
4. Monitor application creation and sync

**Removing Environment:**
1. Remove environment label from cluster
2. ApplicationSet will automatically remove the application
3. Manual cleanup may be required for resources

## Expected Results Per Environment

After successful multi-environment deployment:

### Development Environment
- ✅ Minimal resource usage
- ✅ Monitoring disabled
- ✅ Fast deployment and testing

### Staging Environment
- ✅ Production-like configuration
- ✅ Basic monitoring enabled
- ✅ Pre-production validation

### Production Environment
- ✅ High availability setup
- ✅ Full monitoring and alerting
- ✅ Enhanced security configuration
- ✅ Resource limits and requests

### ArgoCD Environment
- ✅ Administrative oversight
- ✅ Monitoring for operational visibility
- ✅ Conservative resource allocation

## Security Benefits Across Environments

### Environment Isolation
1. **Separate Encryption Keys**: Each environment has unique sealed secrets keys
2. **Cross-Environment Protection**: Secrets from one environment cannot be used in another
3. **Environment-Specific RBAC**: Different access controls per environment
4. **Audit Separation**: Clear audit trails per environment

### Compliance and Governance
- **Change Tracking**: All configuration changes tracked in Git
- **Environment Promotion**: Controlled promotion process through environments
- **Access Control**: Environment-specific access controls
- **Security Scanning**: Environment-specific security configurations

This multi-environment setup provides a robust, scalable, and secure foundation for managing sealed secrets across your entire infrastructure while maintaining environment isolation and operational excellence.