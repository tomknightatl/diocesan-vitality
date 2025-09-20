#!/bin/bash

set -euo pipefail

PRODUCTION_CLUSTER="dv-prd"
STAGING_CLUSTER="dv-stg"
DEV_CLUSTER="dv-dev"
REGION="nyc1"

echo "=== DigitalOcean Kubernetes Cluster Management ==="
echo

check_doctl() {
    if ! command -v doctl &> /dev/null; then
        echo "? doctl is not installed. Please install it first:"
        echo "   https://docs.digitalocean.com/reference/doctl/how-to/install/"
        exit 1
    fi
    echo "? doctl is installed"
}

check_auth() {
    if ! doctl auth list | grep -q "current"; then
        echo "? doctl is not authenticated. Please run: doctl auth init"
        exit 1
    fi
    echo "? doctl is authenticated"
}

get_cluster_config() {
    local cluster_name=$1
    echo "Getting configuration for cluster: $cluster_name"

    if ! doctl kubernetes cluster get "$cluster_name" --format ID,Name,Region,Version,Status,NodePools 2>/dev/null; then
        echo "? Cluster $cluster_name not found"
        return 1
    fi

    echo "Getting detailed node pool information:"
    doctl kubernetes cluster node-pool list "$cluster_name" --format ID,Name,Size,Count,Tags,Labels,Taints 2>/dev/null || true

    return 0
}

get_production_config() {
    echo "=== Checking Production Cluster ($PRODUCTION_CLUSTER) ==="

    if ! get_cluster_config "$PRODUCTION_CLUSTER"; then
        echo "? Production cluster $PRODUCTION_CLUSTER not found!"
        echo "Expected kubectl config name: $PRODUCTION_CLUSTER"
        exit 1
    fi

    echo "? Production cluster found"
    echo

    # Get detailed configuration for cloning
    echo "Getting detailed production cluster configuration..."
    PROD_CONFIG=$(doctl kubernetes cluster get "$PRODUCTION_CLUSTER" --format ID,Name,Region,Version,VPCuuid,Tags --no-header 2>/dev/null)

    if [[ -z "$PROD_CONFIG" ]]; then
        echo "? Could not retrieve production cluster configuration"
        exit 1
    fi

    echo "Production cluster details:"
    echo "$PROD_CONFIG"
    echo

    # Parse production configuration
    PROD_REGION=$(echo "$PROD_CONFIG" | awk '{print $3}')
    PROD_VERSION=$(echo "$PROD_CONFIG" | awk '{print $4}')
    PROD_VPC=$(echo "$PROD_CONFIG" | awk '{print $5}')
    PROD_TAGS=$(echo "$PROD_CONFIG" | awk '{for(i=6;i<=NF;i++) printf "%s ", $i; print ""}' | sed 's/,/ /g')

    echo "Parsed configuration:"
    echo "  Region: $PROD_REGION"
    echo "  Version: $PROD_VERSION"
    echo "  VPC: $PROD_VPC"
    echo "  Tags: $PROD_TAGS"
    echo

    # Get node pool configuration
    PROD_NODE_POOLS=$(doctl kubernetes cluster node-pool list "$PRODUCTION_CLUSTER" --format Name,Size,Count,Tags,Labels --no-header 2>/dev/null)
    echo "Production node pools:"
    echo "$PROD_NODE_POOLS"
    echo
}

check_cluster_exists() {
    local cluster_name=$1
    if doctl kubernetes cluster get "$cluster_name" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

create_cluster_like_production() {
    local new_cluster_name=$1
    local environment=$(echo "$new_cluster_name" | sed 's/.*-//')

    echo "=== Creating $environment cluster: $new_cluster_name ==="

    # Parse node pools from production
    local slow_pool=$(echo "$PROD_NODE_POOLS" | grep "slow-pool" | head -1)
    local fast_pool=$(echo "$PROD_NODE_POOLS" | grep "fast-pool" | head -1)

    local slow_size=$(echo "$slow_pool" | awk '{print $2}')
    local slow_count=$(echo "$slow_pool" | awk '{print $3}')
    local fast_size=$(echo "$fast_pool" | awk '{print $2}')
    local fast_count=$(echo "$fast_pool" | awk '{print $3}')

    echo "Creating cluster with:"
    echo "  Name: $new_cluster_name"
    echo "  Region: $PROD_REGION"
    echo "  Version: $PROD_VERSION"
    echo "  Slow pool: $slow_size (count: $slow_count)"
    echo "  Fast pool: $fast_size (count: $fast_count)"
    echo

    # Build the create command with both node pools
    local create_cmd="doctl kubernetes cluster create $new_cluster_name"
    create_cmd="$create_cmd --region $PROD_REGION"
    create_cmd="$create_cmd --version $PROD_VERSION"
    create_cmd="$create_cmd --node-pool \"name=${environment}-slow-pool;size=${slow_size};count=${slow_count}\""
    create_cmd="$create_cmd --node-pool \"name=${environment}-fast-pool;size=${fast_size};count=${fast_count}\""

    if [[ -n "$PROD_VPC" && "$PROD_VPC" != "<no value>" && "$PROD_VPC" != "<nil>" ]]; then
        create_cmd="$create_cmd --vpc-uuid $PROD_VPC"
    fi

    # Use simple, valid tags
    create_cmd="$create_cmd --tag \"k8s,environment-${environment}\""

    echo "Executing: $create_cmd"
    echo

    # Execute the command (this will take several minutes)
    if eval "$create_cmd"; then
        echo "✅ Successfully created cluster: $new_cluster_name"

        # Wait for cluster to be ready
        echo "Waiting for cluster to be ready..."
        local retries=0
        local max_retries=30

        while [[ $retries -lt $max_retries ]]; do
            local status=$(doctl kubernetes cluster get "$new_cluster_name" --format Status --no-header 2>/dev/null || echo "unknown")

            if [[ "$status" == "running" ]]; then
                echo "✅ Cluster $new_cluster_name is ready"
                break
            fi

            echo "Cluster status: $status (waiting...)"
            sleep 30
            ((retries++))
        done

        if [[ $retries -eq $max_retries ]]; then
            echo "⚠️  Timeout waiting for cluster to be ready. Check cluster status manually."
        fi

        # Get kubectl config
        echo "Getting kubectl credentials for $new_cluster_name..."
        if doctl kubernetes cluster kubeconfig save "$new_cluster_name"; then
            echo "✅ kubectl credentials saved for $new_cluster_name"
        else
            echo "❌  Failed to save kubectl credentials. Run manually: doctl kubernetes cluster kubeconfig save $new_cluster_name"
        fi

    else
        echo "❌ Failed to create cluster: $new_cluster_name"
        return 1
    fi

    echo
}

main() {
    echo "Starting DigitalOcean cluster management..."
    echo

    check_doctl
    check_auth
    echo

    # Get production cluster configuration
    get_production_config

    # Check kubectl config for production cluster
    echo "=== Checking kubectl configuration ==="
    if kubectl config get-contexts | grep -q "$PRODUCTION_CLUSTER"; then
        echo "? kubectl context '$PRODUCTION_CLUSTER' exists"
    else
        echo "??  kubectl context '$PRODUCTION_CLUSTER' not found"
        echo "   Getting kubectl credentials..."
        if doctl kubernetes cluster kubeconfig save "$PRODUCTION_CLUSTER"; then
            echo "? kubectl credentials saved for $PRODUCTION_CLUSTER"
        else
            echo "? Failed to save kubectl credentials for production cluster"
        fi
    fi
    echo

    # Check and create staging cluster
    echo "=== Checking Staging Cluster ($STAGING_CLUSTER) ==="
    if check_cluster_exists "$STAGING_CLUSTER"; then
        echo "? Staging cluster already exists"
        get_cluster_config "$STAGING_CLUSTER"
    else
        echo "? Staging cluster not found"
        read -p "Create staging cluster with production settings? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            create_cluster_like_production "$STAGING_CLUSTER"
        else
            echo "Skipping staging cluster creation"
        fi
    fi
    echo

    # Check and create dev cluster
    echo "=== Checking Dev Cluster ($DEV_CLUSTER) ==="
    if check_cluster_exists "$DEV_CLUSTER"; then
        echo "? Dev cluster already exists"
        get_cluster_config "$DEV_CLUSTER"
    else
        echo "? Dev cluster not found"
        read -p "Create dev cluster with production settings? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            create_cluster_like_production "$DEV_CLUSTER"
        else
            echo "Skipping dev cluster creation"
        fi
    fi

    echo "=== Summary ==="
    echo "Listing all clusters:"
    doctl kubernetes cluster list --format Name,Region,Version,Status,NodePools
    echo
    echo "kubectl contexts:"
    kubectl config get-contexts | grep -E "(dv-dev|dv-stg|dv-prd)" || echo "No matching contexts found"
    echo
    echo "✅ Cluster management complete"
    echo

    # Offer to setup ArgoCD if any clusters exist
    local clusters_exist=false
    if check_cluster_exists "$STAGING_CLUSTER" || check_cluster_exists "$DEV_CLUSTER"; then
        clusters_exist=true
    fi

    if [[ "$clusters_exist" == "true" ]]; then
        echo "🚀 ArgoCD Setup"
        echo "Would you like to install and configure ArgoCD for GitOps deployment?"
        read -p "Setup ArgoCD in new clusters? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Starting ArgoCD setup..."
            ./setup-argocd.sh

            # Offer to setup Cloudflare tunnels
            echo ""
            echo "🌐 Cloudflare Tunnel Setup"
            echo "Would you like to create Cloudflare tunnels for secure ingress?"
            read -p "Setup Cloudflare tunnels? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "Starting Cloudflare tunnel setup..."
                ./setup-cloudflare-tunnels.sh
            else
                echo "ℹ️  Skipping Cloudflare tunnel setup"
                echo "   To setup later, run: ./setup-cloudflare-tunnels.sh"
            fi
        else
            echo "ℹ️  Skipping ArgoCD setup"
            echo "   To setup later, run: ./setup-argocd.sh"
        fi
    fi
}

main "$@"
