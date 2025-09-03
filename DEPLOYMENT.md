# Web Application Deployment Guide

This guide outlines the steps to build, configure, and deploy the web application to a Kubernetes cluster using GitOps principles with ArgoCD.

## Prerequisites

- Docker installed and running.
- `kubectl` installed and configured to access your Kubernetes cluster.
- An account with a container registry (e.g., Docker Hub, Google Container Registry, GitHub Container Registry).
- An Ingress Controller (like NGINX) will be deployed as part of the Kubernetes manifests.

> **Note on Docker Permissions:** On Linux, to run `docker` commands without `sudo`, add your user to the `docker` group by running:
> `sudo usermod -aG docker $USER`
> After this, you must start a new terminal session for the change to take effect.
> **Crucially, once you are in the `docker` group, you should NOT use `sudo` with `docker` commands.** Using `sudo` will cause Docker to run as root, which will prevent it from using the credential helper configured in your user's home directory.

Replace `your-docker-registry/your-repo-name` with your actual registry and repository name.

For authentication instructions with GitHub CLI (gh) and GitHub Container Registry (ghcr.io), please refer to [AUTHENTICATION.md](AUTHENTICATION.md).


## Troubleshooting Docker Permissions and Credential Helper

If you are still encountering issues with Docker permissions or the credential helper, follow these troubleshooting steps:

1.  **Verify Docker Group Membership**:
    Ensure your user account is correctly added to the `docker` group.
    ```sh
    groups
    ```
    You should see `docker` in the output. If not, re-run `sudo usermod -aG docker $USER` and **log out and log back in** (or restart your system) for the changes to take full effect. A new terminal session might not be enough.

2.  **Verify Docker Daemon Status**:
    Ensure the Docker daemon is running.
    ```sh
    sudo systemctl status docker
    ```
    If it's not running or has errors, try restarting it:
    ```sh
    sudo systemctl restart docker
    ```

    # or in Windows Subsystem for Linux (WSL)
    ```sh
    sudo service docker start
    ```


3.  **Verify Credential Helper Configuration**:
    Check your Docker configuration file to ensure the `gh` credential helper is correctly set up.
    ```sh
    cat ~/.docker/config.json
    ```
    You should see an entry like `"credsStore": "gh"` or `"credHelpers": {"ghcr.io": "gh"}`. If not, re-run `gh auth setup-git`.

4.  **Clean up old Docker credentials**:
    As mentioned in the "Docker Registry Login" section, old unencrypted credentials can cause issues. Make sure you have removed any conflicting entries from `~/.docker/config.json`.

5.  **Test Docker Login**:
    After performing the above steps, try logging in again. If the credential helper is working, it should not prompt for a password.
    ```sh
    docker login ghcr.io -u YOUR_USERNAME
    ```
    Replace `YOUR_USERNAME` with your GitHub username.

## Verification Steps

Before proceeding with building and pushing Docker images, it's crucial to verify that you are properly authenticated and have the necessary permissions.

### 1. Verify GitHub CLI (gh) Authentication

To check your GitHub CLI authentication status, run:

```sh
gh auth status
```

This command will show you which GitHub accounts you are logged into and their authentication status. Ensure you are logged in to the correct account.

### 2. Verify Docker and GitHub Container Registry (ghcr.io) Setup

To ensure Docker is running and configured to work with ghcr.io (especially if using `gh` as a credential helper), you can perform the following checks:

*   **Check Docker Daemon Status:**
    ```sh
    sudo systemctl status docker
    ```
    Ensure the Docker daemon is active (running).

*   **Test Docker Login to ghcr.io (if using credential helper):**
    If you have configured `gh` as your Docker credential helper (as recommended in `AUTHENTICATION.md`), you can test your login without providing a password:
    ```sh
    docker login ghcr.io -u YOUR_GITHUB_USERNAME
    ```
    Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username. If successful, this indicates your credential helper is working correctly.

*   **Pull a Public Image (Optional):**
    To further confirm Docker's ability to pull from ghcr.io, you can try pulling a public image (if one is available and known to you). For example:
    ```sh
    docker pull ghcr.io/github/super-linter:latest
    ```
    (Note: Replace `ghcr.io/github/super-linter:latest` with an actual public image from ghcr.io if this one is not suitable or available.)

## Step 1: Build and Push Docker Images

You need to build the Docker images for both the frontend and backend and push them to your container registry.

### Backend

```sh
# Navigate to the backend directory
cd backend

# Build the Docker image
docker build -t ghcr.io/tomknightatl/usccb/usccb-backend:latest .

# Push the image to your registry
docker push ghcr.io/tomknightatl/usccb/usccb-backend:latest
```

### Frontend

```sh
# Navigate to the frontend directory
cd ../frontend

# Build the Docker image
docker build -t ghcr.io/tomknightatl/usccb/usccb-frontend:latest .

# Push the image to your registry
docker push ghcr.io/tomknightatl/usccb/usccb-frontend:latest
```

## Step 2: Create Kubernetes Secret for Supabase

Create a Kubernetes secret to securely store your Supabase URL and service key. This prevents storing sensitive information directly in your Git repository.

Replace the placeholder values with your actual Supabase credentials.

```sh
kubectl create secret generic supabase-credentials \
  --from-literal=SUPABASE_URL='your_supabase_url' \
  --from-literal=SUPABASE_KEY='your_supabase_service_role_key'
```

## Step 2.5: Create Image Pull Secret for GitHub Container Registry (GHCR)

If you are pulling Docker images from a private registry like GitHub Container Registry (`ghcr.io`), Kubernetes needs credentials to authenticate. Create a `docker-registry` type secret using your GHCR credentials. This secret will be referenced by your deployments to pull the images.

Replace the placeholders with your actual GitHub username, Personal Access Token (PAT), and email.

```bash
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=<YOUR_GITHUB_USERNAME> \
  --docker-password=<YOUR_GITHUB_PAT> \
  --docker-email=<YOUR_GITHUB_EMAIL>
```

**Note:** The deployments (`backend-deployment.yaml` and `frontend-deployment.yaml`) have been updated to reference this `ghcr-secret` in their `imagePullSecrets` section.

## Step 3: Review and Update Kubernetes Manifests


The Kubernetes manifests in the `k8s/` directory have been pre-filled with the necessary values based on your previous inputs. However, you should review them and update if these values change in the future.

1.  **`k8s/backend-deployment.yaml`**:
    -   The `spec.template.spec.containers[0].image` is set to your backend image path.
    -   The `envFrom` section is uncommented to use the `supabase-credentials` secret.

2.  **`k8s/frontend-deployment.yaml`**:
    -   The `spec.template.spec.containers[0].image` is set to your frontend image path.

3.  **`k8s/ingress.yaml`**:
    -   The `spec.rules[0].host` is set to `diocesevitality.org`.
    -   Ensure the `kubernetes.io/ingress.class` annotation matches your cluster's Ingress Controller.

After reviewing these files, commit and push them to your Git repository if you made any further changes.

## Step 4: Deploy with ArgoCD ApplicationSet

Instead of manually creating individual ArgoCD Applications, you will deploy an ArgoCD ApplicationSet. This ApplicationSet will automatically create a *single* ArgoCD Application that manages all Kubernetes manifests (Deployments, Services, Ingress, Ingress Controller, etc.) found in the `k8s/` directory of this repository.

1.  **Review the ApplicationSet Manifest**:
    Examine the `k8s/applicationset.yaml` file. Ensure the `repoURL` within the `template.spec.source` section points to your Git repository where these Kubernetes manifests are stored. If you are using a private repository, ensure ArgoCD has the necessary credentials configured.

2.  **Deploy the ApplicationSet**:
    Apply the ApplicationSet manifest to your Kubernetes cluster. This will create the ApplicationSet resource in ArgoCD, which will then automatically create and manage the single ArgoCD Application for your services.

    ```sh
    kubectl apply -f k8s/applicationset.yaml
    ```

Once the ApplicationSet is deployed, ArgoCD will automatically sync the manifests from your `k8s` directory and deploy the frontend and backend to your cluster.

## Step 5: Verify Deployment and Test Application

After deploying the ApplicationSet, you can verify the successful deployment of your application using both the ArgoCD Web UI and `kubectl` commands.

### 1. Verify in ArgoCD Web UI

1.  **Access ArgoCD UI**: Log in to your ArgoCD instance.
2.  **Navigate to Applications**: You should see a new application, likely named `usccb-app` (or whatever name you configured in `applicationset.yaml`).
3.  **Check Status**: Ensure the application shows `Healthy` and `Synced` status. This indicates that all Kubernetes resources defined in your `k8s` directory have been successfully applied to the cluster and are running as expected.
4.  **Inspect Resources**: Click on the application to view its resources (Deployments, Services, Pods, Ingress). Verify that all components are in a healthy state (e.g., Pods are `Running`, Deployments are `Available`).

### 2. Verify with `kubectl` Commands

You can also use `kubectl` to confirm the deployment status directly from your terminal.

*   **Check Deployments**:
    ```bash
    kubectl get deployments -n default
    ```
    You should see `backend-deployment` and `frontend-deployment` listed with desired replicas available.

*   **Check Pods**:
    ```bash
    kubectl get pods -n default
    ```
    Verify that pods for both backend and frontend are `Running`.

*   **Check Services**:
    ```bash
    kubectl get services -n default
    ```
    Confirm that `backend-service` and `frontend-service` are present.

*   **Get Ingress Controller External IP**:
    To find the public IP address of your cluster's Load Balancer, which is managed by the NGINX Ingress Controller, run:
    ```bash
    kubectl get services -n ingress-nginx ingress-nginx-controller
    ```
    Look for the `EXTERNAL-IP` in the output. This is the IP address you will use to configure your DNS records.

*   **Check Ingress**:
    ```bash
    kubectl get ingress -n default
    ```
    Look for `main-ingress` and check its `ADDRESS` column. This should show the external IP address or hostname provided by your Ingress Controller.

*   **Check Ingress Controller Pods**:
    ```bash
    kubectl get pods -n ingress-nginx
    ```
    Verify that the NGINX Ingress Controller pods are running in the `ingress-nginx` namespace.

### 3. Test the Application

Once the Ingress `ADDRESS` is available and you have configured your DNS, you can test your application.

1.  **Configure DNS Records (Example: Cloudflare)**:
    You need to point your domain (`diocesevitality.org`) to the `EXTERNAL-IP` obtained from the Ingress Controller's Load Balancer. Assuming you are using Cloudflare for DNS management:

    *   Log in to your Cloudflare dashboard.
    *   Select your domain (`diocesevitality.org`).
    *   Go to the `DNS` section.
    *   Add a new `A` record:
        *   **Type**: `A`
        *   **Name**: `@` (for the root domain `diocesevitality.org`)
        *   **IPv4 address**: Paste the `EXTERNAL-IP` obtained from `kubectl get services`.
        *   **Proxy status**: `Proxied` (orange cloud) is recommended for Cloudflare's features (CDN, WAF, SSL).
        *   **TTL**: `Auto`
    *   If you want `www.diocesevitality.org` to also work, add another `A` record:
        *   **Type**: `A`
        *   **Name**: `www`
        *   **IPv4 address**: Paste the same `EXTERNAL-IP`.
        *   **Proxy status**: `Proxied`
        *   **TTL**: `Auto`

    Allow some time for DNS changes to propagate (this can take a few minutes to a few hours).

2.  **Get Ingress Host**: The application should be accessible via the domain `diocesevitality.org` that you configured in `k8s/ingress.yaml`.

3.  **Access Frontend**: Open your web browser and navigate to `http://diocesevitality.org/` (or `https://diocesevitality.org/` if you have TLS configured for your Ingress).

4.  **Test Backend API**: You can test the backend API by trying to access an endpoint, for example, `http://diocesevitality.org/api/some-endpoint` (replace `some-endpoint` with an actual API endpoint from your backend).

If you encounter any issues, check the logs of the relevant pods (`kubectl logs <pod-name> -n <namespace>`) and review the events (`kubectl describe pod <pod-name> -n <namespace>`).