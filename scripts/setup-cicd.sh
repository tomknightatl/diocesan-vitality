#!/bin/bash
# CI/CD Setup Script for USCCB Project
# This script automates the initial setup of CI/CD pipeline

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== USCCB CI/CD Setup Script ===${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file with your credentials first."
    echo "Required variables:"
    echo "  DOCKER_USERNAME=your-dockerhub-username"
    echo "  DOCKER_PASSWORD=your-dockerhub-token"
    exit 1
fi

# Load environment variables
echo -e "${YELLOW}Loading environment variables...${NC}"
source .env

# Check required variables
if [ -z "$DOCKER_USERNAME" ] || [ -z "$DOCKER_PASSWORD" ]; then
    echo -e "${RED}Error: DOCKER_USERNAME or DOCKER_PASSWORD not set in .env file${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Environment variables loaded${NC}"

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check GitHub CLI authentication
echo -e "${YELLOW}Checking GitHub CLI authentication...${NC}"
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI is not authenticated${NC}"
    echo "Please run: gh auth login"
    exit 1
fi
echo -e "${GREEN}✓ GitHub CLI authenticated${NC}"

# Test Docker Hub credentials
echo -e "${YELLOW}Testing Docker Hub credentials...${NC}"
if echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin &> /dev/null; then
    echo -e "${GREEN}✓ Docker Hub login successful${NC}"
else
    echo -e "${RED}Error: Docker Hub login failed${NC}"
    echo "Please check your DOCKER_USERNAME and DOCKER_PASSWORD in .env"
    exit 1
fi

# Create GitHub secrets
echo -e "${YELLOW}Setting up GitHub repository secrets...${NC}"

gh secret set DOCKER_USERNAME --body "$DOCKER_USERNAME" 2>/dev/null && \
    echo -e "${GREEN}✓ DOCKER_USERNAME secret created/updated${NC}" || \
    echo -e "${YELLOW}! DOCKER_USERNAME secret may already exist${NC}"

gh secret set DOCKER_PASSWORD --body "$DOCKER_PASSWORD" 2>/dev/null && \
    echo -e "${GREEN}✓ DOCKER_PASSWORD secret created/updated${NC}" || \
    echo -e "${YELLOW}! DOCKER_PASSWORD secret may already exist${NC}"

# Create develop branch if it doesn't exist
echo -e "${YELLOW}Checking for develop branch...${NC}"
if git show-ref --verify --quiet refs/heads/develop; then
    echo -e "${GREEN}✓ Develop branch exists${NC}"
else
    echo -e "${YELLOW}Creating develop branch...${NC}"
    git checkout -b develop
    git push -u origin develop
    echo -e "${GREEN}✓ Develop branch created${NC}"
    git checkout main  # Switch back to main
fi

# Check if kubectl is configured
if command -v kubectl &> /dev/null; then
    echo -e "${YELLOW}Checking Kubernetes connection...${NC}"
    if kubectl cluster-info &> /dev/null; then
        echo -e "${GREEN}✓ Kubernetes cluster connected${NC}"
        
        # Check if ArgoCD is installed
        if kubectl get namespace argocd &> /dev/null; then
            echo -e "${GREEN}✓ ArgoCD namespace found${NC}"
            
            # Ask if user wants to deploy ArgoCD application
            echo ""
            read -p "Do you want to deploy the ArgoCD application for dev environment? (y/N) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                kubectl apply -f k8s/argocd/usccb-app-dev.yaml
                echo -e "${GREEN}✓ ArgoCD application deployed${NC}"
            fi
        else
            echo -e "${YELLOW}! ArgoCD namespace not found. Please install ArgoCD first.${NC}"
        fi
    else
        echo -e "${YELLOW}! Kubernetes cluster not accessible${NC}"
    fi
else
    echo -e "${YELLOW}! kubectl not found. Skipping Kubernetes setup.${NC}"
fi

# Create necessary directories
echo -e "${YELLOW}Creating required directories...${NC}"
mkdir -p .github/workflows
mkdir -p k8s/argocd
mkdir -p scripts
echo -e "${GREEN}✓ Directories created${NC}"

# Summary
echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Commit and push the CI/CD configuration files:"
echo "   git add ."
echo "   git commit -m 'feat: add CI/CD pipeline'"
echo "   git push origin main"
echo ""
echo "2. Make a test change and push to develop branch:"
echo "   git checkout develop"
echo "   # make changes"
echo "   git add ."
echo "   git commit -m 'test: CI/CD pipeline'"
echo "   git push origin develop"
echo ""
echo "3. Monitor the pipeline:"
echo "   gh run list"
echo "   gh run watch"
echo ""
echo "4. Check ArgoCD for deployments (if configured):"
echo "   kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "   # Open https://localhost:8080"
echo ""
echo -e "${GREEN}Happy deploying! 🚀${NC}"