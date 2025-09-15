# Web Application Deployment Guide

This guide outlines the steps to build, configure, and deploy the web application to a Kubernetes cluster using GitOps principles with ArgoCD.

## Prerequisites

- Docker installed and running.
- `kubectl` installed and configured to access your Kubernetes cluster.
- A Docker Hub account (free tier is sufficient for public repositories).
- An Ingress Controller (like NGINX) will be deployed as part of the Kubernetes manifests.

> **Note on Docker Permissions:** On Linux, to run `docker` commands without `sudo`, add your user to the `docker` group by running:
> `sudo usermod -aG docker $USER`
> After this, you must start a new terminal session for the change to take effect.
> **Crucially, once you are in the `docker` group, you should NOT use `sudo` with `docker` commands.** Using `sudo` will cause Docker to run as root, which will prevent it from using the credential helper configured in your user's home directory.

For authentication instructions with Docker Hub, please refer to the Docker Hub Authentication section below.

## Docker Hub Authentication

### Setting up Docker Hub

1. **Create a Docker Hub Account** (if you don't have one):
   - Go to https://hub.docker.com/signup
   - Create a free account

2. **Create Docker Hub Access Token** (recommended over password):
   - Log in to Docker Hub
   - Go to Account Settings → Security
   - Click "New Access Token"
   - Give it a descriptive name (e.g., "Diocesan Vitality Deployment")
   - Copy the token and save it securely

3. **Add Docker Hub credentials to .env file**:
   ```bash
   # Edit your .env file
   nano .env
   
   # Add or update these lines:
   DOCKER_USERNAME=your-dockerhub-username
   DOCKER_PASSWORD=your-dockerhub-access-token
   ```

4. **Login to Docker Hub**:
   ```bash
   # Load environment variables from .env
   source .env
   
   # Login using environment variables
   printf '%s' "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USERNAME" --password-stdin
   ```

5. **Create repository on Docker Hub**:
   - Go to https://hub.docker.com/repositories
   - Click "Create Repository"
   - Name it `diocesan-vitality` (single repository for all images)
   - Choose Public (free) or Private (1 private repo free)
   
   This single repository will hold both images using tags:
   - `diocesan-vitality:backend` for the backend service
   - `diocesan-vitality:frontend` for the frontend service

## Verification Steps

Before proceeding with building and pushing Docker images, verify that you are properly authenticated:

### 1. Verify Docker Hub Authentication

```bash
# Load environment variables
source .env

# Check if you're logged in
docker info | grep Username
# Should show: Username: <your-dockerhub-username>

# Test pulling a public image
docker pull hello-world

# Test pushing (will create a test repo)
docker tag hello-world:latest $DOCKER_USERNAME/test:latest
docker push $DOCKER_USERNAME/test:latest
# Clean up
docker rmi $DOCKER_USERNAME/test:latest
```

## Step 1: Build and Push Docker Images

You need to build the Docker images for both the frontend and backend and push them to Docker Hub.

### Backend

```bash
# Load environment variables
source .env

# Navigate to the backend directory
cd backend

# Build the Docker image with tag
docker build -t $DOCKER_USERNAME/diocesan-vitality:backend .

# Push the backend image to Docker Hub
docker push $DOCKER_USERNAME/diocesan-vitality:backend
```

### Frontend

```bash
# Navigate to the frontend directory
cd ../frontend

# Build the Docker image with tag
docker build -t $DOCKER_USERNAME/diocesan-vitality:frontend .

# Push the frontend image to Docker Hub
docker push $DOCKER_USERNAME/diocesan-vitality:frontend
```

### Pipeline

```bash
# Navigate back to the root directory
cd ..

# Build the Docker image with tag
docker build -f Dockerfile.pipeline -t $DOCKER_USERNAME/diocesan-vitality:pipeline .

# Push the pipeline image to Docker Hub
docker push $DOCKER_USERNAME/diocesan-vitality:pipeline
```

## Step 2: Create Kubernetes Secret for Supabase

Create a Kubernetes secret to securely store your Supabase URL and service key. This prevents storing sensitive information directly in your Git repository.

```bash
# Load environment variables
source .env

# Create secret using environment variables
kubectl create secret generic supabase-credentials \
  -n diocesan-vitality \
  --from-literal=SUPABASE_URL="$SUPABASE_URL" \
  --from-literal=SUPABASE_KEY="$SUPABASE_KEY"
```

## Step 2.5: Create Image Pull Secret for Docker Hub (Only for Private Repositories)

**Note:** This step is only necessary if you're using private Docker Hub repositories. Public repositories don't require authentication to pull images.

If you are using private Docker Hub repositories, create a `docker-registry` type secret:

```bash
# Load environment variables
source .env

# Create image pull secret using environment variables
kubectl create secret docker-registry dockerhub-secret \
  -n diocesan-vitality \
  --docker-server=docker.io \
  --docker-username="$DOCKER_USERNAME" \
  --docker-password="$DOCKER_PASSWORD" \
  --docker-email="your-email@example.com"
```

**Note:** The deployments (`backend-deployment.yaml` and `frontend-deployment.yaml`) have been updated to reference this `dockerhub-secret` in their `imagePullSecrets` section. If using public repositories, you can comment out or remove the `imagePullSecrets` section.

## Step 3: Review and Update Kubernetes Manifests

The Kubernetes manifests in the `k8s/` directory need to be updated with your Docker Hub username from the environment variable:

### Option A: Manual Update
1. **`k8s/backend-deployment.yaml`**:
   - Update `spec.template.spec.containers[0].image` to: `<your-dockerhub-username>/diocesan-vitality:backend`
   - If using public repos, comment out or remove the `imagePullSecrets` section

2. **`k8s/frontend-deployment.yaml`**:
   - Update `spec.template.spec.containers[0].image` to: `<your-dockerhub-username>/diocesan-vitality:frontend`
   - If using public repos, comment out or remove the `imagePullSecrets` section

### Option B: Automated Update Using Environment Variables
```bash
# Load environment variables
source .env

# Update backend deployment with your Docker Hub username
sed -i "s|YOUR_DOCKERHUB_USERNAME|$DOCKER_USERNAME|g" k8s/backend-deployment.yaml

# Update frontend deployment with your Docker Hub username
sed -i "s|YOUR_DOCKERHUB_USERNAME|$DOCKER_USERNAME|g" k8s/frontend-deployment.yaml

# For macOS, use sed -i '' instead:
# sed -i '' "s|YOUR_DOCKERHUB_USERNAME|$DOCKER_USERNAME|g" k8s/backend-deployment.yaml
# sed -i '' "s|YOUR_DOCKERHUB_USERNAME|$DOCKER_USERNAME|g" k8s/frontend-deployment.yaml
```

3. **`k8s/ingress.yaml`**:
   - The `spec.rules[0].host` is set to `diocesanvitality.org`
   - Ensure the `kubernetes.io/ingress.class` annotation matches your cluster's Ingress Controller

After reviewing these files, commit and push them to your Git repository if you made any further changes.

## Step 4: Deploy with ArgoCD ApplicationSet

Instead of manually creating individual ArgoCD Applications, you will deploy an ArgoCD ApplicationSet. This ApplicationSet will automatically create a *single* ArgoCD Application that manages all Kubernetes manifests (Deployments, Services, Ingress, Ingress Controller, etc.) found in the `k8s/` directory of this repository.

1. **Review the ApplicationSet Manifest**:
   Examine the `k8s/applicationset.yaml` file. Ensure the `repoURL` within the `template.spec.source` section points to your Git repository where these Kubernetes manifests are stored. If you are using a private repository, ensure ArgoCD has the necessary credentials configured.

2. **Deploy the ApplicationSet**:
   Apply the ApplicationSet manifest to your Kubernetes cluster. This will create the ApplicationSet resource in ArgoCD, which will then automatically create and manage the single ArgoCD Application for your services.

   ```bash
   kubectl apply -f k8s/applicationset.yaml
   ```

Once the ApplicationSet is deployed, ArgoCD will automatically sync the manifests from your `k8s` directory and deploy the frontend and backend to your cluster.

## Step 5: Verify Deployment and Test Application

After deploying the ApplicationSet, you can verify the successful deployment of your application using both the ArgoCD Web UI and `kubectl` commands.

### 1. Verify in ArgoCD Web UI

1. **Access ArgoCD UI**: Log in to your ArgoCD instance.
2. **Navigate to Applications**: You should see a new application, likely named `diocesan-vitality-app` (or whatever name you configured in `applicationset.yaml`).
3. **Check Status**: Ensure the application shows `Healthy` and `Synced` status.
4. **Inspect Resources**: Click on the application to view its resources (Deployments, Services, Pods, Ingress).

### 2. Verify with `kubectl` Commands

```bash
# Check Deployments
kubectl get deployments -n diocesan-vitality

# Check Pods
kubectl get pods -n diocesan-vitality

# Check Services
kubectl get services -n diocesan-vitality

# Get Ingress Controller External IP
kubectl get services -n ingress-nginx ingress-nginx-controller

# Check Ingress
kubectl get ingress -n diocesan-vitality

# Check Ingress Controller Pods
kubectl get pods -n ingress-nginx
```

### 3. Test the Application

Once the Ingress `ADDRESS` is available and you have configured your DNS:

1. **Configure DNS Records** (Example: Cloudflare):
   - Add an `A` record pointing your domain to the Ingress Controller's External IP

2. **Access Frontend**: Navigate to `http://diocesanvitality.org/` (or `https://diocesanvitality.org/` if TLS is configured)

3. **Test Backend API**: Access `http://diocesanvitality.org/api`

## Troubleshooting

### Docker Hub Issues

1. **Authentication Failed**:
   ```bash
   # Load environment variables and re-login
   source .env
   docker logout
   printf '%s' "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USERNAME" --password-stdin
   ```

2. **Push Denied**:
   - Ensure the repository exists on Docker Hub
   - Check if you have push permissions
   - For private repos, verify your account plan supports the number of private repositories

3. **Rate Limiting**:
   - Docker Hub has pull rate limits for anonymous users (100 pulls per 6 hours)
   - Authenticated users get 200 pulls per 6 hours
   - Consider using a paid plan for higher limits

4. **Image Pull Errors in Kubernetes**:
   ```bash
   # Check pod events
   kubectl describe pod <pod-name> -n diocesan-vitality
   
   # Verify image pull secret (for private repos)
   kubectl get secret dockerhub-secret -n diocesan-vitality -o yaml
   ```

### General Deployment Issues

If the application is not working:

1. **Check Pod Logs**:
   ```bash
   kubectl logs <pod-name> -n diocesan-vitality
   ```

2. **Check Events**:
   ```bash
   kubectl get events -n diocesan-vitality --sort-by='.lastTimestamp'
   ```

3. **Verify Secrets**:
   ```bash
   kubectl get secrets -n diocesan-vitality
   ```

## Quick Deployment Script

For convenience, you can create a deployment script that uses all environment variables:

```bash
#!/bin/bash
# deploy.sh - Complete deployment script

# Load environment variables
source .env

# Login to Docker Hub
printf '%s' "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USERNAME" --password-stdin

# Build and push images
echo "Building and pushing backend..."
cd backend
docker build -t $DOCKER_USERNAME/diocesan-vitality:backend .
docker push $DOCKER_USERNAME/diocesan-vitality:backend

echo "Building and pushing frontend..."
cd ../frontend
docker build -t $DOCKER_USERNAME/diocesan-vitality:frontend .
docker push $DOCKER_USERNAME/diocesan-vitality:frontend

echo "Building and pushing pipeline..."
cd ..
docker build -f Dockerfile.pipeline -t $DOCKER_USERNAME/diocesan-vitality:pipeline .
docker push $DOCKER_USERNAME/diocesan-vitality:pipeline

# Update Kubernetes manifests with Docker Hub username
sed -i "s|YOUR_DOCKERHUB_USERNAME|$DOCKER_USERNAME|g" k8s/backend-deployment.yaml
sed -i "s|YOUR_DOCKERHUB_USERNAME|$DOCKER_USERNAME|g" k8s/frontend-deployment.yaml
sed -i "s|\$DOCKER_USERNAME|$DOCKER_USERNAME|g" k8s/pipeline-cronjob.yaml
sed -i "s|\$DOCKER_USERNAME|$DOCKER_USERNAME|g" k8s/pipeline-job.yaml

# Create Kubernetes secrets
kubectl create namespace diocesan-vitality --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic supabase-credentials \
  -n diocesan-vitality \
  --from-literal=SUPABASE_URL="$SUPABASE_URL" \
  --from-literal=SUPABASE_KEY="$SUPABASE_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

# Create image pull secret if using private repository
kubectl create secret docker-registry dockerhub-secret \
  -n diocesan-vitality \
  --docker-server=docker.io \
  --docker-username="$DOCKER_USERNAME" \
  --docker-password="$DOCKER_PASSWORD" \
  --docker-email="your-email@example.com" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Deployment preparation complete!"
echo "Now commit and push your changes to Git, then apply the ArgoCD ApplicationSet."
```

## Docker Hub vs GitHub Container Registry

### Advantages of Docker Hub:
- **Simpler authentication** - standard Docker login
- **No GitHub dependency** - works independently
- **Free public repositories** - unlimited for public images
- **Wide compatibility** - supported by all Kubernetes distributions
- **Familiar workflow** - most developers know Docker Hub

### Disadvantages:
- **Rate limits** on pulls (even for public repos)
- **Limited private repositories** on free tier (1 private repo)
- **No integration** with GitHub Actions (requires separate auth)

### Migration Notes:
When migrating from GHCR to Docker Hub:
1. Image paths change from `ghcr.io/username/repo` to `username/repo` or `docker.io/username/repo`
2. Authentication uses Docker Hub credentials instead of GitHub PAT
3. Secret type remains `docker-registry` but server changes to `docker.io`
4. Public repositories don't require image pull secrets