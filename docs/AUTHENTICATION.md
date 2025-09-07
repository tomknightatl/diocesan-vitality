# Authentication Instructions

This document provides comprehensive instructions for authenticating with GitHub (for git operations) and Docker Hub (for container registry operations).

## Prerequisites

- Git installed on your system
- Docker installed and running
- GitHub CLI (`gh`) installed ([installation guide](https://github.com/cli/cli#installation)) - for GitHub operations
- Docker Hub account (free at [hub.docker.com](https://hub.docker.com))

## Part 1: GitHub Authentication (for Git Operations)

### Step 1: Create a GitHub Personal Access Token (PAT)

Create a PAT for git operations and GitHub CLI.

#### 1.1 Navigate to GitHub Settings

1. Log in to your GitHub account
2. Click your profile picture → **Settings**
3. Scroll down to **Developer settings** (left sidebar)
4. Click **Personal access tokens** → **Tokens (classic)**
5. Click **Generate new token** → **Generate new token (classic)**

#### 1.2 Configure Token Permissions

**Token Name:** Give it a descriptive name like `usccb-project-token`

**Expiration:** Choose an appropriate expiration (90 days recommended for security)

**Select Scopes:** Check the following permissions:

For Git Operations:
- ✅ **repo** (Full control of private repositories)
- ✅ **workflow** (Update GitHub Action workflows)
- ✅ **admin:org** (if working with organizations)

#### 1.3 Generate and Save Token

1. Click **Generate token**
2. **IMPORTANT:** Copy the token immediately (it won't be shown again)
3. Store it temporarily in a secure location until you save it in `.env`

### Step 2: Configure GitHub CLI

```bash
# Set up environment variables
export GH_TOKEN=ghp_YourActualTokenHere
export GITHUB_TOKEN=ghp_YourActualTokenHere
export GITHUB_USERNAME=your-github-username

# Authenticate gh CLI
echo $GH_TOKEN | gh auth login --with-token

# Configure git to use gh as credential helper
gh auth setup-git

# Configure git identity
git config --global user.email "your-email@example.com"
git config --global user.name "Your Name"
```

### Step 3: Test GitHub Authentication

```bash
# Check gh auth status
gh auth status

# Test git operations
git clone https://github.com/your-username/private-repo.git test-clone
cd test-clone
echo "# Test" > README.md
git add README.md
git commit -m "Test authentication"
git push origin main
```

## Part 2: Docker Hub Authentication (for Container Registry)

### Step 1: Create Docker Hub Account and Access Token

#### 1.1 Create Account (if needed)
1. Go to [hub.docker.com/signup](https://hub.docker.com/signup)
2. Create a free account

#### 1.2 Create Access Token (Recommended over password)
1. Log in to Docker Hub
2. Go to **Account Settings** → **Security**
3. Click **New Access Token**
4. Give it a descriptive name (e.g., "USCCB Deployment")
5. Select access permissions (Read, Write, Delete - or just Read & Write)
6. Click **Generate**
7. **IMPORTANT:** Copy the token immediately (it won't be shown again)

### Step 2: Configure Docker Authentication

#### Option A: Simple Login (Interactive)
```bash
# Login with username (will prompt for password/token)
docker login -u YOUR_DOCKERHUB_USERNAME
# Enter your access token when prompted for password
```

#### Option B: Non-Interactive Login (Using Environment Variables)
```bash
# Export credentials
export DOCKER_USERNAME=your-dockerhub-username
export DOCKER_PASSWORD=your-dockerhub-token

# Login using environment variables
echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin
```

#### Option C: Using Docker Credential Helper (Most Secure)

**For Linux:**
```bash
# Install pass and docker-credential-pass
sudo apt-get install -y pass
wget https://github.com/docker/docker-credential-helpers/releases/download/v0.7.0/docker-credential-pass-v0.7.0.linux-amd64
chmod +x docker-credential-pass-v0.7.0.linux-amd64
sudo mv docker-credential-pass-v0.7.0.linux-amd64 /usr/local/bin/docker-credential-pass

# Initialize pass (requires GPG key)
pass init "your-gpg-key-id"

# Configure Docker to use pass
echo '{"credsStore": "pass"}' > ~/.docker/config.json

# Login (credentials will be stored securely)
docker login -u YOUR_DOCKERHUB_USERNAME
```

**For macOS:**
```bash
# Docker Desktop for Mac includes osxkeychain helper by default
echo '{"credsStore": "osxkeychain"}' > ~/.docker/config.json
docker login -u YOUR_DOCKERHUB_USERNAME
```

**For Windows:**
```bash
# Docker Desktop for Windows includes wincred helper by default
echo '{"credsStore": "wincred"}' > ~/.docker/config.json
docker login -u YOUR_DOCKERHUB_USERNAME
```

### Step 3: Create Docker Hub Repositories

1. Log in to [hub.docker.com](https://hub.docker.com)
2. Click **Repositories** → **Create Repository**
3. Create repositories for your project:
   - Repository name: `usccb-backend`
   - Description: "USCCB Backend API"
   - Visibility: **Public** (free) or **Private** (requires paid plan)
4. Repeat for `usccb-frontend`

### Step 4: Test Docker Hub Authentication

```bash
# Verify you're logged in
docker info | grep Username
# Should show: Username: YOUR_DOCKERHUB_USERNAME

# Test pulling a public image
docker pull hello-world

# Test pushing (creates a test repo)
docker tag hello-world:latest YOUR_DOCKERHUB_USERNAME/test:latest
docker push YOUR_DOCKERHUB_USERNAME/test:latest

# Clean up test image
docker rmi YOUR_DOCKERHUB_USERNAME/test:latest

# Delete test repository from Docker Hub web interface if desired
```

## Part 3: Save Credentials in .env File

### Create or Update .env File

In the root directory of your project, create or edit the `.env` file:

```bash
# Navigate to your project root
cd /path/to/your/project

# Create or edit .env file
nano .env  # or use your preferred editor
```

Add the following lines:

```bash
# GitHub Credentials (for git operations)
GH_TOKEN=ghp_YourGitHubTokenHere
GITHUB_TOKEN=ghp_YourGitHubTokenHere
GITHUB_USERNAME=your-github-username

# Docker Hub Credentials (for container registry)
DOCKER_USERNAME=your-dockerhub-username
DOCKER_PASSWORD=your-dockerhub-access-token

# Other project credentials
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
GENAI_API_KEY_USCCB=your_google_genai_api_key_here
SEARCH_API_KEY_USCCB=your_google_search_api_key_here
SEARCH_CX_USCCB=your_google_search_engine_id_here
```

### Secure the .env File

```bash
# Ensure .env is in .gitignore
echo ".env" >> .gitignore

# Set restrictive permissions (Unix/Linux/macOS)
chmod 600 .env
```

### Load Environment Variables

```bash
# Load environment variables from .env file
export $(cat .env | grep -v '^#' | xargs)

# Verify variables are loaded
echo $DOCKER_USERNAME  # Should show your Docker Hub username
echo $GITHUB_USERNAME  # Should show your GitHub username
```

## Part 4: Kubernetes Secrets for Container Registry

If using private Docker Hub repositories in Kubernetes, create an image pull secret:

```bash
kubectl create secret docker-registry dockerhub-secret \
  --docker-server=docker.io \
  --docker-username=YOUR_DOCKERHUB_USERNAME \
  --docker-password=YOUR_DOCKERHUB_TOKEN \
  --docker-email=YOUR_EMAIL \
  --namespace=usccb
```

Then reference it in your deployments:

```yaml
spec:
  imagePullSecrets:
  - name: dockerhub-secret
```

**Note:** Public Docker Hub repositories don't require image pull secrets.

## Troubleshooting

### Docker Hub Issues

#### 1. "unauthorized: incorrect username or password"
```bash
# Logout and login again
docker logout
docker login -u YOUR_DOCKERHUB_USERNAME
```

#### 2. "denied: requested access to the resource is denied"
- Ensure the repository exists on Docker Hub
- Check if you're using the correct username
- Verify you have push permissions to the repository

#### 3. Rate Limiting
Docker Hub has rate limits:
- **Anonymous users**: 100 pulls per 6 hours per IP
- **Authenticated users (free)**: 200 pulls per 6 hours
- **Paid users**: Higher or unlimited based on plan

To avoid rate limits:
```bash
# Always authenticate before pulling
docker login -u YOUR_DOCKERHUB_USERNAME
```

#### 4. Token vs Password
- Docker Hub access tokens are more secure than passwords
- Tokens can be revoked without changing your password
- Tokens can have limited permissions

### GitHub Issues

#### 1. "Bad credentials" error
```bash
# Clear cached credentials and re-authenticate
git config --global --unset credential.helper
gh auth setup-git
```

#### 2. Token Permissions
Ensure your GitHub PAT has the required scopes:
- `repo` for private repository access
- `workflow` for GitHub Actions
- `write:packages` if using GitHub Packages

## Security Best Practices

1. **Use Access Tokens Instead of Passwords**
   - GitHub: Use Personal Access Tokens
   - Docker Hub: Use Access Tokens

2. **Rotate Tokens Regularly**
   - Set expiration dates on tokens
   - Rotate every 90 days

3. **Use Minimal Required Permissions**
   - Only grant necessary scopes/permissions
   - Use read-only tokens where possible

4. **Never Commit Credentials**
   - Always use `.env` files
   - Ensure `.env` is in `.gitignore`

5. **Use Credential Helpers**
   - Avoid storing credentials in plain text
   - Use system keychains/credential stores

6. **Different Tokens for Different Purposes**
   - Separate tokens for CI/CD
   - Separate tokens for development/production

## Quick Reference

### Complete Setup Script
```bash
#!/bin/bash
# Load environment variables
source .env

# GitHub setup
echo $GH_TOKEN | gh auth login --with-token
gh auth setup-git

# Docker Hub setup
echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin

# Verify authentication
gh auth status
docker info | grep Username

echo "Authentication setup complete!"
```

## Additional Resources

- [Docker Hub Documentation](https://docs.docker.com/docker-hub/)
- [Docker Hub Access Tokens](https://docs.docker.com/docker-hub/access-tokens/)
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [Docker Credential Helpers](https://github.com/docker/docker-credential-helpers)