#!/bin/bash

set -euo pipefail

DOMAIN="diocesanvitality.org"
TUNNEL_PREFIX="do-nyc2-dv"

echo "=== Cloudflare Tunnel Setup for Development/Staging ==="
echo

check_cloudflared() {
    if ! command -v cloudflared &> /dev/null; then
        echo "❌ cloudflared CLI is not installed"
        echo "   Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        echo ""
        echo "Quick install options:"
        echo "  # macOS:"
        echo "  brew install cloudflared"
        echo ""
        echo "  # Linux (x86_64):"
        echo "  wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
        echo "  sudo dpkg -i cloudflared-linux-amd64.deb"
        echo ""
        echo "  # Linux (ARM64):"
        echo "  wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb"
        echo "  sudo dpkg -i cloudflared-linux-arm64.deb"
        exit 1
    fi
    echo "✅ cloudflared CLI is available"
}

check_authentication() {
    echo "Checking Cloudflare authentication..."

    if ! cloudflared tunnel list &>/dev/null; then
        echo "❌ Not authenticated with Cloudflare"
        echo "   Please authenticate first:"
        echo "   cloudflared tunnel login"
        echo ""
        echo "This will:"
        echo "1. Open browser to Cloudflare login"
        echo "2. Select your domain ($DOMAIN)"
        echo "3. Authorize cloudflared CLI access"
        exit 1
    fi

    echo "✅ Cloudflare authentication verified"
}

check_existing_tunnel() {
    local tunnel_name=$1

    if cloudflared tunnel list | grep -q "$tunnel_name"; then
        echo "⚠️  Tunnel '$tunnel_name' already exists"

        # Get tunnel ID
        local tunnel_id=$(cloudflared tunnel list | grep "$tunnel_name" | awk '{print $1}')
        echo "   Tunnel ID: $tunnel_id"

        read -p "   Delete and recreate tunnel? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "   Deleting existing tunnel..."
            cloudflared tunnel delete "$tunnel_name" || true
            sleep 2
            return 1  # Tunnel deleted, needs creation
        else
            echo "   Using existing tunnel"
            return 0  # Tunnel exists, don't create
        fi
    fi

    return 1  # Tunnel doesn't exist, needs creation
}

create_tunnel() {
    local tunnel_name=$1
    local environment=$2
    local ui_hostname=$3
    local api_hostname=$4
    local argocd_hostname=$5

    echo "=== Creating tunnel: $tunnel_name ==="

    # Check if tunnel already exists
    if check_existing_tunnel "$tunnel_name"; then
        echo "ℹ️  Tunnel $tunnel_name already exists, skipping creation"
        return 0
    fi

    # Create the tunnel
    echo "Creating Cloudflare tunnel..."
    cloudflared tunnel create "$tunnel_name"

    # Get tunnel ID
    local tunnel_id=$(cloudflared tunnel list | grep "$tunnel_name" | awk '{print $1}')
    echo "✅ Tunnel created with ID: $tunnel_id"

    # Create DNS records
    echo "Creating DNS records..."
    cloudflared tunnel route dns "$tunnel_name" "$ui_hostname"
    cloudflared tunnel route dns "$tunnel_name" "$api_hostname"
    cloudflared tunnel route dns "$tunnel_name" "$argocd_hostname"

    echo "✅ DNS records created:"
    echo "   - $ui_hostname → $tunnel_name"
    echo "   - $api_hostname → $tunnel_name"
    echo "   - $argocd_hostname → $tunnel_name"

    return 0
}

generate_sealed_secret() {
    local tunnel_name=$1
    local environment=$2
    local cluster_context=$3

    echo "=== Generating sealed secret for $tunnel_name ==="

    # Get tunnel credentials
    local tunnel_id=$(cloudflared tunnel list | grep "$tunnel_name" | awk '{print $1}')
    local creds_file="$HOME/.cloudflared/$tunnel_id.json"

    if [[ ! -f "$creds_file" ]]; then
        echo "❌ Credentials file not found: $creds_file"
        return 1
    fi

    # Switch to cluster context
    kubectl config use-context "$cluster_context"

    # Check if kubeseal is available
    if ! command -v kubeseal &> /dev/null; then
        echo "⚠️  kubeseal not available, creating regular secret"
        echo "   Install kubeseal for production use: https://sealed-secrets.netlify.app/"

        # Create regular secret
        kubectl create secret generic tunnel-credentials \
            --from-file=credentials.json="$creds_file" \
            --namespace="cloudflare-tunnel-${environment}" \
            --dry-run=client -o yaml > "tunnel-credentials-${environment}.yaml"

        echo "✅ Secret manifest created: tunnel-credentials-${environment}.yaml"
        echo "   Apply with: kubectl apply -f tunnel-credentials-${environment}.yaml"

    else
        echo "Creating sealed secret..."

        # Create sealed secret
        kubectl create secret generic tunnel-credentials \
            --from-file=credentials.json="$creds_file" \
            --namespace="cloudflare-tunnel-${environment}" \
            --dry-run=client -o yaml | \
            kubeseal -o yaml > "sealed-tunnel-credentials-${environment}.yaml"

        echo "✅ Sealed secret created: sealed-tunnel-credentials-${environment}.yaml"
        echo "   This can be safely committed to git"

        # Apply the sealed secret
        kubectl apply -f "sealed-tunnel-credentials-${environment}.yaml"
        echo "✅ Sealed secret applied to cluster"
    fi

    return 0
}

setup_tunnel_for_environment() {
    local environment=$1
    local cluster_context=$2

    local tunnel_name="${TUNNEL_PREFIX}-${environment}"
    local ui_hostname="${environment}.ui.${DOMAIN}"
    local api_hostname="${environment}.api.${DOMAIN}"
    local argocd_hostname="${environment}.argocd.${DOMAIN}"

    echo "=== Setting up tunnel for $environment environment ==="
    echo "   Tunnel name: $tunnel_name"
    echo "   Cluster: $cluster_context"
    echo "   UI hostname: $ui_hostname"
    echo "   API hostname: $api_hostname"
    echo "   ArgoCD hostname: $argocd_hostname"
    echo

    # Check cluster access
    if ! kubectl config get-contexts | grep -q "$cluster_context"; then
        echo "❌ kubectl context '$cluster_context' not found"
        echo "   Run: doctl kubernetes cluster kubeconfig save ${cluster_context}"
        return 1
    fi

    # Create tunnel
    if ! create_tunnel "$tunnel_name" "$environment" "$ui_hostname" "$api_hostname" "$argocd_hostname"; then
        echo "❌ Failed to create tunnel for $environment"
        return 1
    fi

    # Generate sealed secret
    if ! generate_sealed_secret "$tunnel_name" "$environment" "$cluster_context"; then
        echo "❌ Failed to create sealed secret for $environment"
        return 1
    fi

    echo "✅ Tunnel setup complete for $environment"
    echo

    return 0
}

show_tunnel_info() {
    echo "=== Tunnel Summary ==="
    echo "Listing all tunnels:"
    cloudflared tunnel list
    echo

    echo "DNS records created:"
    echo "✅ dev.ui.${DOMAIN}"
    echo "✅ dev.api.${DOMAIN}"
    echo "✅ dev.argocd.${DOMAIN}"
    echo "✅ stg.ui.${DOMAIN}"
    echo "✅ stg.api.${DOMAIN}"
    echo "✅ stg.argocd.${DOMAIN}"
    echo

    echo "📁 Files created in current directory:"
    ls -la *tunnel-credentials*.yaml 2>/dev/null || echo "   (No credential files found)"
    echo
}

main() {
    echo "Starting Cloudflare tunnel setup for development and staging..."
    echo

    check_cloudflared
    check_authentication
    echo

    # Setup development tunnel
    if setup_tunnel_for_environment "dev" "dv-dev"; then
        echo "✅ Development tunnel setup complete"
    else
        echo "❌ Failed to setup development tunnel"
    fi

    # Setup staging tunnel
    if setup_tunnel_for_environment "stg" "dv-stg"; then
        echo "✅ Staging tunnel setup complete"
    else
        echo "❌ Failed to setup staging tunnel"
    fi

    show_tunnel_info

    echo "📋 Next Steps:"
    echo "1. Verify tunnels are running:"
    echo "   cloudflared tunnel list"
    echo ""
    echo "2. Test DNS resolution:"
    echo "   nslookup dev.ui.${DOMAIN}"
    echo "   nslookup dev.api.${DOMAIN}"
    echo ""
    echo "3. Deploy applications via ArgoCD:"
    echo "   git push origin develop  # Deploys to dev"
    echo "   git push origin main     # Deploys to staging"
    echo ""
    echo "4. Access applications:"
    echo "   UI:     https://dev.ui.${DOMAIN} | https://stg.ui.${DOMAIN}"
    echo "   API:    https://dev.api.${DOMAIN} | https://stg.api.${DOMAIN}"
    echo "   ArgoCD: https://dev.argocd.${DOMAIN} | https://stg.argocd.${DOMAIN}"
    echo ""
    echo "🔐 Security Notes:"
    echo "   - Tunnel credentials are stored as sealed secrets"
    echo "   - Regular secrets files should NOT be committed to git"
    echo "   - Sealed secrets can be safely committed"
    echo ""
    echo "🏁 Cloudflare tunnel setup complete!"
}

main "$@"
