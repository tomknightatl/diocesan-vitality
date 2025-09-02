# Web Application Deployment Guide

This guide outlines the steps to build, configure, and deploy the web application to a Kubernetes cluster using GitOps principles with ArgoCD.

## Prerequisites

- Docker installed and running.
- `kubectl` installed and configured to access your Kubernetes cluster.
- An account with a container registry (e.g., Docker Hub, Google Container Registry, GitHub Container Registry).
- An Ingress Controller (like NGINX) running in your cluster.

> **Note on Docker Permissions:** On Linux, to run `docker` commands without `sudo`, add your user to the `docker` group by running:
> `sudo usermod -aG docker $USER`
> After this, you must start a new terminal session for the change to take effect.

Replace `your-docker-registry/your-repo-name` with your actual registry and repository name.

## Docker Registry Login

Before building and pushing images, you need to log in to your Docker registry. For GitHub Container Registry (`ghcr.io`), follow these steps:

1.  **Create GitHub Personal Access Tokens (PATs)**:
You will need two types of PATs:
    *   **For `gh auth login` (to configure the credential helper)**:
        *   Go to your GitHub settings: `Settings` > `Developer settings` > `Personal access tokens` > `Tokens (classic)` > `Generate new token (classic)`.
        *   Give your token a descriptive name (e.g., `gh_cli_auth_token`).
        *   **Crucially**, select the following scopes: `repo`, `read:org`, and `workflow`. These permissions are required for the GitHub CLI to interact with your GitHub account and set up the credential helper.
        *   Generate the token and copy it immediately. You won't be able to see it again.
    *   **For pushing to `ghcr.io` (if not using `gh` as credential helper, or for direct `docker login` with PAT)**:
        *   Go to your GitHub settings: `Settings` > `Developer settings` > `Personal access tokens` > `Tokens (classic)` > `Generate new token (classic)`.
        *   Give your token a descriptive name (e.g., `ghcr_push_token`).
        *   **Crucially**, select the `write:packages` scope. This permission is required to push images to GitHub Container Registry.
        *   Generate the token and copy it immediately. You won't be able to see it again.

2.  **Install and Configure Docker Credential Helper (Recommended)**:
    To avoid storing credentials unencrypted and to securely manage your GitHub Container Registry login, use the GitHub CLI (`gh`) as a Docker credential helper.

    *   **Install GitHub CLI (`gh`)**:
        Follow the official installation instructions for your operating system: [https://github.com/cli/cli#installation](https://github.com/cli/cli#installation)
        For Debian/Ubuntu, you can typically use:
        ```sh
        type -p curl >/dev/null || sudo apt update && sudo apt install curl -y
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
        && sudo chmod go+rb /usr/share/keyrings/githubcli-archive-keyring.gpg \
        && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
        && sudo apt update \
        && sudo apt install gh -y
        ```
    *   **Configure `gh` as Docker Credential Helper**:
        After installing `gh`, configure it to handle Docker authentication for `ghcr.io`. When prompted, use the PAT you created for `gh auth login` (with `repo`, `read:org`, `workflow` scopes).
        ```sh
        gh auth login -h ghcr.io -p https
        ```
        Follow the prompts to authenticate with your GitHub account. This will set up `gh` to manage your Docker credentials for `ghcr.io` securely.

3.  **Log in to GitHub Container Registry**:
    Once the credential helper is configured, you can log in using your GitHub username. The credential helper will securely provide the necessary token.

    ```sh
    docker login ghcr.io -u YOUR_USERNAME
    ```
    Replace `YOUR_USERNAME` with your GitHub username. The `gh` credential helper will handle the PAT.

    If you prefer to use a PAT directly without the credential helper (not recommended for security), use the `ghcr_push_token` you created:
    ```sh
    echo YOUR_GHCR_PUSH_PAT | docker login ghcr.io -u YOUR_USERNAME --password-stdin
    ```
    Replace `YOUR_GHCR_PUSH_PAT` with the Personal Access Token that has `write:packages` scope, and `YOUR_USERNAME` with your GitHub username.


## Step 1: Build and Push Docker Images

You need to build the Docker images for both the frontend and backend and push them to your container registry.

### Backend

```sh
# Navigate to the backend directory
cd backend

# Build the Docker image
sudo docker build -t ghcr.io/tomknightatl/usccb/usccb-backend:latest .

# Push the image to your registry
sudo docker push ghcr.io/tomknightatl/usccb/usccb-backend:latest
```

### Frontend

```sh
# Navigate to the frontend directory
cd frontend

# Build the Docker image
sudo docker build -t ghcr.io/tomknightatl/usccb/usccb-frontend:latest .

# Push the image to your registry
sudo docker push ghcr.io/tomknightatl/usccb/usccb-frontend:latest
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