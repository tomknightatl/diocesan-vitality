# Diocesan Vitality Data Project - Architecture Documentation

## Project Overview

The United States Conference of Catholic Bishops (Diocesan Vitality) Data Project is a comprehensive data collection and analysis system for U.S. Catholic dioceses and parishes. It employs automated web scraping, AI-powered content analysis, and modern web technologies to build and maintain a detailed database of Catholic institutions across the United States.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Data Sources                             │
│  (Diocesan Vitality Website, Diocese Websites, Parish Websites)             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Data Extraction Pipeline (Python)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │Extract   │→│Find      │→│Extract   │→│Extract   │          │
│  │Dioceses  │ │Parishes  │ │Parishes  │ │Schedules │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Supabase Database                             │
│         (PostgreSQL - Cloud Hosted)                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Web Application                               │
│  ┌──────────────┐              ┌──────────────┐                │
│  │   Frontend   │◄────API─────►│   Backend    │                │
│  │   (React)    │              │  (FastAPI)   │                │
│  └──────────────┘              └──────────────┘                │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Kubernetes Infrastructure                        │
│                    (with ArgoCD GitOps)                         │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Data Extraction Layer

| Technology | Purpose |
|------------|---------|
| **Python 3.x** | Core runtime environment |
| **Selenium WebDriver** | Dynamic JavaScript content scraping |
| **BeautifulSoup4** | HTML parsing and navigation |
| **Google Gemini AI** | Intelligent content analysis and parish directory detection |
| **Pandas** | Data manipulation and processing |
| **Tenacity** | Retry logic with exponential backoff |
| **Requests** | HTTP client for simple requests |
| **WebDriver Manager** | Automatic ChromeDriver management |

### Backend API

| Technology | Purpose |
|------------|---------|
| **FastAPI** | Modern, high-performance Python web framework |
| **Uvicorn** | Lightning-fast ASGI server |
| **Supabase Python Client** | Database connectivity and operations |
| **Python-dotenv** | Environment variable management |
| **Psycopg2** | PostgreSQL adapter for Python |

### Frontend Application

| Technology | Purpose |
|------------|---------|
| **React 19** | Component-based UI framework |
| **Vite** | Next-generation frontend build tool |
| **React Bootstrap** | Pre-built React components |
| **Bootstrap 5** | CSS framework for responsive design |
| **ESLint** | Code quality and consistency |

### Infrastructure & Deployment

| Technology | Purpose |
|------------|---------|
| **Docker** | Application containerization |
| **Kubernetes** | Container orchestration platform |
| **ArgoCD** | GitOps continuous deployment |
| **GitHub Container Registry** | Container image storage |

### Data Storage

| Technology | Purpose |
|------------|---------|
| **Supabase** | Managed PostgreSQL database service |
| **PostgreSQL** | Relational database system |

## Core Components

### 1. Data Extraction Pipeline

The pipeline consists of four sequential stages:

#### Stage 1: Extract Dioceses (`extract_dioceses.py`)
- Scrapes the official Diocesan Vitality website
- Extracts diocese names, addresses, and official websites
- Stores data in the `Dioceses` table

#### Stage 2: Find Parish Directories (`find_parishes.py`)
- Analyzes diocese websites using AI
- Locates parish directory pages
- Uses Google Gemini AI for intelligent link classification
- Stores URLs in `DiocesesParishDirectory` table

#### Stage 3: Extract Parishes (`extract_parishes.py`)
- Employs specialized extractors for different platforms
- Supports multiple website architectures:
  - Diocese Card Layout
  - Parish Finder (eCatholic)
  - HTML Tables
  - Interactive Maps
  - Generic patterns
- Extracts detailed parish information
- Stores data in `Parishes` table

#### Stage 4: Extract Schedules (`extract_schedule.py`)
- Visits individual parish websites
- Extracts liturgical schedules (Adoration, Reconciliation)
- Stores schedule data in `ParishSchedules` table

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
/api                    # Health check endpoint
/api/dioceses          # Diocese data endpoint
```

- RESTful API design
- CORS middleware for cross-origin requests
- Supabase integration for data access
- Environment-based configuration

#### Frontend (React + Vite)
```
src/
├── App.jsx            # Main application component
├── App.css           # Application styles
├── main.jsx          # Application entry point
└── index.css         # Global styles
```

- Single Page Application (SPA)
- Bootstrap integration for UI components
- Responsive design
- API proxy configuration for development

### 4. Kubernetes Deployment Architecture

```yaml
Namespace: diocesan-vitality
├── Deployments
│   ├── backend-deployment
│   └── frontend-deployment
├── Services
│   ├── backend-service (ClusterIP)
│   └── frontend-service (ClusterIP)
├── Ingress
│   └── main-ingress (NGINX)
├── Secrets
│   ├── supabase-credentials
│   └── ghcr-secret
└── ArgoCD ApplicationSet
    └── diocesan-vitality-applicationset
```

## Database Schema

### Tables Structure

#### Dioceses Table
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| Name | TEXT | Diocese name |
| Address | TEXT | Physical address |
| Website | TEXT | Official website URL |
| extracted_at | TIMESTAMP | Extraction timestamp |

#### DiocesesParishDirectory Table
| Column | Type | Description |
|--------|------|-------------|
| diocese_url | TEXT | Diocese website URL |
| parish_directory_url | TEXT | Parish directory page URL |
| found | TEXT | Discovery status |
| found_method | TEXT | Detection method used |
| updated_at | TIMESTAMP | Last update timestamp |

#### Parishes Table
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| Name | TEXT | Parish name |
| Status | TEXT | Parish status |
| Street Address | TEXT | Street address |
| City | TEXT | City |
| State | TEXT | State |
| Zip Code | TEXT | Zip code |
| Phone Number | TEXT | Contact phone |
| Web | TEXT | Parish website |
| diocese_url | TEXT | Parent diocese URL |
| extraction_method | TEXT | Extraction method used |
| confidence_score | FLOAT | Extraction confidence |
| extracted_at | TIMESTAMP | Extraction timestamp |

#### ParishSchedules Table
| Column | Type | Description |
|--------|------|-------------|
| url | TEXT | Parish website URL |
| offers_reconciliation | BOOLEAN | Reconciliation availability |
| reconciliation_info | TEXT | Reconciliation schedule |
| offers_adoration | BOOLEAN | Adoration availability |
| adoration_info | TEXT | Adoration schedule |
| scraped_at | TIMESTAMP | Scraping timestamp |

## Key Architectural Patterns

### 1. Modular Pipeline Design
- Independent, composable extraction stages
- Orchestration through `run_pipeline.py`
- Configurable processing limits
- Skip capability for individual stages

### 2. Intelligent Extraction Strategy
- AI-powered content analysis
- Platform-specific extractors
- Fallback mechanisms
- Confidence scoring

### 3. Microservices Architecture
- Separation of frontend and backend
- Independent scaling
- API-first design
- Service mesh communication

### 4. Cloud-Native Design
- Stateless containers
- External configuration
- Horizontal scaling capability
- Health monitoring

### 5. GitOps Deployment
- Declarative infrastructure
- Automated synchronization
- Version-controlled deployments
- Self-healing capabilities

## Security Architecture

### Authentication & Authorization
- Supabase service role keys for backend
- Kubernetes secrets management
- Image pull secrets for private registries

### Network Security
- CORS configuration for API access
- Ingress controller with TLS termination
- Service-to-service communication within cluster

### Data Protection
- Environment variable isolation
- Encrypted secrets storage
- Row Level Security (RLS) in database

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
- Time-series visualizations
- Extraction success rates

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