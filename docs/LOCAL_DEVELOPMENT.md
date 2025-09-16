# Local Development Guide

This guide provides everything you need to develop and test the Diocesan Vitality system locally.

## 🚀 Quick Start

### Prerequisites
- **Python 3.12+** and **Node.js 20+**
- **Google Chrome** browser installed
- **API Keys**: Supabase, Google Gemini AI, Google Custom Search

### Complete Setup (5 minutes)

1. **Clone and Setup Environment**
   ```bash
   git clone https://github.com/your-repo/diocesan-vitality.git
   cd diocesan-vitality

   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**
   ```bash
   # Copy environment template
   cp .env.example .env

   # Edit .env file with your API keys:
   # SUPABASE_URL="your_supabase_url"
   # SUPABASE_KEY="your_supabase_key"
   # GENAI_API_KEY="your_google_genai_api_key"
   # SEARCH_API_KEY="your_google_search_api_key"
   # SEARCH_CX="your_google_search_engine_id"
   ```

3. **Start All Services**
   ```bash
   # Terminal 1 - Backend
   cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

   # Terminal 2 - Frontend
   cd frontend && npm install && npm run dev

   # Terminal 3 - Pipeline
   source venv/bin/activate
   python run_pipeline.py --max_parishes_per_diocese 5
   ```

4. **Access Applications**
   - **Dashboard**: http://localhost:5173
   - **Backend API**: http://localhost:8000/docs

## 📋 Detailed Prerequisites

- **Python 3.12+**: Required for pipeline scripts and backend
- **Node.js 20+**: Required for frontend development
- **Chrome Browser**: Selenium WebDriver requires Chrome for automated browsing
- **API Keys**: Required for cloud services:
  - **Supabase**: Database access (URL + Service Role Key)
  - **Google Gemini AI**: Content analysis and parish directory detection
  - **Google Custom Search**: Enhanced search capabilities
- **Active Internet Connection**: Required for web scraping and API calls

## 🔧 Detailed Development Setup

### Environment Variables Configuration

Create a `.env` file in the project root with the following structure:

```bash
# Database Configuration
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your_supabase_service_role_key"

# AI Integration
GENAI_API_KEY="your_google_gemini_api_key"

# Search Integration
SEARCH_API_KEY="your_google_custom_search_api_key"
SEARCH_CX="your_custom_search_engine_id"

# Docker Hub (for deployment)
DOCKER_USERNAME="your_dockerhub_username"
DOCKER_PASSWORD="your_dockerhub_password_or_token"
```

### Getting API Keys

**1. Supabase Setup:**
- Create account at [supabase.com](https://supabase.com)
- Create new project → Get URL and service role key from Settings > API

**2. Google Gemini AI:**
- Visit [Google AI Studio](https://aistudio.google.com)
- Create API key for Gemini model access

**3. Google Custom Search:**
- Create project in [Google Cloud Console](https://console.cloud.google.com)
- Enable Custom Search API → Create credentials
- Setup Custom Search Engine at [cse.google.com](https://cse.google.com)

### Chrome Installation

**Linux (Ubuntu/Debian):**
```bash
wget -O- https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update && sudo apt install google-chrome-stable
```

**Other Platforms:**
Download from [google.com/chrome](https://www.google.com/chrome/)

## 🧪 Testing & Development Commands

### Pipeline Testing

For comprehensive command examples and parameters, see the **[📝 Commands Guide](COMMANDS.md)**.

**Quick Testing Examples:**
```bash
# Test with minimal data
python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 5 --skip_dioceses

# Debug single parish
python extract_parishes.py --diocese_id 123 --max_parishes 1

# Individual pipeline steps
python extract_dioceses.py
python async_extract_parishes.py --diocese_id 123 --num_parishes_per_diocese 10
```

**→ See [Commands Guide](COMMANDS.md) for complete testing and debugging commands.**

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