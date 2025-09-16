# Local Development Guide

This guide provides everything you need to develop and test the Diocesan Vitality system locally.

## 🚀 Quick Start

For complete setup instructions, see the main **[Getting Started section in README.md](../README.md#getting-started)**.

## 📋 Prerequisites

- Python 3.12+
- Node.js 20+
- Chrome browser (for Selenium WebDriver)
- Active internet connection
- Valid API keys (see [Environment Setup](../README.md#environment-setup))

## 🔧 Development Setup

### 1. Environment Setup
Follow the **[Environment Setup](../README.md#environment-setup)** section in the main README.

### 2. Start Development Services

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
→ Backend API available at http://localhost:8000

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install  # First time only
npm run dev
```
→ Frontend UI available at http://localhost:5173

**Terminal 3 - Pipeline:**
```bash
source venv/bin/activate

# Full pipeline with monitoring
python run_pipeline.py --monitoring_url http://localhost:8000 \
  --max_parishes_per_diocese 10 --num_parishes_for_schedule 5

# Quick test with single diocese
python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 5
```

## 🧪 Testing & Development Commands

### Pipeline Testing
```bash
# Test with minimal data
python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 5 \
  --skip_dioceses --skip_parish_directories

# Debug single parish
python extract_parishes.py --diocese_id 123 --max_parishes 1

# Individual pipeline steps
python extract_dioceses.py
python find_parishes.py --diocese_id 123
python async_extract_parishes.py --diocese_id 123 --num_parishes_per_diocese 10
```

### Database Testing
```bash
# Test database connection
python -c "from core.db import get_supabase_client; print('DB:', get_supabase_client().table('Dioceses').select('*').limit(1).execute())"

# Test distributed coordination tables (if using distributed scaling)
python -c "
from core.distributed_work_coordinator import DistributedWorkCoordinator
coordinator = DistributedWorkCoordinator()
print('✅ Coordination tables accessible')
"
```

### API Testing
```bash
# Test backend endpoints
curl http://localhost:8000/api/dioceses
curl http://localhost:8000/api/monitoring/status

# Test frontend build
cd frontend && npm run build
```

## 🐳 Docker Development

### Building Images for Testing
```bash
# Build all images locally for testing
docker build -f backend/Dockerfile -t diocesan-vitality:backend-dev backend/
docker build -f frontend/Dockerfile -t diocesan-vitality:frontend-dev frontend/
docker build -f Dockerfile.pipeline -t diocesan-vitality:pipeline-dev .

# Test pipeline container
docker run --rm --env-file .env diocesan-vitality:pipeline-dev python run_pipeline.py --skip_schedules
```

### Production Deployment
For production deployments, see the **[🚀 Deployment Guide](DEPLOYMENT_GUIDE.md)** which covers:
- Timestamped image tagging
- GitOps workflow with ArgoCD
- Complete deployment process

## 📊 Monitoring & Debugging

### Real-time Monitoring
- **Dashboard**: http://localhost:5173
- **API Status**: http://localhost:8000/api/monitoring/status
- **WebSocket**: Connect to `ws://localhost:8000/ws/monitoring`

### Common Development Commands
```bash
# View logs
tail -f logs/pipeline.log

# Monitor system resources
htop

# Clear Chrome cache (if issues)
rm -rf /tmp/chrome-*

# Check running processes
ps aux | grep chrome
ps aux | grep python
```

### Debugging Issues

**Chrome WebDriver Issues:**
```bash
# Update webdriver
python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"

# Run with visible Chrome (for debugging)
export CHROME_VISIBLE=true
python extract_schedule.py --num_parishes 1
```

**API Connection Issues:**
```bash
# Verify environment variables
cat .env | grep -v "^#"

# Test individual API keys
python -c "from core.ai_client import get_genai_client; print('AI:', get_genai_client().generate_content('Hello').text[:50])"
```

## 🏗️ Architecture Overview

### Local Development Stack
- **Backend**: FastAPI (http://localhost:8000)
- **Frontend**: React + Vite (http://localhost:5173)
- **Database**: Supabase PostgreSQL (remote)
- **Pipeline**: Python scripts with Chrome WebDriver
- **Monitoring**: WebSocket-based real-time dashboard

### Key Files
- `run_pipeline.py` - Main pipeline with monitoring
- `distributed_pipeline_runner.py` - Distributed scaling version
- `core/db.py` - Database utilities
- `core/distributed_work_coordinator.py` - Multi-pod coordination
- `backend/main.py` - FastAPI backend
- `frontend/src/` - React frontend

## 📚 Additional Documentation

- **[📈 Scaling Guide](../k8s/SCALING_README.md)** - Horizontal scaling setup
- **[🚀 Deployment Guide](DEPLOYMENT_GUIDE.md)** - Production deployment
- **[⚙️ Environment Setup](../README.md#environment-setup)** - Configuration and API keys
- **[🏗️ Architecture](ARCHITECTURE.md)** - System architecture details
- **[📊 Monitoring](MONITORING.md)** - Logging and monitoring setup
- **[🗄️ Database](DATABASE.md)** - Database schema and operations

## 💡 Best Practices

### Development Workflow
1. **Start with small datasets** using `--diocese_id` and low limits
2. **Use monitoring** with `--monitoring_url http://localhost:8000`
3. **Test changes locally** before building Docker images
4. **Follow the deployment guide** for production releases

### Code Quality
```bash
# Before committing
pytest                    # Run tests
python -m black .         # Format code
python -m flake8 .        # Check style
```

### Data Safety
- Always test with `--diocese_id` to limit scope
- Use small `--max_parishes_per_diocese` values during development
- Monitor extraction progress in the dashboard
- Back up database before major schema changes