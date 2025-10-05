# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

includeClaudeAttribution: false

## Git Branch Policy

**🚨 CRITICAL: Never Push Directly to Main**

- **NEVER push commits directly to the main branch**
- **ALWAYS push exclusively to the develop branch**
- **All code changes must go through: develop → CI/CD → staging validation → merge to main**
- **Main branch is protected and only updated via controlled merges from develop**

## Pre-commit Hook Policy

**🚨 CRITICAL: Never Bypass Pre-commit Hooks Without Permission**

- **NEVER bypass pre-commit hooks using SKIP=<hook-name>, --no-verify, or any other method without explicit user permission**
- **If pre-commit hooks fail, ALWAYS inform the user and ask how to proceed**
- **NEVER decide on your own to skip or bypass failed pre-commit checks**
- **Only bypass pre-commit hooks when the user explicitly authorizes it**
- **Pre-commit hooks exist for code quality and must be respected by default**

## kubectl Command Policy

**🚨 CRITICAL: kubectl Command Approval Required**

- **NEVER run kubectl create, kubectl apply, kubectl delete, or kubectl patch commands without explicit user permission**
- **ALWAYS ask for permission before executing any kubectl command that modifies cluster state**
- **Exception: Read-only commands (kubectl get, kubectl describe, kubectl logs) are allowed**
- **Required format when kubectl commands are needed:**
  1. List all kubectl commands that will be executed
  2. Ask: "May I run these kubectl commands?"
  3. Wait for explicit user approval before proceeding
- **This policy applies to all kubectl commands, including those in Makefile targets**

## Infrastructure Management Policy

**🚨 CRITICAL: Always Use Makefile Commands for Infrastructure**

- **NEVER run direct CLI commands (doctl, cloudflared, kubectl) for infrastructure operations**
- **ALWAYS use Makefile commands exclusively for:**
  - Cluster creation/destruction: `make cluster-create`, `make cluster-destroy`
  - Tunnel creation/destruction: `make tunnel-create`, `make tunnel-destroy`
  - DNS record management: handled within tunnel commands
  - kubectl context management: handled within cluster commands
- **Commands automatically handle authentication using tokens from .env file**
- **Exception: Read-only commands (doctl kubernetes cluster list, kubectl get) are allowed for status checking**

**🔄 CRITICAL: Infrastructure Commands Must Be Idempotent**

- **ALL Makefile infrastructure commands MUST be idempotent (safe to run multiple times)**
- **Commands must gracefully handle existing resources:**
  - If cluster exists → verify status, configure access, continue successfully
  - If tunnel exists → verify configuration, skip creation, continue successfully
  - If DNS records exist → verify configuration, skip creation, continue successfully
  - If kubectl context exists → use existing context, continue successfully
- **Commands must gracefully handle missing resources:**
  - If cluster doesn't exist during destroy → report "not found", continue successfully
  - If tunnel doesn't exist during destroy → report "not found", continue successfully
  - If DNS records don't exist → report "not found", continue successfully
- **Never fail with errors for expected conditions (resource exists/doesn't exist)**

**⏱️ CRITICAL: Handle Infrastructure Command Timeouts Properly**

- **NEVER re-run infrastructure commands immediately after timeout**
- **Infrastructure commands like `make cluster-create-cli` often succeed even when timeout occurs**
- **If a command times out, check the actual infrastructure state using read-only commands:**
  - `doctl kubernetes cluster list` - check if cluster was created
  - `kubectl get nodes` - verify cluster connectivity
  - `doctl auth list` - verify DigitalOcean authentication
- **Common mistake pattern to avoid:**
  1. Run `make cluster-create-cli` in foreground → times out but cluster is created
  2. Incorrectly assume it failed and run again → fails gracefully due to idempotent design

## ArgoCD App-of-Apps Pattern

**🚀 AUTOMATED: ApplicationSets Deploy Automatically**

- **ArgoCD uses App-of-Apps pattern for automatic ApplicationSet deployment**
- **Infrastructure setup sequence:**
  1. `make cluster-create CLUSTER_LABEL=dev` - Create DigitalOcean Kubernetes cluster
  2. `make tunnel-create CLUSTER_LABEL=dev` - Create Cloudflare tunnel
  3. `make tunnel-verify CLUSTER_LABEL=dev` - Verify tunnel and extract token
  4. `make argocd-install CLUSTER_LABEL=dev` - Install ArgoCD + Auto-deploy ApplicationSets
  5. `make sealed-secrets-create CLUSTER_LABEL=dev` - Create sealed secrets from tunnel token
  6. `make argocd-verify CLUSTER_LABEL=dev` - Verify ArgoCD server is accessible at its URL
     6.5. `make docker-build CLUSTER_LABEL=dev` - Build and push Docker images from appropriate branch
  7. `make app-deploy CLUSTER_LABEL=dev` - Deploy diocesan-vitality application via GitOps
- **Step 4 automatically deploys root Application:** `root-applicationsets-dev`
- **Root Application manages three ApplicationSets:**
  - `sealed-secrets-dev-applicationset.yaml` - Bitnami Sealed Secrets controller
  - `cloudflare-tunnel-dev-applicationset.yaml` - Cloudflare tunnel deployment
  - `diocesan-vitality-dev-applicationset.yaml` - Main application deployment
- **Monitor ApplicationSets:** `kubectl get applicationsets -n argocd`
- **Monitor Applications:** `kubectl get applications -n argocd`
- **Correct approach:**
  1. Run infrastructure command once with appropriate timeout (30+ minutes)
  2. If timeout occurs, check actual infrastructure state first
  3. Only re-run if infrastructure was not actually created
- **NEVER claim a command "timed out" unless it actually reached the specified timeout duration**
- **When commands fail quickly, analyze the actual error message rather than assuming timeout**

## CI/CD Pipeline and Branch Strategy

**🚀 Automated Deployment Pipeline**

- **Branch-to-Environment Mapping:**
  - `develop` branch → Development cluster (`CLUSTER_LABEL=dev`)
  - `staging` branch → Staging cluster (`CLUSTER_LABEL=stg`)
  - `main` branch → Production cluster (`CLUSTER_LABEL=prd`)
- **GitOps Workflow:**
  - Push to `develop` → Auto-deploys to dev environment via ArgoCD
  - Push to `staging` → Auto-deploys to staging environment via ArgoCD
  - Push to `main` → Requires manual approval, then deploys to production
- **Pipeline Stages:**
  1. Code Quality: Linting and formatting checks
  2. Tests: Unit and integration tests
  3. Build: Multi-platform Docker images (linux/amd64, linux/arm64)
  4. Deploy: GitOps-based deployment via ArgoCD ApplicationSets
  5. Smoke Tests: Post-deployment verification

**📋 Complete CI/CD Documentation:** See [docs/CI_CD_PIPELINE.md](docs/CI_CD_PIPELINE.md)

## Monitoring and Live System Access

**🌐 Production System:**

- **Frontend:** https://ui.diocesanvitality.org
- **Dashboard:** https://ui.diocesanvitality.org/dashboard
- **Backend API:** https://api.diocesanvitality.org
- **ArgoCD:** https://argocd.diocesanvitality.org

**🧪 Development System:**

- **Frontend:** https://devui.diocesanvitality.org
- **Dashboard:** https://devui.diocesanvitality.org/dashboard
- **Backend API:** https://devapi.diocesanvitality.org
- **ArgoCD:** https://devargocd.diocesanvitality.org

**📊 Monitoring Commands:**

```bash
# Check cluster status
kubectl config use-context do-nyc2-dv-dev
kubectl get pods -n diocesan-vitality-dev
kubectl get applicationsets -n argocd

# Check infrastructure status
make infra-status CLUSTER_LABEL=dev

# Monitor ArgoCD applications
kubectl get applications -n argocd -w
```

## Development Commands

### Quick Development Setup

```bash
# Install dependencies
make install

# Start backend only
make start

# Start full environment (backend + frontend)
make start-full

# Stop all services
make stop

# Quick development tests
make test-quick

# Format code
make format

# Lint code
make lint
```

### Cluster Development Commands

```bash
# Build and push development images to Docker Hub
DEV_TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)-dev
docker buildx build --platform linux/amd64,linux/arm64 -f backend/Dockerfile -t tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP} --push backend/
docker buildx build --platform linux/amd64,linux/arm64 -f frontend/Dockerfile -t tomatl/diocesan-vitality:frontend-${DEV_TIMESTAMP} --push frontend/
docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.pipeline -t tomatl/diocesan-vitality:pipeline-${DEV_TIMESTAMP} --push .

# Alternative: Build for GitHub Container Registry
docker buildx build --platform linux/amd64,linux/arm64 -f backend/Dockerfile -t ghcr.io/tomknightatl/diocesan-vitality:backend-${DEV_TIMESTAMP} --push backend/

# Update development environment manifests
sed -i "s|image: tomatl/diocesan-vitality:.*backend.*|image: tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP}|g" k8s/environments/development/development-patches.yaml
sed -i "s|image: tomatl/diocesan-vitality:.*frontend.*|image: tomatl/diocesan-vitality:frontend-${DEV_TIMESTAMP}|g" k8s/environments/development/development-patches.yaml
sed -i "s|image: tomatl/diocesan-vitality:.*pipeline.*|image: tomatl/diocesan-vitality:pipeline-${DEV_TIMESTAMP}|g" k8s/environments/development/development-patches.yaml

# Deploy to development cluster via GitOps
git add k8s/environments/development/
git commit -m "Development deployment: ${DEV_TIMESTAMP}"
git push origin develop

# Monitor development cluster deployment
kubectl config use-context do-nyc2-dv-dev
kubectl get application diocesan-vitality-dev -n argocd -w
kubectl get pods -n diocesan-vitality-dev -w
kubectl logs deployment/backend-deployment -n diocesan-vitality-dev --follow
```

### Pipeline Commands

```bash
# Quick pipeline test (5 parishes from diocese 1)
make pipeline

# Single diocese pipeline
make pipeline-single DIOCESE_ID=<id>

# Full pipeline with monitoring
python -m pipeline.run_pipeline --max_parishes_per_diocese 10 --monitoring_url http://localhost:8000

# High-performance async extraction
python -m pipeline.async_extract_parishes --diocese_id <id> --pool_size 6 --batch_size 12

# Distributed pipeline (for production)
python -m pipeline.distributed_pipeline_runner

# Specialized worker types (single image deployment)
python -m pipeline.distributed_pipeline_runner --worker_type discovery    # Steps 1-2: Diocese + Parish directory discovery
python -m pipeline.distributed_pipeline_runner --worker_type extraction   # Step 3: Parish detail extraction
python -m pipeline.distributed_pipeline_runner --worker_type schedule     # Step 4: Mass schedule extraction
python -m pipeline.distributed_pipeline_runner --worker_type reporting    # Step 5: Analytics and reporting
```

### Testing & Environment

```bash
make env-check     # Check environment configuration
make db-check      # Test database connection
make ai-check      # Test AI API connection
make webdriver-check  # Test Chrome WebDriver

# Python testing
pytest                    # Run all tests
pytest tests/unit/       # Run unit tests only
pytest tests/integration/ # Run integration tests
pytest -v --tb=short     # Verbose output with short traceback
```

### Frontend Commands

```bash
cd frontend
npm install        # Install frontend dependencies
npm run dev        # Start development server (default: http://localhost:3000)
npm run build      # Build for production
npm run lint       # Lint frontend code with ESLint
npm run preview    # Preview production build locally
```

### Backend Commands

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000  # Start FastAPI backend
```

## Architecture Overview

### Core System Components

- **Pipeline** (`pipeline/`): Main extraction engine with all pipeline scripts
- **Core Modules** (`core/`): Shared utilities for database, WebDriver, circuit breakers, AI analysis
- **Frontend** (`frontend/`): React dashboard with real-time monitoring via WebSockets
- **Backend** (`backend/`): FastAPI server providing monitoring APIs and data endpoints
- **Extractors** (`extractors/`): Website-specific parish extractors

### Pipeline Architecture

The system operates in three modes:

1. **Traditional Pipeline**: Sequential execution for initial setup/development
   - `pipeline.extract_dioceses` → `pipeline.find_parishes` → `pipeline.async_extract_parishes` → `pipeline.extract_schedule`

2. **Distributed Pipeline**: Production continuous operation
   - Workers coordinate via database tables (`pipeline_workers`, `diocese_work_assignments`)
   - Automatic workload distribution and failover
   - Real-time monitoring dashboard

3. **Specialized Workers**: Production deployment with worker type specialization
   - **Discovery Workers**: Steps 1-2 (Diocese + Parish directory discovery) - 512Mi/200m CPU
   - **Extraction Workers**: Step 3 (Parish detail extraction) - 2.2Gi/800m CPU, scales 2-5 pods
   - **Schedule Workers**: Step 4 (Mass schedule extraction) - 1.5Gi/600m CPU, scales 1-3 pods
   - **Reporting Workers**: Step 5 (Analytics and reporting) - 512Mi/200m CPU
   - Single container image with runtime specialization via `WORKER_TYPE` environment variable

### Key Directories

- **`pipeline/`**: All pipeline scripts (extraction, discovery, scheduling, reporting)
- **`core/`**: Essential utilities (database, WebDriver, circuit breakers, AI analysis, ML URL prediction)
- **`extractors/`**: Website-specific parish extraction logic
- **`backend/`**: FastAPI backend for monitoring and APIs
- **`frontend/`**: React dashboard application
- **`scripts/`**: Development utilities (`dev_quick.py`, `dev_start.py`, `dev_test.py`)
- **`docs/`**: Comprehensive documentation including LOCAL_DEVELOPMENT.md, COMMANDS.md
- **`k8s/`**: Kubernetes deployment manifests for production
- **`tests/`**: Test suite

### Technology Stack

- **Python 3.12+**: Core pipeline with Selenium, BeautifulSoup, Google Gemini AI
- **React + Vite**: Frontend dashboard with real-time updates
- **FastAPI**: Backend monitoring and data APIs
- **Supabase PostgreSQL**: Cloud database
- **Docker + Kubernetes**: Production deployment

### Environment Configuration

Required environment variables in `.env` (copy from `.env.example`):

- `SUPABASE_URL`, `SUPABASE_KEY`: Database connection
- `GENAI_API_KEY`: Google Gemini AI for content analysis
- `SEARCH_API_KEY`, `SEARCH_CX`: Google Custom Search
- `MONITORING_URL`: Backend monitoring endpoint (default: http://localhost:8000)
- `DOCKER_USERNAME`, `DOCKER_PASSWORD`: Docker Hub credentials for pushing images
- `GITHUB_TOKEN`: GitHub Personal Access Token for GitHub Container Registry access

**Container Registry Options**:

- **Docker Hub**: `tomatl/diocesan-vitality` (production deployments)
- **GitHub Container Registry**: `ghcr.io/tomknightatl/diocesan-vitality` (development/internal)

**Setup**: Copy `.env.example` to `.env` and fill in your API keys

```bash
cp .env.example .env
# Edit .env with your API keys
```

### Development Workflow

#### Local Development

1. Start backend: `cd backend && uvicorn main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Run pipeline: `python -m pipeline.run_pipeline --max_parishes_per_diocese 5`
4. Monitor via dashboard: http://localhost:3000/dashboard

#### Cluster Development (Alternative)

1. Build and push development images: `DEV_TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)-dev && docker buildx build --platform linux/amd64,linux/arm64 -f backend/Dockerfile -t tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP} --push backend/`
2. Update development manifests: `sed -i "s|image: tomatl/diocesan-vitality:.*backend.*|image: tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP}|g" k8s/environments/development/development-patches.yaml`
3. Deploy via GitOps: `git add k8s/environments/development/ && git commit -m "Development deployment: ${DEV_TIMESTAMP}" && git push origin develop`
4. Monitor cluster: `kubectl config use-context do-nyc2-dv-dev && kubectl get pods -n diocesan-vitality-dev -w`

### Key Features

- **Respectful Automation**: Comprehensive robots.txt compliance, rate limiting, blocking detection
- **AI-Powered Analysis**: Google Gemini integration for intelligent content extraction
- **Circuit Breaker Protection**: Automatic failure detection and recovery (17+ circuit breakers)
- **ML URL Prediction**: Machine learning system reducing 404 errors by 50%
- **Real-time Monitoring**: WebSocket-based dashboard with live extraction progress
- **Distributed Processing**: Kubernetes-based horizontal scaling with auto-failover
- **Worker Specialization**: Specialized worker types with optimized resource allocation and independent scaling

### Database Schema

Primary tables: `dioceses`, `parishes`, `mass_schedules`, `pipeline_workers`, `diocese_work_assignments`
See `docs/DATABASE.md` for complete schema documentation.

### Performance Optimization

- **Async Processing**: 60% performance improvement with concurrent extraction
- **Intelligent Caching**: Content-aware TTL management
- **Adaptive Timeouts**: Dynamic optimization based on site complexity
- **Quality-Weighted ML Training**: Success-based URL discovery optimization

### Code Quality Standards

#### Python Code Style (Black & Flake8 Compliance)

**MANDATORY: All Python code written by Claude must comply with Black and flake8 standards**

- **Line Length**: 127 characters maximum (Black format)
- **Import Organization**:
  - Standard library imports first
  - Third-party imports second
  - Local imports last
  - Separate groups with blank lines
- **String Quotes**: Use double quotes for strings (Black default)
- **Trailing Commas**: Include trailing commas in multi-line structures
- **Whitespace**: Follow PEP 8 whitespace rules
- **Flake8 Ignored Rules**: E203 (whitespace before ':'), W503 (line break before binary operator)

**Example compliant code structure:**

```python
import os
import sys
from typing import Dict, List, Optional

import requests
from selenium import webdriver

from core.database import get_connection
from core.utils import logger


def extract_parish_data(
    url: str,
    timeout: int = 30,
    retry_count: int = 3,
) -> Optional[Dict[str, str]]:
    """Extract parish data from URL with proper error handling."""
    try:
        response = requests.get(url, timeout=timeout)
        return {"status": "success", "data": response.text}
    except Exception as e:
        logger.error(f"Failed to extract data from {url}: {e}")
        return None
```

```bash
# Code formatting (Black)
make format            # Format all Python code
black . --line-length=127 --exclude="venv|node_modules"

# Linting (Flake8)
make lint             # Run Python linting
flake8 . --exclude=venv,node_modules --max-line-length=127 --extend-ignore=E203,W503

# Frontend linting
cd frontend && npm run lint

# Development utilities
make clean            # Clean cache and temporary files
make kill-chrome      # Kill stuck Chrome processes
make restart          # Restart all services
make ports            # Check development port usage
```

### Testing Commands

```bash
# Run all tests
pytest                           # Full test suite
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only
pytest -v --tb=short           # Verbose with short traceback

# Quick development checks
make test-quick                 # Essential checks (db, ai, env)
make env-check                  # Environment configuration
make db-check                   # Database connectivity
make ai-check                   # AI API connectivity
make webdriver-check            # Chrome WebDriver
make monitor-check              # Monitoring integration
```

### Important Documentation References

- **[docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)**: Complete local setup guide
- **[docs/COMMANDS.md](docs/COMMANDS.md)**: Comprehensive command reference
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Detailed system architecture
- **[docs/DATABASE.md](docs/DATABASE.md)**: Database schema and operations
- **[docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)**: Docker and Kubernetes deployment
- **[docs/CI_CD_PIPELINE.md](docs/CI_CD_PIPELINE.md)**: Complete CI/CD pipeline documentation

## Git Workflow Rules

### IMPORTANT: Repository Changes

- **NEVER commit or push changes without explicit user permission**
- **ALWAYS ask before running git commit or git push commands**
- **Exception: Only push when the user explicitly requests "commit and push" or similar**
- When changes are ready, inform the user and ask for permission to commit/push
- Provide a summary of changes before requesting permission

### IMPORTANT: Pre-commit Hooks

- **NEVER bypass pre-commit hooks using PRE_COMMIT_ALLOW_NO_CONFIG=1 or --no-verify without explicit user permission**
- **If pre-commit hooks fail, inform the user and ask how to proceed**
- **Only bypass pre-commit hooks when the user explicitly authorizes it**
- Pre-commit hooks exist for code quality and should be respected by default

## GitOps and ArgoCD Rules

### CRITICAL: ArgoCD-Managed Resources

- **NEVER directly patch, edit, or modify Kubernetes objects that are deployed by ArgoCD Applications**
- **ALWAYS use GitOps principles**: modify the source manifests in the repository, then let ArgoCD sync the changes
- **To change ArgoCD-managed resources**:
  1. Update the corresponding YAML manifests in the `k8s/` directory
  2. Commit changes to git (with user permission)
  3. Let ArgoCD automatically sync the changes, or manually trigger a sync
- **ArgoCD Applications create and manage**: namespaces, deployments, services, configmaps, secrets, and other Kubernetes resources
- **Exception**: Only manually modify Kubernetes objects in emergency situations and immediately update the source manifests to match

## Common Troubleshooting Scenarios

### Infrastructure Command Timeouts

**Symptom:** `make cluster-create` or similar command times out after 30+ minutes
**Resolution:**

1. **Don't panic or re-run immediately** - cluster may still be creating successfully
2. Check actual cluster state: `doctl kubernetes cluster list`
3. If cluster exists with "running" status → Success! Continue with `make cluster-context`
4. If cluster is "provisioning" → Wait a few more minutes, check again
5. Only re-run if cluster truly doesn't exist

### ArgoCD Application Not Syncing

**Symptom:** Application shows "OutOfSync" status for extended period
**Resolution:**

```bash
# Check application status
kubectl get application <app-name> -n argocd -o yaml

# Common fixes:
# 1. Verify correct branch in ApplicationSet
kubectl get applicationset -n argocd <appset-name> -o yaml | grep targetRevision

# 2. Manually trigger sync if needed (with user permission)
kubectl patch application <app-name> -n argocd --type merge -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{"syncStrategy":{"hook":{},"apply":{"force":false}}}}}'

# 3. Check ArgoCD logs for errors
kubectl logs -n argocd deployment/argocd-application-controller
```

### Sealed Secrets Not Decrypting

**Symptom:** Pods failing with missing secret data
**Resolution:**

1. Verify sealed-secrets controller is running: `kubectl get pods -n kube-system -l app.kubernetes.io/name=sealed-secrets`
2. Check SealedSecret resource exists: `kubectl get sealedsecrets -n <namespace>`
3. Verify secret was created: `kubectl get secret <secret-name> -n <namespace>`
4. Re-create sealed secret if needed: `make sealed-secrets-create CLUSTER_LABEL=<env>`

### Tunnel Not Connecting

**Symptom:** URLs not accessible, cloudflared pod logs show connection errors
**Resolution:**

1. Check tunnel pod status: `kubectl get pods -n cloudflare-tunnel-<env>`
2. View tunnel logs: `kubectl logs -n cloudflare-tunnel-<env> deployment/cloudflared`
3. Verify tunnel token secret exists: `kubectl get secret cloudflared-token -n cloudflare-tunnel-<env>`
4. Verify tunnel exists in Cloudflare: Check output of `make tunnel-check CLUSTER_LABEL=<env>`
5. Re-create tunnel token if needed: `make tunnel-verify CLUSTER_LABEL=<env>` then `make sealed-secrets-create CLUSTER_LABEL=<env>`

### Docker Build Platform Issues

**Symptom:** `docker buildx` fails with platform errors
**Resolution:**

```bash
# Ensure buildx is properly set up
docker buildx create --use --name multiplatform --driver docker-container

# Verify buildx builder
docker buildx inspect multiplatform --bootstrap

# If issues persist, use single platform for testing
docker build -f backend/Dockerfile -t tomatl/diocesan-vitality:backend-test backend/
```
