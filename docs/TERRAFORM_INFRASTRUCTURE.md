# Terraform Infrastructure Management

This document covers the hybrid Terraform + GitOps approach for managing the Diocesan Vitality infrastructure.

## Architecture Overview

We use a **hybrid approach** that combines the strengths of both Terraform and GitOps:

- **Terraform**: Manages infrastructure layer (clusters, DNS, tunnels)
- **ArgoCD**: Manages application layer (Kubernetes resources, deployments)

```
┌─────────────────────────────────────────────────────────┐
│                 Terraform Layer                         │
│  • DigitalOcean Kubernetes Clusters                    │
│  • Cloudflare Tunnels & DNS Records                    │
│  • Network & Security Configuration                     │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                  ArgoCD Layer                           │
│  • Application Deployments                             │
│  • Kubernetes Resources                                │
│  • GitOps Workflow                                     │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
terraform/
├── modules/
│   ├── do-k8s-cluster/          # DigitalOcean K8s cluster module
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── cloudflare-tunnel/       # Cloudflare tunnel module
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── environments/
│   ├── dev/                     # Development environment
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars.example
│   └── staging/                 # Staging environment
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── terraform.tfvars.example
└── scripts/
    ├── deploy-dev.sh           # Complete dev deployment
    └── deploy-staging.sh       # Complete staging deployment
```

## Prerequisites

### Required Tools
- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.0
- [doctl](https://github.com/digitalocean/doctl#installing-doctl) (DigitalOcean CLI)
- [kubectl](https://kubernetes.io/docs/tasks/tools/) (Kubernetes CLI)
- [jq](https://stedolan.github.io/jq/download/) (JSON processor)

### Required Credentials

Set up environment variables using the `.env` file pattern:

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Configure API credentials in `.env`**:
   ```bash
   # DigitalOcean API Token - Get from: https://cloud.digitalocean.com/account/api/tokens
   DIGITALOCEAN_TOKEN=your-do-token-here
   
   # Cloudflare API Token - Create at: https://dash.cloudflare.com/profile/api-tokens
   # Required permissions: Zone:Read, DNS:Edit, Cloudflare Tunnel:Edit
   CLOUDFLARE_API_TOKEN=your-cf-token-here
   
   # Cloudflare Account ID - Get from dashboard sidebar
   CLOUDFLARE_ACCOUNT_ID=your-account-id-here
   
   # Cloudflare Zone ID - Get from diocesan-vitality.org domain overview
   CLOUDFLARE_ZONE_ID=your-zone-id-here
   ```

3. **Load environment variables**:
   ```bash
   source .env
   # or use: export $(cat .env | xargs)
   ```

### Configuration

All configuration is handled through the `.env` file. The deployment scripts automatically generate the necessary `terraform.tfvars` files from your environment variables.

No additional configuration files need to be created manually.

## Quick Start

### Deploy Development Environment

```bash
# Set up environment
export DIGITALOCEAN_TOKEN="your-token"
export CLOUDFLARE_API_TOKEN="your-token"

# Deploy complete dev environment
./terraform/scripts/deploy-dev.sh
```

This script will:
1. ✅ Check all prerequisites
2. 🏗️ Deploy DigitalOcean cluster with Terraform
3. 🌐 Create Cloudflare tunnel and DNS records
4. ⚙️ Configure kubectl access
5. 🔐 Apply tunnel secrets
6. 🚀 Install ArgoCD
7. 📋 Apply ApplicationSets for GitOps
8. 📊 Display access information

### Deploy Staging Environment

```bash
./terraform/scripts/deploy-staging.sh
```

## Manual Terraform Operations

### Initialize and Plan

```bash
cd terraform/environments/dev
terraform init
terraform plan
```

### Apply Infrastructure

```bash
terraform apply
```

### View Outputs

```bash
terraform output
terraform output -json hostnames
```

### Destroy Infrastructure

```bash
terraform destroy
```

## Environment Configurations

### Development (dev)
- **Cluster**: `dv-dev` (2 nodes, s-2vcpu-2gb)
- **Domains**: 
  - UI: `dev.ui.diocesan-vitality.org`
  - API: `dev.api.diocesan-vitality.org`
  - ArgoCD: `dev.argocd.diocesan-vitality.org`
- **Auto-scaling**: 1-3 nodes

### Staging (staging)
- **Cluster**: `dv-stg` (2 nodes, s-2vcpu-4gb)
- **Domains**:
  - UI: `stg.ui.diocesan-vitality.org`
  - API: `stg.api.diocesan-vitality.org`
  - ArgoCD: `stg.argocd.diocesan-vitality.org`
- **Auto-scaling**: 2-4 nodes

### Production (existing)
- **Cluster**: `dv-prd` (managed manually)
- **Domains**:
  - UI: `ui.diocesan-vitality.org`
  - API: `api.diocesan-vitality.org`
  - ArgoCD: `argocd.diocesan-vitality.org`

## Integration with GitOps

After Terraform creates the infrastructure, ArgoCD manages application deployments:

1. **Infrastructure Layer** (Terraform):
   - Kubernetes clusters
   - Cloudflare tunnels
   - DNS records
   - Network configuration

2. **Application Layer** (ArgoCD):
   - Diocesan Vitality applications
   - Sealed Secrets
   - Cloudflare tunnel configurations
   - Monitoring stack

### ApplicationSet Targeting

ArgoCD ApplicationSets automatically target the correct clusters:

```yaml
# Development deployments → dv-dev cluster
- cluster: dv-dev
  values:
    environment: development
    branch: develop

# Staging deployments → dv-stg cluster  
- cluster: dv-stg
  values:
    environment: staging
    branch: main
```

## State Management

### Current Setup (Local State)
- Dev: `terraform/environments/dev/terraform-dev.tfstate`
- Staging: `terraform/environments/staging/terraform-staging.tfstate`

### Recommended: Remote State (Future)
```hcl
terraform {
  backend "s3" {
    bucket = "diocesan-vitality-terraform-state"
    key    = "environments/dev/terraform.tfstate"
    region = "us-east-1"
  }
}
```

## Security Best Practices

### Secrets Management
1. **Never commit** `.tfvars` files with real values
2. **Use environment variables** for API tokens
3. **Rotate credentials** regularly
4. **Use Sealed Secrets** for Kubernetes secrets

### Access Control
1. **Limit Terraform access** to infrastructure team
2. **Use least-privilege** API tokens
3. **Audit infrastructure changes** via Git history
4. **Monitor resource usage** for unexpected changes

## Troubleshooting

### Common Issues

**Terraform init fails**
```bash
# Clear and reinitialize
rm -rf .terraform .terraform.lock.hcl
terraform init
```

**Cluster access denied**
```bash
# Update kubeconfig
export KUBECONFIG=$(terraform output -raw kubeconfig_path)
kubectl config current-context
```

**DNS records not resolving**
```bash
# Check Cloudflare tunnel status
dig dev.ui.diocesan-vitality.org
```

**ArgoCD applications not syncing**
```bash
# Check ApplicationSet status
kubectl get applicationsets -n argocd
kubectl describe applicationset diocesan-vitality-environments -n argocd
```

### Useful Commands

```bash
# View all Terraform outputs
terraform output -json | jq

# Check cluster nodes
kubectl get nodes -o wide

# View ArgoCD applications
kubectl get applications -n argocd

# Check tunnel connectivity
kubectl logs -n cloudflare-tunnel deployment/cloudflared

# Port forward to ArgoCD
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

## Migration from Scripts

The old script-based approach has been superseded by this Terraform approach:

| Old Approach | New Approach |
|--------------|--------------|
| `k8s/cluster-management/create-dev-cluster.sh` | `terraform/scripts/deploy-dev.sh` |
| `k8s/cluster-management/setup-cloudflare-tunnels.sh` | Terraform cloudflare-tunnel module |
| `k8s/cluster-management/setup-argocd.sh` | Integrated in deployment scripts |

### Benefits of Migration
- ✅ **Declarative infrastructure** with state management
- ✅ **Consistent environments** across dev/staging
- ✅ **Infrastructure as Code** with version control
- ✅ **Drift detection** and remediation
- ✅ **Rollback capabilities** for infrastructure changes
- ✅ **Cost management** through easy destroy/recreate

## Next Steps

1. **Test the development deployment** using `deploy-dev.sh`
2. **Migrate to remote state** for production use
3. **Add production environment** to Terraform
4. **Integrate with CI/CD** for automated deployments
5. **Add monitoring** for infrastructure health

## Related Documentation

- [Development Environments](DEVELOPMENT_ENVIRONMENTS.md) - GitOps workflow
- [Kubernetes Setup](../k8s/README.md) - Application layer configuration
- [Local Development](LOCAL_DEVELOPMENT.md) - Local setup instructions