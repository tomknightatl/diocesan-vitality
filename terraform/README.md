# Terraform Infrastructure

This directory contains Terraform configurations for managing the Diocesan Vitality infrastructure using a hybrid Terraform + GitOps approach.

## Quick Start

```bash
# Deploy development environment
./scripts/deploy-dev.sh

# Deploy staging environment  
./scripts/deploy-staging.sh
```

## Directory Structure

```
terraform/
├── modules/                     # Reusable Terraform modules
│   ├── do-k8s-cluster/         # DigitalOcean Kubernetes cluster
│   └── cloudflare-tunnel/      # Cloudflare tunnel + DNS
├── environments/               # Environment-specific configurations
│   ├── dev/                   # Development environment
│   └── staging/               # Staging environment
└── scripts/                   # Deployment automation scripts
    ├── deploy-dev.sh          # Complete dev deployment
    └── deploy-staging.sh      # Complete staging deployment
```

## What This Manages

### Infrastructure Layer (Terraform)
- ✅ DigitalOcean Kubernetes clusters
- ✅ Cloudflare tunnels and DNS records
- ✅ Network configuration
- ✅ Security settings

### Application Layer (ArgoCD)
- ✅ Kubernetes resources
- ✅ Application deployments
- ✅ GitOps workflow
- ✅ Secret management

## Prerequisites

1. **Install Tools**:
   - [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.0
   - [doctl](https://github.com/digitalocean/doctl) (DigitalOcean CLI)
   - [kubectl](https://kubernetes.io/docs/tasks/tools/) (Kubernetes CLI)

2. **Set Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API tokens
   source .env
   ```

3. **Configure Variables**:
   ```bash
   # Copy and edit configuration files
   cp environments/dev/terraform.tfvars.example environments/dev/terraform.tfvars
   cp environments/staging/terraform.tfvars.example environments/staging/terraform.tfvars
   ```

## Usage Examples

### Deploy Complete Environment
```bash
# Development
./scripts/deploy-dev.sh

# Staging
./scripts/deploy-staging.sh
```

### Manual Terraform Operations
```bash
# Navigate to environment
cd environments/dev

# Initialize and plan
terraform init
terraform plan

# Apply changes
terraform apply

# View outputs
terraform output
```

### Access Services
```bash
# Get kubeconfig
export KUBECONFIG=$(terraform output -raw kubeconfig_path)

# Access ArgoCD
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Visit: https://localhost:8080

# Get ArgoCD password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

## Environment Details

| Environment | Cluster | Nodes | URLs |
|-------------|---------|--------|------|
| **Development** | `dv-dev` | 2 nodes (s-2vcpu-2gb) | `dev.*.diocesan-vitality.org` |
| **Staging** | `dv-stg` | 2 nodes (s-2vcpu-4gb) | `stg.*.diocesan-vitality.org` |
| **Production** | `dv-prd` | Manual management | `*.diocesan-vitality.org` |

## CI/CD Integration

GitHub Actions automatically:
- ✅ Validates Terraform configurations on PR
- ✅ Plans infrastructure changes
- ✅ Applies changes on merge (with approval)
- ✅ Manages state and rollbacks

See `.github/workflows/terraform-infrastructure.yml` for the complete CI/CD pipeline.

## Security

- 🔐 **API tokens** stored as GitHub Secrets
- 🔐 **State files** managed securely (local for now, remote recommended)
- 🔐 **Credentials** never committed to repository
- 🔐 **Access control** via environment protection rules

## Troubleshooting

**Cluster access issues**:
```bash
export KUBECONFIG=$(terraform output -raw kubeconfig_path)
kubectl get nodes
```

**DNS not resolving**:
```bash
dig dev.ui.diocesan-vitality.org
```

**ArgoCD not accessible**:
```bash
kubectl get pods -n argocd
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

## Migration Path

This Terraform approach replaces the previous script-based infrastructure:

| Old | New |
|-----|-----|
| `k8s/cluster-management/create-dev-cluster.sh` | `terraform/scripts/deploy-dev.sh` |
| `k8s/cluster-management/setup-cloudflare-tunnels.sh` | `terraform/modules/cloudflare-tunnel/` |
| Manual cluster management | Declarative infrastructure as code |

## Documentation

For complete documentation, see:
- **[Terraform Infrastructure Guide](../docs/TERRAFORM_INFRASTRUCTURE.md)** - Comprehensive documentation
- **[Development Environments](../docs/DEVELOPMENT_ENVIRONMENTS.md)** - GitOps workflow
- **[ArgoCD Setup](../k8s/argocd/README.md)** - Application management