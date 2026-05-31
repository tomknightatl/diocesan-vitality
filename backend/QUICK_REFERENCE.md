# Quick Reference Guide - Intelligent Model Routing System

## Quick Start

### 1. Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY to .env
```

### 2. Start Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test API
```bash
# Get available models
curl http://localhost:8000/api/ai/models

# Generate content
curl -X POST http://localhost:8000/api/ai/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello world", "task_type": "text_generation"}'

# Check costs
curl http://localhost:8000/api/ai/costs/summary
```

## API Endpoints

### POST /api/ai/generate
Generate AI content with automatic model routing.

**Request:**
```json
{
  "prompt": "Your prompt here",
  "task_type": "text_generation",
  "max_tokens": 1000,
  "temperature": 0.7,
  "top_p": 0.9,
  "system_prompt": "Optional system prompt",
  "complexity_score": null,
  "metadata": {}
}
```

**Response:**
```json
{
  "content": "Generated content",
  "model_used": "gemini-2.5-flash",
  "tokens_used": {
    "input_tokens": 10,
    "output_tokens": 20,
    "total_tokens": 30
  },
  "cost": 0.00000675,
  "generation_time": 0.5,
  "complexity_score": 0.3,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### GET /api/ai/models
List all available models with capabilities.

### GET /api/ai/config
Get current AI configuration.

### POST /api/ai/config/reload
Reload AI configuration from file.

### GET /api/ai/costs/summary
Get cost analytics and statistics.

### GET /api/ai/costs/recent?limit=50
Get recent generation history.

## Task Types

- `text_generation` - General text generation
- `extraction` - Data extraction
- `analysis` - Text analysis
- `summarization` - Text summarization
- `translation` - Language translation
- `code_generation` - Code generation
- `question_answering` - Q&A tasks

## Model Selection

Automatic routing based on complexity:

- **Complexity > 0.7** → `gemini-2.5-pro` (best quality)
- **Complexity 0.4-0.7** → `gemini-2.5-flash` (balanced)
- **Complexity < 0.4** → `gemini-2.5-flash-lite` (lowest cost)

## Pricing

| Model | Input/1K tokens | Output/1K tokens |
|-------|----------------|------------------|
| gemini-2.5-pro | $0.00125 | $0.005 |
| gemini-2.5-flash | $0.000075 | $0.0003 |
| gemini-2.5-flash-lite | $0.0000375 | $0.00015 |

## Configuration

Edit `config/ai_config.json`:

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

## Environment Variables

- `GEMINI_API_KEY` - Your Google Gemini API key (required)
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase service role key

## Testing

```bash
# Run verification
python3 verify_implementation.py

# Run tests (requires pytest)
pytest tests/ -v
```

## Common Use Cases

### Simple Text Generation
```json
{
  "prompt": "Write a short story",
  "task_type": "text_generation"
}
```

### Data Extraction
```json
{
  "prompt": "Extract name, address, phone from this text...",
  "task_type": "extraction",
  "system_prompt": "You are a data extraction expert"
}
```

### Summarization
```json
{
  "prompt": "Summarize this article...",
  "task_type": "summarization",
  "max_tokens": 200
}
```

### Code Generation
```json
{
  "prompt": "Write a Python function to parse JSON",
  "task_type": "code_generation"
}
```

## Cost Optimization Tips

1. **Use appropriate task types** for optimal routing
2. **Set reasonable max_tokens** to control costs
3. **Monitor costs** with `/api/ai/costs/summary`
4. **Adjust complexity factors** in config if needed
5. **Use system prompts** to reduce iterations

## Troubleshooting

### "GEMINI_API_KEY not configured"
- Add `GEMINI_API_KEY` to `.env` file
- Verify API key is valid

### High costs
- Check complexity scores in responses
- Review cost breakdown by model
- Adjust complexity calculation factors

### Slow generation
- Check network connectivity
- Consider faster models for simple tasks
- Monitor generation times

## File Structure

```
backend/
├── ai/
│   ├── __init__.py          # Module exports
│   ├── model_router.py      # Core routing logic
│   ├── models.py            # Pydantic models
│   └── README.md            # Full documentation
├── config/
│   └── ai_config.json       # AI configuration
├── tests/
│   ├── __init__.py
│   └── test_model_router.py # Test suite
├── main.py                  # FastAPI app with AI endpoints
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
├── verify_implementation.py # Verification script
└── IMPLEMENTATION_SUMMARY.md # Full summary
```

## Support

For detailed documentation, see `ai/README.md`
For implementation details, see `IMPLEMENTATION_SUMMARY.md`