# Authentication Instructions

This document provides comprehensive instructions for authenticating with GitHub (for git operations) and GitHub Container Registry (ghcr.io) using a single Personal Access Token (PAT) stored securely in your `.env` file.

## Prerequisites

- Git installed on your system
- Docker installed and running
- GitHub CLI (`gh`) installed ([installation guide](https://github.com/cli/cli#installation))

## Step 1: Create a GitHub Personal Access Token (PAT)

Create a single PAT with all necessary permissions for both git and docker operations.

### 1.1 Navigate to GitHub Settings

1. Log in to your GitHub account
2. Click your profile picture → **Settings**
3. Scroll down to **Developer settings** (left sidebar)
4. Click **Personal access tokens** → **Tokens (classic)**
5. Click **Generate new token** → **Generate new token (classic)**

### 1.2 Configure Token Permissions

**Token Name:** Give it a descriptive name like `usccb-project-token`

**Expiration:** Choose an appropriate expiration (90 days recommended for security)

**Select Scopes:** Check the following permissions:

#### For Git Operations:
- ✅ **repo** (Full control of private repositories)
  - This includes all sub-permissions for repository access

#### For GitHub Container Registry:
- ✅ **write:packages** (Upload packages to GitHub Package Registry)
- ✅ **read:packages** (Download packages from GitHub Package Registry)
- ✅ **delete:packages** (Delete packages from GitHub Package Registry)

#### For GitHub CLI:
- ✅ **workflow** (Update GitHub Action workflows)
- ✅ **admin:org** (Full control of orgs and teams, read and write org projects) - *if working with organizations*

### 1.3 Generate and Save Token

1. Click **Generate token**
2. **IMPORTANT:** Copy the token immediately (it won't be shown again)
3. Store it temporarily in a secure location until you save it in `.env`

## Step 2: Save PAT in .env File

### 2.1 Create or Update .env File

In the root directory of your project, create or edit the `.env` file:

```bash
# Navigate to your project root
cd /path/to/your/project

# Create or edit .env file
nano .env  # or use your preferred editor
```

### 2.2 Add Token to .env

Add the following lines to your `.env` file:

```bash
# GitHub Personal Access Token
# Note: GH_TOKEN and GITHUB_TOKEN should have the same value (your PAT)
# Some tools use GH_TOKEN, others use GITHUB_TOKEN, so we set both
GH_TOKEN=ghp_YourActualTokenHere
GITHUB_TOKEN=ghp_YourActualTokenHere

# GitHub Username
# Note: When using GitHub Container Registry (ghcr.io), DOCKER_USERNAME 
# is always the same as your GITHUB_USERNAME
GITHUB_USERNAME=your-github-username
DOCKER_USERNAME=your-github-username
```

Replace:
- `ghp_YourActualTokenHere` with your actual PAT (use the same token for both GH_TOKEN and GITHUB_TOKEN)
- `your-github-username` with your GitHub username (use the same username for both GITHUB_USERNAME and DOCKER_USERNAME)

### 2.3 Secure the .env File

```bash
# Ensure .env is in .gitignore
echo ".env" >> .gitignore

# Set restrictive permissions (Unix/Linux/macOS)
chmod 600 .env
```

## Step 3: Load Environment Variables

Before running authentication commands, load your environment variables:

```bash
# Load environment variables from .env file
export $(cat .env | grep -v '^#' | xargs)

# Verify variables are loaded
echo $GH_TOKEN | cut -c1-10  # Should show first 10 characters of token
echo $GITHUB_USERNAME         # Should show your username
```

**For permanent loading**, add this to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
# Auto-load project .env file
if [ -f "/path/to/your/project/.env" ]; then
    export $(cat /path/to/your/project/.env | grep -v '^#' | xargs)
fi
```

## Step 4: Authenticate with GitHub CLI

### 4.1 Configure GitHub CLI with Token

```bash
# Authenticate gh CLI using token from environment
echo $GH_TOKEN | gh auth login --with-token

# Expected output:
# The value of the GH_TOKEN environment variable is being used for authentication.
# To have GitHub CLI store credentials instead, first clear the value from the environment.
```

**Note:** This message is informational, not an error. It's telling you that gh is using the token from your environment variable, which is exactly what we want.

### 4.2 Configure Git Credential Helper

Set up GitHub CLI as your git credential helper:

```bash
# Configure git to use gh as credential helper
gh auth setup-git
```

Configure git with your identity:

```bash
# Configure git with your identity
git config --global user.email "your-email@example.com"
git config --global user.name "Your Name"
```

## Step 5: Configure Docker for GitHub Container Registry

### 5.1 Clean Docker Configuration

Before attempting to login, we need to ensure Docker doesn't have conflicting credential helper configurations:

```bash
# Check if Docker config exists and back it up
if [ -f ~/.docker/config.json ]; then
    echo "Docker config found, backing up..."
    cp ~/.docker/config.json ~/.docker/config.json.backup
    echo "Backed up existing config to ~/.docker/config.json.backup"
else
    echo "No existing Docker config found"
fi

# Create clean Docker config
mkdir -p ~/.docker
echo '{}' > ~/.docker/config.json
echo "Docker config cleaned and ready"
```

### 5.2 Configure Credential Storage (Choose One Option)

To avoid storing credentials unencrypted, configure a credential helper for your operating system BEFORE logging in:

#### Option A: Simple Setup (Unencrypted - OK for Development)

If you're just developing locally and don't mind the security warning:

```bash
# Keep the clean config - credentials will be stored base64 encoded
echo "Using basic credential storage (base64 encoded)"
```

#### Option B: Encrypted Storage for Linux

```bash
# Install pass and gpg2
sudo apt-get install -y pass gnupg2

# Generate a GPG key (if you don't have one)
gpg2 --gen-key
# Follow the prompts to create your key

# Initialize pass with your GPG key email/ID
pass init "your-email@example.com"

# Download and install docker-credential-pass
VERSION=$(curl -s https://api.github.com/repos/docker/docker-credential-helpers/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
wget https://github.com/docker/docker-credential-helpers/releases/download/v${VERSION}/docker-credential-pass-v${VERSION}.linux-amd64
chmod +x docker-credential-pass-v${VERSION}.linux-amd64
sudo mv docker-credential-pass-v${VERSION}.linux-amd64 /usr/local/bin/docker-credential-pass

# Configure Docker to use pass
echo '{"credsStore": "pass"}' > ~/.docker/config.json
echo "Docker configured to use encrypted pass storage"
```

#### Option C: Encrypted Storage for macOS

```bash
# Configure Docker to use macOS keychain
echo '{"credsStore": "osxkeychain"}' > ~/.docker/config.json
echo "Docker configured to use macOS keychain"
```

#### Option D: Encrypted Storage for Windows (WSL2)

```bash
# For WSL2, use the Linux instructions above (Option B)
# For native Windows, use Windows Credential Manager:
echo '{"credsStore": "wincred"}' > ~/.docker/config.json
echo "Docker configured to use Windows Credential Manager"
```

### 5.3 Login to GitHub Container Registry

Now login to ghcr.io. The output will vary depending on your credential storage choice:

```bash
# Login to GitHub Container Registry using token from environment
echo $GH_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# Expected output (varies by storage method):
# 
# If using Option A (unencrypted):
# WARNING! Your credentials are stored unencrypted in '/home/[username]/.docker/config.json'.
# Configure a credential helper to remove this warning. See
# https://docs.docker.com/go/credential-store/
# Login Succeeded
#
# If using Options B, C, or D (encrypted):
# Login Succeeded
```

**Note:** If you chose Option A and see the warning, that's expected for development environments. Your credentials are stored base64-encoded (not plain text) but not encrypted. For production use, consider using one of the encrypted options.

## Step 6: Test Authentication

### 6.1 Test GitHub CLI Authentication

```bash
# Check gh auth status
gh auth status

# Expected output:
# ✓ Logged in to github.com as your-username
# ✓ Git operations for github.com configured to use https protocol
# ✓ Token: ghp_****...
```

### 6.2 Test Git Operations

```bash
# Clone a private repository (if you have one)
git clone https://github.com/your-username/private-repo.git test-clone

# Or create a test repository
gh repo create test-auth-repo --private --clone

# Make a test commit
cd test-auth-repo
echo "# Test" > README.md
git add README.md
git commit -m "Test authentication"
git push origin main

# Clean up test repo (optional)
gh repo delete test-auth-repo --yes
cd ..
rm -rf test-auth-repo
```

### 6.3 Test Docker/GHCR Authentication

```bash
# Verify you're logged in to ghcr.io
echo $GH_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
# Should show: Login Succeeded

# Test by pushing your own image (the real test of authentication)
# Pull a small image from Docker Hub as our test base
docker pull alpine:latest

# Tag it for your ghcr.io namespace
docker tag alpine:latest ghcr.io/$GITHUB_USERNAME/test-auth:latest

# Push to ghcr.io (this tests write access)
docker push ghcr.io/$GITHUB_USERNAME/test-auth:latest
echo "✓ Image successfully pushed to ghcr.io/$GITHUB_USERNAME/test-auth:latest"

# Test pulling your own image (this tests read access)
docker rmi ghcr.io/$GITHUB_USERNAME/test-auth:latest
docker pull ghcr.io/$GITHUB_USERNAME/test-auth:latest
echo "✓ Successfully pulled your image from ghcr.io"

# Optional: Make your test image public for others
echo "To make this image public, visit:"
echo "https://github.com/$GITHUB_USERNAME?tab=packages"
echo "Click on 'test-auth' package and change visibility to public"

# Clean up
docker rmi ghcr.io/$GITHUB_USERNAME/test-auth:latest
docker rmi alpine:latest
```

**Note:** Most images on ghcr.io require authentication to pull, even if marked as public. The best test is to push and pull your own images.

### 6.4 Verify All Services

Run this comprehensive check script:

```bash
#!/bin/bash
# Save as check-auth.sh and run with: bash check-auth.sh

echo "=== Authentication Status Check ==="
echo

# Check environment variables
echo "1. Environment Variables:"
if [ -n "$GH_TOKEN" ]; then
    echo "   ✓ GH_TOKEN is set (${#GH_TOKEN} characters)"
else
    echo "   ✗ GH_TOKEN is not set"
fi

if [ -n "$GITHUB_USERNAME" ]; then
    echo "   ✓ GITHUB_USERNAME: $GITHUB_USERNAME"
else
    echo "   ✗ GITHUB_USERNAME is not set"
fi
echo

# Check GitHub CLI
echo "2. GitHub CLI:"
if gh auth status &>/dev/null; then
    echo "   ✓ Authenticated with GitHub"
    gh auth status 2>&1 | grep "Logged in" | sed 's/^/   /'
else
    echo "   ✗ Not authenticated with GitHub CLI"
fi
echo

# Check Git configuration
echo "3. Git Configuration:"
git_user=$(git config --global user.name)
git_email=$(git config --global user.email)
if [ -n "$git_user" ] && [ -n "$git_email" ]; then
    echo "   ✓ Git user configured: $git_user <$git_email>"
else
    echo "   ✗ Git user not fully configured"
fi

git_helper=$(git config --global credential.helper)
if [[ "$git_helper" == *"gh"* ]] || [[ "$git_helper" == *"manager"* ]]; then
    echo "   ✓ Git credential helper configured: $git_helper"
else
    echo "   ⚠ Git credential helper: $git_helper"
fi
echo

# Check Docker/GHCR
echo "4. Docker/GHCR Authentication:"
if docker info &>/dev/null; then
    echo "   ✓ Docker daemon is running"
    
    # Check if logged in to ghcr.io by checking config
    if grep -q "ghcr.io" ~/.docker/config.json 2>/dev/null; then
        echo "   ✓ Configured for ghcr.io"
    else
        echo "   ⚠ Not configured for ghcr.io (need to login)"
    fi
else
    echo "   ✗ Docker daemon is not running or not accessible"
fi
echo

echo "=== Check Complete ==="
```

## Troubleshooting

### Common Issues and Solutions

#### 1. "Bad credentials" error with git
```bash
# Clear cached credentials and re-authenticate
git config --global --unset credential.helper
gh auth setup-git
```

#### 2. Docker login error: "docker-credential-gh": executable file not found
```bash
# This means Docker is trying to use a credential helper that doesn't exist
# Fix by resetting Docker config:
cp ~/.docker/config.json ~/.docker/config.json.backup 2>/dev/null
echo '{}' > ~/.docker/config.json

# Then retry login:
echo $GH_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
```

#### 3. Docker push error: "unauthorized: unauthenticated: User cannot be authenticated with the token provided"
This error occurs even after successful login when:
- Your PAT is missing `write:packages` permission
- The token has expired
- There's a mismatch between the username and token

**Solution:**
```bash
# First, verify your token has the correct permissions
gh auth status
# Check that Token scopes includes: 'write:packages'

# If write:packages is missing, create a new PAT with all required permissions
# Then update your .env file and reload:
source .env

# Clean Docker config and re-login
echo '{}' > ~/.docker/config.json
echo $GH_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# Retry the push
docker push ghcr.io/$GITHUB_USERNAME/test-auth:latest
```

#### 4. Multiple GitHub tokens (OAuth and PAT) causing conflicts
If `gh auth status` shows multiple tokens (e.g., both ghp_* and gho_* tokens):

```bash
# Remove the OAuth token stored in config file
rm ~/.config/gh/hosts.yml

# Or manually edit to remove just the OAuth token entry
nano ~/.config/gh/hosts.yml
# Delete the section with the gho_* token

# Re-authenticate with just your PAT
echo $GH_TOKEN | gh auth login --with-token

# Verify only one token remains
gh auth status
# Should now show only the ghp_* token from GH_TOKEN
```

#### 5. Docker permission denied
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Log out and back in, then retry
```

#### 6. Token not working
- Verify token has not expired
- Check token permissions match those listed above (especially `write:packages`)
- Regenerate token if necessary with all required scopes

#### 7. Environment variables not loading
```bash
# Debug environment variables
env | grep -E "GH_TOKEN|GITHUB"

# Manually source .env file
set -a; source .env; set +a
```

#### 8. "GH_TOKEN environment variable is being used" message
This is just an informational message from gh CLI, not an error. It means gh is using the token from the environment variable, which is what we want.

### Security Best Practices

1. **Never commit `.env` files** to version control
2. **Rotate tokens regularly** (every 90 days recommended)
3. **Use minimal required permissions** for tokens
4. **Store tokens in password managers** for backup
5. **Use different tokens** for different environments (dev/staging/prod)
6. **Monitor token usage** in GitHub Settings → Personal access tokens

## Quick Reference

```bash
# One-liner setup after creating .env
export $(cat .env | xargs) && echo $GH_TOKEN | gh auth login --with-token && gh auth setup-git && echo $GH_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
```

## Additional Resources

- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [GitHub Container Registry Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [GitHub PAT Documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [Docker Credential Helpers](https://github.com/docker/docker-credential-helpers)