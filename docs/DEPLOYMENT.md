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

Replace `your-dockerhub-username/your-repo-name` with your actual Docker Hub username and repository name.

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
   - Give it a descriptive name (e.g., "USCCB Deployment")
   - Copy the token and save it securely

3. **Login to Docker Hub**:
   ```bash
   # Using token (recommended)
   docker login -u YOUR_DOCKERHUB_USERNAME
   # Enter your access token when prompted for password
   
   # Or using environment variables from .env
   source .env
   echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin
   ```

4. **Create repositories on Docker Hub** (if using private repos):
   - Go to https://hub.docker.com/repositories
   - Click "Create Repository"
   - Name it `usccb-backend`
   - Choose Public (free) or Private (requires paid plan)
   - Repeat for `usccb-frontend`

## Verification Steps

Before proceeding with building and pushing Docker images, verify that you are properly authenticated:

### 1. Verify Docker Hub Authentication

```bash
# Check if you're logged in
docker info | grep Username
# Should show: Username: YOUR_DOCKERHUB_USERNAME

# Test pulling a public image
docker pull hello-world

# Test pushing (will create a test repo)
docker tag hello-world:latest YOUR_DOCKERHUB_USERNAME/test:latest
docker push YOUR_DOCKERHUB_USERNAME/test:latest
# Clean up
docker rmi YOUR_DOCKERHUB_USERNAME/test:latest
```

## Step 1: Build and Push Docker Images

You need to build the Docker images for both the frontend and backend and push them to Docker Hub.

### Backend

```bash
# Navigate to the backend directory
cd backend

# Build the Docker image
docker build -t YOUR_DOCKERHUB_USERNAME/usccb-backend:latest .

# Push the image to Docker Hub
docker push YOUR_DOCKERHUB_USERNAME/usccb-backend:latest
```

### Frontend

```bash
# Navigate to the frontend directory
cd ../frontend

# Build the Docker image
docker build -t YOUR_DOCKERHUB_USERNAME/usccb-frontend:latest .

# Push the image to Docker Hub
docker push YOUR_DOCKERHUB_USERNAME/usccb-frontend:latest
```

## Step 2: Create Kubernetes Secret for Supabase

Create a Kubernetes secret to securely store your Supabase URL and service key. This prevents storing sensitive information directly in your Git repository.

Replace the placeholder values with your actual Supabase credentials.

```bash
kubectl create secret generic supabase-credentials \
  -n usccb \
  --from-literal=SUPABASE_URL='your_supabase_url' \
  --from-literal=SUPABASE_KEY='your_supabase_service_role_key'
```

## Step 2.5: Create Image Pull Secret for Docker Hub (Only for Private Repositories)

**Note:** This step is only necessary if you're using private Docker Hub repositories. Public repositories don't require authentication to pull images.

If you are using private Docker Hub repositories, create a `docker-registry` type secret:

```bash
kubectl create secret docker-registry dockerhub-secret \
  -n usccb \
  --docker-server=docker.io \
  --docker-username=<YOUR_DOCKERHUB_USERNAME> \
  --docker-password=<YOUR_DOCKERHUB_TOKEN> \
  --docker-email=<YOUR_EMAIL>
```

**Note:** The deployments (`backend-deployment.yaml` and `frontend-deployment.yaml`) have been updated to reference this `dockerhub-secret` in their `imagePullSecrets` section. If using public repositories, you can comment out or remove the `imagePullSecrets` section.

## Step 3: Review and Update Kubernetes Manifests

The Kubernetes manifests in the `k8s/` directory need to be updated with your Docker Hub username:

1. **`k8s/backend-deployment.yaml`**:
   - Update `spec.template.spec.containers[0].image` to: `YOUR_DOCKERHUB_USERNAME/usccb-backend:latest`
   - If using public repos, comment out or remove the `imagePullSecrets` section

2. **`k8s/frontend-deployment.yaml`**:
   - Update `spec.template.spec.containers[0].image` to: `YOUR_DOCKERHUB_USERNAME/usccb-frontend:latest`
   - If using public repos, comment out or remove the `imagePullSecrets` section

3. **`k8s/ingress.yaml`**:
   - The `spec.rules[0].host` is set to `diocesevitality.org`
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
2. **Navigate to Applications**: You should see a new application, likely named `usccb-app` (or whatever name you configured in `applicationset.yaml`).
3. **Check Status**: Ensure the application shows `Healthy` and `Synced` status.
4. **Inspect Resources**: Click on the application to view its resources (Deployments, Services, Pods, Ingress).

### 2. Verify with `kubectl` Commands

```bash
# Check Deployments
kubectl get deployments -n usccb

# Check Pods
kubectl get pods -n usccb

# Check Services
kubectl get services -n usccb

# Get Ingress Controller External IP
kubectl get services -n ingress-nginx ingress-nginx-controller

# Check Ingress
kubectl get ingress -n usccb

# Check Ingress Controller Pods
kubectl get pods -n ingress-nginx
```

### 3. Test the Application

Once the Ingress `ADDRESS` is available and you have configured your DNS:

1. **Configure DNS Records** (Example: Cloudflare):
   - Add an `A` record pointing your domain to the Ingress Controller's External IP

2. **Access Frontend**: Navigate to `http://diocesevitality.org/` (or `https://diocesevitality.org/` if TLS is configured)

3. **Test Backend API**: Access `http://diocesevitality.org/api`

## Troubleshooting

### Docker Hub Issues

1. **Authentication Failed**:
   ```bash
   # Re-login to Docker Hub
   docker logout
   docker login -u YOUR_DOCKERHUB_USERNAME
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
   kubectl describe pod <pod-name> -n usccb
   
   # Verify image pull secret (for private repos)
   kubectl get secret dockerhub-secret -n usccb -o yaml
   ```

### General Deployment Issues

If the application is not working:

1. **Check Pod Logs**:
   ```bash
   kubectl logs <pod-name> -n usccb
   ```

2. **Check Events**:
   ```bash
   kubectl get events -n usccb --sort-by='.lastTimestamp'
   ```

3. **Verify Secrets**:
   ```bash
   kubectl get secrets -n usccb
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