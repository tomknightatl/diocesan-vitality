# Local Development Guide

This guide provides everything you need to develop and test the Diocesan Vitality system locally.

## 📋 Prerequisites (Required First!)

Before starting development, ensure you have these components installed in the correct order:

### 1. System Requirements
- **Python 3.12+**: Download from [python.org](https://python.org)
- **Node.js 20+**: Download from [nodejs.org](https://nodejs.org)
- **Git**: Version control system
- **Active Internet Connection**: Required for web scraping and API calls

### 2. Browser and WebDriver Installation (Critical!)

**⚠️ Browser and WebDriver must be installed BEFORE running any pipeline commands!**

The system requires a browser (Chrome/Chromium) and corresponding WebDriver. Installation varies by platform and architecture:

#### **Linux x86-64 (Standard Desktop/Server):**
```bash
# Install Chrome browser
wget -O- https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update && sudo apt install google-chrome-stable

# Verify installation
google-chrome --version
```

#### **Linux ARM64 (Raspberry Pi, Apple Silicon, etc.):**
```bash
# Chrome is not available for ARM64, use Chromium instead
sudo apt update && sudo apt install chromium-browser chromium-chromedriver

# Verify installation
chromium-browser --version
chromedriver --version

# Ensure ChromeDriver is in PATH
which chromedriver  # Should return /usr/bin/chromedriver
```

#### **macOS (Intel and Apple Silicon):**
```bash
# Install Chrome
brew install --cask google-chrome

# Install ChromeDriver
brew install chromedriver

# For Apple Silicon Macs, you may need Rosetta for some drivers
# If you encounter issues, try:
brew install --cask chromedriver

# Verify installation
google-chrome --version
chromedriver --version
```

#### **Windows:**
```powershell
# Install Chrome
# Download from https://www.google.com/chrome/ and run installer as Administrator

# ChromeDriver will be automatically managed by the Python webdriver-manager
# No manual installation required
```

#### **Docker/Containerized Environments:**
```dockerfile
# For x86-64 containers
RUN wget -O- https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable

# For ARM64 containers
RUN apt-get update && apt-get install -y chromium-browser chromium-chromedriver
```

#### **Troubleshooting WebDriver Issues:**

**Architecture Mismatch (Common on ARM64):**
```bash
# Check your architecture
uname -m

# If you see "aarch64" and get "Exec format error":
sudo apt install chromium-chromedriver  # Use system ChromeDriver
sudo rm -rf ~/.wdm/drivers/chromedriver  # Remove incompatible drivers

# Verify the fix
file /usr/bin/chromedriver  # Should show ARM aarch64
```

**WebDriver Not Found:**
```bash
# Check ChromeDriver location
which chromedriver

# If not found, install manually:
# Linux ARM64:
sudo apt install chromium-chromedriver

# Linux x86-64:
# Download from https://chromedriver.chromium.org/
```

**Permission Issues:**
```bash
# Fix ChromeDriver permissions
sudo chmod +x /usr/bin/chromedriver

# Fix cache directory permissions
sudo chown -R $USER:$USER ~/.wdm/
```

### 3. API Keys Setup (Required Before Running Pipeline)

You need these API keys **before** starting development:

**Supabase Database:**
- Create account at [supabase.com](https://supabase.com)
- Create new project → Settings > API → Copy URL and service role key

**Google Gemini AI:**
- Visit [Google AI Studio](https://aistudio.google.com)
- Create API key for Gemini model access

**Google Custom Search (Optional but Recommended):**
- Create project in [Google Cloud Console](https://console.cloud.google.com)
- Enable Custom Search API → Create credentials
- Setup Custom Search Engine at [cse.google.com](https://cse.google.com)

## 🚀 Quick Start (5 Minutes)

Once prerequisites are installed, follow these steps:

### Step 1: Clone and Setup Environment
```bash
git clone https://github.com/your-repo/diocesan-vitality.git
cd diocesan-vitality

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
nano .env  # or use your preferred editor
```

**Required .env configuration:**
```bash
# Database Configuration
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your_supabase_service_role_key"

# AI Integration
GENAI_API_KEY="your_google_gemini_api_key"

# Search Integration (Optional)
SEARCH_API_KEY="your_google_custom_search_api_key"
SEARCH_CX="your_custom_search_engine_id"

# Monitoring
MONITORING_URL="http://localhost:8000"

# Docker Hub (for deployment only)
DOCKER_USERNAME="your_dockerhub_username"
DOCKER_PASSWORD="your_dockerhub_password_or_token"
```

### Step 3: Verify Installation
```bash
# Test all components in order
make env-check     # Check environment variables
make db-check      # Test database connection
make ai-check      # Test AI API connection
make webdriver-check  # Test Chrome WebDriver

# Manual WebDriver test (if make commands fail)
source .venv/bin/activate
python -c "
from core.driver import setup_driver
driver = setup_driver()
if driver:
    print('✅ WebDriver: SUCCESS')
    driver.quit()
else:
    print('❌ WebDriver: FAILED - Check browser installation')
"

# Test pipeline with minimal data
python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 1
```

### Step 4: Start Development Environment
```bash
# Option A: Start everything at once
make start-full

# Option B: Start components individually
# Terminal 1 - Backend
make start

# Terminal 2 - Frontend (new terminal)
cd frontend && npm install && npm run dev

# Terminal 3 - Test pipeline (new terminal)
source .venv/bin/activate
make pipeline
```

### Step 5: Access Applications
- **Dashboard**: http://localhost:5173
- **Backend API**: http://localhost:8000/docs
- **Monitoring**: http://localhost:5173/dashboard

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

# Monitoring
MONITORING_URL="http://localhost:8000"

# Docker Hub (for deployment)
DOCKER_USERNAME="your_dockerhub_username"
DOCKER_PASSWORD="your_dockerhub_password_or_token"
```

### Frontend Setup
```bash
cd frontend

# Install Node.js dependencies
npm install

# Start development server
npm run dev

# Build for production (testing)
npm run build

# Lint frontend code
npm run lint
```

### Backend Setup
```bash
cd backend

# Start FastAPI development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the makefile
cd .. && make start
```

## 🧪 Testing & Development Commands

### Environment Verification
```bash
# Check all environment requirements
make env-check

# Individual checks
make db-check      # Test database connection
make ai-check      # Test AI API connection
make webdriver-check  # Test Chrome WebDriver
```

### Pipeline Testing

For comprehensive command examples and parameters, see the **[📝 Commands Guide](COMMANDS.md)**.

**Quick Testing Examples:**
```bash
# Quick test with minimal data
make pipeline

# Test specific diocese
make pipeline-single DIOCESE_ID=123

# Full pipeline with monitoring
python run_pipeline.py --max_parishes_per_diocese 10 --monitoring_url http://localhost:8000

# Distributed pipeline (production-like)
python distributed_pipeline_runner.py --max_parishes_per_diocese 10

# Specialized workers (single image deployment)
python distributed_pipeline_runner.py --worker_type discovery    # Steps 1-2
python distributed_pipeline_runner.py --worker_type extraction   # Step 3
python distributed_pipeline_runner.py --worker_type schedule     # Step 4
python distributed_pipeline_runner.py --worker_type reporting    # Step 5

# Debug single parish
python async_extract_parishes.py --diocese_id 123 --pool_size 1 --batch_size 1
```

**Individual Pipeline Steps:**
```bash
# Step 1: Extract dioceses
python extract_dioceses.py

# Step 2: Find parishes in dioceses
python find_parishes.py

# Step 3: Extract parish details
python async_extract_parishes.py --diocese_id 123

# Step 4: Extract schedules
python extract_schedule.py --diocese_id 123
```

### Database Testing
```bash
# Test database connection
python -c "from core.db import get_supabase_client; print('DB:', get_supabase_client().table('Dioceses').select('*').limit(1).execute())"

# Test distributed coordination tables
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

# Test WebSocket monitoring
# Connect to ws://localhost:8000/ws/monitoring
```

## 🐳 Docker Development

### Building Images for Testing
```bash
# Build all images locally for testing
docker build -f backend/Dockerfile -t diocesan-vitality:backend-dev backend/
docker build -f frontend/Dockerfile -t diocesan-vitality:frontend-dev frontend/
docker build -f Dockerfile.pipeline -t diocesan-vitality:pipeline-dev .

# Test pipeline container
docker run --rm --env-file .env diocesan-vitality:pipeline-dev python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 5
```

## ☸️ Cluster Development Environment

### Overview

In addition to local development, you can now develop directly in a Kubernetes cluster using the development environment. This provides a production-like environment for testing changes and running the full distributed pipeline.

### Prerequisites for Cluster Development

1. **kubectl access** to the development cluster:
   ```bash
   # Check available contexts
   kubectl config get-contexts

   # Switch to development cluster (when available)
   kubectl config use-context do-nyc2-dv-dev
   ```

2. **Docker Hub access** for pushing development images:
   ```bash
   # Login to Docker Hub
   docker login
   ```

### Cluster Development Workflow

#### Step 1: Build and Push Development Images

When developing features that need cluster testing, build and push images with development tags:

```bash
# Generate development timestamp
DEV_TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)-dev

# Build multi-architecture images for cluster compatibility
echo "🏗️ Building development images..."

# Backend
docker buildx build --platform linux/amd64,linux/arm64 \
  -f backend/Dockerfile \
  -t tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP} \
  --push backend/

# Frontend
docker buildx build --platform linux/amd64,linux/arm64 \
  -f frontend/Dockerfile \
  -t tomatl/diocesan-vitality:frontend-${DEV_TIMESTAMP} \
  --push frontend/

# Pipeline
docker buildx build --platform linux/amd64,linux/arm64 \
  -f Dockerfile.pipeline \
  -t tomatl/diocesan-vitality:pipeline-${DEV_TIMESTAMP} \
  --push .

echo "✅ Development images pushed with tag: ${DEV_TIMESTAMP}"
```

#### Step 2: Update Development Environment

Update the development Kubernetes manifests to use your new images:

```bash
# Update development patches with new image tags
sed -i "s|image: tomatl/diocesan-vitality:.*backend.*|image: tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP}|g" k8s/environments/development/development-patches.yaml
sed -i "s|image: tomatl/diocesan-vitality:.*frontend.*|image: tomatl/diocesan-vitality:frontend-${DEV_TIMESTAMP}|g" k8s/environments/development/development-patches.yaml
sed -i "s|image: tomatl/diocesan-vitality:.*pipeline.*|image: tomatl/diocesan-vitality:pipeline-${DEV_TIMESTAMP}|g" k8s/environments/development/development-patches.yaml
```

#### Step 3: Deploy via GitOps

Commit and push the changes to trigger ArgoCD deployment to the development cluster:

```bash
# Commit development changes
git add k8s/environments/development/
git commit -m "Development cluster update: ${DEV_TIMESTAMP}

🔧 Development images:
- backend: tomatl/diocesan-vitality:backend-${DEV_TIMESTAMP}
- frontend: tomatl/diocesan-vitality:frontend-${DEV_TIMESTAMP}
- pipeline: tomatl/diocesan-vitality:pipeline-${DEV_TIMESTAMP}

Feature: [describe your changes]"

# Push to trigger ArgoCD sync
git push origin develop  # Development uses develop branch
```

#### Step 4: Monitor Deployment

Watch the deployment progress in the development cluster:

```bash
# Switch to development cluster context
kubectl config use-context do-nyc2-dv-dev

# Monitor ArgoCD application sync
kubectl get application diocesan-vitality-dev -n argocd -w

# Watch pod updates
kubectl get pods -n diocesan-vitality-dev -w

# Check deployment status
kubectl get deployments -n diocesan-vitality-dev

# View logs
kubectl logs deployment/backend-deployment -n diocesan-vitality-dev --follow
kubectl logs deployment/frontend-deployment -n diocesan-vitality-dev --follow
kubectl logs deployment/extraction-deployment -n diocesan-vitality-dev --follow
```

### Development Cluster Features

#### Real-time Pipeline Testing
```bash
# Monitor distributed pipeline in development cluster
kubectl get pods -n diocesan-vitality-dev -l worker-type

# Check pipeline coordination
kubectl logs deployment/discovery-deployment -n diocesan-vitality-dev --follow
kubectl logs deployment/extraction-deployment -n diocesan-vitality-dev --follow
kubectl logs deployment/schedule-deployment -n diocesan-vitality-dev --follow
```

#### Development Database Access
```bash
# Port-forward to access development database
kubectl port-forward service/backend-service 8000:80 -n diocesan-vitality-dev

# Access development API
curl http://localhost:8000/api/dioceses
curl http://localhost:8000/api/monitoring/status
```

#### Debug and Troubleshooting
```bash
# Get detailed pod information
kubectl describe pods -n diocesan-vitality-dev

# Execute commands in development pods
kubectl exec -it deployment/backend-deployment -n diocesan-vitality-dev -- /bin/bash

# Check resource usage
kubectl top pods -n diocesan-vitality-dev
kubectl top nodes
```

### Automated Development Builds (Recommended)

Use GitHub Actions to automatically build and deploy development images:

```bash
# Push to develop branch triggers automatic development deployment
git checkout develop
git push origin develop

# Or manually trigger build via GitHub Actions
gh workflow run ci-cd-pipeline.yml -f environment=staging
```

**GitHub Actions handles:**
- Multi-architecture builds (ARM64 + AMD64)
- Automatic tagging with timestamps
- Push to Docker Hub
- Development cluster deployment
- Integration testing

### Development vs Production Workflow

| **Development Cluster** | **Production** |
|------------------------|----------------|
| Manual image builds → Push to `develop` branch | Automatic builds via CI/CD |
| Quick iteration cycle | Full test suite required |
| `k8s/environments/development/` | `k8s/environments/production/` |
| ArgoCD syncs from `develop` branch | ArgoCD syncs from `main` branch |
| Test distributed pipeline | Production data collection |

### Best Practices for Cluster Development

1. **Use development timestamps**: Add `-dev` suffix to distinguish from production
2. **Test locally first**: Verify basic functionality before cluster deployment
3. **Monitor resource usage**: Check CPU/memory limits in development cluster
4. **Use feature branches**: Create feature branches for complex changes
5. **Clean up**: Remove old development images regularly

### Development Cluster Setup

If you need to create a development cluster:

```bash
# Create development cluster infrastructure
make cluster-create CLUSTER_LABEL=dev
make tunnel-create CLUSTER_LABEL=dev
make argocd-install CLUSTER_LABEL=dev
make argocd-apps CLUSTER_LABEL=dev
make sealed-secrets-create CLUSTER_LABEL=dev
```

See the **[Infrastructure Commands](#infrastructure-commands)** section in the Makefile for complete cluster setup.

## 📊 Monitoring & Debugging

### Real-time Monitoring
- **Dashboard**: http://localhost:5173/dashboard
- **API Status**: http://localhost:8000/api/monitoring/status
- **WebSocket**: Connect to `ws://localhost:8000/ws/monitoring`

### Log Files
```bash
# View pipeline logs
tail -f scraping.log

# View backend logs
tail -f backend/logs/app.log

# Monitor all logs
tail -f *.log
```

### Common Development Commands
```bash
# Check running processes
ps aux | grep chrome
ps aux | grep python
ps aux | grep node

# Monitor system resources
htop

# Clear Chrome cache (if issues)
rm -rf /tmp/chrome-*
```

### Troubleshooting Common Issues

**Chrome WebDriver Issues:**
```bash
# Test WebDriver setup
source .venv/bin/activate
python -c "
from core.driver import setup_driver
driver = setup_driver()
if driver:
    print('✅ WebDriver working!')
    driver.quit()
else:
    print('❌ WebDriver failed')
"

# Architecture mismatch (ARM64/Raspberry Pi):
uname -m  # Check if you're on aarch64/arm64
sudo apt install chromium-chromedriver  # Use system driver
sudo rm -rf ~/.wdm/drivers/chromedriver  # Remove x86 drivers

# Verify correct architecture
file /usr/bin/chromedriver  # Should match your system architecture

# For x86-64 systems, update webdriver-manager:
python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"

# Run with visible Chrome (for debugging)
export CHROME_VISIBLE=true
python extract_schedule.py --diocese_id 123 --max_parishes 1

# Check browser installation
google-chrome --version || chromium-browser --version
which google-chrome || which chromium-browser
```

**API Connection Issues:**
```bash
# Verify environment variables
cat .env | grep -v "^#"

# Test individual API keys
python -c "from core.ai_client import get_genai_client; print('AI OK')"
python -c "from core.db import get_supabase_client; print('DB OK')"
```

**Permission Issues (Linux):**
```bash
# If apt-get permission denied during Chrome installation
sudo chown -R $USER:$USER /home/$USER/.cache
sudo apt update && sudo apt install google-chrome-stable

# If Python permission issues
sudo chown -R $USER:$USER .venv/
```

**Pipeline Hanging/Timeout Issues:**
```bash
# Check if Chrome processes are hanging
pkill -f chrome
pkill -f chromedriver

# Restart with smaller batch size
python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 5
```

## 🗄️ Database Management

### Overview

The database management system provides tools for resetting, backing up, and maintaining your local development database. The primary tool is the `reset_local_database.py` script, which automates the complete workflow of wiping your local database and restoring it from production.

### When to Use Database Reset

Use the database reset workflow when:

- **Schema Changes**: After major database schema updates that require a clean slate
- **Data Corruption**: When local data becomes corrupted or inconsistent
- **Testing Scenarios**: When you need a fresh production-like dataset for testing
- **Development Reset**: When switching between different development branches with conflicting data
- **Performance Issues**: When database performance degrades due to accumulated test data
- **Sync Issues**: When local and production databases become out of sync

### ⚠️ Safety Warnings

**CRITICAL: Database reset is a destructive operation that cannot be undone!**

- **All local data will be permanently lost**
- **Any uncommitted changes will be wiped**
- **Local test data and development entries will be replaced with production data**
- **The operation requires explicit confirmation by default**
- **Always backup important local data before proceeding**

### Step-by-Step Reset Instructions

#### Prerequisites

Before running the database reset, ensure you have:

1. **Supabase CLI installed and configured**
   ```bash
   # Install Supabase CLI
   npm install -g supabase
   # Or: brew install supabase/tap/supabase

   # Verify installation
   supabase --version
   ```

2. **Required environment variables in `.env`**
   ```bash
   # Production database credentials
   SUPABASE_URL_PRD="https://your-production-project.supabase.co"
   SUPABASE_KEY_PRD="your_production_service_role_key"

   # Development database credentials
   SUPABASE_URL_DEV="http://localhost:54321"
   SUPABASE_KEY_DEV="your_dev_service_role_key"
   SUPABASE_DB_PASSWORD_DEV="your_dev_db_password"
   ```

3. **Local Supabase instance accessible**
   ```bash
   # Check if Supabase is running
   supabase status

   # Start if not running
   supabase start
   ```

4. **Required Python dependencies**
   ```bash
   pip install supabase python-dotenv psycopg2-binary
   ```

#### Reset Workflow

The reset process performs the following operations automatically:

1. **Stops local Supabase services** - Ensures clean database state
2. **Drops all tables** - Removes all existing data and schema
3. **Restores schema** - Applies clean schema from `sql/initial_schema.sql`
4. **Copies production data** - Transfers all data from production database
5. **Restarts Supabase services** - Brings local instance back online
6. **Verifies database integrity** - Confirms successful reset

#### Running the Reset

**Standard Reset (Recommended):**
```bash
# Run with confirmation prompt
python scripts/reset_local_database.py
```

**Automated Reset (Use with Caution):**
```bash
# Skip confirmation prompt (for CI/CD or automated workflows)
python scripts/reset_local_database.py --skip-confirmation
```

### Usage Examples

#### Example 1: Standard Development Reset
```bash
# Activate virtual environment
source .venv/bin/activate

# Run reset with confirmation
python scripts/reset_local_database.py

# Expected output:
# ======================================================================
# 🔄 LOCAL DATABASE RESET WORKFLOW
# ======================================================================
# Started at: 2024-01-15 14:30:00
#
# ⚠️  WARNING: DESTRUCTIVE OPERATION
# ======================================================================
# This will COMPLETELY WIPE your local development database...
# [Confirmation prompt appears]
# Do you want to proceed? (type 'yes' to confirm): yes
#
# Step 1/6: Stopping Supabase services
# ✅ Supabase services stopped
#
# Step 2/6: Dropping all tables
# ✅ Dropped 8 tables
#
# Step 3/6: Restoring schema
# ✅ Schema restored successfully (45 statements executed)
#
# Step 4/6: Copying production data
# 📦 Copying table: Dioceses
# 📦 Copying table: Parishes
# ...
# ✅ Production data copied successfully
#
# Step 5/6: Restarting Supabase services
# ✅ Supabase services started successfully
#
# Step 6/6: Verifying database
#    Verification results:
#       Dioceses: ✅ 195 rows
#       Parishes: ✅ 1247 rows
#       ParishData: ✅ 892 rows
# ...
# ✅ Database verification passed
#
# ======================================================================
# ✅ DATABASE RESET COMPLETED SUCCESSFULLY!
# ======================================================================
# Duration: 45.32 seconds
```

#### Example 2: Automated Reset for CI/CD
```bash
# In CI/CD pipeline or automated scripts
python scripts/reset_local_database.py --skip-confirmation

# No confirmation prompt, runs immediately
# Useful for automated testing environments
```

#### Example 3: Reset After Schema Changes
```bash
# After pulling schema changes from main branch
git pull origin main

# Reset database to apply new schema
python scripts/reset_local_database.py

# Verify new schema structure
python -c "
from core.db import get_supabase_client
client = get_supabase_client()
print('Schema updated successfully')
"
```

### Troubleshooting Tips

#### Issue: Supabase CLI Not Found
**Symptoms:** `Command not found: supabase`

**Solution:**
```bash
# Install Supabase CLI
npm install -g supabase

# Or using Homebrew (macOS)
brew install supabase/tap/supabase

# Verify installation
supabase --version
```

#### Issue: Database Connection Failed
**Symptoms:** `Failed to connect to local database`, `OperationalError`

**Solution:**
```bash
# Check Supabase status
supabase status

# Start Supabase if not running
supabase start

# Verify environment variables
cat .env | grep SUPABASE

# Check database password
echo $SUPABASE_DB_PASSWORD_DEV
```

#### Issue: Permission Denied
**Symptoms:** `Permission denied`, `Access denied`

**Solution:**
```bash
# Fix script permissions
chmod +x scripts/reset_local_database.py

# Fix .env file permissions
chmod 600 .env

# Re-run with proper permissions
python scripts/reset_local_database.py
```

#### Issue: Timeout During Data Copy
**Symptoms:** `Data copy timed out after 5 minutes`

**Solution:**
```bash
# Check network connectivity
ping supabase.co

# Verify production database is accessible
python -c "
import os
from supabase import create_client
client = create_client(os.getenv('SUPABASE_URL_PRD'), os.getenv('SUPABASE_KEY_PRD'))
print('Production database accessible')
"

# Try running reset again (may be temporary network issue)
python scripts/reset_local_database.py
```

#### Issue: Schema File Not Found
**Symptoms:** `Schema file not found: sql/initial_schema.sql`

**Solution:**
```bash
# Check if schema file exists
ls -la sql/initial_schema.sql

# If missing, restore from git
git checkout sql/initial_schema.sql

# Or create from production backup
python scripts/backup_production_database.py
```

#### Issue: Verification Failed
**Symptoms:** `Verification failed for tables: Dioceses, Parishes`

**Solution:**
```bash
# Check database connection
python -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port='54322',
    database='postgres',
    user='postgres',
    password='your_password'
)
print('Database connection successful')
conn.close()
"

# Manually check tables
python -c "
from core.db import get_supabase_client
client = get_supabase_client()
result = client.table('Dioceses').select('*').limit(1).execute()
print(f'Dioceses table: {len(result.data)} rows')
"

# Re-run reset if verification fails
python scripts/reset_local_database.py
```

### Expected Output and Success Indicators

#### Successful Reset Output

A successful reset will display:

1. **Workflow Header**
   ```
   ======================================================================
   🔄 LOCAL DATABASE RESET WORKFLOW
   ======================================================================
   Started at: 2024-01-15 14:30:00
   ```

2. **Confirmation Prompt** (unless `--skip-confirmation` used)
   ```
   ⚠️  WARNING: DESTRUCTIVE OPERATION
   ======================================================================
   This will COMPLETELY WIPE your local development database...
   Do you want to proceed? (type 'yes' to confirm):
   ```

3. **Step-by-Step Progress**
   ```
   Step 1/6: Stopping Supabase services
   ✅ Supabase services stopped

   Step 2/6: Dropping all tables
   ✅ Dropped 8 tables

   Step 3/6: Restoring schema
   ✅ Schema restored successfully (45 statements executed)

   Step 4/6: Copying production data
   📦 Copying table: Dioceses
   📦 Copying table: Parishes
   ...
   ✅ Production data copied successfully

   Step 5/6: Restarting Supabase services
   ✅ Supabase services started successfully

   Step 6/6: Verifying database
   ✅ Database verification passed
   ```

4. **Success Summary**
   ```
   ======================================================================
   ✅ DATABASE RESET COMPLETED SUCCESSFULLY!
   ======================================================================
   Started at:  2024-01-15 14:30:00
   Completed at: 2024-01-15 14:30:45
   Duration:    45.32 seconds

   Your local database has been reset and is ready for use.
   ```

#### Success Indicators

✅ **All steps completed without errors**
✅ **Verification shows all key tables with data**
✅ **Supabase services are running**
✅ **Duration is reasonable (typically 30-90 seconds)**
✅ **No error messages in output**

#### Failure Indicators

❌ **Error messages with traceback**
❌ **Verification failed for one or more tables**
❌ **Supabase services failed to start**
❌ **Timeout errors during data copy**
❌ **Connection errors to production database**

### Related Database Scripts

The reset script integrates with several other database management tools:

#### `scripts/copy_database.py`
- **Purpose**: Copy data from production to development database
- **Used by**: Reset script (Step 4)
- **Tables copied**: Dioceses, Parishes, ParishData, ScheduleKeywords, etc.
- **Usage**: `python scripts/copy_database.py`

#### `scripts/backup_production_database.py`
- **Purpose**: Create full backup of production database
- **Output**: Compressed SQL file in `backup/` directory
- **Usage**: `python scripts/backup_production_database.py`
- **Recommended**: Run before major production changes

#### `scripts/init_dev_database.py`
- **Purpose**: Initialize development database schema
- **Used by**: Reset script (Step 3 - alternative method)
- **Usage**: `python scripts/init_dev_database.py`
- **Note**: Manual SQL execution may be required via Supabase dashboard

### Best Practices

1. **Always backup before reset**
   ```bash
   # Backup current local state
   python scripts/backup_production_database.py
   ```

2. **Test in development environment first**
   - Never run reset on production database
   - Always verify in local development environment
   - Use `--skip-confirmation` only in automated CI/CD

3. **Monitor reset duration**
   - Normal duration: 30-90 seconds
   - Longer durations may indicate network issues
   - Timeouts after 5 minutes for data copy step

4. **Verify after reset**
   ```bash
   # Quick verification
   python -c "
   from core.db import get_supabase_client
   client = get_supabase_client()
   print('✅ Database ready')
   "

   # Check key tables
   python -c "
   from core.db import get_supabase_client
   client = get_supabase_client()
   dioceses = client.table('Dioceses').select('*').execute()
   print(f'✅ Dioceses: {len(dioceses.data)} rows')
   "
   ```

5. **Document reset reasons**
   - Keep track of why resets were performed
   - Note any schema changes applied
   - Record any issues encountered

### Integration with Development Workflow

The database reset fits naturally into your development workflow:

```bash
# Typical development cycle
git pull origin main                    # Pull latest changes
python scripts/reset_local_database.py  # Reset database
make start                              # Start development environment
make pipeline                           # Test with fresh data
```

```bash
# Before major feature testing
git checkout feature-branch
python scripts/reset_local_database.py  # Clean slate
# Test feature with production-like data
```

```bash
# After schema migrations
git pull origin main
python scripts/reset_local_database.py  # Apply new schema
# Verify migration worked correctly
```

### Additional Resources

- **[Database Schema Documentation](DATABASE.md)** - Complete schema reference
- **[Commands Guide](COMMANDS.md)** - Additional database commands
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Production database management
- **[Supabase Documentation](https://supabase.com/docs)** - Official Supabase docs

## 🔄 Schema Development Workflow

### Overview

The schema development workflow provides a systematic approach to making, testing, and deploying database schema changes locally. This workflow integrates with the existing local development setup and uses the `scripts/apply_schema_change.py` tool to automate migration generation, application, and validation.

**Key Benefits:**
- **Automated migration generation** from local schema changes
- **Safe testing environment** with rollback capability
- **Comprehensive validation** to catch errors early
- **Integration with existing development workflow**
- **Version-controlled migrations** for team collaboration

### Prerequisites

Before starting schema development, ensure you have:

1. **Supabase CLI installed and configured**
   ```bash
   # Install Supabase CLI
   npm install -g supabase
   # Or: brew install supabase/tap/supabase

   # Verify installation
   supabase --version
   ```

2. **Local Supabase stack running**
   ```bash
   # Check if Supabase is running
   supabase status

   # Start if not running
   supabase start
   ```

3. **Python 3.8+ with required dependencies**
   ```bash
   # Ensure virtual environment is active
   source .venv/bin/activate

   # Install dependencies if needed
   pip install -r requirements.txt
   ```

4. **Schema change management script**
   ```bash
   # Make script executable
   chmod +x scripts/apply_schema_change.py

   # Verify script works
   python scripts/apply_schema_change.py --help
   ```

### Workflow Steps

#### Step 1: Make Local Schema Changes

Make your schema changes using any of these methods:

**Option A: Using Supabase Studio (GUI)**
```bash
# Open Supabase Studio
supabase studio

# Navigate to Table Editor
# Make your changes (add tables, modify columns, etc.)
```

**Option B: Using SQL via Supabase CLI**
```bash
# Execute SQL directly
supabase db query --local "
  CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
  );
"
```

**Option C: Editing migration files manually**
```bash
# Create new migration file
supabase migration new add_user_preferences

# Edit the generated file
vim supabase/migrations/20260621150000_add_user_preferences.sql
```

#### Step 2: Generate Migration from Changes

Use the schema change management script to generate a migration:

```bash
# Generate migration with descriptive name
python scripts/apply_schema_change.py --generate --name "add_user_preferences_table"

# Or use automatic workflow (recommended)
python scripts/apply_schema_change.py --auto --name "add_user_preferences_table"
```

**What happens:**
1. Script detects schema differences between migrations and actual database
2. Generates SQL migration file with timestamp prefix
3. Displays migration content for review
4. Creates file in `supabase/migrations/` directory

**Example output:**
```
2026-06-21 10:07:20 - INFO - Generating migration diff: add_user_preferences_table
2026-06-21 10:07:21 - INFO - Migration diff generated successfully: supabase/migrations/20260621100721_add_user_preferences_table.sql
2026-06-21 10:07:21 - INFO - Migration file size: 1234 bytes
2026-06-21 10:07:21 - INFO - Migration content:
--------------------------------------------------------------------------------
-- Alter table
ALTER TABLE "public"."users" ADD COLUMN "preferences" jsonb DEFAULT '{}'::jsonb;

-- Create index
CREATE INDEX "idx_users_preferences" ON "public"."users" USING gin ("preferences");
--------------------------------------------------------------------------------
```

#### Step 3: Review and Validate Migration

**Review the generated migration:**
```bash
# View the migration file
cat supabase/migrations/20260621100721_add_user_preferences_table.sql

# Or use the script's review feature
python scripts/apply_schema_change.py --generate --name "test_change"
# Script will prompt for review: yes/no/edit
```

**Validate the current schema:**
```bash
# Check for schema errors
python scripts/apply_schema_change.py --validate

# Validate specific schema
python scripts/apply_schema_change.py --validate --schema public
```

#### Step 4: Test Migration Locally

**Apply migration to local database:**
```bash
# Apply specific migration
python scripts/apply_schema_change.py --apply --file "20260621100721_add_user_preferences_table.sql"

# Or apply all pending migrations
python scripts/apply_schema_change.py --apply

# Or use automatic workflow (includes validation)
python scripts/apply_schema_change.py --auto --name "add_user_preferences_table"
```

**Test the changes:**
```bash
# Verify schema changes
supabase db query --local "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users';"

# Test with application code
python -c "
from core.db import get_supabase_client
client = get_supabase_client()
result = client.table('users').select('*').limit(1).execute()
print('Schema test passed')
"
```

#### Step 5: Verify and Validate

**Check migration status:**
```bash
# View applied migrations
python scripts/apply_schema_change.py --status

# Or use Supabase CLI directly
supabase migration list --local
```

**Validate schema integrity:**
```bash
# Run schema validation
python scripts/apply_schema_change.py --validate

# Check for specific issues
supabase db lint --local --schema public
```

**Test with application:**
```bash
# Start development environment
make start

# Run pipeline tests
make pipeline

# Test API endpoints
curl http://localhost:8000/api/dioceses
```

#### Step 6: Rollback if Needed (Optional)

If issues arise, rollback the migration:

```bash
# Rollback last migration
python scripts/apply_schema_change.py --rollback

# Rollback multiple migrations
python scripts/apply_schema_change.py --rollback --rollback-count 2

# Rollback with confirmation skip (use with caution)
python scripts/apply_schema_change.py --rollback --yes
```

**Reset database completely (if needed):**
```bash
# Reset to clean state
supabase db reset --local

# Or use the database reset script
python scripts/reset_local_database.py
```

### Common Scenarios

#### Scenario 1: Adding a New Table

**Workflow:**
```bash
# 1. Create table using Supabase Studio or SQL
supabase db query --local "
  CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    old_values JSONB,
    new_values JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
  );
"

# 2. Generate migration
python scripts/apply_schema_change.py --auto --name "add_audit_logs_table"

# 3. Review and approve migration when prompted
# 4. Migration is automatically applied and validated

# 5. Test the new table
supabase db query --local "SELECT COUNT(*) FROM audit_logs;"
```

#### Scenario 2: Modifying Existing Table

**Workflow:**
```bash
# 1. Add column to existing table
supabase db query --local "ALTER TABLE users ADD COLUMN last_login TIMESTAMPTZ;"

# 2. Generate migration
python scripts/apply_schema_change.py --generate --name "add_users_last_login"

# 3. Review migration content
cat supabase/migrations/20260621100721_add_users_last_login.sql

# 4. Apply migration
python scripts/apply_schema_change.py --apply

# 5. Validate schema
python scripts/apply_schema_change.py --validate

# 6. Test with application
python -c "from core.db import get_supabase_client; print('Test passed')"
```

#### Scenario 3: Adding Indexes

**Workflow:**
```bash
# 1. Create index
supabase db query --local "
  CREATE INDEX idx_users_email ON users(email);
  CREATE INDEX idx_users_created_at ON users(created_at DESC);
"

# 2. Generate migration
python scripts/apply_schema_change.py --auto --name "add_user_indexes"

# 3. Review and approve
# 4. Test index performance
supabase db query --local "
  EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';
"
```

#### Scenario 4: Data Migration

**Workflow:**
```bash
# 1. Create migration file for data changes
supabase migration new migrate_user_status

# 2. Edit migration file with data migration logic
vim supabase/migrations/20260621100721_migrate_user_status.sql

# 3. Add data migration SQL
# -- Add new column
# ALTER TABLE users ADD COLUMN status TEXT;
#
# -- Migrate existing data
# UPDATE users SET status = 'active' WHERE is_active = true;
# UPDATE users SET status = 'inactive' WHERE is_active = false;
#
# -- Add constraint
# ALTER TABLE users ADD CONSTRAINT check_status CHECK (status IN ('active', 'inactive'));

# 4. Apply migration
python scripts/apply_schema_change.py --apply

# 5. Verify data migration
supabase db query --local "SELECT status, COUNT(*) FROM users GROUP BY status;"
```

#### Scenario 5: Testing Before Deployment

**Workflow:**
```bash
# 1. Test workflow without making changes
python scripts/apply_schema_change.py --auto --name "test_deployment" --dry-run

# 2. Create backup before applying
python scripts/apply_schema_change.py --auto --name "important_change" --backup

# 3. Apply and validate
python scripts/apply_schema_change.py --auto --name "important_change"

# 4. Test thoroughly with application
make pipeline

# 5. If issues occur, rollback
python scripts/apply_schema_change.py --rollback
```

### Best Practices

#### 1. Use Descriptive Migration Names

Always use clear, descriptive names:
- ✅ Good: `add_user_preferences_table`, `add_index_on_users_email`, `migrate_user_status`
- ❌ Bad: `change1`, `fix`, `update`

#### 2. Test with Dry-Run First

Always test workflows before applying:
```bash
python scripts/apply_schema_change.py --auto --name "test" --dry-run
```

#### 3. Create Backups for Important Changes

For critical schema changes:
```bash
python scripts/apply_schema_change.py --auto --name "critical" --backup
```

#### 4. Review Generated Migrations

Always review auto-generated migrations:
```bash
python scripts/apply_schema_change.py --generate --name "change"
# Review the generated file
python scripts/apply_schema_change.py --apply
```

#### 5. Validate After Changes

Always validate the schema:
```bash
python scripts/apply_schema_change.py --validate
```

#### 6. Use Automatic Workflow

For most cases, use the automatic workflow:
```bash
python scripts/apply_schema_change.py --auto --name "descriptive_name"
```

#### 7. Keep Migration History

Track migration history:
```bash
python scripts/apply_schema_change.py --status
```

#### 8. Test with Application

Always test schema changes with the application:
```bash
make start
make pipeline
curl http://localhost:8000/api/dioceses
```

#### 9. Commit Migration Files

Always commit migration files to version control:
```bash
git add supabase/migrations/
git commit -m "Add user preferences table

- Add user_preferences table with RLS
- Add indexes for performance
- Include migration documentation"
```

#### 10. Document Complex Changes

For complex schema changes, document the rationale:
```sql
-- Migration: add_user_preferences.sql
-- Description: Add user preferences to support personalized settings
-- Reason: Users need to store theme, notification, and display preferences
-- Impact: Non-breaking change, adds new functionality
-- Rollback: DROP TABLE IF EXISTS user_preferences CASCADE;
```

### Troubleshooting

#### Issue: "Supabase CLI not found"

**Solution:**
```bash
# Install Supabase CLI
npm install -g supabase

# Verify installation
supabase --version
```

#### Issue: "Local Supabase stack is not running"

**Solution:**
```bash
# Start local stack
supabase start

# Check status
supabase status
```

#### Issue: "Migration file was not created"

**Solution:**
```bash
# Check for schema changes
supabase db diff --local --schema public

# If no changes, no migration will be generated
# Make actual schema changes first
```

#### Issue: "Schema validation failed"

**Solution:**
```bash
# Review validation errors
python scripts/apply_schema_change.py --validate

# Check for specific issues
supabase db lint --local --schema public

# Consider rolling back
python scripts/apply_schema_change.py --rollback
```

#### Issue: "Cannot rollback N migration(s)"

**Solution:**
```bash
# Check migration status
python scripts/apply_schema_change.py --status

# You're trying to rollback more than applied
# Adjust rollback count
python scripts/apply_schema_change.py --rollback --rollback-count 1
```

#### Issue: Generated migration is empty

**Solution:**
```bash
# No schema changes detected
# Make actual changes first
supabase db query --local "CREATE TABLE test_table (id INT);"

# Then generate migration
python scripts/apply_schema_change.py --generate --name "add_test_table"
```

#### Issue: Migration application fails

**Solution:**
```bash
# Check migration file syntax
cat supabase/migrations/20260621150000_migration.sql

# Test SQL manually
supabase db query --local "$(cat supabase/migrations/20260621150000_migration.sql)"

# Check logs
tail -f logs/schema_change_*.log

# Reset and try again
supabase db reset --local
```

### Integration with Development Workflow

The schema development workflow integrates seamlessly with the existing development process:

#### Typical Development Cycle

```bash
# 1. Pull latest changes
git pull origin main

# 2. Start development environment
make start

# 3. Make schema changes
supabase studio  # or use SQL

# 4. Generate and apply migration
python scripts/apply_schema_change.py --auto --name "add_new_feature"

# 5. Test with application
make pipeline

# 6. Validate schema
python scripts/apply_schema_change.py --validate

# 7. Commit changes
git add supabase/migrations/
git commit -m "Add new feature schema changes"
```

#### Before Major Feature Testing

```bash
# 1. Reset database for clean state
python scripts/reset_local_database.py

# 2. Apply schema migrations
python scripts/apply_schema_change.py --apply

# 3. Test feature with clean schema
make pipeline
```

#### After Schema Migrations

```bash
# 1. Pull schema changes
git pull origin main

# 2. Apply new migrations
python scripts/apply_schema_change.py --apply

# 3. Verify migration worked
python scripts/apply_schema_change.py --validate

# 4. Test application compatibility
make start
make pipeline
```

### Additional Resources

- **[Schema Change Management Script](SCHEMA_CHANGE_MANAGEMENT.md)** - Complete script documentation
- **[Supabase Migration Reference](supabase-migration-reference.md)** - Detailed command reference
- **[Database Schema Documentation](DATABASE.md)** - Complete schema reference
- **[Commands Guide](COMMANDS.md)** - Additional database commands
- **[Supabase CLI Documentation](https://supabase.com/docs/guides/cli)** - Official Supabase docs

### Quick Reference

#### Essential Commands

```bash
# Automatic workflow (recommended)
python scripts/apply_schema_change.py --auto --name "descriptive_name"

# Generate migration only
python scripts/apply_schema_change.py --generate --name "change"

# Apply migration
python scripts/apply_schema_change.py --apply

# Check status
python scripts/apply_schema_change.py --status

# Validate schema
python scripts/apply_schema_change.py --validate

# Rollback
python scripts/apply_schema_change.py --rollback

# Dry-run test
python scripts/apply_schema_change.py --auto --name "test" --dry-run
```

#### Common Flags

```bash
--backup          # Create database backup before changes
--dry-run         # Test without making changes
--schema SCHEMA   # Specify schema (default: public)
--skip-validation # Skip validation (use with caution)
--yes             # Skip confirmations (use with caution)
```

#### File Locations

```
supabase/
├── migrations/              # Migration files
│   └── 20260621150000_name.sql
├── config.toml             # Configuration
└── seed.sql                # Seed data

scripts/
└── apply_schema_change.py  # Schema management script

logs/
└── schema_change_*.log     # Operation logs
```

---

## 🏗️ Architecture Overview

### Local Development Stack
- **Backend**: FastAPI (http://localhost:8000)
- **Frontend**: React + Vite (http://localhost:5173)
- **Database**: Supabase PostgreSQL (remote)
- **Pipeline**: Python scripts with Chrome WebDriver
- **Monitoring**: WebSocket-based real-time dashboard

### Key Files
- `run_pipeline.py` - Main pipeline with monitoring
- `distributed_pipeline_runner.py` - Distributed scaling version with worker specialization
- `core/db.py` - Database utilities
- `core/distributed_work_coordinator.py` - Multi-pod coordination with worker types
- `backend/main.py` - FastAPI backend
- `frontend/src/` - React frontend

## 💡 Best Practices

### Development Workflow
1. **Always verify prerequisites first** using `make env-check`
2. **Start with small datasets** using `--diocese_id` and low limits
3. **Use monitoring** with `--monitoring_url http://localhost:8000`
4. **Test changes locally** before building Docker images
5. **Follow the deployment guide** for production releases

### Code Quality
```bash
# Before committing
make format     # Format code
make lint       # Check style
make test-quick # Run tests
```

### Data Safety
- Always test with `--diocese_id` to limit scope
- Use small `--max_parishes_per_diocese` values during development
- Monitor extraction progress in the dashboard
- Back up database before major schema changes

## 📚 Additional Documentation

- **[📝 Commands Guide](COMMANDS.md)** - Complete command reference
- **[📈 Scaling Guide](../k8s/SCALING_README.md)** - Horizontal scaling setup
- **[🚀 Deployment Guide](DEPLOYMENT_GUIDE.md)** - Production deployment
- **[🏗️ Architecture](ARCHITECTURE.md)** - System architecture details
- **[📊 Monitoring](MONITORING.md)** - Logging and monitoring setup
- **[🗄️ Database](DATABASE.md)** - Database schema and operations

## 🚨 Common Setup Issues

### Issue: Chrome WebDriver Not Found
**Symptoms:** `WebDriverException`, `chromedriver not found`, `No such file or directory`
**Solution:** Install browser and WebDriver correctly:
```bash
# 1. Check your system architecture first
uname -m

# 2. For ARM64 (Raspberry Pi, Apple Silicon under Linux):
sudo apt install chromium-browser chromium-chromedriver

# 3. For x86-64 (Standard Linux/Windows):
# Install Chrome browser first, then WebDriver is auto-managed

# 4. Verify installation
source .venv/bin/activate
make webdriver-check
```

### Issue: Architecture Mismatch (Exec format error)
**Symptoms:** `[Errno 8] Exec format error`, ChromeDriver fails to start
**Common on:** Raspberry Pi, ARM64 systems, Apple Silicon
**Solution:**
```bash
# Remove incompatible x86 drivers
sudo rm -rf ~/.wdm/drivers/chromedriver

# Install ARM64 compatible drivers
sudo apt install chromium-chromedriver

# Verify correct architecture
file /usr/bin/chromedriver  # Should show ARM aarch64 for ARM systems

# Test the fix
source .venv/bin/activate
python -c "from core.driver import setup_driver; print('✅ Success' if setup_driver() else '❌ Failed')"
```

### Issue: API Keys Not Working
**Symptoms:** API authentication errors, connection failures
**Solution:** Verify your `.env` file:
```bash
# Check if .env exists and has correct format
cat .env

# Test each API individually
make ai-check
make db-check
```

### Issue: Permission Denied Errors
**Solution:** Fix file permissions:
```bash
# Linux/macOS
sudo chown -R $USER:$USER .
chmod +x scripts/*.py

# Reactivate virtual environment
source .venv/bin/activate
```

### Issue: Frontend Not Starting
**Solution:** Ensure Node.js dependencies are installed:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## 🔧 Platform-Specific Notes

### **Raspberry Pi / ARM64 Systems**
- **Use Chromium**: Chrome is not available for ARM64, use `chromium-browser` instead
- **System WebDriver**: Install `chromium-chromedriver` via apt, avoid webdriver-manager
- **Memory Considerations**: Consider using `--max_parishes_per_diocese 5` for memory-constrained systems
- **Performance**: ARM systems are slower, expect longer processing times

### **Apple Silicon Macs (M1/M2/M3)**
- **Use x86-64 Chrome**: Install standard Chrome via Homebrew
- **Rosetta Required**: Some WebDriver components may require Rosetta 2
- **Docker Considerations**: Use `--platform linux/amd64` for x86 containers

### **Windows Subsystem for Linux (WSL)**
- **GUI Applications**: May need X11 forwarding for visible browser debugging
- **File Permissions**: Use `sudo chown -R $USER:$USER .` for permission issues
- **Chrome Installation**: Install Chrome for Linux, not Windows Chrome

### **Docker Development**
- **Architecture Matching**: Use `linux/amd64` for x86 hosts, `linux/arm64` for ARM hosts
- **Headless Required**: Always use headless mode in containers
- **Volume Mounts**: Mount `/tmp` for Chrome cache directories

### **Performance Optimization by Platform**
```bash
# Raspberry Pi / Low Memory Systems
python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 2

# Standard Desktop/Server
python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 10

# High-Performance Systems
python run_pipeline.py --diocese_id 123 --max_parishes_per_diocese 25
```

---

**Need help?** Check the [Commands Guide](COMMANDS.md) for detailed examples or create an issue in the repository.
