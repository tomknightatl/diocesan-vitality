#!/bin/bash

# Deploy USCCB Pipeline to Kubernetes
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying Diocesan Vitality Pipeline to Kubernetes${NC}"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed or not in PATH${NC}"
    exit 1
fi

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed or not in PATH${NC}"
    exit 1
fi

# Get GitHub username from environment or prompt
if [ -z "$GITHUB_USERNAME" ]; then
    read -p "Enter your GitHub username: " GITHUB_USERNAME
    export GITHUB_USERNAME
fi

echo -e "${YELLOW}📝 Configuration:${NC}"
echo "Docker Hub Username: $GITHUB_USERNAME"
echo "Container Registry: docker.io/$GITHUB_USERNAME/diocesan-vitality:pipeline"

# Build and push Docker image
echo -e "${BLUE}🔨 Building Docker image...${NC}"
docker build -f Dockerfile.pipeline -t $GITHUB_USERNAME/diocesan-vitality:pipeline .

echo -e "${BLUE}📤 Pushing to Docker Hub...${NC}"
docker push $GITHUB_USERNAME/diocesan-vitality:pipeline

# Update Kubernetes manifests with correct image name
echo -e "${BLUE}🔄 Updating Kubernetes manifests...${NC}"
sed -i.bak "s/tomknightatl\/usccb-pipeline:latest/$GITHUB_USERNAME\/diocesan-vitality:pipeline/g" k8s/pipeline-cronjob.yaml
sed -i.bak "s/tomknightatl\/usccb-pipeline:latest/$GITHUB_USERNAME\/diocesan-vitality:pipeline/g" k8s/pipeline-job.yaml

# Apply Kubernetes resources
echo -e "${BLUE}🎯 Applying Kubernetes resources...${NC}"

# Apply ConfigMap
echo "Applying ConfigMap..."
kubectl apply -f k8s/pipeline-configmap.yaml

# Create namespace if it doesn't exist
kubectl create namespace diocesan-vitality --dry-run=client -o yaml | kubectl apply -f -

# Check if secrets exist, if not, warn user
if ! kubectl get secret diocesan-vitality-secrets -n diocesan-vitality &> /dev/null; then
    echo -e "${YELLOW}⚠️  Secret 'diocesan-vitality-secrets' not found in diocesan-vitality namespace. Please create it manually:${NC}"
    echo "kubectl create secret generic diocesan-vitality-secrets -n diocesan-vitality \\"
    echo "  --from-literal=supabase-url='your-supabase-url' \\"
    echo "  --from-literal=supabase-key='your-supabase-key' \\"
    echo "  --from-literal=genai-api-key='your-genai-key' \\"
    echo "  --from-literal=search-api-key='your-search-key' \\"
    echo "  --from-literal=search-cx='your-search-cx'"
    echo ""
    read -p "Press Enter after creating the secret to continue..."
fi

# Apply CronJob
echo "Applying CronJob..."
kubectl apply -f k8s/pipeline-cronjob.yaml

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${BLUE}📊 Status:${NC}"
kubectl get cronjobs
echo ""
echo -e "${BLUE}💡 Useful commands:${NC}"
echo "• View CronJob: kubectl get cronjobs"
echo "• View Jobs: kubectl get jobs"
echo "• View Pods: kubectl get pods"
echo "• View Logs: kubectl logs -l job-name=diocesan-vitality-pipeline-cronjob-XXXXX"
echo "• Run manual job: kubectl apply -f k8s/pipeline-job.yaml"
echo "• Delete job: kubectl delete job diocesan-vitality-pipeline-job"