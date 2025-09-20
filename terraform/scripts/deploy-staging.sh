#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGING_DIR="$SCRIPT_DIR/../environments/staging"

echo "=== Deploying Staging Infrastructure with Terraform ==="
echo

check_prerequisites() {
    echo "Checking prerequisites..."

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        echo "❌ Terraform is not installed"
        echo "   Install from: https://developer.hashicorp.com/terraform/downloads"
        exit 1
    fi
    echo "✅ Terraform is available"

    # Check doctl
    if ! command -v doctl &> /dev/null; then
        echo "❌ doctl is not installed"
        echo "   Install from: https://github.com/digitalocean/doctl#installing-doctl"
        exit 1
    fi
    echo "✅ doctl is available"

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        echo "❌ kubectl is not installed"
        echo "   Install from: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    echo "✅ kubectl is available"

    # Check environment variables
    if [[ -z "${DIGITALOCEAN_TOKEN:-}" ]]; then
        echo "❌ DIGITALOCEAN_TOKEN environment variable is required"
        echo "   1. Copy environment template: cp .env.example .env"
        echo "   2. Edit .env with your DigitalOcean token from: https://cloud.digitalocean.com/account/api/tokens"
        echo "   3. Load variables: source .env"
        exit 1
    fi
    echo "✅ DigitalOcean token is configured"

    if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
        echo "❌ CLOUDFLARE_API_TOKEN environment variable is required"
        echo "   1. Copy environment template: cp .env.example .env"
        echo "   2. Edit .env with your Cloudflare token from: https://dash.cloudflare.com/profile/api-tokens"
        echo "   3. Required permissions: Zone:Read, DNS:Edit, Cloudflare Tunnel:Edit"
        echo "   4. Load variables: source .env"
        exit 1
    fi
    echo "✅ Cloudflare API token is configured"

    # Check Cloudflare configuration
    if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
        echo "❌ CLOUDFLARE_ACCOUNT_ID environment variable is required"
        echo "   1. Edit .env with your Cloudflare account ID from dashboard sidebar"
        echo "   2. Load variables: source .env"
        exit 1
    fi

    if [[ -z "${CLOUDFLARE_ZONE_ID:-}" ]]; then
        echo "❌ CLOUDFLARE_ZONE_ID environment variable is required"
        echo "   1. Edit .env with your zone ID from diocesan-vitality.org domain overview"
        echo "   2. Load variables: source .env"
        exit 1
    fi
    echo "✅ Cloudflare configuration is set"

    echo
}

generate_tfvars() {
    echo "Generating terraform.tfvars from environment variables..."
    cd "$STAGING_DIR"

    cat > terraform.tfvars << EOF
# Auto-generated from environment variables
kubernetes_version = "${KUBERNETES_VERSION:-1.31.9-do.3}"
cloudflare_account_id = "${CLOUDFLARE_ACCOUNT_ID}"
cloudflare_zone_id = "${CLOUDFLARE_ZONE_ID}"
EOF
    echo "✅ terraform.tfvars generated"
}

deploy_infrastructure() {
    echo "=== Deploying Infrastructure ==="
    cd "$STAGING_DIR"

    echo "Initializing Terraform..."
    terraform init

    echo "Planning infrastructure changes..."
    terraform plan -out=tfplan

    echo "Applying infrastructure changes..."
    terraform apply tfplan

    echo "✅ Infrastructure deployment complete"
    echo
}

setup_kubernetes() {
    echo "=== Setting up Kubernetes Access ==="
    cd "$STAGING_DIR"

    # Get kubeconfig path from Terraform output
    KUBECONFIG_PATH=$(terraform output -raw kubeconfig_path)

    if [[ -f "$KUBECONFIG_PATH" ]]; then
        echo "Setting up kubectl access..."
        export KUBECONFIG="$KUBECONFIG_PATH"

        # Test cluster access
        if kubectl get nodes &>/dev/null; then
            echo "✅ Cluster access confirmed"
            kubectl get nodes
        else
            echo "❌ Failed to access cluster"
            exit 1
        fi
    else
        echo "❌ Kubeconfig file not found at: $KUBECONFIG_PATH"
        exit 1
    fi

    echo
}

apply_tunnel_secrets() {
    echo "=== Applying Cloudflare Tunnel Secrets ==="
    cd "$STAGING_DIR"

    # Get secret file path from Terraform output
    SECRET_FILE=$(terraform output -raw cloudflare_tunnel.k8s_secret_file 2>/dev/null || echo "k8s-secrets/cloudflare-tunnel-staging.yaml")

    if [[ -f "$SECRET_FILE" ]]; then
        echo "Creating cloudflare-tunnel namespace..."
        kubectl create namespace cloudflare-tunnel --dry-run=client -o yaml | kubectl apply -f -

        echo "Applying Cloudflare tunnel credentials..."
        kubectl apply -f "$SECRET_FILE"
        echo "✅ Tunnel secrets applied"
    else
        echo "❌ Secret file not found at: $SECRET_FILE"
        exit 1
    fi

    echo
}

install_argocd() {
    echo "=== Installing ArgoCD ==="

    echo "Creating argocd namespace..."
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

    echo "Installing ArgoCD..."
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

    echo "Waiting for ArgoCD to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-application-controller -n argocd
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-repo-server -n argocd

    echo "✅ ArgoCD installed successfully"
    echo
}

apply_applicationsets() {
    echo "=== Applying ArgoCD ApplicationSets ==="

    ARGOCD_DIR="$SCRIPT_DIR/../../k8s/argocd"

    echo "Applying ApplicationSets..."
    kubectl apply -f "$ARGOCD_DIR/diocesan-vitality-environments-applicationset.yaml"
    kubectl apply -f "$ARGOCD_DIR/sealed-secrets-multi-env-applicationset.yaml"
    kubectl apply -f "$ARGOCD_DIR/cloudflare-tunnel-multi-env-applicationset.yaml"

    echo "✅ ApplicationSets applied"
    echo
}

show_access_info() {
    echo "=== Access Information ==="
    cd "$STAGING_DIR"

    # Get hostnames from Terraform output
    UI_HOSTNAME=$(terraform output -json hostnames | jq -r '.ui')
    API_HOSTNAME=$(terraform output -json hostnames | jq -r '.api')
    ARGOCD_HOSTNAME=$(terraform output -json hostnames | jq -r '.argocd')

    echo "🌐 Service URLs:"
    echo "   UI:     https://$UI_HOSTNAME"
    echo "   API:    https://$API_HOSTNAME"
    echo "   ArgoCD: https://$ARGOCD_HOSTNAME"
    echo

    echo "🔐 ArgoCD Access:"
    echo "   Username: admin"
    echo "   Password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 -d"
    echo

    echo "⚡ Quick Commands:"
    echo "   Set kubeconfig: export KUBECONFIG=$(terraform output -raw kubeconfig_path)"
    echo "   Port forward:   kubectl port-forward svc/argocd-server -n argocd 8080:443"
    echo "   View apps:      kubectl get applications -n argocd"
    echo

    echo "📚 Next Steps:"
    echo "1. Access ArgoCD UI and change admin password"
    echo "2. Verify applications are syncing properly"
    echo "3. Configure any environment-specific secrets"
    echo "4. Test application deployments"
    echo
}

main() {
    check_prerequisites
    generate_tfvars
    deploy_infrastructure
    setup_kubernetes
    apply_tunnel_secrets
    install_argocd
    apply_applicationsets
    show_access_info

    echo "🏁 Staging environment deployment complete!"
    echo "   Infrastructure managed by Terraform"
    echo "   Applications managed by ArgoCD"
}

main "$@"
