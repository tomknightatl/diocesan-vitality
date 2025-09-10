from supabase import create_client, Client
import config
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

supabase_client: Client = None

# Define retryable exceptions for Supabase connection
RETRYABLE_SUPABASE_EXCEPTIONS = (Exception,) # Broad exception for now, can be refined

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RETRYABLE_SUPABASE_EXCEPTIONS),
    reraise=False, # Do not re-raise after retries, let the function return None
)
def _create_supabase_client_with_retry(url, key):
    """Internal helper to create Supabase client with retry logic."""
    return create_client(url, key)

def get_supabase_client() -> Client:
    """Initializes and returns the Supabase client."""
    global supabase_client
    if supabase_client is None:
        if config.SUPABASE_URL and config.SUPABASE_KEY:
            try:
                supabase_client = _create_supabase_client_with_retry(config.SUPABASE_URL, config.SUPABASE_KEY)
                if supabase_client:
                    print("Supabase client initialized successfully.")
                else:
                    print("Failed to initialize Supabase client after multiple retries.")
            except Exception as e:
                print(f"Error initializing Supabase client: {e}")
                supabase_client = None
        else:
            print("Supabase URL and/or Key NOT loaded.")
    return supabase_client
