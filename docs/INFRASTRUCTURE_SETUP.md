# Infrastructure Setup Guide

This guide provides the exact scripts to set up the Diocesan Vitality infrastructure in four sequential steps.

## Prerequisites

Before running these steps, ensure you have:

1. **Required Environment Variables** in `.env`:
   ```bash
   DIGITALOCEAN_TOKEN=<your_do_token>
   CLOUDFLARE_API_TOKEN=<your_cf_token>
   CLOUDFLARE_ACCOUNT_ID=<your_cf_account_id>
   CLOUDFLARE_ZONE_ID=<your_cf_zone_id>
   ```

2. **Required Tools Installed**:
   - `terraform` (v1.0+)
   - `kubectl` (v1.21+)
   - `doctl` (DigitalOcean CLI)

3. **Authentication Setup**:
   ```bash
   # Configure DigitalOcean CLI
   doctl auth init --access-token $DIGITALOCEAN_TOKEN

   # Verify access
   doctl account get
   ```

## Step 1: Create Cluster and kubectl Context

**Purpose**: Create DigitalOcean Kubernetes cluster and add kubectl context

**Script**:
```bash
#!/bin/bash
set -e

echo "🚀 Step 1: Creating cluster and kubectl context..."

# Navigate to dev environment
cd terraform/environments/dev

# Export required environment variables
export DIGITALOCEAN_TOKEN=$(grep DIGITALOCEAN_TOKEN ../../../.env | cut -d'=' -f2)

# Initialize and apply Terraform for cluster only
terraform init
terraform apply -target=module.k8s_cluster -auto-approve

# Extract cluster info
CLUSTER_NAME=$(terraform output -json cluster_info | jq -r '.name')
CLUSTER_ID=$(terraform output -json cluster_info | jq -r '.id')

echo "✅ Cluster created: $CLUSTER_NAME (ID: $CLUSTER_ID)"

# Add kubectl context (Terraform should do this, but verify/add manually if needed)
doctl kubernetes cluster kubeconfig save $CLUSTER_NAME

# Rename context to standard format
kubectl config rename-context do-nyc2-$CLUSTER_NAME do-nyc2-$CLUSTER_NAME 2>/dev/null || true

# Verify cluster connectivity
echo "🔍 Verifying cluster connectivity..."
kubectl config use-context do-nyc2-$CLUSTER_NAME
kubectl get nodes

echo "✅ Step 1 Complete: Cluster created and kubectl context configured"
echo "   Context: do-nyc2-$CLUSTER_NAME"
```

**Manual Commands**:
```bash
cd terraform/environments/dev
export DIGITALOCEAN_TOKEN=<your_token>
terraform init
terraform apply -target=module.k8s_cluster -auto-approve
doctl kubernetes cluster kubeconfig save dv-dev
kubectl config use-context do-nyc2-dv-dev
kubectl get nodes
```

## Step 2: Install ArgoCD and Configure Repository

**Purpose**: Install ArgoCD and configure it to access the git repository

**Script**:
```bash
#!/bin/bash
set -e

echo "🚀 Step 2: Installing ArgoCD and configuring repository..."

# Ensure we're using the correct kubectl context
kubectl config use-context do-nyc2-dv-dev

# Create ArgoCD namespace
kubectl create namespace argocd

# Install ArgoCD
echo "📦 Installing ArgoCD..."
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD pods to be ready
echo "⏳ Waiting for ArgoCD pods to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s

# Configure repository access
echo "🔧 Configuring repository access..."
kubectl patch configmap argocd-cm -n argocd --patch '{"data":{"repositories":"- url: https://github.com/t-k-/diocesan-vitality.git"}}'

# Get ArgoCD admin password
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

echo "✅ Step 2 Complete: ArgoCD installed and configured"
echo "   ArgoCD Admin Password: $ARGOCD_PASSWORD"
echo "   Access via port-forward: kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "   Then visit: https://localhost:8080 (admin/$ARGOCD_PASSWORD)"
```

**Manual Commands**:
```bash
kubectl config use-context do-nyc2-dv-dev
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s
kubectl patch configmap argocd-cm -n argocd --patch '{"data":{"repositories":"- url: https://github.com/t-k-/diocesan-vitality.git"}}'
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo
```

## Step 3: Install ArgoCD ApplicationSets

**Purpose**: Deploy ApplicationSets that manage sealed secrets, cloudflare tunnel, and diocesan vitality applications

**Script**:
```bash
#!/bin/bash
set -e

echo "🚀 Step 3: Installing ArgoCD ApplicationSets..."

# Ensure we're using the correct kubectl context
kubectl config use-context do-nyc2-dv-dev

# Navigate to repository root
cd ../../../

# Apply ApplicationSets
echo "📦 Installing Sealed Secrets ApplicationSet..."
kubectl apply -f k8s/argocd/sealed-secrets-multi-env-applicationset.yaml

echo "📦 Installing Cloudflare Tunnel ApplicationSet..."
kubectl apply -f k8s/argocd/cloudflare-tunnel-multi-env-applicationset.yaml

echo "📦 Installing Diocesan Vitality Environments ApplicationSet..."
kubectl apply -f k8s/argocd/diocesan-vitality-environments-applicationset.yaml

# Wait a moment for ApplicationSets to create Applications
sleep 10

# Check ApplicationSet status
echo "🔍 Checking ApplicationSets..."
kubectl get applicationsets -n argocd

echo "🔍 Checking created Applications..."
kubectl get applications -n argocd

echo "✅ Step 3 Complete: ApplicationSets installed"
echo "   Note: Applications may take time to sync. Check ArgoCD UI for detailed status."
```

**Manual Commands**:
```bash
kubectl config use-context do-nyc2-dv-dev
kubectl apply -f k8s/argocd/sealed-secrets-multi-env-applicationset.yaml
kubectl apply -f k8s/argocd/cloudflare-tunnel-multi-env-applicationset.yaml
kubectl apply -f k8s/argocd/diocesan-vitality-environments-applicationset.yaml
kubectl get applicationsets -n argocd
kubectl get applications -n argocd
```

## Step 4: Create Cloudflare Tunnel and DNS Records

**Purpose**: Create Cloudflare tunnel with public hostnames and DNS records

**Script**:
```bash
#!/bin/bash
set -e

echo "🚀 Step 4: Creating Cloudflare tunnel and DNS records..."

# Navigate to dev environment
cd terraform/environments/dev

# Export required environment variables
export CLOUDFLARE_API_TOKEN=$(grep CLOUDFLARE_API_TOKEN ../../../.env | cut -d'=' -f2)

# Apply Cloudflare tunnel configuration
echo "📦 Creating Cloudflare tunnel..."
terraform apply -target=module.cloudflare_tunnel -auto-approve

# Extract tunnel info
TUNNEL_NAME=$(terraform output -json tunnel_info | jq -r '.name')
TUNNEL_ID=$(terraform output -json tunnel_info | jq -r '.id')
TUNNEL_CNAME=$(terraform output -json tunnel_info | jq -r '.cname')

echo "✅ Cloudflare tunnel created:"
echo "   Name: $TUNNEL_NAME"
echo "   ID: $TUNNEL_ID"
echo "   CNAME: $TUNNEL_CNAME"

# Show hostnames
echo "🌐 DNS Records created:"
terraform output -json hostnames | jq -r 'to_entries[] | "   \(.key): \(.value)"'

echo "✅ Step 4 Complete: Cloudflare tunnel and DNS records created"
echo ""
echo "🔍 Next Steps:"
echo "   1. Check tunnel health in Cloudflare dashboard"
echo "   2. Deploy cloudflared daemon to cluster"
echo "   3. Test external access to services"
```

**Manual Commands**:
```bash
cd terraform/environments/dev
export CLOUDFLARE_API_TOKEN=<your_token>
terraform apply -target=module.cloudflare_tunnel -auto-approve
terraform output tunnel_info
terraform output hostnames
```

## Complete Setup Script

**Run all steps sequentially**:
```bash
#!/bin/bash
set -e

echo "🚀 Starting complete infrastructure setup..."

# Step 1: Create cluster
./scripts/01-create-cluster.sh

# Step 2: Install ArgoCD
./scripts/02-install-argocd.sh

# Step 3: Install ApplicationSets
./scripts/03-install-applicationsets.sh

# Step 4: Create Cloudflare tunnel
./scripts/04-create-tunnel.sh

echo "🎉 Infrastructure setup complete!"
echo ""
echo "📋 Summary:"
echo "   ✅ Cluster: do-nyc2-dv-dev"
echo "   ✅ ArgoCD: Installed and configured"
echo "   ✅ ApplicationSets: Deployed"
echo "   ✅ Cloudflare Tunnel: Created with DNS records"
echo ""
echo "🔗 Access Points:"
echo "   • ArgoCD: kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "   • Dev UI: https://dev.ui.diocesanvitality.org (after tunnel setup)"
echo "   • Dev API: https://dev.api.diocesanvitality.org (after tunnel setup)"
```

## Cleanup Scripts

**Destroy infrastructure** (reverse order):
```bash
#!/bin/bash
set -e

echo "🧹 Starting infrastructure cleanup..."

cd terraform/environments/dev

# Step 4: Destroy Cloudflare tunnel
export CLOUDFLARE_API_TOKEN=$(grep CLOUDFLARE_API_TOKEN ../../../.env | cut -d'=' -f2)
terraform destroy -target=module.cloudflare_tunnel -auto-approve

# Step 3: Delete ApplicationSets
kubectl delete -f ../../../k8s/argocd/ || true

# Step 2: Delete ArgoCD
kubectl delete namespace argocd || true

# Step 1: Destroy cluster
export DIGITALOCEAN_TOKEN=$(grep DIGITALOCEAN_TOKEN ../../../.env | cut -d'=' -f2)
terraform destroy -target=module.k8s_cluster -auto-approve

echo "✅ Infrastructure cleanup complete"
```

## Troubleshooting

### Common Issues

**1. Kubectl context not found**:
```bash
doctl kubernetes cluster kubeconfig save dv-dev
kubectl config get-contexts
```

**2. ArgoCD pods not ready**:
```bash
kubectl get pods -n argocd
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server
```

**3. ApplicationSets not syncing**:
```bash
kubectl get applications -n argocd
kubectl describe application <app-name> -n argocd
```

**4. Terraform state issues**:
```bash
cd terraform/environments/dev
terraform refresh
terraform plan
```

### Health Checks

**Verify cluster health**:
```bash
kubectl get nodes
kubectl get pods --all-namespaces
```

**Verify ArgoCD health**:
```bash
kubectl get pods -n argocd
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
curl -k https://localhost:8080
```

**Verify Cloudflare tunnel**:
```bash
cd terraform/environments/dev
terraform output tunnel_info
# Check Cloudflare dashboard for tunnel status
```
