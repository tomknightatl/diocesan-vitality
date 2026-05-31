# Quick Reference: AI Authentication System

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Set Authentication (Choose One)

**Option A: API Key (Development)**
```bash
export GENAI_API_KEY=your_api_key_here
```

**Option B: Service Account (Production)**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

**Option C: Auto-Detect (Recommended)**
```bash
# No setup needed - system auto-detects available credentials
```

### 2. Use in Code

```python
from core.ai_model_factory import get_ai_model_factory

# Get model factory (auto-configures authentication)
factory = get_ai_model_factory()

# Get model for your component
model = factory.get_model("content_analyzer")

# Use the model
response = model.generate_content("Your prompt here")
print(response.text)
```

## Common Patterns

### Get Model with Custom Parameters

```python
model = factory.get_model(
    component_name="schedule_extractor",
    parameters={
        "temperature": 0.5,
        "max_tokens": 8192,
        "top_p": 0.95
    }
)
```

### Get Model with System Instruction

```python
model = factory.get_model(
    component_name="content_analyzer",
    system_instruction="You are an expert web scraper analyzing Catholic parish directories."
)
```

### Check Authentication Status

```python
from core.ai_auth_manager import get_ai_auth_manager

auth_manager = get_ai_auth_manager()
if auth_manager.authenticate():
    print(f"✅ Authenticated with {auth_manager.active_strategy_name}")
else:
    print("❌ Authentication failed")
```

### Get Configuration

```python
from core.ai_config import get_ai_config

config = get_ai_config()
print(f"Auth method: {config.auth_method}")
print(f"Default model: {config.default_model}")
print(f"Caching enabled: {config.enable_caching}")
```

### List Available Models

```python
factory = get_ai_model_factory()
models = factory.list_available_models()
for model in models:
    print(f"- {model}")
```

### Test Model Availability

```python
factory = get_ai_model_factory()
success, message = factory.test_model("gemini-1.5-flash")
print(f"Test result: {success} - {message}")
```

## Environment Variables

### Authentication
- `GENAI_API_KEY` - Google AI API key
- `GOOGLE_APPLICATION_CREDENTIALS` - Service account JSON path

### Configuration
- `GOOGLE_AI_AUTH_METHOD` - api_key, oauth, service_account, auto_detect
- `GOOGLE_AI_DEFAULT_MODEL` - Default model name
- `GOOGLE_AI_FORCE_MODEL` - Override all models

### Model Parameters
- `GOOGLE_AI_TEMPERATURE` - 0.0 to 2.0
- `GOOGLE_AI_MAX_TOKENS` - 1 to 32768
- `GOOGLE_AI_TOP_P` - 0.0 to 1.0
- `GOOGLE_AI_TOP_K` - 1 to 100

### Performance
- `GOOGLE_AI_ENABLE_CACHING` - true/false
- `GOOGLE_AI_CACHE_TTL` - seconds
- `GOOGLE_AI_MAX_RETRIES` - number
- `GOOGLE_AI_TIMEOUT` - seconds

## Component Models

| Component | Default Model |
|-----------|---------------|
| content_analyzer | gemini-2.5-flash |
| schedule_extractor | gemini-1.5-flash |
| fallback_extractor | gemini-1.5-flash |
| url_filter | gemini-1.5-flash |
| parish_prioritizer | gemini-1.5-flash |

## Troubleshooting

### Authentication Fails
```bash
# Check environment variables
echo $GENAI_API_KEY
echo $GOOGLE_APPLICATION_CREDENTIALS

# Test authentication
python3 -c "
from core.ai_auth_manager import get_ai_auth_manager
auth = get_ai_auth_manager()
print(f'Authenticated: {auth.authenticate()}')
print(f'Strategy: {auth.active_strategy_name}')
"
```

### Model Creation Fails
```bash
# Test model availability
python3 -c "
from core.ai_model_factory import get_ai_model_factory
factory = get_ai_model_factory()
success, msg = factory.test_model('gemini-1.5-flash')
print(f'{success}: {msg}')
"
```

### Cache Issues
```python
# Clear cache
factory = get_ai_model_factory()
factory.clear_cache()

# Check cache stats
stats = factory.get_cache_stats()
print(stats)
```

## Migration from Old Code

### Before
```python
import google.generativeai as genai
from pipeline import config

genai.configure(api_key=config.GENAI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
```

### After
```python
from core.ai_model_factory import get_ai_model_factory

factory = get_ai_model_factory()
model = factory.get_model("content_analyzer")
```

## Testing

Run the test suite:
```bash
python3 tests/test_ai_system.py
```

## Documentation

- **Full Usage Guide**: `docs/AI_AUTHENTICATION_USAGE.md`
- **Implementation Summary**: `docs/PHASE1_IMPLEMENTATION_SUMMARY.md`
- **Configuration File**: `config/ai_config.yaml`

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the full usage guide
3. Run the test suite to verify installation
4. Check logs for detailed error messages