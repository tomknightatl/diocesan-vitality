# llm_utils.py

`llm_utils.py` provides utility functions for interacting with Google's Gemini Large Language Models (LLMs) and for processing their responses, especially for structured data extraction.

## Functions

### `configure_gemini_api_key()`

- **Purpose**: Configures the Google Gemini API key from the `GEMINI_API_KEY` environment variable.
- **Raises**: `ValueError` if the `GEMINI_API_KEY` environment variable is not set.

### `invoke_gemini_model(prompt_text: str, model_name: str = "gemini-1.5-flash") -> str`

- **Purpose**: Invokes the specified Google Gemini model with a given text prompt.
- **Retry Logic**: Includes robust retry logic with exponential backoff for common API errors (e.g., `DeadlineExceeded`, `ServiceUnavailable`, `ResourceExhausted`).
- **Args**:
    - `prompt_text`: The text prompt to send to the model.
    - `model_name`: The name of the Gemini model to use (default: `gemini-1.5-flash`).
- **Returns**: The text content of the model's response.
- **Raises**: Exceptions encountered during the API call if retries fail, or `NameError` if the `genai` module is not configured.

### `extract_structured_data(llm_response: str, pydantic_model: type[BaseModel]) -> BaseModel`

- **Purpose**: Extracts and validates structured data from an LLM's raw text response.
- **Process**: It expects the LLM response to be a JSON string, which it then parses and validates against a provided Pydantic model.
- **Args**:
    - `llm_response`: The raw text response from the LLM (expected to be JSON).
    - `pydantic_model`: The Pydantic model to validate the extracted data against.
- **Returns**: An instance of the Pydantic model populated with the extracted data.
- **Raises**:
    - `ValueError`: If the LLM response is not valid JSON.
    - `ValidationError`: If the extracted data does not conform to the Pydantic model.
