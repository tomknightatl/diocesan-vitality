# Local Development Guide

This guide provides everything you need to develop and test the Diocesan Vitality extraction scripts locally.

## Prerequisites

- Python 3.12+
- Chrome browser (for selenium webdriver)
- Active internet connection
- Valid API keys (see Environment Setup)

## Quick Start

1. **Activate Virtual Environment**
   ```bash
   source venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (see Environment Setup section)
   ```

4. **Start Local Services** (see Environment Setup for details)

   **Terminal 1 - Backend (required for monitoring):**
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   **Terminal 2 - Frontend (optional):**
   ```bash
   cd frontend
   npm install  # First time only
   npm run dev
   ```

5. **Run Extraction Scripts**
   ```bash
   # Full pipeline with monitoring
   python run_pipeline_monitored.py --monitoring_url http://localhost:8000

   # Individual steps
   python extract_dioceses.py
   python find_parishes.py
   python extract_parishes.py
   python extract_schedule.py
   ```

## Environment Setup

### Required Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-service-role-key

# Google AI API Keys
GENAI_API_KEY_Diocesan Vitality=your-google-gemini-api-key
SEARCH_API_KEY_Diocesan Vitality=your-google-search-api-key
SEARCH_CX_Diocesan Vitality=your-google-search-cx-id
```

### API Key Setup

1. **Supabase**: Get URL and service role key from your Supabase project dashboard
2. **Google Gemini**: Create API key at https://ai.google.dev/
3. **Google Custom Search**:
   - Create API key at Google Cloud Console
   - Set up Custom Search Engine at https://cse.google.com/

### Local Services Setup

#### Backend Server (Required for Monitoring)

Start the FastAPI backend server:
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Server runs at http://localhost:8000

#### Frontend Dashboard (Optional)

For the full monitoring dashboard experience:
```bash
cd frontend
npm install  # First time only
npm run dev
```
Dashboard available at http://localhost:5173

### Monitoring Features

- **Real-time Logs**: View extraction progress live
- **Error Tracking**: See detailed error messages
- **Progress Tracking**: Monitor parishes processed
- **WebSocket Connection**: Live updates without refresh

### Available API Endpoints

- `GET /api/logs` - Recent log entries
- `GET /api/statistics` - Current extraction stats
- `GET /api/parishes` - Parish data
- `GET /api/dioceses` - Diocese data
- `WS /ws/monitoring` - WebSocket for live updates

## Development Workflow

### Running Individual Scripts

```bash
# Extract dioceses (Step 1)
python extract_dioceses.py

# Find parish directories (Step 2)
python find_parishes.py --diocese_id 123

# Extract parish details (Step 3)
python extract_parishes.py --diocese_id 123 --max_parishes 10

# Extract schedules (Step 4)
python extract_schedule.py --num_parishes 20
```

### Running Full Pipeline

```bash
# With monitoring (recommended)
python run_pipeline_monitored.py \
  --max_parishes_per_diocese 10 \
  --num_parishes_for_schedule 5 \
  --monitoring_url http://localhost:8000

# Without monitoring
python run_pipeline.py \
  --max_parishes_per_diocese 10 \
  --num_parishes_for_schedule 5
```

### Common Development Options

```bash
# Skip steps for faster iteration
python run_pipeline_monitored.py \
  --skip_dioceses \
  --skip_parish_directories \
  --diocese_id 123 \
  --max_parishes_per_diocese 5

# Focus on specific diocese
python run_pipeline_monitored.py \
  --diocese_id 123 \
  --max_parishes_per_diocese 20
```

## Testing

### Unit Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_extraction.py

# Run with verbose output
pytest -v
```

### Integration Tests
```bash
# Test database connections
python -c "from core.db import get_supabase_client; print('DB:', get_supabase_client().table('Dioceses').select('*').limit(1).execute())"

# Test API keys
python -c "from core.ai_client import get_genai_client; print('AI:', get_genai_client().generate_content('Hello').text[:50])"
```

## Database Management

### Local Database Queries
```bash
# View diocese data
python -c "
from core.db import get_supabase_client
db = get_supabase_client()
result = db.table('Dioceses').select('id, Name, State').limit(10).execute()
for diocese in result.data:
    print(f'{diocese[\"id\"]}: {diocese[\"Name\"]}, {diocese[\"State\"]}')
"

# Count parishes
python -c "
from core.db import get_supabase_client
db = get_supabase_client()
count = len(db.table('Parishes').select('id').execute().data)
print(f'Total parishes: {count}')
"
```

### Data Cleanup
```bash
# Clear test data (careful!)
python scripts/cleanup_test_data.py

# Reset specific diocese data
python scripts/reset_diocese.py --diocese_id 123
```

## Debugging

### Common Issues

1. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Chrome Driver Issues**
   ```bash
   # Update webdriver
   python -c "from selenium import webdriver; from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"
   ```

3. **API Key Errors**
   ```bash
   # Verify .env file
   cat .env | grep -v "^#"
   ```

4. **Database Connection Issues**
   ```bash
   # Test connection
   python -c "from core.db import get_supabase_client; print(get_supabase_client().table('Dioceses').select('count').execute())"
   ```

### Log Debugging

```bash
# View recent logs
tail -f logs/pipeline.log

# Search for errors
grep -i error logs/pipeline.log

# View specific diocese extraction
grep "Diocese.*123" logs/pipeline.log
```

### Chrome Debugging

```bash
# Run with visible Chrome (for debugging)
export CHROME_VISIBLE=true
python extract_schedule.py --num_parishes 1
```

## Performance Optimization

### For Development Speed

```bash
# Use smaller limits
python run_pipeline_monitored.py \
  --max_parishes_per_diocese 5 \
  --num_parishes_for_schedule 3 \
  --diocese_id 123

# Skip expensive steps
python run_pipeline_monitored.py \
  --skip_schedules \
  --skip_reporting
```

### Chrome Performance
```bash
# Add to your shell profile for faster Chrome startup
export CHROME_USER_DATA_DIR=/tmp/chrome-dev
export WDM_LOCAL_CACHE=/tmp/webdriver-cache
```

## VS Code Configuration

### Recommended Extensions
- Python
- Pylance
- Python Docstring Generator
- GitLens

### launch.json
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Run Pipeline",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/run_pipeline_monitored.py",
            "args": [
                "--max_parishes_per_diocese", "5",
                "--num_parishes_for_schedule", "3",
                "--monitoring_url", "http://localhost:8000"
            ],
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

## Troubleshooting

### Pipeline Stuck/Slow
1. Check Chrome processes: `ps aux | grep chrome`
2. Clear Chrome cache: `rm -rf /tmp/chrome-*`
3. Restart with smaller limits
4. Check network connectivity

### Memory Issues
1. Monitor usage: `htop` or `ps aux --sort=-%mem | head`
2. Reduce batch sizes in scripts
3. Clear Python cache: `find . -name "*.pyc" -delete`

### Database Issues
1. Check Supabase dashboard for service status
2. Verify API key permissions
3. Test with simple query first
4. Check rate limits

## Best Practices

### Code Quality
```bash
# Before committing
pytest                    # Run tests
python -m flake8 .       # Check style
python -m black .        # Format code
```

### Git Workflow
```bash
# Feature development
git checkout -b feature/parish-extraction-fix
# ... make changes ...
git add .
git commit -m "Fix parish extraction timeout issue"
git push origin feature/parish-extraction-fix
```

### Data Safety
- Always test with small limits first
- Use `--diocese_id` to limit scope during development
- Back up database before major changes
- Monitor extraction progress in dashboard

## Docker Development

### Building and Testing Pipeline Container
```bash
# Build pipeline container locally
docker build -f Dockerfile.pipeline -t diocesan-vitality-pipeline:test .

# Run pipeline container with environment file
docker run --rm --env-file .env diocesan-vitality-pipeline:test

# Test with specific arguments
docker run --rm --env-file .env diocesan-vitality-pipeline:test python run_pipeline.py --skip_schedules

# Debug pipeline container interactively
docker run -it --rm --env-file .env diocesan-vitality-pipeline:test /bin/bash

# Test Chrome/ChromeDriver setup in container
docker run --rm diocesan-vitality-pipeline:test google-chrome --version
docker run --rm diocesan-vitality-pipeline:test python -c "from webdriver_manager.chrome import ChromeDriverManager; print('ChromeDriver OK')"
```

### Building Backend and Frontend Containers
```bash
# Build backend container
docker build -t diocesan-vitality-backend:test ./backend

# Build frontend container
docker build -t diocesan-vitality-frontend:test ./frontend

# Test all containers before production deployment
docker build -t diocesan-vitality-backend:test ./backend
docker build -t diocesan-vitality-frontend:test ./frontend
docker build -f Dockerfile.pipeline -t diocesan-vitality-pipeline:test .
```

## IDE Configuration

### VS Code Setup

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
      "name": "Run Pipeline",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/run_pipeline_monitored.py",
      "args": [
        "--max_parishes_per_diocese", "5",
        "--num_parishes_for_schedule", "3",
        "--monitoring_url", "http://localhost:8000"
      ],
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}"
    },
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

### Recommended VS Code Extensions
- Python
- Pylance
- Python Docstring Generator
- GitLens
- Docker
- Kubernetes

## Code Quality Setup

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
        language_version: python3.12

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

### Code Formatting and Linting
```bash
# Format Python code
python -m black .

# Check Python code style
python -m flake8 . --exclude=venv,node_modules --max-line-length=88

# Format JavaScript/React code (in frontend directory)
cd frontend && npm run lint
```

## Advanced Testing

### Docker Testing Strategy
```bash
# Test production builds locally before deploying
docker build -t diocesan-vitality-backend:test ./backend
docker build -t diocesan-vitality-frontend:test ./frontend
docker build -f Dockerfile.pipeline -t diocesan-vitality-pipeline:test .

# Tag for staging environment testing (if available)
docker tag diocesan-vitality-backend:test $DOCKER_USERNAME/diocesan-vitality:backend-test
docker tag diocesan-vitality-frontend:test $DOCKER_USERNAME/diocesan-vitality:frontend-test
docker tag diocesan-vitality-pipeline:test $DOCKER_USERNAME/diocesan-vitality:pipeline-test
```

### Integration Testing
```bash
# Test API endpoints while backend is running
curl http://localhost:8000/api
curl http://localhost:8000/api/dioceses
curl http://localhost:8000/api/monitoring/status

# Test WebSocket monitoring connection
# Open browser dev tools and test WebSocket at ws://localhost:8000/ws/monitoring
```

### End-to-End Pipeline Testing
```bash
# Full pipeline test with minimal data
python run_pipeline.py \
  --max_dioceses 1 \
  --max_parishes_per_diocese 2 \
  --num_parishes_for_schedule 1

# Test monitoring-enabled pipeline
python run_pipeline_monitored.py \
  --diocese_id 123 \
  --max_parishes_per_diocese 5 \
  --monitoring_url http://localhost:8000
```

## Production Deployment Troubleshooting

### Issue: Updated Docker Images Not Reflected in Production

**Problem**: After building and pushing updated Docker images and syncing ArgoCD, the application still shows the old version.

**Root Cause**: Kubernetes deployments using image tags without version numbers won't automatically pull updated images, even with `imagePullPolicy: Always`.

**Solution**: Force restart the deployments:
```bash
# Force restart deployments to pull latest images
kubectl rollout restart deployment/frontend-deployment -n diocesan-vitality
kubectl rollout restart deployment/backend-deployment -n diocesan-vitality
kubectl rollout restart deployment/pipeline-deployment -n diocesan-vitality

# Verify new pods are running
kubectl get pods -n diocesan-vitality

# Check image SHA of new pods (optional)
kubectl get pod <pod-name> -n diocesan-vitality -o jsonpath='{.status.containerStatuses[0].imageID}'
```

### Production Deployment Workflow
```bash
# 1. Build and push images
docker build -t $DOCKER_USERNAME/diocesan-vitality:backend ./backend
docker build -t $DOCKER_USERNAME/diocesan-vitality:frontend ./frontend
docker build -f Dockerfile.pipeline -t $DOCKER_USERNAME/diocesan-vitality:pipeline .

docker push $DOCKER_USERNAME/diocesan-vitality:backend
docker push $DOCKER_USERNAME/diocesan-vitality:frontend
docker push $DOCKER_USERNAME/diocesan-vitality:pipeline

# 2. Sync ArgoCD application

# 3. Force deployment restart (if using same tags)
kubectl rollout restart deployment/frontend-deployment -n diocesan-vitality
kubectl rollout restart deployment/backend-deployment -n diocesan-vitality

# 4. Verify deployment
kubectl get pods -n diocesan-vitality
```

## Continuous Integration

### GitHub Actions Workflow
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
        python-version: '3.12'

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

## Development Workflow

### Feature Development Process
```bash
# 1. Create feature branch
git checkout -b feature/your-feature-name

# 2. Set up environment
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)

# 3. Start services (see Environment Setup section for details)
cd backend && uvicorn main:app --reload  # Terminal 1
cd frontend && npm run dev               # Terminal 2

# 4. Make changes and test
python extract_dioceses.py --max_dioceses 1
pytest tests/ -v

# 5. Test Docker builds before committing
docker build -t diocesan-vitality-backend:test ./backend
docker build -t diocesan-vitality-frontend:test ./frontend
docker build -f Dockerfile.pipeline -t diocesan-vitality-pipeline:test .

# 6. Commit and push
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature-name
```

## Architecture Overview

### Local Development Stack
- **Backend**: FastAPI Python application (http://localhost:8000)
- **Frontend**: React app with Vite (http://localhost:5173)
- **Database**: Supabase (PostgreSQL) - remote connection
- **Monitoring**: WebSocket-based real-time dashboard
- **Pipeline**: Python extraction scripts with Chrome WebDriver

### Production Stack
- **Frontend**: React app served by NGINX
- **Backend**: FastAPI Python application
- **Pipeline**: Kubernetes Deployment with monitoring integration
- **Database**: Supabase (PostgreSQL)
- **Infrastructure**: Kubernetes with ArgoCD GitOps
- **Container Registry**: Docker Hub

## Quick Reference

### Most Common Commands
```bash
# Daily development workflow
source venv/bin/activate
# Start services (see Environment Setup section)
cd backend && uvicorn main:app --reload &
python run_pipeline_monitored.py --diocese_id 123 --max_parishes_per_diocese 10

# Quick test single parish
python extract_parishes.py --diocese_id 123 --max_parishes 1

# Debug specific parish website
python extract_schedule.py --num_parishes 1 --parish_id 456
```

### Key Files
- `run_pipeline_monitored.py` - Main pipeline with monitoring
- `core/db.py` - Database utilities
- `core/ai_client.py` - AI/LLM integration
- `core/driver.py` - Chrome WebDriver setup
- `config.py` - Configuration constants
- `.env` - Local environment variables