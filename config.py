import os
from dotenv import load_dotenv
from core.logger import get_logger

logger = get_logger(__name__)

load_dotenv()

# --- Supabase Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- GenAI API Key Setup ---
GENAI_API_KEY = os.getenv("GENAI_API_KEY_USCCB")

# --- Search Engine API Key Setup ---
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY_USCCB")
SEARCH_CX = os.getenv("SEARCH_CX_USCCB")

# --- Pipeline Defaults ---
DEFAULT_MAX_DIOCESES = 5
DEFAULT_MAX_PARISHES_PER_DIOCESE = 5
DEFAULT_NUM_PARISHES_FOR_SCHEDULE = 5

def validate_config():
    """Validates that all necessary environment variables are loaded."""
    if not all([SUPABASE_URL, SUPABASE_KEY, GENAI_API_KEY, SEARCH_API_KEY, SEARCH_CX]):
        logger.warning("Warning: One or more environment variables are not set.")
        logger.warning("Please check your .env file or environment configuration.")
        return False
    
    logger.info("All configurations loaded successfully.")
    return True

if __name__ == "__main__":
    validate_config()
