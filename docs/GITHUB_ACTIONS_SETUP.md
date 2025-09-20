# 🚀 GitHub Actions Setup Guide

This guide explains how to set up automated Docker builds and deployments using GitHub Actions.

## 📋 Overview

The GitHub Actions workflow automates:
- 🔍 **Change Detection**: Detects changes in backend, frontend, or pipeline code
- 🏗️ **Multi-Architecture Builds**: Builds for both ARM64 and AMD64
- 📤 **Image Publishing**: Pushes to Docker Hub automatically
- 📝 **Manifest Updates**: Updates Kubernetes deployment files
- 🔄 **GitOps Integration**: Commits updated manifests for ArgoCD sync

## 🛠️ Setup Steps

### 1. Repository Secrets

Add these secrets in your GitHub repository (see [Creating Repository Secrets](#-creating-repository-secrets) below for step-by-step instructions):

**Required Secrets:**
- `DOCKER_USERNAME`: Your Docker Hub username
- `DOCKER_PASSWORD`: Your Docker Hub password or access token

### 2. Workflow Files

The workflow is defined in `.github/workflows/docker-build-push.yml` and includes:

- **Change Detection Job**: Determines which components changed
- **Build Jobs**: Separate jobs for backend, frontend, and pipeline
- **Manifest Update Job**: Updates Kubernetes manifests automatically

### 3. Deployment Methods

#### Method 1: Automatic (Recommended)
```bash
# Simply push to main branch
git push origin main
```

#### Method 2: Manual Trigger
```bash
# Using GitHub CLI
gh workflow run docker-build-push.yml -f force_build=true

# Using deployment script
./scripts/deploy.sh
```

## 📊 Workflow Features

### Change Detection
The workflow automatically detects changes in:
- `backend/**` → Builds backend image
- `frontend/**` → Builds frontend image
- `Dockerfile.pipeline`, `core/`, `extractors/` → Builds pipeline image

### Image Tagging Strategy
- **Main Branch**: `main-[component]-YYYY-MM-DD-HH-mm-ss`
- **Pull Requests**: `pr-[component]-pr-YYYY-MM-DD-HH-mm-ss`
- **Latest Tags**: `[component]-latest` (main branch only)

### Multi-Architecture Support
All images are built for:
- `linux/amd64` (production x86_64 servers)
- `linux/arm64` (development ARM64 systems)

## 🔧 Troubleshooting

### Common Issues

**1. Build Failures**
- Check GitHub Actions logs in the "Actions" tab
- Verify Docker Hub credentials in repository secrets
- Ensure Dockerfiles are present and valid

**2. Permission Errors**
- Verify `DOCKER_PASSWORD` is correct (use access token, not password)
- Check Docker Hub repository exists and is accessible

**3. Manifest Update Failures**
- Ensure GitHub token has repository write permissions
- Check for merge conflicts in Kubernetes manifests

### Monitoring Builds

**GitHub Actions Dashboard:**
```
https://github.com/YOUR_USERNAME/diocesan-vitality/actions
```

**Watch Current Build:**
```bash
gh run watch
```

**List Recent Runs:**
```bash
gh run list
```

## 🎯 Best Practices

### Development Workflow
1. Create feature branch
2. Make changes
3. Test locally
4. Create pull request (triggers build without push)
5. Merge to main (triggers build and deployment)

### Image Management
- Images are automatically tagged with timestamps
- Old images can be cleaned up manually from Docker Hub
- Use `latest` tags for development, timestamped for production

### Security
- Never commit Docker Hub credentials to the repository
- Use Docker Hub access tokens instead of passwords
- Regularly rotate access tokens

## 📖 References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Docker Buildx Documentation](https://docs.docker.com/buildx/)

## 🔐 Creating Repository Secrets

### Step-by-Step Instructions

**1. Navigate to Repository Settings**
- Go to your GitHub repository: `https://github.com/tomknightatl/diocesan-vitality`
- Click the **Settings** tab (near the top right of the repository page)

**2. Access Secrets and Variables**
- In the left sidebar, scroll down to **Security** section
- Click **Secrets and variables** → **Actions**

**3. Add New Repository Secret**
- Click the **New repository secret** button
- You'll see a form with two fields: "Name" and "Secret"

**4. Create DOCKER_USERNAME Secret**
- **Name:** `DOCKER_USERNAME`
- **Secret:** Your Docker Hub username (e.g., `tomatl`)
- Click **Add secret**

**5. Create DOCKER_PASSWORD Secret**
- Click **New repository secret** again
- **Name:** `DOCKER_PASSWORD`
- **Secret:** Your Docker Hub password or access token
- Click **Add secret**

### 🔑 Getting Docker Hub Access Token (Recommended)

Instead of using your Docker Hub password, create an access token:

**1. Log into Docker Hub**
- Go to [hub.docker.com](https://hub.docker.com)
- Sign in to your account

**2. Create Access Token**
- Click your username (top right) → **Account Settings**
- Go to **Security** tab
- Click **New Access Token**
- Name: `diocesan-vitality-github-actions`
- Permissions: **Read, Write, Delete**
- Click **Generate**

**3. Copy Token**
- **Important:** Copy the token immediately - you won't see it again!
- Use this token as the `DOCKER_PASSWORD` secret value

### ✅ Verify Secrets

After adding both secrets, you should see:
- `DOCKER_USERNAME` ✓
- `DOCKER_PASSWORD` ✓

The secrets list will show the names but not the values (for security).

### 🔄 Testing the Setup

**1. Trigger a Test Build**
```bash
# Push a small change to trigger the workflow
git commit --allow-empty -m "Test GitHub Actions setup"
git push origin main
```

**2. Monitor the Build**
- Go to the **Actions** tab in your repository
- You should see a new workflow run starting
- Click on it to see the build progress

**3. Check for Errors**
- If authentication fails, verify your Docker Hub credentials
- Check the workflow logs for specific error messages

## 🆘 Getting Help

If you encounter issues:
1. Check the GitHub Actions logs
2. Review the workflow file for syntax errors
3. Verify all required secrets are set correctly
4. Test Docker builds locally first
5. Ensure Docker Hub repository exists and is accessible
