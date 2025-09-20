#!/bin/bash

set -euo pipefail

STAGING_CLUSTER="dv-stg"
DEV_CLUSTER="dv-dev"

echo "=== DigitalOcean Dev/Staging Cluster Destruction ==="
echo "⚠️  WARNING: This will permanently delete dev and staging clusters!"
echo

check_doctl() {
    if ! command -v doctl &> /dev/null; then
        echo "❌ doctl is not installed. Please install it first:"
        echo "   https://docs.digitalocean.com/reference/doctl/how-to/install/"
        exit 1
    fi
    echo "✅ doctl is installed"
}

check_auth() {
    if ! doctl auth list | grep -q "current"; then
        echo "❌ doctl is not authenticated. Please run: doctl auth init"
        exit 1
    fi
    echo "✅ doctl is authenticated"
}

check_cluster_exists() {
    local cluster_name=$1
    if doctl kubernetes cluster get "$cluster_name" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

destroy_cluster() {
    local cluster_name=$1

    echo "🗑️  Destroying cluster $cluster_name..."

    if ! check_cluster_exists "$cluster_name"; then
        echo "ℹ️  Cluster $cluster_name does not exist or already destroyed"
        return 0
    fi

    # Remove kubectl context first (non-fatal if it fails)
    echo "   Removing kubectl context..."
    kubectl config delete-context "$cluster_name" 2>/dev/null || echo "   (kubectl context not found or already removed)"
    kubectl config delete-cluster "$cluster_name" 2>/dev/null || echo "   (kubectl cluster not found or already removed)"
    kubectl config unset "users.$cluster_name-admin" 2>/dev/null || echo "   (kubectl user not found or already removed)"

    # Destroy the cluster
    if doctl kubernetes cluster delete "$cluster_name" --force; then
        echo "✅ Successfully destroyed cluster: $cluster_name"

        # Wait for complete deletion
        echo "   Waiting for cluster deletion to complete..."
        local retries=0
        local max_retries=20

        while [[ $retries -lt $max_retries ]]; do
            if ! check_cluster_exists "$cluster_name"; then
                echo "✅ Cluster $cluster_name deletion confirmed"
                break
            fi

            echo "   Still deleting... ($(($retries + 1))/$max_retries)"
            sleep 15
            ((retries++))
        done

        if [[ $retries -eq $max_retries ]]; then
            echo "⚠️  Timeout waiting for deletion confirmation. Check cluster status manually."
        fi

    else
        echo "❌ Failed to destroy cluster: $cluster_name"
        return 1
    fi

    echo
}

main() {
    echo "Starting dev/staging cluster destruction process..."
    echo

    check_doctl
    check_auth
    echo

    # List current clusters
    echo "=== Current clusters ==="
    doctl kubernetes cluster list --format Name,Region,Version,Status
    echo

    # Check what we're about to destroy
    local clusters_to_destroy=()

    if check_cluster_exists "$STAGING_CLUSTER"; then
        clusters_to_destroy+=("$STAGING_CLUSTER")
    fi

    if check_cluster_exists "$DEV_CLUSTER"; then
        clusters_to_destroy+=("$DEV_CLUSTER")
    fi

    if [[ ${#clusters_to_destroy[@]} -eq 0 ]]; then
        echo "ℹ️  No target clusters found to destroy ($STAGING_CLUSTER, $DEV_CLUSTER)"
        echo "✅ Nothing to do"
        exit 0
    fi

    echo "📋 Clusters found for destruction:"
    for cluster in "${clusters_to_destroy[@]}"; do
        echo "   - $cluster"
        doctl kubernetes cluster get "$cluster" --format ID,Name,Region,Version,Status,NodePools
    done
    echo

    echo "⚠️  DANGER ZONE ⚠️"
    echo "This will permanently destroy ALL dev/staging clusters:"
    echo "   🎯 Target clusters: ${clusters_to_destroy[*]}"
    echo "   💀 All data will be lost"
    echo "   🔄 This action cannot be undone"
    echo

    read -p "Continue with cluster destruction? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cluster destruction cancelled"
        exit 0
    fi

    # Final confirmation for all clusters
    echo
    echo "⚠️  FINAL WARNING: About to destroy ${#clusters_to_destroy[@]} cluster(s)"
    echo "   Clusters: ${clusters_to_destroy[*]}"
    echo "   This will delete ALL workloads, data, and configurations!"
    echo
    read -p "Type 'DELETE ALL' to confirm destruction of all clusters: " -r

    if [[ "$REPLY" != "DELETE ALL" ]]; then
        echo "❌ Destruction cancelled"
        exit 0
    fi

    # Destroy all clusters
    local destroyed_count=0
    echo
    echo "🚀 Starting destruction of ${#clusters_to_destroy[@]} cluster(s)..."
    echo

    for cluster in "${clusters_to_destroy[@]}"; do
        if destroy_cluster "$cluster"; then
            ((destroyed_count++))
        fi
    done

    echo "=== Destruction Summary ==="
    echo "📊 Clusters processed: ${#clusters_to_destroy[@]}"
    echo "✅ Clusters destroyed: $destroyed_count"
    echo "❌ Clusters failed: $((${#clusters_to_destroy[@]} - destroyed_count))"
    echo

    if [[ $destroyed_count -gt 0 ]]; then
        echo "🧹 Final cleanup - listing remaining clusters:"
        doctl kubernetes cluster list --format Name,Region,Version,Status
    fi

    echo
    echo "🏁 Dev/staging cluster destruction process complete"
}

main "$@"
