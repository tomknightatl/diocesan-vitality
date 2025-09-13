# Local Development Guide

This guide provides everything you need to develop and test the USCCB extraction scripts locally.

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

4. **Start Local Backend** (for monitoring)
   ```bash
   cd backend
   python main.py
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
GENAI_API_KEY_USCCB=your-google-gemini-api-key
SEARCH_API_KEY_USCCB=your-google-search-api-key
SEARCH_CX_USCCB=your-google-search-cx-id
```

### API Key Setup

1. **Supabase**: Get URL and service role key from your Supabase project dashboard
2. **Google Gemini**: Create API key at https://ai.google.dev/
3. **Google Custom Search**:
   - Create API key at Google Cloud Console
   - Set up Custom Search Engine at https://cse.google.com/

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

## Local Monitoring Dashboard

### Backend Setup

1. **Start Backend Server**
   ```bash
   cd backend
   python main.py
   ```
   Server runs at http://localhost:8000

2. **Start Frontend** (optional)
   ```bash
   cd frontend
   npm start
   ```
   Dashboard available at http://localhost:3000

### Monitoring Features

- **Real-time Logs**: View extraction progress live
- **Error Tracking**: See detailed error messages
- **Progress Tracking**: Monitor parishes processed
- **WebSocket Connection**: Live updates without refresh

### API Endpoints

- `GET /api/logs` - Recent log entries
- `GET /api/statistics` - Current extraction stats
- `GET /api/parishes` - Parish data
- `GET /api/dioceses` - Diocese data
- `WS /ws/monitoring` - WebSocket for live updates

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

## Quick Reference

### Most Common Commands
```bash
# Daily development workflow
source venv/bin/activate
cd backend && python main.py &  # Start monitoring
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