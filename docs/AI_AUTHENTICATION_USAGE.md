# AI Authentication and Configuration - Usage Examples

This document provides comprehensive examples of how to use the new AI authentication and configuration system.

## Overview

The new AI system consists of three core components:

1. **`core/ai_config.py`** - Configuration management
2. **`core/ai_auth_manager.py`** - Authentication abstraction
3. **`core/ai_model_factory.py`** - Model factory pattern

## Basic Usage

### 1. Simple API Key Authentication (Development)

```python
from core.ai_config import get_ai_config
from core.ai_auth_manager import get_ai_auth_manager
from core.ai_model_factory import get_ai_model_factory

# Set your API key in environment variable: GENAI_API_KEY=your_api_key

# Get configuration (uses defaults from config/ai_config.yaml)
config = get_ai_config()

# Get authentication manager (auto-detects API key)
auth_manager = get_ai_auth_manager(auth_method="api_key")

# Authenticate
if auth_manager.authenticate():
    print(f"Authenticated using: {auth_manager.active_strategy_name}")

# Get model factory
factory = get_ai_model_factory()

# Get a model for a component
model = factory.get_model("content_analyzer")

# Use the model
response = model.generate_content("Hello, world!")
print(response.text)
```

### 2. Auto-Detect Authentication (Recommended)

```python
from core.ai_config import get_ai_config
from core.ai_auth_manager import get_ai_auth_manager
from core.ai_model_factory import get_ai_model_factory

# Auto-detect will try: service_account -> oauth -> api_key
auth_manager = get_ai_auth_manager(auth_method="auto_detect")

# Authenticate (automatically detects best available method)
if auth_manager.authenticate():
    print(f"Authenticated using: {auth_manager.active_strategy_name}")

# Get model factory (automatically configures genai)
factory = get_ai_model_factory()

# Get model for component
model = factory.get_model("schedule_extractor")

# Use the model
response = model.generate_content("Extract schedule from this text...")
print(response.text)
```

### 3. Service Account Authentication (Production)

```python
import os
from core.ai_config import get_ai_config
from core.ai_auth_manager import get_ai_auth_manager
from core.ai_model_factory import get_ai_model_factory

# Set service account path in environment variable:
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Or provide it directly:
auth_manager = get_ai_auth_manager(
    auth_method="service_account",
    credentials_path="/path/to/service-account.json"
)

# Authenticate
if auth_manager.authenticate():
    print(f"Authenticated using: {auth_manager.active_strategy_name}")

# Get model factory
factory = get_ai_model_factory()

# Get model
model = factory.get_model("content_analyzer")

# Use the model
response = model.generate_content("Analyze this content...")
print(response.text)
```

## Advanced Usage

### 4. Custom Configuration

```python
from core.ai_config import AIConfig, get_ai_config
from core.ai_auth_manager import get_ai_auth_manager
from core.ai_model_factory import get_ai_model_factory

# Load custom configuration
config = AIConfig(config_path="/path/to/custom_config.yaml")

# Or use environment variables to override:
# GOOGLE_AI_AUTH_METHOD=oauth
# GOOGLE_AI_DEFAULT_MODEL=gemini-1.5-pro
# GOOGLE_AI_TEMPERATURE=0.5

# Get config with overrides
config = get_ai_config()

# Create auth manager with custom config
auth_manager = get_ai_auth_manager(auth_method=config.auth_method)

# Create model factory with custom config
factory = get_ai_model_factory(config=config)

# Get model with custom parameters
model = factory.get_model(
    component_name="content_analyzer",
    parameters={
        "temperature": 0.3,
        "max_tokens": 8192,
        "top_p": 0.95
    }
)
```

### 5. System Instructions

```python
from core.ai_model_factory import get_ai_model_factory

factory = get_ai_model_factory()

# Get model with system instruction
model = factory.get_model(
    component_name="content_analyzer",
    system_instruction="You are an expert web scraper analyzing Catholic parish directories."
)

# Use the model
response = model.generate_content("Analyze this parish directory page...")
print(response.text)
```

### 6. Model Caching

```python
from core.ai_config import get_ai_config
from core.ai_model_factory import get_ai_model_factory

# Enable caching in config
config = get_ai_config()
print(f"Caching enabled: {config.enable_caching}")
print(f"Cache TTL: {config.cache_ttl} seconds")

# Get model factory
factory = get_ai_model_factory()

# First call creates and caches the model
model1 = factory.get_model("content_analyzer")

# Second call returns cached model (faster)
model2 = factory.get_model("content_analyzer")

# Check cache stats
stats = factory.get_cache_stats()
print(f"Cache stats: {stats}")

# Clear cache if needed
factory.clear_cache(component_name="content_analyzer")
```

### 7. Model Capabilities and Metadata

```python
from core.ai_model_factory import get_ai_model_factory

factory = get_ai_model_factory()

# Get model capabilities
capabilities = factory.get_model_capabilities("gemini-1.5-flash")
print(f"Model capabilities: {capabilities}")

# Get model metadata
metadata = factory.get_model_metadata("gemini-1.5-flash")
print(f"Model metadata: {metadata}")

# List available models
models = factory.list_available_models()
print(f"Available models: {models}")

# Test a model
success, message = factory.test_model("gemini-1.5-flash")
print(f"Model test: {success} - {message}")
```

### 8. Component-Specific Models

```python
from core.ai_config import get_ai_config
from core.ai_model_factory import get_ai_model_factory

config = get_ai_config()

# Get model for different components
content_analyzer_model = factory.get_model("content_analyzer")
schedule_extractor_model = factory.get_model("schedule_extractor")
fallback_extractor_model = factory.get_model("fallback_extractor")

# Each component can use a different model
print(f"Content analyzer model: {config.get_model_for_component('content_analyzer')}")
print(f"Schedule extractor model: {config.get_model_for_component('schedule_extractor')}")

# Get all component models
all_models = config.get_all_component_models()
print(f"All component models: {all_models}")
```

### 9. Error Handling and Fallback

```python
from core.ai_auth_manager import get_ai_auth_manager, AuthenticationFailedError
from core.ai_model_factory import get_ai_model_factory

# Try to authenticate with fallback
auth_manager = get_ai_auth_manager(auth_method="auto_detect")

try:
    if auth_manager.authenticate():
        factory = get_ai_model_factory()
        model = factory.get_model("content_analyzer")
        response = model.generate_content("Test")
        print(response.text)
    else:
        print("Authentication failed, trying fallback...")
        # Try alternative authentication method
        auth_manager_fallback = get_ai_auth_manager(auth_method="api_key")
        if auth_manager_fallback.authenticate():
            factory = get_ai_model_factory(auth_manager=auth_manager_fallback)
            model = factory.get_model("content_analyzer")
            response = model.generate_content("Test")
            print(response.text)

except AuthenticationFailedError as e:
    print(f"Authentication failed: {e}")
except Exception as e:
    print(f"Error: {e}")
```

### 10. Refreshing Credentials

```python
from core.ai_auth_manager import get_ai_auth_manager

auth_manager = get_ai_auth_manager(auth_method="oauth")

# Authenticate
if auth_manager.authenticate():
    print("Authenticated successfully")

    # Later, refresh credentials if needed
    if auth_manager.refresh_credentials():
        print("Credentials refreshed successfully")
    else:
        print("Failed to refresh credentials")
```

## Environment Variables

The system supports the following environment variables for configuration:

### Authentication
- `GENAI_API_KEY` - Google AI API key (for api_key method)
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON file (for service_account method)

### Configuration Overrides
- `GOOGLE_AI_AUTH_METHOD` - Authentication method (api_key, oauth, service_account, auto_detect)
- `GOOGLE_AI_FORCE_MODEL` - Force a specific model for all components
- `GOOGLE_AI_ENABLE_WEB_AUTH` - Enable web-based OAuth flow (true/false)
- `GOOGLE_AI_DEFAULT_MODEL` - Default model name

### Model Parameters
- `GOOGLE_AI_TEMPERATURE` - Temperature (0.0-2.0)
- `GOOGLE_AI_MAX_TOKENS` - Maximum tokens (1-32768)
- `GOOGLE_AI_TOP_P` - Top-p sampling (0.0-1.0)
- `GOOGLE_AI_TOP_K` - Top-k sampling (1-100)

### Performance
- `GOOGLE_AI_ENABLE_CACHING` - Enable model caching (true/false)
- `GOOGLE_AI_CACHE_TTL` - Cache time-to-live in seconds
- `GOOGLE_AI_MAX_RETRIES` - Maximum number of retries
- `GOOGLE_AI_TIMEOUT` - Timeout in seconds

### Logging
- `GOOGLE_AI_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `GOOGLE_AI_LOG_REQUESTS` - Log API requests (true/false)
- `GOOGLE_AI_LOG_RESPONSES` - Log API responses (true/false)

## Configuration File Structure

The `config/ai_config.yaml` file has the following structure:

```yaml
authentication:
  method: auto_detect  # api_key, oauth, service_account, auto_detect
  enable_web_auth: false
  force_model: null

models:
  default: "gemini-1.5-flash"
  components:
    content_analyzer: "gemini-2.5-flash"
    schedule_extractor: "gemini-1.5-flash"
    fallback_extractor: "gemini-1.5-flash"
    url_filter: "gemini-1.5-flash"
    parish_prioritizer: "gemini-1.5-flash"

model_parameters:
  temperature: 0.7
  max_tokens: 4096
  top_p: 0.9
  top_k: 40

performance:
  enable_caching: true
  cache_ttl: 3600
  max_retries: 3
  timeout: 30

logging:
  level: "INFO"
  log_requests: false
  log_responses: false
```

## Migration from Old Code

### Before (Old Pattern):
```python
import google.generativeai as genai
from pipeline import config

genai.configure(api_key=config.GENAI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content("Hello")
```

### After (New Pattern):
```python
from core.ai_model_factory import get_ai_model_factory

factory = get_ai_model_factory()
model = factory.get_model("content_analyzer")
response = model.generate_content("Hello")
```

## Best Practices

1. **Use Auto-Detect**: Let the system automatically detect the best authentication method
2. **Enable Caching**: Model caching improves performance for repeated requests
3. **Component-Specific Models**: Use different models for different components based on needs
4. **Environment Variables**: Use environment variables for sensitive configuration
5. **Error Handling**: Always handle authentication and model creation errors
6. **Test Models**: Test model availability before using in production
7. **Monitor Cache**: Check cache stats to optimize performance

## Troubleshooting

### Authentication Fails
- Check that credentials are properly set in environment variables
- Verify service account file exists and has correct permissions
- Ensure API key is valid and has necessary permissions

### Model Creation Fails
- Check that model name is correct and available
- Verify authentication is successful before creating models
- Check network connectivity to Google AI services

### Cache Issues
- Clear cache if models are not updating: `factory.clear_cache()`
- Adjust cache TTL if models are expiring too quickly
- Disable caching if you need fresh models for each request

### Performance Issues
- Enable caching to reduce model creation overhead
- Use appropriate model for the task (flash for speed, pro for quality)
- Adjust timeout and retry settings for your network conditions