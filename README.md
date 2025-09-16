# Diocese Data Project

**🌐 LIVE SYSTEM**: The production system is running at [https://diocesanvitality.org](https://diocesanvitality.org) with real-time data collection and monitoring.

**For local development**: Follow the "Getting Started" and "Environment Setup" sections below to configure your development environment.

## Overview

This project is a comprehensive data collection and analysis system for U.S. Catholic dioceses and parishes. It employs advanced web scraping techniques, AI-powered content analysis, and automated data processing to build and maintain a detailed database of Catholic institutions across the United States. The system collects information from the official conference website and individual diocese websites, including diocese details, parish directories, and detailed parish information.

## Cloud Architecture

The system runs in the cloud using a **two-tier architecture** designed for cost efficiency and scalability:

### 🌐 **Tier 1: Always-On Web Services**
**Deployment**: Single small node (s-1vcpu-2gb) running continuously
- **Frontend**: React dashboard serving the user interface at [diocesanvitality.org](https://diocesanvitality.org)
- **Backend**: FastAPI server providing data APIs and real-time monitoring
- **Database**: Supabase (managed PostgreSQL) for persistent data storage
- **Cost**: Minimal (~$12/month) - runs 24/7 to serve users

### 🚀 **Tier 2: On-Demand Data Collection**
**Deployment**: Dedicated node (s-2vcpu-4gb) that scales from 0→1 when needed
- **Pipeline**: Automated data extraction and processing system
- **Chrome/Selenium**: Headless browser automation for web scraping
- **AI Processing**: Google Gemini integration for content analysis
- **Cost**: Pay-per-use (~$0.02/hour) - only runs when collecting data

### 💡 **Cost-Optimized Design**
- **Always available**: Users can access the dashboard and data anytime
- **Scheduled extraction**: Pipeline runs on-demand or scheduled basis
- **Auto-scaling**: Data collection node scales to 0 when idle (no cost)
- **Resource isolation**: Web services and data collection don't compete for resources

### 🔄 **Operational Flow**
1. **Continuous**: Frontend + Backend serve users on small node
2. **On-demand**: Scale up dedicated node for data collection
3. **Real-time**: Live extraction monitoring via WebSocket dashboard
4. **Auto-shutdown**: Pipeline node scales to 0 after completion
5. **Fresh data**: Updated information available immediately via web interface

## How It Works

The Data Extraction Pipeline is a multi-step process that systematically collects and organizes Catholic diocese and parish information from across the United States.

![Data Extraction Pipeline Architecture](./docs/architecture-diagram.svg)

### Pipeline Steps

1. **Extract Dioceses**: Scrapes the official conference website for all U.S. dioceses
2. **Find Parish Directories**: Uses AI to locate parish directory pages on diocese websites
3. **Extract Parishes**: Collects detailed parish information using specialized extractors
4. **Extract Schedules**: Visits individual parish websites to gather mass and service times

## Distributed Pipeline Architecture

**Production Deployment**: The system currently runs a **distributed pipeline** designed for continuous operation and horizontal scaling, which differs from the traditional sequential pipeline described above.

### How the Distributed Pipeline Works

When you see pipeline pods running in Kubernetes, they operate in **distributed mode**:

#### ✅ **Continuous Operation**
- Pods run **indefinitely** (not one-time execution)
- Workers register with a coordination system and process dioceses continuously
- Each worker gets assigned specific dioceses to avoid conflicts
- Workers automatically restart processing when new work becomes available

#### ⚙️ **Modified Pipeline Steps**
The distributed pipeline **skips initial setup steps** and focuses on the core extraction:

1. **Diocese Data**: ~~Extract Dioceses~~ (assumes diocese data already exists in database)
2. **Parish Directories**: ~~Find Parish Directories~~ (assumes directory URLs already discovered)
3. **✅ Parish Extraction**: Workers coordinate to extract parishes from assigned dioceses
4. **📊 Reporting**: Only the "lead" worker generates statistical reports

#### 🔄 **Worker Coordination**
- **Database-backed coordination**: Workers register in `pipeline_workers` table
- **Diocese assignment**: Work is distributed via `diocese_work_assignments` table
- **Conflict prevention**: No two workers process the same diocese simultaneously
- **Automatic failover**: If a worker becomes unresponsive, its work is reassigned
- **Real-time monitoring**: Workers report status to the monitoring dashboard

#### 📈 **Scaling Behavior**
- **HPA (Horizontal Pod Autoscaler)**: Automatically scales from 1-5 workers based on CPU/memory
- **Pod anti-affinity**: Each worker gets its own dedicated node
- **Graceful scaling**: Workers coordinate during scale-up/scale-down events

### When to Use Each Pipeline Mode

| **Traditional Pipeline** | **Distributed Pipeline** |
|--------------------------|---------------------------|
| Initial data collection   | Production continuous operation |
| Complete database setup   | Ongoing data maintenance |
| Single-machine execution  | Kubernetes cluster deployment |
| `python run_pipeline.py`  | Kubernetes pods with `distributed_pipeline_runner.py` |

### Monitoring the Distributed Pipeline

- **Dashboard**: [https://diocesanvitality.org/dashboard](https://diocesanvitality.org/dashboard)
- **Active Workers**: Shows currently running workers and their assignments
- **Real-time Logs**: Live extraction progress and status updates
- **Performance Metrics**: CPU, memory, and extraction rate monitoring

## Key Features

### 🚀 **Core Data Extraction**
- **Automated Diocese Discovery**: Scrapes the official conference website to collect diocese information
- **AI-Powered Parish Directory Detection**: Uses Google's Gemini AI to intelligently identify parish directory pages
- **Advanced Web Scraping**: Employs Selenium with retry logic and pattern detection for robust data extraction
- **Multi-Platform Parish Extraction**: Supports various website platforms including SquareSpace, WordPress, eCatholic, and custom implementations

### ⚡ **Performance & Optimization**
- **High-Performance Concurrent Processing**: Asyncio-based extraction with 60% performance improvement
- **🤖 ML-Based URL Prediction**: Machine learning system that reduces 404 errors by 50% through intelligent URL discovery
- **🔗 Enhanced URL Management**: Success-based URL memory with "golden URLs" prioritization
- **⚡ Adaptive Timeout Management**: Dynamic timeout optimization based on site complexity and response patterns
- **💾 Intelligent Caching**: Smart caching system with content-aware TTL management
- **🛡️ Circuit Breaker Protection**: Automatic failure detection and recovery for external services

### 📊 **Analytics & Monitoring**
- **🖥️ Hybrid Multi-Worker Dashboard**: Real-time extraction monitoring at [diocesanvitality.org](https://diocesanvitality.org)
- **🔧 Worker Selector**: Switch between aggregate view and individual worker monitoring
- **🛡️ Enhanced Circuit Breaker Visualization**: 17+ circuit breakers with health-based sorting and color coding
- **📊 Health Scoring**: Dynamic health calculation with green/yellow/red indicators
- **🔍 Comprehensive URL Visit Tracking**: Detailed visit analytics with response times, quality scores, and error classification
- **📈 Quality-Weighted ML Training**: Advanced machine learning training using visit success data
- **🎯 Intelligent Parish Prioritization**: Multi-factor scoring for optimal extraction order

### 🤝 **Respectful Automation**
- **🤖 Gold-Standard Web Ethics**: Comprehensive robots.txt compliance with immediate cessation when blocked
- **⏱️ Thoughtful Rate Limiting**: 2-5 second delays between requests per domain with randomized timing
- **🛡️ Advanced Blocking Detection**: Real-time detection of 403 Forbidden, rate limiting, and Cloudflare protection
- **📊 Transparency & Accountability**: Detailed logging of respectful behavior and blocking compliance
- **🔍 Proper Identification**: Clear User-Agent strings identifying research purpose
- **💡 Ethical Data Collection**: Prioritizing website owners' preferences over data collection efficiency

### 🔧 **Advanced Features**
- **Interactive Parish Finder Support**: Specialized extractors for JavaScript-based parish finder interfaces
- **Cloud Database Integration**: Stores data in Supabase with automated upserts and conflict resolution
- **Comprehensive Logging**: Detailed extraction statistics and error tracking
- **🔄 Parallel Processing Framework**: Domain-aware rate limiting with resource management

## Why Respectful Automation?

Our investment in respectful automation reflects a core commitment to **ethical data collection** and **sustainable web practices**. Here's why this matters:

### 🎯 **Mission Alignment**
- **Catholic Social Teaching**: Our approach reflects Catholic principles of respect, stewardship, and responsible use of resources
- **Community Partnership**: Parish websites serve their communities first - our research comes second
- **Long-term Sustainability**: Respectful practices ensure continued access and community trust

### 📊 **Practical Benefits**
- **Higher Success Rates**: Respectful behavior reduces blocking and improves data quality
- **Sustainable Operations**: Avoids IP bans and maintains long-term access to data sources
- **Legal Compliance**: Proactive adherence to robots.txt and web standards reduces legal risks
- **Community Relations**: Demonstrates good faith to diocesan IT administrators

### 🛡️ **Technical Excellence**
- **Professional Standards**: Industry best practices for automated data collection
- **Error Reduction**: Proper rate limiting reduces server stress and timeout errors
- **Quality Assurance**: Respectful timing allows for complete page loads and accurate extraction
- **Monitoring Transparency**: Clear logging enables accountability and troubleshooting

### 💡 **Research Ethics**
- **Academic Integrity**: Maintains high standards for data collection methodology
- **Transparency**: Open documentation of our respectful practices and limitations
- **Reproducibility**: Other researchers can build upon our ethical framework
- **Community Benefit**: Collected data serves the broader Catholic research community

**Our respectful automation isn't just about following rules—it's about building technology that serves the Catholic community with dignity and care.**

---

## Project Architecture

The system uses a modern, scalable architecture designed for automated data collection and real-time monitoring:

- **Python Pipeline**: Core extraction engine with AI-powered content analysis
- **React Dashboard**: Real-time monitoring interface with WebSocket updates
- **Kubernetes Deployment**: Production-ready containerized infrastructure
- **Supabase Database**: Cloud PostgreSQL with comprehensive schema

**→ See [Architecture Documentation](docs/ARCHITECTURE.md) for detailed technical information.**

## Project Structure

### Key Components
- **`run_pipeline.py`**: Main orchestration script for the entire extraction pipeline
- **`async_extract_parishes.py`**: High-performance concurrent extraction (60% faster)
- **`core/`**: Essential utilities for database, WebDriver, and circuit breaker management
- **`frontend/`**: React dashboard with real-time monitoring
- **`backend/`**: FastAPI server for monitoring and data APIs
- **`k8s/`**: Kubernetes deployment manifests

### Technology Stack
- **Python 3.12+** with Selenium, BeautifulSoup, Google Gemini AI
- **React + FastAPI** for real-time monitoring dashboard
- **Supabase PostgreSQL** for cloud database storage
- **Docker + Kubernetes** for containerized deployment

**→ See [Architecture Documentation](docs/ARCHITECTURE.md) for complete technical details, database schema, and component specifications.**

## 📚 Documentation

- **[🚀 Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Complete guide for deploying new Docker images
- **[📈 Scaling Guide](k8s/SCALING_README.md)** - Horizontal scaling and distributed pipeline setup
- **[🔧 Local Development](docs/LOCAL_DEVELOPMENT.md)** - Development setup and testing

## Getting Started

For complete setup instructions including prerequisites, environment configuration, and development workflow, see the **[🔧 Local Development Guide](docs/LOCAL_DEVELOPMENT.md)**.

### Quick Setup Summary

1. **Prerequisites**: Python 3.12+, Node.js 20+, Chrome browser
2. **Environment**: Clone repository, create virtual environment, install dependencies
3. **Configuration**: Set up `.env` file with API keys
4. **Development**: Start backend, frontend, and pipeline services

**→ Follow the [Local Development Guide](docs/LOCAL_DEVELOPMENT.md) for detailed step-by-step instructions.**



## Running the System

The system can be run in two environments: **local development** for testing and development, or **cloud production** for continuous operation with real-time monitoring.

### 🌐 **Cloud Production (Live System)**

**Access the live system**: [https://diocesanvitality.org/dashboard](https://diocesanvitality.org/dashboard)

The production system runs automatically in Kubernetes with:
- **Real-time dashboard**: Monitor live data extraction progress
- **Automatic pipeline**: Continuously collects fresh diocese and parish data
- **Auto-scaling**: Data collection infrastructure scales up/down as needed
- **High availability**: Frontend and backend available 24/7

**For system administrators:**
- Pipeline management via Kubernetes scaling (requires cluster access)
- Monitoring and logs available through the web dashboard
- See `/k8s/README.md` for deployment and management instructions

### 💻 **Local Development**

For development, testing, or running custom extractions on your local machine, see the **[🔧 Local Development Guide](docs/LOCAL_DEVELOPMENT.md)** for complete setup instructions.

### 📝 **Command Reference**

For comprehensive command examples, parameters, and usage instructions for all scripts, see the **[📝 Commands Guide](docs/COMMANDS.md)**.

**Quick Examples:**
```bash
# Full pipeline with monitoring
source venv/bin/activate && python run_pipeline.py --max_parishes_per_diocese 10

# Process specific diocese
python run_pipeline.py --diocese_id 2024 --max_parishes_per_diocese 25

# High-performance concurrent extraction
python async_extract_parishes.py --diocese_id 2024 --pool_size 6 --batch_size 12
```

**→ See [Commands Guide](docs/COMMANDS.md) for complete command reference and examples.**




## Reporting and Analytics

### `report_statistics.py`

This script connects to the Supabase database to provide statistics and visualizations of the collected data. It reports the current number of records in key tables and generates charts showing how these numbers have changed over time.

**Usage:**

```bash
python report_statistics.py
```

The script will generate PNG image files (e.g., `dioceses_records_over_time.png`, `parishes_records_over_time.png`) in the current directory, visualizing the record counts over time.

---



## Data Coverage

The production system continuously maintains current data:
- **196 U.S. Catholic Dioceses** (all active dioceses)
- **17,000+ Parish Records** with detailed information
- **High Success Rates**: 85-95% successful parish directory detection
- **Rich Data Fields**: Including addresses, coordinates, contact info, and schedules
- **Live Updates**: Data refreshed automatically through continuous pipeline operation
- **Real-time Dashboard**: Current extraction status visible at [diocesanvitality.org/dashboard](https://diocesanvitality.org/dashboard)

## Contributing

The project is designed for extensibility:
- **New Extractors**: Add support for additional website platforms in `parish_extractors.py`
- **Enhanced AI**: Improve content analysis in `llm_utils.py`
- **Additional Data Points**: Extend `ParishData` model in `parish_extraction_core.py`
- **Quality Improvements**: Enhance validation in the pattern detection system

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- The official conference website for providing publicly accessible diocese information
- Google AI for Gemini API access enabling intelligent content analysis
- Supabase for reliable cloud database infrastructure
- The open-source community for the excellent web scraping and data processing libraries

---

## Web Application

The project includes a modern web application providing real-time access to collected data and extraction monitoring. The system is fully deployed in production and available at [https://diocesanvitality.org](https://diocesanvitality.org).

### Live Production System

**🌐 Access the Dashboard**: [https://diocesanvitality.org/dashboard](https://diocesanvitality.org/dashboard)

Features:
- **Real-time extraction monitoring**: Watch live data collection progress
- **Interactive data browser**: Explore dioceses and parishes
- **Live logs**: Four-step extraction process visibility
- **System health**: Circuit breaker status and performance metrics

### Architecture

-   **/frontend**: React SPA with real-time WebSocket dashboard
-   **/backend**: FastAPI server with monitoring and data APIs
-   **/pipeline**: Containerized extraction system with live monitoring
-   **/k8s**: Production Kubernetes deployment manifests

### Container Registry

The web application uses **Docker Hub** for container image storage. Docker Hub provides:
- **Free public repositories**: Unlimited public container images
- **Simple authentication**: Standard Docker login workflow
- **Wide compatibility**: Supported by all Kubernetes distributions
- **No vendor lock-in**: Works independently of any specific cloud provider

**→ See [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) for complete Docker Hub setup and deployment instructions.**

---

## Documentation

### 📖 Core Documentation
- **[README.md](README.md)**: Main project documentation
- **[docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)**: Complete local development setup and workflow
- **[docs/COMMANDS.md](docs/COMMANDS.md)**: Complete command reference for all scripts
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: System architecture and design patterns
- **[docs/MONITORING.md](docs/MONITORING.md)**: Real-time monitoring and operational visibility

### ⚡ Performance & Optimization
- **[docs/ASYNC_PERFORMANCE_GUIDE.md](docs/ASYNC_PERFORMANCE_GUIDE.md)**: High-performance concurrent extraction optimization
- **[docs/ml-model-training.md](docs/ml-model-training.md)**: ML-based URL prediction system training

### 🚀 Deployment & Infrastructure
- **[docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)**: Docker and Kubernetes deployment instructions
- **[docs/DATABASE.md](docs/DATABASE.md)**: Database schema and data management
- **[docs/supabase-setup.md](docs/supabase-setup.md)**: Database setup instructions
- **[docs/AUTHENTICATION.md](docs/AUTHENTICATION.md)**: Authentication and security configuration
- **[docs/CLOUDFLARE.md](docs/CLOUDFLARE.md)**: Cloudflare tunnel and DNS configuration

### 🖥️ Application Components
- **[backend/README.md](backend/README.md)**: FastAPI backend server documentation
- **[frontend/README.md](frontend/README.md)**: React frontend application setup

### ☁️ Kubernetes & GitOps
- **[k8s/README.md](k8s/README.md)**: Kubernetes deployment and pipeline management
- **[k8s/SCALING_README.md](k8s/SCALING_README.md)**: Horizontal scaling documentation
- **[k8s/argocd/README.md](k8s/argocd/README.md)**: ArgoCD GitOps configuration
- **[k8s/argocd/bitnami-sealed-secrets-application-set-README.md](k8s/argocd/bitnami-sealed-secrets-application-set-README.md)**: Sealed secrets management
- **[k8s/argocd/cloudflare-tunnel-applicationsetREADME.md](k8s/argocd/cloudflare-tunnel-applicationsetREADME.md)**: Cloudflare tunnel configuration

### 🧪 Testing & Quality Assurance
- **[tests/TESTING.md](tests/TESTING.md)**: Testing framework and test procedures

### 🗄️ Database & Migrations
- **[sql/migrations/README.md](sql/migrations/README.md)**: Database migration procedures

### 📊 Advanced Features
- **[docs/DIOCESE_PARISH_DIRECTORY_OVERRIDE.md](docs/DIOCESE_PARISH_DIRECTORY_OVERRIDE.md)**: Directory URL override system