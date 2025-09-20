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