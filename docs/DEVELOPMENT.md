# USCCB Local Development Environment Setup

This guide will help you set up a local development environment for the USCCB project, allowing you to test changes before deploying to production.

## 🏗️ Architecture Overview

Your production setup:
- **Frontend**: React app (Vite) served by NGINX
- **Backend**: FastAPI Python application
- **Database**: Supabase (PostgreSQL)
- **Infrastructure**: Kubernetes with ArgoCD
- **Container Registry**: Docker Hub

## 🚀 Local Development Stack

### Prerequisites

```bash
# Required tools:
# - Node.js 20+ and npm
# - Python 3.11+
# - Git
```

### 1. Environment Setup

# Edit .env 
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
GENAI_API_KEY_USCCB=your_genai_key_here
SEARCH_API_KEY_USCCB=your_search_key_here
SEARCH_CX_USCCB=your_search_cx_here

# Local development specific
NODE_ENV=development
PYTHONPATH=.
```

### 2. Backend Development

```bash
# Navigate to project root
cd /path/to/USCCB

# Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Load local environment
export $(cat .env | grep -v '^#' | xargs)

# Run backend in development mode
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Backend will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### 3. Frontend Development

```bash
# In a new terminal, navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Frontend will be available at http://localhost:5173
# Vite proxy will forward /api calls to backend at localhost:8000
```

### 4. Database Scripts Development

```bash
# With your virtual environment activated and .env loaded
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)

# Test individual scripts
python extract_dioceses.py --max_dioceses 2
python find_parishes.py --max_dioceses_to_process 1
python extract_parishes.py --num_dioceses 1 --num_parishes_per_diocese 3

# Test full pipeline
python run_pipeline.py --max_dioceses 1 --max_parishes_per_diocese 2 --num_parishes_for_schedule 1
```

### 5. Pipeline Development

The data extraction pipeline can be developed and tested both locally and in containerized environments.

```bash
# Run individual pipeline components locally
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)

# Test individual scripts
python extract_dioceses.py --max_dioceses 2
python find_parishes.py --diocese_id 123
python extract_parishes.py --diocese_id 123 --num_parishes_per_diocese 5
python extract_schedule.py

# Test full pipeline with limits
python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 5 --skip_schedules

# Test pipeline container locally
docker build -f Dockerfile.pipeline -t usccb-pipeline:test .
docker run --rm --env-file .env usccb-pipeline:test

# Test with specific arguments
docker run --rm --env-file .env usccb-pipeline:test python run_pipeline.py --skip_schedules

# Debug pipeline container
docker run -it --rm --env-file .env usccb-pipeline:test /bin/bash

# Test Chrome/ChromeDriver setup
docker run --rm usccb-pipeline:test google-chrome --version
docker run --rm usccb-pipeline:test python -c "from webdriver_manager.chrome import ChromeDriverManager; print('OK')"
```

## 💡 Recommended Daily Workflow
```bash
# Terminal 1: Backend
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)
cd backend && uvicorn main:app --reload

# Terminal 2: Frontend  
cd frontend && npm run dev

# Terminal 3: Testing
python extract_dioceses.py --max_dioceses 1
pytest tests/ -v
This approach gives you:
```

## 🧪 Testing Strategy

### Unit Tests
```bash
# Run Python tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Test specific modules
pytest tests/test_extractors.py -v
```

### Integration Tests
```bash
# Test API endpoints
curl http://localhost:8000/api
curl http://localhost:8000/api/dioceses

# Test frontend
npm run test  # If you add frontend tests
```

### End-to-End Testing
```bash
# Test full pipeline with minimal data
python run_pipeline.py \
  --max_dioceses 1 \
  --max_parishes_per_diocese 2 \
  --num_parishes_for_schedule 1

# Test Docker build (for production preparation)
docker build -t usccb-backend:test ./backend
docker build -t usccb-frontend:test ./frontend
docker build -f Dockerfile.pipeline -t usccb-pipeline:test .
```

## 🔧 Development Workflow

### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Start local development environment
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)

# Backend terminal
cd backend && uvicorn main:app --reload

# Frontend terminal  
cd frontend && npm run dev

# Make changes and test locally
```

### 2. Testing Changes
```bash
# Test Python code
pytest tests/ -v

# Test API manually
curl http://localhost:8000/api/dioceses

# Test frontend
open http://localhost:5173

# Test data extraction
python extract_dioceses.py --max_dioceses 1
```

### 3. Pre-Production Testing
```bash
# Test Docker builds (verifies production readiness)
docker build -t usccb-backend:test ./backend
docker build -t usccb-frontend:test ./frontend
docker build -f Dockerfile.pipeline -t usccb-pipeline:test .

# Tag images for production testing (if you have a staging environment)
docker tag usccb-backend:test $DOCKER_USERNAME/usccb:backend-test
docker tag usccb-frontend:test $DOCKER_USERNAME/usccb:frontend-test
docker tag usccb-pipeline:test $DOCKER_USERNAME/usccb:pipeline-test
```

## 🚀 Production Deployment

### 1. Build and Push
```bash
# Load production environment
source .env

# Build production images
docker build -t $DOCKER_USERNAME/usccb:backend ./backend
docker build -t $DOCKER_USERNAME/usccb:frontend ./frontend
docker build -f Dockerfile.pipeline -t $DOCKER_USERNAME/usccb:pipeline .

# Push to registry
docker push $DOCKER_USERNAME/usccb:backend
docker push $DOCKER_USERNAME/usccb:frontend
docker push $DOCKER_USERNAME/usccb:pipeline
```

### 2. Deploy via GitOps
```bash
# Commit changes
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature-name

# Create pull request
# After review and merge, ArgoCD will automatically deploy
```

## 🛠️ Development Tools Setup

### VS Code Configuration
Create `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.envFile": "${workspaceFolder}/.env",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "eslint.workingDirectories": ["frontend"]
}
```

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Backend Debug",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/backend/main.py",
      "envFile": "${workspaceFolder}/.env",
      "console": "integratedTerminal"
    }
  ]
}
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat << EOF > .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.56.0
    hooks:
      - id: eslint
        files: frontend/.*\.[jt]sx?$
        types: [file]
EOF

# Install hooks
pre-commit install
```

## 📊 Monitoring and Debugging

### Log Monitoring
```bash
# Backend logs in terminal where uvicorn is running
# Frontend logs in terminal where npm run dev is running

# Python script logs
tail -f scraping.log
```

### Database Monitoring
```bash
# Check Supabase tables
python -c "
from core.db import get_supabase_client
client = get_supabase_client()
print(client.table('Dioceses').select('count').execute())
"

# Run statistics report
python report_statistics.py
```

## 🔄 Continuous Integration

Create `.github/workflows/test.yml`:
```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        
    - name: Run tests
      run: |
        pytest tests/ -v
        
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '20'
        
    - name: Install frontend dependencies
      working-directory: ./frontend
      run: npm install
      
    - name: Build frontend
      working-directory: ./frontend
      run: npm run build
```

## 🎯 Recommended Development Flow

```bash
# 1. Set up environment (one time)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Start local environment (each development session)
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)

# 3. Run backend (terminal 1)
cd backend && uvicorn main:app --reload

# 4. Run frontend (terminal 2)  
cd frontend && npm run dev

# 5. Test data pipeline with small limits (terminal 3)
python run_pipeline.py --max_dioceses 1 --max_parishes_per_diocese 2

# 6. Run tests before committing
pytest tests/ -v

# 7. Test Docker builds before pushing
docker build -t usccb-backend:test ./backend
docker build -t usccb-frontend:test ./frontend
docker build -f Dockerfile.pipeline -t usccb-pipeline:test .
```

## 🚨 Deployment Troubleshooting

### Issue: Updated Docker Images Not Reflected in Production

**Problem**: After building and pushing updated Docker images to Docker Hub and syncing ArgoCD, the application is still showing the old version.

**Root Cause**: Kubernetes deployments using image tags without version numbers (e.g., `tomatl/usccb:frontend`) won't automatically pull updated images even with `imagePullPolicy: Always`, because Kubernetes considers images with the same tag to be identical.

**Solution**: Force restart the deployments to pull the latest images:

```bash
# Force restart frontend deployment
kubectl rollout restart deployment/frontend-deployment -n usccb

# Force restart backend deployment  
kubectl rollout restart deployment/backend-deployment -n usccb

# Verify new pods are running with updated images
kubectl get pods -n usccb

# Check the image SHA of the new pods (optional verification)
kubectl get pod <pod-name> -n usccb -o jsonpath='{.status.containerStatuses[0].imageID}'
```

**Prevention**: For future deployments, consider using versioned tags (e.g., `tomatl/usccb:frontend-v1.2.3`) to ensure Kubernetes always pulls the correct image version.

### Updated Production Deployment Workflow

```bash
# 1. Build and push (as before)
docker build -t $DOCKER_USERNAME/usccb:backend ./backend
docker build -t $DOCKER_USERNAME/usccb:frontend ./frontend
docker build -f Dockerfile.pipeline -t $DOCKER_USERNAME/usccb:pipeline .
docker push $DOCKER_USERNAME/usccb:backend
docker push $DOCKER_USERNAME/usccb:frontend
docker push $DOCKER_USERNAME/usccb:pipeline

# 2. Sync ArgoCD (as before)
# Use ArgoCD UI or CLI to sync the application

# 3. Force deployment restart (NEW STEP)
kubectl rollout restart deployment/frontend-deployment -n usccb
kubectl rollout restart deployment/backend-deployment -n usccb

# 4. Verify deployment
kubectl get pods -n usccb
```

This setup provides a complete local development environment that mirrors your production setup while allowing for rapid iteration and testing of changes before they reach production via ArgoCD.