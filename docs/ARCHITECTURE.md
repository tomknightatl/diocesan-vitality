# Diocesan Vitality Data Project - Architecture Documentation

> **Note:** The visual architecture diagram (`architecture-diagram.svg`) shows the legacy 4-step pipeline and does not yet reflect the current 5-step pipeline with distributed architecture, chart generation, and Kubernetes deployment. Refer to this document for the most up-to-date architectural information.

## Project Overview

The United States Conference of Catholic Bishops (Diocesan Vitality) Data Project is a comprehensive data collection and analysis system for U.S. Catholic dioceses and parishes. It employs automated web scraping, AI-powered content analysis, and modern web technologies to build and maintain a detailed database of Catholic institutions across the United States.

## System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Data Sources                              │
│   (Diocesan Vitality Website, Diocese Websites, Parish Websites) │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│         Distributed Data Extraction Pipeline (Python)             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │ Extract  │→│  Find    │→│ Extract  │→│ Extract  │→│Generate││
│  │ Dioceses │ │Parishes  │ │ Parishes │ │Schedules │ │Reports ││
│  │  (Step1) │ │ (Step2)  │ │ (Step3)  │ │ (Step4)  │ │(Step5) ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘│
│             HPA 1-5 Pods │ Worker Specialization                 │
└─────────────────────────┼────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Supabase Database                              │
│              (PostgreSQL - Cloud Hosted)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Dioceses  │ │ Diocese  │ │ Parishes │ │ Parish   │           │
│  │          │ │Directory │ │          │ │  Data    │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│              Kubernetes Application Layer                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Frontend   │◄───┤   Backend   │    │  Pipeline   │         │
│  │   (React)   │    │  (FastAPI)  │    │   Workers   │         │
│  │             │    │             │    │   (1-5)     │         │
│  │ Fetches     │    │ Generates & │    │ Runs Steps  │         │
│  │ charts via  │    │ caches      │    │ 1-4 only    │         │
│  │ /api/charts │    │ charts in   │    │             │         │
│  │             │    │ /tmp/charts │    │             │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                   │
│  Chart Generation: Backend on-demand with 1-hour cache TTL       │
└──────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│            ArgoCD GitOps + Cloudflare Tunnel                      │
│          (Automated Deployment & Secure Access)                   │
└──────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Data Extraction Layer

| Technology             | Purpose                                                     |
| ---------------------- | ----------------------------------------------------------- |
| **Python 3.x**         | Core runtime environment                                    |
| **Selenium WebDriver** | Dynamic JavaScript content scraping                         |
| **BeautifulSoup4**     | HTML parsing and navigation                                 |
| **Google Gemini AI**   | Intelligent content analysis and parish directory detection |
| **Pandas**             | Data manipulation and processing                            |
| **Tenacity**           | Retry logic with exponential backoff                        |
| **Requests**           | HTTP client for simple requests                             |
| **WebDriver Manager**  | Automatic ChromeDriver management                           |

### Backend API

| Technology                 | Purpose                                       |
| -------------------------- | --------------------------------------------- |
| **FastAPI**                | Modern, high-performance Python web framework |
| **Uvicorn**                | Lightning-fast ASGI server                    |
| **Supabase Python Client** | Database connectivity and operations          |
| **Python-dotenv**          | Environment variable management               |
| **Psycopg2**               | PostgreSQL adapter for Python                 |

### Frontend Application

| Technology          | Purpose                             |
| ------------------- | ----------------------------------- |
| **React 19**        | Component-based UI framework        |
| **Vite**            | Next-generation frontend build tool |
| **React Bootstrap** | Pre-built React components          |
| **Bootstrap 5**     | CSS framework for responsive design |
| **ESLint**          | Code quality and consistency        |

### Infrastructure & Deployment

| Technology     | Purpose                          |
| -------------- | -------------------------------- |
| **Docker**     | Application containerization     |
| **Kubernetes** | Container orchestration platform |
| **ArgoCD**     | GitOps continuous deployment     |
| **Docker Hub** | Container image storage          |

### Data Storage

| Technology     | Purpose                             |
| -------------- | ----------------------------------- |
| **Supabase**   | Managed PostgreSQL database service |
| **PostgreSQL** | Relational database system          |

## Core Components

### 1. Data Extraction Pipeline

The pipeline consists of four sequential stages with both standard and high-performance processing options:

#### Pipeline Workflow

1. **Diocese Collection** → Scrapes the official source for basic diocese information
2. **Parish Directory Discovery** → AI-powered detection of parish listing pages
3. **Parish Extraction** → Advanced scraping with platform-specific extractors
4. **Schedule Extraction** → Extracts liturgical schedules from parish websites
5. **Reporting & Analytics** → Generates statistical reports and visualizations

#### Pipeline Stages

#### Stage 1: Extract Dioceses (`extract_dioceses.py`)

- Scrapes the official Diocesan Vitality website
- Extracts diocese names, addresses, and official websites
- Stores data in the `Dioceses` table

#### Stage 2: Find Parish Directories (`find_parishes.py`)

- Analyzes diocese websites using AI
- Locates parish directory pages
- Uses Google Gemini AI for intelligent link classification
- Stores URLs in `DiocesesParishDirectory` table

#### Stage 3: Extract Parishes (`async_extract_parishes.py`)

- High-performance async extraction with concurrent processing
- Employs specialized extractors for different platforms:
  - Diocese Card Layout
  - Parish Finder (eCatholic)
  - HTML Tables
  - Interactive Maps
  - Generic patterns
- Extracts detailed parish information
- Stores data in `Parishes` table
- 60% performance improvement over sequential processing

#### Stage 4: Extract Schedules (`extract_schedule_respectful.py`)

- Visits individual parish websites
- Extracts liturgical schedules (Adoration, Reconciliation)
- Implements respectful automation with rate limiting
- Respects robots.txt and crawl delays
- Stores schedule data in `ParishData` table

#### Stage 5: Generate Reports (`report_statistics.py`)

- Analyzes extracted data across all tables
- Generates time-series visualizations with matplotlib
- Creates PNG charts showing extraction progress over time
- Saves charts to shared volume (`/app/charts`)
- Charts served dynamically via backend API

### 2. Pattern Detection System

The system includes intelligent pattern detection (`PatternDetector` class) that:

- **Identifies Platform Types**:
  - SquareSpace
  - WordPress
  - Drupal
  - eCatholic
  - Custom CMS
  - Static HTML

- **Detects Listing Types**:
  - Interactive Maps
  - Static Tables
  - Card Grids
  - Paginated Lists
  - Parish Finders
  - Diocese Card Layouts

- **Determines Extraction Strategy**:
  - Selects appropriate extractor based on detected patterns
  - Assigns confidence scores
  - Identifies JavaScript requirements

### 3. Web Application Architecture

#### Backend API (FastAPI)

```python
/api                         # Health check endpoint
/api/summary                 # Summary statistics
/api/dioceses                # Diocese data with pagination/filtering
/api/parishes                # Parish data with pagination/filtering
/api/monitoring/status       # Real-time pipeline status
/api/monitoring/websocket    # WebSocket for live updates
/api/charts/{chart_name}     # Serve generated chart images
```

**Key Features:**

- RESTful API design
- CORS middleware for cross-origin requests
- Supabase integration for data access
- WebSocket support for real-time monitoring
- File serving for dynamically generated charts
- Environment-based configuration

**Chart Serving Architecture:**

- Pipeline worker generates charts in Step 5 (reporting)
- Charts saved to shared PersistentVolume at `/app/charts`
- Backend mounts same volume and serves charts via `/api/charts/{chart_name}`
- Frontend fetches charts as HTTP responses (no direct volume access needed)
- Charts update automatically when reporting worker runs

#### Frontend (React + Vite)

```
src/
├── App.jsx            # Main application component
├── Dashboard.jsx      # Real-time monitoring dashboard
├── Reports.jsx        # Statistical reports and charts
├── Dioceses.jsx       # Diocese data tables
├── Parishes.jsx       # Parish data tables
├── App.css            # Application styles
├── main.jsx           # Application entry point
└── index.css          # Global styles
```

**Key Features:**

- Single Page Application (SPA)
- Bootstrap integration for UI components
- Responsive design
- Real-time WebSocket integration for live updates
- Dynamic chart loading from backend API
- API proxy configuration for development

### 4. Kubernetes Deployment Architecture

```yaml
Namespace: diocesan-vitality-{env}
├── Deployments
│   ├── backend-deployment
│   ├── frontend-deployment
│   └── pipeline-deployment (with HPA)
├── Services
│   ├── backend-service (ClusterIP)
│   └── frontend-service (ClusterIP)
├── PersistentVolumeClaims
│   └── charts-pvc (ReadWriteMany, 1Gi)
├── Secrets
│   ├── diocesan-vitality-secrets
│   └── cloudflared-token
├── HorizontalPodAutoscaler
│   └── pipeline-hpa (1-5 replicas, CPU/Memory based)
└── ArgoCD ApplicationSet
    └── diocesan-vitality-{env}-applicationset
```

**Volume Mount Architecture:**

- `charts-pvc`: Shared PersistentVolume for chart images
  - Mounted to pipeline pod at `/app/charts` (read-write)
  - Mounted to backend pod at `/app/charts` (read-only for serving)
  - Frontend has no volume mount (accesses via backend API)

**Multi-Environment Setup:**

- Development: `diocesan-vitality-dev` namespace
- Staging: `diocesan-vitality-stg` namespace
- Production: `diocesan-vitality-prd` namespace

## Database Schema

### Tables Structure

#### Dioceses Table

| Column       | Type      | Description          |
| ------------ | --------- | -------------------- |
| id           | UUID      | Primary key          |
| Name         | TEXT      | Diocese name         |
| Address      | TEXT      | Physical address     |
| Website      | TEXT      | Official website URL |
| extracted_at | TIMESTAMP | Extraction timestamp |

#### DiocesesParishDirectory Table

| Column               | Type      | Description               |
| -------------------- | --------- | ------------------------- |
| diocese_url          | TEXT      | Diocese website URL       |
| parish_directory_url | TEXT      | Parish directory page URL |
| found                | TEXT      | Discovery status          |
| found_method         | TEXT      | Detection method used     |
| updated_at           | TIMESTAMP | Last update timestamp     |

#### Parishes Table

| Column                     | Type      | Description                           |
| -------------------------- | --------- | ------------------------------------- |
| id                         | UUID      | Primary key                           |
| Name                       | TEXT      | Parish name                           |
| Status                     | TEXT      | Parish status (Parish, Mission, etc.) |
| Street Address             | TEXT      | Street address                        |
| City                       | TEXT      | City                                  |
| State                      | TEXT      | State                                 |
| Zip Code                   | TEXT      | Zip code                              |
| Phone Number               | TEXT      | Contact phone                         |
| Web                        | TEXT      | Parish website                        |
| diocese_id                 | INTEGER   | Foreign key to Dioceses table         |
| diocese_url                | TEXT      | Parent diocese URL                    |
| parish_directory_url       | TEXT      | Source directory URL                  |
| extraction_method          | TEXT      | Extraction method used                |
| confidence_score           | FLOAT     | Extraction confidence (0.0-1.0)       |
| extracted_at               | TIMESTAMP | Extraction timestamp                  |
| detail_extraction_success  | BOOLEAN   | Detail extraction status              |
| is_blocked                 | BOOLEAN   | Website blocking detection            |
| blocking_type              | TEXT      | Type of blocking detected             |
| robots_txt_check           | JSONB     | robots.txt compliance info            |
| respectful_automation_used | BOOLEAN   | Respectful automation flag            |
| created_at                 | TIMESTAMP | Record creation timestamp             |

#### ParishData Table

| Column         | Type      | Description                          |
| -------------- | --------- | ------------------------------------ |
| id             | UUID      | Primary key                          |
| parish_id      | UUID      | Foreign key to Parishes table        |
| fact_type      | TEXT      | Type of data (Adoration, Confession) |
| fact_value     | TEXT      | Extracted schedule information       |
| extraction_url | TEXT      | Source URL for extraction            |
| extracted_at   | TIMESTAMP | Extraction timestamp                 |
| created_at     | TIMESTAMP | Record creation timestamp            |

## Key Architectural Patterns

### 1. Distributed Pipeline Architecture

**Multi-Pod Coordination:**

- Pipeline runs as horizontally-scaled Kubernetes deployment (1-5 pods via HPA)
- Database-backed work coordination (`pipeline_workers`, `diocese_work_assignments` tables)
- Automatic failover and load balancing across worker pods
- Real-time heartbeat monitoring (30-second intervals)

**Worker Specialization:**

- **Discovery Workers** (`worker_type=discovery`): Diocese + Parish directory discovery (Steps 1-2)
- **Extraction Workers** (`worker_type=extraction`): Parish detail extraction (Step 3)
- **Schedule Workers** (`worker_type=schedule`): Mass schedule extraction (Step 4)
- **Reporting Workers** (`worker_type=reporting`): Analytics and chart generation (Step 5)
- **All Workers** (`worker_type=all`): Run all steps sequentially (default)

**Work Distribution:**

- Diocese-based work partitioning for parallel processing
- Claim-based locking to prevent duplicate work
- Automatic work reassignment on worker failure
- Continuous processing without cooldown periods

**Pipeline Orchestration:**

- Production: `distributed_pipeline_runner.py` with multi-pod coordination
- Local Development: `run_pipeline.py` for single-threaded execution
- Configurable processing limits per stage
- Real-time monitoring via WebSocket API

### 2. Intelligent Extraction Strategy

- AI-powered content analysis with Google Gemini
- Platform-specific extractors (eCatholic, SquareSpace, WordPress, Drupal, etc.)
- Fallback mechanisms with confidence scoring (0.0-1.0)
- ML-based URL prediction reducing 404 errors by 50%
- Circuit breaker pattern (17+ circuit breakers) for resilience

### 3. Microservices Architecture

- Separation of frontend, backend, and pipeline components
- Independent horizontal scaling with HPA
- API-first design with RESTful endpoints
- WebSocket support for real-time monitoring
- Service mesh communication within Kubernetes

### 4. Cloud-Native Design

- Stateless containers with immutable infrastructure
- External configuration via environment variables and secrets
- Horizontal scaling capability (HPA for pipeline: 1-5 pods)
- Health monitoring (liveness and readiness probes)
- Persistent storage via PersistentVolumeClaims

### 5. GitOps Deployment

- Declarative infrastructure with Kustomize overlays
- Automated synchronization via ArgoCD
- Version-controlled deployments (Git as source of truth)
- Self-healing capabilities
- Multi-environment support (dev, staging, production)

## Respectful Automation

The system implements comprehensive ethical web scraping practices:

### robots.txt Compliance

- Automatic robots.txt fetching and parsing
- Respect for `User-agent: *` and custom bot rules
- Crawl delay observance (default: 1 second minimum)
- Disallowed path checking before each request

### Rate Limiting

- Configurable delays between requests (1-30 seconds)
- Adaptive rate limiting based on site responsiveness
- Domain-specific rate limiting
- Exponential backoff on errors

### Blocking Detection

- Comprehensive blocking pattern recognition (Cloudflare, Incapsula, reCAPTCHA, etc.)
- Automatic blocking status tracking in database
- Evidence collection for debugging
- Graceful degradation on blocked sites

### Resource Conservation

- Efficient caching to minimize redundant requests
- Batch processing to reduce database operations
- Connection pooling for database and HTTP clients
- WebDriver cleanup and resource management

## Security Architecture

### Authentication & Authorization

- Supabase service role keys for backend
- Kubernetes secrets management
- Image pull secrets for private registries

### Network Security

- CORS configuration for API access with allowlist
- Ingress controller with TLS termination (Cloudflare Tunnel)
- Service-to-service communication within cluster (ClusterIP)
- No public exposure of backend or database

### Data Protection

- Environment variable isolation
- Encrypted secrets storage (Sealed Secrets)
- Row Level Security (RLS) in database
- Secure API key management

## Performance Optimizations

### Extraction Pipeline

- Retry logic with exponential backoff
- Parallel processing capability
- Caching mechanisms
- Rate limiting compliance

### Web Application

- Multi-stage Docker builds
- Static asset optimization
- NGINX caching
- Database connection pooling

### Infrastructure

- Horizontal pod autoscaling
- Resource limits and requests
- Load balancing
- CDN integration (Cloudflare)

## Monitoring & Observability

### Logging

- Structured logging with Python logger
- Centralized log aggregation
- Error tracking and alerting

### Metrics

- Extraction statistics tracking
- API performance metrics
- Database query performance

### Reporting

- `report_statistics.py` for data analytics
- Time-series visualizations with matplotlib
- Extraction success rates and progress tracking
- PNG chart generation saved to shared volume (`/app/charts`)
- Charts served via backend API (`/api/charts/{chart_name}`)
- Automatic chart updates on reporting worker execution

## Development Workflow

### Local Development

1. Virtual environment setup (`venv`)
2. Environment variables (`.env` file)
3. Docker Compose for services
4. Hot reloading for frontend/backend

### CI/CD Pipeline

```
Code Push → GitHub → Docker Build → GHCR Push → ArgoCD Sync → K8s Deploy
```

### Testing Strategy

- Unit tests with pytest
- Mock external dependencies
- Fixture-based test data
- Integration testing

## Scalability Considerations

### Horizontal Scaling

- Stateless application design
- Database connection pooling
- Load balancer distribution
- Pod autoscaling

### Vertical Scaling

- Resource optimization
- Memory management
- CPU utilization monitoring

### Data Scaling

- Batch processing capability
- Incremental updates
- Indexed database queries
- Partitioning strategies

## Conclusion

The Diocesan Vitality Data Project demonstrates a modern, scalable approach to data collection and presentation. The architecture combines intelligent web scraping, cloud-native deployment, and modern web technologies to create a robust system for managing Catholic diocese and parish information. The modular design allows for easy maintenance, scaling, and future enhancements while maintaining high reliability and performance standards.
