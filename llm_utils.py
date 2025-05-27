import google.generativeai as genai
from google.api_core.exceptions import DeadlineExceeded, ServiceUnavailable, ResourceExhausted, InternalServerError, GoogleAPIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Define exceptions on which GenAI calls should be retried
RETRYABLE_GENAI_EXCEPTIONS = (
    DeadlineExceeded, ServiceUnavailable, ResourceExhausted,
    InternalServerError, GoogleAPIError
)

@retry(
    stop=stop_after_attempt(3), # Retry up to 3 times
    wait=wait_exponential(multiplier=1, min=2, max=10), # Exponential backoff: 2s, 4s, 8s...
    retry=retry_if_exception_type(RETRYABLE_GENAI_EXCEPTIONS),
    reraise=True # Reraise the last exception if all retries fail
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
    if not genai.get_model(model_name): # Checks if genai is configured by trying to get model
         raise NameError("genai module not available or not configured. Call genai.configure(api_key=YOUR_API_KEY) first.")
    
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt_text)
    return response.text
