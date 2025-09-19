# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

includeClaudeAttribution: false

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
```

### Testing & Environment
```bash
make env-check     # Check environment configuration
make db-check      # Test database connection
make ai-check      # Test AI API connection
make webdriver-check  # Test Chrome WebDriver
```

### Frontend Commands
```bash
cd frontend
npm run dev        # Start development server
npm run build      # Build for production
npm run lint       # Lint frontend code
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
The system operates in two modes:

1. **Traditional Pipeline**: Sequential execution for initial setup/development
   - `extract_dioceses.py` → `find_parishes.py` → `async_extract_parishes.py` → `extract_schedule.py`

2. **Distributed Pipeline**: Production continuous operation
   - Workers coordinate via database tables (`pipeline_workers`, `diocese_work_assignments`)
   - Automatic workload distribution and failover
   - Real-time monitoring dashboard

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
Required environment variables in `.env`:
- `SUPABASE_URL`, `SUPABASE_KEY`: Database connection
- `GENAI_API_KEY`: Google Gemini AI for content analysis
- `SEARCH_API_KEY`, `SEARCH_CX`: Google Custom Search
- `MONITORING_URL`: Backend monitoring endpoint (default: http://localhost:8000)

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

### Database Schema
Primary tables: `dioceses`, `parishes`, `mass_schedules`, `pipeline_workers`, `diocese_work_assignments`
See `docs/DATABASE.md` for complete schema documentation.

### Performance Optimization
- **Async Processing**: 60% performance improvement with concurrent extraction
- **Intelligent Caching**: Content-aware TTL management
- **Adaptive Timeouts**: Dynamic optimization based on site complexity
- **Quality-Weighted ML Training**: Success-based URL discovery optimization