#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
    cat << EOF
Kubectl Context Management for Diocesan Vitality

Usage: $0 [COMMAND]

Commands:
  list             List all kubectl contexts
  current          Show current kubectl context
  dev              Switch to development cluster context
  staging          Switch to staging cluster context
  status           Show status of all environment contexts
  help             Show this help message

Examples:
  $0 list          # List all available contexts
  $0 dev           # Switch to development environment
  $0 staging       # Switch to staging environment
  $0 status        # Check status of all environments

EOF
}

list_contexts() {
    echo "🔧 Available kubectl contexts:"
    kubectl config get-contexts
}

show_current() {
    CURRENT=$(kubectl config current-context 2>/dev/null || echo "No context set")
    echo "📍 Current context: $CURRENT"
}

switch_to_dev() {
    DEV_CONTEXT="diocesan-vitality-dev"
    if kubectl config get-contexts -o name | grep -q "^${DEV_CONTEXT}$"; then
        kubectl config use-context "$DEV_CONTEXT"
        echo "✅ Switched to development context: $DEV_CONTEXT"

        # Test connection
        if kubectl get nodes &>/dev/null; then
            echo "🔗 Connection to development cluster confirmed"
            kubectl get nodes
        else
            echo "⚠️  Warning: Cannot connect to development cluster"
        fi
    else
        echo "❌ Development context '$DEV_CONTEXT' not found"
        echo "   Run: cd terraform/environments/dev && terraform apply"
        echo "   Or manually add context with: kubectl config set-context $DEV_CONTEXT"
    fi
}

switch_to_staging() {
    STAGING_CONTEXT="diocesan-vitality-staging"
    if kubectl config get-contexts -o name | grep -q "^${STAGING_CONTEXT}$"; then
        kubectl config use-context "$STAGING_CONTEXT"
        echo "✅ Switched to staging context: $STAGING_CONTEXT"

        # Test connection
        if kubectl get nodes &>/dev/null; then
            echo "🔗 Connection to staging cluster confirmed"
            kubectl get nodes
        else
            echo "⚠️  Warning: Cannot connect to staging cluster"
        fi
    else
        echo "❌ Staging context '$STAGING_CONTEXT' not found"
        echo "   Run: cd terraform/environments/staging && terraform apply"
        echo "   Or manually add context with: kubectl config set-context $STAGING_CONTEXT"
    fi
}

show_status() {
    echo "🎯 Diocesan Vitality Kubernetes Contexts Status"
    echo "==============================================="

    CURRENT=$(kubectl config current-context 2>/dev/null || echo "none")
    echo "📍 Current context: $CURRENT"
    echo

    # Check development context
    DEV_CONTEXT="diocesan-vitality-dev"
    if kubectl config get-contexts -o name | grep -q "^${DEV_CONTEXT}$"; then
        echo "✅ Development context: $DEV_CONTEXT (available)"
        if [[ "$CURRENT" == "$DEV_CONTEXT" ]]; then
            echo "   🔹 Currently active"
            if kubectl get nodes &>/dev/null; then
                NODE_COUNT=$(kubectl get nodes --no-headers | wc -l)
                echo "   🔗 Connected ($NODE_COUNT nodes)"
            else
                echo "   ⚠️  Connection failed"
            fi
        fi
    else
        echo "❌ Development context: $DEV_CONTEXT (not found)"
        echo "   💡 Create with: cd terraform/environments/dev && terraform apply"
    fi
    echo

    # Check staging context
    STAGING_CONTEXT="diocesan-vitality-staging"
    if kubectl config get-contexts -o name | grep -q "^${STAGING_CONTEXT}$"; then
        echo "✅ Staging context: $STAGING_CONTEXT (available)"
        if [[ "$CURRENT" == "$STAGING_CONTEXT" ]]; then
            echo "   🔹 Currently active"
            if kubectl get nodes &>/dev/null; then
                NODE_COUNT=$(kubectl get nodes --no-headers | wc -l)
                echo "   🔗 Connected ($NODE_COUNT nodes)"
            else
                echo "   ⚠️  Connection failed"
            fi
        fi
    else
        echo "❌ Staging context: $STAGING_CONTEXT (not found)"
        echo "   💡 Create with: cd terraform/environments/staging && terraform apply"
    fi
    echo

    # Show other contexts
    OTHER_CONTEXTS=$(kubectl config get-contexts -o name | grep -v "diocesan-vitality" || true)
    if [[ -n "$OTHER_CONTEXTS" ]]; then
        echo "📋 Other contexts:"
        echo "$OTHER_CONTEXTS" | sed 's/^/   /'
    fi
}

main() {
    case "${1:-help}" in
        list)
            list_contexts
            ;;
        current)
            show_current
            ;;
        dev|development)
            switch_to_dev
            ;;
        stg|staging)
            switch_to_staging
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "❌ Unknown command: $1"
            echo
            show_help
            exit 1
            ;;
    esac
}

main "$@"
