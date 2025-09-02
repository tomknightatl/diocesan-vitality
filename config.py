import os
from dotenv import load_dotenv

load_dotenv()

# --- Supabase Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- GenAI API Key Setup ---
GENAI_API_KEY = os.getenv("GENAI_API_KEY_USCCB")

# --- Search Engine API Key Setup ---
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY_USCCB")
SEARCH_CX = os.getenv("SEARCH_CX_USCCB")

def validate_config():
    """Validates that all necessary environment variables are loaded."""
    if not all([SUPABASE_URL, SUPABASE_KEY, GENAI_API_KEY, SEARCH_API_KEY, SEARCH_CX]):
        print("Warning: One or more environment variables are not set.")
        print("Please check your .env file or environment configuration.")
        return False
    
    print("All configurations loaded successfully.")
    return True

if __name__ == "__main__":
    validate_config()
