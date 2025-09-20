#!/bin/bash

# 🚀 Automated Deployment Script for GitHub Actions
# This script triggers GitHub Actions to build and deploy new images

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "This script must be run from within the diocesan-vitality git repository"
    exit 1
fi

# Check if we're on the main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    print_warning "You're not on the main branch (currently on: $CURRENT_BRANCH)"
    read -p "Do you want to continue? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    print_warning "You have uncommitted changes"
    read -p "Do you want to commit them first? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Please commit your changes and run this script again"
        exit 1
    fi
fi

print_status "🚀 Starting automated deployment process..."

# Option 1: Force build all images
echo
echo "Deployment options:"
echo "1. Auto-deploy (push to main branch - recommended)"
echo "2. Force build all images (manual trigger)"
echo "3. Cancel"
echo

read -p "Choose option [1-3]: " -n 1 -r
echo

case $REPLY in
    1)
        print_status "📤 Pushing to main branch to trigger automatic build..."

        # Ensure we're up to date
        git fetch origin main

        # Push to main branch (this will trigger the GitHub Action)
        if git push origin main; then
            print_success "✅ Code pushed to main branch"
            print_status "🔄 GitHub Actions will automatically:"
            print_status "   • Detect changes in backend/, frontend/, or pipeline files"
            print_status "   • Build multi-architecture Docker images"
            print_status "   • Push images to Docker Hub"
            print_status "   • Update Kubernetes manifests"
            print_status "   • Commit updated manifests back to repository"
            echo
            print_status "📊 Monitor progress at: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git.*/\1/')/actions"
        else
            print_error "❌ Failed to push to main branch"
            exit 1
        fi
        ;;

    2)
        print_status "🔧 Triggering manual build of all images..."

        # Check if GitHub CLI is installed
        if ! command -v gh &> /dev/null; then
            print_error "GitHub CLI (gh) is not installed"
            print_status "Install it with: sudo apt install gh"
            print_status "Or visit: https://cli.github.com/"
            exit 1
        fi

        # Check if authenticated
        if ! gh auth status &> /dev/null; then
            print_error "Not authenticated with GitHub CLI"
            print_status "Run: gh auth login"
            exit 1
        fi

        # Trigger workflow manually
        if gh workflow run docker-build-push.yml -f force_build=true; then
            print_success "✅ Manual build triggered"
            print_status "📊 Monitor progress at: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git.*/\1/')/actions"
        else
            print_error "❌ Failed to trigger manual build"
            exit 1
        fi
        ;;

    3)
        print_status "❌ Deployment cancelled"
        exit 0
        ;;

    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

print_success "🎉 Deployment process initiated!"
echo
print_status "📋 Next steps:"
print_status "   1. Monitor GitHub Actions for build completion"
print_status "   2. ArgoCD will automatically sync the updated manifests"
print_status "   3. Verify deployment in your Kubernetes cluster"
echo
print_status "🔍 Useful commands:"
print_status "   • Watch build: gh run watch"
print_status "   • Check pods: kubectl get pods -n diocesan-vitality"
print_status "   • Check ArgoCD: kubectl get application diocesan-vitality-app -n argocd"
