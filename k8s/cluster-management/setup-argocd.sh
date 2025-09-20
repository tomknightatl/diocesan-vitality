#!/bin/bash

set -euo pipefail

REPO_URL="https://github.com/tomknightatl/diocesan-vitality"
ARGOCD_VERSION="v2.12.3"

echo "=== ArgoCD Setup for Development/Staging Clusters ==="
echo

check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo "❌ kubectl is not installed"
        exit 1
    fi
    echo "✅ kubectl is available"
}

check_cluster_access() {
    local cluster_name=$1
    echo "Checking access to cluster: $cluster_name"

    if ! kubectl config get-contexts | grep -q "$cluster_name"; then
        echo "❌ kubectl context '$cluster_name' not found"
        echo "   Run: doctl kubernetes cluster kubeconfig save $cluster_name"
        return 1
    fi

    # Test cluster connectivity
    kubectl config use-context "$cluster_name"
    if ! kubectl get nodes &>/dev/null; then
        echo "❌ Cannot connect to cluster $cluster_name"
        return 1
    fi

    echo "✅ Cluster $cluster_name is accessible"
    return 0
}

install_argocd() {
    local cluster_name=$1
    echo "=== Installing ArgoCD in cluster: $cluster_name ==="

    # Switch to cluster context
    kubectl config use-context "$cluster_name"

    # Create ArgoCD namespace
    echo "Creating argocd namespace..."
    kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

    # Install ArgoCD
    echo "Installing ArgoCD $ARGOCD_VERSION..."
    kubectl apply -n argocd -f "https://raw.githubusercontent.com/argoproj/argo-cd/$ARGOCD_VERSION/manifests/install.yaml"

    # Wait for ArgoCD to be ready
    echo "Waiting for ArgoCD to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-application-controller -n argocd
    kubectl wait --for=condition=available --timeout=300s deployment/argocd-repo-server -n argocd

    echo "✅ ArgoCD installed successfully in $cluster_name"
}

store_password_securely() {
    local cluster_name=$1
    local password=$2
    local password_file="/tmp/argocd-${cluster_name}-password.txt"

    # Store password in a temporary file with restricted permissions
    echo "$password" > "$password_file"
    chmod 600 "$password_file"

    echo "🔐 Password stored securely at: $password_file (readable only by you)"
    echo "   File will be automatically cleaned up on next reboot"
    echo
}

get_argocd_password() {
    local cluster_name=$1
    echo "Getting ArgoCD admin password for $cluster_name..."

    kubectl config use-context "$cluster_name"
    local password=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

    echo "ArgoCD Admin Credentials for $cluster_name:"
    echo "  Username: admin"
    echo "  Password: [REDACTED - use one of the methods below to retrieve]"
    echo

    # Store password securely for retrieval
    store_password_securely "$cluster_name" "$password"
}

add_repository() {
    local cluster_name=$1
    echo "=== Adding GitHub repository to ArgoCD in $cluster_name ==="

    kubectl config use-context "$cluster_name"

    # Create repository secret
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: diocesan-vitality-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: $REPO_URL
EOF

    echo "✅ Repository $REPO_URL added to ArgoCD in $cluster_name"
}

install_applications() {
    local cluster_name=$1
    local environment=$2
    echo "=== Installing ArgoCD Applications for $environment in $cluster_name ==="

    kubectl config use-context "$cluster_name"

    # Apply the main application ApplicationSet
    echo "Installing diocesan-vitality ApplicationSet..."
    kubectl apply -f "$(dirname "$0")/../argocd/diocesan-vitality-environments-applicationset.yaml"

    # Apply infrastructure ApplicationSets
    echo "Installing sealed-secrets ApplicationSet..."
    kubectl apply -f "$(dirname "$0")/../argocd/sealed-secrets-multi-env-applicationset.yaml"

    echo "Installing cloudflare-tunnel ApplicationSet..."
    kubectl apply -f "$(dirname "$0")/../argocd/cloudflare-tunnel-multi-env-applicationset.yaml"

    echo "✅ ApplicationSets installed in $cluster_name"
    echo "   - Diocesan Vitality applications (dev/staging environments)"
    echo "   - Sealed Secrets (infrastructure)"
    echo "   - Cloudflare Tunnel (infrastructure)"
}

setup_port_forward() {
    local cluster_name=$1
    echo "=== Setting up ArgoCD access for $cluster_name ==="

    kubectl config use-context "$cluster_name"

    echo "To access ArgoCD UI for $cluster_name:"
    echo "  1. Get password using one of these secure methods:"
    echo "     • From temp file: cat /tmp/argocd-${cluster_name}-password.txt"
    echo "     • From kubectl: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 -d"
    echo "     • From ArgoCD CLI: argocd admin initial-password -n argocd"
    echo "  2. Run: kubectl port-forward svc/argocd-server -n argocd 8080:443"
    echo "  3. Visit: https://localhost:8080"
    echo "  4. Login with username 'admin' and the password from step 1"
    echo "  5. Accept self-signed certificate warning"
    echo "  6. IMPORTANT: Change the admin password immediately after first login"
    echo
}

check_existing_argocd() {
    local cluster_name=$1

    kubectl config use-context "$cluster_name"

    if kubectl get namespace argocd &>/dev/null; then
        echo "⚠️  ArgoCD namespace already exists in $cluster_name"
        read -p "   Reinstall ArgoCD? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "   Removing existing ArgoCD installation..."
            kubectl delete namespace argocd --timeout=60s || true
            sleep 10
            return 0
        else
            echo "   Skipping ArgoCD installation for $cluster_name"
            return 1
        fi
    fi
    return 0
}

setup_cluster() {
    local cluster_name=$1
    local environment=$2

    echo "=== Setting up ArgoCD for $cluster_name ($environment) ==="
    echo

    # Check cluster access
    if ! check_cluster_access "$cluster_name"; then
        echo "❌ Skipping $cluster_name - cluster not accessible"
        return 1
    fi

    # Check if ArgoCD already exists
    if ! check_existing_argocd "$cluster_name"; then
        echo "ℹ️  Skipping ArgoCD installation for $cluster_name"
    else
        # Install ArgoCD
        install_argocd "$cluster_name"

        # Get admin password
        get_argocd_password "$cluster_name"
    fi

    # Add repository
    add_repository "$cluster_name"

    # Install applications
    install_applications "$cluster_name" "$environment"

    # Show access instructions
    setup_port_forward "$cluster_name"

    echo "✅ ArgoCD setup complete for $cluster_name"
    echo
}

main() {
    echo "Starting ArgoCD setup for development and staging clusters..."
    echo

    check_kubectl
    echo

    # Setup development cluster
    if setup_cluster "dv-dev" "development"; then
        echo "✅ Development cluster (dv-dev) setup complete"
    else
        echo "❌ Failed to setup development cluster"
    fi
    echo

    # Setup staging cluster
    if setup_cluster "dv-stg" "staging"; then
        echo "✅ Staging cluster (dv-stg) setup complete"
    else
        echo "❌ Failed to setup staging cluster"
    fi
    echo

    echo "=== Setup Summary ==="
    echo "ArgoCD has been installed and configured in available clusters with:"
    echo "✅ Diocesan Vitality applications (GitOps deployment)"
    echo "✅ Sealed Secrets (secure secret management)"
    echo "✅ Cloudflare Tunnel (secure ingress)"
    echo
    echo "📋 Next Steps:"
    echo "1. Access ArgoCD UI using port-forward commands shown above"
    echo "2. Verify applications are syncing:"
    echo "   kubectl get applications -n argocd"
    echo "3. Configure Cloudflare tunnel credentials (sealed secrets)"
    echo "4. Push to develop/main branches to trigger deployments"
    echo "5. Monitor application status in ArgoCD UI"
    echo
    echo "🔐 Security Setup Required:"
    echo "   - Create sealed secrets for Cloudflare tunnel credentials"
    echo "   - Configure environment-specific tunnel subdomains"
    echo "   - Update DNS records for new environments"
    echo
    echo "📚 Documentation:"
    echo "   - ArgoCD setup: k8s/argocd/README.md"
    echo "   - Development workflow: docs/DEVELOPMENT_ENVIRONMENTS.md"
    echo "   - Infrastructure configs: k8s/infrastructure/"
    echo
    echo "🏁 ArgoCD setup complete!"
}

main "$@"
