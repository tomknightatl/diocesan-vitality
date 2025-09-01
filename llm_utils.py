import os
import logging
import google.generativeai as genai
from google.api_core.exceptions import DeadlineExceeded, ServiceUnavailable, ResourceExhausted, InternalServerError, GoogleAPIError
import json
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define exceptions on which GenAI calls should be retried
RETRYABLE_GENAI_EXCEPTIONS = (
    DeadlineExceeded, ServiceUnavailable, ResourceExhausted,
    InternalServerError, GoogleAPIError
)

def configure_gemini_api_key():
    """
    Configures the Google Gemini API key from the GEMINI_API_KEY environment variable.

    Raises:
        ValueError: If the GEMINI_API_KEY environment variable is not set.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)

@retry(
    stop=stop_after_attempt(3), # Retry up to 3 times
    wait=wait_exponential(multiplier=1, min=2, max=10), # Exponential backoff: 2s, 4s, 8s...
    retry=retry_if_exception_type(RETRYABLE_GENAI_EXCEPTIONS),
    reraise=True, # Reraise the last exception if all retries fail
    before_sleep=lambda retry_state: logger.info(f"Retrying {retry_state.fn.__name__} for the {retry_state.attempt_number} time after {retry_state.idle_for:.2f}s...")
)
def invoke_gemini_model(prompt_text: str, model_name: str = "gemini-1.5-flash") -> str:
    """
    Invokes the specified Google Gemini model with the given prompt and retry logic.

    Args:
        prompt_text: The text prompt to send to the model.
        model_name: The name of the Gemini model to use (e.g., "gemini-1.5-flash").

    Returns:
        The text content of the model's response.

    Raises:
        Any exception encountered during the API call if retries fail,
        or NameError if the 'genai' module is not configured.
    """
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt_text)
        if not response.text:
            raise ValueError("Gemini model returned an empty response.")
        return response.text
    except Exception as e:
        logger.error(f"Failed to invoke Gemini model after multiple retries: {e}")
        raise

def extract_structured_data(llm_response: str, pydantic_model: type[BaseModel]) -> BaseModel:
    """
    Extracts and validates structured data from an LLM's text response using a Pydantic model.

    Args:
        llm_response (str): The raw text response from the LLM, expected to be a JSON string.
        pydantic_model (type[BaseModel]): The Pydantic model to validate the extracted data against.

    Returns:
        BaseModel: An instance of the Pydantic model populated with the extracted data.

    Raises:
        ValueError: If the LLM response is not valid JSON.
        ValidationError: If the extracted data does not conform to the Pydantic model.
    """
    try:
        data = json.loads(llm_response)
    except json.JSONDecodeError as e:
        logger.error(f"LLM response is not valid JSON: {e}")
        raise ValueError("LLM response is not valid JSON.") from e

    try:
        return pydantic_model.model_validate(data)
    except ValidationError as e:
        logger.error(f"Extracted data does not conform to Pydantic model: {e.errors()}")
        raise ValidationError(f"Extracted data does not conform to Pydantic model: {e.errors()}") from e
