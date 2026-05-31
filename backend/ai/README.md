# Intelligent Model Routing System

An intelligent AI model routing system that automatically selects the optimal model based on task complexity, cost constraints, and quality requirements.

## Features

- **Automatic Model Selection**: Routes requests to the most appropriate model based on complexity analysis
- **Cost Tracking**: Monitors token usage and costs across all generations
- **Multi-Model Support**: Supports multiple Gemini models with different capabilities
- **Complexity Analysis**: Calculates task complexity using multiple factors
- **RESTful API**: Clean API endpoints for AI generation and management
- **Comprehensive Testing**: Full test coverage with pytest

## Architecture

### Model Selection Logic

The system uses intelligent routing based on task complexity:

- **High Complexity (>0.7)** → `gemini-2.5-pro` (best quality, higher cost)
- **Medium Complexity (0.4-0.7)** → `gemini-2.5-flash` (balanced quality and cost)
- **Low Complexity (<0.4)** → `gemini-2.5-flash-lite` (fastest, lowest cost)

### Complexity Calculation

Complexity scores (0-1) are calculated using weighted factors:

1. **Prompt Length** (20%): Longer prompts indicate more complex tasks
2. **Task Complexity** (50%): Some task types are inherently more complex
3. **Domain Specificity** (30%): Technical terms and domain knowledge increase complexity

## Available Models

### Gemini 2.5 Pro
- **Best for**: Complex extraction, analysis, code generation
- **Quality**: Highest (1.0)
- **Speed**: Moderate (0.6)
- **Cost**: $0.00125/1K input tokens, $0.005/1K output tokens
- **Features**: Function calling, vision support

### Gemini 2.5 Flash
- **Best for**: Text generation, summarization, Q&A
- **Quality**: High (0.8)
- **Speed**: Fast (0.9)
- **Cost**: $0.000075/1K input tokens, $0.0003/1K output tokens
- **Features**: Function calling, vision support

### Gemini 2.5 Flash Lite
- **Best for**: Translation, simple text generation
- **Quality**: Good (0.6)
- **Speed**: Fastest (1.0)
- **Cost**: $0.0000375/1K input tokens, $0.00015/1K output tokens
- **Features**: Basic text generation

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

3. Configure AI settings (optional):
```bash
# Edit config/ai_config.json to customize routing behavior
```

## API Endpoints

### POST /api/ai/generate
Generate AI content with automatic model routing.

**Request Body:**
```json
{
  "prompt": "Extract structured data from this HTML",
  "task_type": "extraction",
  "max_tokens": 1000,
  "temperature": 0.7,
  "top_p": 0.9,
  "system_prompt": "You are a data extraction expert",
  "complexity_score": null,
  "metadata": {}
}
```

**Response:**
```json
{
  "content": "Extracted data...",
  "model_used": "gemini-2.5-pro",
  "tokens_used": {
    "input_tokens": 150,
    "output_tokens": 300,
    "total_tokens": 450
  },
  "cost": 0.001875,
  "generation_time": 2.345,
  "complexity_score": 0.85,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### GET /api/ai/models
Get list of available AI models with capabilities and pricing.

**Response:**
```json
{
  "models": [
    {
      "model_id": "gemini-2.5-pro",
      "name": "Gemini 2.5 Pro",
      "description": "Highest quality model for complex tasks",
      "max_tokens": 8192,
      "context_window": 1000000,
      "supports_function_calling": true,
      "supports_vision": true,
      "input_cost_per_1k_tokens": 0.00125,
      "output_cost_per_1k_tokens": 0.005,
      "complexity_threshold": 0.7,
      "quality_score": 1.0,
      "speed_score": 0.6,
      "recommended_for": ["extraction", "analysis", "code_generation"]
    }
  ],
  "total_count": 3
}
```

### GET /api/ai/config
Get current AI configuration.

**Response:**
```json
{
  "default_model": "gemini-2.5-flash",
  "max_retries": 3,
  "timeout": 60,
  "enable_cost_tracking": true,
  "complexity_calculation": {
    "enabled": true,
    "factors": {
      "prompt_length": 0.2,
      "task_complexity": 0.5,
      "domain_specificity": 0.3
    }
  }
}
```

### POST /api/ai/config/reload
Reload AI configuration from file.

**Response:**
```json
{
  "status": "success",
  "message": "AI configuration reloaded successfully",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### GET /api/ai/costs/summary
Get cost summary for AI generations.

**Response:**
```json
{
  "total_cost": 0.123456,
  "total_tokens": 15000,
  "total_requests": 50,
  "average_cost_per_request": 0.002469,
  "average_tokens_per_request": 300.0,
  "cost_by_model": {
    "gemini-2.5-pro": 0.1,
    "gemini-2.5-flash": 0.02,
    "gemini-2.5-flash-lite": 0.003456
  },
  "cost_by_task_type": {
    "extraction": 0.1,
    "text_generation": 0.02,
    "summarization": 0.003456
  }
}
```

### GET /api/ai/costs/recent?limit=50
Get recent AI generations with cost information.

**Response:**
```json
{
  "generations": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "model_id": "gemini-2.5-pro",
      "task_type": "extraction",
      "tokens": {
        "input": 150,
        "output": 300,
        "total": 450
      },
      "cost": 0.001875,
      "generation_time": 2.345
    }
  ],
  "total_count": 50
}
```

## Task Types

The system supports the following task types:

- `text_generation`: General text generation
- `extraction`: Data extraction from structured/unstructured text
- `analysis`: Text analysis and insights
- `summarization`: Text summarization
- `translation`: Language translation
- `code_generation`: Code generation and explanation
- `question_answering`: Q&A tasks

## Configuration

### AI Configuration File (`config/ai_config.json`)

```json
{
  "api_key": "",
  "default_model": "gemini-2.5-flash",
  "max_retries": 3,
  "timeout": 60,
  "enable_cost_tracking": true,
  "complexity_calculation": {
    "enabled": true,
    "factors": {
      "prompt_length": 0.2,
      "task_complexity": 0.5,
      "domain_specificity": 0.3
    }
  }
}
```

### Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase service role key

## Usage Examples

### Basic Text Generation

```python
import httpx

response = httpx.post(
    "http://localhost:8000/api/ai/generate",
    json={
        "prompt": "Write a short story about a church community",
        "task_type": "text_generation",
        "max_tokens": 500,
    }
)

result = response.json()
print(result["content"])
print(f"Model used: {result['model_used']}")
print(f"Cost: ${result['cost']:.6f}")
```

### Data Extraction

```python
response = httpx.post(
    "http://localhost:8000/api/ai/generate",
    json={
        "prompt": "Extract parish name, address, and phone from this text...",
        "task_type": "extraction",
        "system_prompt": "You are a data extraction expert. Extract structured data.",
    }
)
```

### Cost Monitoring

```python
# Get cost summary
response = httpx.get("http://localhost:8000/api/ai/costs/summary")
summary = response.json()

print(f"Total cost: ${summary['total_cost']:.6f}")
print(f"Total requests: {summary['total_requests']}")
print(f"Average cost per request: ${summary['average_cost_per_request']:.6f}")

# Get recent generations
response = httpx.get("http://localhost:8000/api/ai/costs/recent?limit=10")
recent = response.json()

for gen in recent['generations']:
    print(f"{gen['timestamp']}: {gen['model_id']} - ${gen['cost']:.6f}")
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest backend/tests/ -v

# Run specific test file
pytest backend/tests/test_model_router.py -v

# Run with coverage
pytest backend/tests/ --cov=backend/ai --cov-report=html
```

## Cost Optimization Tips

1. **Use appropriate task types**: The system routes based on task complexity. Choose the right task type for optimal routing.

2. **Set reasonable max_tokens**: Limit output tokens to control costs.

3. **Monitor costs regularly**: Use `/api/ai/costs/summary` to track spending.

4. **Adjust complexity factors**: Modify `complexity_calculation.factors` in config to fine-tune routing.

5. **Use system prompts**: Provide clear system prompts to reduce the need for multiple iterations.

## Error Handling

The system implements comprehensive error handling:

- **400 Bad Request**: Invalid input parameters
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Generation or API failure

All errors include detailed messages for debugging.

## Performance Considerations

- **Connection Pooling**: HTTP client is reused across requests
- **Async Operations**: All I/O operations are asynchronous
- **Cost Tracking**: Thread-safe cost tracking with locks
- **Singleton Pattern**: Router instance is shared across the application

## Security

- **API Key Protection**: Never log or expose API keys
- **Input Validation**: All inputs are validated with Pydantic
- **Rate Limiting**: Implement rate limiting for production use
- **Environment Variables**: Sensitive data stored in environment variables

## Troubleshooting

### "GEMINI_API_KEY not configured"
- Ensure `GEMINI_API_KEY` is set in your `.env` file
- Verify the API key is valid and active

### High costs
- Check complexity scores in responses
- Review cost breakdown by model and task type
- Adjust complexity calculation factors

### Slow generation times
- Check network connectivity to Gemini API
- Consider using faster models for simple tasks
- Monitor generation times in cost tracking

## Future Enhancements

- [ ] Add support for streaming responses
- [ ] Implement caching for repeated prompts
- [ ] Add more models (GPT-4, Claude, etc.)
- [ ] Implement rate limiting per user
- [ ] Add A/B testing for model selection
- [ ] Implement cost budgets and alerts
- [ ] Add support for function calling
- [ ] Implement batch processing

## License

This module is part of the Diocesan Vitality project.

## Support

For issues or questions, please contact the development team.