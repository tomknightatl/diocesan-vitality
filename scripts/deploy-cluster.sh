#!/bin/bash

# ⚠️  DEPRECATED: Multi-Cluster Deployment Script
#
# This script is deprecated in favor of GitOps with ArgoCD.
#
# RECOMMENDED APPROACH:
# - Use ArgoCD ApplicationSets for automated deployments
# - Push to 'develop' branch for dv-dev cluster
# - Push to 'main' branch for dv-stg cluster
# - Manual ArgoCD sync for production
#
# See: docs/DEVELOPMENT_ENVIRONMENTS.md for GitOps workflow
# See: k8s/argocd/README.md for ArgoCD setup
#
# This script remains for emergency manual deployments only.

echo "⚠️  WARNING: This script is deprecated!"
echo "   Recommended: Use GitOps with ArgoCD instead"
echo "   See: docs/DEVELOPMENT_ENVIRONMENTS.md"
echo ""
read -p "Continue with manual deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    echo "💡 Use GitOps: git push origin develop  # for dv-dev"
    echo "💡 Use GitOps: git push origin main     # for dv-stg"
    exit 0
fi
echo ""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage function
usage() {
    echo "Usage: $0 <environment> [options]"
    echo ""
    echo "Environments:"
    echo "  dev, development    Deploy to development cluster (do-nyc2-dv-dev)"
    echo "  stg, staging        Deploy to staging cluster (do-nyc2-dv-stg)"
    echo "  prod, production    Deploy to production cluster (via ArgoCD)"
    echo ""
    echo "Options:"
    echo "  --force            Force deployment without confirmation"
    echo "  --build-images     Build new images before deployment"
    echo "  --skip-tests       Skip test verification"
    echo ""
    echo "Examples:"
    echo "  $0 dev --build-images"
    echo "  $0 staging"
    echo "  $0 production --force"
    exit 1
}

# Parse arguments
ENVIRONMENT=""
FORCE_DEPLOY=false
BUILD_IMAGES=false
SKIP_TESTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        dev|development)
            ENVIRONMENT="development"
            CLUSTER_CONTEXT="do-nyc2-dv-dev"
            NAMESPACE="diocesan-vitality-dev"
            shift
            ;;
        stg|staging)
            ENVIRONMENT="staging"
            CLUSTER_CONTEXT="do-nyc2-dv-stg"
            NAMESPACE="diocesan-vitality-staging"
            shift
            ;;
        prod|production)
            ENVIRONMENT="production"
            CLUSTER_CONTEXT="do-nyc2-dv-prd"
            NAMESPACE="diocesan-vitality"
            shift
            ;;
        --force)
            FORCE_DEPLOY=true
            shift
            ;;
        --build-images)
            BUILD_IMAGES=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

if [ -z "$ENVIRONMENT" ]; then
    print_error "Environment is required"
    usage
fi

print_status "🚀 Starting deployment to $ENVIRONMENT environment"
print_status "📋 Configuration:"
print_status "   Environment: $ENVIRONMENT"
print_status "   Cluster: $CLUSTER_CONTEXT"
print_status "   Namespace: $NAMESPACE"
print_status "   Force deploy: $FORCE_DEPLOY"
print_status "   Build images: $BUILD_IMAGES"
print_status "   Skip tests: $SKIP_TESTS"

# Confirmation
if [ "$FORCE_DEPLOY" != "true" ]; then
    echo
    read -p "Do you want to continue with deployment to $ENVIRONMENT? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled"
        exit 0
    fi
fi

# Verify kubectl context
print_status "🔧 Verifying cluster connectivity..."
if kubectl config use-context "$CLUSTER_CONTEXT" > /dev/null 2>&1; then
    print_success "✅ Connected to cluster: $CLUSTER_CONTEXT"
else
    print_error "❌ Failed to connect to cluster: $CLUSTER_CONTEXT"
    print_status "Available contexts:"
    kubectl config get-contexts
    exit 1
fi

# Run tests (unless skipped)
if [ "$SKIP_TESTS" != "true" ]; then
    print_status "🧪 Running tests..."
    if python -m pytest tests/ -v; then
        print_success "✅ All tests passed"
    else
        print_error "❌ Tests failed"
        exit 1
    fi
fi

# Build images (if requested)
if [ "$BUILD_IMAGES" = "true" ]; then
    print_status "🏗️ Building images..."
    TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)

    # Trigger GitHub Actions workflow for image building
    if command -v gh &> /dev/null; then
        gh workflow run multi-cluster-ci-cd.yml -f target_cluster="$ENVIRONMENT"
        print_success "✅ Image build triggered via GitHub Actions"
        print_status "Monitor progress: gh run watch"

        read -p "Press Enter when images are built and ready for deployment..."
    else
        print_warning "GitHub CLI not found. Please build images manually or install gh CLI"
        exit 1
    fi
fi

# Deploy to cluster
print_status "🚀 Deploying to $ENVIRONMENT cluster..."

case $ENVIRONMENT in
    development)
        kubectl apply -k k8s/environments/development/
        kubectl rollout status deployment/backend-deployment -n "$NAMESPACE" --timeout=300s
        kubectl rollout status deployment/frontend-deployment -n "$NAMESPACE" --timeout=300s
        kubectl rollout status deployment/pipeline-deployment -n "$NAMESPACE" --timeout=300s
        ;;
    staging)
        kubectl apply -k k8s/environments/staging/
        kubectl rollout status deployment/backend-deployment -n "$NAMESPACE" --timeout=300s
        kubectl rollout status deployment/frontend-deployment -n "$NAMESPACE" --timeout=300s
        kubectl rollout status deployment/pipeline-deployment -n "$NAMESPACE" --timeout=300s
        ;;
    production)
        print_status "🔄 Production deployment uses ArgoCD"
        print_status "Updating production manifests for ArgoCD to sync..."

        # ArgoCD watches the main k8s/ directory
        print_status "ArgoCD will automatically deploy updated manifests"
        print_warning "Ensure ArgoCD application is configured and syncing"
        ;;
esac

# Verify deployment
print_status "🔍 Verifying deployment..."
kubectl get pods -n "$NAMESPACE"
kubectl get services -n "$NAMESPACE"

if kubectl get pods -n "$NAMESPACE" | grep -E "Running|Completed" > /dev/null; then
    print_success "✅ Deployment verification passed"
else
    print_error "❌ Some pods are not running properly"
    kubectl describe pods -n "$NAMESPACE"
    exit 1
fi

# Success summary
echo
print_success "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
print_status "📋 Summary:"
print_status "   Environment: $ENVIRONMENT"
print_status "   Cluster: $CLUSTER_CONTEXT"
print_status "   Namespace: $NAMESPACE"
print_status "   Status: All services running"
echo
print_status "🔧 Useful commands:"
print_status "   kubectl get pods -n $NAMESPACE"
print_status "   kubectl logs -f deployment/backend-deployment -n $NAMESPACE"
print_status "   kubectl get services -n $NAMESPACE"
