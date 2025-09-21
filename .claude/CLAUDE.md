# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

includeClaudeAttribution: false

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

### Pipeline Commands
```bash
# Quick pipeline test (5 parishes from diocese 1)
make pipeline

# Single diocese pipeline
make pipeline-single DIOCESE_ID=<id>

# Full pipeline with monitoring
python run_pipeline.py --max_parishes_per_diocese 10 --monitoring_url http://localhost:8000

# High-performance async extraction
python async_extract_parishes.py --diocese_id <id> --pool_size 6 --batch_size 12

# Distributed pipeline (for production)
python distributed_pipeline_runner.py

# Specialized worker types (single image deployment)
python distributed_pipeline_runner.py --worker_type discovery    # Steps 1-2: Diocese + Parish directory discovery
python distributed_pipeline_runner.py --worker_type extraction   # Step 3: Parish detail extraction
python distributed_pipeline_runner.py --worker_type schedule     # Step 4: Mass schedule extraction
python distributed_pipeline_runner.py --worker_type reporting    # Step 5: Analytics and reporting
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
- **Pipeline Scripts**: Main extraction engine (`run_pipeline.py`, `async_extract_parishes.py`)
- **Core Modules** (`core/`): Shared utilities for database, WebDriver, circuit breakers, AI analysis
- **Frontend** (`frontend/`): React dashboard with real-time monitoring via WebSockets
- **Backend** (`backend/`): FastAPI server providing monitoring APIs and data endpoints
- **Distributed Pipeline**: Kubernetes-based distributed processing (`distributed_pipeline_runner.py`)

### Pipeline Architecture
The system operates in three modes:

1. **Traditional Pipeline**: Sequential execution for initial setup/development
   - `extract_dioceses.py` → `find_parishes.py` → `async_extract_parishes.py` → `extract_schedule.py`

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
- **`core/`**: Essential utilities (database, WebDriver, circuit breakers, AI analysis, ML URL prediction)
- **`extractors/`**: Website-specific parish extraction logic
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

**Setup**: Copy `.env.example` to `.env` and fill in your API keys
```bash
cp .env.example .env
# Edit .env with your API keys
```

### Development Workflow
1. Start backend: `cd backend && uvicorn main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Run pipeline: `python run_pipeline.py --max_parishes_per_diocese 5`
4. Monitor via dashboard: http://localhost:3000/dashboard

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
```bash
# Code formatting (Black)
make format            # Format all Python code
black . --line-length=127 --exclude="venv|node_modules"

# Linting (Flake8)
make lint             # Run Python linting
flake8 . --exclude=venv,node_modules --max-line-length=88 --extend-ignore=E203,W503

# Frontend linting
cd frontend && npm run lint

# Development utilities
make clean            # Clean cache and temporary files
make kill-chrome      # Kill stuck Chrome processes
make restart          # Restart all services
make ports            # Check development port usage
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