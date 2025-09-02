from supabase import create_client, Client
import config

supabase_client: Client = None

def get_supabase_client() -> Client:
    """Initializes and returns the Supabase client."""
    global supabase_client
    if supabase_client is None:
        if config.SUPABASE_URL and config.SUPABASE_KEY:
            try:
                supabase_client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                print("Supabase client initialized successfully.")
            except Exception as e:
                print(f"Error initializing Supabase client: {e}")
                supabase_client = None
        else:
            print("Supabase URL and/or Key NOT loaded.")
    return supabase_client
