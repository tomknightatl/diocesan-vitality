# Web Application Deployment Guide

This guide outlines the steps to build, configure, and deploy the web application to a Kubernetes cluster using GitOps principles with ArgoCD.

## Prerequisites

- Docker installed and running.
- `kubectl` installed and configured to access your Kubernetes cluster.
- An account with a container registry (e.g., Docker Hub, Google Container Registry, GitHub Container Registry).
- An Ingress Controller (like NGINX) running in your cluster.
- ArgoCD installed in your cluster.

## Step 1: Build and Push Docker Images

You need to build the Docker images for both the frontend and backend and push them to your container registry.

Replace `your-docker-registry/your-repo-name` with your actual registry and repository name.

### Backend

```sh
# Navigate to the backend directory
cd backend

# Build the Docker image
docker build -t your-docker-registry/your-repo-name/usccb-backend:latest .

# Push the image to your registry
docker push your-docker-registry/your-repo-name/usccb-backend:latest
```

### Frontend

```sh
# Navigate to the frontend directory
cd frontend

# Build the Docker image
docker build -t your-docker-registry/your-repo-name/usccb-frontend:latest .

# Push the image to your registry
docker push your-docker-registry/your-repo-name/usccb-frontend:latest
```

## Step 2: Create Kubernetes Secret for Supabase

Create a Kubernetes secret to securely store your Supabase URL and service key. This prevents storing sensitive information directly in your Git repository.

Replace the placeholder values with your actual Supabase credentials.

```sh
kubectl create secret generic supabase-credentials \
  --from-literal=SUPABASE_URL='your_supabase_url' \
  --from-literal=SUPABASE_KEY='your_supabase_service_role_key'
```

## Step 3: Update Kubernetes Manifests

The Kubernetes manifests in the `k8s/` directory contain placeholder values that you must update.

1.  **`k8s/backend-deployment.yaml`**:
    -   Update the `spec.template.spec.containers[0].image` to the backend image path you pushed in Step 1.
    -   Uncomment the `envFrom` section to use the `supabase-credentials` secret you created.

2.  **`k8s/frontend-deployment.yaml`**:
    -   Update the `spec.template.spec.containers[0].image` to the frontend image path you pushed in Step 1.

3.  **`k8s/ingress.yaml`**:
    -   Update the `spec.rules[0].host` to the domain where you want to host the application (e.g., `usccb.your-domain.com`).
    -   Ensure the `kubernetes.io/ingress.class` annotation matches your cluster's Ingress Controller.

After updating these files, commit and push them to your Git repository.

## Step 4: Deploy with ArgoCD

Create a new Application in ArgoCD to manage the deployment.

-   **General Settings**:
    -   **Application Name**: `usccb-webapp` (or your preferred name)
    -   **Project**: `default` (or your preferred project)
    -   **Sync Policy**: `Automatic` (with pruning and self-healing enabled for a full GitOps experience)
-   **Source**:
    -   **Repository URL**: The URL of your Git repository.
    -   **Revision**: `HEAD` (or the branch you are using).
    -   **Path**: `k8s`
-   **Destination**:
    -   **Cluster URL**: `https://kubernetes.default.svc` (or the target cluster).
    -   **Namespace**: `default` (or the target namespace where you created the secret).

Once you create the application, ArgoCD will automatically sync the manifests from your `k8s` directory and deploy the frontend and backend to your cluster.

